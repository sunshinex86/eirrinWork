"""市場データ分析 API ルート"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from typing import Optional

from fastapi import APIRouter, Query

from src.utils.market_analysis_service import (
    analyze_skill_supply_demand,
    analyze_tech_trend,
    analyze_unit_price_trend,
    default_date_range,
)

router = APIRouter(tags=["市場データ分析"])


@router.get("/market/skill-supply-demand")
def get_skill_supply_demand(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """スキル別の需要（案件掲載数）と供給（経歴書登録数）を比較する"""
    if not start_date or not end_date:
        default_start, default_end = default_date_range()
        start_date = start_date or default_start
        end_date = end_date or default_end
    return analyze_skill_supply_demand(start_date, end_date)


@router.get("/market/unit-price-trend")
def get_unit_price_trend(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    skill_id: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
):
    """月次の単価（万円/月）推移を集計する"""
    if not start_date or not end_date:
        default_start, default_end = default_date_range()
        start_date = start_date or default_start
        end_date = end_date or default_end
    return analyze_unit_price_trend(start_date, end_date, skill_id=skill_id, job_type=job_type)


@router.get("/market/tech-trend")
def get_tech_trend(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    top_n: int = Query(10),
):
    """月次のスキル出現頻度推移から上昇/下降トレンドを抽出する"""
    if not start_date or not end_date:
        default_start, default_end = default_date_range()
        start_date = start_date or default_start
        end_date = end_date or default_end
    return analyze_tech_trend(start_date, end_date, top_n=top_n)
