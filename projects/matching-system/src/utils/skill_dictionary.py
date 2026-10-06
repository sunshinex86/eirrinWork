"""スキル辞書操作ユーティリティ

`data/skills/skill_dictionary.json` と `data/skills/skill_tree.json` を
操作するためのインターフェース。
"""
import json
from pathlib import Path
from typing import Optional


_SKILL_DICT_PATH = Path(__file__).parent.parent.parent / "data" / "skills" / "skill_dictionary.json"
_SKILL_TREE_PATH = Path(__file__).parent.parent.parent / "data" / "skills" / "skill_tree.json"

# キャッシュ
_skill_dict: Optional[dict] = None
_skill_tree: Optional[dict] = None


def _load_dictionary() -> dict:
    """スキル辞書をロードする（キャッシュあり）"""
    global _skill_dict
    if _skill_dict is None:
        with open(_SKILL_DICT_PATH, "r", encoding="utf-8") as f:
            _skill_dict = json.load(f)
    return _skill_dict


def _load_tree() -> dict:
    """スキルツリーをロードする（キャッシュあり）"""
    global _skill_tree
    if _skill_tree is None:
        with open(_SKILL_TREE_PATH, "r", encoding="utf-8") as f:
            _skill_tree = json.load(f)
    return _skill_tree


def get_all_skills() -> list[dict]:
    """全スキル一覧を取得"""
    data = _load_dictionary()
    return data["skills"]


def get_skill_by_id(skill_id: str) -> Optional[dict]:
    """スキルIDからスキルを検索"""
    for skill in get_all_skills():
        if skill["id"] == skill_id:
            return skill
    return None


def get_skill_by_name(name: str) -> Optional[dict]:
    """スキル名（正規化前）からスキルを検索"""
    name_lower = name.strip().lower()
    for skill in get_all_skills():
        if skill["name"].lower() == name_lower:
            return skill
        for alias in skill.get("aliases", []):
            if alias.lower() == name_lower:
                return skill
    return None


def resolve_skill_id(name: str) -> Optional[str]:
    """スキル名/別名から skill_id を解決する（REQ-02: 唯一の標準化元）

    辞書に登録されているスキル名またはエイリアスから、正規化された skill_id を返す。
    未登録スキルの場合は None を返す（未登録スキルの識別に対応）。

    Args:
        name: スキル名（例: "JS", "JavaScript", "javascript" のいずれも）

    Returns:
        skill_id（例: "javascript"）、未登録の場合は None
    """
    skill = get_skill_by_name(name)
    if skill:
        return skill["id"]

    # テキスト正規化して再検索
    from src.utils.text_utils import normalize_skill_name
    normalized = normalize_skill_name(name)
    # 正規化後の名前で直接マッチしないか確認
    for skill in get_all_skills():
        if normalize_skill_name(skill["name"]) == normalized:
            return skill["id"]
        for alias in skill.get("aliases", []):
            if normalize_skill_name(alias) == normalized:
                return skill["id"]
    return None


def search_skills(query: str) -> list[dict]:
    """スキル名・エイリアスで部分一致検索"""
    q = query.strip().lower()
    results = []
    for skill in get_all_skills():
        if q in skill["name"].lower():
            results.append(skill)
            continue
        for alias in skill.get("aliases", []):
            if q in alias.lower():
                results.append(skill)
                break
    return results


def get_skills_by_category(category: str) -> list[dict]:
    """カテゴリ別にスキルを取得"""
    return [s for s in get_all_skills() if s.get("category") == category]


def get_categories() -> list[str]:
    """全カテゴリ一覧を取得"""
    categories = set()
    for skill in get_all_skills():
        cat = skill.get("category")
        if cat:
            categories.add(cat)
    return sorted(categories)


def get_skill_count() -> int:
    """登録済みスキル数を取得"""
    return len(get_all_skills())


def get_root_categories() -> list[dict]:
    """スキルツリーのルートカテゴリ一覧を取得"""
    tree = _load_tree()
    return tree["roots"]


def find_skill_in_tree(skill_id: str) -> Optional[dict]:
    """スキルツリー内のスキルノードを検索"""
    def _search(node):
        if node["id"] == skill_id:
            return node
        for child in node.get("children", []):
            result = _search(child)
            if result:
                return result
        return None

    for root in get_root_categories():
        result = _search(root)
        if result:
            return result
    return None


def get_skill_path(skill_id: str) -> list[str]:
    """スキルツリー内のルートからのパスを取得"""
    def _search(node, path):
        current_path = path + [node["name"]]
        if node["id"] == skill_id:
            return current_path
        for child in node.get("children", []):
            result = _search(child, current_path)
            if result:
                return result
        return None

    for root in get_root_categories():
        result = _search(root, [])
        if result:
            return result
    return []


def get_children(skill_id: str) -> list[dict]:
    """スキルの子ノード一覧を取得"""
    node = find_skill_in_tree(skill_id)
    if node:
        return node.get("children", [])
    return []


