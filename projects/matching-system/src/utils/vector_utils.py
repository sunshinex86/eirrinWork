"""ベクトル埋め込みユーティリティ

sentence-transformers を使ったローカル埋め込みモデルのラッパー。
コサイン類似度計算、テキスト間類似度算出を提供する。

REQ-RE2-01: 暗黙的ダウンロード禁止
  - _load_model() は local_files_only=True でモデルをロードする
  - is_available() は副作用なし（モデルロードをトリガーしない）
  - モデル未取得時は not_downloaded で終了、DLは専用スクリプトのみ
"""
import logging
import math
from collections import OrderedDict
from typing import Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity

from config import EMBEDDING_MODEL_NAME, EMBEDDING_ENABLED

_logger = logging.getLogger(__name__)

# --- モデル状態管理（6種 + disabled） ---
_embedding_model = None
_model_status = "disabled"  # disabled | not_installed | not_downloaded | ready | load_failure | timeout


def get_model_status() -> str:
    """モデルの状態を返す（副作用なし）"""
    global _model_status
    return _model_status


def _check_cache_exists() -> bool:
    """ローカルキャッシュにモデルが存在するか確認する（副作用なし）"""
    import os as _os
    from pathlib import Path as _Path
    _cache_dir = _Path.home() / ".cache" / "huggingface" / "hub"
    if not _cache_dir.exists():
        return False
    pattern = f"*{EMBEDDING_MODEL_NAME.replace('/', '_')}*"
    return any(_cache_dir.rglob(pattern))


def _check_importable() -> bool:
    """sentence-transformers がインストールされているか確認する（副作用なし）"""
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


def _load_model():
    """埋め込みモデルを lazy loading でロードする（REQ-RE2-01: local_files_only=True）

    マッチング処理内からのみ呼ばれる遅延ロード。
    ローカルファイルのみを参照し、オンライン取得は行わない。
    """
    global _embedding_model, _model_status

    if not EMBEDDING_ENABLED:
        _model_status = "disabled"
        raise RuntimeError("Embedding is disabled (EMBEDDING_ENABLED=false)")

    if _embedding_model is not None:
        _model_status = "ready"
        return _embedding_model

    _model_status = "not_loaded"

    # 事前チェック: キャッシュに存在しなければ not_downloaded で終了
    if not _check_cache_exists():
        _model_status = "not_downloaded"
        raise RuntimeError(f"モデルがダウンロードされていません: {EMBEDDING_MODEL_NAME}")

    try:
        from sentence_transformers import SentenceTransformer
        _model_status = "loading"
        # local_files_only=True: ローカルキャッシュのみ参照、オンライン取得しない
        _embedding_model = SentenceTransformer(
            EMBEDDING_MODEL_NAME,
            local_files_only=True,
        )
        _model_status = "ready"
    except ImportError:
        _model_status = "not_installed"
        _logger.error("sentence-transformers not installed")
        raise ImportError("sentence-transformers がインストールされていません")
    except OSError as e:
        _model_status = "not_downloaded"
        _logger.error(f"Model not downloaded: {e}")
        raise RuntimeError(f"モデルがダウンロードされていません: {e}")
    except Exception as e:
        _model_status = "load_failure"
        _logger.error(f"Model load failed: {e}", exc_info=True)
        raise RuntimeError(f"モデル読込失敗: {e}")
    return _embedding_model


def is_available() -> bool:
    """埋め込みモデルが利用可能かどうかを返す（REQ-RE2-01: 副作用なし）

    モデルロードをトリガーしない。以下の情報のみから判定する：
    - EMBEDDING_ENABLED 設定
    - sentence-transformers パッケージのインストール有無
    - ローカルキャッシュの存在
    - 既存の _model_status
    """
    global _model_status

    if not EMBEDDING_ENABLED:
        _model_status = "disabled"
        return False

    # 既にロード済み or ロード失敗が確定している場合
    if _model_status == "ready":
        return True
    if _model_status in ("not_downloaded", "not_installed", "load_failure", "timeout"):
        return False

    # パッケージインストール確認（副作用なし）
    if not _check_importable():
        _model_status = "not_installed"
        return False

    # ローカルキャッシュ確認（副作用なし）
    if not _check_cache_exists():
        _model_status = "not_downloaded"
        return False

    # 未ロードだが利用可能な状態
    _model_status = "not_loaded"
    return True


