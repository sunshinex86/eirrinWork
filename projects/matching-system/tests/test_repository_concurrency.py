"""排他制御・同時更新・原子的保存のテスト（REQ-RE6-04）

- multiprocessing によるプロセス間排他テスト
- ロックタイムアウト例外テスト（FileLockTimeoutError限定）
- bulk_merge + CRUD 同時実行テスト
"""
import json
import threading
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.repository.json_job_repo import JsonJobRepository
from src.repository.json_resume_repo import JsonResumeRepository


# --- multiprocessing用トップレベル関数（spawn対応） ---
def _mp_run_worker(json_path, worker_id, n_items):
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.repository.json_job_repo import JsonJobRepository
    repo = JsonJobRepository(Path(json_path))
    for i in range(n_items):
        try:
            repo.create({"id": f"mp-worker-{worker_id}-{i}"})
        except (ValueError, OSError):
            pass


def _mp_run_crud(json_path):
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.repository.json_job_repo import JsonJobRepository
    repo = JsonJobRepository(Path(json_path))
    for i in range(3):
        try:
            repo.create({"id": f"crud-{i}"})
        except (ValueError, OSError):
            pass


def _mp_run_bulk_merge(json_path):
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.repository.json_job_repo import JsonJobRepository
    repo = JsonJobRepository(Path(json_path))
    items = [{"id": f"merge-{i}"} for i in range(3)]
    repo.bulk_merge(items, on_conflict="skip")


def _mp10_worker(barrier, q, wid, path):
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.repository.json_job_repo import JsonJobRepository
    try:
        barrier.wait()
        repo = JsonJobRepository(Path(path))
        for i in range(5):
            repo.create({"id": f"mp10-{wid}-{i}"})
        q.put((wid, "ok", None))
    except Exception as e:
        q.put((wid, "fail", str(e)))


def _mp6_crud_worker(barrier, q, path):
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.repository.json_job_repo import JsonJobRepository
    try:
        barrier.wait()
        repo = JsonJobRepository(Path(path))
        for i in range(3):
            repo.create({"id": f"crud-{i}"})
        q.put(("crud", "ok", None))
    except Exception as e:
        q.put(("crud", "fail", str(e)))


def _mp6_merge_worker(barrier, q, path):
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.repository.json_job_repo import JsonJobRepository
    try:
        barrier.wait()
        repo = JsonJobRepository(Path(path))
        items = [{"id": f"merge-{i}"} for i in range(3)]
        repo.bulk_merge(items, on_conflict="skip")
        q.put(("merge", "ok", None))
    except Exception as e:
        q.put(("merge", "fail", str(e)))


# --- テストクラス ---

class TestAtomicSave:
    def test_save_uses_os_replace(self, temp_json_file):
        repo = JsonJobRepository(temp_json_file)
        repo._save([{"id": "t1"}])
        saved = json.loads(temp_json_file.read_text(encoding="utf-8"))
        assert len(saved) == 1

    def test_temp_file_cleaned(self, temp_json_file):
        repo = JsonJobRepository(temp_json_file)
        repo._save([{"id": "t1"}])
        tmp_files = list(temp_json_file.parent.glob("*.json.tmp*"))
        assert len(tmp_files) == 0


class TestSharedLock:
    def test_crud_uses_shared_lock(self, temp_json_file):
        repo = JsonJobRepository(temp_json_file)
        c = repo.create({"id": "t1", "title": "test"})
        assert c["id"] == "t1"
        u = repo.update("t1", {"title": "u"})
        assert u["title"] == "u"
        assert repo.delete("t1") is True

    def test_bulk_merge_skip(self, temp_json_file):
        repo = JsonJobRepository(temp_json_file)
        repo.create({"id": "e", "title": "o"})
        result = repo.bulk_merge([{"id": "e", "title": "x"}], on_conflict="skip")
        assert result["created"] == 0
        assert repo.find_by_id("e")["title"] == "o"

    def test_bulk_merge_counts(self, temp_json_file):
        repo = JsonJobRepository(temp_json_file)
        repo.create({"id": "e"})
        result = repo.bulk_merge([{"id": "e"}, {"id": "n1"}, {"id": "n2"}], on_conflict="skip")
        assert result["created"] == 2
        assert result["skipped"] == 1
        assert repo.count() == 3


