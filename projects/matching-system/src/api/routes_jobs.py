"""案件 CRUD API ルート

REQ-RE4-01: 原リクエスト個別判定による旧形式スキル自動変換（required/preferred個別）
REQ-RE4-08: 変換後Pydantic検証結果の保存（model_dump）
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
import config
from src.repository.json_job_repo import JsonJobRepository


def _auto_convert_job_skills(data: dict) -> list[dict]:
    """旧形式 required_skills/preferred_skills → structured_* 自動変換（REQ-RE4-01）

    呼出元で各フィールドの原リクエスト有無を確認してから呼ぶこと。

    Returns:
        未解決スキルのリスト。
    """
    from src.utils.skill_dictionary import resolve_skill_id
    unresolved = []

    for old_key, new_key in [("required_skills", "structured_required_skills"),
                               ("preferred_skills", "structured_preferred_skills")]:
        if new_key in data:
            continue  # 呼出元で制御済みだが念のため
        old = data.get(old_key)
        if not old or not isinstance(old, dict):
            continue
        converted = []
        for items in old.values():
            if not isinstance(items, list):
                continue
            for name in items:
                if not isinstance(name, str) or not name.strip():
                    continue
                sid = resolve_skill_id(name)
                if sid is None:
                    unresolved.append({"field": f"{old_key}.*", "raw_value": name, "reason": "SKILL_NOT_REGISTERED"})
                    continue
                converted.append({
                    "skill_id": sid,
                    "required_level": 3,
                    "required_years": 3,
                })
        if converted:
            data[new_key] = converted

    return unresolved


def _normalize_job_skill_ids(job: dict) -> None:
    """案件スキルIDを同義語解決（REQ-RE3-01）"""
    from src.utils.skill_dictionary import resolve_skill_id
    for key in ("structured_required_skills", "structured_preferred_skills"):
        for s in job.get(key, []):
            sid = s.get("skill_id", "") if isinstance(s, dict) else getattr(s, "skill_id", "")
            if not sid:
                continue
            resolved = resolve_skill_id(sid)
            if resolved and resolved != sid:
                if isinstance(s, dict):
                    s["skill_id"] = resolved
                else:
                    s.skill_id = resolved


def _format_validation_error(e: ValidationError) -> dict:
    """Pydantic ValidationErrorを統一エラーレスポンス形式に整形"""
    errors = []
    for err in e.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []))
        errors.append({
            "field": field,
            "message": err.get("msg", ""),
            "type": err.get("type", ""),
        })
    return {"code": "VALIDATION_ERROR", "errors": errors}


def _separate_job_skills(skills: list[dict], usage_type: str) -> tuple[list[dict], list[dict]]:
    """案件structured_skillsを登録済みと未登録に分離（FIX-02）

    Returns:
        (registered_skills, pending_data)
        pending_dataは {raw_value, required_level, required_years} を含む。
    """
    from src.utils.skill_dictionary import resolve_skill_id, get_skill_by_id
    registered = []
    pending_data = []
    for s in skills:
        sid = s.get("skill_id", "") if isinstance(s, dict) else getattr(s, "skill_id", "")
        if not sid:
            continue
        resolved = resolve_skill_id(sid) or get_skill_by_id(sid)
        if resolved:
            registered.append(s)
        else:
            pending_data.append({
                "raw_value": sid,
                "required_level": s.get("required_level"),
                "required_years": s.get("required_years"),
                "usage_type": usage_type,
            })
    return registered, pending_data


def _collect_pending_skills(unresolved: list[dict], owner_type: str, owner_id: str, usage_type: str = "required") -> list[dict]:
    """未解決スキルからPendingSkill dictを生成（共通）"""
    import uuid, datetime
    return [{
        "pending_id": str(uuid.uuid4()), "owner_type": owner_type, "owner_id": owner_id,
        "raw_name": u.get("raw_value", ""), "usage_type": usage_type,
        "level": u.get("level"), "years": u.get("years"), "last_used_year": u.get("last_used_year"),
        "required_level": u.get("required_level"), "required_years": u.get("required_years"),
        "status": "pending", "registered_skill_id": None,
        "created_at": datetime.datetime.now().isoformat(), "resolved_at": None,
    } for u in unresolved]


def _collect_pending_job_skills(unresolved: list[dict], owner_id: str) -> list[dict]:
    """未解決案件スキルからPendingSkill dictリストを生成"""
    usage_map = {"required_skills.*": "required", "preferred_skills.*": "preferred"}
    all_pending = []
    for u in unresolved:
        field = u.get("field", "")
        all_pending.extend(_collect_pending_skills([u], "job", owner_id, usage_map.get(field, "required")))
    return all_pending


def _build_warnings(pending_skills: list[dict]) -> list[dict]:
    """APIレスポンス用の警告リストを生成"""
    return [
        {"code": "SKILL_NOT_REGISTERED", "raw_name": p["raw_name"], "pending_id": p["pending_id"]}
        for p in pending_skills
    ]


router = APIRouter(tags=["案件"])
repo = JsonJobRepository(config.JOBS_FILE)


@router.get("/jobs")
def list_jobs(skills: str = ""):
    """案件一覧を取得（任意でスキルフィルタ）"""
    items = repo.find_all()
    if skills:
        skill_list = [s.strip() for s in skills.split(",") if s.strip()]
        filtered = []
        for item in items:
            all_skills = []
            for skill_type in ("required_skills", "preferred_skills"):
                s = item.get(skill_type, {})
                for key in ("languages", "frameworks", "tools", "certifications", "other"):
                    all_skills.extend(s.get(key, []))
            for key in ("structured_required_skills", "structured_preferred_skills"):
                for ss in item.get(key, []):
                    sid = ss.get("skill_id", "") if isinstance(ss, dict) else getattr(ss, "skill_id", "")
                    if sid:
                        all_skills.append(sid)
            if any(
                any(skill.lower() in user_skill.lower() for user_skill in all_skills)
                for skill in skill_list
            ):
                filtered.append(item)
        return filtered
    return items


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    """案件を1件取得"""
    item = repo.find_by_id(job_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"案件ID '{job_id}' が見つかりません")
    return item


@router.post("/jobs", status_code=201)
def create_job(job: dict):
    """案件を新規作成（REQ-RE4-01 + FIX-02: pending対応）"""
    has_required = "structured_required_skills" in job
    has_preferred = "structured_preferred_skills" in job
    job.pop("pending_skills", None)  # クライアントからのpendingは無視
    # 同義語正規化→重複チェック（FIX-04: この順序で実施）
    _normalize_job_skill_ids(job)
    for key, fname in [("structured_required_skills", "structured_required_skills"),
                        ("structured_preferred_skills", "structured_preferred_skills")]:
        if key in job and job[key]:
            from src.utils.skill_utils import validate_job_skills_no_duplicates
            try:
                validate_job_skills_no_duplicates(job[key], field_name=fname)
            except ValueError as e:
                raise HTTPException(status_code=400, detail={"code": "DUPLICATE_SKILL_ID", "message": str(e)})

    try:
        from src.models.job import Job
        validated = Job.model_validate(job)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=_format_validation_error(e))
    item = validated.model_dump()

    item_id = item.get("id")
    if repo.exists(item_id):
        raise HTTPException(status_code=409, detail=f"ID '{item_id}' は既に存在します")

    # 旧形式スキル変換（原リクエストでstructured_未指定時のみ）
    unresolved = []
    pending_items = []
    if not has_required or not has_preferred:
        if not has_required and "structured_required_skills" in item:
            del item["structured_required_skills"]
        if not has_preferred and "structured_preferred_skills" in item:
            del item["structured_preferred_skills"]
        unresolved = _auto_convert_job_skills(item)

    # 同義語正規化
    _normalize_job_skill_ids(item)

    # structured_* 内の未登録IDを分離
    for key, utype in [("structured_required_skills", "required"), ("structured_preferred_skills", "preferred")]:
        if key in item and item[key]:
            registered, pending_data = _separate_job_skills(item[key], utype)
            item[key] = registered
            pending_items.extend(_collect_pending_skills(pending_data, "job", item_id, utype))

    # 旧形式変換で解決できなかったスキルもpendingへ
    if unresolved:
        pending_items.extend(_collect_pending_job_skills(unresolved, item_id))

    # 保留スキルをitemに追加
    if pending_items:
        item["pending_skills"] = pending_items

    # 変換後Pydantic再検証（REQ-RE4-08）
    try:
        validated = Job.model_validate(item)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=_format_validation_error(e))
    item = validated.model_dump()

    result = repo.create(item)
    from src.utils.market_event_log import record_job_posted
    record_job_posted(result)
    if pending_items:
        result["warnings"] = _build_warnings(pending_items)
    return result


@router.put("/jobs/{job_id}")
def update_job(job_id: str, job: dict):
    """案件を更新（REQ-RE4-01 + FIX-02: pending対応）"""
    if not repo.exists(job_id):
        raise HTTPException(status_code=404, detail=f"案件ID '{job_id}' が見つかりません")

    has_required = "structured_required_skills" in job
    has_preferred = "structured_preferred_skills" in job
    job.pop("pending_skills", None)  # クライアントからのpendingは無視
    # 同義語正規化→重複チェック（FIX-04: この順序で実施）
    _normalize_job_skill_ids(job)
    for key, fname in [("structured_required_skills", "structured_required_skills"),
                        ("structured_preferred_skills", "structured_preferred_skills")]:
        if key in job and job[key]:
            from src.utils.skill_utils import validate_job_skills_no_duplicates
            try:
                validate_job_skills_no_duplicates(job[key], field_name=fname)
            except ValueError as e:
                raise HTTPException(status_code=400, detail={"code": "DUPLICATE_SKILL_ID", "message": str(e)})

    try:
        from src.models.job import Job
        validated = Job.model_validate(job)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=_format_validation_error(e))
    item = validated.model_dump()

    unresolved = []
    pending_items = []
    if not has_required or not has_preferred:
        if not has_required and "structured_required_skills" in item:
            del item["structured_required_skills"]
        if not has_preferred and "structured_preferred_skills" in item:
            del item["structured_preferred_skills"]
        unresolved = _auto_convert_job_skills(item)

    _normalize_job_skill_ids(item)

    for key, utype in [("structured_required_skills", "required"), ("structured_preferred_skills", "preferred")]:
        if key in item and item[key]:
            registered, pending_data = _separate_job_skills(item[key], utype)
            item[key] = registered
            pending_items.extend(_collect_pending_skills(pending_data, "job", job_id, utype))

    if unresolved:
        pending_items.extend(_collect_pending_job_skills(unresolved, job_id))

    # 既存pendingとマージ（FIX-02: 更新時に既存pendingを保持）
    existing_item = repo.find_by_id(job_id)
    existing_pending = existing_item.get("pending_skills", []) if existing_item else []
    seen_ids = {p["pending_id"] for p in existing_pending}
    seen_keys = {(p["raw_name"], p.get("usage_type", "")) for p in existing_pending}
    merged_pending = list(existing_pending)
    for p in pending_items:
        key = (p["raw_name"], p.get("usage_type", ""))
        if p["pending_id"] not in seen_ids and key not in seen_keys:
            merged_pending.append(p)
            seen_ids.add(p["pending_id"])
            seen_keys.add(key)
    if merged_pending:
        item["pending_skills"] = merged_pending

    try:
        validated = Job.model_validate(item)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=_format_validation_error(e))
    item = validated.model_dump()

    result = repo.update(job_id, item)
    if pending_items:
        result.setdefault("warnings", []).extend(_build_warnings(pending_items))
    return result


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str):
    """案件を削除"""
    if not repo.delete(job_id):
        raise HTTPException(status_code=404, detail=f"案件ID '{job_id}' が見つかりません")
    from src.utils.market_event_log import record_job_closed
    record_job_closed(job_id)
    return None


@router.post("/jobs/load-samples")
def load_sample_jobs():
    """サンプル案件を一括読込（REQ-RE4-01/08: 二段階検証＋model_dump保存）"""
    import json
    if not config.ENABLE_SAMPLE_LOAD:
        raise HTTPException(status_code=404, detail="サンプル読込は無効です")

    sample_path = Path(config.SAMPLE_JOBS_FILE)
    if not sample_path.exists():
        raise HTTPException(status_code=500, detail="サンプルファイルが見つかりません")

    with open(sample_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    results = {"created": 0, "skipped": 0, "failed": 0, "unresolved_skills": [], "errors": [], "committed": False}
    new_items = []
    all_ok = True

    from src.models.job import Job

    # 同一ファイル内重複IDチェック
    seen_ids_in_file = set()
    for sample in samples:
        sid = sample.get("id", "")
        if not sid:
            continue
        if sid in seen_ids_in_file:
            results["failed"] += 1
            results["errors"].append({"id": sid, "error": f"同一ファイル内で重複したIDです: {sid}"})
            all_ok = False
        seen_ids_in_file.add(sid)

    if not all_ok:
        results["committed"] = False
        return results

    for sample in samples:
        sid = sample.get("id", "unknown")

        # 1. 原データPydantic検証
        try:
            Job.model_validate(sample)
        except Exception as ve:
            results["failed"] += 1
            results["errors"].append({"id": sid, "error": f"Schema検証エラー: {ve}"})
            all_ok = False
            continue

        item = dict(sample)

        # 2. スキル変換（create/updateと同様、キーの存在で個別判定）
        from src.utils.skill_dictionary import resolve_skill_id
        # structured形式があるキー（空リスト含む）はそのまま使用、ないキーは旧形式から変換
        req_exists = "structured_required_skills" in sample
        pref_exists = "structured_preferred_skills" in sample
        if req_exists:
            item["structured_required_skills"] = sample.get("structured_required_skills", [])
        if pref_exists:
            item["structured_preferred_skills"] = sample.get("structured_preferred_skills", [])
        # _auto_convert_job_skills は既存キーをスキップ
        unresolved = _auto_convert_job_skills(item)
        for us in unresolved:
            us["record_id"] = sid
            results["unresolved_skills"].append(us)

        # 保留スキルを生成（FIX-02: 未登録スキルは保留として保存）
        pending_items = list(_collect_pending_job_skills(unresolved, sid))

        # 3. 同義語正規化
        _normalize_job_skill_ids(item)

        # 4. 重複チェック（FIX-04）
        from src.utils.skill_utils import validate_job_skills_no_duplicates
        for key in ("structured_required_skills", "structured_preferred_skills"):
            if key in item and item[key]:
                try:
                    validate_job_skills_no_duplicates(item[key], field_name=key)
                except ValueError as e:
                    results["failed"] += 1
                    results["errors"].append({"id": sid, "error": f"重複スキル: {e}"})
                    all_ok = False

        # 5. structured_* 内の未登録IDを分離
        for key, utype in [("structured_required_skills", "required"), ("structured_preferred_skills", "preferred")]:
            if key in item and item[key]:
                registered, pending_data = _separate_job_skills(item[key], utype)
                item[key] = registered
                pending_items.extend(_collect_pending_skills(pending_data, "job", sid, utype))

        if pending_items:
            item["pending_skills"] = pending_items

        # 5. 変換後Pydantic再検証（REQ-RE4-08）
        try:
            validated = Job.model_validate(item)
            item_to_save = validated.model_dump()
        except Exception as ve:
            results["failed"] += 1
            results["errors"].append({"id": sid, "error": f"変換後スキーマ検証エラー: {ve}"})
            all_ok = False
            continue

        # 6. 未登録ID検証は不要（_separate_job_skillsで分離済み）
            results["failed"] += 1
            results["errors"].append({"id": sid, "error": str(e.detail)})
            all_ok = False
            continue

        new_items.append(item_to_save)

    if not all_ok:
        results["committed"] = False
        return results

    # 全件OK → bulk_merge
    from src.repository.json_job_repo import JsonJobRepository
    from src.repository.exceptions import FileLockTimeoutError, RepositoryError

    merge_repo = JsonJobRepository(config.JOBS_FILE)
    existing_ids_before = {j["id"] for j in merge_repo.find_all()}
    try:
        merge_result = merge_repo.bulk_merge(new_items, on_conflict="skip")
    except FileLockTimeoutError as e:
        raise HTTPException(status_code=503, detail=f"ロック獲得タイムアウト: {e}")
    except RepositoryError as e:
        raise HTTPException(status_code=500, detail=f"リポジトリエラー: {e}")

    from src.utils.market_event_log import record_job_posted
    for created_item in new_items:
        if created_item["id"] not in existing_ids_before:
            record_job_posted(created_item)

    results["created"] = merge_result["created"]
    results["skipped"] = merge_result["skipped"]
    results["committed"] = True
    return results
