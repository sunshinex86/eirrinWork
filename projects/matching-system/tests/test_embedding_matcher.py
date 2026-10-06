"""ルール＋埋め込みマッチングスコア関数のテスト（10軸版）"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.matching.embedding_matcher import (
    compute_hybrid_score,
    _compute_role_score,
    _compute_required_skill_score,
    _compute_preferred_skill_score,
    _compute_skill_depth_score,
    _compute_context_score,
    _compute_embedding_similarity_score,
    ROLE_KEYWORDS,
)


class TestRoleScore:
    """ルールベースロール一致スコアのテスト"""

    def test_exact_role_match(self, sample_resume, sample_job):
        """同じロールが含まれている場合"""
        score = _compute_role_score(sample_resume, sample_job)
        assert score > 0.5

    def test_no_role_in_job(self, sample_resume):
        """案件にロール指定がない場合"""
        job_no_role = {
            "id": "job-no-role",
            "title": "未分類ポジション",
            "job_type": "",
            "description": "業務内容未定",
        }
        score = _compute_role_score(sample_resume, job_no_role)
        assert score == 1.0

    def test_no_role_in_resume(self, sample_job):
        """経歴書にロール情報がない場合"""
        resume_no_role = {
            "id": "r-no-role",
            "name": "テスト",
            "work_history": [],
            "employment_type": "正社員",
        }
        score = _compute_role_score(resume_no_role, sample_job)
        assert score == 0.5


class TestRequiredSkillScore:
    """必須スキル一致スコアのテスト"""

    def test_required_skill_match(self):
        """必須スキル一致"""
        resume = {
            "structured_skills": [
                {"skill_id": "python", "level": 4, "years": 5, "last_used_year": 2026},
                {"skill_id": "sql", "level": 3, "years": 3, "last_used_year": 2026},
            ]
        }
        job = {
            "structured_required_skills": [
                {"skill_id": "python", "required_level": 3, "required_years": 3, "required": True},
                {"skill_id": "sql", "required_level": 2, "required_years": 2, "required": True},
            ]
        }
        score = _compute_required_skill_score(resume, job)
        assert score >= 0.9  # 完全一致＋レベルボーナス

    def test_required_skill_partial(self):
        """一部不足"""
        resume = {
            "structured_skills": [
                {"skill_id": "python", "level": 4, "years": 5, "last_used_year": 2026},
            ]
        }
        job = {
            "structured_required_skills": [
                {"skill_id": "python", "required_level": 3, "required_years": 3, "required": True},
                {"skill_id": "java", "required_level": 3, "required_years": 3, "required": True},
            ]
        }
        score = _compute_required_skill_score(resume, job)
        assert 0.4 < score < 0.7

    def test_no_required_skills(self):
        """必須スキルなし"""
        score = _compute_required_skill_score({"structured_skills": []}, {"structured_required_skills": []})
        assert score == 1.0


class TestPreferredSkillScore:
    """歓迎スキル一致スコアのテスト"""

    def test_preferred_match(self):
        resume = {"structured_skills": [{"skill_id": "react", "level": 3, "years": 2, "last_used_year": 2026}]}
        job = {"structured_preferred_skills": [{"skill_id": "react", "required_level": 2, "required_years": 1, "required": False}]}
        score = _compute_preferred_skill_score(resume, job)
        assert score == 1.0

    def test_no_preferred(self):
        score = _compute_preferred_skill_score({"structured_skills": []}, {"structured_preferred_skills": []})
        assert score == 1.0


class TestContextScore:
    """文脈スコアのテスト"""

    @patch("src.matching.embedding_matcher.embedding_available", return_value=False)
    def test_rule_context_match(self, mock_avail):
        """ルールベース業界一致"""
        resume = {"work_history": [{"industry": "IT・通信", "description": ""}]}
        job = {"industry": "IT・通信", "description": ""}
        score = _compute_context_score(resume, job)
        assert score == 1.0

    @patch("src.matching.embedding_matcher.embedding_available", return_value=False)
    def test_rule_context_no_match(self, mock_avail):
        resume = {"work_history": [{"industry": "製造", "description": ""}]}
        job = {"industry": "金融", "description": ""}
        score = _compute_context_score(resume, job)
        assert score < 0.5


class TestHybridScore:
    """統合スコアリングのテスト"""

    def test_hybrid_score_structure(self, sample_resume, sample_job):
        """統合スコアの戻り値構造が正しいこと"""
        with patch("src.matching.embedding_matcher.embedding_available", return_value=False):
            result = compute_hybrid_score(sample_resume, sample_job)
            expected_keys = {"mode", "degraded", "total_score", "weights", "breakdown", "matched_skills", "missing_required_skills", "missing_preferred_skills", "rag_sources", "rag_corrections", "explanation"}
            assert set(result.keys()) == expected_keys
            assert result["mode"] == "hybrid_degraded"
            assert result["degraded"] is True
            assert 0.0 <= result["total_score"] <= 1.0

    def test_breakdown_7_axes(self, sample_resume, sample_job):
        """10軸ブレークダウンが含まれること"""
        with patch("src.matching.embedding_matcher.embedding_available", return_value=False):
            result = compute_hybrid_score(sample_resume, sample_job)
            axes = {"required_skill_score", "preferred_skill_score", "skill_depth_score",
                    "skill_hierarchy_score", "experience_score", "location_score",
                    "context_score", "role_score", "unit_price_score", "embedding_score"}
            assert set(result["breakdown"].keys()) == axes
            for val in result["breakdown"].values():
                assert 0.0 <= val <= 1.0

    def test_degraded_false_when_embedding_available(self, sample_resume, sample_job):
        """embedding 利用可能時は degraded=false"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = __import__('numpy').zeros(384)

        with patch("src.matching.embedding_matcher.embedding_available", return_value=True):
            with patch("src.utils.vector_utils._load_model", return_value=mock_model):
                result = compute_hybrid_score(sample_resume, sample_job)
                assert result["mode"] == "hybrid"
                assert result["degraded"] is False

    def test_empty_data(self):
        """空データでもエラーにならないこと"""
        empty = {"id": "e", "skills": {}, "structured_skills": [], "structured_required_skills": [],
                 "structured_preferred_skills": [], "work_history": [], "years_of_experience": 0,
                 "title": "", "company": "", "description": "", "industry": "",
                 "job_type": "", "employment_type": ""}
        with patch("src.matching.embedding_matcher.embedding_available", return_value=False):
            result = compute_hybrid_score(empty, empty)
            assert 0.0 <= result["total_score"] <= 1.0

    def test_explanation_generated(self, sample_resume, sample_job):
        """説明文が生成されること"""
        with patch("src.matching.embedding_matcher.embedding_available", return_value=False):
            result = compute_hybrid_score(sample_resume, sample_job)
            assert len(result["explanation"]) > 0


