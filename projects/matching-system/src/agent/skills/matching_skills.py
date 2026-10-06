"""マッチングAIエージェントスキル

AIエージェントが実行するスキル関数群。
RAGパイプラインとスキル辞書を活用して、マッチングの高度な分析を提供する。
"""


def analyze_skill_gap(resume_skills: list[str], required_skills: list[str]) -> dict:
    """スキルギャップを分析する

    Args:
        resume_skills: 候補者のスキル一覧
        required_skills: 案件で必要なスキル一覧

    Returns:
        ギャップ分析結果
    """
    from src.utils.skill_extractor import normalize_skill

    resume_normalized = {normalize_skill(s) for s in resume_skills}
    required_normalized = {normalize_skill(s) for s in required_skills}

    matched = resume_normalized & required_normalized
    missing = required_normalized - resume_normalized
    extra = resume_normalized - required_normalized

    return {
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "extra_skills": sorted(extra),
        "match_rate": round(len(matched) / len(required_normalized) * 100, 1) if required_normalized else 100.0,
        "gap_severity": "high" if len(missing) > len(required_normalized) * 0.5 else "medium" if missing else "low",
    }


def get_industry_context(industry_name: str) -> dict:
    """業界に関連する知識をナレッジベースから取得する

    Args:
        industry_name: 業界名

    Returns:
        業界コンテキスト情報
    """
    from src.utils.rag_pipeline import search_knowledge_keyword, get_knowledge_by_category

    # 業界ナレッジを検索
    results = search_knowledge_keyword(industry_name)
    industry_knowledge = [r for r in results if r.get("category") == "industry"]

    # 全業界ナレッジを取得（関連性比較用）
    all_industries = get_knowledge_by_category("industry")

    return {
        "industry": industry_name,
        "found_knowledge": industry_knowledge[:2] if industry_knowledge else [],
        "related_industries": [
            {"id": ind["id"], "summary": ind["content"][:100]}
            for ind in all_industries[:5]
        ],
    }


def suggest_skill_improvements(missing_skills: list[str], target_role: str = "") -> list[dict]:
    """不足スキルに対する改善提案を生成する

    Args:
        missing_skills: 不足しているスキル一覧
        target_role: 目標ロール（任意）

    Returns:
        改善提案リスト
    """
    from src.utils.skill_dictionary import search_skills, get_skill_path

    suggestions = []
    for skill in missing_skills:
        # スキル辞書でスキルを検索
        dict_results = search_skills(skill)
        path = []
        if dict_results:
            path = get_skill_path(dict_results[0]["id"])

        suggestions.append({
            "skill": skill,
            "found_in_dictionary": len(dict_results) > 0,
            "skill_path": " → ".join(path) if path else "",
            "suggestion": _generate_suggestion(skill, dict_results[:1] if dict_results else []),
        })

    return suggestions


def _generate_suggestion(skill: str, dict_info: list[dict]) -> str:
    """スキル改善提案を生成"""
    if dict_info:
        return f"「{dict_info[0]['name']}」は需要の高いスキルです。実務経験または学習を通じて習得することを推奨します。"
    return f"「{skill}」の習得を検討してください。オンラインコースや実務経験でスキルアップが可能です。"


def rank_matches_with_reason(matches: list[dict]) -> list[dict]:
    """マッチ結果を分析して、ランキングと理由を付与する

    REQ-RE3-08: total_score降順で安定ソート後、連番rankを付与。

    Args:
        matches: マッチ結果のリスト（total_score を含む）

    Returns:
        分析済みマッチ結果（スコア降順、rank付き）
    """
    # total_score降順で安定ソート（同点は入力順維持）
    sorted_matches = sorted(matches, key=lambda m: m.get("total_score", 0), reverse=True)
    ranked = []
    for i, match in enumerate(sorted_matches):
        score = match.get("total_score", 0) * 100
        rank = i + 1

        if score >= 80:
            level = "excellent"
            reason = "スキル・経験・ロールの全てが高い適合度を示しています。"
        elif score >= 60:
            level = "good"
            reason = "主要な要件を満たしています。一部のスキル不足は補完可能です。"
        elif score >= 40:
            level = "fair"
            reason = "一部の要件に合致しますが、主要スキルの強化が必要です。"
        else:
            level = "poor"
            reason = "マッチ度が低いです。別の候補を検討することを推奨します。"

        ranked.append({
            "rank": rank,
            "target": match.get("target_name", ""),
            "score": score,
            "level": level,
            "reason": reason,
        })

    return ranked


def validate_skill_consistency(**kwargs) -> dict:
    """スキル辞書とツリーの整合性をチェックする

    REQ-RE3-08: validate_detailed() の構造化結果をそのまま返す。

    Returns:
        検証結果 {"valid": bool, "errors": list[str], "warnings": list[str]}
    """
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
        from scripts.validate_skill_ontology import validate_detailed
        return validate_detailed()
    except Exception as e:
        return {"valid": False, "errors": [str(e)], "warnings": []}


def extract_skills(text: str, use_rag: bool = False, top_k: int = 20) -> dict:
    """テキストからスキルを抽出する（REQ-10: 共通サービス呼出し）"""
    from src.utils.skill_extraction_service import extract_skills_service
    return extract_skills_service(text=text, use_rag=use_rag, top_k=top_k)
