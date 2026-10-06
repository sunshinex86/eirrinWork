"""スキル抽出ユーティリティ
自由記述テキストや職歴説明からスキルを抽出・正規化する

REQ-02: SKILL_SYNONYMS 廃止。
スキル辞書（skill_dictionary.py）を唯一の標準化元として利用する。
"""
from .text_utils import normalize_skill_name


def normalize_skill(skill: str) -> str:
    """スキル名を正規化（辞書ベースの skill_id 解決）

    スキル辞書を使って、任意のスキル名・別名から skill_id を返す。
    辞書にないスキルは、正規化後の名前をそのまま返す（未登録スキルとして識別可能）。

    Args:
        skill: スキル名（例: "JS", "JavaScript", "javascript", "Python"）

    Returns:
        skill_id（例: "javascript", "python"）
        辞書にない場合は正規化後の名前（例: "react native"）
    """
    from src.utils.skill_dictionary import resolve_skill_id

    skill_id = resolve_skill_id(skill)
    if skill_id:
        return skill_id

    # 辞書にない場合は正規化後の名前を返す（未登録スキル）
    return normalize_skill_name(skill)


def match_skills(
    candidate_skills: list[str],
    required_skills: list[str],
) -> tuple[list[str], list[str]]:
    """スキルリストの一致を判定（skill_id ベースの比較）

    REQ-02: スキルIDを比較単位とする。

    Returns:
        matched: 一致したスキル一覧
        missing: 不足しているスキル一覧
    """
    candidate_ids = {normalize_skill(s) for s in candidate_skills}
    matched = []
    missing = []

    for req in required_skills:
        req_id = normalize_skill(req)
        if req_id in candidate_ids:
            matched.append(req)
        else:
            # 部分一致も検討（正規化済み）
            found = False
            for cand_id in candidate_ids:
                if cand_id in req_id:
                    matched.append(req)
                    found = True
                    break
                if len(req_id) >= 3 and req_id in cand_id:
                    matched.append(req)
                    found = True
                    break
            if not found:
                missing.append(req)

    return matched, missing


def flatten_skills(skills_obj: dict) -> list[str]:
    """スキルオブジェクト {languages:[], frameworks:[], ...} をフラットリストに変換"""
    result = []
    for key in ("languages", "frameworks", "tools", "certifications", "other"):
        result.extend(skills_obj.get(key, []))
    return result
