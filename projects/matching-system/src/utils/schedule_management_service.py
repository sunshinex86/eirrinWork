"""スケジュール管理サービス

availability モデリング、時間マッチング、競合検知を行う。
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any


def model_availability(candidate_availability: dict[str, Any], job_window: dict[str, Any]) -> dict[str, Any]:
    """候補者の開始可能日と job の開始日を比較し、より適切な候補を上位にする。

    ビジネス要件:
    - candidate.available_from が project_start より後なら不適合
    - candidate.available_from が project_start に近いほど高スコア
    - 現在の時刻窓との重なりがあれば、match を補強する
    """
    slots = candidate_availability.get("slots", [])
    if not slots:
        return {
            "availability_score": 0.0,
            "status": "unknown",
            "matches": [],
            "conflicts": ["availability slots are missing"],
        }

    project_start = _parse_date(job_window.get("project_start") or job_window.get("start"))
    candidate_start = _parse_date(candidate_availability.get("available_from"))
    if candidate_start is None:
        candidate_start = _parse_date(slots[0].get("start"))

    matches = []
    conflicts = []
    overlap_count = 0
    for slot in slots:
        start = slot.get("start")
        end = slot.get("end")
        if not start or not end:
            continue
        if _overlaps(start, end, job_window.get("start"), job_window.get("end")):
            matches.append({"start": start, "end": end, "status": "available"})
            overlap_count += 1
        else:
            conflicts.append({"start": start, "end": end, "status": "not_available"})

    if candidate_start is None or project_start is None:
        score = round(overlap_count / max(1, len(slots)), 3)
        return {
            "availability_score": score,
            "status": "match" if score >= 0.5 else "conflict",
            "matches": matches,
            "conflicts": conflicts,
        }

    if candidate_start > project_start:
        return {
            "availability_score": 0.0,
            "status": "conflict",
            "matches": matches,
            "conflicts": conflicts + [{
                "candidate_available_from": candidate_start.isoformat(),
                "project_start": project_start.isoformat(),
                "status": "candidate_starts_after_project",
            }],
        }

    alignment_days = max(0, (project_start - candidate_start).days)
    alignment_score = round(max(0.0, 1.0 - (alignment_days / 60.0)), 3)
    overlap_score = round(overlap_count / max(1, len(slots)), 3)
    score = round((alignment_score * 0.7) + (overlap_score * 0.3), 3)

    return {
        "availability_score": score,
        "status": "match" if score >= 0.3 else "conflict",
        "candidate_available_from": candidate_start.isoformat(),
        "project_start": project_start.isoformat(),
        "alignment_days": alignment_days,
        "matches": matches,
        "conflicts": conflicts,
    }


def detect_schedule_conflicts(candidate_availability: dict[str, Any], other_events: list[dict[str, Any]]) -> dict[str, Any]:
    """競合検知を行う。"""
    conflicts = []
    for event in other_events:
        for slot in candidate_availability.get("slots", []):
            if _overlaps(slot.get("start"), slot.get("end"), event.get("start"), event.get("end")):
                conflicts.append({
                    "event": event,
                    "slot": slot,
                })
    return {"conflicts": conflicts}


def _parse_date(value: str | date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(value).date()
    except Exception:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except Exception:
            return None


def _overlaps(a_start: str | None, a_end: str | None, b_start: str | None, b_end: str | None) -> bool:
    if not a_start or not a_end or not b_start or not b_end:
        return False
    try:
        a_s = datetime.fromisoformat(a_start)
        a_e = datetime.fromisoformat(a_end)
        b_s = datetime.fromisoformat(b_start)
        b_e = datetime.fromisoformat(b_end)
        return a_s < b_e and b_s < a_e
    except Exception:
        return False
