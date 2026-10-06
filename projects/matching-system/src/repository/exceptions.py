"""リポジトリ層の共通例外定義（REQ-RE3-04）

OSError非継承のアプリケーション例外として定義する。
既存の広い `except OSError` による誤分類を解消し、
API層で適切なHTTPステータスコード（503/500）へ変換する。
"""


class RepositoryError(Exception):
    """リポジトリ操作の基底例外"""
    pass


class FileLockTimeoutError(RepositoryError):
    """ファイルロック獲得タイムアウト（API→HTTP 503）"""
    pass


class RepositoryReadError(RepositoryError):
    """JSON読込失敗（API→HTTP 500）"""
    pass


class RepositoryWriteError(RepositoryError):
    """JSON保存失敗（API→HTTP 500）"""
    pass