class TestRAGCorrection:
    """RAG context_score 補正ロジックのテスト（FIX-03）"""

    @pytest.fixture
    def basic_resume(self):
        return {
            "id": "r1", "work_history": [{"industry": "IT・通信", "description": "開発"}],
            "structured_skills": [], "skills": {}, "years_of_experience": 5,
            "location": "東京", "desired_locations": [],
        }

    @pytest.fixture
    def basic_job(self):
        return {
            "id": "j1", "industry": "IT・通信", "title": "エンジニア", "description": "開発",
            "structured_required_skills": [], "structured_preferred_skills": [],
            "required_skills": {}, "preferred_skills": {}, "required_experience_years": 3,
            "location": "東京", "remote_policy": "", "unit_price_min": 0, "unit_price_max": 0,
        }

    def _run(self, resume, job, mock_results):
        """RAG有効状態で compute_hybrid_score を実行"""
        with patch("src.matching.embedding_matcher.embedding_available", return_value=False):
            with patch("config.RAG_ENABLED", True):
                with patch("config.RAG_CONTEXT_SIMILARITY_THRESHOLD", 0.70):
                    with patch("src.utils.rag_pipeline.search_matching_context", return_value=mock_results):
                        return compute_hybrid_score(resume, job)

    def _make_entry(self, entry_id, similarity_score, category="industry", tags=None, content=""):
        """RAG検索結果エントリを生成"""
        return {
            "id": entry_id,
            "similarity_score": similarity_score,
            "category": category,
            "tags": tags or [],
            "content": content,
        }

    def test_rag_disabled_no_correction(self, basic_resume, basic_job):
        """RAG無効時は補正なし"""
        with patch("src.matching.embedding_matcher.embedding_available", return_value=False):
            with patch("config.RAG_ENABLED", False):
                result = compute_hybrid_score(basic_resume, basic_job)
        assert len(result["rag_corrections"]) == 0

    def test_below_threshold_no_correction(self, basic_resume, basic_job):
        """類似度0.6999（閾値未満）→ 補正なし"""
        entry = self._make_entry("k1", 0.6999, tags=["IT・通信"], content="IT・通信")
        result = self._run(basic_resume, basic_job, [entry])
        corr = result["rag_corrections"][0]
        assert corr["before_score"] == corr["after_score"]
        assert "類似度不足" in corr["reason"]

    def test_threshold_met_with_match(self, basic_resume, basic_job):
        """類似度0.70以上 + 両側一致 → 補正あり（異業界でctx_scoreに余地）"""
        r = {"id": "r1", "work_history": [{"industry": "製造", "description": ""}],
             "structured_skills": [], "skills": {}, "years_of_experience": 5,
             "location": "東京", "desired_locations": []}
        j = {"id": "j1", "industry": "金融", "title": "", "description": "",
             "structured_required_skills": [], "structured_preferred_skills": [],
             "required_skills": {}, "preferred_skills": {}, "required_experience_years": 3,
             "location": "東京", "remote_policy": "", "unit_price_min": 0, "unit_price_max": 0}
        # 製造vs金融でルールベースctx_score=0.3、RAGで0.85エントリで加点
        entry = self._make_entry("k1", 0.85, tags=["製造", "金融"], content="製造×金融の経験")
        result = self._run(r, j, [entry])
        corr = result["rag_corrections"][0]
        assert corr["after_score"] > corr["before_score"]
        assert "業界ナレッジ一致" in corr["reason"]
        boost = corr["after_score"] - corr["before_score"]
        assert 0 < boost <= 0.30

    def test_rag_enabled_enters_block(self):
        """RAG有効でsearch_matching_contextが呼ばれることを確認"""
        r = {"id": "r1", "work_history": [{"industry": "IT・通信", "description": ""}],
             "structured_skills": [], "skills": {}, "years_of_experience": 5,
             "location": "東京", "desired_locations": []}
        j = {"id": "j1", "industry": "IT・通信", "title": "", "description": "",
             "structured_required_skills": [], "structured_preferred_skills": [],
             "required_skills": {}, "preferred_skills": {}, "required_experience_years": 3,
             "location": "東京", "remote_policy": "", "unit_price_min": 0, "unit_price_max": 0}
        entry = self._make_entry("k1", 0.85, tags=["IT・通信"], content="IT")
        result = self._run(r, j, [entry])
        # RAGブロックに入れば最低1件はrag_correctionsに追加される
        assert len(result["rag_corrections"]) >= 1
        corr = result["rag_corrections"][0]

    def test_resume_only_match(self):
        """Resume側のみ一致 → 補正なし"""
        r = {"id": "r1", "work_history": [{"industry": "IT・通信", "description": ""}],
             "structured_skills": [], "skills": {}, "years_of_experience": 5,
             "location": "東京", "desired_locations": []}
        j = {"id": "j1", "industry": "金融", "title": "", "description": "",
             "structured_required_skills": [], "structured_preferred_skills": [],
             "required_skills": {}, "preferred_skills": {}, "required_experience_years": 3,
             "location": "東京", "remote_policy": "", "unit_price_min": 0, "unit_price_max": 0}
        entry = self._make_entry("k1", 0.85, tags=["IT・通信"], content="IT・通信")
        result = self._run(r, j, [entry])
        corr = result["rag_corrections"][0]
        assert corr["before_score"] == corr["after_score"]
        assert "関連性が不十分" in corr["reason"]

    def test_job_only_match(self):
        """Job側のみ一致 → 補正なし"""
        r = {"id": "r1", "work_history": [{"industry": "金融", "description": ""}],
             "structured_skills": [], "skills": {}, "years_of_experience": 5,
             "location": "東京", "desired_locations": []}
        j = {"id": "j1", "industry": "IT・通信", "title": "", "description": "",
             "structured_required_skills": [], "structured_preferred_skills": [],
             "required_skills": {}, "preferred_skills": {}, "required_experience_years": 3,
             "location": "東京", "remote_policy": "", "unit_price_min": 0, "unit_price_max": 0}
        entry = self._make_entry("k1", 0.85, tags=["IT・通信"], content="IT・通信")
        result = self._run(r, j, [entry])
        corr = result["rag_corrections"][0]
        assert corr["before_score"] == corr["after_score"]
        assert "関連性が不十分" in corr["reason"]

    def test_job_industry_empty(self):
        """Job業界が空 → 補正なし"""
        r = {"id": "r1", "work_history": [{"industry": "IT・通信", "description": ""}],
             "structured_skills": [], "skills": {}, "years_of_experience": 5,
             "location": "東京", "desired_locations": []}
        j = {"id": "j1", "industry": "", "title": "", "description": "",
             "structured_required_skills": [], "structured_preferred_skills": [],
             "required_skills": {}, "preferred_skills": {}, "required_experience_years": 3,
             "location": "東京", "remote_policy": "", "unit_price_min": 0, "unit_price_max": 0}
        entry = self._make_entry("k1", 0.85, tags=["IT・通信"], content="IT・通信")
        result = self._run(r, j, [entry])
        corr = result["rag_corrections"][0]
        assert corr["before_score"] == corr["after_score"]

    def test_non_industry_category(self, basic_resume, basic_job):
        """カテゴリがindustry以外 → 補正なし"""
        entry = self._make_entry("k1", 0.85, category="role", tags=["IT・通信"], content="IT・通信")
        result = self._run(basic_resume, basic_job, [entry])
        corr = result["rag_corrections"][0]
        assert corr["before_score"] == corr["after_score"]
        assert "補正対象外" in corr["reason"]

    def test_keyword_fallback_no_correction(self, basic_resume, basic_job):
        """Keyword fallback（similarity_scoreなし）→ 補正なし"""
        entry = {"id": "k1", "category": "industry", "tags": ["IT・通信"], "content": "IT"}
        result = self._run(basic_resume, basic_job, [entry])
        corr = result["rag_corrections"][0]
        assert corr["before_score"] == corr["after_score"]
        assert "類似度不明" in corr["reason"]

    def test_multiple_results_total_boost_capped(self):
        """複数RAG結果でも合計加点は0.30以下"""
        r = {"id": "r1", "work_history": [{"industry": "製造", "description": ""}],
             "structured_skills": [], "skills": {}, "years_of_experience": 5,
             "location": "東京", "desired_locations": []}
        j = {"id": "j1", "industry": "金融", "title": "", "description": "",
             "structured_required_skills": [], "structured_preferred_skills": [],
             "required_skills": {}, "preferred_skills": {}, "required_experience_years": 3,
             "location": "東京", "remote_policy": "", "unit_price_min": 0, "unit_price_max": 0}
        e1 = self._make_entry("k1", 0.95, tags=["製造", "金融"], content="両方")
        e2 = self._make_entry("k2", 0.90, tags=["製造", "金融"], content="両方")
        result = self._run(r, j, [e1, e2])
        base = result["rag_corrections"][0]["before_score"]
        max_after = max(c["after_score"] for c in result["rag_corrections"])
        assert max_after - base <= 0.301

    def test_rag_exception_preserves_score(self):
        """RAG例外発生 → 元スコア維持"""
        r = {"id": "r1", "work_history": [{"industry": "IT・通信", "description": ""}],
             "structured_skills": [], "skills": {}, "years_of_experience": 5,
             "location": "東京", "desired_locations": []}
        j = {"id": "j1", "industry": "IT・通信", "title": "", "description": "",
             "structured_required_skills": [], "structured_preferred_skills": [],
             "required_skills": {}, "preferred_skills": {}, "required_experience_years": 3,
             "location": "東京", "remote_policy": "", "unit_price_min": 0, "unit_price_max": 0}
        with patch("src.matching.embedding_matcher.embedding_available", return_value=False):
            with patch("config.RAG_ENABLED", True):
                with patch("src.utils.rag_pipeline.search_matching_context",
                          side_effect=Exception("search failed")):
                    result = compute_hybrid_score(r, j)
        assert len(result["rag_corrections"]) == 0

    def test_correction_info_structure(self):
        """補正情報の構造を確認"""
        r = {"id": "r1", "work_history": [{"industry": "製造", "description": ""}],
             "structured_skills": [], "skills": {}, "years_of_experience": 5,
             "location": "東京", "desired_locations": []}
        j = {"id": "j1", "industry": "金融", "title": "", "description": "",
             "structured_required_skills": [], "structured_preferred_skills": [],
             "required_skills": {}, "preferred_skills": {}, "required_experience_years": 3,
             "location": "東京", "remote_policy": "", "unit_price_min": 0, "unit_price_max": 0}
        entry = self._make_entry("k1", 0.85, tags=["製造", "金融"], content="両方")
        result = self._run(r, j, [entry])
        corr = result["rag_corrections"][0]
        assert corr["source_id"] == "k1"
        assert 0.0 <= corr["before_score"] <= 1.0
        assert 0.0 <= corr["after_score"] <= 1.0
        assert len(corr["reason"]) > 0


