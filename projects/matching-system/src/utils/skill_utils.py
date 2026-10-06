"""スキル操作ユーティリティ（FIX-04）

重複スキルの統合・検証を行う共通サービス。
Resumeは統合、Jobは重複エラー、スコアリング層は防御的統合。
"""
import datetime
from typing import Optional


def _key(skill: dict) -> str:
    """スキルアイテムからskill_idを取得（dict/list両対応）"""
    return skill["skill_id"] if isinstance(skill, dict) else skill.skill_id


def deduplicate_resume_skills(skills: list[dict]) -> list[dict]:
    """Resumeのstructured_skillsを統合する（FIX-04）

    Pydantic検証前に呼び出す。同一skill_idを統合:
    - level: 最大値
    - years: 最大値
    - last_used_year: 最新年
    - estimated: いずれかがTrueならTrue

    Args:
        skills: 統合前のスキルリスト

    Returns:
        統合後のスキルリスト（同一skill_idは1件）
    """
    merged: dict[str, dict] = {}
    for s in skills:
        sid = _key(s)
        if sid not in merged:
            merged[sid] = dict(s) if isinstance(s, dict) else s.model_dump()
            continue
        existing = merged[sid]
        # level: 最大値
        for field in ("level", "years"):
            v = s.get(field, 0) if isinstance(s, dict) else getattr(s, field, 0)
            ev = existing.get(field, 0)
            if v is not None and (ev is None or v > ev):
                existing[field] = v
        # last_used_year: 最新年
        v = s.get("last_used_year", 0) if isinstance(s, dict) else getattr(s, "last_used_year", 0)
        ev = existing.get("last_used_year", 0)
        if v is not None and (ev is None or v > ev):
            existing["last_used_year"] = v
        # estimated: OR
        v = s.get("estimated", False) if isinstance(s, dict) else getattr(s, "estimated", False)
        if v:
            existing["estimated"] = True
    return list(merged.values())


def validate_job_skills_no_duplicates(skills: list[dict], field_name: str = "structured_skills") -> None:
    """Jobスキルリスト内の同一skill_id重複をチェック（FIX-04）

    Raises:
        ValueError: 重複が見つかった場合
    """
    seen: set[str] = set()
    for s in skills:
        sid = _key(s)
        if sid in seen:
            raise ValueError(f"同一skill_id '{sid}' が {field_name} 内で重複しています")
        seen.add(sid)


def deduplicate_job_skills_defensive(skills: list[dict]) -> list[dict]:
    """Jobスキルの防御的重複統合（FIX-04）

    required_level / required_years も統合する（最大値）。
    スコアリング層で使用。
    """
    merged: dict[str, dict] = {}
    for s in skills:
        sid = _key(s)
        if sid not in merged:
            merged[sid] = dict(s) if isinstance(s, dict) else s.model_dump()
            continue
        existing = merged[sid]
        for field in ("required_level", "required_years", "level", "years"):
            v = s.get(field, 0) if isinstance(s, dict) else getattr(s, field, 0)
            ev = existing.get(field, 0)
            if v is not None and (ev is None or v > ev):
                existing[field] = v
    return list(merged.values())


def deduplicate_skills_defensive(skills: list[dict]) -> list[dict]:
    """スコアリング層の防御的重複統合（FIX-04）

    既存不正データに対する安全策。使用元がResumeかJobかに応じて適切な統合を行う。
    マッチング計算の直前に使用する。
    """
    # required_levelフィールドの有無でJob/Resumeを判定
    if skills and ("required_level" in skills[0] or "required_years" in skills[0]):
        return deduplicate_job_skills_defensive(skills)
    return deduplicate_resume_skills(skills)