def invalidate_cache():
    """キャッシュをクリアする（辞書・ツリー更新後に呼び出す）"""
    global _skill_dict, _skill_tree
    _skill_dict = None
    _skill_tree = None


# --- CRUD操作（FIX-06） ---

def _write_dictionary(data: dict) -> None:
    """スキル辞書を安全に書き込む（OSロック + 一時ファイル + 原子的置換）"""
    import tempfile, os
    from src.repository.exceptions import FileLockTimeoutError, RepositoryWriteError
    lock_path = _SKILL_DICT_PATH.with_suffix(".json.lock")
    deadline = 10.0  # seconds
    import time, json as _json
    start = time.time()
    while time.time() - start < deadline:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            time.sleep(0.05)
    else:
        raise FileLockTimeoutError(f"スキル辞書のロック取得に失敗: {lock_path}")
    try:
        tmp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False,
                                          dir=str(_SKILL_DICT_PATH.parent), suffix=".tmp")
        try:
            _json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.close()
            os.replace(tmp.name, str(_SKILL_DICT_PATH))
        except Exception:
            if tmp and not tmp.closed:
                tmp.close()
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)
            raise RepositoryWriteError(f"スキル辞書の書込みに失敗")
    finally:
        if os.path.exists(str(lock_path)):
            os.unlink(str(lock_path))
    invalidate_cache()


def add_skill(name: str, category: str = "", aliases: list[str] | None = None,
              parent_id: str | None = None) -> dict:
    """新規スキルを登録

    Args:
        name: スキル名（重複不可）
        category: カテゴリ
        aliases: 別名リスト
        parent_id: スキルツリー上の親ID（省略時は未分類）

    Returns:
        登録されたスキル辞書

    Raises:
        ValueError: 同名スキルが既に存在する場合
    """
    # 重複チェック
    existing = get_skill_by_name(name)
    if existing:
        raise ValueError(f"同名スキル'{name}'が既に存在します (id={existing['id']})")
    # 別名の重複チェック
    normalized_aliases = [a.strip() for a in (aliases or []) if a.strip()]
    # 入力内の重複
    if len(set(a.lower() for a in normalized_aliases)) != len(normalized_aliases):
        raise ValueError("別名リスト内に重複があります")
    # 名称と別名の自己重複
    for alias in normalized_aliases:
        if alias.lower() == name.strip().lower():
            raise ValueError(f"別名'{alias}'はスキル名称と同じです")
        conflict = get_skill_by_name(alias)
        if conflict:
            raise ValueError(f"別名'{alias}'は既存スキル'{conflict['name']}'の名称または別名と重複します")
    # ID重複チェック
    import re
    skill_id = re.sub(r'[^a-z0-9_]', '_', name.strip().lower())
    base_id = skill_id
    counter = 1
    while get_skill_by_id(skill_id):
        skill_id = f"{base_id}_{counter}"
        counter += 1

    data = _load_dictionary()
    new_skill = {
        "id": skill_id,
        "name": name,
        "category": category,
        "aliases": aliases or [],
    }
    data["skills"].append(new_skill)
    _write_dictionary(data)

    # ツリーにも追加（parent_id指定時）
    if parent_id:
        _add_to_tree(skill_id, parent_id)

    # 整合性検証
    issues = validate_consistency()
    if issues:
        import logging
        logging.getLogger(__name__).warning(f"スキル辞書整合性問題: {issues}")

    return new_skill


def _add_to_tree(skill_id: str, parent_id: str) -> None:
    """スキルをツリーに追加（OSロック+一時ファイル+原子的置換）"""
    import tempfile, os, json as _json, time
    from src.repository.exceptions import FileLockTimeoutError
    lock_path = _SKILL_TREE_PATH.with_suffix(".json.lock")
    deadline = 10.0
    start = time.time()
    while time.time() - start < deadline:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            time.sleep(0.05)
    else:
        raise FileLockTimeoutError(f"スキルツリーのロック取得に失敗: {lock_path}")
    try:
        # ロック保持下で読込→変更→書込
        invalidate_cache()
        tree = _load_tree()
        def _insert(node):
            if node["id"] == parent_id:
                node.setdefault("children", []).append({"id": skill_id, "name": skill_id, "children": []})
                return True
            for child in node.get("children", []):
                if _insert(child):
                    return True
            return False
        inserted = any(_insert(root) for root in tree["roots"])
        if not inserted:
            return  # parent_id が見つからない場合は追加しない
        tmp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False,
                                          dir=str(_SKILL_TREE_PATH.parent), suffix=".tmp")
        try:
            _json.dump(tree, tmp, ensure_ascii=False, indent=2)
            tmp.close()
            os.replace(tmp.name, str(_SKILL_TREE_PATH))
        except Exception:
            if tmp and not tmp.closed:
                tmp.close()
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)
            raise
    finally:
        if os.path.exists(str(lock_path)):
            os.unlink(str(lock_path))
    invalidate_cache()


