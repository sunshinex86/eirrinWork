"""
会議まとめの内容を meeting_output フォルダに保存するスクリプト。
フォルダが存在しない場合は自動作成する。

使い方:
    python upload.py "会議まとめの内容..."
    python upload.py --file summary.txt
    echo "会議まとめの内容..." | python upload.py
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent / "meeting_output"


def save_summary(content: str, filename: str | None = None) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"meeting_summary_{timestamp}.md"

    output_path = OUTPUT_DIR / filename
    output_path.write_text(content, encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="会議まとめを meeting_output フォルダに保存する")
    parser.add_argument("content", nargs="?", help="保存する会議まとめの内容")
    parser.add_argument("--file", help="会議まとめの内容が書かれたファイルのパス")
    parser.add_argument("--name", help="保存するファイル名（省略時はタイムスタンプ付きで自動生成）")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.file:
        content = Path(args.file).read_text(encoding="utf-8")
    elif args.content:
        content = args.content
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        print("エラー: 保存する内容を指定してください（引数 / --file / 標準入力）。", file=sys.stderr)
        sys.exit(1)

    output_path = save_summary(content, args.name)
    print(f"保存しました: {output_path}")


if __name__ == "__main__":
    main()
