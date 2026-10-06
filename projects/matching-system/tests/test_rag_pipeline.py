"""RAG パイプラインテスト"""
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRagConfidence:
    """REQ-RE6-05: RAG信頼度評価テスト"""

    def test_confidence_below_85_no_auto_save(self):
        """0.84 → can_auto_save=false"""
        from src.utils.skill_extraction_service import _evaluate_rag_confidence
        sug = _evaluate_rag_confidence({
            "skill_id": "python", "canonical_name": "Python",
            "confidence": 0.84, "source_id": "doc1",
        }, "Java開発経験")
        assert sug["can_auto_save"] is False

    def test_confidence_85_with_direct_evidence(self):
        """0.85 + 直接根拠あり → can_auto_save=true"""
        from src.utils.skill_extraction_service import _evaluate_rag_confidence
        sug = _evaluate_rag_confidence({
            "skill_id": "python", "canonical_name": "Python",
            "confidence": 0.85, "source_id": "doc1",
        }, "Pythonを使って開発")
        assert sug["can_auto_save"] is True
        assert sug["has_direct_evidence"] is True

    def test_confidence_85_without_direct_evidence(self):
        """0.85 + 直接根拠なし → can_auto_save=false"""
        from src.utils.skill_extraction_service import _evaluate_rag_confidence
        sug = _evaluate_rag_confidence({
            "skill_id": "python", "canonical_name": "Python",
            "confidence": 0.85, "source_id": "doc1",
        }, "Java開発経験")
        assert sug["can_auto_save"] is False
        assert sug["has_direct_evidence"] is False

    def test_alias_detected_as_direct_evidence(self):
        """エイリアスも直接根拠として認識"""
        from src.utils.skill_extraction_service import _evaluate_rag_confidence
        sug = _evaluate_rag_confidence({
            "skill_id": "javascript", "canonical_name": "JavaScript",
            "confidence": 0.90, "source_id": "doc1",
        }, "JSとTSを使用")
        assert sug["has_direct_evidence"] is True

    def test_rag_disabled_preserves_dictionary(self):
        """RAG無効時も辞書ベース抽出結果が維持される"""
        from src.utils.skill_extraction_service import extract_skills_service
        result = extract_skills_service("Python開発", use_rag=False)
        assert len(result["skills"]) > 0
        assert "rag_sources" in result
        assert "rag_suggestions" in result

    def test_rag_exception_preserves_dictionary(self):
        """RAG例外時も辞書ベース抽出結果が維持"""
        from src.utils.skill_extraction_service import extract_skills_service
        import config
        with patch.object(config, "RAG_ENABLED", True):
            with patch("src.utils.rag_pipeline.search_skill_context", side_effect=Exception("RAG error")):
                result = extract_skills_service("Python開発", use_rag=True)
                assert len(result["skills"]) > 0, "辞書抽出結果が消えている"


    def test_highest_confidence_wins_via_service(self):
        """複数RAG文書→同一skill_id、最高confidence採用を本番処理で検証"""
        from src.utils.skill_extraction_service import extract_skills_service
        import config
        with patch.object(config, "RAG_ENABLED", True):
            with patch("src.utils.rag_pipeline.search_skill_context") as mock:
                # Java入力なので、pythonは直接抽出されない
                mock.return_value = [
                    {"id": "doc1", "skill_ids": [], "tags": [], "content": "Python is a language"},
                    {"id": "doc2", "skill_ids": ["python"], "tags": [], "content": ""},
                ]
                result = extract_skills_service("Java開発経験", use_rag=True, top_k=5)
                # pythonは直接抽出されない（Java入力）
                skill_ids = [s["skill_id"] for s in result["skills"]]
                assert "python" not in skill_ids, "python should NOT be in direct extraction"
                # rag_suggestions に同一pythonが1件のみ（重複除去＋最高confidence採用）
                sug_ids = [s["skill_id"] for s in result.get("rag_suggestions", [])]
                python_sugs = [s for s in sug_ids if s == "python"]
                assert len(python_sugs) == 1, f"Expected exactly 1 python suggestion, got {len(python_sugs)}: {sug_ids}"
                # confidenceは0.70（doc2の値）が採用されている
                python_sugs_full = [s for s in result.get("rag_suggestions", []) if s["skill_id"] == "python"]
                assert python_sugs_full[0]["confidence"] == 0.70, f"Expected confidence 0.70, got {python_sugs_full[0]['confidence']}"
                assert python_sugs_full[0]["source_id"] == "doc2", f"Expected source_id doc2, got {python_sugs_full[0]['source_id']}"

    def test_rag_skills_not_mixed_into_skills(self):
        """RAG候補がskillsへ混入しない"""
        from src.utils.skill_extraction_service import extract_skills_service
        import config
        with patch.object(config, "RAG_ENABLED", True):
            with patch("src.utils.rag_pipeline.search_skill_context") as mock:
                mock.return_value = [{"id": "doc1", "skill_ids": ["aws", "docker"], "tags": [], "content": ""}]
                result = extract_skills_service("Python開発", use_rag=True)
                skill_ids = [s["skill_id"] for s in result["skills"]]
                assert "aws" not in skill_ids, "RAG候補がskillsに混入している"
                assert "docker" not in skill_ids, "RAG候補がskillsに混入している"
                # rag_suggestions には含まれる
                sug_ids = [s["skill_id"] for s in result.get("rag_suggestions", [])]
                assert "aws" in sug_ids or "docker" in sug_ids

    def test_top_k_limits_rag_suggestions_and_sources(self):
        """top_kでrag_suggestionsとrag_sourcesが制限される"""
        from src.utils.skill_extraction_service import extract_skills_service
        import config
        with patch.object(config, "RAG_ENABLED", True):
            with patch("src.utils.rag_pipeline.search_skill_context") as mock:
                # 5つのRAG文書が返るが、top_k=3で制限されるべき
                mock.return_value = [
                    {"id": f"doc{i}", "skill_ids": [f"skill{i}"], "tags": [], "content": ""}
                    for i in range(5)
                ]
                result = extract_skills_service("Java開発", use_rag=True, top_k=3)
                assert len(result.get("rag_suggestions", [])) <= 3, f"rag_suggestions exceeded top_k=3: {len(result['rag_suggestions'])}"
                assert len(result.get("rag_sources", [])) <= 3, f"rag_sources exceeded top_k=3: {len(result['rag_sources'])}"
