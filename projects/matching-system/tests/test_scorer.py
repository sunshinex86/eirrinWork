"""マッチングスコアラーのテスト"""
import pytest
from src.matching.scorer import (
    _compute_skill_score,
    _compute_experience_score,
    _compute_location_score,
    _compute_industry_score,
    _compute_unit_price_score,
    score_resume_against_job,
)


class TestSkillScore:
    """スキルスコア計算のテスト"""

    def test_perfect_match(self):
        """完全一致: 1.0"""
        resume_skills = {"languages": ["Python", "SQL"], "frameworks": [], "tools": [], "certifications": [], "other": []}
        required = {"languages": ["Python"], "frameworks": [], "tools": [], "certifications": [], "other": []}
        preferred = {"languages": [], "frameworks": [], "tools": [], "certifications": [], "other": []}
        score, matched, missing_req, missing_pref = _compute_skill_score(resume_skills, required, preferred)
        assert score == 1.0
        assert "Python" in matched

    def test_perfect_with_preferred(self):
        """必須＋歓迎すべて一致: 1.0"""
        resume_skills = {"languages": ["Python", "SQL", "Go"], "frameworks": [], "tools": [], "certifications": [], "other": []}
        required = {"languages": ["Python"], "frameworks": [], "tools": [], "certifications": [], "other": []}
        preferred = {"languages": ["Go"], "frameworks": [], "tools": [], "certifications": [], "other": []}
        score, matched, missing_req, missing_pref = _compute_skill_score(resume_skills, required, preferred)
        assert score == 1.0

    def test_missing_required_caps_at_0_6(self):
        """必須スキル不足で 0.6 キャップ"""
        resume_skills = {"languages": ["Python"], "frameworks": [], "tools": [], "certifications": [], "other": []}
        required = {"languages": ["Python", "SQL"], "frameworks": [], "tools": [], "certifications": [], "other": []}
        preferred = {"languages": [], "frameworks": [], "tools": [], "certifications": [], "other": []}
        score, matched, missing_req, missing_pref = _compute_skill_score(resume_skills, required, preferred)
        # required: Python(matched)*2 + SQL(missing)*0 = 2, max=4 → 0.5 → capped at 0.6 → but raw=0.5 < 0.6
        assert score == 0.5
        assert "SQL" in missing_req

    def test_missing_required_with_preferred_match(self):
        """必須スキル不足だが歓迎スキルはあり: raw > 0.6 → capped at 0.6"""
        resume_skills = {"languages": ["Python", "Go"], "frameworks": [], "tools": [], "certifications": [], "other": []}
        required = {"languages": ["Python", "SQL"], "frameworks": [], "tools": [], "certifications": [], "other": []}
        preferred = {"languages": ["Go"], "frameworks": [], "tools": [], "certifications": [], "other": []}
        score, matched, missing_req, missing_pref = _compute_skill_score(resume_skills, required, preferred)
        # required: Python*2=2, max_r=4. preferred: Go*1=1, max_p=1. total_max=5, achieved=3 → 0.6 → capped
        assert score == 0.6
        assert "SQL" in missing_req
        assert "Go" in matched

    def test_no_skills_required(self):
        """必須スキル・歓迎スキルが空の場合は 1.0"""
        empty = {"languages": [], "frameworks": [], "tools": [], "certifications": [], "other": []}
        resume_skills = {"languages": ["Python"], "frameworks": [], "tools": [], "certifications": [], "other": []}
        score, matched, missing_req, missing_pref = _compute_skill_score(resume_skills, empty, empty)
        assert score == 1.0

    def test_synonym_matching(self):
        """シノニム経由のスキル一致"""
        resume_skills = {"languages": ["JS", "TS"], "frameworks": [], "tools": [], "certifications": [], "other": []}
        required = {"languages": ["JavaScript"], "frameworks": [], "tools": [], "certifications": [], "other": []}
        preferred = {"languages": ["TypeScript"], "frameworks": [], "tools": [], "certifications": [], "other": []}
        score, matched, missing_req, missing_pref = _compute_skill_score(resume_skills, required, preferred)
        assert score == 1.0


class TestExperienceScore:
    """経験年数スコア計算のテスト"""

    def test_sufficient_experience(self):
        """十分な経験: 1.0"""
        assert _compute_experience_score(12, 5) == 1.0
        assert _compute_experience_score(5, 5) == 1.0

    def test_partial_experience_70_percent_and_above(self):
        """70%以上: 比例"""
        score = _compute_experience_score(7, 10)
        assert score == 0.7

    def test_partial_experience_below_70_percent(self):
        """70%未満: 半減"""
        score = _compute_experience_score(6, 10)
        assert score == 0.3  # 0.6 * 0.5

    def test_zero_required_years(self):
        """必要年数0の場合は1.0"""
        assert _compute_experience_score(5, 0) == 1.0


