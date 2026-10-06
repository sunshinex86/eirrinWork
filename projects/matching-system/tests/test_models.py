"""モデルのバリデーションテスト"""
import pytest
from pydantic import ValidationError

from src.models.resume import Resume, Education, WorkHistory, SkillSet, ResumeSkill
from src.models.job import Job, JobSkill
from src.models.match_result import MatchBreakdown, HybridBreakdown, MatchItem, MatchResult, SemanticMatchRequest, SemanticMatchResponse


class TestResumeModel:
    """経歴書モデルのテスト"""

    def test_minimal_resume_creation(self):
        """最低限のフィールドで作成できること"""
        r = Resume(id="r-001", name="田中", age=30)
        assert r.id == "r-001"
        assert r.name == "田中"
        assert r.age == 30
        assert r.skills.languages == []
        assert r.work_history == []

    def test_full_resume_creation(self, sample_resume):
        """全フィールドで正しく作成できること"""
        r = Resume(**sample_resume)
        assert r.id == "resume-001"
        assert r.name == "田中 太郎"
        assert len(r.work_history) == 2
        assert r.skills.languages == ["Python", "Java", "SQL", "TypeScript"]

    def test_missing_required_fields(self):
        """必須フィールド不足でエラーになること"""
        with pytest.raises(ValidationError):
            Resume()  # id, name, age が必須
        with pytest.raises(ValidationError):
            Resume(id="r-001")  # name, age が不足

    def test_get_all_skills(self, sample_resume):
        """全スキルがフラットリストで取得できること"""
        r = Resume(**sample_resume)
        skills = r.get_all_skills()
        assert "Python" in skills
        assert "Django" in skills
        assert "Docker" in skills
        assert "AWS SAA" in skills
        assert "git" in skills
        # languages:4, frameworks:3, tools:4, certifications:2, other:2 = 15
        assert len(skills) == 15

    def test_get_latest_industry(self, sample_resume):
        """直近の業界が取得できること"""
        r = Resume(**sample_resume)
        assert r.get_latest_industry() == "IT・通信"

    def test_get_latest_industry_empty(self):
        """職歴なしの場合は空文字"""
        r = Resume(id="r-001", name="田中", age=30)
        assert r.get_latest_industry() == ""

    def test_default_values(self):
        """デフォルト値が正しく設定されること"""
        r = Resume(id="r-001", name="田中", age=30)
        assert r.email == ""
        assert r.employment_type == "正社員"
        assert r.years_of_experience == 0
        assert r.desired_unit_price_min == 0

    def test_education_model(self):
        """学歴モデルの作成"""
        edu = Education(school="東京大学", graduation_year=2014)
        assert edu.school == "東京大学"
        assert edu.degree == "学士"  # default
        assert edu.department == ""  # default

    def test_work_history_model(self):
        """職歴モデル（end_dateがNone = 現在就業中）"""
        wh = WorkHistory(company="A社", position="エンジニア", start_date="2020-04")
        assert wh.end_date is None
        assert wh.industry == ""

    def test_skill_set_model(self):
        """スキルセットモデル"""
        s = SkillSet(languages=["Python", "Java"])
        assert s.languages == ["Python", "Java"]
        assert s.frameworks == []
        assert s.tools == []

    def test_resume_skill_model(self):
        """属性付きスキルモデル（経歴書側）"""
        rs = ResumeSkill(skill_id="python", level=4, years=5, last_used_year=2026)
        assert rs.skill_id == "python"
        assert rs.level == 4
        assert rs.years == 5
        assert rs.last_used_year == 2026

    def test_resume_skill_default_level(self):
        """属性付きスキルのデフォルトレベル"""
        rs = ResumeSkill(skill_id="java")
        assert rs.level == 1
        assert rs.years == 0

    def test_resume_with_structured_skills(self, sample_resume):
        """経歴書に属性付きスキルを設定"""
        skills = [
            ResumeSkill(skill_id="python", level=4, years=8, last_used_year=2026),
            ResumeSkill(skill_id="java", level=3, years=5, last_used_year=2020),
        ]
        r = Resume(**sample_resume, structured_skills=skills)
        assert len(r.structured_skills) == 2
        assert r.get_skill_id_list() == ["python", "java"]


