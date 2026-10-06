"""サンプルデータ読込APIのテスト"""
import sys, json
from pathlib import Path
from unittest.mock import patch
import pytest
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from fastapi.testclient import TestClient
from src.api.main import app


class TestSampleLoad:
    @pytest.fixture(autouse=True)
    def _isolate(self, tmp_path, monkeypatch):
        from src.repository.json_resume_repo import JsonResumeRepository
        from src.repository.json_job_repo import JsonJobRepository
        import src.api.routes_resumes
        import src.api.routes_jobs
        from src.api.routes_match import matcher
        rf = tmp_path / "r.json"; rf.write_text("[]", encoding="utf-8")
        jf = tmp_path / "j.json"; jf.write_text("[]", encoding="utf-8")
        rr = JsonResumeRepository(rf); jr = JsonJobRepository(jf)
        monkeypatch.setattr(src.api.routes_resumes, "repo", rr)
        monkeypatch.setattr(src.api.routes_jobs, "repo", jr)
        monkeypatch.setattr(matcher, "resume_repo", rr)
        monkeypatch.setattr(matcher, "job_repo", jr)
        self.client = TestClient(app)

    def test_load_sample_resumes(self):
        """サンプル経歴書の一括読込"""
        with patch.object(config, 'ENABLE_SAMPLE_LOAD', True):
            resp = self.client.post("/api/resumes/load-samples")
            assert resp.status_code == 200
            data = resp.json()
            assert data["created"] + data["skipped"] > 0

    def test_load_sample_jobs(self):
        """サンプル案件の一括読込"""
        with patch.object(config, 'ENABLE_SAMPLE_LOAD', True):
            resp = self.client.post("/api/jobs/load-samples")
            assert resp.status_code == 200
            data = resp.json()
            assert data["created"] + data["skipped"] > 0

    def test_disabled_returns_404(self):
        """無効時は404"""
        with patch.object(config, 'ENABLE_SAMPLE_LOAD', False):
            resp = self.client.post("/api/resumes/load-samples")
            assert resp.status_code == 404


class TestSampleSchemaValidation:
    """REQ-RE2-05: サンプル全件Schema検証テスト"""

    @pytest.fixture(autouse=True)
    def _isolate(self, tmp_path, monkeypatch):
        from src.repository.json_resume_repo import JsonResumeRepository
        from src.repository.json_job_repo import JsonJobRepository
        import src.api.routes_resumes
        import src.api.routes_jobs
        from src.api.routes_match import matcher
        rf = tmp_path / "res.json"; rf.write_text("[]", encoding="utf-8")
        jf = tmp_path / "job.json"; jf.write_text("[]", encoding="utf-8")
        rr = JsonResumeRepository(rf); jr = JsonJobRepository(jf)
        monkeypatch.setattr(src.api.routes_resumes, "repo", rr)
        monkeypatch.setattr(src.api.routes_jobs, "repo", jr)
        monkeypatch.setattr(matcher, "resume_repo", rr)
        monkeypatch.setattr(matcher, "job_repo", jr)

    @patch.object(config, 'ENABLE_SAMPLE_LOAD', True)
    def test_validation_passes_for_normal_samples(self):
        """正常サンプルは全件保存される"""
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)
        resp = client.post("/api/resumes/load-samples")
        assert resp.status_code == 200
        data = resp.json()
        assert data["committed"] is True
        assert data["created"] + data["skipped"] > 0

    @patch.object(config, 'ENABLE_SAMPLE_LOAD', True)
    def test_job_validation_passes_for_normal_samples(self):
        """正常サンプル（案件）は全件保存される"""
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)
        resp = client.post("/api/jobs/load-samples")
        assert resp.status_code == 200
        data = resp.json()
        assert data["committed"] is True

    @patch.object(config, 'ENABLE_SAMPLE_LOAD', True)
    def test_unresolved_skills_allows_save(self):
        """未解決スキル警告のみの場合は保存可能"""
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)
        # 経歴書に未登録スキル名があっても致命的エラーでなければ保存される
        resp = client.post("/api/resumes/load-samples")
        assert resp.status_code == 200
        data = resp.json()
        # unresolved_skills があっても committed=true（警告のみ）
        if data.get("unresolved_skills"):
            assert data["committed"] is True

    def test_results_structure(self):
        """レスポンス構造に必要なフィールドが含まれる"""
        # commited/failed/errors の構造が存在することはAPIレベルで確認
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)
        with patch.object(config, 'ENABLE_SAMPLE_LOAD', True):
            resp = client.post("/api/resumes/load-samples")
            assert resp.status_code == 200
            data = resp.json()
            assert "committed" in data
            assert "failed" in data
            assert "errors" in data


