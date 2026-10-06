import json

import pytest

import src.utils.market_event_log as event_log
from src.utils.market_analysis_service import (
    analyze_skill_supply_demand,
    analyze_unit_price_trend,
    analyze_tech_trend,
)


@pytest.fixture
def isolated_events(tmp_path, monkeypatch):
    """イベントログを一時ファイルに分離する"""
    events_file = tmp_path / "events.jsonl"
    monkeypatch.setattr(event_log, "EVENTS_FILE", events_file)
    return events_file


def _job(entity_id, date, skill_ids, price_min, price_max, job_type="ITエンジニア"):
    return {
        "id": entity_id, "posted_date": date, "unit_price_min": price_min, "unit_price_max": price_max,
        "job_type": job_type, "industry": "IT・通信",
        "structured_required_skills": [{"skill_id": s} for s in skill_ids],
        "structured_preferred_skills": [],
    }


def _resume(entity_id, date, skill_ids):
    return {
        "id": entity_id, "registered_at": date,
        "structured_skills": [{"skill_id": s} for s in skill_ids],
    }


class TestSkillSupplyDemand:
    def test_scarce_skill_detected(self, isolated_events):
        event_log.record_job_posted(_job("j1", "2026-02-01", ["python"], 60, 80))
        event_log.record_job_posted(_job("j2", "2026-02-15", ["python"], 60, 80))
        event_log.record_resume_registered(_resume("r1", "2026-02-10", ["python"]))

        result = analyze_skill_supply_demand("2026-01-01", "2026-03-01")
        python_row = next(s for s in result["skills"] if s["skill_id"] == "python")
        assert python_row["demand_count"] == 2
        assert python_row["supply_count"] == 1
        assert python_row["status"] == "scarce"

    def test_out_of_range_events_excluded(self, isolated_events):
        event_log.record_job_posted(_job("j1", "2025-12-01", ["python"], 60, 80))
        result = analyze_skill_supply_demand("2026-01-01", "2026-03-01")
        assert result["skills"] == []
        assert result["insufficient_data"] is True

    def test_insufficient_data_flag(self, isolated_events):
        event_log.record_job_posted(_job("j1", "2026-02-01", ["python"], 60, 80))
        result = analyze_skill_supply_demand("2026-01-01", "2026-03-01")
        assert result["insufficient_data"] is True


class TestUnitPriceTrend:
    def test_monthly_average_and_growth_rate(self, isolated_events):
        event_log.record_job_posted(_job("j1", "2026-01-10", ["python"], 60, 80))
        event_log.record_job_posted(_job("j2", "2026-02-10", ["python"], 80, 100))

        result = analyze_unit_price_trend("2026-01-01", "2026-02-28")
        jan = next(m for m in result["monthly"] if m["month"] == "2026-01")
        feb = next(m for m in result["monthly"] if m["month"] == "2026-02")
        assert jan["avg_unit_price"] == 70.0
        assert feb["avg_unit_price"] == 90.0
        assert feb["mom_growth_rate"] == pytest.approx((90.0 - 70.0) / 70.0, abs=1e-4)

    def test_skill_filter(self, isolated_events):
        event_log.record_job_posted(_job("j1", "2026-01-10", ["python"], 60, 80))
        event_log.record_job_posted(_job("j2", "2026-01-15", ["java"], 100, 120))

        result = analyze_unit_price_trend("2026-01-01", "2026-01-31", skill_id="java")
        jan = next(m for m in result["monthly"] if m["month"] == "2026-01")
        assert jan["avg_unit_price"] == 110.0
        assert jan["sample_size"] == 1

    def test_empty_month_has_null_average(self, isolated_events):
        result = analyze_unit_price_trend("2026-01-01", "2026-01-31")
        jan = result["monthly"][0]
        assert jan["avg_unit_price"] is None
        assert jan["sample_size"] == 0


class TestTechTrend:
    def test_rising_skill_ranked_first(self, isolated_events):
        event_log.record_job_posted(_job("j1", "2026-01-05", ["python"], 60, 80))
        event_log.record_job_posted(_job("j2", "2026-04-05", ["python"], 60, 80))
        event_log.record_job_posted(_job("j3", "2026-05-05", ["python"], 60, 80))
        event_log.record_job_posted(_job("j4", "2026-06-05", ["python"], 60, 80))

        result = analyze_tech_trend("2026-01-01", "2026-06-30")
        assert result["rising"][0]["skill_id"] == "python"
        assert result["rising"][0]["growth_rate"] > 0

    def test_declining_skill_detected(self, isolated_events):
        event_log.record_job_posted(_job("j1", "2026-01-05", ["cobol"], 60, 80))
        event_log.record_job_posted(_job("j2", "2026-01-10", ["cobol"], 60, 80))
        event_log.record_job_posted(_job("j3", "2026-01-15", ["cobol"], 60, 80))

        result = analyze_tech_trend("2026-01-01", "2026-06-30")
        declining_ids = [t["skill_id"] for t in result["declining"]]
        assert "cobol" in declining_ids
