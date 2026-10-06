"""スキル関連 API（FIX-02: pending変換, FIX-06: スキル管理）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["スキル"])


class ExtractRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000, description="抽出元テキスト")
    use_rag: bool = Field(default=False, description="RAG補完を使用するか")
    top_k: int = Field(default=20, ge=1, le=100, description="最大候補数")


class RecommendationReasonRequest(BaseModel):
    resume_id: str = Field(..., min_length=1, description="経歴書ID")
    job_id: str = Field(..., min_length=1, description="案件ID")


class JdOptimizationRequest(BaseModel):
    raw_jd: str = Field(..., min_length=1, max_length=40000, description="最適化対象JD")
    budget_range: dict | None = Field(default=None, description="予算レンジ（例: {\"unit_price_max\": 90}\")")


class RecommendationActionsRequest(BaseModel):
    resume_id: str = Field(..., min_length=1, description="経歴書ID")
    top_n: int = Field(default=5, ge=1, le=20, description="推薦件数")


class ScheduleAvailabilityRequest(BaseModel):
    candidate_availability: dict = Field(..., description="候補者の稼働状況")
    job_window: dict = Field(..., description="案件の希望時間帯")


class ScheduleConflictRequest(BaseModel):
    candidate_availability: dict = Field(..., description="候補者の稼働状況")
    other_events: list[dict] = Field(..., description="競合イベント一覧")


@router.post("/skills/extract")
def extract_skills(req: ExtractRequest):
    """自由記述テキストからスキルを抽出する"""
    from src.utils.skill_extraction_service import extract_skills_service
    result = extract_skills_service(text=req.text, use_rag=req.use_rag, top_k=req.top_k)
    return result


@router.post("/skills/recommendation/reason")
def recommendation_reason(req: RecommendationReasonRequest):
    """推薦理由をスキル・業界・経験で分解し、ギャップ分析を返す。"""
    from src.utils.recommendation_reasoning_service import build_recommendation_reason
    return build_recommendation_reason(resume_id=req.resume_id, job_id=req.job_id)


@router.post("/skills/jd/optimize")
def optimize_jd_route(req: JdOptimizationRequest):
    """JDを自動最適化し、スキル抽出・標準化・予算妥当性分析を返す。"""
    from src.utils.jd_optimization_service import optimize_jd
    return optimize_jd(raw_jd=req.raw_jd, budget_range=req.budget_range)


@router.post("/skills/recommendation/actions")
def recommendation_actions(req: RecommendationActionsRequest):
    """推薦順位、連絡優先度、自動コミュニケーション生成を返す。"""
    from src.utils.recommendation_action_service import build_recommendation_actions
    return build_recommendation_actions(resume_id=req.resume_id, top_n=req.top_n)


@router.post("/skills/schedule/availability")
def schedule_availability(req: ScheduleAvailabilityRequest):
    """availability モデリングと時間マッチングを行う。"""
    from src.utils.schedule_management_service import model_availability
    return model_availability(candidate_availability=req.candidate_availability, job_window=req.job_window)


@router.post("/skills/schedule/conflicts")
def schedule_conflicts(req: ScheduleConflictRequest):
    """スケジュール競合を検知する。"""
    from src.utils.schedule_management_service import detect_schedule_conflicts
    return detect_schedule_conflicts(candidate_availability=req.candidate_availability, other_events=req.other_events)


# --- Pendingスキル変換API（FIX-02） ---

def _find_and_update_pending(repo, item_id: str, pending_id: str, update_fn) -> dict:
    """保留スキルを検索・更新する共通処理

    update_fn(p, item) として呼び出される。itemはrepoから取得したリソース全体。
    register/linkはstatus=pendingのみ、ignoreはpending/registeredの両方を許可する。
    """
    item = repo.find_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"リソースID '{item_id}' が見つかりません")
    pending_list = item.get("pending_skills", [])
    found = False
    for p in pending_list:
        if p.get("pending_id") == pending_id:
            # register/link/ignoreは全てpending状態のみ許可（registered/ignoredは終端状態）
            if p.get("status") != "pending":
                raise HTTPException(status_code=400, detail=f"pending_id '{pending_id}' は既に {p['status']} 状態です（終端状態のため変更不可）")
            update_fn(p, item)
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail=f"pending_id '{pending_id}' が見つかりません")
    repo.update(item_id, item)
    return item


@router.post("/resumes/{resume_id}/pending-skills/{pending_id}/register")
def pending_skill_register(resume_id: str, pending_id: str):
    """保留スキルを新規スキルとして辞書に登録"""
    import config
    from src.repository.json_resume_repo import JsonResumeRepository
    from src.utils.skill_dictionary import add_skill
    repo = JsonResumeRepository(config.RESUMES_FILE)

    result_skill_id = [None]

    def _register(p: dict, item: dict):
        raw_name = p.get("raw_name", "")
        if not raw_name:
            raise HTTPException(status_code=400, detail="raw_name が空です")
        new_skill = add_skill(name=raw_name)
        result_skill_id[0] = new_skill["id"]
        p["status"] = "registered"
        p["registered_skill_id"] = new_skill["id"]
        p["resolved_at"] = __import__('datetime').datetime.now().isoformat()
        existing_ids = {s["skill_id"] for s in item.get("structured_skills", [])}
        if new_skill["id"] not in existing_ids:
            item.setdefault("structured_skills", []).append({
                "skill_id": new_skill["id"],
                "level": p.get("level") or 1,
                "years": p.get("years") or 0,
                "last_used_year": p.get("last_used_year") or __import__('datetime').datetime.now().year,
                "estimated": False,
            })

    _find_and_update_pending(repo, resume_id, pending_id, _register)
    return {"status": "registered", "registered_skill_id": result_skill_id[0]}


@router.post("/resumes/{resume_id}/pending-skills/{pending_id}/link")
def pending_skill_link(resume_id: str, pending_id: str, request: dict):
    """保留スキルを既存スキルに紐付け"""
    import config
    from src.repository.json_resume_repo import JsonResumeRepository
    from src.utils.skill_dictionary import get_skill_by_id
    repo = JsonResumeRepository(config.RESUMES_FILE)

    skill_id = request.get("skill_id", "")
    if not skill_id or not get_skill_by_id(skill_id):
        raise HTTPException(status_code=400, detail=f"存在しないskill_idです: {skill_id}")

    def _link(p: dict, item: dict):
        p["status"] = "registered"
        p["registered_skill_id"] = skill_id
        p["resolved_at"] = __import__('datetime').datetime.now().isoformat()
        existing_ids = {s["skill_id"] for s in item.get("structured_skills", [])}
        if skill_id not in existing_ids:
            item.setdefault("structured_skills", []).append({
                "skill_id": skill_id,
                "level": p.get("level") or 1,
                "years": p.get("years") or 0,
                "last_used_year": p.get("last_used_year") or __import__('datetime').datetime.now().year,
                "estimated": False,
            })

    item = _find_and_update_pending(repo, resume_id, pending_id, _link)
    return {"status": "registered", "linked_skill_id": skill_id}


@router.post("/resumes/{resume_id}/pending-skills/{pending_id}/ignore")
def pending_skill_ignore(resume_id: str, pending_id: str):
    """保留スキルを無視（status=ignored）"""
    import config
    from src.repository.json_resume_repo import JsonResumeRepository
    repo = JsonResumeRepository(config.RESUMES_FILE)

    def _ignore(p: dict, item: dict):
        p["status"] = "ignored"
        p["resolved_at"] = __import__('datetime').datetime.now().isoformat()
        # registered済みpendingをignore→structured_skillsから除去
        if p.get("registered_skill_id"):
            sid = p["registered_skill_id"]
            skey = "structured_skills"
            item[skey] = [s for s in item.get(skey, []) if s.get("skill_id") != sid]

    _find_and_update_pending(repo, resume_id, pending_id, _ignore)
    return {"status": "ignored"}


# Job用エンドポイント

@router.post("/jobs/{job_id}/pending-skills/{pending_id}/register")
def job_pending_skill_register(job_id: str, pending_id: str):
    """Job保留スキルを新規スキルとして辞書に登録"""
    import config
    from src.repository.json_job_repo import JsonJobRepository
    from src.utils.skill_dictionary import add_skill
    repo = JsonJobRepository(config.JOBS_FILE)

    result_skill_id = [None]

    def _register(p: dict, item: dict):
        raw_name = p.get("raw_name", "")
        if not raw_name:
            raise HTTPException(status_code=400, detail="raw_name が空です")
        new_skill = add_skill(name=raw_name)
        result_skill_id[0] = new_skill["id"]
        p["status"] = "registered"
        p["registered_skill_id"] = new_skill["id"]
        p["resolved_at"] = __import__('datetime').datetime.now().isoformat()
        utype = p.get("usage_type", "required")
        key = "structured_required_skills" if utype == "required" else "structured_preferred_skills"
        existing_ids = {s["skill_id"] for s in item.get(key, [])}
        if new_skill["id"] not in existing_ids:
            item.setdefault(key, []).append({
                "skill_id": new_skill["id"],
                "required_level": p.get("required_level") or 1,
                "required_years": p.get("required_years") or 0,
            })

    _find_and_update_pending(repo, job_id, pending_id, _register)
    return {"status": "registered", "registered_skill_id": result_skill_id[0]}


@router.post("/jobs/{job_id}/pending-skills/{pending_id}/link")
def job_pending_skill_link(job_id: str, pending_id: str, request: dict):
    """Job保留スキルを既存スキルに紐付け"""
    import config
    from src.repository.json_job_repo import JsonJobRepository
    from src.utils.skill_dictionary import get_skill_by_id
    repo = JsonJobRepository(config.JOBS_FILE)

    skill_id = request.get("skill_id", "")
    if not skill_id or not get_skill_by_id(skill_id):
        raise HTTPException(status_code=400, detail=f"存在しないskill_idです: {skill_id}")

    def _link(p: dict, item: dict):
        p["status"] = "registered"
        p["registered_skill_id"] = skill_id
        p["resolved_at"] = __import__('datetime').datetime.now().isoformat()
        utype = p.get("usage_type", "required")
        key = "structured_required_skills" if utype == "required" else "structured_preferred_skills"
        existing_ids = {s["skill_id"] for s in item.get(key, [])}
        if skill_id not in existing_ids:
            item.setdefault(key, []).append({
                "skill_id": skill_id,
                "required_level": p.get("required_level") or 1,
                "required_years": p.get("required_years") or 0,
            })

    item = _find_and_update_pending(repo, job_id, pending_id, _link)
    return {"status": "registered", "linked_skill_id": skill_id}


@router.post("/jobs/{job_id}/pending-skills/{pending_id}/ignore")
def job_pending_skill_ignore(job_id: str, pending_id: str):
    """Job保留スキルを無視"""
    import config
    from src.repository.json_job_repo import JsonJobRepository
    repo = JsonJobRepository(config.JOBS_FILE)

    def _ignore(p: dict, item: dict):
        p["status"] = "ignored"
        p["resolved_at"] = __import__('datetime').datetime.now().isoformat()
        if p.get("registered_skill_id"):
            sid = p["registered_skill_id"]
            for skey in ("structured_required_skills", "structured_preferred_skills"):
                item[skey] = [s for s in item.get(skey, []) if s.get("skill_id") != sid]

    _find_and_update_pending(repo, job_id, pending_id, _ignore)
    return {"status": "ignored"}


# --- 類似スキル検索（FIX-02） ---

@router.get("/skills/similar")
def similar_skills(name: str):
    """類似スキル名を検索"""
    from src.utils.skill_dictionary import search_skills
    results = search_skills(name)
    return {"results": results}


# --- スキル管理API（FIX-06） ---

@router.get("/skills")
def list_skills(name: str = "", category: str = ""):
    """スキル一覧を取得（名前・カテゴリでフィルタ可能）"""
    from src.utils.skill_dictionary import get_all_skills, search_skills, get_skills_by_category
    if name:
        return {"skills": search_skills(name)}
    if category:
        return {"skills": get_skills_by_category(category)}
    return {"skills": get_all_skills()}


@router.post("/skills", status_code=201)
def create_skill(skill: dict):
    """新規スキルを登録"""
    from src.utils.skill_dictionary import add_skill
    name = skill.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="スキル名は必須です")
    try:
        result = add_skill(name=name, category=skill.get("category", ""),
                           aliases=skill.get("aliases", []),
                           parent_id=skill.get("parent_id"))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/skills/{skill_id}")
def update_skill(skill_id: str, skill: dict):
    """スキル情報を更新"""
    from src.utils.skill_dictionary import update_skill
    try:
        result = update_skill(skill_id, name=skill.get("name"),
                              category=skill.get("category"),
                              aliases=skill.get("aliases"))
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: str):
    """スキルを論理削除"""
    from src.utils.skill_dictionary import delete_skill, get_skill_references
    refs = get_skill_references(skill_id)
    try:
        result = delete_skill(skill_id)
        return {"skill": result, "references": refs}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/skills/{skill_id}/tree")
def skill_tree_position(skill_id: str):
    """スキルのツリー上の位置を取得"""
    from src.utils.skill_dictionary import find_skill_in_tree, get_skill_path
    node = find_skill_in_tree(skill_id)
    path = get_skill_path(skill_id)
    return {"node": node, "path": path}


@router.get("/skills/{skill_id}/references")
def skill_references(skill_id: str):
    """スキルを参照しているJob/Resume一覧"""
    from src.utils.skill_dictionary import get_skill_references
    return get_skill_references(skill_id)


@router.post("/skills/validate")
def validate_skills():
    """スキル辞書とツリーの整合性を検証"""
    from src.utils.skill_dictionary import validate_consistency
    issues = validate_consistency()
    return {"valid": len(issues) == 0, "issues": issues}