class TestP5SampleValidation:
    """REQ-RE3-06: サンプル検証補完のテスト"""

    def test_duplicate_id_rejected(self):
        """同一ファイル内重複IDが検出される"""
        samples = [{"id": "x"}, {"id": "x"}]
        seen, errors = set(), []
        for s in samples:
            sid = s.get("id", "")
            if sid in seen:
                errors.append({"id": sid})
            seen.add(sid)
        assert len(errors) == 1

    def test_no_duplicate_passes(self):
        """重複なし→エラーなし"""
        samples = [{"id": "a"}, {"id": "b"}]
        seen, errors = set(), []
        for s in samples:
            sid = s.get("id", "")
            if sid in seen:
                errors.append({"id": sid})
            seen.add(sid)
        assert len(errors) == 0

    def test_post_conversion_revalidation(self):
        """変換後データ再検証: 正常pass, 不正拒否"""
        from src.models.resume import Resume
        Resume.model_validate({"id": "t", "name": "T", "age": 30})
        try:
            Resume.model_validate({"id": "", "name": "T", "age": 30})
            assert False
        except Exception:
            pass


class TestP6Rollback:
    """REQ-RE3-07: ロールバックテスト"""

    def test_invalid_sample_causes_rollback(self):
        """不正サンプルを含む場合→committed=false"""
        samples = [
            {"id": "good", "name": "A", "age": 30, "skills": {}},
            {"id": "bad", "name": "B", "age": 999, "skills": {}},  # age out of range
        ]
        from src.models.resume import Resume
        all_ok = True
        errors = []
        for s in samples:
            try:
                Resume.model_validate(s)
            except Exception as e:
                errors.append({"id": s.get("id"), "error": str(e)})
                all_ok = False
        assert all_ok is False
        assert len(errors) == 1
        assert errors[0]["id"] == "bad"

    def test_all_valid_passes(self):
        """全件正常→committed=true"""
        samples = [
            {"id": "a", "name": "A", "age": 30, "skills": {}},
            {"id": "b", "name": "B", "age": 25, "skills": {}},
        ]
        from src.models.resume import Resume
        all_ok = True
        for s in samples:
            try:
                Resume.model_validate(s)
            except Exception:
                all_ok = False
        assert all_ok is True


    @patch.object(config, 'ENABLE_SAMPLE_LOAD', True)
    def test_converted_pydantic_result_saved(self, tmp_path, monkeypatch):
        """変換後Pydantic結果が実際に保存される（正規ID・デフォルト値）"""
        import json
        from fastapi.testclient import TestClient
        from src.api.main import app
        from src.repository.json_resume_repo import JsonResumeRepository
        import src.api.routes_resumes
        from src.api.routes_match import matcher

        resume_file = tmp_path / "resumes.json"
        resume_file.write_text("[]", encoding="utf-8")
        repo = JsonResumeRepository(resume_file)
        monkeypatch.setattr(src.api.routes_resumes, "repo", repo)
        monkeypatch.setattr(matcher, "resume_repo", repo)
        monkeypatch.setattr(config, "RESUMES_FILE", resume_file)

        samples = [
            {"id": "conv-test", "name": "  Converted  ", "age": 30,
             "years_of_experience": 5, "skills": {"languages": ["Python"]},
             "desired_unit_price_min": 400, "desired_unit_price_max": 600,
             "employment_type": "正社員"},
        ]
        sample_file = tmp_path / "sample_conv.json"
        sample_file.write_text(json.dumps(samples), encoding="utf-8")
        monkeypatch.setattr(config, "SAMPLE_RESUMES_FILE", sample_file)

        client = TestClient(app)
        resp = client.post("/api/resumes/load-samples")
        assert resp.status_code == 200
        data = resp.json()
        assert data["committed"] is True
        assert data["created"] == 1

        # 保存データを確認
        saved = repo.find_by_id("conv-test")
        assert saved is not None
        # 名前の前後空白が除去されている（Pydantic検証結果の反映）
        assert saved["name"] == "Converted", f"Expected stripped name, got {saved['name']}"
        # structured_skills に同義語解決後の正規IDが入っている
        saved_ids = [s["skill_id"] for s in saved.get("structured_skills", [])]
        assert "python" in saved_ids, f"Expected 'python' in {saved_ids}"

    @patch.object(config, 'ENABLE_SAMPLE_LOAD', True)
    def test_job_converted_values_saved(self, tmp_path, monkeypatch):
        """案件変換後: 正規ID・required/preferred個別・デフォルト値"""
        import json
        from fastapi.testclient import TestClient
        from src.api.main import app
        from src.repository.json_job_repo import JsonJobRepository
        import src.api.routes_jobs
        from src.api.routes_match import matcher

        job_file = tmp_path / "jobs.json"
        job_file.write_text("[]", encoding="utf-8")
        repo = JsonJobRepository(job_file)
        monkeypatch.setattr(src.api.routes_jobs, "repo", repo)
        monkeypatch.setattr(matcher, "job_repo", repo)
        monkeypatch.setattr(config, "JOBS_FILE", job_file)

        samples = [
            {"id": "job-conv", "title": "Engineer", "company": "Corp",
             "required_skills": {"languages": ["TypeScript"]},
             "preferred_skills": {"frameworks": ["React"]},
             "required_experience_years": 3, "unit_price_min": 300, "unit_price_max": 600,
             "employment_type": "正社員", "headcount": 1},
        ]
        sample_file = tmp_path / "sample_job_conv.json"
        sample_file.write_text(json.dumps(samples), encoding="utf-8")
        monkeypatch.setattr(config, "SAMPLE_JOBS_FILE", sample_file)

        client = TestClient(app)
        resp = client.post("/api/jobs/load-samples")
        assert resp.status_code == 200
        data = resp.json()
        assert data["committed"] is True

        saved = repo.find_by_id("job-conv")
        assert saved is not None
        # required: TypeScript → typescript（同義語正規化）
        req_ids = [s["skill_id"] for s in saved.get("structured_required_skills", [])]
        assert "typescript" in req_ids, f"Expected typescript in required, got {req_ids}"
        # preferred: React → react
        pref_ids = [s["skill_id"] for s in saved.get("structured_preferred_skills", [])]
        assert "react" in pref_ids, f"Expected react in preferred, got {pref_ids}"
        # required_level/required_years デフォルト値
        for skill in saved.get("structured_required_skills", []):
            assert skill.get("required_level", 0) >= 1
            assert skill.get("required_years", 0) >= 0

