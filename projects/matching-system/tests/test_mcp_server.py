"""MCP Server のテスト（fastmcp SDK 準拠）"""
import sys
import json
from pathlib import Path
from unittest.mock import patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server import (
    search_skills, get_skill_context,
    search_knowledge, analyze_skill_gap,
    recommendation_reason, optimize_jd,
)


class TestMCPSearchSkills:
    """search_skills ツールのテスト"""

    def test_search_by_name(self):
        """スキル名で検索"""
        from mcp_server import SearchSkillsInput
        params = SearchSkillsInput(query="Python")
        result = search_skills(params)
        data = json.loads(result)
        assert "results" in data
        assert any(r.get("id") == "python" for r in data["results"])

    def test_search_by_alias(self):
        """エイリアスで検索"""
        from mcp_server import SearchSkillsInput
        params = SearchSkillsInput(query="py")
        result = search_skills(params)
        data = json.loads(result)
        assert len(data["results"]) > 0

    def test_search_with_category(self):
        """カテゴリフィルタ"""
        from mcp_server import SearchSkillsInput
        params = SearchSkillsInput(query="Python", category="programming_language")
        result = search_skills(params)
        data = json.loads(result)
        assert len(data["results"]) > 0


class TestMCPSkillContext:
    """get_skill_context ツールのテスト"""

    def test_known_skill(self):
        """既知スキルのコンテキスト"""
        from mcp_server import SkillContextInput
        params = SkillContextInput(skill_name="Python")
        result = get_skill_context(params)
        data = json.loads(result)
        assert "skill" in data
        assert data["skill"]["id"] == "python"

    def test_unknown_skill(self):
        """未知スキル"""
        from mcp_server import SkillContextInput
        params = SkillContextInput(skill_name="NonExistentSkill")
        result = get_skill_context(params)
        data = json.loads(result)
        assert data["skill"] is None


class TestMCPSearchKnowledge:
    """search_knowledge ツールのテスト"""

    def test_search(self):
        """ナレッジ検索"""
        from mcp_server import KnowledgeSearchInput
        params = KnowledgeSearchInput(query="IT")
        result = search_knowledge(params)
        data = json.loads(result)
        assert isinstance(data, list)


class TestMCAnalyzeSkillGap:
    """analyze_skill_gap ツールのテスト"""

    @patch("src.repository.json_resume_repo.JsonResumeRepository.find_by_id")
    @patch("src.repository.json_job_repo.JsonJobRepository.find_by_id")
    def test_gap_analysis(self, mock_job, mock_resume):
        """スキルギャップ分析"""
        mock_resume.return_value = {
            "structured_skills": [
                {"skill_id": "python", "level": 4, "years": 5, "last_used_year": 2026}
            ]
        }
        mock_job.return_value = {
            "structured_required_skills": [
                {"skill_id": "python", "required_level": 3, "required_years": 3, "required": True},
                {"skill_id": "java", "required_level": 3, "required_years": 3, "required": True},
            ]
        }
        from mcp_server import SkillGapInput
        params = SkillGapInput(resume_id="r1", job_id="j1")
        result = analyze_skill_gap(params)
        data = json.loads(result)
        assert "matched_skills" in data
        assert "missing_skills" in data
        assert "match_rate" in data
        assert "java" in data["missing_skills"]


class TestRecommendationReasoningMCP:
    """推薦理由分解 / JD最適化のMCPツールのテスト"""

    def test_recommendation_reason_tool(self):
        from mcp_server import RecommendationReasonInput
        params = RecommendationReasonInput(resume_id="resume-001", job_id="job-001")
        result = json.loads(recommendation_reason(params))
        assert "skill_matches" in result
        assert "gap_analysis" in result

    def test_jd_optimization_tool(self):
        from mcp_server import JdOptimizationInput
        params = JdOptimizationInput(raw_jd="Python, Django, SQL, 5年経験, 800万円")
        result = json.loads(optimize_jd(params))
        assert "optimized_jd" in result
        assert "normalized_skills" in result
        assert "budget_assessment" in result


class TestMCPInputValidation:
    """入力バリデーションのテスト"""

    def test_invalid_method_rejected(self):
        """無効なmethodはバリデーションエラー"""
        from pydantic import ValidationError
        from mcp_server import MatchingScoreInput
        with pytest.raises(ValidationError):
            MatchingScoreInput(resume_id="r1", job_id="j1", method="invalid")

    def test_empty_query_rejected(self):
        """空クエリはエラー"""
        from pydantic import ValidationError
        from mcp_server import SearchSkillsInput
        with pytest.raises(ValidationError):
            SearchSkillsInput(query="")
