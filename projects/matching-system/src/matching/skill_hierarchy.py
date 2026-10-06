"""スキル階層スコアリング（REQ-04）

スキルツリーの親子関係を利用したマッチングスコア計算。
完全一致、子→親、親→子で異なる係数を設定する。
"""
from typing import Optional


def _find_node(tree_roots: list[dict], skill_id: str) -> Optional[dict]:
    """ツリー内のノードを skill_id で検索"""
    def _search(nodes):
        for node in nodes:
            if node["id"] == skill_id:
                return node
            result = _search(node.get("children", []))
            if result:
                return result
        return None
    return _search(tree_roots)


def _get_path_to_root(tree_roots: list[dict], skill_id: str) -> list[str]:
    """ルートから指定スキルまでのIDパスを取得"""
    def _search(nodes, path: list[str]) -> Optional[list[str]]:
        for node in nodes:
            current = path + [node["id"]]
            if node["id"] == skill_id:
                return current
            result = _search(node.get("children", []), current)
            if result:
                return result
        return None
    return _search(tree_roots, []) or []


def compute_hierarchy_coefficient(
    candidate_skill_id: str,
    required_skill_id: str,
    tree_roots: list[dict],
    exact_match: float = 1.0,
    child_to_parent: float = 0.5,
    parent_to_child: float = 0.3,
) -> tuple[float, str]:
    """スキル階層に基づく係数を計算（REQ-04）

    Args:
        candidate_skill_id: 候補者が持つスキルID
        required_skill_id: 案件で要求されるスキルID
        tree_roots: スキルツリーのルートノード一覧
        exact_match: 完全一致の係数（デフォルト1.0）
        child_to_parent: 子→親の係数（デフォルト0.5）
        parent_to_child: 親→子の係数（デフォルト0.3）

    Returns:
        (係数, 一致理由)
    """
    if candidate_skill_id == required_skill_id:
        return exact_match, "完全一致"

    cand_path = _get_path_to_root(tree_roots, candidate_skill_id)
    req_path = _get_path_to_root(tree_roots, required_skill_id)

    if not cand_path or not req_path:
        return 0.0, "ツリー上で関係なし"

    # 子→親: 候補者のスキルが案件要件の子孫にあたる
    # （例: Spring Boot 経験者 → Spring 要件）
    if required_skill_id in cand_path:
        cand_idx = cand_path.index(candidate_skill_id)
        req_idx = cand_path.index(required_skill_id)
        if req_idx < cand_idx:  # 要件が上流（親）
            return child_to_parent, f"子スキル「{candidate_skill_id}」→親スキル「{required_skill_id}」"

    # 親→子: 候補者のスキルが案件要件の祖先にあたる
    # （例: Java 経験のみ → Spring Boot 要件: 部分適合）
    if candidate_skill_id in req_path:
        cand_idx = req_path.index(candidate_skill_id)
        req_idx = req_path.index(required_skill_id)
        if cand_idx < req_idx:  # 候補者が上流（親）
            return parent_to_child, f"親スキル「{candidate_skill_id}」→子スキル「{required_skill_id}」（部分適合）"

    return 0.0, "ツリー上で関係なし"


def compute_hierarchy_score(
    candidate_ids: set[str],
    required_ids: set[str],
    tree_roots: list[dict],
    exact_coeff: float = 1.0,
    child_parent_coeff: float = 0.5,
    parent_child_coeff: float = 0.3,
) -> tuple[float, list[str]]:
    """スキルセット間の階層スコアを計算

    Args:
        candidate_ids: 候補者のスキルID一覧
        required_ids: 案件の必須スキルID一覧
        tree_roots: スキルツリー
        exact_coeff, child_parent_coeff, parent_child_coeff: 各階層の係数

    Returns:
        (スコア, 説明文リスト)
    """
    if not required_ids:
        return 1.0, []

    total_score = 0.0
    reasons = []
    for req_id in required_ids:
        best_coeff = 0.0
        best_reason = "該当なし"
        for cand_id in candidate_ids:
            coeff, reason = compute_hierarchy_coefficient(
                cand_id, req_id, tree_roots,
                exact_coeff, child_parent_coeff, parent_child_coeff,
            )
            if coeff > best_coeff:
                best_coeff = coeff
                best_reason = reason
        total_score += best_coeff
        if best_reason != "該当なし":
            reasons.append(f"{req_id}: {best_reason}")

    return total_score / len(required_ids), reasons
