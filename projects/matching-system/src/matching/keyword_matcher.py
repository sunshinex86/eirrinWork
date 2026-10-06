"""キーワードベースマッチングエンジン

経歴書と案件の双方向マッチングを実行するファサード。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import datetime, timezone, timedelta

import config
from src.repository.json_resume_repo import JsonResumeRepository
from src.repository.json_job_repo import JsonJobRepository
from src.matching.scorer import score_resume_against_job
from src.models.match_result import MatchResult, MatchItem, MatchBreakdown

JST = timezone(timedelta(hours=9))


class KeywordMatcher:
    """キーワードベースの双方向マッチングを実行する"""

    def __init__(self):
        self.resume_repo = JsonResumeRepository(config.RESUMES_FILE)
        self.job_repo = JsonJobRepository(config.JOBS_FILE)

    def match_resume_to_jobs(self, resume_id: str) -> MatchResult:
        """1件の経歴書を全案件に対してマッチング"""
        resume = self.resume_repo.find_by_id(resume_id)
        if resume is None:
            raise ValueError(f"経歴書ID '{resume_id}' が見つかりません")

        jobs = self.job_repo.find_all()
        matches = []

        for job in jobs:
            result = score_resume_against_job(resume, job)
            matches.append(MatchItem(
                target_id=job["id"],
                target_name=job.get("title", ""),
                target_company=job.get("company", ""),
                total_score=result["total_score"],
                breakdown=MatchBreakdown(**result["breakdown"]),
                matched_skills=result["matched_skills"],
                missing_required_skills=result["missing_required_skills"],
                missing_preferred_skills=result["missing_preferred_skills"],
                explanation=result["explanation"],
            ))

        # スコア降順でソート
        matches.sort(key=lambda m: m.total_score, reverse=True)

        return MatchResult(
            source_id=resume_id,
            source_type="resume",
            matches=matches,
            generated_at=datetime.now(JST).isoformat(),
        )

    def match_job_to_resumes(self, job_id: str) -> MatchResult:
        """1件の案件を全経歴書に対してマッチング"""
        job = self.job_repo.find_by_id(job_id)
        if job is None:
            raise ValueError(f"案件ID '{job_id}' が見つかりません")

        resumes = self.resume_repo.find_all()
        matches = []

        for resume in resumes:
            result = score_resume_against_job(resume, job)
            matches.append(MatchItem(
                target_id=resume["id"],
                target_name=resume.get("name", ""),
                target_company="",  # 経歴書に現在の会社名
                total_score=result["total_score"],
                breakdown=MatchBreakdown(**result["breakdown"]),
                matched_skills=result["matched_skills"],
                missing_required_skills=result["missing_required_skills"],
                missing_preferred_skills=result["missing_preferred_skills"],
                explanation=result["explanation"],
            ))

        matches.sort(key=lambda m: m.total_score, reverse=True)

        return MatchResult(
            source_id=job_id,
            source_type="job",
            matches=matches,
            generated_at=datetime.now(JST).isoformat(),
        )

    def match_all(self) -> list[MatchResult]:
        """全経歴書を全案件に対してマッチング（一括処理）"""
        results = []
        resumes = self.resume_repo.find_all()
        for resume in resumes:
            results.append(self.match_resume_to_jobs(resume["id"]))
        return results
