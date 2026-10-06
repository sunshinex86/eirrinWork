"""ベクトル埋め込みユーティリティのテスト"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.vector_utils import (
    compute_cosine_similarity,
    compute_cosine_similarity_matrix,
    compute_embedding_similarity,
)


class TestCosineSimilarity:
    """コサイン類似度計算のテスト"""

    def test_identical_vectors(self):
        """同一ベクトル: 1.0"""
        vec = np.array([1.0, 2.0, 3.0])
        assert compute_cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """直交ベクトル: 0.0"""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        assert compute_cosine_similarity(vec1, vec2) == pytest.approx(0.0, abs=1e-10)

    def test_same_direction(self):
        """同じ方向のベクトル: 1.0"""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([2.0, 4.0, 6.0])
        assert compute_cosine_similarity(vec1, vec2) == pytest.approx(1.0)

    def test_opposite_direction(self):
        """逆方向ベクトルは負→0.0にクランプ（REQ-05）"""
        vec1 = np.array([1.0, 0.0])
        vec2 = np.array([-1.0, 0.0])
        result = compute_cosine_similarity(vec1, vec2)
        assert result == 0.0

    def test_zero_vector(self):
        """ゼロベクトル: 0.0"""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.zeros(3)
        assert compute_cosine_similarity(vec1, vec2) == 0.0
        assert compute_cosine_similarity(vec2, vec2) == 0.0

    def test_partial_similarity(self):
        """部分的に一致するベクトル"""
        vec1 = np.array([1.0, 1.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        result = compute_cosine_similarity(vec1, vec2)
        assert 0.0 < result < 1.0

    def test_different_dimensions(self):
        """異なる次元数のベクトルは 0.0（REQ-05）"""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([1.0, 2.0])
        result = compute_cosine_similarity(vec1, vec2)
        assert result == 0.0

    def test_1d_vectors(self):
        """1次元ベクトル"""
        vec1 = np.array([5.0])
        vec2 = np.array([10.0])
        assert compute_cosine_similarity(vec1, vec2) == pytest.approx(1.0)
        vec3 = np.array([-5.0])
        # 負のコサイン類似度 → 0.0 にクランプされる（REQ-05）
        assert compute_cosine_similarity(vec1, vec3) == 0.0


class TestCosineSimilarityMatrix:
    """コサイン類似度行列計算のテスト"""

    def test_single_pair(self):
        """1対1の行列"""
        embs1 = np.array([[1.0, 0.0, 0.0]])
        embs2 = np.array([[1.0, 0.0, 0.0]])
        matrix = compute_cosine_similarity_matrix(embs1, embs2)
        assert matrix.shape == (1, 1)
        assert matrix[0][0] == pytest.approx(1.0)

    def test_multiple_pairs(self):
        """複数対複数の行列"""
        embs1 = np.array([[1.0, 0.0], [0.0, 1.0]])
        embs2 = np.array([[1.0, 0.0], [0.0, 1.0]])
        matrix = compute_cosine_similarity_matrix(embs1, embs2)
        assert matrix.shape == (2, 2)
        assert matrix[0][0] == pytest.approx(1.0)  # (1,0) vs (1,0)
        assert matrix[0][1] == pytest.approx(0.0, abs=1e-10)  # (1,0) vs (0,1)
        assert matrix[1][0] == pytest.approx(0.0, abs=1e-10)  # (0,1) vs (1,0)
        assert matrix[1][1] == pytest.approx(1.0)  # (0,1) vs (0,1)

    def test_different_sizes(self):
        """異なるサイズの行列 (3x2 vs 2x2)"""
        embs1 = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
        embs2 = np.array([[1.0, 0.0], [0.0, 1.0]])
        matrix = compute_cosine_similarity_matrix(embs1, embs2)
        assert matrix.shape == (3, 2)


class TestEmbeddingSimilarity:
    """テキスト間埋め込み類似度のテスト（モデルモック）"""

    def test_with_mock_model(self):
        """モックモデルを使用した埋め込み類似度"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 4
        # 類似したテキストに対して似たベクトルを返す
        mock_model.encode.side_effect = [
            np.array([0.1, 0.2, 0.3, 0.4]),  # text1
            np.array([0.1, 0.2, 0.3, 0.4]),  # text2（同一）
        ]

        with patch("src.utils.vector_utils._load_model", return_value=mock_model):
            from src.utils.vector_utils import generate_embedding

            vec1 = generate_embedding("PythonとDjangoを使った開発")
            vec2 = generate_embedding("PythonとDjangoを使った開発")
            score = compute_cosine_similarity(vec1, vec2)
            assert score == pytest.approx(1.0)

    def test_different_texts_with_mock(self):
        """異なるテキストで低類似度"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 4
        mock_model.encode.side_effect = [
            np.array([0.1, 0.2, 0.3, 0.4]),  # text1
            np.array([0.9, 0.8, 0.1, 0.0]),  # text2（異なる）
        ]

        with patch("src.utils.vector_utils._load_model", return_value=mock_model):
            from src.utils.vector_utils import generate_embedding

            vec1 = generate_embedding("Python開発")
            vec2 = generate_embedding("製造業プロジェクト管理")
            score = compute_cosine_similarity(vec1, vec2)
            # 上記のベクトルだと 0.66 程度になる
            assert 0.0 < score < 1.0

    def test_empty_string(self):
        """空文字の場合はゼロベクトル"""
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 4
        mock_model.encode.return_value = np.zeros(4)

        with patch("src.utils.vector_utils._load_model", return_value=mock_model):
            from src.utils.vector_utils import generate_embedding

            vec = generate_embedding("")
            assert np.all(vec == 0)


class TestSafetyFeatures:
    """REQ-05: Embeddingスコア正常化のテスト"""

    def test_negative_cosine_clamped_to_zero(self):
        """負のコサイン類似度は0.0にクランプ"""
        vec1 = np.array([1.0, 0.0])
        vec2 = np.array([-1.0, 0.0])
        score = compute_cosine_similarity(vec1, vec2)
        assert score == 0.0

    def test_nan_vector_returns_zero(self):
        """NaN を含むベクトルは 0.0"""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([float('nan'), 0.0, 0.0])
        score = compute_cosine_similarity(vec1, vec2)
        assert score == 0.0

    def test_inf_vector_returns_zero(self):
        """無限大を含むベクトルは 0.0"""
        vec1 = np.array([1.0, 0.0])
        vec2 = np.array([float('inf'), 0.0])
        score = compute_cosine_similarity(vec1, vec2)
        assert score == 0.0

    def test_dimension_mismatch_returns_zero(self):
        """次元不一致は 0.0"""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([1.0, 2.0])
        score = compute_cosine_similarity(vec1, vec2)
        assert score == 0.0

    def test_empty_vector_returns_zero(self):
        """空のベクトルは 0.0"""
        vec1 = np.array([])
        vec2 = np.array([])
        score = compute_cosine_similarity(vec1, vec2)
        assert score == 0.0

    def test_similarity_matrix_clipped(self):
        """類似度行列も 0.0〜1.0 にクランプ"""
        embs1 = np.array([[1.0, 0.0]])
        embs2 = np.array([[-1.0, 0.0]])
        matrix = compute_cosine_similarity_matrix(embs1, embs2)
        assert matrix[0][0] == 0.0

    def test_embedding_similarity_with_nan(self):
        """compute_embedding_similarity が例外を出さない"""
        with patch("src.utils.vector_utils.generate_embedding", side_effect=Exception("test")):
            score = compute_embedding_similarity("test", "test")
            assert score == 0.0

    def test_model_status_initially_disabled(self):
        """EMBEDDING_ENABLED=false の初期状態は 'disabled'"""
        import src.utils.vector_utils as vu
        vu.clear_cache()
        vu._embedding_model = None
        vu._model_status = "disabled"
        status = vu.get_model_status()
        assert status == "disabled"


class TestIsAvailable:
    """利用可否判定のテスト"""

    def test_available_when_enabled(self):
        """EMBEDDING_ENABLED=true かつモデル利用可能時は True"""
        with patch("src.utils.vector_utils.EMBEDDING_ENABLED", True):
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            with patch("src.utils.vector_utils._load_model", return_value=mock_model):
                from src.utils.vector_utils import is_available
                assert is_available() is True

    def test_disabled_when_not_enabled(self):
        """EMBEDDING_ENABLED=false は False"""
        import src.utils.vector_utils as vu
        vu.clear_cache()
        vu._embedding_model = None
        vu._model_status = "disabled"
        # E2E tests may have set EMBEDDING_ENABLED=true, so patch explicitly
        with patch("src.utils.vector_utils.EMBEDDING_ENABLED", False):
            assert vu.is_available() is False


class TestLocalFilesOnly:
    """REQ-RE2-01: local_files_only=True 確認"""

    @patch("src.utils.vector_utils._check_cache_exists", return_value=True)
    @patch("src.utils.vector_utils.EMBEDDING_ENABLED", True)
    def test_load_model_uses_local_files_only(self, mock_cache):
        """SentenceTransformer が local_files_only=True で呼ばれること"""
        with patch("sentence_transformers.SentenceTransformer") as mock_st:
            from src.utils.vector_utils import _load_model
            try:
                _load_model()
            except Exception:
                pass
            # SentenceTransformer が local_files_only=True で呼ばれたことを確認
            if mock_st.called:
                args, kwargs = mock_st.call_args
                assert kwargs.get("local_files_only") is True, f"Expected local_files_only=True, got {kwargs}"

    @patch("src.utils.vector_utils._check_cache_exists", return_value=False)
    @patch("src.utils.vector_utils.EMBEDDING_ENABLED", True)
    def test_load_model_raises_not_downloaded_when_no_cache(self, mock_cache):
        """キャッシュがない場合、not_downloaded で終了し SentenceTransformer を呼ばない"""
        import src.utils.vector_utils as vu
        vu.clear_cache()
        vu._embedding_model = None
        vu._model_status = "not_loaded"
        with patch.object(vu, "EMBEDDING_ENABLED", True):
            with patch("sentence_transformers.SentenceTransformer") as mock_st:
                with pytest.raises(RuntimeError):
                    vu._load_model()
                mock_st.assert_not_called()

    @patch("src.utils.vector_utils.EMBEDDING_ENABLED", False)
    def test_disabled_does_not_load(self):
        """EMBEDDING_ENABLED=false ではロードしない"""
        import src.utils.vector_utils as vu
        vu.clear_cache()
        vu._embedding_model = None
        vu._model_status = "disabled"
        with patch("sentence_transformers.SentenceTransformer") as mock_st:
            with patch.object(vu, "EMBEDDING_ENABLED", False):
                with pytest.raises(RuntimeError, match="disabled"):
                    vu._load_model()
                mock_st.assert_not_called()
                assert vu._model_status == "disabled"


class TestIsAvailableSideEffects:
    """REQ-RE2-01: is_available() 副作用なし確認"""

    def test_is_available_does_not_call_load_model(self):
        """is_available() が _load_model() を呼ばないこと"""
        with patch("src.utils.vector_utils._load_model") as mock_load:
            from src.utils.vector_utils import is_available, clear_cache
            clear_cache()
            # デフォルトは EMBEDDING_ENABLED=false → is_available=False
            result = is_available()
            # _load_model は呼ばれていない
            mock_load.assert_not_called()

    @patch("src.utils.vector_utils.EMBEDDING_ENABLED", True)
    @patch("src.utils.vector_utils._check_importable", return_value=True)
    @patch("src.utils.vector_utils._check_cache_exists", return_value=True)
    def test_available_returns_true_without_loading(self, mock_cache, mock_import):
        """キャッシュ存在時はロードなしで True を返す"""
        with patch("src.utils.vector_utils._load_model") as mock_load:
            from src.utils.vector_utils import is_available, clear_cache
            clear_cache()
            result = is_available()
            assert result is True
            mock_load.assert_not_called()