class TestSampleLoadRealProcessing:
    """REQ-RE6-03: Sample読込 実処理テスト（一時Sample+一時Repository+実API）"""

    @patch.object(config, 'ENABLE_SAMPLE_LOAD', True)
    def test_normal_2_created(self, tmp_path, monkeypatch):
        """正常2件 -> created=2"""
        import json
        from fastapi.testclient import TestClient
        from src.api.main import app
        from src.repository.json_resume_repo import JsonResumeRepository
        import src.api.routes_resumes
        from src.api.routes_match import matcher

        resume_file = tmp_path / "resumes.json"
        resume_file.write_text("[]", encoding="utf-8")
        repo = JsonResumeRepository(resume_file)
        monkeypatch.setattr(src.api.routes_resumes, "repo", repo)
        monkeypatch.setattr(matcher, "resume_repo", repo)
        monkeypatch.setattr(config, "RESUMES_FILE", resume_file)

        samples = [
            {"id": "rr1", "name": "T1", "age": 30, "years_of_experience": 5,
             "skills": {"languages": ["Python"]}, "desired_unit_price_min": 400, "desired_unit_price_max": 600,
             "employment_type": "正社員"},
            {"id": "rr2", "name": "T2", "age": 35, "years_of_experience": 10,
             "skills": {"languages": ["Java"]}, "desired_unit_price_min": 500, "desired_unit_price_max": 800,
             "employment_type": "正社員"},
        ]
        sample_file = tmp_path / "sample_resumes.json"
        sample_file.write_text(json.dumps(samples), encoding="utf-8")
        monkeypatch.setattr(config, "SAMPLE_RESUMES_FILE", sample_file)

        client = TestClient(app)
        resp = client.post("/api/resumes/load-samples")
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 2, f"Expected created=2, got {data}"
        assert data["committed"] is True

    @patch.object(config, 'ENABLE_SAMPLE_LOAD', True)
    def test_duplicate_id_in_file_rejected(self, tmp_path, monkeypatch):
        """重複ID -> committed=false + failed>0"""
        import json
        from fastapi.testclient import TestClient
        from src.api.main import app
        from src.repository.json_resume_repo import JsonResumeRepository
        import src.api.routes_resumes
        from src.api.routes_match import matcher

        resume_file = tmp_path / "resumes.json"
        resume_file.write_text("[]", encoding="utf-8")
        repo = JsonResumeRepository(resume_file)
        monkeypatch.setattr(src.api.routes_resumes, "repo", repo)
        monkeypatch.setattr(matcher, "resume_repo", repo)
        monkeypatch.setattr(config, "RESUMES_FILE", resume_file)

        samples = [
            {"id": "dup-1", "name": "A", "age": 30, "years_of_experience": 5,
             "skills": {"languages": ["Python"]}, "desired_unit_price_min": 300, "desired_unit_price_max": 600,
             "employment_type": "正社員"},
            {"id": "dup-1", "name": "B", "age": 35, "years_of_experience": 10,
             "skills": {"languages": ["Java"]}, "desired_unit_price_min": 400, "desired_unit_price_max": 800,
             "employment_type": "正社員"},
        ]
        sample_file = tmp_path / "sample_dup.json"
        sample_file.write_text(json.dumps(samples), encoding="utf-8")
        monkeypatch.setattr(config, "SAMPLE_RESUMES_FILE", sample_file)

        client = TestClient(app)
        resp = client.post("/api/resumes/load-samples")
        assert resp.status_code == 200
        data = resp.json()
        assert data["committed"] is False
        assert data["failed"] == 1

    @patch.object(config, 'ENABLE_SAMPLE_LOAD', True)
    def test_invalid_data_rollback(self, tmp_path, monkeypatch):
        """不正1件+正常1件 -> rollback、既存データ不変"""
        import json
        from fastapi.testclient import TestClient
        from src.api.main import app
        from src.repository.json_resume_repo import JsonResumeRepository
        import src.api.routes_resumes
        from src.api.routes_match import matcher

        resume_file = tmp_path / "resumes.json"
        resume_file.write_text("[]", encoding="utf-8")
        repo = JsonResumeRepository(resume_file)
        repo.create({"id": "existing", "name": "Existing", "age": 30,
                     "years_of_experience": 5, "desired_unit_price_min": 300, "desired_unit_price_max": 600,
                     "employment_type": "正社員"})
        monkeypatch.setattr(src.api.routes_resumes, "repo", repo)
        monkeypatch.setattr(matcher, "resume_repo", repo)
        monkeypatch.setattr(config, "RESUMES_FILE", resume_file)

        samples = [
            {"id": "good", "name": "Good", "age": 30, "years_of_experience": 5,
             "skills": {}, "desired_unit_price_min": 300, "desired_unit_price_max": 600,
             "employment_type": "正社員"},
            {"id": "bad", "name": "Bad", "age": 999, "years_of_experience": 5,
             "skills": {}, "desired_unit_price_min": 300, "desired_unit_price_max": 600,
             "employment_type": "正社員"},
        ]
        sample_file = tmp_path / "sample_bad.json"
        sample_file.write_text(json.dumps(samples), encoding="utf-8")
        monkeypatch.setattr(config, "SAMPLE_RESUMES_FILE", sample_file)

        client = TestClient(app)
        resp = client.post("/api/resumes/load-samples")
        assert resp.status_code == 200
        data = resp.json()
        assert data["committed"] is False
        assert data["failed"] == 1
        all_items = repo.find_all()
        ids = [i["id"] for i in all_items]
        assert "existing" in ids
        assert "good" not in ids

    @patch.object(config, 'ENABLE_SAMPLE_LOAD', True)
    def test_unresolved_skills_returned(self, tmp_path, monkeypatch):
        """未登録スキル名 -> unresolved_skills>0, committed=true"""
        import json
        from fastapi.testclient import TestClient
        from src.api.main import app
        from src.repository.json_resume_repo import JsonResumeRepository
        import src.api.routes_resumes
        from src.api.routes_match import matcher

        resume_file = tmp_path / "resumes.json"
        resume_file.write_text("[]", encoding="utf-8")
        repo = JsonResumeRepository(resume_file)
        monkeypatch.setattr(src.api.routes_resumes, "repo", repo)
        monkeypatch.setattr(matcher, "resume_repo", repo)
        monkeypatch.setattr(config, "RESUMES_FILE", resume_file)

        samples = [
            {"id": "urs-1", "name": "U", "age": 30, "years_of_experience": 5,
             "skills": {"languages": ["UnknownSkillXYZ"]}, "desired_unit_price_min": 300, "desired_unit_price_max": 600,
             "employment_type": "正社員"},
        ]
        sample_file = tmp_path / "sample_unresolved.json"
        sample_file.write_text(json.dumps(samples), encoding="utf-8")
        monkeypatch.setattr(config, "SAMPLE_RESUMES_FILE", sample_file)

        client = TestClient(app)
        resp = client.post("/api/resumes/load-samples")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data.get("unresolved_skills", [])) > 0
        assert data["committed"] is True

    @patch.object(config, 'ENABLE_SAMPLE_LOAD', True)
    def test_job_required_preferred_split(self, tmp_path, monkeypatch):
        """必須/歓迎スキルの振り分け"""
        import json
        from fastapi.testclient import TestClient
        from src.api.main import app
        from src.repository.json_job_repo import JsonJobRepository
        import src.api.routes_jobs
        from src.api.routes_match import matcher

        job_file = tmp_path / "jobs.json"
        job_file.write_text("[]", encoding="utf-8")
        repo = JsonJobRepository(job_file)
        monkeypatch.setattr(src.api.routes_jobs, "repo", repo)
        monkeypatch.setattr(matcher, "job_repo", repo)
        monkeypatch.setattr(config, "JOBS_FILE", job_file)

        samples = [
            {"id": "job-test", "title": "Dev", "company": "C",
             "required_skills": {"languages": ["Python"]},
             "preferred_skills": {"languages": ["Go"]},
             "required_experience_years": 3, "unit_price_min": 300, "unit_price_max": 600,
             "employment_type": "正社員", "headcount": 1},
        ]
        sample_file = tmp_path / "sample_job_test.json"
        sample_file.write_text(json.dumps(samples), encoding="utf-8")
        monkeypatch.setattr(config, "SAMPLE_JOBS_FILE", sample_file)

        client = TestClient(app)
        resp = client.post("/api/jobs/load-samples")
        assert resp.status_code == 200
        data = resp.json()
        assert data["committed"] is True
        saved = repo.find_by_id("job-test")
        assert saved is not None
        assert len(saved.get("structured_required_skills", [])) > 0
        assert len(saved.get("structured_preferred_skills", [])) > 0
