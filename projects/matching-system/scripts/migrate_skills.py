#!/usr/bin/env python3
"""スキルデータ移行スクリプト

既存の文字列リスト形式のスキルを、REQ-01 の属性付きスキル形式に変換する。

使い方:
    python scripts/migrate_skills.py          # 実際の移行
    python scripts/migrate_skills.py --dry-run # 変更前に確認
"""
import argparse
import json
import sys
from pathlib import Path

# プロジェクトルート
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.utils.skill_dictionary import get_skill_by_name


def _estimate_level(years: float, total_exp: int) -> int:
    """経験年数からスキルレベルを推定（移行時のヒューリスティック）"""
    # 経歴書の総経験年数を基準にレベル推定
    if total_exp >= 10:
        base_level = 4
    elif total_exp >= 7:
        base_level = 3
    elif total_exp >= 4:
        base_level = 2
    else:
        base_level = 1

    # 個別スキルの経験年数で微調整
    if years >= 8:
        return min(base_level + 1, 5)
    elif years >= 5:
        return base_level
    elif years >= 2:
        return max(base_level - 1, 1)
    else:
        return max(base_level - 2, 1)


def _compute_last_used_year(work_history: list) -> int:
    """職歴から最後に使用した年を推定"""
    current_year = 2026
    # 最新の職歴の終了年を基準に
    for wh in reversed(work_history):
        end = wh.get("end_date")
        if end is None:
            return current_year  # 現在も就業中
        try:
            year = int(end[:4])
            return year
        except (ValueError, TypeError):
            pass
    return current_year


def _migrate_skills(skills_obj: dict, work_history: list, total_exp: int) -> list[dict]:
    """文字列リスト形式のスキルを属性付き形式に変換"""
    new_skills = []
    last_used = _compute_last_used_year(work_history)

    for category in ("languages", "frameworks", "tools", "certifications", "other"):
        skill_names = skills_obj.get(category, [])
        for name in skill_names:
            # スキル辞書で ID を検索
            skill_entry = get_skill_by_name(name)
            skill_id = skill_entry["id"] if skill_entry else name.lower().replace(" ", "_").replace(".", "")
            # 経験年数を推定（カテゴリと総経験年数から）
            if category == "languages":
                years = max(1, int(total_exp * 0.8))
            elif category == "frameworks":
                years = max(1, int(total_exp * 0.5))
            else:
                years = max(1, int(total_exp * 0.3))

            level = _estimate_level(years, total_exp)

            new_skills.append({
                "skill_id": skill_id,
                "level": level,
                "years": years,
                "last_used_year": last_used,
                "estimated": True,
            })
    return new_skills


def _migrate_resume(resume: dict) -> dict:
    """1件の経歴書を移行（旧形式は維持、structured_* に新形式を保存）"""
    new = dict(resume)
    old_skills = new.get("skills", {})
    new["structured_skills"] = _migrate_skills(
        old_skills,
        new.get("work_history", []),
        new.get("years_of_experience", 0),
    )
    return new


def _migrate_job_skills(skills_obj: dict) -> list[dict]:
    """案件のスキルを移行"""
    new_skills = []
    for category in ("languages", "frameworks", "tools", "certifications", "other"):
        skill_names = skills_obj.get(category, [])
        for name in skill_names:
            skill_entry = get_skill_by_name(name)
            skill_id = skill_entry["id"] if skill_entry else name.lower().replace(" ", "_").replace(".", "")
            new_skills.append({
                "skill_id": skill_id,
                "required_level": 3,
                "required_years": 3,
            })
    return new_skills


def _migrate_job(job: dict) -> dict:
    """1件の案件を移行（旧形式は維持、structured_* に新形式を保存）"""
    new = dict(job)
    if "required_skills" in new:
        new["structured_required_skills"] = _migrate_job_skills(new.get("required_skills", {}))
    if "preferred_skills" in new:
        new["structured_preferred_skills"] = _migrate_job_skills(new.get("preferred_skills", {}))
    return new


def migrate_file(input_path: Path, output_path: Path, item_type: str, dry_run: bool):
    """ファイル単位で移行"""
    with open(input_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    if not isinstance(items, list):
        print(f"  ERROR: {input_path.name} は配列形式ではありません")
        return

    migrated = []
    for item in items:
        if item_type == "resume":
            migrated.append(_migrate_resume(item))
        elif item_type == "job":
            migrated.append(_migrate_job(item))

    if dry_run:
        print(f"  [DRY-RUN] {input_path.name}: {len(items)} → {len(migrated)} items")
        if migrated:
            sample = migrated[0]
            sample_skills = sample.get('structured_skills', [])
            print(f"    sample structured_skills ({len(sample_skills)}): {sample_skills[:2]}...")
        return

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(migrated, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {input_path.name}: {len(items)} → {len(migrated)} items migrated")


def main():
    parser = argparse.ArgumentParser(description="スキルデータ移行スクリプト")
    parser.add_argument("--dry-run", action="store_true", help="変更を適用せずに確認のみ")
    args = parser.parse_args()

    data_dir = ROOT / "data"

    files = [
        ("resumes.json", "resumes.json.bak", "resume"),
        ("jobs.json", "jobs.json.bak", "job"),
        ("sample_resumes.json", "sample_resumes.json.bak", "resume"),
        ("sample_jobs.json", "sample_jobs.json.bak", "job"),
    ]

    for src_name, bak_name, item_type in files:
        src_path = data_dir / src_name
        if not src_path.exists():
            continue

        print(f"[FILE] {src_name} ({item_type})")
        if not args.dry_run:
            # バックアップ
            bak_path = data_dir / bak_name
            if not bak_path.exists():
                import shutil
                shutil.copy2(src_path, bak_path)
                print(f"  [backup] {bak_name}")

        migrate_file(src_path, src_path, item_type, dry_run=args.dry_run)

    result = "移行完了" if not args.dry_run else "DRY-RUN 完了（変更は適用されていません）"
    print(f"\n[OK] {result}")


if __name__ == "__main__":
    main()
