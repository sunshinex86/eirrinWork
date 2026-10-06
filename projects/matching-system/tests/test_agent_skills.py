"""AIエージェントスキルのテスト"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.skills.matching_skills import (
    analyze_skill_gap,
    get_industry_context,
    suggest_skill_improvements,
    rank_matches_with_reason,
    validate_skill_consistency,
)


class TestAnalyzeSkillGap:
    """スキルギャップ分析のテスト"""

    def test_full_match(self):
        """全スキル一致"""
        result = analyze_skill_gap(["Python", "Django"], ["Python", "Django"])
        assert result["match_rate"] == 100.0
        assert result["gap_severity"] == "low"
        assert len(result["matched_skills"]) == 2
        assert result["missing_skills"] == []

    def test_partial_match(self):
        """一部スキル不足"""
        result = analyze_skill_gap(["Python"], ["Python", "Django", "Docker"])
        assert 0 < result["match_rate"] < 100
        assert len(result["missing_skills"]) == 2

    def test_no_match(self):
        """スキル不一致"""
        result = analyze_skill_gap(["Ruby"], ["Python", "Django"])
        assert result["match_rate"] == 0.0
        assert result["gap_severity"] == "high"

    def test_empty_required(self):
        """必要なスキルが空"""
        result = analyze_skill_gap(["Python"], [])
        assert result["match_rate"] == 100.0

    def test_empty_resume(self):
        """経歴書にスキルがない"""
        result = analyze_skill_gap([], ["Python"])
        assert result["match_rate"] == 0.0

    def test_synonym_handling(self):
        """シノニム解決（JS = JavaScript）"""
        result = analyze_skill_gap(["JS"], ["JavaScript"])
        assert result["match_rate"] == 100.0


class TestGetIndustryContext:
    """業界コンテキスト取得のテスト"""

    def test_known_industry(self):
        """既知の業界名でコンテキスト取得"""
        result = get_industry_context("IT")
        assert result["industry"] == "IT"
        assert "related_industries" in result

    def test_unknown_industry(self):
        """未知の業界名でもエラーにならない"""
        result = get_industry_context("unknown_industry_xyz")
        assert result["industry"] == "unknown_industry_xyz"
        assert isinstance(result["found_knowledge"], list)


class TestSuggestSkillImprovements:
    """スキル改善提案のテスト"""

    def test_known_skill_suggestion(self):
        """辞書にあるスキルの改善提案"""
        suggestions = suggest_skill_improvements(["Python"])
        assert len(suggestions) == 1
        assert suggestions[0]["found_in_dictionary"] is True

    def test_unknown_skill_suggestion(self):
        """辞書にないスキルの改善提案"""
        suggestions = suggest_skill_improvements(["NonExistentSkill"])
        assert len(suggestions) == 1
        assert suggestions[0]["found_in_dictionary"] is False

    def test_multiple_skills(self):
        """複数スキルの改善提案"""
        suggestions = suggest_skill_improvements(["Python", "Django", "UnknownSkill"])
        assert len(suggestions) == 3

    def test_skill_path(self):
        """スキルパスが取得できること"""
        suggestions = suggest_skill_improvements(["Django"])
        if suggestions[0]["skill_path"]:
            assert "Python" in suggestions[0]["skill_path"] or "Django" in suggestions[0]["skill_path"]


class TestRankMatchesWithReason:
    """マッチランキングのテスト"""

    def test_excellent_match(self):
        """高スコアマッチ"""
        matches = [{"total_score": 0.85, "target_name": "Candidate A"}]
        ranked = rank_matches_with_reason(matches)
        assert ranked[0]["level"] == "excellent"
        assert ranked[0]["rank"] == 1

    def test_good_match(self):
        """中スコアマッチ"""
        matches = [{"total_score": 0.65, "target_name": "Candidate B"}]
        ranked = rank_matches_with_reason(matches)
        assert ranked[0]["level"] == "good"

    def test_fair_match(self):
        """やや低スコアマッチ"""
        matches = [{"total_score": 0.45, "target_name": "Candidate C"}]
        ranked = rank_matches_with_reason(matches)
        assert ranked[0]["level"] == "fair"

    def test_poor_match(self):
        """低スコアマッチ"""
        matches = [{"total_score": 0.25, "target_name": "Candidate D"}]
        ranked = rank_matches_with_reason(matches)
        assert ranked[0]["level"] == "poor"

    def test_multiple_matches(self):
        """複数マッチのランキング"""
        matches = [
            {"total_score": 0.9, "target_name": "A"},
            {"total_score": 0.7, "target_name": "B"},
            {"total_score": 0.5, "target_name": "C"},
        ]
        ranked = rank_matches_with_reason(matches)
        assert len(ranked) == 3
        assert ranked[0]["rank"] == 1
        assert ranked[1]["rank"] == 2
        assert ranked[2]["rank"] == 3

    def test_unsorted_input(self):
        """未ソート入力でもrankがスコア順になる"""
        matches = [
            {"total_score": 0.5, "target_name": "C"},
            {"total_score": 0.9, "target_name": "A"},
            {"total_score": 0.7, "target_name": "B"},
        ]
        ranked = rank_matches_with_reason(matches)
        # 降順ソートされている
        names = [r["target"] for r in ranked]
        assert names == ["A", "B", "C"], f"降順ソートされていません: {names}"
        # rankは連番
        assert [r["rank"] for r in ranked] == [1, 2, 3]

    def test_same_score_stable_sort(self):
        """同点スコアは入力順維持"""
        matches = [
            {"total_score": 0.7, "target_name": "B1"},
            {"total_score": 0.9, "target_name": "A"},
            {"total_score": 0.7, "target_name": "B2"},
        ]
        ranked = rank_matches_with_reason(matches)
        # 同点0.7は入力順（B1→B2）
        b_items = [(r["rank"], r["target"]) for r in ranked if r["target"].startswith("B")]
        assert b_items[0][1] == "B1", f"B1が先であるべき: {b_items}"
        assert b_items[1][1] == "B2", f"B2が次であるべき: {b_items}"

    def test_validate_detailed_structure(self):
        """validate_skill_consistencyが構造化結果を返す"""
        # バリデーション関数がerrors/warningsキーを持つdictを返す
        result = validate_skill_consistency()
        assert isinstance(result, dict)
        assert "valid" in result
        assert "errors" in result
        assert "warnings" in result
        assert isinstance(result["errors"], list)
        assert isinstance(result["warnings"], list)
