"""経歴書 CRUD API ルート

REQ-RE4-01: 原リクエスト判定による旧形式スキル自動変換
REQ-RE4-08: 変換後Pydantic検証結果の保存（model_dump）
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
import config
from src.repository.json_resume_repo import JsonResumeRepository


def _auto_convert_skills(data: dict) -> list[dict]:
    """旧形式 skills → structured_skills 自動変換（REQ-RE4-01）

    原リクエストで structured_skills 未指定時に旧形式から自動生成する。
    呼出元で「structured_skills が原リクエストに存在しないこと」を確認してから呼ぶこと。

    Returns:
        未解決スキルのリスト（変換できなかった旧形式スキル名）。空リストなら全件解決済み。
    """
    from src.utils.skill_dictionary import resolve_skill_id
    current_year = __import__('datetime').datetime.now().year

    old_skills = data.get("skills")
    unresolved = []
    converted = []

    if not old_skills or not isinstance(old_skills, dict):
        return unresolved  # 旧形式なし

    for items in old_skills.values():
        if not isinstance(items, list):
            continue
        for name in items:
            if not isinstance(name, str) or not name.strip():
                continue
            sid = resolve_skill_id(name)
            if sid is None:
                unresolved.append({"field": "skills.*", "raw_value": name, "reason": "SKILL_NOT_REGISTERED"})
                continue
            converted.append({
                "skill_id": sid,
                "level": 1,
                "years": 0,
                "last_used_year": current_year,
                "estimated": True,
            })

    if converted:
        data["structured_skills"] = converted
    return unresolved


def _normalize_skill_ids(skills: list[dict]) -> None:
    """スキルIDを同義語解決し正規IDに書き換える（REQ-RE3-01）"""
    from src.utils.skill_dictionary import resolve_skill_id
    for s in skills:
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


def _separate_skills(skills: list[dict]) -> tuple[list[dict], list[dict]]:
    """structured_skillsを登録済みと未登録に分離（FIX-02）

    Returns:
        (registered_skills, pending_data) のタプル。
        pending_dataは {raw_value, level, years, last_used_year} を含む。
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
                "level": s.get("level"),
                "years": s.get("years"),
                "last_used_year": s.get("last_used_year"),
            })
    return registered, pending_data


def _collect_pending_skills(unresolved: list[dict], owner_type: str, owner_id: str, usage_type: str = "resume") -> list[dict]:
    """未解決スキルリストからPendingSkill dictリストを生成（FIX-02）"""
    import uuid
    import datetime
    pending = []
    for u in unresolved:
        pending.append({
            "pending_id": str(uuid.uuid4()),
            "owner_type": owner_type,
            "owner_id": owner_id,
            "raw_name": u.get("raw_value", ""),
            "usage_type": usage_type,
            "level": u.get("level"),
            "years": u.get("years"),
            "last_used_year": u.get("last_used_year"),
            "required_level": None,
            "required_years": None,
            "status": "pending",
            "registered_skill_id": None,
            "created_at": datetime.datetime.now().isoformat(),
            "resolved_at": None,
        })
    return pending


def _build_warnings(pending_skills: list[dict]) -> list[dict]:
    """APIレスポンス用の警告リストを生成"""
    return [
        {"code": "SKILL_NOT_REGISTERED", "raw_name": p["raw_name"], "pending_id": p["pending_id"]}
        for p in pending_skills
    ]


