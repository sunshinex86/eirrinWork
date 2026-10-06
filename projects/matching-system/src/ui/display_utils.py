"""UI表示用ユーティリティ関数（Streamlit非依存）

REQ-RE3-07: UIテストで本番コードをimport可能にするため、表示ロジックを分離。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any


def format_sample_result_status(result: dict) -> list[str]:
    """サンプル読込結果の表示メッセージを生成する（純粋関数）"""
    parts: list[str] = []
    committed = result.get("committed", False)

    if not committed and result.get("failed", 0) > 0:
        return [f"❌ 検証失敗: {result['failed']}件が保存できませんでした"]

    if result.get("created", 0):
        parts.append(f"✅ {result['created']}件成功")
    if result.get("skipped", 0):
        parts.append(f"⏭️ {result['skipped']}件重複")
    if result.get("failed"):
        parts.append(f"❌ {result['failed']}件失敗")

    return parts if parts else ["読込結果が空です"]


def has_unresolved_warnings(result: dict) -> bool:
    """未解決スキル警告の有無を返す"""
    return len(result.get("unresolved_skills", [])) > 0


def get_unresolved_count(result: dict) -> int:
    """未解決スキル件数を返す"""
    return len(result.get("unresolved_skills", []))


def has_rag_sources(match_item: dict) -> bool:
    """RAG参照情報の有無を返す"""
    return len(match_item.get("rag_sources", [])) > 0


def get_rag_source_count(match_item: dict) -> int:
    """RAG参照情報の件数を返す"""
    return len(match_item.get("rag_sources", []))


def build_candidate_availability_from_resume(resume: dict) -> dict[str, Any]:
    """候補者の resume から schedule 用 availability を推定する。

    1. resume に明示的な availability があれば優先使用
    2. 未明示なら available_from を推定し、work_history の現在職務状態から slots も構築
    """
    explicit = resume.get("availability")
    if isinstance(explicit, dict):
        payload = {
            "slots": explicit.get("slots", []),
        }
        if explicit.get("available_from"):
            payload["available_from"] = explicit["available_from"]
        if payload.get("slots"):
            return payload

    work_history = resume.get("work_history", [])
    current_suffix = date.today()
    latest = work_history[0] if work_history else {}

    if latest.get("end_date") is None:
        available_from = current_suffix + timedelta(days=30)
        slots = [
            {
                "start": f"{current_suffix}T18:00:00",
                "end": f"{current_suffix}T21:00:00",
            },
            {
                "start": f"{current_suffix + timedelta(days=1)}T18:00:00",
                "end": f"{current_suffix + timedelta(days=1)}T21:00:00",
            },
        ]
    else:
        available_from = current_suffix
        slots = [
            {
                "start": f"{current_suffix}T09:00:00",
                "end": f"{current_suffix}T18:00:00",
            },
            {
                "start": f"{current_suffix + timedelta(days=1)}T09:00:00",
                "end": f"{current_suffix + timedelta(days=1)}T18:00:00",
            },
        ]

    return {
        "available_from": available_from.isoformat(),
        "slots": slots,
    }