def update_skill(skill_id: str, name: str | None = None, category: str | None = None,
                 aliases: list[str] | None = None) -> dict:
    """スキル情報を更新

    Raises:
        ValueError: 存在しないskill_idまたは同名スキル重複
    """
    data = _load_dictionary()
    for skill in data["skills"]:
        if skill["id"] == skill_id:
            # 全ての検証を先に実施（データ変更前に完了）
            new_name = name if name is not None else None
            new_normalized = None
            if new_name is not None:
                existing = get_skill_by_name(new_name)
                if existing and existing["id"] != skill_id:
                    raise ValueError(f"同名スキル'{new_name}'が既に存在します")
                # 新しい名称が自身の既存aliasと重複しないか
                for alias in skill.get("aliases", []):
                    if alias.lower() == new_name.strip().lower():
                        raise ValueError(f"新しい名称'{new_name}'は既存の別名'{alias}'と重複します")
            if aliases is not None:
                new_normalized = [a.strip() for a in aliases if a.strip()]
                if len(set(a.lower() for a in new_normalized)) != len(new_normalized):
                    raise ValueError("別名リスト内に重複があります")
                current_name = new_name if new_name is not None else skill["name"]
                for alias in new_normalized:
                    if alias.lower() == current_name.strip().lower():
                        raise ValueError(f"別名'{alias}'はスキル名称と同じです")
                    conflict = get_skill_by_name(alias)
                    if conflict and conflict["id"] != skill_id:
                        raise ValueError(f"別名'{alias}'は既存スキル'{conflict['name']}'の名称または別名と重複します")
            # 検証通過後に一括更新
            if new_name is not None:
                skill["name"] = new_name
            if category is not None:
                skill["category"] = category
            if new_normalized is not None:
                skill["aliases"] = new_normalized
            _write_dictionary(data)
            issues = validate_consistency()
            if issues:
                import logging
                logging.getLogger(__name__).warning(f"スキル辞書整合性問題: {issues}")
            return skill
    raise ValueError(f"skill_id '{skill_id}' が見つかりません")


def delete_skill(skill_id: str) -> dict:
    """スキルを論理削除（無効化）

    Job/Resumeから参照されている場合は物理削除せず無効化する。
    enabled=false としてマークする。

    Returns:
        更新後のスキル辞書
    """
    data = _load_dictionary()
    for skill in data["skills"]:
        if skill["id"] == skill_id:
            skill["enabled"] = False
            _write_dictionary(data)
            issues = validate_consistency()
            if issues:
                import logging
                logging.getLogger(__name__).warning(f"スキル辞書整合性問題: {issues}")
            return skill
    raise ValueError(f"skill_id '{skill_id}' が見つかりません")


def get_skill_references(skill_id: str) -> dict:
    """スキルを参照しているResume/Jobを検索

    Returns:
        {"resumes": [id, ...], "jobs": [id, ...]}
    """
    import config
    from src.repository.json_resume_repo import JsonResumeRepository
    from src.repository.json_job_repo import JsonJobRepository
    from src.repository.exceptions import RepositoryError

    refs: dict[str, list[str]] = {"resumes": [], "jobs": []}

    try:
        resume_repo = JsonResumeRepository(config.RESUMES_FILE)
        for r in resume_repo.find_all():
            for s in r.get("structured_skills", []):
                sid = s.get("skill_id", "") if isinstance(s, dict) else getattr(s, "skill_id", "")
                if sid == skill_id:
                    refs["resumes"].append(r["id"])
                    break
    except (RepositoryError, FileNotFoundError):
        pass

    try:
        job_repo = JsonJobRepository(config.JOBS_FILE)
        for j in job_repo.find_all():
            for key in ("structured_required_skills", "structured_preferred_skills"):
                for s in j.get(key, []):
                    sid = s.get("skill_id", "") if isinstance(s, dict) else getattr(s, "skill_id", "")
                    if sid == skill_id:
                        refs["jobs"].append(j["id"])
                        break
    except (RepositoryError, FileNotFoundError):
        pass

    return refs


def validate_consistency() -> list[str]:
    """スキル辞書とスキルツリーの整合性を検証

    Returns:
        問題点のメッセージリスト（空リスト=整合）
    """
    issues: list[str] = []
    dict_ids = {s["id"] for s in get_all_skills()}

    def _check_node(node: dict) -> None:
        if node["id"] not in dict_ids and node.get("type") != "category":
            issues.append(f"ツリーに存在するID '{node['id']}' が辞書にありません")
        for child in node.get("children", []):
            _check_node(child)

    try:
        for root in get_root_categories():
            _check_node(root)
    except Exception as e:
        issues.append(f"ツリー検証エラー: {e}")

    return issues