class TestRoleKeywords:
    """ロール分類キーワード定義のテスト"""

    def test_role_keywords_defined(self):
        """主要なロールが定義されていること"""
        assert "SE" in ROLE_KEYWORDS
        assert "PM" in ROLE_KEYWORDS
        assert "アーキテクト" in ROLE_KEYWORDS

    def test_role_has_labels(self):
        """各ロールにラベルがあること"""
        for role, info in ROLE_KEYWORDS.items():
            assert len(info["labels"]) > 0


class TestSkillDepthScore:
    """REQ-RE2-02: スキル深度スコアの全必須スキル平均"""

    def test_5_required_1_matched_max_0_2(self):
        """必須5件中1件完全一致の場合、max 0.2"""
        from src.matching.embedding_matcher import _compute_skill_depth_score
        resume = {"structured_skills": [
            {"skill_id": "python", "level": 5, "years": 10, "last_used_year": 2026},
        ]}
        job = {"structured_required_skills": [
            {"skill_id": "python", "required_level": 3, "required_years": 3},
            {"skill_id": "java", "required_level": 3, "required_years": 3},
            {"skill_id": "sql", "required_level": 2, "required_years": 2},
            {"skill_id": "docker", "required_level": 2, "required_years": 2},
            {"skill_id": "aws", "required_level": 2, "required_years": 2},
        ]}
        score = _compute_skill_depth_score(resume, job)
        # 1件完全一致(level_score=1.0, years_score=1.0, freshness=1.0 → depth=1.0) / 5 = 0.2
        assert score <= 0.21, f"Expected <=0.2, got {score}"
        assert score > 0.15, f"Expected around 0.2, got {score}"

    def test_required_skills_empty_resume_skills_empty(self):
        """必須スキルあり、候補者スキル空 = 0.0"""
        from src.matching.embedding_matcher import _compute_skill_depth_score
        resume = {"structured_skills": []}
        job = {"structured_required_skills": [
            {"skill_id": "python", "required_level": 3, "required_years": 3},
        ]}
        score = _compute_skill_depth_score(resume, job)
        assert score == 0.0

    def test_no_required_skills(self):
        """必須スキルなし = 1.0"""
        from src.matching.embedding_matcher import _compute_skill_depth_score
        resume = {"structured_skills": []}
        job = {"structured_required_skills": []}
        score = _compute_skill_depth_score(resume, job)
        assert score == 1.0

    def test_no_fallback_to_years_of_experience(self):
        """総経験年数による代替計算が行われないこと"""
        from src.matching.embedding_matcher import _compute_skill_depth_score
        resume = {"structured_skills": [], "years_of_experience": 20}
        job = {"structured_required_skills": [
            {"skill_id": "python", "required_level": 3, "required_years": 3},
        ]}
        score = _compute_skill_depth_score(resume, job)
        assert score == 0.0, f"Expected 0.0 (no fallback), got {score}"

    def test_denominator_is_total_required_not_matched_count(self):
        """分母は一致件数ではなく必須スキル総数"""
        from src.matching.embedding_matcher import _compute_skill_depth_score
        resume = {"structured_skills": [
            {"skill_id": "python", "level": 3, "years": 3, "last_used_year": 2026},
        ]}
        job = {"structured_required_skills": [
            {"skill_id": "python", "required_level": 3, "required_years": 3},
            {"skill_id": "java", "required_level": 3, "required_years": 3},
        ]}
        score = _compute_skill_depth_score(resume, job)
        # python matching score (level=1.0*0.5 + years=1.0*0.4 + freshness=1.0*0.1 = 1.0)
        # java matching score = 0.0 (unmatched)
        # score = (1.0 + 0.0) / 2 = 0.5
        assert 0.4 < score < 0.6, f"Expected 0.5, got {score}"


