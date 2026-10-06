"""テスト用の共有フィクスチャ"""
import sys
import json
import tempfile
from pathlib import Path
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "embedding_e2e: Embedding実モデルE2Eテスト（RUN_EMBEDDING_E2E=1必要）")

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def isolate_market_events(tmp_path, monkeypatch):
    """market_event_log の書込先を一時ファイルに分離し、本番イベントログを汚染しないようにする"""
    import src.utils.market_event_log as event_log
    monkeypatch.setattr(event_log, "EVENTS_FILE", tmp_path / "market_events_test.jsonl")


@pytest.fixture
def sample_resume():
    """テスト用の標準的な経歴書データ"""
    return {
        "id": "resume-001",
        "name": "田中 太郎",
        "age": 34,
        "email": "tanaka@example.com",
        "phone": "090-1234-5678",
        "location": "東京都港区",
        "desired_locations": ["東京都23区内", "リモート可"],
        "education": [
            {
                "school": "東京大学",
                "department": "工学部 情報工学科",
                "graduation_year": 2014,
                "degree": "学士",
            }
        ],
        "work_history": [
            {
                "company": "株式会社ABCテクノロジー",
                "position": "シニアエンジニア",
                "start_date": "2020-04",
                "end_date": None,
                "description": "Python/Djangoを使用したバックエンドAPI開発。",
                "industry": "IT・通信",
            },
            {
                "company": "DEFソフトウェア株式会社",
                "position": "エンジニア",
                "start_date": "2014-04",
                "end_date": "2020-03",
                "description": "Javaによる業務システム開発。",
                "industry": "IT・通信",
            },
        ],
        "skills": {
            "languages": ["Python", "Java", "SQL", "TypeScript"],
            "frameworks": ["Django", "FastAPI", "React"],
            "tools": ["Docker", "Git", "AWS", "Jenkins"],
            "certifications": ["基本情報技術者", "AWS SAA"],
            "other": ["git", "docker"],
        },
        "years_of_experience": 12,
        "desired_unit_price_min": 70,
        "desired_unit_price_max": 100,
        "employment_type": "正社員",
        "self_pr": "新しい技術へのキャッチアップが早い。",
    }


@pytest.fixture
def sample_job():
    """テスト用の標準的な案件データ"""
    return {
        "id": "job-001",
        "title": "Pythonバックエンドエンジニア",
        "company": "GHIテクノロジーズ株式会社",
        "industry": "IT・通信",
        "job_type": "ITエンジニア",
        "location": "東京都渋谷区",
        "remote_policy": "週2回リモート可",
        "required_skills": {
            "languages": ["Python", "SQL"],
            "frameworks": ["Django", "FastAPI"],
            "tools": ["Docker", "Git"],
            "other": ["REST API設計経験"],
        },
        "preferred_skills": {
            "languages": ["TypeScript", "Go"],
            "frameworks": ["React"],
            "tools": ["AWS", "Kubernetes"],
            "other": ["docker"],
        },
        "description": "自社SaaSプロダクトのバックエンド開発。",
        "required_experience_years": 5,
        "unit_price_min": 60,
        "unit_price_max": 90,
        "employment_type": "正社員",
        "duration": "長期",
        "headcount": 2,
    }


@pytest.fixture
def sample_resume_2():
    """テスト用の2人目の経歴書（スキル不足）"""
    return {
        "id": "resume-002",
        "name": "鈴木 花子",
        "age": 28,
        "email": "suzuki@example.com",
        "location": "神奈川県横浜市",
        "desired_locations": ["東京都23区内", "神奈川県", "リモート可"],
        "education": [],
        "work_history": [
            {
                "company": "株式会社データインサイト",
                "position": "データアナリスト",
                "start_date": "2020-04",
                "end_date": None,
                "description": "Python、SQLを用いたデータ分析。",
                "industry": "IT・通信",
            }
        ],
        "skills": {
            "languages": ["Python", "SQL", "R"],
            "frameworks": [],
            "tools": ["Git", "BigQuery"],
            "certifications": ["python"],
            "other": ["データ分析"],
        },
        "years_of_experience": 6,
        "desired_unit_price_min": 50,
        "desired_unit_price_max": 70,
        "employment_type": "正社員",
        "self_pr": "データに基づいた意思決定支援が得意。",
    }


