#!/usr/bin/env python3
"""経歴書×案件マッチングシステム 起動スクリプト

FastAPIバックエンド（port 8000）と
Streamlitフロントエンド（port 8501）を同時起動します。

Usage:
    python run.py          # 通常起動
    python run.py --api    # APIのみ起動
    python run.py --ui     # UIのみ起動
"""
import subprocess
import sys
import time
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="経歴書×案件マッチングシステム")
    parser.add_argument("--api", action="store_true", help="APIのみ起動")
    parser.add_argument("--ui", action="store_true", help="UIのみ起動")
    args = parser.parse_args()

    root = Path(__file__).parent

    processes = []

    if not args.ui and not args.api:
        # 両方起動
        print("=" * 50)
        print("🤝 経歴書×案件マッチングシステム 起動中...")
        print("=" * 50)

        # API起動
        print("📡 FastAPI 起動中... (http://localhost:8000)")
        print("   API ドキュメント: http://localhost:8000/docs")
        api_proc = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "src.api.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
        ], cwd=root)

        # Streamlit起動
        print("🖥️  Streamlit 起動中... (http://localhost:8501)")
        ui_proc = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run",
            "src/ui/app.py",
            "--server.port", "8501",
        ], cwd=root)

        processes = [api_proc, ui_proc]
        print()
        print("✅ 起動完了！")
        print("   UI:  http://localhost:8501")
        print("   API: http://localhost:8000/docs")
        print()
        print("Ctrl+C で終了します")

    elif args.api:
        # APIのみ
        print("📡 FastAPI 起動中... (http://localhost:8000)")
        api_proc = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "src.api.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
        ], cwd=root)
        processes = [api_proc]
    elif args.ui:
        # UIのみ
        print("🖥️  Streamlit 起動中... (http://localhost:8501)")
        ui_proc = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run",
            "src/ui/app.py",
            "--server.port", "8501",
        ], cwd=root)
        processes = [ui_proc]

    try:
        for proc in processes:
            proc.wait()
    except KeyboardInterrupt:
        print("\n🛑 終了しています...")
        for proc in processes:
            proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("✅ 終了しました")


if __name__ == "__main__":
    main()