# --- ベクトルキャッシュ（簡易 LRU） ---
_vector_cache: OrderedDict = OrderedDict()
_VECTOR_CACHE_MAX = 256


def _cache_embedding(text: str, vec: np.ndarray):
    """ベクトルをキャッシュに保存"""
    if len(_vector_cache) >= _VECTOR_CACHE_MAX:
        _vector_cache.popitem(last=False)
    _vector_cache[hash(text)] = vec


def _get_cached_embedding(text: str) -> Optional[np.ndarray]:
    """キャッシュからベクトルを取得"""
    return _vector_cache.get(hash(text))


def clear_cache():
    """ベクトルキャッシュをクリア"""
    _vector_cache.clear()


# --- 安全なスコア計算（REQ-05） ---


def _safe_clip_score(score: float) -> float:
    """スコアを安全に 0.0〜1.0 にクランプ（NaN/∞対応）"""
    if math.isnan(score) or math.isinf(score):
        return 0.0
    return max(0.0, min(1.0, score))


def _validate_vector(vec: np.ndarray) -> bool:
    """ベクトルの妥当性を検証"""
    if vec is None:
        return False
    if vec.ndim == 0 or vec.size == 0:
        return False
    if np.any(np.isnan(vec)) or np.any(np.isinf(vec)):
        return False
    return True


# --- 公開関数 ---


def generate_embedding(text: str) -> np.ndarray:
    """テキストの埋め込みベクトルを生成する

    Args:
        text: 入力テキスト

    Returns:
        埋め込みベクトル（numpy 配列）
    """
    if not text or not text.strip():
        model = _load_model()
        return np.zeros(model.get_sentence_embedding_dimension())

    # キャッシュ確認
    cached = _get_cached_embedding(text)
    if cached is not None:
        return cached

    model = _load_model()
    embedding = model.encode(text, normalize_embeddings=True)

    # キャッシュに保存
    _cache_embedding(text, embedding)
    return embedding


def generate_embeddings_batch(texts: list[str]) -> np.ndarray:
    """複数テキストの埋め込みベクトルを一括生成する

    Args:
        texts: 入力テキストのリスト

    Returns:
        埋め込みベクトルの配列 (n_texts, embedding_dim)
    """
    valid_texts = [t if t and t.strip() else "" for t in texts]
    model = _load_model()
    embeddings = model.encode(valid_texts, normalize_embeddings=True)
    return embeddings


def compute_cosine_similarity(
    vec1: np.ndarray,
    vec2: np.ndarray,
) -> float:
    """2つのベクトル間のコサイン類似度を計算する（REQ-05: 安全処理）

    Args:
        vec1: 1つ目のベクトル
        vec2: 2つ目のベクトル

    Returns:
        0.0〜1.0 のコサイン類似度（異常時は 0.0）
    """
    if not _validate_vector(vec1) or not _validate_vector(vec2):
        return 0.0

    if vec1.shape != vec2.shape:
        return 0.0

    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0

    try:
        v1 = vec1.reshape(1, -1)
        v2 = vec2.reshape(1, -1)
        result = sklearn_cosine_similarity(v1, v2)
        raw_score = float(result[0][0])
        return _safe_clip_score(raw_score)
    except ValueError:
        return 0.0


def compute_cosine_similarity_matrix(
    embeddings1: np.ndarray,
    embeddings2: np.ndarray,
) -> np.ndarray:
    """2つの埋め込みセット間のコサイン類似度行列を計算する

    Args:
        embeddings1: 1つ目の埋め込みセット (n, dim)
        embeddings2: 2つ目の埋め込みセット (m, dim)

    Returns:
        0.0〜1.0 の類似度行列 (n, m)
    """
    if embeddings1.size == 0 or embeddings2.size == 0:
        return np.array([[0.0]])

    try:
        result = sklearn_cosine_similarity(embeddings1, embeddings2)
        return np.clip(result, 0.0, 1.0)
    except ValueError:
        return np.array([[0.0]])


def compute_embedding_similarity(text1: str, text2: str) -> float:
    """2つのテキスト間の埋め込み類似度を計算する（便利関数）

    Args:
        text1: 1つ目のテキスト
        text2: 2つ目のテキスト

    Returns:
        0.0〜1.0 の類似度スコア
    """
    try:
        vec1 = generate_embedding(text1)
        vec2 = generate_embedding(text2)
        return compute_cosine_similarity(vec1, vec2)
    except Exception:
        return 0.0
