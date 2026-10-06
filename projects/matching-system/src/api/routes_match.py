"""マッチング API ルート"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, HTTPException, Query
from src.matching.keyword_matcher import KeywordMatcher
from src.matching.semantic_matcher import semantic_match, is_available as semantic_available
from src.matching.embedding_matcher import compute_hybrid_score
from src.models.match_result import (
    SemanticMatchRequest, SemanticMatchResponse,
    HybridBreakdown, RagCorrection, ScheduleMatch,
)
from src.models.match_result import MatchItem as MatchItemModel

router = APIRouter(tags=["マッチング"])
matcher = KeywordMatcher()


def _compute_schedule_match(resume: dict, job: dict) -> ScheduleMatch:
    """候補者の稼働可能日と案件のプロジェクト開始日を比較する"""
    from src.utils.schedule_management_service import model_availability
    from src.ui.display_utils import build_candidate_availability_from_resume

    project_start = job.get("project_start_date") or ""
    if not project_start:
        return ScheduleMatch(status="unknown", message="案件のプロジェクト開始日が未設定です")

    availability = build_candidate_availability_from_resume(resume)
    job_window = {
        "project_start": project_start,
        "start": f"{project_start}T00:00:00",
        "end": f"{project_start}T23:59:59",
    }
    result = model_availability(availability, job_window)
    status = result.get("status", "unknown")
    candidate_from = result.get("candidate_available_from", availability.get("available_from", ""))

    if status == "conflict" and candidate_from and candidate_from > project_start:
        message = f"候補者の稼働可能日（{candidate_from}）が案件開始日（{project_start}）より後のため、スケジュールが一致しません"
    elif status == "conflict":
        message = "候補者の稼働可能時間と案件の稼働時間が一致しません"
    else:
        message = f"候補者は案件開始日（{project_start}）までに稼働可能です"

    return ScheduleMatch(
        status=status,
        score=result.get("availability_score", 0.0),
        candidate_available_from=candidate_from or "",
        project_start_date=project_start,
        message=message,
    )


def _run_hybrid_match(source_id: str, source_repo, target_repo, source_type: str) -> dict:
    """Hybridマッチングを実行（共通処理）"""
    source = source_repo.find_by_id(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"{source_type}ID '{source_id}' が見つかりません")
    targets = target_repo.find_all()
    matches = []
    for target in targets:
        if source_type == "resume":
            result = compute_hybrid_score(source, target)
            matches.append(MatchItemModel(
                target_id=target["id"],
                target_name=target.get("title", ""),
                target_company=target.get("company", ""),
                total_score=result["total_score"],
                mode=result["mode"],
                degraded=result["degraded"],
                weights=result.get("weights", {}),
                hybrid_breakdown=HybridBreakdown(**result["breakdown"]),
                matched_skills=result["matched_skills"],
                missing_required_skills=result["missing_required_skills"],
                missing_preferred_skills=result["missing_preferred_skills"],
                rag_sources=result.get("rag_sources", []),
                rag_corrections=result.get("rag_corrections", []),
                schedule=_compute_schedule_match(source, target),
                explanation=result["explanation"],
            ))
        else:
            result = compute_hybrid_score(target, source)
            matches.append(MatchItemModel(
                target_id=target["id"],
                target_name=target.get("name", ""),
                target_company="",
                total_score=result["total_score"],
                mode=result["mode"],
                degraded=result["degraded"],
                weights=result.get("weights", {}),
                hybrid_breakdown=HybridBreakdown(**result["breakdown"]),
                matched_skills=result["matched_skills"],
                missing_required_skills=result["missing_required_skills"],
                missing_preferred_skills=result["missing_preferred_skills"],
                rag_sources=result.get("rag_sources", []),
                rag_corrections=result.get("rag_corrections", []),
                schedule=_compute_schedule_match(target, source),
                explanation=result["explanation"],
            ))
    matches.sort(key=lambda m: m.total_score, reverse=True)
    from datetime import datetime, timezone, timedelta
    JST = timezone(timedelta(hours=9))
    from src.models.match_result import MatchResult
    return MatchResult(
        source_id=source_id,
        source_type=source_type,
        matches=matches,
        generated_at=datetime.now(JST).isoformat(),
    ).model_dump()


@router.post("/match/resume-to-jobs/{resume_id}")
def match_resume_to_jobs(resume_id: str, mode: str = Query("hybrid", pattern="^(hybrid|keyword|semantic)$")):
    """経歴書に対して全案件をマッチング（REQ-FIX-01: デフォルトHybrid）

    Args:
        resume_id: 経歴書ID
        mode: マッチング方式（hybrid / keyword / semantic、デフォルト hybrid）
    """
    try:
        if mode == "keyword":
            result = matcher.match_resume_to_jobs(resume_id)
            return result.model_dump()
        elif mode == "semantic":
            from src.matching.semantic_matcher import semantic_match
            resume = matcher.resume_repo.find_by_id(resume_id)
            if resume is None:
                raise HTTPException(status_code=404, detail=f"経歴書ID '{resume_id}' が見つかりません")
            jobs = matcher.job_repo.find_all()
            matches = []
            for job in jobs:
                sm = semantic_match(resume_id, job["id"])
                matches.append(MatchItemModel(
                    target_id=job["id"],
                    target_name=job.get("title", ""),
                    target_company=job.get("company", ""),
                    total_score=sm.get("score", 0) / 100.0,
                    mode="semantic",
                    explanation=sm.get("explanation", ""),
                ))
            matches.sort(key=lambda m: m.total_score, reverse=True)
            from datetime import datetime, timezone, timedelta
            JST = timezone(timedelta(hours=9))
            from src.models.match_result import MatchResult
            return MatchResult(
                source_id=resume_id, source_type="resume",
                matches=matches, generated_at=datetime.now(JST).isoformat(),
            ).model_dump()
        else:  # hybrid（デフォルト）
            return _run_hybrid_match(resume_id, matcher.resume_repo, matcher.job_repo, "resume")
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/match/job-to-resumes/{job_id}")
def match_job_to_resumes(job_id: str, mode: str = Query("hybrid", pattern="^(hybrid|keyword|semantic)$")):
    """案件に対して全経歴書をマッチング（REQ-FIX-01: デフォルトHybrid）

    Args:
        job_id: 案件ID
        mode: マッチング方式（hybrid / keyword / semantic、デフォルト hybrid）
    """
    try:
        if mode == "keyword":
            result = matcher.match_job_to_resumes(job_id)
            return result.model_dump()
        elif mode == "semantic":
            from src.matching.semantic_matcher import semantic_match
            job = matcher.job_repo.find_by_id(job_id)
            if job is None:
                raise HTTPException(status_code=404, detail=f"案件ID '{job_id}' が見つかりません")
            resumes = matcher.resume_repo.find_all()
            matches = []
            for resume in resumes:
                sm = semantic_match(resume["id"], job_id)
                matches.append(MatchItemModel(
                    target_id=resume["id"],
                    target_name=resume.get("name", ""),
                    total_score=sm.get("score", 0) / 100.0,
                    mode="semantic",
                    explanation=sm.get("explanation", ""),
                ))
            matches.sort(key=lambda m: m.total_score, reverse=True)
            from datetime import datetime, timezone, timedelta
            JST = timezone(timedelta(hours=9))
            from src.models.match_result import MatchResult
            return MatchResult(
                source_id=job_id, source_type="job",
                matches=matches, generated_at=datetime.now(JST).isoformat(),
            ).model_dump()
        else:  # hybrid（デフォルト）
            return _run_hybrid_match(job_id, matcher.job_repo, matcher.resume_repo, "job")
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/match/status")
def match_status():
    """マッチングシステムの状態を返す"""
    from src.repository.json_resume_repo import JsonResumeRepository
    from src.repository.json_job_repo import JsonJobRepository
    from config import RESUMES_FILE, JOBS_FILE

    resume_repo = JsonResumeRepository(RESUMES_FILE)
    job_repo = JsonJobRepository(JOBS_FILE)

    return {
        "resume_count": resume_repo.count(),
        "job_count": job_repo.count(),
        "semantic_matching_enabled": semantic_available(),
        "weights": {
            "skill_match": 0.40,
            "experience_match": 0.20,
            "location_match": 0.15,
            "industry_match": 0.10,
            "unit_price_match": 0.15,
        },
    }


@router.post("/match/semantic")
def run_semantic_match(request: SemanticMatchRequest):
    """Claude APIを使った意味的マッチング"""
    result = semantic_match(request.resume_id, request.job_id)
    return SemanticMatchResponse(**result)



# --- ハイブリッド（10軸統合）マッチングエンドポイント（REQ-06） ---

@router.post("/match/hybrid/resume-to-jobs/{resume_id}")
def match_hybrid_resume_to_jobs(resume_id: str):
    """経歴書に対して全案件を10軸ハイブリッドマッチング"""
    try:
        resume = matcher.resume_repo.find_by_id(resume_id)
        if resume is None:
            raise HTTPException(status_code=404, detail=f"経歴書ID '{resume_id}' が見つかりません")

        jobs = matcher.job_repo.find_all()
        matches = []

        for job in jobs:
            result = compute_hybrid_score(resume, job)
            matches.append(MatchItemModel(
                target_id=job["id"],
                target_name=job.get("title", ""),
                target_company=job.get("company", ""),
                total_score=result["total_score"],
                mode=result["mode"],
                degraded=result["degraded"],
                weights=result.get("weights", {}),
                hybrid_breakdown=HybridBreakdown(**result["breakdown"]),
                matched_skills=result["matched_skills"],
                missing_required_skills=result["missing_required_skills"],
                missing_preferred_skills=result["missing_preferred_skills"],
                rag_sources=result.get("rag_sources", []),
                rag_corrections=result.get("rag_corrections", []),
                explanation=result["explanation"],
            ))

        matches.sort(key=lambda m: m.total_score, reverse=True)

        from datetime import datetime, timezone, timedelta
        JST = timezone(timedelta(hours=9))
        from src.models.match_result import MatchResult
        return MatchResult(
            source_id=resume_id,
            source_type="resume",
            matches=matches,
            generated_at=datetime.now(JST).isoformat(),
        ).model_dump()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match/hybrid/job-to-resumes/{job_id}")
def match_hybrid_job_to_resumes(job_id: str):
    """案件に対して全経歴書を10軸ハイブリッドマッチング"""
    try:
        job = matcher.job_repo.find_by_id(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"案件ID '{job_id}' が見つかりません")

        resumes = matcher.resume_repo.find_all()
        matches = []

        for resume in resumes:
            result = compute_hybrid_score(resume, job)
            matches.append(MatchItemModel(
                target_id=resume["id"],
                target_name=resume.get("name", ""),
                target_company="",
                total_score=result["total_score"],
                mode=result["mode"],
                degraded=result["degraded"],
                weights=result.get("weights", {}),
                hybrid_breakdown=HybridBreakdown(**result["breakdown"]),
                matched_skills=result["matched_skills"],
                missing_required_skills=result["missing_required_skills"],
                missing_preferred_skills=result["missing_preferred_skills"],
                rag_sources=result.get("rag_sources", []),
                rag_corrections=result.get("rag_corrections", []),
                explanation=result["explanation"],
            ))

        matches.sort(key=lambda m: m.total_score, reverse=True)

        from datetime import datetime, timezone, timedelta
        JST = timezone(timedelta(hours=9))
        from src.models.match_result import MatchResult
        return MatchResult(
            source_id=job_id,
            source_type="job",
            matches=matches,
            generated_at=datetime.now(JST).isoformat(),
        ).model_dump()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/match/hybrid/status")
def hybrid_match_status():
    """ハイブリッドマッチングの状態を返す"""
    from src.utils.vector_utils import is_available as embedding_available
    try:
        from config import HYBRID_WEIGHTS
        weights = HYBRID_WEIGHTS
    except (ImportError, AttributeError):
        weights = {}

    return {
        "hybrid_matching_enabled": True,
        "degraded_mode": not embedding_available(),
        "weights": weights,
    }