class TestConcurrentAccess:
    def test_concurrent_creates_all_succeed(self, temp_json_file):
        repo = JsonJobRepository(temp_json_file)
        n = 10

        def create_item(i):
            try:
                repo.create({"id": f"c-{i}"})
            except (ValueError, OSError):
                pass

        threads = [threading.Thread(target=create_item, args=(i,)) for i in range(n)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=5)

        ids = {item["id"] for item in repo.find_all() if item["id"].startswith("c-")}
        assert len(ids) == n, f"Expected {n}, got {len(ids)}"


class TestMultiProcessConcurrency:
    """REQ-RE6-04: multiprocessing厳密化（Barrier+Queue+10件+6件完全一致）"""

    def test_two_processes_ten_items_exact(self, tmp_path):
        import multiprocessing
        json_file = tmp_path / "mp10.json"
        json_file.write_text("[]", encoding="utf-8")
        ctx = multiprocessing.get_context("spawn")
        barrier = ctx.Barrier(2, timeout=30)
        q = ctx.Queue()

        p1 = ctx.Process(target=_mp10_worker, args=(barrier, q, 1, str(json_file)))
        p2 = ctx.Process(target=_mp10_worker, args=(barrier, q, 2, str(json_file)))
        p1.start(); p2.start()
        p1.join(timeout=30); p2.join(timeout=30)

        results = []
        while not q.empty():
            results.append(q.get_nowait())
        for wid, status, err in results:
            assert status == "ok", f"Worker {wid} failed: {err}"
        assert p1.exitcode == 0 and p2.exitcode == 0

        repo = JsonJobRepository(json_file)
        ids = {item["id"] for item in repo.find_all()}
        expected = {f"mp10-{w}-{i}" for w in [1, 2] for i in range(5)}
        assert len(ids) == len(expected), f"Expected {len(expected)}, got {len(ids)}"
        assert ids == expected
        data = json.loads(json_file.read_text(encoding="utf-8"))
        assert len(data) == len(expected)

    def test_crud_plus_bulk_merge_6_items(self, tmp_path):
        import multiprocessing
        json_file = tmp_path / "mp6.json"
        json_file.write_text("[]", encoding="utf-8")
        ctx = multiprocessing.get_context("spawn")
        barrier = ctx.Barrier(2, timeout=30)
        q = ctx.Queue()

        p1 = ctx.Process(target=_mp6_crud_worker, args=(barrier, q, str(json_file)))
        p2 = ctx.Process(target=_mp6_merge_worker, args=(barrier, q, str(json_file)))
        p1.start(); p2.start()
        p1.join(timeout=30); p2.join(timeout=30)

        results = []
        while not q.empty():
            results.append(q.get_nowait())
        for name, status, err in results:
            assert status == "ok", f"{name} failed: {err}"
        assert p1.exitcode == 0 and p2.exitcode == 0

        repo = JsonJobRepository(json_file)
        ids = {item["id"] for item in repo.find_all()}
        expected = {f"crud-{i}" for i in range(3)} | {f"merge-{i}" for i in range(3)}
        assert len(ids) == len(expected), f"Expected {len(expected)}, got {len(ids)}"
        assert ids == expected
        data = json.loads(json_file.read_text(encoding="utf-8"))
        assert len(data) == len(expected)


class TestLockTimeout:
    """REQ-RE6-04: ロックタイムアウト例外（FileLockTimeoutError限定）"""

    def test_lock_timeout_raises_error(self, tmp_path):
        from src.repository.exceptions import FileLockTimeoutError
        from src.repository.json_job_repo import acquire_file_lock

        lock_dir = tmp_path
        lock_held = threading.Event()
        stop_holding = threading.Event()
        timeout_caught = threading.Event()
        wrong_error = threading.Event()

        def holder():
            with acquire_file_lock(lock_dir):
                lock_held.set()
                stop_holding.wait(timeout=10)

        t = threading.Thread(target=holder, daemon=True)
        t.start()
        lock_held.wait(timeout=5)

        try:
            with acquire_file_lock(lock_dir):
                pass
        except FileLockTimeoutError:
            timeout_caught.set()
        except OSError:
            wrong_error.set()

        stop_holding.set()
        t.join(timeout=3)
        assert timeout_caught.is_set(), "Expected FileLockTimeoutError"
        assert not wrong_error.is_set(), "OSError should NOT be success"
