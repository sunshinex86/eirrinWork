"""スキル階層スコアリングのテスト"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.matching.skill_hierarchy import (
    compute_hierarchy_coefficient,
    compute_hierarchy_score,
)


SAMPLE_TREE = [
    {
        "id": "programming",
        "name": "プログラミング",
        "children": [
            {
                "id": "python",
                "name": "Python",
                "children": [
                    {"id": "django", "name": "Django", "children": []},
                    {"id": "flask", "name": "Flask", "children": []},
                ]
            },
            {
                "id": "java",
                "name": "Java",
                "children": [
                    {
                        "id": "spring",
                        "name": "Spring",
                        "children": [
                            {"id": "spring-boot", "name": "Spring Boot", "children": []},
                        ]
                    }
                ]
            },
        ]
    }
]


class TestHierarchyCoefficient:
    """階層係数計算のテスト"""

    def test_exact_match(self):
        """完全一致: 1.0"""
        coeff, reason = compute_hierarchy_coefficient("python", "python", SAMPLE_TREE)
        assert coeff == 1.0
        assert "完全一致" in reason

    def test_child_to_parent(self):
        """子→親: 0.5（Spring Boot → Spring）"""
        coeff, reason = compute_hierarchy_coefficient("spring-boot", "spring", SAMPLE_TREE)
        assert coeff == 0.5
        assert "子スキル" in reason

    def test_parent_to_child(self):
        """親→子: 0.3（Java → Spring Boot）"""
        coeff, reason = compute_hierarchy_coefficient("java", "spring-boot", SAMPLE_TREE)
        assert coeff == 0.3
        assert "親スキル" in reason

    def test_no_relation(self):
        """関係なし: 0.0"""
        coeff, reason = compute_hierarchy_coefficient("python", "spring-boot", SAMPLE_TREE)
        assert coeff == 0.0

    def test_custom_coefficients(self):
        """カスタム係数"""
        coeff, _ = compute_hierarchy_coefficient(
            "spring-boot", "spring", SAMPLE_TREE,
            exact_match=1.0, child_to_parent=0.8, parent_to_child=0.4,
        )
        assert coeff == 0.8


class TestHierarchyScore:
    """統合階層スコアのテスト"""

    def test_all_exact_match(self):
        """全件完全一致"""
        score, reasons = compute_hierarchy_score(
            {"python", "java"}, {"python", "java"}, SAMPLE_TREE,
        )
        assert score == 1.0

    def test_mixed_match(self):
        """混合マッチ"""
        score, reasons = compute_hierarchy_score(
            {"python", "spring-boot"}, {"python", "spring"}, SAMPLE_TREE,
        )
        assert 0.5 < score < 1.0  # python(1.0) + spring-boot→spring(0.5) = 1.5/2 = 0.75
        assert score == 0.75

    def test_no_required(self):
        """要件なし"""
        score, reasons = compute_hierarchy_score({"python"}, set(), SAMPLE_TREE)
        assert score == 1.0
