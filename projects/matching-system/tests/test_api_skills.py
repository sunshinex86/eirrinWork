"""スキル抽出APIのテスト（REQ-FIX-06）"""
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from src.api.main import app


class TestSkillsExtract:
    """POST /api/skills/extract のテスト"""

    def setup_method(self):
        self.client = TestClient(app)


class TestRecommendationAndJdFeatures:
    """新規の推薦理由分解 / JD最適化 APIテスト"""

    def setup_method(self):
        self.client = TestClient(app)

    def test_recommendation_reason_endpoint(self):
        """推薦理由分解とギャップ分析を返すこと"""
        resp = self.client.post("/api/skills/recommendation/reason", json={
            "resume_id": "resume-001",
            "job_id": "job-001"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "skill_matches" in data
        assert "industry_matches" in data
        assert "experience_matches" in data
        assert "gap_analysis" in data

    def test_jd_optimization_endpoint(self):
        """JD最適化・スキル抽出・予算妥当性分析を返すこと"""
        resp = self.client.post("/api/skills/jd/optimize", json={
            "raw_jd": "Python, Django, SQL, 5年経験, 800万円"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "optimized_jd" in data
        assert "extracted_skills" in data
        assert "normalized_skills" in data
        assert "budget_assessment" in data

    def test_extract_known_skill(self):
        """既知スキルの抽出"""
        resp = self.client.post("/api/skills/extract", json={
            "text": "PythonとDjangoを使った開発",
            "use_rag": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["skills"]) > 0
        ids = [s["skill_id"] for s in data["skills"]]
        assert "python" in ids or "django" in ids

    def test_extract_returns_confidence(self):
        """confidence/registered/source が返されること"""
        resp = self.client.post("/api/skills/extract", json={
            "text": "Java",
            "use_rag": False,
        })
        data = resp.json()
        for s in data["skills"]:
            assert "confidence" in s
            assert "registered" in s
            assert "source" in s
            assert 0.0 <= s["confidence"] <= 1.0

    def test_extract_rag_disabled_by_default(self):
        """デフォルトでRAG無効"""
        resp = self.client.post("/api/skills/extract", json={"text": "Python"})
        assert resp.status_code == 200
        data = resp.json()
        assert "rag_sources" in data

    def test_invalid_input_rejected(self):
        """空テキストはエラー"""
        resp = self.client.post("/api/skills/extract", json={"text": ""})
        assert resp.status_code == 422
