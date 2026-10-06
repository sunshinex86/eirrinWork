"""多要素重み付きマッチングスコアラー

経歴書と案件の間のマッチングスコアを計算するコアエンジン。
5つの評価軸（スキル・経験・勤務地・業界・年収）の重み付き線形和。
"""
from config import MATCHING_WEIGHTS, INDUSTRY_GROUPS
from src.utils.skill_extractor import match_skills, flatten_skills


def _compute_skill_score(resume_skills: dict, job_required: dict, job_preferred: dict) -> tuple[float, list[str], list[str], list[str]]:
    """スキル一致スコアを計算

    必須スキルは2倍重み、歓迎スキルは1倍重み。
    必須スキルが1つでも不足している場合、スコアは0.6でキャップ。

    Returns:
        score: 0-1のスコア
        matched: 一致したスキル一覧
        missing_required: 不足している必須スキル
        missing_preferred: 不足している歓迎スキル
    """
    resume_flat = flatten_skills(resume_skills)
    required_flat = flatten_skills(job_required)
    preferred_flat = flatten_skills(job_preferred)

    matched_required, missing_required = match_skills(resume_flat, required_flat)
    matched_preferred, missing_preferred = match_skills(resume_flat, preferred_flat)

    # 必須: 2倍重み, 歓迎: 1倍重み
    max_possible = len(required_flat) * 2 + len(preferred_flat)
    if max_possible == 0:
        return 1.0, [], [], []

    achieved = len(matched_required) * 2 + len(matched_preferred)
    raw_score = achieved / max_possible

    # 必須スキル不足のペナルティ: スコアを0.6でキャップ
    if len(missing_required) > 0:
        raw_score = min(raw_score, 0.6)

    all_matched = matched_required + matched_preferred
    return raw_score, all_matched, missing_required, missing_preferred


def _compute_experience_score(resume_years: int, job_required_years: int) -> float:
    """経験年数一致スコアを計算

    - 必要年数以上: 1.0
    - 70%以上: 比例スコア
    - 70%未満: 半減ペナルティ
    """
    if job_required_years == 0:
        return 1.0

    ratio = resume_years / job_required_years

    if ratio >= 1.0:
        return 1.0
    elif ratio >= 0.7:
        return ratio
    else:
        return ratio * 0.5


def _compute_location_score(
    resume_location: str,
    resume_desired: list[str],
    job_location: str,
    job_remote: str,
) -> float:
    """勤務地一致スコアを計算

    - 完全一致または希望勤務地リストに含まれる: 1.0
    - リモート対応が双方の希望と合致: 1.0
    - 同一都道府県: 0.5
    - 不一致: 0.0
    """
    # 居住地と勤務地の都道府県を抽出
    def _extract_pref(loc: str) -> str:
        for pref in ("東京都", "大阪府", "京都府", "北海道",
                      "神奈川県", "埼玉県", "千葉県", "愛知県",
                      "兵庫県", "福岡県"):
            if pref in loc:
                return pref
        return loc[:3] if len(loc) >= 3 else loc

    resume_pref = _extract_pref(resume_location)
    job_pref = _extract_pref(job_location)

    # 希望勤務地に含まれているか
    if resume_desired:
        for desired in resume_desired:
            desired_pref = _extract_pref(desired)
            if desired_pref == job_pref:
                return 1.0
            # リモート対応
            if "リモート" in desired and "リモート" in job_remote:
                return 1.0

    # 完全一致
    if resume_pref == job_pref:
        return 1.0

    # リモート対応チェック
    if "リモート" in job_remote:
        # 求人がリモート可で、候補者もリモート希望
        if resume_desired and any("リモート" in d for d in resume_desired):
            return 1.0

    # 不一致
    return 0.0


def _compute_industry_score(resume_industries: list[str], job_industry: str) -> float:
    """業界一致スコアを計算

    - 直近業界が一致: 1.0
    - 同じ業界グループ: 0.5
    - 不一致: 0.0
    """
    if not resume_industries or not job_industry:
        return 0.0

    # 直近の業界
    latest = resume_industries[-1] if resume_industries else ""

    if latest == job_industry:
        return 1.0

    # 業界グループ検索
    for group_name, members in INDUSTRY_GROUPS.items():
        if latest in members and job_industry in members:
            return 0.5

    return 0.0


