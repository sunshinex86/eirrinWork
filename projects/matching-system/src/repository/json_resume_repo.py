"""経歴書 JSONリポジトリ実装

REQ-RE2-03: OSレベルファイルロックによる排他制御
REQ-RE2-04: 一時ファイル経由 + os.replace による原子的保存
REQ-RE3-04: 共通deadline方式のリトライループ＋例外分離
"""
import json
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from .base import BaseRepository
from .exceptions import (
    FileLockTimeoutError,
    RepositoryReadError,
    RepositoryWriteError,
)

# プロセス共有ロック（REQ-RE2-03: OSレベルファイルロック）
_file_lock = threading.Lock()
LOCK_TIMEOUT = 10  # 秒（全体deadline）


def _os_lock(lock_path: Path, deadline: float) -> int:
    """OSレベルのファイルロックを取得する（REQ-RE3-04: 50msリトライ＋共通deadline）

    Args:
        lock_path: ロックファイルのパス
        deadline: 絶対期限（monotonic 秒）。この時刻までリトライする。

    Returns:
        ロックファイルのファイルディスクリプタ

    Raises:
        FileLockTimeoutError: deadline超過時に送出
    """
    import platform
    system = platform.system()

    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    try:
        while True:
            try:
                if system == "Windows":
                    import msvcrt
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # ロック成功
                return fd
            except (IOError, OSError, ImportError):
                # 非ブロッキング失敗 → 50ms待機してリトライ
                now = time.monotonic()
                if now >= deadline:
                    os.close(fd)
                    raise FileLockTimeoutError(
                        f"OSファイルロック獲得タイムアウト（{LOCK_TIMEOUT}秒）: {lock_path}"
                    )
                time.sleep(0.05)  # 50ms
    except FileLockTimeoutError:
        raise
    except Exception:
        os.close(fd)
        raise


def _os_unlock(fd: int):
    """OSレベルのファイルロックを解放する"""
    import platform
    system = platform.system()
    try:
        if system == "Windows":
            import msvcrt
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_UN)
    except Exception:
        pass
    finally:
        os.close(fd)


@contextmanager
def acquire_file_lock(lock_dir: Path):
    """JSONファイル操作用のOSレベルファイルロック

    REQ-RE3-04: 共通deadline方式（threading lock + OS lock 全体で最大10秒）。
    二重ロック防止: 内部メソッドはロック取得なしで動作する前提。
    本ロックは呼出元が責任を持って1回だけ取得する。
    """
    lock_path = lock_dir / "resumes.json.lock"
    fd = None
    deadline = time.monotonic() + LOCK_TIMEOUT  # 共通deadline

    # プロセス内排他（残り時間を渡す）
    remaining = max(0, deadline - time.monotonic())
    if not _file_lock.acquire(timeout=remaining):
        raise FileLockTimeoutError(
            f"プロセス内ロック獲得タイムアウト（{LOCK_TIMEOUT}秒）: resumes.json.lock"
        )
    try:
        fd = _os_lock(lock_path, deadline)
        yield
    except (IOError, OSError) as e:
        # yield 内のOSError → ロックエラーに変換せずそのまま再送出
        raise
    finally:
        if fd is not None:
            _os_unlock(fd)
        _file_lock.release()


