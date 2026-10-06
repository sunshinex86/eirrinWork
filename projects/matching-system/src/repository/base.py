"""Repository抽象基底クラス
データアクセス層を抽象化し、将来のDB移行を容易にする
"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseRepository(ABC):
    """データアクセスの抽象基底クラス"""

    @abstractmethod
    def find_all(self) -> list:
        """全件取得"""
        ...

    @abstractmethod
    def find_by_id(self, item_id: str) -> Optional[dict]:
        """IDで1件取得"""
        ...

    @abstractmethod
    def create(self, item: dict) -> dict:
        """新規作成"""
        ...

    @abstractmethod
    def update(self, item_id: str, item: dict) -> Optional[dict]:
        """更新（存在しないIDの場合はNoneを返す）"""
        ...

    @abstractmethod
    def delete(self, item_id: str) -> bool:
        """削除（存在しないIDの場合はFalseを返す）"""
        ...

    @abstractmethod
    def exists(self, item_id: str) -> bool:
        """IDの存在確認"""
        ...