@pytest.fixture
def sample_job_2():
    """テスト用の2つ目の案件（業界違い・遠隔地）"""
    return {
        "id": "job-002",
        "title": "製造業向けプロジェクトマネージャー",
        "company": "大阪テクノロジー",
        "industry": "製造",
        "job_type": "PM",
        "location": "大阪府大阪市",
        "remote_policy": "",
        "required_skills": {
            "languages": ["Java"],
            "frameworks": ["Spring"],
            "tools": [],
            "other": ["プロジェクト管理", "PMP"],
        },
        "preferred_skills": {
            "languages": [],
            "frameworks": [],
            "tools": [],
            "other": ["kubernetes"],
        },
        "description": "大手製造業の基幹システム構築。",
        "required_experience_years": 10,
        "unit_price_min": 80,
        "unit_price_max": 110,
        "employment_type": "正社員",
        "duration": "3年以上",
        "headcount": 1,
    }




@pytest.fixture
def isolated_api_storage(tmp_path, monkeypatch):
    """APIテスト用の分離ストレージ（REQ-RE5-07）

    正式JSONファイルではなく tmp_path 上の一時JSONを使用する。
    テスト前後で正式JSONの内容は変化しない。
    """
    from src.repository.json_resume_repo import JsonResumeRepository
    from src.repository.json_job_repo import JsonJobRepository
    import src.api.routes_resumes
    import src.api.routes_jobs
    from src.api.routes_match import matcher

    resume_file = tmp_path / "resumes.json"
    job_file = tmp_path / "jobs.json"
    resume_file.write_text("[]", encoding="utf-8")
    job_file.write_text("[]", encoding="utf-8")

    resume_repo = JsonResumeRepository(resume_file)
    job_repo = JsonJobRepository(job_file)

    monkeypatch.setattr(src.api.routes_resumes, "repo", resume_repo)
    monkeypatch.setattr(src.api.routes_jobs, "repo", job_repo)
    monkeypatch.setattr(matcher, "resume_repo", resume_repo)
    monkeypatch.setattr(matcher, "job_repo", job_repo)

    return {
        "resume_file": resume_file,
        "job_file": job_file,
        "resume_repo": resume_repo,
        "job_repo": job_repo,
    }


@pytest.fixture
def isolated_skill_dictionary(tmp_path):
    """スキル辞書を一時ファイルに分離（P5テスト用）"""
    import shutil
    import src.utils.skill_dictionary as sd
    src_dir = Path(__file__).parent.parent / "data" / "skills"
    for fname in ["skill_dictionary.json", "skill_tree.json"]:
        shutil.copy2(src_dir / fname, tmp_path / fname)
    orig_dict = sd._SKILL_DICT_PATH
    orig_tree = sd._SKILL_TREE_PATH
    sd._SKILL_DICT_PATH = tmp_path / "skill_dictionary.json"
    sd._SKILL_TREE_PATH = tmp_path / "skill_tree.json"
    sd.invalidate_cache()
    yield
    sd._SKILL_DICT_PATH = orig_dict
    sd._SKILL_TREE_PATH = orig_tree
    sd.invalidate_cache()


@pytest.fixture(autouse=True)
def check_production_files_unchanged():
    """テスト前後で正式JSONおよび.lock/.bakが変化しないことを確認（REQ-RE6-08）"""
    import hashlib
    data_dir = Path(__file__).parent.parent / "data"

    def _snapshot():
        """現在のファイル状態をスナップショット"""
        snap = {}
        for pattern in ["*.json", "*.lock", "*.bak"]:
            for f in sorted(data_dir.glob(pattern)):
                if f.is_file():
                    snap[f.name] = {
                        "md5": hashlib.md5(f.read_bytes()).hexdigest(),
                        "size": f.stat().st_size,
                    }
        return snap

    before = _snapshot()
    before_names = set(before.keys())
    yield
    after = _snapshot()
    after_names = set(after.keys())
    # ファイル名集合の完全一致確認（新規作成・削除なし）
    assert before_names == after_names, f"File set changed. Added: {after_names - before_names}, Removed: {before_names - after_names}"
    for name, info in after.items():
        before_info = before.get(name)
        assert before_info is not None, f"New file created during test: {name}"
        assert info == before_info, f"File changed during test: {name}"

@pytest.fixture
def temp_json_file():
    """テスト用の一時JSONファイルを作成・削除"""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    json.dump([], tmp)
    tmp.close()
    yield Path(tmp.name)
    # クリーンアップ
    Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture
def temp_resumes_file():
    """経歴書テスト用の一時ファイル"""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    json.dump([], tmp)
    tmp.close()
    yield Path(tmp.name)
    Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture
def temp_jobs_file():
    """案件テスト用の一時ファイル"""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    json.dump([], tmp)
    tmp.close()
    yield Path(tmp.name)
    Path(tmp.name).unlink(missing_ok=True)
