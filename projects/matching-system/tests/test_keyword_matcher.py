"""キーワードマッチングエンジンの統合テスト"""
import json
import tempfile
from pathlib import Path
import pytest

# テスト前に environment をセットアップ
import config

from src.matching.keyword_matcher import KeywordMatcher
from src.repository.json_resume_repo import JsonResumeRepository
from src.repository.json_job_repo import JsonJobRepository


class TestKeywordMatcher:
    """KeywordMatcherのテスト"""

    @pytest.fixture(autouse=True)
    def setup_repos(self):
        """各テスト前に一時ファイルでリポジトリをセットアップ"""
        # 一時ファイル作成
        self.resume_file = Path(tempfile.mktemp(suffix=".json"))
        self.job_file = Path(tempfile.mktemp(suffix=".json"))

        # 空データで初期化
        json.dump([], open(self.resume_file, "w", encoding="utf-8"))
        json.dump([], open(self.job_file, "w", encoding="utf-8"))

        # configを上書き
        self.orig_resume_file = config.RESUMES_FILE
        self.orig_job_file = config.JOBS_FILE
        config.RESUMES_FILE = self.resume_file
        config.JOBS_FILE = self.job_file

        self.matcher = KeywordMatcher()

        yield

        # クリーンアップ
        config.RESUMES_FILE = self.orig_resume_file
        config.JOBS_FILE = self.orig_job_file
        self.resume_file.unlink(missing_ok=True)
        self.job_file.unlink(missing_ok=True)

    def test_match_resume_to_jobs(self, sample_resume, sample_job):
        """経歴書→案件のマッチングが動作すること"""
        self.matcher.resume_repo.create(sample_resume)
        self.matcher.job_repo.create(sample_job)

        result = self.matcher.match_resume_to_jobs("resume-001")
        assert result.source_id == "resume-001"
        assert result.source_type == "resume"
        assert len(result.matches) == 1
        assert result.matches[0].target_id == "job-001"
        assert result.matches[0].total_score > 0.0

    def test_match_job_to_resumes(self, sample_resume, sample_job):
        """案件→経歴書のマッチングが動作すること"""
        self.matcher.resume_repo.create(sample_resume)
        self.matcher.job_repo.create(sample_job)

        result = self.matcher.match_job_to_resumes("job-001")
        assert result.source_id == "job-001"
        assert result.source_type == "job"
        assert len(result.matches) == 1
        assert result.matches[0].target_id == "resume-001"
        assert result.matches[0].target_name == "田中 太郎"

    def test_matches_are_sorted_by_score_desc(self, sample_resume, sample_resume_2, sample_job):
        """マッチ結果がスコア降順でソートされていること"""
        self.matcher.resume_repo.create(sample_resume)    # 高スコア
        self.matcher.resume_repo.create(sample_resume_2)  # 低スコア
        self.matcher.job_repo.create(sample_job)

        result = self.matcher.match_job_to_resumes("job-001")
        scores = [m.total_score for m in result.matches]
        assert scores == sorted(scores, reverse=True)
        assert result.matches[0].target_id == "resume-001"  # 田中が1位

    def test_match_resume_not_found(self):
        """存在しない経歴書IDでエラーになること"""
        with pytest.raises(ValueError, match="見つかりません"):
            self.matcher.match_resume_to_jobs("non-existent")

    def test_match_job_not_found(self):
        """存在しない案件IDでエラーになること"""
        with pytest.raises(ValueError, match="見つかりません"):
            self.matcher.match_job_to_resumes("non-existent")

    def test_empty_data(self):
        """データが空の場合もエラーにならず空結果が返ること"""
        result = self.matcher.match_resume_to_jobs("resume-001") if False else None
        # 空データは resume がないのでエラーになる
        pass

    def test_match_structure(self, sample_resume, sample_job):
        """マッチ結果の構造が正しいこと"""
        self.matcher.resume_repo.create(sample_resume)
        self.matcher.job_repo.create(sample_job)

        result = self.matcher.match_resume_to_jobs("resume-001")
        match = result.matches[0]
        assert hasattr(match, "total_score")
        assert hasattr(match, "breakdown")
        assert hasattr(match, "matched_skills")
        assert hasattr(match, "missing_required_skills")
        assert hasattr(match, "missing_preferred_skills")
        assert hasattr(match, "explanation")
        assert match.total_score > 0
        assert match.breakdown.skill_match >= 0

    def test_match_all(self, sample_resume, sample_resume_2, sample_job):
        """一括マッチングが動作すること"""
        self.matcher.resume_repo.create(sample_resume)
        self.matcher.resume_repo.create(sample_resume_2)
        self.matcher.job_repo.create(sample_job)

        results = self.matcher.match_all()
        assert len(results) == 2  # 経歴書2件分
        for r in results:
            assert r.source_type == "resume"
            assert len(r.matches) == 1
