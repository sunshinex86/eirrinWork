"""市場データ分析 API のテスト"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from src.api.main import app


class TestMarketRoutes:
    """GET /api/market/* のテスト"""

    def setup_method(self):
        self.client = TestClient(app)

    def test_skill_supply_demand_default_range(self):
        """start_date/end_date省略時はデフォルト期間で応答すること"""
        resp = self.client.get("/api/market/skill-supply-demand")
        assert resp.status_code == 200
        data = resp.json()
        assert "start_date" in data
        assert "end_date" in data
        assert "insufficient_data" in data
        assert "skills" in data

    def test_skill_supply_demand_with_range(self):
        resp = self.client.get(
            "/api/market/skill-supply-demand",
            params={"start_date": "2026-01-01", "end_date": "2026-08-06"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["start_date"] == "2026-01-01"
        assert data["end_date"] == "2026-08-06"
        assert "skills" in data

    def test_unit_price_trend_default_range(self):
        resp = self.client.get("/api/market/unit-price-trend")
        assert resp.status_code == 200
        data = resp.json()
        assert "start_date" in data
        assert "end_date" in data
        assert "skill_id" in data
        assert "job_type" in data
        assert "insufficient_data" in data
        assert "monthly" in data

    def test_unit_price_trend_with_filters(self):
        resp = self.client.get(
            "/api/market/unit-price-trend",
            params={
                "start_date": "2026-01-01",
                "end_date": "2026-08-06",
                "skill_id": "python",
                "job_type": "SES",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["skill_id"] == "python"
        assert data["job_type"] == "SES"
        assert "monthly" in data

    def test_tech_trend_default_range(self):
        resp = self.client.get("/api/market/tech-trend")
        assert resp.status_code == 200
        data = resp.json()
        assert "start_date" in data
        assert "end_date" in data
        assert "insufficient_data" in data
        assert "rising" in data
        assert "declining" in data

    def test_tech_trend_with_top_n(self):
        resp = self.client.get(
            "/api/market/tech-trend",
            params={"start_date": "2026-01-01", "end_date": "2026-08-06", "top_n": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["rising"]) <= 5
        assert len(data["declining"]) <= 5
