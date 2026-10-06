#!/usr/bin/env python3
"""Embeddingモデルダウンロードスクリプト（REQ-RE2-01）

通常のマッチング実行とは独立してモデルを事前取得する。
ダウンロード後、local_files_only=True での再ロード確認と
テストEmbedding生成まで成功した場合のみ正常終了する。

Usage:
    python scripts/download_embedding_model.py
    python scripts/download_embedding_model.py --model-name all-MiniLM-L6-v2
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import EMBEDDING_MODEL_NAME


def main():
    parser = argparse.ArgumentParser(description="Embeddingモデルをダウンロードする")
    parser.add_argument("--model-name", default=EMBEDDING_MODEL_NAME,
                        help=f"モデル名（デフォルト: {EMBEDDING_MODEL_NAME}）")
    args = parser.parse_args()

    model_name = args.model_name
    print(f"モデル: {model_name}")

    # Step 1: パッケージ確認
    try:
        from sentence_transformers import SentenceTransformer, __version__
        print(f"sentence-transformers version: {__version__}")
    except ImportError:
        print("Error: sentence-transformers がインストールされていません。")
        print("pip install sentence-transformers を実行してください。")
        sys.exit(1)

    # Step 2: ダウンロード（オンライン取得可能）
    print("ダウンロードを開始します...")
    print(f"保存先: ~/.cache/huggingface/hub/")
    try:
        model = SentenceTransformer(model_name)
        print(f"モデル次元数: {model.get_sentence_embedding_dimension()}")
    except Exception as e:
        print(f"Error: ダウンロードに失敗しました: {e}")
        sys.exit(1)

    # Step 3: local_files_only=True での再ロード確認
    print("ローカルキャッシュからのロード確認...")
    try:
        model_reloaded = SentenceTransformer(model_name, local_files_only=True)
        print(f"✅ ローカルロード成功（次元数: {model_reloaded.get_sentence_embedding_dimension()}）")
    except Exception as e:
        print(f"Error: ローカルロードに失敗しました: {e}")
        sys.exit(1)

    # Step 4: テストEmbedding生成
    print("テストEmbedding生成...")
    try:
        test_vec = model_reloaded.encode("テスト文です", normalize_embeddings=True)
        print(f"✅ Embedding確認: 次元={len(test_vec)}, 先頭={test_vec[0]:.4f}")
    except Exception as e:
        print(f"Error: Embedding生成に失敗しました: {e}")
        sys.exit(1)

    print(f"\n✅ ダウンロード完了: {model_name}")
    print("EMBEDDING_ENABLED=true に設定して使用してください。")
    sys.exit(0)


if __name__ == "__main__":
    main()
