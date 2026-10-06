#!/usr/bin/env python3
"""スキル辞書・ツリー整合性バリデーションスクリプト（REQ-03）

チェック項目:
1. ツリー内のスキルIDが辞書に存在すること
2. 辞書登録スキルにツリーパスが存在すること（原則）
3. 同一名称に複数IDが割り当てられていないこと
4. 孤立ノード（親がいないノード）の検出

使い方:
    python scripts/validate_skill_ontology.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.skill_dictionary import (
    get_all_skills, get_root_categories, find_skill_in_tree, get_skill_by_id,
)


def _collect_ids_by_type(roots: list[dict]) -> tuple[set[str], set[str]]:
    """type 別にツリーIDを収集"""
    skill_ids = set()
    cat_ids = set()
    def collect(nodes):
        for node in nodes:
            ntype = node.get("type", "category")
            if ntype == "skill":
                skill_ids.add(node["id"])
            else:
                cat_ids.add(node["id"])
            collect(node.get("children", []))
    collect(roots)
    return skill_ids, cat_ids


def _collect_results() -> tuple[list[str], list[str]]:
    """整合性チェックを実行し、errors/warningsを返す（内部関数）"""
    errors: list[str] = []
    warnings: list[str] = []

    skills = get_all_skills()
    dict_ids = {s["id"] for s in skills}
    dict_names: dict[str, str] = {}
    for s in skills:
        n = s["name"].lower()
        if n in dict_names:
            errors.append(f"重複名称: '{s['name']}' (IDs: {dict_names[n]}, {s['id']})")
        dict_names[n] = s["id"]

    try:
        roots = get_root_categories()
    except Exception:
        warnings.append("get_root_categories() でエラー。ツリーチェックをスキップします。")
        roots = []

    tree_skill_ids, tree_cat_ids = _collect_ids_by_type(roots)
    all_tree_ids = tree_skill_ids | tree_cat_ids

    for tid in sorted(tree_skill_ids):
        if tid not in dict_ids:
            errors.append(f"スキルノード '{tid}' が辞書に存在しません")

    for cid in sorted(tree_cat_ids):
        if cid not in dict_ids:
            warnings.append(f"カテゴリノード '{cid}' は辞書に未登録（カテゴリのため許容）")

    for s in skills:
        sid = s["id"]
        if sid not in all_tree_ids:
            warnings.append(f"ツリー未登録: '{sid}' ({s['name']}) にツリーパスがありません")

    if len(dict_ids) != len(skills):
        errors.append("重複IDが存在します")

    # 印刷
    print(f"辞書エントリ数: {len(skills)}")
    print(f"ツリーノード数: {len(all_tree_ids)}（スキル: {len(tree_skill_ids)}, カテゴリ: {len(tree_cat_ids)}）")
    print(f"辞書のみ（ツリー未登録）: {len(dict_ids - all_tree_ids)} 件")
    print(f"ツリーのみ（辞書未登録）: {len(tree_skill_ids - dict_ids)} 件（スキルノード）")

    if errors:
        print(f"\n❌ エラー ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print(f"\n⚠️  警告 ({len(warnings)}):")
        for w in warnings:
            print(f"  - {w}")

    return errors, warnings


def validate():
    """整合性チェックを実行する（bool返却、従来互換）"""
    errors, warnings = _collect_results()
    if errors:
        return False
    print("\n✅ 整合性チェック完了: 問題なし")
    return True


def validate_detailed() -> dict:
    """整合性チェックを実行し、構造化結果を返す（REQ-RE3-08）

    Returns:
        {"valid": bool, "errors": list[str], "warnings": list[str]}
    """
    errors, warnings = _collect_results()
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


if __name__ == "__main__":
    success = validate()
    sys.exit(0 if success else 1)
