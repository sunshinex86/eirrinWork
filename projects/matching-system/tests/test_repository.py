"""JSONリポジトリのCRUDテスト"""
import json
import pytest
from src.repository.json_resume_repo import JsonResumeRepository
from src.repository.json_job_repo import JsonJobRepository


class TestJsonResumeRepository:
    """経歴書JSONリポジトリのテスト"""

    def test_create_and_find_by_id(self, temp_resumes_file, sample_resume):
        """作成してIDで取得できること"""
        repo = JsonResumeRepository(temp_resumes_file)
        repo.create(sample_resume)
        found = repo.find_by_id("resume-001")
        assert found is not None
        assert found["name"] == "田中 太郎"
        assert found["years_of_experience"] == 12

    def test_find_all(self, temp_resumes_file, sample_resume, sample_resume_2):
        """複数件の登録と全件取得"""
        repo = JsonResumeRepository(temp_resumes_file)
        repo.create(sample_resume)
        repo.create(sample_resume_2)
        all_items = repo.find_all()
        assert len(all_items) == 2

    def test_find_by_id_not_found(self, temp_resumes_file):
        """存在しないID"""
        repo = JsonResumeRepository(temp_resumes_file)
        assert repo.find_by_id("non-existent") is None

    def test_update(self, temp_resumes_file, sample_resume):
        """更新が正しく反映されること"""
        repo = JsonResumeRepository(temp_resumes_file)
        repo.create(sample_resume)
        sample_resume["name"] = "田中 二郎"
        sample_resume["years_of_experience"] = 15
        updated = repo.update("resume-001", sample_resume)
        assert updated is not None
        assert updated["name"] == "田中 二郎"
        # 再取得して確認
        found = repo.find_by_id("resume-001")
        assert found["name"] == "田中 二郎"
        assert found["years_of_experience"] == 15

    def test_update_not_found(self, temp_resumes_file):
        """存在しないIDの更新はNone"""
        repo = JsonResumeRepository(temp_resumes_file)
        result = repo.update("non-existent", {"id": "non-existent", "name": "test"})
        assert result is None

    def test_delete(self, temp_resumes_file, sample_resume):
        """削除が正しく行われること"""
        repo = JsonResumeRepository(temp_resumes_file)
        repo.create(sample_resume)
        assert repo.delete("resume-001") is True
        assert repo.find_by_id("resume-001") is None
        assert repo.find_all() == []

    def test_delete_not_found(self, temp_resumes_file):
        """存在しないIDの削除はFalse"""
        repo = JsonResumeRepository(temp_resumes_file)
        assert repo.delete("non-existent") is False

    def test_exists(self, temp_resumes_file, sample_resume):
        """存在確認"""
        repo = JsonResumeRepository(temp_resumes_file)
        assert repo.exists("resume-001") is False
        repo.create(sample_resume)
        assert repo.exists("resume-001") is True

    def test_count(self, temp_resumes_file, sample_resume, sample_resume_2):
        """件数カウント"""
        repo = JsonResumeRepository(temp_resumes_file)
        assert repo.count() == 0
        repo.create(sample_resume)
        assert repo.count() == 1
        repo.create(sample_resume_2)
        assert repo.count() == 2

    def test_duplicate_id_raises_error(self, temp_resumes_file, sample_resume):
        """重複IDでエラーになること"""
        repo = JsonResumeRepository(temp_resumes_file)
        repo.create(sample_resume)
        with pytest.raises(ValueError, match="既に存在します"):
            repo.create(sample_resume)

    def test_persistence(self, temp_resumes_file, sample_resume):
        """ファイルに永続化されること（別インスタンスから読み取れる）"""
        repo1 = JsonResumeRepository(temp_resumes_file)
        repo1.create(sample_resume)

        repo2 = JsonResumeRepository(temp_resumes_file)
        found = repo2.find_by_id("resume-001")
        assert found is not None
        assert found["name"] == "田中 太郎"


class TestJsonJobRepository:
    """案件JSONリポジトリのテスト"""

    def test_create_and_find_by_id(self, temp_jobs_file, sample_job):
        """作成してIDで取得できること"""
        repo = JsonJobRepository(temp_jobs_file)
        repo.create(sample_job)
        found = repo.find_by_id("job-001")
        assert found is not None
        assert found["title"] == "Pythonバックエンドエンジニア"
        assert found["required_skills"]["languages"] == ["Python", "SQL"]

    def test_find_all(self, temp_jobs_file, sample_job, sample_job_2):
        """複数件の登録と全件取得"""
        repo = JsonJobRepository(temp_jobs_file)
        repo.create(sample_job)
        repo.create(sample_job_2)
        all_items = repo.find_all()
        assert len(all_items) == 2

    def test_find_by_id_not_found(self, temp_jobs_file):
        assert JsonJobRepository(temp_jobs_file).find_by_id("non-existent") is None

    def test_update(self, temp_jobs_file, sample_job):
        repo = JsonJobRepository(temp_jobs_file)
        repo.create(sample_job)
        sample_job["title"] = "更新後のタイトル"
        updated = repo.update("job-001", sample_job)
        assert updated is not None
        assert updated["title"] == "更新後のタイトル"

    def test_update_not_found(self, temp_jobs_file):
        repo = JsonJobRepository(temp_jobs_file)
        assert repo.update("non-existent", {"id": "non-existent", "title": "t", "company": "c"}) is None

    def test_delete(self, temp_jobs_file, sample_job):
        repo = JsonJobRepository(temp_jobs_file)
        repo.create(sample_job)
        assert repo.delete("job-001") is True
        assert repo.find_by_id("job-001") is None

    def test_delete_not_found(self, temp_jobs_file):
        assert JsonJobRepository(temp_jobs_file).delete("non-existent") is False

    def test_exists(self, temp_jobs_file, sample_job):
        repo = JsonJobRepository(temp_jobs_file)
        assert repo.exists("job-001") is False
        repo.create(sample_job)
        assert repo.exists("job-001") is True

    def test_count(self, temp_jobs_file, sample_job):
        repo = JsonJobRepository(temp_jobs_file)
        assert repo.count() == 0
        repo.create(sample_job)
        assert repo.count() == 1

    def test_duplicate_id_raises_error(self, temp_jobs_file, sample_job):
        repo = JsonJobRepository(temp_jobs_file)
        repo.create(sample_job)
        with pytest.raises(ValueError, match="既に存在します"):
            repo.create(sample_job)