class TestJobModel:
    """案件モデルのテスト"""

    def test_minimal_job_creation(self):
        """最低限のフィールドで作成できること"""
        j = Job(id="j-001", title="エンジニア", company="A社")
        assert j.id == "j-001"
        assert j.title == "エンジニア"
        assert j.required_skills.languages == []

    def test_full_job_creation(self, sample_job):
        """全フィールドで正しく作成できること"""
        j = Job(**sample_job)
        assert j.id == "job-001"
        assert j.required_skills.languages == ["Python", "SQL"]
        assert j.preferred_skills.languages == ["TypeScript", "Go"]

    def test_missing_required_fields(self):
        """必須フィールド不足でエラーになること"""
        with pytest.raises(ValidationError):
            Job()
        with pytest.raises(ValidationError):
            Job(id="j-001")  # title, company が不足

    def test_get_all_required_skills(self, sample_job):
        """必須スキルがフラットリストで取得できること"""
        j = Job(**sample_job)
        skills = j.get_all_required_skills()
        assert "Python" in skills
        assert "Django" in skills
        assert "REST API設計経験" in skills

    def test_get_all_preferred_skills(self, sample_job):
        """歓迎スキルがフラットリストで取得できること"""
        j = Job(**sample_job)
        skills = j.get_all_preferred_skills()
        assert "TypeScript" in skills
        assert "Kubernetes" in skills

    def test_default_values(self):
        """デフォルト値が正しいこと"""
        j = Job(id="j-001", title="エンジニア", company="A社")
        assert j.employment_type == "正社員"
        assert j.headcount == 1
        assert j.unit_price_min == 0

    def test_job_skill_model(self):
        """属性付きスキルモデル（案件側）"""
        js = JobSkill(skill_id="python", required_level=3, required_years=3)
        assert js.skill_id == "python"
        assert js.required_level == 3
        assert js.required_years == 3

    def test_job_with_structured_skills(self, sample_job):
        """案件に属性付きスキルを設定"""
        req = [
            JobSkill(skill_id="python", required_level=3, required_years=3),
            JobSkill(skill_id="sql", required_level=2, required_years=2),
        ]
        pref = [
            JobSkill(skill_id="react", required_level=2, required_years=1),
        ]
        j = Job(**sample_job, structured_required_skills=req, structured_preferred_skills=pref)
        assert len(j.structured_required_skills) == 2
        assert j.get_required_skill_ids() == ["python", "sql"]
        assert j.get_preferred_skill_ids() == ["react"]

    def test_job_skill_defaults(self):
        """属性付きスキルのデフォルト"""
        js = JobSkill(skill_id="java")
        assert js.required_level == 1
        assert js.required_years == 0


class TestMatchResultModels:
    """マッチ結果モデルのテスト"""

    def test_match_breakdown(self):
        """内訳スコアモデル"""
        mb = MatchBreakdown(
            skill_match=0.8,
            experience_match=0.9,
            location_match=1.0,
            industry_match=0.5,
            unit_price_match=0.7,
        )
        assert mb.skill_match == 0.8
        assert mb.experience_match == 0.9

    def test_hybrid_breakdown(self):
        """10軸統合スコア内訳モデル"""
        hb = HybridBreakdown(
            required_skill_score=0.9,
            preferred_skill_score=0.7,
            skill_depth_score=0.8,
            skill_hierarchy_score=0.75,
            context_score=0.8,
            role_score=0.9,
            embedding_score=0.78,
        )
        assert hb.required_skill_score == 0.9
        assert hb.preferred_skill_score == 0.7
        assert hb.skill_depth_score == 0.8
        assert hb.skill_hierarchy_score == 0.75
        assert hb.context_score == 0.8
        assert hb.role_score == 0.9
        assert hb.embedding_score == 0.78

    def test_hybrid_breakdown_defaults(self):
        """10軸内訳のデフォルト値"""
        hb = HybridBreakdown()
        assert hb.required_skill_score == 0.0
        assert hb.embedding_score == 0.0

    def test_match_item(self):
        """マッチ項目モデル"""
        item = MatchItem(
            target_id="job-001",
            target_name="Pythonエンジニア",
            total_score=0.85,
            matched_skills=["Python", "SQL"],
            missing_required_skills=["Go"],
        )
        assert item.total_score == 0.85
        assert item.target_name == "Pythonエンジニア"

    def test_match_item_with_hybrid(self):
        """10軸統合スコア付きマッチ項目モデル"""
        hb = HybridBreakdown(
            required_skill_score=0.9,
            preferred_skill_score=0.7,
            skill_depth_score=0.8,
            skill_hierarchy_score=0.75,
            context_score=0.8,
            role_score=0.9,
            embedding_score=0.78,
        )
        item = MatchItem(
            target_id="job-001",
            target_name="Pythonエンジニア",
            total_score=0.82,
            mode="hybrid",
            degraded=False,
            hybrid_breakdown=hb,
            matched_skills=["python", "django"],
            missing_required_skills=["go"],
            rag_sources=["industry-it", "role-se"],
            explanation="良いマッチです。",
        )
        assert item.mode == "hybrid"
        assert item.degraded is False
        assert item.hybrid_breakdown is not None
        assert item.hybrid_breakdown.required_skill_score == 0.9
        assert item.rag_sources == ["industry-it", "role-se"]
        assert item.total_score == 0.82

    def test_match_result(self):
        """マッチ結果モデル"""
        result = MatchResult(
            source_id="resume-001",
            source_type="resume",
            matches=[],
            generated_at="2025-01-01T00:00:00",
        )
        assert result.source_type == "resume"
        assert result.matches == []

    def test_semantic_match_request(self):
        """AIマッチリクエストモデル"""
        req = SemanticMatchRequest(resume_id="r-001", job_id="j-001")
        assert req.resume_id == "r-001"

    def test_semantic_match_response_with_error(self):
        """AIマッチレスポンス（エラーあり）"""
        resp = SemanticMatchResponse(
            score=0,
            error="APIキー未設定",
        )
        assert resp.error == "APIキー未設定"
        assert resp.score == 0
