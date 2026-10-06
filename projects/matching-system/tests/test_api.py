"""FastAPIエンドポイントの統合テスト"""
import json
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from src.api.main import app


class TestAPI:
    """APIエンドポイントのテスト"""

    @pytest.fixture(autouse=True)
    def setup_data(self, sample_resume, sample_job, isolated_api_storage, check_production_files_unchanged):
        """テスト用のデータとファイルを準備（一時JSON＋分離ストレージ、REQ-RE5-07）"""
        self.sample_resume = sample_resume
        self.sample_job = sample_job
        self.client = TestClient(app)


    # --- ヘルスチェック ---

    def test_health_check(self):
        response = self.client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "matching-system"

    # --- 経歴書 CRUD ---

    def test_create_resume(self):
        response = self.client.post("/api/resumes", json=self.sample_resume)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "resume-001"
        assert data["name"] == "田中 太郎"

    def test_create_resume_duplicate(self):
        self.client.post("/api/resumes", json=self.sample_resume)
        response = self.client.post("/api/resumes", json=self.sample_resume)
        assert response.status_code == 409

    def test_create_resume_missing_id(self):
        response = self.client.post("/api/resumes", json={"name": "No ID"})
        assert response.status_code == 400

    def test_list_resumes(self):
        self.client.post("/api/resumes", json=self.sample_resume)
        response = self.client.get("/api/resumes")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_list_resumes_filter_by_skills(self):
        self.client.post("/api/resumes", json=self.sample_resume)
        response = self.client.get("/api/resumes?skills=Python,Django")
        assert response.status_code == 200
        assert len(response.json()) == 1
        response = self.client.get("/api/resumes?skills=Ruby")
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_get_resume(self):
        self.client.post("/api/resumes", json=self.sample_resume)
        response = self.client.get("/api/resumes/resume-001")
        assert response.status_code == 200
        assert response.json()["name"] == "田中 太郎"

    def test_get_resume_not_found(self):
        response = self.client.get("/api/resumes/non-existent")
        assert response.status_code == 404

    def test_update_resume(self):
        self.client.post("/api/resumes", json=self.sample_resume)
        updated = dict(self.sample_resume)
        updated["name"] = "田中 更新"
        response = self.client.put("/api/resumes/resume-001", json=updated)
        assert response.status_code == 200
        assert response.json()["name"] == "田中 更新"

    def test_update_resume_not_found(self):
        response = self.client.put("/api/resumes/non-existent", json=self.sample_resume)
        assert response.status_code == 404

    def test_delete_resume(self):
        self.client.post("/api/resumes", json=self.sample_resume)
        response = self.client.delete("/api/resumes/resume-001")
        assert response.status_code == 204
        response = self.client.get("/api/resumes/resume-001")
        assert response.status_code == 404

    def test_delete_resume_not_found(self):
        response = self.client.delete("/api/resumes/non-existent")
        assert response.status_code == 404

    # --- 案件 CRUD ---

    def test_create_job(self):
        response = self.client.post("/api/jobs", json=self.sample_job)
        assert response.status_code == 201
        assert response.json()["title"] == "Pythonバックエンドエンジニア"

    def test_create_job_duplicate(self):
        self.client.post("/api/jobs", json=self.sample_job)
        response = self.client.post("/api/jobs", json=self.sample_job)
        assert response.status_code == 409

    def test_list_jobs(self):
        self.client.post("/api/jobs", json=self.sample_job)
        response = self.client.get("/api/jobs")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_list_jobs_filter_by_skills(self):
        self.client.post("/api/jobs", json=self.sample_job)
        response = self.client.get("/api/jobs?skills=Python")
        assert response.status_code == 200
        assert len(response.json()) == 1
        response = self.client.get("/api/jobs?skills=Ruby")
        assert len(response.json()) == 0

    def test_get_job(self):
        self.client.post("/api/jobs", json=self.sample_job)
        response = self.client.get("/api/jobs/job-001")
        assert response.status_code == 200

    def test_get_job_not_found(self):
        response = self.client.get("/api/jobs/non-existent")
        assert response.status_code == 404

    def test_update_job(self):
        self.client.post("/api/jobs", json=self.sample_job)
        updated = dict(self.sample_job)
        updated["title"] = "更新案件"
        response = self.client.put("/api/jobs/job-001", json=updated)
        assert response.status_code == 200
        assert response.json()["title"] == "更新案件"

    def test_update_job_not_found(self):
        response = self.client.put("/api/jobs/non-existent", json=self.sample_job)
        assert response.status_code == 404

    def test_delete_job(self):
        self.client.post("/api/jobs", json=self.sample_job)
        response = self.client.delete("/api/jobs/job-001")
        assert response.status_code == 204

    def test_delete_job_not_found(self):
        response = self.client.delete("/api/jobs/non-existent")
        assert response.status_code == 404

    # --- マッチング API ---

    @patch("src.matching.embedding_matcher.embedding_available", return_value=False)
    def test_match_resume_to_jobs(self, mock_avail):
        self.client.post("/api/resumes", json=self.sample_resume)
        self.client.post("/api/jobs", json=self.sample_job)
        response = self.client.post("/api/match/resume-to-jobs/resume-001")
        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == "resume-001"
        assert data["source_type"] == "resume"
        assert len(data["matches"]) == 1

    def test_match_resume_to_jobs_not_found(self):
        response = self.client.post("/api/match/resume-to-jobs/non-existent")
        assert response.status_code == 404

    @patch("src.matching.embedding_matcher.embedding_available", return_value=False)
    def test_match_job_to_resumes(self, mock_avail):
        self.client.post("/api/resumes", json=self.sample_resume)
        self.client.post("/api/jobs", json=self.sample_job)
        response = self.client.post("/api/match/job-to-resumes/job-001")
        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == "job-001"
        assert data["source_type"] == "job"
        assert len(data["matches"]) == 1

    def test_match_job_to_resumes_not_found(self):
        response = self.client.post("/api/match/job-to-resumes/non-existent")
        assert response.status_code == 404

    def test_match_status(self):
        self.client.post("/api/resumes", json=self.sample_resume)
        self.client.post("/api/jobs", json=self.sample_job)
        response = self.client.get("/api/match/status")
        assert response.status_code == 200
        data = response.json()
        assert data["resume_count"] >= 1
        assert data["job_count"] >= 1
        assert "semantic_matching_enabled" in data
        assert "weights" in data

    def test_semantic_match_endpoint(self):
        """AIマッチングエンドポイント（APIキーなし）"""
        self.client.post("/api/resumes", json=self.sample_resume)
        self.client.post("/api/jobs", json=self.sample_job)
        response = self.client.post("/api/match/semantic", json={
            "resume_id": "resume-001",
            "job_id": "job-001",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 0.0
        assert "CLAUDE_API_KEY" in data["error"]

    # --- ハイブリッドマッチング API（10軸統合） ---

    @patch("src.matching.embedding_matcher.embedding_available", return_value=False)
    def test_hybrid_match_resume_to_jobs(self, mock_available):
        """ハイブリッドマッチング: 経歴書→案件"""
        self.client.post("/api/resumes", json=self.sample_resume)
        self.client.post("/api/jobs", json=self.sample_job)
        response = self.client.post("/api/match/hybrid/resume-to-jobs/resume-001")
        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == "resume-001"
        assert data["source_type"] == "resume"
        assert len(data["matches"]) == 1
        match = data["matches"][0]
        assert match["mode"] in ("hybrid", "hybrid_degraded")
        assert "degraded" in match
        assert match["hybrid_breakdown"] is not None
        assert 0.0 <= match["total_score"] <= 1.0

    def test_hybrid_match_not_found(self):
        """ハイブリッドマッチング: 存在しないID"""
        response = self.client.post("/api/match/hybrid/resume-to-jobs/non-existent")
        assert response.status_code == 404

    @patch("src.matching.embedding_matcher.embedding_available", return_value=False)
    def test_hybrid_match_job_to_resumes(self, mock_available):
        """ハイブリッドマッチング: 案件→経歴書"""
        self.client.post("/api/resumes", json=self.sample_resume)
        self.client.post("/api/jobs", json=self.sample_job)
        response = self.client.post("/api/match/hybrid/job-to-resumes/job-001")
        assert response.status_code == 200
        data = response.json()
        assert data["source_id"] == "job-001"
        assert data["source_type"] == "job"
        assert len(data["matches"]) == 1
        match = data["matches"][0]
        assert match["target_name"] == "田中 太郎"

    @patch("src.utils.vector_utils.is_available", return_value=False)
    def test_hybrid_match_status(self, mock_available):
        """ハイブリッドマッチングステータス"""
        response = self.client.get("/api/match/hybrid/status")
        assert response.status_code == 200
        data = response.json()
        assert "hybrid_matching_enabled" in data
        assert "degraded_mode" in data
        assert "weights" in data


class TestP1Validation:
    """P1: CRUD Core — Pydantic検証・同義語解決・統一エラーレスポンスのテスト"""

    @pytest.fixture(autouse=True)
    def setup_data(self, sample_resume, sample_job, isolated_api_storage, check_production_files_unchanged):
        self.sample_resume = sample_resume
        self.sample_job = sample_job
        self.client = TestClient(app)

    # --- 同義語解決（REQ-RE3-01） ---

    def test_create_resume_synonym_normalization(self):
        """同義語ID（JS→javascript）が保存時に正規化される"""
        data = dict(self.sample_resume)
        data["id"] = "synonym-test-1"
        data["structured_skills"] = [{"skill_id": "JS", "level": 3, "years": 5}]
        resp = self.client.post("/api/resumes", json=data)
        assert resp.status_code == 201
        # 保存されたデータを確認
        resp2 = self.client.get("/api/resumes/synonym-test-1")
        saved = resp2.json()
        saved_ids = [s["skill_id"] for s in saved.get("structured_skills", [])]
        assert "javascript" in saved_ids, f"JSがjavascriptに正規化されていません: {saved_ids}"
        assert "JS" not in saved_ids, f"JSがそのまま保存されています: {saved_ids}"

    def test_create_job_synonym_normalization(self):
        """案件の同義語ID（TS→typescript, k8s→kubernetes）が保存時に正規化される"""
        data = dict(self.sample_job)
        data["id"] = "job-synonym-1"
        data["structured_required_skills"] = [{"skill_id": "TS", "required_level": 3, "required_years": 3}]
        data["structured_preferred_skills"] = [{"skill_id": "k8s", "required_level": 2, "required_years": 1}]
        resp = self.client.post("/api/jobs", json=data)
        assert resp.status_code == 201
        resp2 = self.client.get("/api/jobs/job-synonym-1")
        saved = resp2.json()
        req_ids = [s["skill_id"] for s in saved.get("structured_required_skills", [])]
        pref_ids = [s["skill_id"] for s in saved.get("structured_preferred_skills", [])]
        assert "typescript" in req_ids, f"TSがtypescriptに正規化されていません: {req_ids}"
        assert "kubernetes" in pref_ids, f"k8sがkubernetesに正規化されていません: {pref_ids}"

    def test_update_resume_synonym_normalization(self):
        """更新時も同義語解決が機能する"""
        self.client.post("/api/resumes", json=self.sample_resume)
        update_data = {"id": "resume-001", "name": "更新 太郎", "age": 35,
                       "structured_skills": [{"skill_id": "Golang", "level": 4, "years": 3}]}
        resp = self.client.put("/api/resumes/resume-001", json=update_data)
        assert resp.status_code == 200
        resp2 = self.client.get("/api/resumes/resume-001")
        saved = resp2.json()
        saved_ids = [s["skill_id"] for s in saved.get("structured_skills", [])]
        assert "go" in saved_ids, f"Golangがgoに正規化されていません: {saved_ids}"

    # --- Pydantic検証エラー（REQ-RE3-02） ---

    def test_create_resume_age_out_of_range(self):
        """数値範囲超過→HTTP 400 + VALIDATION_ERROR"""
        data = dict(self.sample_resume)
        data["id"] = "age-error"
        data["age"] = 200
        resp = self.client.post("/api/resumes", json=data)
        assert resp.status_code == 400
        detail = resp.json().get("detail", {})
        assert detail.get("code") == "VALIDATION_ERROR"
        assert len(detail.get("errors", [])) > 0
        # ageフィールドのエラーが含まれる
        fields = [e.get("field") for e in detail["errors"]]
        assert any("age" in f for f in fields), f"ageエラーが見つかりません: {fields}"

    def test_create_resume_empty_id(self):
        """空ID→HTTP 400 + VALIDATION_ERROR"""
        data = dict(self.sample_resume)
        data["id"] = ""
        resp = self.client.post("/api/resumes", json=data)
        assert resp.status_code == 400
        detail = resp.json().get("detail", {})
        assert detail.get("code") == "VALIDATION_ERROR"

    def test_create_resume_blank_name(self):
        """空白のみの名前→HTTP 400"""
        data = dict(self.sample_resume)
        data["id"] = "blank-name"
        data["name"] = "   "
        resp = self.client.post("/api/resumes", json=data)
        assert resp.status_code == 400

    def test_create_job_empty_id(self):
        """案件の空ID→HTTP 400"""
        data = dict(self.sample_job)
        data["id"] = ""
        resp = self.client.post("/api/jobs", json=data)
        assert resp.status_code == 400
        detail = resp.json().get("detail", {})
        assert detail.get("code") == "VALIDATION_ERROR"

    def test_create_job_empty_title(self):
        """案件の空title→HTTP 400"""
        data = dict(self.sample_job)
        data["id"] = "empty-title"
        data["title"] = ""
        resp = self.client.post("/api/jobs", json=data)
        assert resp.status_code == 400

    # --- 未登録スキルID（REQ-RE3-01/02） ---

    def test_create_resume_unknown_skill_id(self):
        """未登録skill_id→201 + pending_skills（structured_skillsから除去）"""
        data = dict(self.sample_resume)
        data["id"] = "unknown-skill"
        data["structured_skills"] = [{"skill_id": "NONEXISTENT_SKILL", "level": 3, "years": 1}]
        resp = self.client.post("/api/resumes", json=data)
        assert resp.status_code == 201
        body = resp.json()
        # structured_skillsから除去されている
        assert all(s["skill_id"] != "NONEXISTENT_SKILL" for s in body.get("structured_skills", []))
        # pending_skillsに移されている
        pending = body.get("pending_skills", [])
        assert len(pending) >= 1
        assert pending[0]["raw_name"] == "NONEXISTENT_SKILL"
        assert pending[0]["status"] == "pending"
        assert pending[0]["owner_type"] == "resume"
        assert pending[0]["owner_id"] == "unknown-skill"
        assert pending[0]["level"] == 3
        assert pending[0]["years"] == 1
        # warningsが含まれる
        assert "warnings" in body
        assert body["warnings"][0]["code"] == "SKILL_NOT_REGISTERED"

    def test_create_resume_old_format_unresolved_skill(self):
        """旧形式スキルに未登録名 → pending保存（structured_skillsには含まれない）"""
        data = dict(self.sample_resume)
        data["id"] = "old-format-pending"
        data.pop("structured_skills", None)
        data["skills"] = {"languages": ["Python", "TotallyUnknownLang"], "frameworks": []}
        resp = self.client.post("/api/resumes", json=data)
        assert resp.status_code == 201
        body = resp.json()
        assert "pending_skills" in body
        assert any(p["raw_name"] == "TotallyUnknownLang" for p in body["pending_skills"])

    def test_create_job_structured_unresolved_skill(self):
        """Job structured_required_skills未登録 → pending保存 + warnings + usage_type=required"""
        data = dict(self.sample_job)
        data["id"] = "job-pending-req"
        data["structured_required_skills"] = [{"skill_id": "UNKNOWN_SKILL_REQ", "required_level": 3, "required_years": 2}]
        data["structured_preferred_skills"] = []
        resp = self.client.post("/api/jobs", json=data)
        assert resp.status_code == 201
        body = resp.json()
        assert all(s["skill_id"] != "UNKNOWN_SKILL_REQ" for s in body.get("structured_required_skills", []))
        pending = body.get("pending_skills", [])
        assert len(pending) >= 1
        assert pending[0]["raw_name"] == "UNKNOWN_SKILL_REQ"
        assert pending[0]["usage_type"] == "required"
        assert pending[0]["required_level"] == 3
        assert pending[0]["required_years"] == 2
        assert "warnings" in body

    def test_create_job_structured_preferred_unresolved(self):
        """Job structured_preferred_skills未登録 → usage_type=preferred"""
        data = dict(self.sample_job)
        data["id"] = "job-pending-pref"
        data["structured_required_skills"] = []
        data["structured_preferred_skills"] = [{"skill_id": "UNKNOWN_PREF", "required_level": 2, "required_years": 1}]
        resp = self.client.post("/api/jobs", json=data)
        assert resp.status_code == 201
        body = resp.json()
        pending = body.get("pending_skills", [])
        assert len(pending) >= 1
        assert pending[0]["usage_type"] == "preferred"

    def test_update_resume_pending_skills(self):
        """Resume更新時も未登録→pending保存 + warnings"""
        # 先に作成
        data = dict(self.sample_resume)
        data["id"] = "update-pending-test"
        self.client.post("/api/resumes", json=data)
        # 更新（未登録ID追加）
        update = dict(data)
        update["structured_skills"] = [{"skill_id": "NEW_UNKNOWN", "level": 2, "years": 3}]
        resp = self.client.put(f"/api/resumes/{data['id']}", json=update)
        assert resp.status_code == 200
        body = resp.json()
        pending = body.get("pending_skills", [])
        assert len(pending) >= 1
        assert pending[0]["raw_name"] == "NEW_UNKNOWN"
        assert "warnings" in body

    def test_owner_type_and_id_correct(self):
        """pending_skillsのowner_type/owner_idが保存元を正しく示す"""
        data = dict(self.sample_resume)
        data["id"] = "owner-check"
        data["structured_skills"] = [{"skill_id": "UNKNOWN_OWNER", "level": 1, "years": 1}]
        resp = self.client.post("/api/resumes", json=data)
        body = resp.json()
        p = body["pending_skills"][0]
        assert p["owner_type"] == "resume"
        assert p["owner_id"] == "owner-check"

    def test_level_years_preserved_in_pending(self):
        """structured_skillsのレベル・年数がpendingに保持される"""
        data = dict(self.sample_resume)
        data["id"] = "level-years-pending"
        data["structured_skills"] = [{"skill_id": "UNKNOWN_LVL", "level": 5, "years": 10, "last_used_year": 2025}]
        resp = self.client.post("/api/resumes", json=data)
        body = resp.json()
        p = body["pending_skills"][0]
        assert p["level"] == 5
        assert p["years"] == 10
        assert p["last_used_year"] == 2025

    def test_pending_skills_persisted_after_create(self):
        """未登録スキルを含むResume作成後、GETでpending_skillsが永続化されていることを確認"""
        data = dict(self.sample_resume)
        data["id"] = "pending-persist-test"
        data["structured_skills"] = [
            {"skill_id": "PYTHON_SKILL", "level": 3, "years": 5},
            {"skill_id": "UNREGISTERED_DB", "level": 2, "years": 3},
        ]
        create_resp = self.client.post("/api/resumes", json=data)
        assert create_resp.status_code == 201
        create_body = create_resp.json()
        assert "pending_skills" in create_body
        assert any(p["raw_name"] == "UNREGISTERED_DB" for p in create_body["pending_skills"])

        # GETで永続化確認
        get_resp = self.client.get("/api/resumes/pending-persist-test")
        assert get_resp.status_code == 200
        get_body = get_resp.json()
        assert "pending_skills" in get_body
        assert any(p["raw_name"] == "UNREGISTERED_DB" and p["status"] == "pending"
                   for p in get_body["pending_skills"])

    def test_sample_load_pending_persisted(self, tmp_path, isolated_api_storage):
        """サンプル一括読込→未登録スキルがpending_skillsとして保存されることを確認"""
        import json
        # isolated_api_storage が使用する一時JSONパスをconfigに反映
        storage = isolated_api_storage
        with patch.object(config, 'RESUMES_FILE', str(storage["resume_file"])):
            with patch.object(config, 'JOBS_FILE', str(storage["job_file"])):

                # 未登録スキルを含むサンプルデータを一時ファイルに作成（旧形式）
                sample = [{
                    "id": "pend-load-test-001",
                    "name": "サンプル pending",
                    "age": 30,
                    "skills": {"languages": ["Python"], "other": ["ZZZ_UNREGISTERED_X1"]},
                    "work_history": [], "years_of_experience": 5,
                    "location": "東京", "desired_locations": [],
                }]
                sample_file = tmp_path / "test_samples.json"
                sample_file.write_text(json.dumps(sample, ensure_ascii=False), encoding="utf-8")

                with patch.object(config, 'ENABLE_SAMPLE_LOAD', True):
                    with patch.object(config, 'SAMPLE_RESUMES_FILE', str(sample_file)):
                        load_resp = self.client.post("/api/resumes/load-samples")
        assert load_resp.status_code == 200
        load_body = load_resp.json()
        assert load_body.get("committed") is True
        unreg = load_body.get("unresolved_skills", [])
        assert len(unreg) >= 1, f"未登録スキルが検出されませんでした: {load_body}"
        assert any(u["raw_value"] == "ZZZ_UNREGISTERED_X1" for u in unreg)

        # GETで永続化確認
        with patch.object(config, 'RESUMES_FILE', str(storage["resume_file"])):
            get_resp = self.client.get("/api/resumes/pend-load-test-001")
        assert get_resp.status_code == 200
        get_body = get_resp.json()
        assert "pending_skills" in get_body
        assert any(
            p["raw_name"] == "ZZZ_UNREGISTERED_X1" and p["status"] == "pending"
            for p in get_body["pending_skills"]
        )
        # structured_skillsに未登録スキルが含まれていないこと
        pending_names = [p["raw_name"] for p in get_body.get("pending_skills", [])]
        for s in get_body.get("structured_skills", []):
            assert s.get("skill_id", "") not in pending_names

    def test_invalid_owner_type_rejected(self):
        """不正なowner_type→ValidationError"""
        from src.models.resume import PendingSkill
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PendingSkill(pending_id="p1", owner_type="invalid", owner_id="o1",
                         raw_name="test", usage_type="resume")

    def test_invalid_usage_type_rejected(self):
        """不正なusage_type→ValidationError"""
        from src.models.resume import PendingSkill
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PendingSkill(pending_id="p1", owner_type="resume", owner_id="o1",
                         raw_name="test", usage_type="not_valid")

    def test_invalid_status_rejected(self):
        """不正なstatus→ValidationError"""
        from src.models.resume import PendingSkill
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PendingSkill(pending_id="p1", owner_type="resume", owner_id="o1",
                         raw_name="test", usage_type="resume", status="invalid_status")

    def test_update_keeps_existing_pending(self):
        """更新時に既存pendingが保持される（新規pendingとマージ）"""
        # 作成: 未登録スキルA
        data = dict(self.sample_resume)
        data["id"] = "merge-pending-test"
        data["structured_skills"] = [{"skill_id": "PENDING_A", "level": 2, "years": 1}]
        resp = self.client.post("/api/resumes", json=data).json()
        pending_a_id = resp["pending_skills"][0]["pending_id"]

        # 更新: 未登録スキルBを追加
        update = dict(self.sample_resume)
        update["structured_skills"] = [
            {"skill_id": "PENDING_A", "level": 2, "years": 1},
            {"skill_id": "PENDING_B", "level": 3, "years": 2},
        ]
        resp2 = self.client.put("/api/resumes/merge-pending-test", json=update).json()
        pendings = resp2.get("pending_skills", [])
        raw_names = {p["raw_name"] for p in pendings}
        assert "PENDING_A" in raw_names, "既存pendingが消失"
        assert "PENDING_B" in raw_names, "新規pendingが保存されていない"

    def test_update_without_pending_preserves_existing(self):
        """pendingをリクエストから省略して更新 → 既存pending保持"""
        data = dict(self.sample_resume)
        data["id"] = "omit-pending-test"
        data["structured_skills"] = [{"skill_id": "PENDING_OMIT", "level": 1, "years": 1}]
        self.client.post("/api/resumes", json=data)

        # pendingを含めず更新
        update = dict(self.sample_resume)
        update["id"] = "omit-pending-test"
        resp = self.client.put("/api/resumes/omit-pending-test", json=update).json()
        pendings = resp.get("pending_skills", [])
        assert any(p["raw_name"] == "PENDING_OMIT" for p in pendings), "pending省略で既存pending消失"

    def test_job_update_keeps_existing_pending(self):
        """Job更新時も既存pendingが保持される"""
        data = dict(self.sample_job)
        data["id"] = "job-merge-pending"
        data["structured_required_skills"] = [{"skill_id": "JOB_PEND_A", "required_level": 3, "required_years": 2}]
        data["structured_preferred_skills"] = []
        self.client.post("/api/jobs", json=data)

        update = dict(data)
        update["structured_required_skills"] = [
            {"skill_id": "JOB_PEND_A", "required_level": 3, "required_years": 2},
            {"skill_id": "JOB_PEND_B", "required_level": 2, "required_years": 1},
        ]
        resp = self.client.put("/api/jobs/job-merge-pending", json=update).json()
        names = {p["raw_name"] for p in resp.get("pending_skills", [])}
        assert "JOB_PEND_A" in names
        assert "JOB_PEND_B" in names

    def test_sample_load_response_structure(self):
        """サンプル読込レスポンスの構造を確認"""
        with patch.object(config, 'ENABLE_SAMPLE_LOAD', True):
            resp = self.client.post("/api/resumes/load-samples")
        body = resp.json()
        assert "unresolved_skills" in body
        assert isinstance(body.get("unresolved_skills"), list)
        assert body.get("committed") is True
        # unresolved_skillsがあれば構造検証
        for us in body.get("unresolved_skills", []):
            assert "field" in us and "raw_value" in us and "reason" in us
            assert "record_id" in us

    # --- P5: Pending変換API ---

    def test_pending_register_resume(self, isolated_api_storage, isolated_skill_dictionary):
        """保留スキルを新規登録→辞書追加＋pending+structured更新"""
        import uuid
        unreg_name = f"ZZZ_UNREG_{uuid.uuid4().hex[:8]}"
        storage = isolated_api_storage
        data = dict(self.sample_resume)
        data["id"] = "p5-reg-test"
        data["structured_skills"] = [{"skill_id": unreg_name, "level": 2, "years": 1}]
        resp = self.client.post("/api/resumes", json=data)
        assert resp.status_code == 201
        body = resp.json()
        pid = body["pending_skills"][0]["pending_id"]
        with patch.object(config, 'RESUMES_FILE', str(storage["resume_file"])):
            reg = self.client.post(f"/api/resumes/p5-reg-test/pending-skills/{pid}/register")
        assert reg.status_code == 200
        reg_body = reg.json()
        assert reg_body["status"] == "registered"
        assert isinstance(reg_body["registered_skill_id"], str)

    def test_pending_link_resume(self, isolated_api_storage, isolated_skill_dictionary):
        """保留スキルを既存スキルに紐付け"""
        import uuid
        unreg_name = f"ZZZ_UNREG_{uuid.uuid4().hex[:8]}"
        storage = isolated_api_storage
        data = dict(self.sample_resume)
        data["id"] = "p5-link-test"
        data["structured_skills"] = [{"skill_id": unreg_name, "level": 3, "years": 5}]
        resp = self.client.post("/api/resumes", json=data).json()
        pid = resp["pending_skills"][0]["pending_id"]
        with patch.object(config, 'RESUMES_FILE', str(storage["resume_file"])):
            reg = self.client.post(f"/api/resumes/p5-link-test/pending-skills/{pid}/register").json()
        assert isinstance(reg["registered_skill_id"], str)
        linked_skill_id = reg["registered_skill_id"]
        # 別のpendingを作成→link APIで紐付け
        data2 = dict(self.sample_resume)
        data2["id"] = "p5-link-test"
        data2["structured_skills"] = [
            {"skill_id": unreg_name, "level": 3, "years": 5},
            {"skill_id": f"ZZZ_UNREG2_{uuid.uuid4().hex[:8]}", "level": 2, "years": 2},
        ]
        resp2 = self.client.put("/api/resumes/p5-link-test", json=data2).json()
        pid2 = [p["pending_id"] for p in resp2.get("pending_skills", [])
                if p["raw_name"] != unreg_name][0]
        with patch.object(config, 'RESUMES_FILE', str(storage["resume_file"])):
            link = self.client.post(f"/api/resumes/p5-link-test/pending-skills/{pid2}/link",
                                    json={"skill_id": linked_skill_id}).json()
        assert link["status"] == "registered"
        assert link["linked_skill_id"] == linked_skill_id

    def test_pending_ignore_resume(self, isolated_api_storage, isolated_skill_dictionary):
        """保留スキルを無視→status=ignored"""
        import uuid
        unreg_name = f"ZZZ_UNREG_{uuid.uuid4().hex[:8]}"
        storage = isolated_api_storage
        data = dict(self.sample_resume)
        data["id"] = "p5-ign-test"
        data["structured_skills"] = [{"skill_id": unreg_name, "level": 1, "years": 1}]
        resp = self.client.post("/api/resumes", json=data)
        pid = resp.json()["pending_skills"][0]["pending_id"]
        with patch.object(config, 'RESUMES_FILE', str(storage["resume_file"])):
            ign = self.client.post(f"/api/resumes/p5-ign-test/pending-skills/{pid}/ignore")
        assert ign.status_code == 200
        assert ign.json()["status"] == "ignored"

    def test_pending_register_job(self, isolated_api_storage, isolated_skill_dictionary):
        """Job保留スキル新規登録"""
        import uuid
        unreg_name = f"ZZZ_UNREG_{uuid.uuid4().hex[:8]}"
        storage = isolated_api_storage
        data = dict(self.sample_job)
        data["id"] = "p5-job-reg"
        data["structured_required_skills"] = [{"skill_id": unreg_name, "required_level": 3, "required_years": 2}]
        data["structured_preferred_skills"] = []
        resp = self.client.post("/api/jobs", json=data)
        assert resp.status_code == 201
        pending = resp.json().get("pending_skills", [])
        assert len(pending) >= 1
        pid = pending[0]["pending_id"]
        with patch.object(config, 'JOBS_FILE', str(storage["job_file"])):
            reg = self.client.post(f"/api/jobs/p5-job-reg/pending-skills/{pid}/register")
        assert reg.status_code == 200

    def test_skill_management_api(self, isolated_skill_dictionary):
        """スキル管理API CRUD"""
        import uuid
        skill_name = f"P5TestSkill_{uuid.uuid4().hex[:8]}"
        # create
        resp = self.client.post("/api/skills", json={"name": skill_name, "category": "test"})
        assert resp.status_code == 201
        sid = resp.json()["id"]
        # list
        lst = self.client.get("/api/skills").json()
        assert any(s["id"] == sid for s in lst["skills"])
        # similar
        sim = self.client.get("/api/skills/similar", params={"name": skill_name}).json()
        assert len(sim["results"]) >= 1
        # tree
        tree = self.client.get(f"/api/skills/{sid}/tree").json()
        assert "path" in tree
        # references
        refs = self.client.get(f"/api/skills/{sid}/references").json()
        assert "resumes" in refs and "jobs" in refs
        # delete
        resp = self.client.delete(f"/api/skills/{sid}")
        assert resp.status_code == 200
        # validate
        val = self.client.post("/api/skills/validate").json()
        assert "valid" in val

    def test_job_pending_link_and_ignore(self, isolated_api_storage, isolated_skill_dictionary):
        """Job pending link/ignore"""
        import uuid
        unreg_a = f"ZZZ_UNREG_{uuid.uuid4().hex[:8]}"
        unreg_b = f"ZZZ_UNREG_{uuid.uuid4().hex[:8]}"
        unreg_c = f"ZZZ_UNREG_{uuid.uuid4().hex[:8]}"
        storage = isolated_api_storage
        data = dict(self.sample_job)
        data["id"] = "p5-job-link-ign"
        data["structured_required_skills"] = [{"skill_id": unreg_a, "required_level": 3, "required_years": 2}]
        data["structured_preferred_skills"] = [{"skill_id": unreg_b, "required_level": 2, "required_years": 1},
                                                  {"skill_id": unreg_c, "required_level": 1, "required_years": 1}]
        resp = self.client.post("/api/jobs", json=data).json()
        pid_a = [p["pending_id"] for p in resp["pending_skills"] if p["raw_name"] == unreg_a][0]
        pid_b = [p["pending_id"] for p in resp["pending_skills"] if p["raw_name"] == unreg_b][0]
        pid_c = [p["pending_id"] for p in resp["pending_skills"] if p["raw_name"] == unreg_c][0]
        with patch.object(config, 'JOBS_FILE', str(storage["job_file"])):
            # register A → 辞書に追加
            reg = self.client.post(f"/api/jobs/p5-job-link-ign/pending-skills/{pid_a}/register").json()
            skill_id = reg["registered_skill_id"]
            # link B → Aのskill_idに紐付け
            link = self.client.post(f"/api/jobs/p5-job-link-ign/pending-skills/{pid_b}/link",
                                    json={"skill_id": skill_id}).json()
            assert link["status"] == "registered"
            # 再register → 400
            r2 = self.client.post(f"/api/jobs/p5-job-link-ign/pending-skills/{pid_a}/register")
            assert r2.status_code == 400
            # ignore C → status確認
            ign = self.client.post(f"/api/jobs/p5-job-link-ign/pending-skills/{pid_c}/ignore")
            assert ign.status_code == 200
            assert ign.json()["status"] == "ignored"
            # GETでstatus永続化確認
            get_resp = self.client.get("/api/jobs/p5-job-link-ign")
            assert get_resp.status_code == 200
            c_status = [p["status"] for p in get_resp.json().get("pending_skills", []) if p["pending_id"] == pid_c]
            assert c_status == ["ignored"]

    def test_skill_update_api(self, isolated_skill_dictionary):
        """スキルPUT更新"""
        import uuid
        sname = f"ZZZ_PUT_{uuid.uuid4().hex[:8]}"
        resp = self.client.post("/api/skills", json={"name": sname, "category": "test"}).json()
        sid = resp["id"]
        # 名称更新
        new_name = f"{sname}_updated"
        upd = self.client.put(f"/api/skills/{sid}", json={"name": new_name})
        assert upd.status_code == 200
        assert upd.json()["name"] == new_name
        # 同名重複禁止
        dup = self.client.post("/api/skills", json={"name": new_name})
        assert dup.status_code == 400
        # 存在しないID
        nf = self.client.put("/api/skills/nonexistent", json={"name": "x"})
        assert nf.status_code == 400

    # --- サンプル読込は従来形式維持 ---

    def test_sample_load_preserves_legacy_format(self):
        """サンプル一括読込のエラーレスポンスは従来のcommitted/failed/errors形式を維持"""
        with patch.object(config, 'ENABLE_SAMPLE_LOAD', True):
            resp = self.client.post("/api/resumes/load-samples")
            assert resp.status_code == 200
            data = resp.json()
            assert "committed" in data
            assert "failed" in data
            assert "errors" in data
            assert "created" in data
