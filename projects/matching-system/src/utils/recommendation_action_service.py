"""自動マッチング＋アクション提案サービス

候補者と案件の自動マッチングを行い、以下を返す:
- 推薦順位
- 連絡優先度
- 自動コミュニケーション生成
"""
from __future__ import annotations

from typing import Any

import config
from src.matching.embedding_matcher import compute_hybrid_score
from src.repository.json_job_repo import JsonJobRepository
from src.repository.json_resume_repo import JsonResumeRepository
from src.utils.skill_dictionary import get_skill_by_id


def build_recommendation_actions(resume_id: str, top_n: int = 5) -> dict[str, Any]:
    """候補者に対する自動推薦順位・連絡優先度・自動送信文を生成する。"""
    resume_repo = JsonResumeRepository(config.RESUMES_FILE)
    job_repo = JsonJobRepository(config.JOBS_FILE)

    resume = resume_repo.find_by_id(resume_id)
    if resume is None:
        raise ValueError(f"resume_id '{resume_id}' が見つかりません")

    jobs = job_repo.find_all()
    rankings = []
    for job in jobs:
        result = compute_hybrid_score(resume, job)
        matched_ids = set(result.get("matched_skills", []))
        missing_required = result.get("missing_required_skills", [])
        total_score = float(result.get("total_score", 0.0))
        priority = _priority_from_score(total_score)

        communication = _build_communication_text(
            resume_name=resume.get("name", "候補者"),
            job_title=job.get("title", "案件"),
            matched_skills=sorted(matched_ids),
            missing_required=missing_required,
            total_score=total_score,
        )

        rankings.append({
            "job_id": job.get("id"),
            "job_title": job.get("title", ""),
            "company": job.get("company", ""),
            "score": round(total_score, 3),
            "priority": priority,
            "matched_skills": sorted(matched_ids),
            "missing_required_skills": missing_required,
            "recommended_action": _recommended_action(priority),
            "communication_text": communication,
        })

    rankings.sort(key=lambda item: item["score"], reverse=True)
    return {
        "resume_id": resume_id,
        "recommendations": rankings[: max(1, top_n)],
        "contact_priority_order": [item["job_id"] for item in rankings[: max(1, top_n)]],
    }


def _priority_from_score(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def _recommended_action(priority: str) -> str:
    if priority == "high":
        return "今すぐ連絡・面談設定"
    if priority == "medium":
        return "詳細確認後に連絡"
    return "保留または候補拡大"


def _build_communication_text(resume_name: str, job_title: str, matched_skills: list[str], missing_required: list[str], total_score: float) -> str:
    matched_text = ", ".join(matched_skills[:3]) if matched_skills else "関連スキル"
    missing_text = ", ".join(missing_required[:3]) if missing_required else "補完可能な要素"
    return (
        f"{resume_name}さんの{job_title}への推薦度は {round(total_score * 100, 1)} 点です。"
        f"既に一致している主要スキルは {matched_text} です。"
        f"一方、{missing_text} の補強が必要なため、面談前に補足確認を推奨します。"
    )