class TestLocationScore:
    """勤務地スコア計算のテスト"""

    def test_exact_match(self):
        """完全一致: 1.0"""
        assert _compute_location_score("東京都港区", [], "東京都渋谷区", "") == 1.0

    def test_desired_location_match(self):
        """希望勤務地リストに含まれる: 1.0"""
        assert _compute_location_score("大阪府", ["東京都23区内", "大阪府"], "大阪府大阪市", "") == 1.0

    def test_remote_match(self):
        """リモート対応: 1.0"""
        assert _compute_location_score(
            "北海道", ["リモート可"], "東京都渋谷区", "フルリモート可"
        ) == 1.0

    def test_remote_from_job_side(self):
        """求人がリモート可で候補者もリモート希望"""
        assert _compute_location_score(
            "北海道", ["リモート可"], "東京都渋谷区", "週2回リモート可"
        ) == 1.0

    def test_no_match(self):
        """不一致: 0.0"""
        assert _compute_location_score("東京都港区", [], "大阪府大阪市", "") == 0.0

    def test_different_prefecture_no_remote(self):
        """異なる都道府県でリモートなし: 0.0"""
        assert _compute_location_score("東京都", ["東京都"], "大阪府", "") == 0.0


class TestIndustryScore:
    """業界スコア計算のテスト"""

    def test_exact_match(self):
        assert _compute_industry_score(["IT・通信", "IT・通信"], "IT・通信") == 1.0

    def test_latest_industry_match(self):
        """直近業界のみ一致: 1.0"""
        assert _compute_industry_score(["金融", "IT・通信"], "IT・通信") == 1.0

    def test_group_match(self):
        """同じ業界グループ: 0.5"""
        assert _compute_industry_score(["ソフトウェア"], "インターネット") == 0.5

    def test_no_match(self):
        assert _compute_industry_score(["IT・通信"], "製造") == 0.0

    def test_empty(self):
        assert _compute_industry_score([], "IT・通信") == 0.0
        assert _compute_industry_score(["IT・通信"], "") == 0.0


class TestUnitPriceScore:
    """単価スコア計算のテスト"""

    def test_full_overlap(self):
        """完全に包含: 1.0"""
        assert _compute_unit_price_score(500, 800, 500, 800) == 1.0

    def test_partial_overlap(self):
        """部分的オーバーラップ"""
        score = _compute_unit_price_score(500, 800, 600, 900)
        # overlap: 600-800 = 200, resume_range: 300 → 200/300 = 0.6667
        assert 0.6 < score < 0.7

    def test_no_overlap(self):
        """オーバーラップなし: 0.0"""
        assert _compute_unit_price_score(500, 600, 700, 800) == 0.0

    def test_unset_unit_price(self):
        """未設定の場合はペナルティなし"""
        assert _compute_unit_price_score(0, 0, 500, 800) == 1.0
        assert _compute_unit_price_score(500, 800, 0, 0) == 1.0

    def test_fixed_value(self):
        """一方が固定値"""
        assert _compute_unit_price_score(500, 500, 500, 800) == 0.5


class TestScoreResumeAgainstJob:
    """経歴書×案件の統合スコアリングテスト"""

    def test_high_match(self, sample_resume, sample_job):
        """高スコアのマッチング"""
        result = score_resume_against_job(sample_resume, sample_job)
        assert result["total_score"] > 0.7
        assert "breakdown" in result
        assert "explanation" in result
        assert len(result["matched_skills"]) > 0

    def test_low_match(self, sample_resume_2, sample_job_2):
        """低スコアのマッチング（業界違い・遠隔地・スキル不足）"""
        result = score_resume_against_job(sample_resume_2, sample_job_2)
        assert result["total_score"] < 0.5

    def test_result_structure(self, sample_resume, sample_job):
        """戻り値の構造が正しいこと"""
        result = score_resume_against_job(sample_resume, sample_job)
        expected_keys = {
            "total_score", "breakdown", "matched_skills",
            "missing_required_skills", "missing_preferred_skills", "explanation",
        }
        assert set(result.keys()) == expected_keys
        breakdown_keys = {"skill_match", "experience_match", "location_match", "industry_match", "unit_price_match"}
        assert set(result["breakdown"].keys()) == breakdown_keys

    def test_missing_required_skill_penalty(self, sample_resume, sample_job):
        """必須スキル不足が正しく検出されること"""
        # 田中太郎は "REST API設計経験" を持っていない
        result = score_resume_against_job(sample_resume, sample_job)
        assert "REST API設計経験" in result["missing_required_skills"]

    def test_scores_are_normalized(self, sample_resume, sample_job):
        """全スコアが0-1の範囲内であること"""
        result = score_resume_against_job(sample_resume, sample_job)
        assert 0.0 <= result["total_score"] <= 1.0
        for key, val in result["breakdown"].items():
            assert 0.0 <= val <= 1.0, f"{key} = {val} is not in [0, 1]"

    def test_empty_data(self):
        """空データでもエラーにならないこと"""
        empty_resume = {
            "id": "r-empty", "name": "空", "age": 30,
            "skills": {}, "work_history": [], "desired_locations": [],
            "years_of_experience": 0, "desired_unit_price_min": 0, "desired_unit_price_max": 0,
            "location": "",
        }
        empty_job = {
            "id": "j-empty", "title": "空", "company": "空",
            "required_skills": {}, "preferred_skills": {},
            "required_experience_years": 0, "unit_price_min": 0, "unit_price_max": 0,
            "location": "", "remote_policy": "", "industry": "",
        }
        result = score_resume_against_job(empty_resume, empty_job)
        assert 0.0 <= result["total_score"] <= 1.0
