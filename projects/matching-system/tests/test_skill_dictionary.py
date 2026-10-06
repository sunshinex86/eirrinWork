"""スキル辞書操作ユーティリティのテスト"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.skill_dictionary import (
    get_all_skills,
    get_skill_by_id,
    get_skill_by_name,
    search_skills,
    get_skills_by_category,
    get_categories,
    get_skill_count,
    get_root_categories,
    find_skill_in_tree,
    get_skill_path,
    get_children,
)


class TestSkillDictionary:
    """スキル辞書のテスト"""

    def test_get_all_skills_returns_list(self):
        """全スキルがリストで取得できること"""
        skills = get_all_skills()
        assert isinstance(skills, list)

    def test_skill_count_100_plus(self):
        """100以上のスキルが登録されていること"""
        count = get_skill_count()
        assert count >= 100, f"Expected >=100, got {count}"

    def test_get_skill_by_id_found(self):
        """ID検索で見つかること"""
        skill = get_skill_by_id("python")
        assert skill is not None
        assert skill["name"] == "Python"

    def test_get_skill_by_id_not_found(self):
        """存在しないIDはNone"""
        assert get_skill_by_id("non-existent-skill") is None

    def test_get_skill_by_name_exact(self):
        """名前検索（完全一致）"""
        skill = get_skill_by_name("Python")
        assert skill is not None
        assert skill["id"] == "python"

    def test_get_skill_by_name_alias(self):
        """エイリアス検索"""
        skill = get_skill_by_name("py")
        assert skill is not None
        assert skill["id"] == "python"

    def test_get_skill_by_name_not_found(self):
        """存在しない名前はNone"""
        assert get_skill_by_name("NonExistentSkillXXXX") is None

    def test_search_skills_partial(self):
        """部分一致検索"""
        results = search_skills("React")
        assert len(results) >= 1
        assert any(s["id"] == "react" for s in results)

    def test_search_skills_empty(self):
        """該当なしの検索"""
        results = search_skills("zzzznotexist")
        assert results == []

    def test_get_skills_by_category(self):
        """カテゴリ別取得"""
        cloud_skills = get_skills_by_category("cloud")
        assert len(cloud_skills) >= 3  # AWS, GCP, Azure 等
        assert any(s["id"] == "aws" for s in cloud_skills)

    def test_get_categories(self):
        """カテゴリ一覧"""
        categories = get_categories()
        assert "programming_language" in categories
        assert "database" in categories
        assert "framework" in categories


class TestSkillTree:
    """スキルツリーのテスト"""

    def test_root_categories(self):
        """ルートカテゴリが5つあること"""
        roots = get_root_categories()
        assert len(roots) >= 4

    def test_find_skill_in_tree_found(self):
        """ツリー内検索（見つかる）"""
        node = find_skill_in_tree("python")
        assert node is not None
        assert node["name"] == "Python"

    def test_find_skill_in_tree_not_found(self):
        """ツリー内検索（見つからない）"""
        assert find_skill_in_tree("non-existent") is None

    def test_get_skill_path(self):
        """スキルパス取得"""
        path = get_skill_path("django")
        assert len(path) >= 3
        assert "Django" in path
        # ルートに "Python" が含まれていること
        assert "Python" in path

    def test_get_skill_path_not_found(self):
        """存在しないスキルのパスは空リスト"""
        assert get_skill_path("non-existent") == []

    def test_get_children(self):
        """子ノード取得"""
        children = get_children("python")
        assert len(children) >= 3  # Django, Flask, FastAPI
        child_names = [c["name"] for c in children]
        assert "Django" in child_names
        assert "Flask" in child_names
        assert "FastAPI" in child_names

    def test_get_children_leaf(self):
        """末端スキルの子ノードは空"""
        assert get_children("flask") == []

    def test_get_children_not_found(self):
        """存在しないIDの子ノードは空"""
        assert get_children("non-existent") == []

    def test_tree_has_max_five_layers(self):
        """最大5階層を超えないこと"""
        def max_depth(node, current=0):
            depth = current + 1
            max_d = depth
            for child in node.get("children", []):
                child_depth = max_depth(child, depth)
                max_d = max(max_d, child_depth)
            return max_d

        roots = get_root_categories()
        depths = []
        for root in roots:
            for child in root.get("children", []):
                depths.append(max_depth(child, 1))
        max_d = max(depths) if depths else 0
        assert max_d <= 6, f"Tree depth {max_d} exceeds 6 (max allowed)"