def _process_skills(item: dict, old_skills_raw: dict, owner_id: str = "") -> list[dict]:
    """スキル変換・同義語正規化・保留スキル収集（FIX-02）

    structured_skillsから未登録IDを除去し、pending_skillsへ移動する。

    Returns:
        pending_skills のリスト。空リストなら保留スキルなし。
    """
    import uuid
    import datetime
    unresolved_old = _auto_convert_skills(item)

    pending_items = []

    # structured_skills 内の未登録IDを分離
    if "structured_skills" in item and item["structured_skills"]:
        _normalize_skill_ids(item["structured_skills"])
        registered, pending_data = _separate_skills(item["structured_skills"])
        item["structured_skills"] = registered
        for pd in pending_data:
            pending_items.append({
                "pending_id": str(uuid.uuid4()),
                "owner_type": "resume",
                "owner_id": owner_id,
                "raw_name": pd["raw_value"],
                "usage_type": "resume",
                "level": pd.get("level"),
                "years": pd.get("years"),
                "last_used_year": pd.get("last_used_year"),
                "required_level": None, "required_years": None,
                "status": "pending",
                "registered_skill_id": None,
                "created_at": datetime.datetime.now().isoformat(),
                "resolved_at": None,
            })

    # 旧形式変換で解決できなかったスキルもpendingへ
    for u in unresolved_old:
        pending_items.append({
            "pending_id": str(uuid.uuid4()),
            "owner_type": "resume",
            "owner_id": owner_id,
            "raw_name": u.get("raw_value", ""),
            "usage_type": "resume",
            "level": None, "years": None, "last_used_year": None,
            "required_level": None, "required_years": None,
            "status": "pending",
            "registered_skill_id": None,
            "created_at": datetime.datetime.now().isoformat(),
            "resolved_at": None,
        })

    return pending_items


def _merge_pending_skills(existing: list[dict], new_items: list[dict]) -> list[dict]:
    """既存pending_skillsと新規pending_skillsをマージ（FIX-02）

    - pending_idが一致→既存を維持
    - (raw_name, usage_type) が既存pendingに存在 → 追加しない
    - 異なるusage_typeの同じraw_nameは別エントリとして追加可能
    """
    seen_ids = {p["pending_id"] for p in existing}
    seen_keys = {(p["raw_name"], p.get("usage_type", "")) for p in existing}
    merged = list(existing)
    for p in new_items:
        key = (p["raw_name"], p.get("usage_type", ""))
        if p["pending_id"] not in seen_ids and key not in seen_keys:
            merged.append(p)
            seen_ids.add(p["pending_id"])
            seen_keys.add(key)
    return merged


router = APIRouter(tags=["経歴書"])
repo = JsonResumeRepository(config.RESUMES_FILE)


@router.get("/resumes")
def list_resumes(skills: str = ""):
    """経歴書一覧を取得（任意でスキルフィルタ）"""
    items = repo.find_all()
    if skills:
        skill_list = [s.strip() for s in skills.split(",") if s.strip()]
        filtered = []
        for item in items:
            all_skills = []
            s = item.get("skills", {})
            for key in ("languages", "frameworks", "tools", "certifications", "other"):
                all_skills.extend(s.get(key, []))
            for ss in item.get("structured_skills", []):
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


@router.get("/resumes/{resume_id}")
def get_resume(resume_id: str):
    """経歴書を1件取得"""
    item = repo.find_by_id(resume_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"経歴書ID '{resume_id}' が見つかりません")
    return item


