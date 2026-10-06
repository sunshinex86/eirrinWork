"""UI表示ロジックの単体テスト（REQ-RE2-06, REQ-RE2-07, REQ-RE3-07）

REQ-RE3-07: 本番コード（display_utils.py）からimportする。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ui.display_utils import (
    format_sample_result_status,
    has_unresolved_warnings,
    get_unresolved_count,
    has_rag_sources,
    get_rag_source_count,
    build_candidate_availability_from_resume,
)


class TestSampleResultStatus:
    """サンプル読込結果の表示ロジックテスト"""

    def test_committed_true_shows_success(self):
        result = {"created": 3, "skipped": 1, "failed": 0, "committed": True}
        msgs = format_sample_result_status(result)
        assert "✅" in msgs[0]
        assert "⏭️" in msgs[1]

    def test_committed_false_no_success_message(self):
        """committed=false かつ failed>0 の場合は成功メッセージを表示しない"""
        result = {"created": 0, "skipped": 0, "failed": 2, "committed": False, "errors": []}
        msgs = format_sample_result_status(result)
        assert "✅" not in msgs[0]
        assert "❌" in msgs[0]
        assert "検証失敗" in msgs[0]

    def test_committed_false_no_failed_returns_info(self):
        """committed=false だが failed=0 の場合は「空です」"""
        result = {"created": 0, "skipped": 0, "failed": 0, "committed": False}
        msgs = format_sample_result_status(result)
        assert "読込結果が空です" in msgs[0]

    def test_empty_result(self):
        result = {"created": 0, "skipped": 0, "failed": 0, "committed": True}
        msgs = format_sample_result_status(result)
        assert "読込結果が空です" in msgs[0]


class TestUnresolvedSkillsDisplay:
    """未解決スキル表示のテスト"""

    def test_has_warnings(self):
        result = {"unresolved_skills": [{"record_id": "r1", "field": "skills.*", "raw_value": "unknown_skill", "reason": "SKILL_NOT_REGISTERED"}]}
        assert has_unresolved_warnings(result) is True
        assert get_unresolved_count(result) == 1

    def test_no_warnings(self):
        result = {"unresolved_skills": []}
        assert has_unresolved_warnings(result) is False
        assert get_unresolved_count(result) == 0

    def test_missing_key(self):
        result = {}
        assert has_unresolved_warnings(result) is False
        assert get_unresolved_count(result) == 0

    def test_multiple_warnings(self):
        result = {"unresolved_skills": [
            {"record_id": "r1", "field": "skills.*", "raw_value": "s1", "reason": "SKILL_NOT_REGISTERED"},
            {"record_id": "r2", "field": "skills.*", "raw_value": "s2", "reason": "SKILL_NOT_REGISTERED"},
        ]}
        assert get_unresolved_count(result) == 2


class TestRagSourcesDisplay:
    """RAG参照情報表示のテスト"""

    def test_has_sources(self):
        match = {"rag_sources": ["doc001", "doc002"]}
        assert has_rag_sources(match) is True
        assert get_rag_source_count(match) == 2

    def test_no_sources(self):
        match = {"rag_sources": []}
        assert has_rag_sources(match) is False

    def test_empty_list(self):
        match = {}
        assert has_rag_sources(match) is False
        assert get_rag_source_count(match) == 0

    def test_single_source(self):
        match = {"rag_sources": ["doc001"]}
        assert has_rag_sources(match) is True
        assert get_rag_source_count(match) == 1


class TestCandidateAvailabilityInference:
    """resume から schedule 用 availability を推定するテスト"""

    def test_explicit_availability_is_used(self):
        resume = {
            "availability": {
                "slots": [
                    {"start": "2026-07-23T09:00:00", "end": "2026-07-23T12:00:00"}
                ]
            }
        }
        result = build_candidate_availability_from_resume(resume)
        assert result["slots"][0]["start"] == "2026-07-23T09:00:00"

    def test_work_history_is_used_when_availability_missing(self):
        resume = {
            "work_history": [
                {"company": "A", "end_date": None, "position": "Engineer"}
            ]
        }
        result = build_candidate_availability_from_resume(resume)
        assert len(result["slots"]) == 2
        assert result["slots"][0]["start"].endswith("T18:00:00")