class TestRagSources:
    """REQ-RE2-07: RAG参照情報表示テスト"""

    def test_rag_sources_in_hybrid_result(self, sample_resume, sample_job):
        """ハイブリッド結果に rag_sources が含まれること"""
        from src.matching.embedding_matcher import compute_hybrid_score
        with patch("src.matching.embedding_matcher.embedding_available", return_value=False):
            result = compute_hybrid_score(sample_resume, sample_job)
            assert "rag_sources" in result
            assert isinstance(result["rag_sources"], list)

    def test_rag_sources_empty_when_rag_disabled(self, sample_resume, sample_job):
        """RAG無効時は rag_sources が空リスト"""
        from src.matching.embedding_matcher import compute_hybrid_score
        with patch("src.matching.embedding_matcher.embedding_available", return_value=False):
            with patch("config.RAG_ENABLED", False):
                result = compute_hybrid_score(sample_resume, sample_job)
                assert result["rag_sources"] == []

class TestEmbeddingE2E:
    """REQ-RE5-06: Embedding実動作E2Eテスト（実モデル、REQ-RE5-06）"""

    def _model_available(self) -> bool:
        """Embeddingモデルが利用可能か確認（REQ-RE5-06: embedding_availableをMockしない）"""
        import os
        os.environ["EMBEDDING_ENABLED"] = "true"
        # configをリロード
        import importlib
        import config
        importlib.reload(config)
        # vector_utilsもリロード
        import src.utils.vector_utils as vu
        importlib.reload(vu)
        return vu.is_available()

    @pytest.mark.embedding_e2e
    def test_hybrid_mode_with_real_model(self, sample_resume, sample_job):
        """実モデルE2E: embedding_available非Mock・実ベクトル生成・mode=hybrid"""
        import os
        run_e2e = os.environ.get("RUN_EMBEDDING_E2E", "0") == "1"

        if not self._model_available():
            if run_e2e:
                pytest.fail("RUN_EMBEDDING_E2E=1 but model not available (run scripts/download_embedding_model.py)")
            pytest.skip("Embedding model not downloaded (run scripts/download_embedding_model.py)")

        from src.matching.embedding_matcher import compute_hybrid_score

        # embedding_availableをMockしない（REQ-RE5-06）
        result = compute_hybrid_score(sample_resume, sample_job)

        assert result["mode"] == "hybrid", f"Expected hybrid, got {result['mode']}"
        assert result["degraded"] is False
        # embedding_score > 0（実モデルで実際に計算）
        emb = result["breakdown"]["embedding_score"]
        assert emb > 0.0, f"Expected embedding_score > 0 with real model, got {emb}"
        assert 0.0 <= result["total_score"] <= 1.0

    def test_degraded_mode_without_model(self, sample_resume, sample_job):
        """モデル未取得相当で hybrid_degraded になること"""
        with patch("src.matching.embedding_matcher.embedding_available", return_value=False):
            from src.matching.embedding_matcher import compute_hybrid_score
            result = compute_hybrid_score(sample_resume, sample_job)
            assert result["mode"] == "hybrid_degraded"
            assert result["degraded"] is True
            assert result["weights"].get("embedding", -1) == 0.0
            total_w = sum(v for k, v in result["weights"].items() if k != "embedding")
            assert abs(total_w - 1.0) < 0.01