@router.post("/resumes", status_code=201)
def create_resume(resume: dict):
    """経歴書を新規作成（REQ-RE4-01: 原リクエスト判定＋二段階検証、FIX-02: pending対応）"""
    # 1. 原リクエスト判定（model_validate前）
    has_structured = "structured_skills" in resume
    # クライアントからのpending_skillsは無視（サーバー側で生成）
    resume.pop("pending_skills", None)
    # 同義語正規化→重複統合（FIX-04: この順序で実施、JS/javascriptを統合）
    if "structured_skills" in resume and resume["structured_skills"]:
        _normalize_skill_ids(resume["structured_skills"])
        from src.utils.skill_utils import deduplicate_resume_skills
        resume["structured_skills"] = deduplicate_resume_skills(resume["structured_skills"])

    # 2. 原データPydantic検証
    try:
        from src.models.resume import Resume
        validated = Resume.model_validate(resume)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=_format_validation_error(e))
    item = validated.model_dump()

    item_id = item.get("id")
    if repo.exists(item_id):
        raise HTTPException(status_code=409, detail=f"ID '{item_id}' は既に存在します")

    # 3. スキル処理＋保留スキル収集（FIX-02）
    pending_items = _process_skills(item, resume.get("skills", {}), owner_id=item_id) if not has_structured else []
    if has_structured and "structured_skills" in item and item["structured_skills"]:
        _normalize_skill_ids(item["structured_skills"])
        registered, pending_data = _separate_skills(item["structured_skills"])
        item["structured_skills"] = registered
        import uuid, datetime
        for pd in pending_data:
            pending_items.append({
                "pending_id": str(uuid.uuid4()), "owner_type": "resume", "owner_id": item_id,
                "raw_name": pd["raw_value"], "usage_type": "resume",
                "level": pd.get("level"), "years": pd.get("years"),
                "last_used_year": pd.get("last_used_year"),
                "required_level": None, "required_years": None,
                "status": "pending", "registered_skill_id": None,
                "created_at": datetime.datetime.now().isoformat(), "resolved_at": None,
            })

    # 保留スキルをitemに追加
    if pending_items:
        item["pending_skills"] = pending_items

    # 4. 変換後Pydantic再検証（REQ-RE4-08）
    try:
        validated = Resume.model_validate(item)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=_format_validation_error(e))
    item = validated.model_dump()

    result = repo.create(item)
    from src.utils.market_event_log import record_resume_registered
    record_resume_registered(result)
    if pending_items:
        result["warnings"] = _build_warnings(pending_items)
    return result


@router.put("/resumes/{resume_id}")
def update_resume(resume_id: str, resume: dict):
    """経歴書を更新（REQ-RE4-01: 原リクエスト判定＋二段階検証、FIX-02: pending対応）"""
    if not repo.exists(resume_id):
        raise HTTPException(status_code=404, detail=f"経歴書ID '{resume_id}' が見つかりません")

    has_structured = "structured_skills" in resume
    # クライアントからのpending_skillsは無視（サーバー側で管理）
    resume.pop("pending_skills", None)
    # 同義語正規化→重複統合（FIX-04: この順序で実施）
    if "structured_skills" in resume and resume["structured_skills"]:
        _normalize_skill_ids(resume["structured_skills"])
        from src.utils.skill_utils import deduplicate_resume_skills
        resume["structured_skills"] = deduplicate_resume_skills(resume["structured_skills"])

    try:
        from src.models.resume import Resume
        validated = Resume.model_validate(resume)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=_format_validation_error(e))
    item = validated.model_dump()

    pending_items = _process_skills(item, resume.get("skills", {}), owner_id=resume_id) if not has_structured else []
    if has_structured and "structured_skills" in item and item["structured_skills"]:
        _normalize_skill_ids(item["structured_skills"])
        registered, pending_data = _separate_skills(item["structured_skills"])
        item["structured_skills"] = registered
        import uuid, datetime
        for pd in pending_data:
            pending_items.append({
                "pending_id": str(uuid.uuid4()), "owner_type": "resume", "owner_id": resume_id,
                "raw_name": pd["raw_value"], "usage_type": "resume",
                "level": pd.get("level"), "years": pd.get("years"),
                "last_used_year": pd.get("last_used_year"),
                "required_level": None, "required_years": None,
                "status": "pending", "registered_skill_id": None,
                "created_at": datetime.datetime.now().isoformat(), "resolved_at": None,
            })
    # 既存pendingとマージ（FIX-02: 更新時に既存pendingを保持）
    existing_item = repo.find_by_id(resume_id)
    existing_pending = existing_item.get("pending_skills", []) if existing_item else []
    merged_pending = _merge_pending_skills(existing_pending, pending_items)
    if merged_pending:
        item["pending_skills"] = merged_pending

    try:
        validated = Resume.model_validate(item)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=_format_validation_error(e))
    item = validated.model_dump()

    result = repo.update(resume_id, item)
    if pending_items:
        result.setdefault("warnings", []).extend(_build_warnings(pending_items))
    return result