def _compute_unit_price_score(
    resume_min: int, resume_max: int,
    job_min: int, job_max: int,
) -> float:
    """単価帯のオーバーラップ率を計算

    - オーバーラップ率80%以上: 1.0
    - オーバーラップあり: 比例スコア
    - オーバーラップなし: 0.0
    """
    # 範囲が未設定の場合はスキップ
    if resume_min == 0 and resume_max == 0:
        return 1.0  # 未設定ならペナルティなし
    if job_min == 0 and job_max == 0:
        return 1.0

    # オーバーラップ範囲を計算
    overlap_min = max(resume_min, job_min)
    overlap_max = min(resume_max, job_max)

    if overlap_min > overlap_max:
        return 0.0  # オーバーラップなし

    overlap = overlap_max - overlap_min
    resume_range = resume_max - resume_min
    job_range = job_max - job_min

    if resume_range == 0 or job_range == 0:
        return 0.5  # どちらかが固定値

    # 希望単価帯に対するカバー率
    coverage = overlap / resume_range
    return min(coverage, 1.0)


def score_resume_against_job(resume: dict, job: dict) -> dict:
    """経歴書と案件のマッチングスコアを計算

    Args:
        resume: 経歴書データ（dict）
        job: 案件データ（dict）

    Returns:
        スコア詳細を含むdict
    """
    weights = MATCHING_WEIGHTS

    # 1. スキルマッチ
    skill_score, matched, missing_req, missing_pref = _compute_skill_score(
        resume.get("skills", {}),
        job.get("required_skills", {}),
        job.get("preferred_skills", {}),
    )

    # 2. 経験年数マッチ
    experience_score = _compute_experience_score(
        resume.get("years_of_experience", 0),
        job.get("required_experience_years", 0),
    )

    # 3. 勤務地マッチ
    location_score = _compute_location_score(
        resume.get("location", ""),
        resume.get("desired_locations", []),
        job.get("location", ""),
        job.get("remote_policy", ""),
    )

    # 4. 業界マッチ
    industries = [wh.get("industry", "") for wh in resume.get("work_history", [])]
    industry_score = _compute_industry_score(industries, job.get("industry", ""))

    # 5. 単価マッチ
    unit_price_score = _compute_unit_price_score(
        resume.get("desired_unit_price_min", 0),
        resume.get("desired_unit_price_max", 0),
        job.get("unit_price_min", 0),
        job.get("unit_price_max", 0),
    )

    # 重み付き合計
    total = (
        skill_score * weights["skill_match"] +
        experience_score * weights["experience_match"] +
        location_score * weights["location_match"] +
        industry_score * weights["industry_match"] +
        unit_price_score * weights["unit_price_match"]
    )

    # 説明文の生成
    explanation_parts = []
    if skill_score >= 0.8:
        explanation_parts.append("スキルの一致率が非常に高い")
    elif skill_score >= 0.5:
        explanation_parts.append("スキルが概ね一致")
    else:
        explanation_parts.append("スキル一致率が低い")

    if missing_req:
        explanation_parts.append(f"必須スキル不足: {', '.join(missing_req[:3])}")

    if experience_score >= 1.0:
        explanation_parts.append("経験年数は十分")
    elif experience_score >= 0.7:
        explanation_parts.append("経験年数は概ね充足")
    else:
        explanation_parts.append("経験年数が不足気味")

    if location_score >= 1.0:
        explanation_parts.append("勤務地条件が合致")
    elif location_score >= 0.5:
        explanation_parts.append("勤務地が近隣")

    if unit_price_score >= 0.8:
        explanation_parts.append("単価条件が合致")
    elif unit_price_score == 0.0:
        explanation_parts.append("単価条件が合わない")

    return {
        "total_score": round(total, 4),
        "breakdown": {
            "skill_match": round(skill_score, 4),
            "experience_match": round(experience_score, 4),
            "location_match": round(location_score, 4),
            "industry_match": round(industry_score, 4),
            "unit_price_match": round(unit_price_score, 4),
        },
        "matched_skills": matched,
        "missing_required_skills": missing_req,
        "missing_preferred_skills": missing_pref,
        "explanation": "。".join(explanation_parts) + "。",
    }
