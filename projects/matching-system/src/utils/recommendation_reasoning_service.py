"""推薦理由分解とギャップ分析サービス

候補者の経歴書と案件JDを受け取り、
- スキルマッチの分解
- 業界マッチの分解
- 経験マッチの分解
- ギャップ分析
を構造化で返す。
"""
from __future__ import annotations

from typing import Any

import config
from src.repository.json_job_repo import JsonJobRepository
from src.repository.json_resume_repo import JsonResumeRepository
from src.utils.skill_dictionary import get_skill_by_id


def build_recommendation_reason(resume_id: str, job_id: str) -> dict[str, Any]:
    """候補者と案件の推薦理由を分解して返す."""
    resume_repo = JsonResumeRepository(config.RESUMES_FILE)
    job_repo = JsonJobRepository(config.JOBS_FILE)

    resume = resume_repo.find_by_id(resume_id)
    job = job_repo.find_by_id(job_id)
    if resume is None:
        raise ValueError(f"resume_id '{resume_id}' が見つかりません")
    if job is None:
        raise ValueError(f"job_id '{job_id}' が見つかりません")

    resume_ids = {
        s["skill_id"] if isinstance(s, dict) else s.skill_id
        for s in resume.get("structured_skills", [])
    }
    required_ids = {
        s["skill_id"] if isinstance(s, dict) else s.skill_id
        for s in job.get("structured_required_skills", [])
    }
    preferred_ids = {
        s["skill_id"] if isinstance(s, dict) else s.skill_id
        for s in job.get("structured_preferred_skills", [])
    }

    matched_ids = sorted(resume_ids & required_ids)
    missing_required_ids = sorted(required_ids - resume_ids)
    missing_preferred_ids = sorted(preferred_ids - resume_ids)

    skill_matches = []
    for skill_id in matched_ids:
        skill = get_skill_by_id(skill_id)
        if not skill:
            continue
        skill_matches.append({
            "skill_id": skill_id,
            "canonical_name": skill.get("name", skill_id),
            "match_type": "required",
            "evidence": [f"Resumeに{skill.get('name', skill_id)}を保持"],
        })

    industry_matches = []
    resume_industry = ""
    if resume.get("work_history"):
        resume_industry = resume["work_history"][-1].get("industry", "") if isinstance(resume["work_history"], list) else ""
    if resume_industry and resume_industry == job.get("industry", ""):
        industry_matches.append({
            "industry": job.get("industry", ""),
            "reason": "候補者の直近職歴と案件業界が一致しています。",
        })
    else:
        industry_matches.append({
            "industry": job.get("industry", ""),
            "reason": "業界は近い領域の可能性があります。関連業界コンテキストを補強すると判断しやすくなります。",
        })

    experience_years = int(resume.get("years_of_experience", 0) or 0)
    required_years = int(job.get("required_experience_years", 0) or 0)
    experience_gap = max(required_years - experience_years, 0)
    experience_matches = [
        {
            "resume_years": experience_years,
            "required_years": required_years,
            "status": "match" if experience_gap == 0 else "gap",
            "reason": (
                "経験年数は案件要件に合致しています。"
                if experience_gap == 0
                else f"経験年数に{experience_gap}年の差があります。"
            ),
        }
    ]

    gap_analysis = {
        "missing_required_skills": [
            {
                "skill_id": sid,
                "canonical_name": get_skill_by_id(sid).get("name", sid) if get_skill_by_id(sid) else sid,
            }
            for sid in missing_required_ids
        ],
        "missing_preferred_skills": [
            {
                "skill_id": sid,
                "canonical_name": get_skill_by_id(sid).get("name", sid) if get_skill_by_id(sid) else sid,
            }
            for sid in missing_preferred_ids
        ],
        "experience_gap_years": experience_gap,
        "industry_gap": [] if industry_matches else [job.get("industry", "")],
        "match_rate": round(len(matched_ids) / len(required_ids) * 100, 1) if required_ids else 100.0,
    }

    return {
        "skill_matches": skill_matches,
        "industry_matches": industry_matches,
        "experience_matches": experience_matches,
        "gap_analysis": gap_analysis,
        "recommendation_summary": (
            f"{resume.get('name', '')}は{job.get('title', '')}に対し、"
            f"主要スキル{len(skill_matches)}件が一致し、"
            f"経験年数差は{experience_gap}年です。"
        ),
    }