@router.delete("/resumes/{resume_id}", status_code=204)
def delete_resume(resume_id: str):
    """経歴書を削除"""
    if not repo.delete(resume_id):
        raise HTTPException(status_code=404, detail=f"経歴書ID '{resume_id}' が見つかりません")
    return None


@router.post("/resumes/load-samples")
def load_sample_resumes():
    """サンプル経歴書を一括読込（REQ-RE4-01/08: 二段階検証＋model_dump保存）"""
    import json
    if not config.ENABLE_SAMPLE_LOAD:
        raise HTTPException(status_code=404, detail="サンプル読込は無効です")

    sample_path = Path(config.SAMPLE_RESUMES_FILE)
    if not sample_path.exists():
        raise HTTPException(status_code=500, detail="サンプルファイルが見つかりません")

    with open(sample_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    results = {"created": 0, "skipped": 0, "failed": 0, "unresolved_skills": [], "errors": [], "committed": False}
    new_items = []
    all_ok = True

    from src.models.resume import Resume

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
            Resume.model_validate(sample)
        except Exception as ve:
            results["failed"] += 1
            results["errors"].append({"id": sid, "error": f"Schema検証エラー: {ve}"})
            all_ok = False
            continue

        item = dict(sample)

        # 2. スキル変換（create/updateと同様、キーの存在で判定）
        from src.utils.skill_dictionary import resolve_skill_id
        has_structured = "structured_skills" in sample
        unresolved = []
        if has_structured:
            # structured形式が存在する場合（空リスト含む）、旧形式を変換せずそのまま使用
            item["structured_skills"] = sample.get("structured_skills", [])
        else:
            # structured形式がない場合のみ旧形式から変換
            old_skills = sample.get("skills", {})
            unresolved = _auto_convert_skills(item)

        # 未解決スキルを収集（黙って削除しない）
        for us in unresolved:
            us["record_id"] = sid
            results["unresolved_skills"].append(us)

        # 保留スキル生成（旧形式からの未登録）
        pending_items = _collect_pending_skills(unresolved, "resume", sid)

        # 3. 同義語正規化→重複統合→未登録ID分離（FIX-04）
        if "structured_skills" in item and item["structured_skills"]:
            _normalize_skill_ids(item["structured_skills"])
            from src.utils.skill_utils import deduplicate_resume_skills
            item["structured_skills"] = deduplicate_resume_skills(item["structured_skills"])
            registered, pending_data = _separate_skills(item["structured_skills"])
            item["structured_skills"] = registered
            pending_items.extend(_collect_pending_skills(pending_data, "resume", sid))

        if pending_items:
            item["pending_skills"] = pending_items

        # 4. 変換後Pydantic再検証（REQ-RE4-08）
        try:
            validated = Resume.model_validate(item)
            item_to_save = validated.model_dump()
        except Exception as ve:
            results["failed"] += 1
            results["errors"].append({"id": sid, "error": f"変換後スキーマ検証エラー: {ve}"})
            all_ok = False
            continue

        new_items.append(item_to_save)

    if not all_ok:
        results["committed"] = False
        return results

    # 全件OK → bulk_merge
    from src.repository.json_resume_repo import JsonResumeRepository
    from src.repository.exceptions import FileLockTimeoutError, RepositoryError

    merge_repo = JsonResumeRepository(config.RESUMES_FILE)
    existing_ids_before = {r["id"] for r in merge_repo.find_all()}
    try:
        merge_result = merge_repo.bulk_merge(new_items, on_conflict="skip")
    except FileLockTimeoutError as e:
        raise HTTPException(status_code=503, detail=f"ロック獲得タイムアウト: {e}")
    except RepositoryError as e:
        raise HTTPException(status_code=500, detail=f"リポジトリエラー: {e}")

    from src.utils.market_event_log import record_resume_registered
    for created_item in new_items:
        if created_item["id"] not in existing_ids_before:
            record_resume_registered(created_item)

    results["created"] = merge_result["created"]
    results["skipped"] = merge_result["skipped"]
    results["committed"] = True
    return results
