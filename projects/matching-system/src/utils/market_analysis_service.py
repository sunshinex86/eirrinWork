"""市場データ分析サービス

REQ: 技能供給需要分析・単価トレンド分析・技術トレンド分析。
market_event_log（追記専用イベントログ）を集計する純粋関数群。
API/MCP/UI から共通で利用する（既存の *_service.py と同じ層構造）。
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from statistics import median
from typing import Any, Optional

from src.utils.market_event_log import read_events

MIN_SAMPLE_SIZE = 3  # これ未満は insufficient_data=True として扱う


def _in_range(event_date: str, start_date: str, end_date: str) -> bool:
    if not event_date:
        return False
    return start_date <= event_date <= end_date


def _month_of(event_date: str) -> str:
    """YYYY-MM-DD -> YYYY-MM"""
    return event_date[:7] if len(event_date) >= 7 else event_date


def _month_range(start_date: str, end_date: str) -> list[str]:
    start = datetime.fromisoformat(start_date).date().replace(day=1)
    end = datetime.fromisoformat(end_date).date().replace(day=1)
    months = []
    cur = start
    while cur <= end:
        months.append(cur.strftime("%Y-%m"))
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)
    return months


def default_date_range() -> tuple[str, str]:
    """デフォルト期間: 今年の1/1〜今日"""
    today = date.today()
    return f"{today.year}-01-01", today.isoformat()


def analyze_skill_supply_demand(start_date: str, end_date: str) -> dict[str, Any]:
    """スキル別の需要（案件掲載数）と供給（経歴書登録数）を比較する。

    需要・供給とも指定期間内に発生したイベントのみを対象とする
    （= 期間内に新規発生した需要シグナル vs 供給シグナルの比較）。

    Returns:
        {
          "start_date", "end_date", "insufficient_data",
          "skills": [
            {"skill_id", "demand_count", "supply_count", "ratio", "status"},
            ...
          ]  # ratio 降順。status は "scarce"(ratio>=2) / "balanced" / "surplus"(ratio<=0.5)
        }
    """
    job_events = [e for e in read_events("job_posted") if _in_range(e.get("date", ""), start_date, end_date)]
    resume_events = [e for e in read_events("resume_registered") if _in_range(e.get("date", ""), start_date, end_date)]

    demand: dict[str, int] = defaultdict(int)
    for e in job_events:
        for sid in e.get("skill_ids", []):
            demand[sid] += 1

    supply: dict[str, int] = defaultdict(int)
    for e in resume_events:
        for sid in e.get("skill_ids", []):
            supply[sid] += 1

    skill_ids = set(demand) | set(supply)
    skills = []
    for sid in skill_ids:
        d = demand.get(sid, 0)
        s = supply.get(sid, 0)
        if s == 0:
            ratio = float(d) if d > 0 else 0.0
        else:
            ratio = round(d / s, 2)
        if ratio >= 2.0:
            status = "scarce"
        elif ratio <= 0.5:
            status = "surplus"
        else:
            status = "balanced"
        skills.append({
            "skill_id": sid,
            "demand_count": d,
            "supply_count": s,
            "ratio": ratio,
            "status": status,
        })
    skills.sort(key=lambda x: x["ratio"], reverse=True)

    total_events = len(job_events) + len(resume_events)
    return {
        "start_date": start_date,
        "end_date": end_date,
        "insufficient_data": total_events < MIN_SAMPLE_SIZE,
        "skills": skills,
    }


def analyze_unit_price_trend(
    start_date: str,
    end_date: str,
    skill_id: Optional[str] = None,
    job_type: Optional[str] = None,
) -> dict[str, Any]:
    """月次の単価（万円/月）推移を集計する。

    案件の unit_price_min/unit_price_max の中央値を1件分の単価として扱い、
    月ごとに平均・中央値・サンプル数・前月比を算出する。

    Returns:
        {
          "start_date", "end_date", "skill_id", "job_type", "insufficient_data",
          "monthly": [
            {"month", "avg_unit_price", "median_unit_price", "sample_size", "mom_growth_rate"},
            ...
          ]  # month 昇順
        }
    """
    events = [e for e in read_events("job_posted") if _in_range(e.get("date", ""), start_date, end_date)]
    if skill_id:
        events = [e for e in events if skill_id in e.get("skill_ids", [])]
    if job_type:
        events = [e for e in events if e.get("job_type") == job_type]

    by_month: dict[str, list[float]] = defaultdict(list)
    for e in events:
        lo, hi = e.get("unit_price_min", 0), e.get("unit_price_max", 0)
        if lo == 0 and hi == 0:
            continue
        by_month[_month_of(e["date"])].append((lo + hi) / 2)

    months = _month_range(start_date, end_date)
    monthly = []
    prev_avg = None
    for m in months:
        prices = by_month.get(m, [])
        if not prices:
            monthly.append({
                "month": m, "avg_unit_price": None, "median_unit_price": None,
                "sample_size": 0, "mom_growth_rate": None,
            })
            prev_avg = None
            continue
        avg = round(sum(prices) / len(prices), 1)
        med = round(median(prices), 1)
        growth = round((avg - prev_avg) / prev_avg, 4) if prev_avg else None
        monthly.append({
            "month": m, "avg_unit_price": avg, "median_unit_price": med,
            "sample_size": len(prices), "mom_growth_rate": growth,
        })
        prev_avg = avg

    return {
        "start_date": start_date,
        "end_date": end_date,
        "skill_id": skill_id,
        "job_type": job_type,
        "insufficient_data": len(events) < MIN_SAMPLE_SIZE,
        "monthly": monthly,
    }


def analyze_tech_trend(start_date: str, end_date: str, top_n: int = 10) -> dict[str, Any]:
    """月次のスキル出現頻度推移から上昇/下降トレンドを抽出する（案件掲載ベース）。

    各スキルについて期間前半と後半の合計出現数を比較し、増加率でランキングする。

    Returns:
        {
          "start_date", "end_date", "insufficient_data",
          "rising": [{"skill_id", "growth_rate", "monthly_counts"}, ...],   # 増加率降順
          "declining": [{"skill_id", "growth_rate", "monthly_counts"}, ...], # 増加率昇順（負値）
        }
    """
    events = [e for e in read_events("job_posted") if _in_range(e.get("date", ""), start_date, end_date)]
    months = _month_range(start_date, end_date)

    counts: dict[str, dict[str, int]] = defaultdict(lambda: {m: 0 for m in months})
    for e in events:
        m = _month_of(e["date"])
        if m not in months:
            continue
        for sid in e.get("skill_ids", []):
            counts[sid][m] += 1

    mid = len(months) // 2
    first_half = months[:mid] if mid > 0 else months
    second_half = months[mid:] if mid > 0 else months

    trends = []
    for sid, monthly_counts in counts.items():
        total = sum(monthly_counts.values())
        if total == 0:
            continue
        first_sum = sum(monthly_counts[m] for m in first_half)
        second_sum = sum(monthly_counts[m] for m in second_half)
        if first_sum == 0:
            growth_rate = float(second_sum) if second_sum > 0 else 0.0
        else:
            growth_rate = round((second_sum - first_sum) / first_sum, 3)
        trends.append({
            "skill_id": sid,
            "growth_rate": growth_rate,
            "monthly_counts": monthly_counts,
        })

    rising = sorted([t for t in trends if t["growth_rate"] > 0], key=lambda x: x["growth_rate"], reverse=True)[:top_n]
    declining = sorted([t for t in trends if t["growth_rate"] < 0], key=lambda x: x["growth_rate"])[:top_n]

    return {
        "start_date": start_date,
        "end_date": end_date,
        "insufficient_data": len(events) < MIN_SAMPLE_SIZE,
        "rising": rising,
        "declining": declining,
    }