class JsonResumeRepository(BaseRepository):
    """JSONファイルを使った経歴書のリポジトリ"""

    def __init__(self, filepath: Path):
        self.filepath = Path(filepath)
        self._ensure_file()

    def _ensure_file(self):
        if not self.filepath.exists():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self._save([])

    def _load(self) -> list[dict]:
        """JSONファイルを読み込む（REQ-RE3-04: 読込失敗→RepositoryReadError）"""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except OSError as e:
            raise RepositoryReadError(
                f"JSON読込失敗（OSError）: {self.filepath}"
            ) from e
        except UnicodeError as e:
            raise RepositoryReadError(
                f"JSON読込失敗（UnicodeError）: {self.filepath}"
            ) from e
        except json.JSONDecodeError as e:
            raise RepositoryReadError(
                f"JSON読込失敗（JSONDecodeError）: {self.filepath}"
            ) from e

    def _save(self, data: list[dict]):
        """原子的保存: 一時ファイル → os.replace（REQ-RE2-04/REQ-RE3-04）

        呼出元が acquire_file_lock() を取得済みであること。
        このメソッド内ではロックを取得しない。
        保存失敗時は RepositoryWriteError に変換する。
        """
        tmp_fd = None
        tmp_path = None
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(
                suffix=".json",
                dir=str(self.filepath.parent),
            )
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp_fd = None  # fdopenで閉じた
            os.replace(tmp_path, str(self.filepath))
            tmp_path = None
        except OSError as e:
            raise RepositoryWriteError(
                f"JSON保存失敗（OSError）: {self.filepath}"
            ) from e
        except (TypeError, ValueError) as e:
            raise RepositoryWriteError(
                f"JSON保存失敗（シリアライズエラー）: {self.filepath}"
            ) from e
        finally:
            if tmp_fd is not None:
                os.close(tmp_fd)
            if tmp_path is not None and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    # --- 内部メソッド（ロック取得なし、呼出元責任） ---

    def _find_all(self) -> list[dict]:
        return self._load()

    def _find_by_id(self, item_id: str) -> Optional[dict]:
        data = self._load()
        for item in data:
            if item.get("id") == item_id:
                return item
        return None

    def _create(self, item: dict) -> dict:
        data = self._load()
        if any(d.get("id") == item.get("id") for d in data):
            raise ValueError(f"ID '{item.get('id')}' は既に存在します")
        data.append(item)
        self._save(data)
        return item

    def _update(self, item_id: str, item: dict) -> Optional[dict]:
        data = self._load()
        for i, d in enumerate(data):
            if d.get("id") == item_id:
                item["id"] = item_id
                data[i] = item
                self._save(data)
                return item
        return None

    def _delete(self, item_id: str) -> bool:
        data = self._load()
        for i, d in enumerate(data):
            if d.get("id") == item_id:
                del data[i]
                self._save(data)
                return True
        return False

    def _exists(self, item_id: str) -> bool:
        return self._find_by_id(item_id) is not None

    def _count(self) -> int:
        return len(self._load())

    # --- 公開メソッド（acquire_file_lock 経由） ---

    def find_all(self) -> list[dict]:
        with acquire_file_lock(self.filepath.parent):
            return self._find_all()

    def find_by_id(self, item_id: str) -> Optional[dict]:
        with acquire_file_lock(self.filepath.parent):
            return self._find_by_id(item_id)

    def create(self, item: dict) -> dict:
        with acquire_file_lock(self.filepath.parent):
            return self._create(item)

    def update(self, item_id: str, item: dict) -> Optional[dict]:
        with acquire_file_lock(self.filepath.parent):
            return self._update(item_id, item)

    def delete(self, item_id: str) -> bool:
        with acquire_file_lock(self.filepath.parent):
            return self._delete(item_id)

    def exists(self, item_id: str) -> bool:
        with acquire_file_lock(self.filepath.parent):
            return self._exists(item_id)

    def count(self) -> int:
        with acquire_file_lock(self.filepath.parent):
            return self._count()

    # --- バッチ操作 ---

    def bulk_merge(self, items: list[dict], on_conflict: str = "skip") -> dict:
        """複数アイテムを一括マージ

        ロック取得 → 最新読込 → マージ（on_conflict="skip"で重複防止）
        → 一時保存 → os.replace → 解放

        Args:
            items: マージするアイテムのリスト
            on_conflict: "skip"（デフォルト）— 既存idと重複する場合は追加しない

        Returns:
            {"created": N, "skipped": M}
        """
        with acquire_file_lock(self.filepath.parent):
            data = self._load()
            existing_ids = {d["id"] for d in data}
            created = 0
            skipped = 0
            for item in items:
                item_id = item.get("id")
                if not item_id:
                    skipped += 1
                    continue
                if item_id in existing_ids:
                    skipped += 1
                    continue
                data.append(item)
                existing_ids.add(item_id)
                created += 1
            self._save(data)
            return {"created": created, "skipped": skipped}
