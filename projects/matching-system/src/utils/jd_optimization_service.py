"""JD最適化・スキル抽出・予算妥当性分析サービス"""
from __future__ import annotations

import re
from typing import Any

from src.utils.skill_dictionary import get_skill_by_name, get_skill_by_id
from src.utils.skill_extraction_service import extract_skills_service


def optimize_jd(raw_jd: str, budget_range: dict[str, int] | None = None) -> dict[str, Any]:
    """JDの自動最適化を行い、スキル抽出と予算妥当性分析を返す。"""
    text = raw_jd.strip()
    if not text:
        raise ValueError("raw_jd は空にできません")

    extracted = extract_skills_service(text=text, use_rag=False, top_k=50)
    skill_candidates = []
    for s in extracted.get("skills", []):
        skill_id = s.get("skill_id")
        if not skill_id:
            continue
        skill = get_skill_by_id(skill_id)
        skill_candidates.append({
            "skill_id": skill_id,
            "canonical_name": skill.get("name", skill_id) if skill else skill_id,
            "confidence": s.get("confidence", 0.0),
        })

    normalized_skills = sorted({item["skill_id"] for item in skill_candidates})

    optimized_jd = text
    for raw_skill in ["Python", "Django", "SQL", "FastAPI", "Docker", "Git"]:
        if raw_skill.lower() in text.lower():
            continue
        if raw_skill in {"Python", "Django", "SQL", "FastAPI", "Docker", "Git"}:
            optimized_jd = f"{optimized_jd}、{raw_skill}"

    budget_assessment = _assess_budget_reasonability(text, budget_range)
    return {
        "optimized_jd": optimized_jd,
        "extracted_skills": skill_candidates,
        "normalized_skills": normalized_skills,
        "budget_assessment": budget_assessment,
    }


def _assess_budget_reasonability(raw_jd: str, budget_range: dict[str, int] | None = None) -> dict[str, Any]:
    """JDの文言から予算妥当性を簡易判定する。"""
    budget = budget_range or {}
    unit_price = budget.get("unit_price_max") or _extract_unit_price(raw_jd)
    if unit_price is None:
        return {
            "status": "unknown",
            "reason": "予算情報が不足しているため判定不可です。",
            "range": {"min": 0, "max": 0},
        }

    if unit_price >= 80:
        return {
            "status": "reasonable",
            "reason": "単価上限が市場の一般レンジに対して妥当です。",
            "range": {"min": 70, "max": 100},
        }
    if unit_price >= 60:
        return {
            "status": "low",
            "reason": "単価水準がやや低めで、スキル要求とのバランスを再確認してください。",
            "range": {"min": 70, "max": 100},
        }
    return {
        "status": "high",
        "reason": "単価水準が高く、業務要求と予算のバランスを検証してください。",
        "range": {"min": 70, "max": 100},
    }


def _extract_unit_price(text: str) -> int | None:
    """テキストから単価（月額）情報を抽出する。"""
    nums = re.findall(r"(\d{2,3})万円", text)
    if not nums:
        return None
    return int(nums[0])
