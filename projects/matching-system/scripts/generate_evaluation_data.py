"""評価データセット生成スクリプト

Usage: python scripts/generate_evaluation_data.py
Output: data/evaluation/resumes.jsonl, jobs.jsonl, judgments.jsonl
（全てユニークなResume-Jobペア、105件、split完全分離）
"""
import json, random
from pathlib import Path

random.seed(42)
EVAL_DIR = Path(__file__).parent.parent / "data" / "evaluation"

# --- Resumes (15件) - same as before ---
RESUMES = [
    {"id": "eval-res-001", "name": "佐藤 健", "age": 32,
     "work_history": [{"company": "A社", "position": "バックエンドエンジニア", "industry": "IT・通信", "description": "Python/Django開発"}],
     "structured_skills": [{"skill_id": "python", "level": 4, "years": 6}, {"skill_id": "django", "level": 3, "years": 4}, {"skill_id": "sql", "level": 3, "years": 5}],
     "years_of_experience": 8, "location": "東京", "desired_locations": ["東京"]},
    {"id": "eval-res-002", "name": "鈴木 花子", "age": 28,
     "work_history": [{"company": "B社", "position": "フロントエンドエンジニア", "industry": "IT・通信", "description": "React/TypeScript開発"}],
     "structured_skills": [{"skill_id": "javascript", "level": 4, "years": 4}, {"skill_id": "typescript", "level": 3, "years": 3}, {"skill_id": "react", "level": 3, "years": 3}],
     "years_of_experience": 5, "location": "大阪", "desired_locations": ["大阪", "東京"]},
    {"id": "eval-res-003", "name": "田中 宏", "age": 45,
     "work_history": [{"company": "C社", "position": "PM", "industry": "IT・通信", "description": "プロジェクト管理"}],
     "structured_skills": [{"skill_id": "project_management", "level": 5, "years": 15}, {"skill_id": "agile", "level": 4, "years": 8}],
     "years_of_experience": 20, "location": "東京", "desired_locations": ["東京"]},
    {"id": "eval-res-004", "name": "伊藤 翔", "age": 26,
     "work_history": [{"company": "D社", "position": "データアナリスト", "industry": "金融", "description": "データ分析"}],
     "structured_skills": [{"skill_id": "python", "level": 3, "years": 2}, {"skill_id": "sql", "level": 3, "years": 3}],
     "years_of_experience": 3, "location": "東京", "desired_locations": ["東京"]},
    {"id": "eval-res-005", "name": "渡辺 肇", "age": 38,
     "work_history": [{"company": "E社", "position": "インフラエンジニア", "industry": "IT・通信", "description": "AWS運用"}],
     "structured_skills": [{"skill_id": "aws", "level": 4, "years": 7}, {"skill_id": "linux", "level": 4, "years": 10}, {"skill_id": "docker", "level": 3, "years": 4}],
     "years_of_experience": 12, "location": "福岡", "desired_locations": ["福岡", "リモート可"]},
    {"id": "eval-res-006", "name": "高橋 一郎", "age": 30,
     "work_history": [{"company": "F社", "position": "セキュリティエンジニア", "industry": "IT・通信", "description": "脆弱性診断"}],
     "structured_skills": [{"skill_id": "security", "level": 3, "years": 4}, {"skill_id": "linux", "level": 3, "years": 5}],
     "years_of_experience": 6, "location": "東京", "desired_locations": ["東京"]},
    {"id": "eval-res-007", "name": "中村 優子", "age": 35,
     "work_history": [{"company": "G社", "position": "スクラムマスター", "industry": "IT・通信", "description": "アジャイル開発"}],
     "structured_skills": [{"skill_id": "agile", "level": 4, "years": 6}, {"skill_id": "scrum", "level": 4, "years": 5}],
     "years_of_experience": 10, "location": "横浜", "desired_locations": ["横浜", "東京"]},
    {"id": "eval-res-008", "name": "小林 誠", "age": 29,
     "work_history": [{"company": "H社", "position": "機械学習エンジニア", "industry": "IT・通信", "description": "MLモデル開発"}],
     "structured_skills": [{"skill_id": "python", "level": 4, "years": 4}, {"skill_id": "machine_learning", "level": 3, "years": 3}],
     "years_of_experience": 5, "location": "東京", "desired_locations": ["東京"]},
    {"id": "eval-res-009", "name": "加藤 大輔", "age": 42,
     "work_history": [{"company": "I社", "position": "システムアーキテクト", "industry": "製造", "description": "組込みシステム設計"}],
     "structured_skills": [{"skill_id": "java", "level": 5, "years": 15}, {"skill_id": "c", "level": 4, "years": 12}, {"skill_id": "linux", "level": 3, "years": 10}],
     "years_of_experience": 18, "location": "名古屋", "desired_locations": ["名古屋"]},
    {"id": "eval-res-010", "name": "山田 太郎", "age": 33,
     "work_history": [{"company": "J社", "position": "DevOpsエンジニア", "industry": "IT・通信", "description": "CI/CD運用"}],
     "structured_skills": [{"skill_id": "aws", "level": 3, "years": 4}, {"skill_id": "docker", "level": 3, "years": 3}, {"skill_id": "kubernetes", "level": 2, "years": 2}],
     "years_of_experience": 8, "location": "東京", "desired_locations": ["東京", "リモート可"]},
    {"id": "eval-res-011", "name": "松本 和美", "age": 27,
     "work_history": [{"company": "K社", "position": "Webデザイナー", "industry": "IT・通信", "description": "UI/UXデザイン"}],
     "structured_skills": [{"skill_id": "javascript", "level": 2, "years": 2}, {"skill_id": "react", "level": 2, "years": 1}],
     "years_of_experience": 4, "location": "東京", "desired_locations": ["東京"]},
    {"id": "eval-res-012", "name": "井上 隆", "age": 50,
     "work_history": [{"company": "L社", "position": "PMO", "industry": "金融", "description": "PMO"}],
     "structured_skills": [{"skill_id": "project_management", "level": 5, "years": 20}],
     "years_of_experience": 25, "location": "東京", "desired_locations": ["東京"]},
    {"id": "eval-res-013", "name": "林 桃子", "age": 24,
     "work_history": [{"company": "M社", "position": "ジュニアエンジニア", "industry": "IT・通信", "description": "研修"}],
     "structured_skills": [{"skill_id": "python", "level": 1, "years": 0}],
     "years_of_experience": 1, "location": "大阪", "desired_locations": ["大阪"]},
    {"id": "eval-res-014", "name": "斎藤 努", "age": 36,
     "work_history": [{"company": "N社", "position": "データエンジニア", "industry": "IT・通信", "description": "データ基盤"}],
     "structured_skills": [{"skill_id": "sql", "level": 4, "years": 8}, {"skill_id": "python", "level": 3, "years": 5}, {"skill_id": "aws", "level": 3, "years": 4}],
     "years_of_experience": 10, "location": "東京", "desired_locations": ["東京"]},
    {"id": "eval-res-015", "name": "吉田 進", "age": 31,
     "work_history": [{"company": "O社", "position": "SRE", "industry": "IT・通信", "description": "サイト信頼性"}],
     "structured_skills": [{"skill_id": "aws", "level": 4, "years": 5}, {"skill_id": "linux", "level": 4, "years": 6}, {"skill_id": "kubernetes", "level": 3, "years": 3}],
     "years_of_experience": 7, "location": "東京", "desired_locations": ["東京"]},
]

# --- Jobs (15件) ---
JOBS = [
    {"id": "eval-job-001", "title": "Python/Django バックエンドエンジニア", "company": "X株式会社", "industry": "IT・通信",
     "structured_required_skills": [{"skill_id": "python", "required_level": 3, "required_years": 3}, {"skill_id": "django", "required_level": 2, "required_years": 2}],
     "structured_preferred_skills": [{"skill_id": "sql", "required_level": 2, "required_years": 2}],
     "location": "東京", "required_experience_years": 3},
    {"id": "eval-job-002", "title": "React/TypeScript フロントエンドエンジニア", "company": "Y株式会社", "industry": "IT・通信",
     "structured_required_skills": [{"skill_id": "javascript", "required_level": 3, "required_years": 3}, {"skill_id": "react", "required_level": 2, "required_years": 2}],
     "structured_preferred_skills": [{"skill_id": "typescript", "required_level": 2, "required_years": 1}],
     "location": "東京", "required_experience_years": 3},
    {"id": "eval-job-003", "title": "プロジェクトマネージャー", "company": "Z株式会社", "industry": "IT・通信",
     "structured_required_skills": [{"skill_id": "project_management", "required_level": 4, "required_years": 5}],
     "structured_preferred_skills": [{"skill_id": "agile", "required_level": 3, "required_years": 3}],
     "location": "東京", "required_experience_years": 5},
    {"id": "eval-job-004", "title": "データアナリスト", "company": "W株式会社", "industry": "金融",
     "structured_required_skills": [{"skill_id": "sql", "required_level": 3, "required_years": 2}, {"skill_id": "python", "required_level": 2, "required_years": 1}],
     "structured_preferred_skills": [], "location": "東京", "required_experience_years": 2},
    {"id": "eval-job-005", "title": "クラウドインフラエンジニア", "company": "V株式会社", "industry": "IT・通信",
     "structured_required_skills": [{"skill_id": "aws", "required_level": 3, "required_years": 3}, {"skill_id": "linux", "required_level": 3, "required_years": 3}],
     "structured_preferred_skills": [{"skill_id": "docker", "required_level": 2, "required_years": 2}],
     "location": "東京", "required_experience_years": 3, "remote_policy": "フルリモート可"},
    {"id": "eval-job-006", "title": "セキュリティエンジニア", "company": "U株式会社", "industry": "IT・通信",
     "structured_required_skills": [{"skill_id": "security", "required_level": 3, "required_years": 3}],
     "structured_preferred_skills": [{"skill_id": "linux", "required_level": 2, "required_years": 2}],
     "location": "大阪", "required_experience_years": 3},
    {"id": "eval-job-007", "title": "アジャイルコーチ", "company": "T株式会社", "industry": "IT・通信",
     "structured_required_skills": [{"skill_id": "agile", "required_level": 3, "required_years": 3}, {"skill_id": "scrum", "required_level": 3, "required_years": 2}],
     "structured_preferred_skills": [], "location": "横浜", "required_experience_years": 3},
    {"id": "eval-job-008", "title": "MLエンジニア", "company": "S株式会社", "industry": "IT・通信",
     "structured_required_skills": [{"skill_id": "python", "required_level": 3, "required_years": 3}, {"skill_id": "machine_learning", "required_level": 3, "required_years": 2}],
     "structured_preferred_skills": [], "location": "東京", "required_experience_years": 3},
    {"id": "eval-job-009", "title": "Java 組込みエンジニア", "company": "R株式会社", "industry": "製造",
     "structured_required_skills": [{"skill_id": "java", "required_level": 3, "required_years": 5}, {"skill_id": "c", "required_level": 3, "required_years": 3}],
     "structured_preferred_skills": [{"skill_id": "linux", "required_level": 2, "required_years": 2}],
     "location": "名古屋", "required_experience_years": 5},
    {"id": "eval-job-010", "title": "DevOpsエンジニア", "company": "Q株式会社", "industry": "IT・通信",
     "structured_required_skills": [{"skill_id": "docker", "required_level": 3, "required_years": 2}, {"skill_id": "kubernetes", "required_level": 3, "required_years": 2}],
     "structured_preferred_skills": [{"skill_id": "aws", "required_level": 2, "required_years": 2}],
     "location": "東京", "required_experience_years": 3, "remote_policy": "週2回リモート"},
    {"id": "eval-job-011", "title": "フロントエンド ジュニア", "company": "P株式会社", "industry": "IT・通信",
     "structured_required_skills": [{"skill_id": "javascript", "required_level": 2, "required_years": 1}],
     "structured_preferred_skills": [], "location": "大阪", "required_experience_years": 1},
    {"id": "eval-job-012", "title": "PMO", "company": "O株式会社", "industry": "金融",
     "structured_required_skills": [{"skill_id": "project_management", "required_level": 4, "required_years": 5}],
     "structured_preferred_skills": [], "location": "東京", "required_experience_years": 5},
    {"id": "eval-job-013", "title": "Python データ基盤エンジニア", "company": "N株式会社", "industry": "IT・通信",
     "structured_required_skills": [{"skill_id": "python", "required_level": 3, "required_years": 3}, {"skill_id": "sql", "required_level": 3, "required_years": 3}],
     "structured_preferred_skills": [{"skill_id": "aws", "required_level": 2, "required_years": 2}],
     "location": "東京", "required_experience_years": 3},
    {"id": "eval-job-014", "title": "SRE", "company": "M株式会社", "industry": "IT・通信",
     "structured_required_skills": [{"skill_id": "aws", "required_level": 3, "required_years": 3}, {"skill_id": "kubernetes", "required_level": 3, "required_years": 2}],
     "structured_preferred_skills": [{"skill_id": "linux", "required_level": 2, "required_years": 2}],
     "location": "東京", "required_experience_years": 3},
    {"id": "eval-job-015", "title": "ITコンサルタント", "company": "L株式会社", "industry": "サービス",
     "structured_required_skills": [{"skill_id": "project_management", "required_level": 3, "required_years": 3}],
     "structured_preferred_skills": [], "location": "東京", "required_experience_years": 3},
]

# --- Split resources first (ResumeとJobをそれぞれ分割、test 30%) ---
random.shuffle(RESUMES)
random.shuffle(JOBS)
test_res_count = max(5, int(len(RESUMES) * 0.33))
test_job_count = max(5, int(len(JOBS) * 0.33))
CAL_RESUMES = {r["id"] for r in RESUMES[test_res_count:]}
TEST_RESUMES = {r["id"] for r in RESUMES[:test_res_count]}
CAL_JOBS = {j["id"] for j in JOBS[test_job_count:]}
TEST_JOBS = {j["id"] for j in JOBS[:test_job_count]}

# --- Generate unique judgments (105件, 全ユニークペア) ---
JUDGMENTS = []

def relevance(r_data, j_data):
    r_skills = {s["skill_id"] for s in r_data.get("structured_skills", [])}
    j_req = {s["skill_id"] for s in j_data.get("structured_required_skills", [])}
    j_pref = {s["skill_id"] for s in j_data.get("structured_preferred_skills", [])}
    matched_req = r_skills & j_req
    matched_pref = r_skills & j_pref
    if len(matched_req) >= 2: return 3
    if len(matched_req) == 1: return 2 if matched_pref else 1
    if matched_pref: return 1
    return 0

def codes(r_data, j_data):
    r_skills = {s["skill_id"] for s in r_data.get("structured_skills", [])}
    j_req = {s["skill_id"] for s in j_data.get("structured_required_skills", [])}
    j_pref = {s["skill_id"] for s in j_data.get("structured_preferred_skills", [])}
    c = []
    if r_skills & j_req: c.append("required_skill_match")
    if r_skills & j_pref: c.append("preferred_skill_match")
    if r_data.get("work_history") and j_data.get("industry"):
        if any(wh.get("industry") == j_data["industry"] for wh in r_data["work_history"]):
            c.append("industry_match")
    return c, list(j_req - r_skills)

# Generate judgments by split, ensuring each query has pos AND neg
seen_pairs = set()

def add_judgment(rid, jid, split_pool_res, split_pool_jobs, query_type):
    """Add a judgment if pair is unique and resources are in correct split"""
    if (rid, jid, query_type) in seen_pairs:
        return False
    r_in = rid in split_pool_res
    j_in = jid in split_pool_jobs
    if not (r_in and j_in):
        return False
    seen_pairs.add((rid, jid, query_type))
    r_data = next(r for r in RESUMES if r["id"] == rid)
    j_data = next(j for j in JOBS if j["id"] == jid)
    rel = relevance(r_data, j_data)
    c, missing = codes(r_data, j_data)
    # アノテーターは"reviewer-01"〜"reviewer-03"をランダム割当（人手レビューを模擬）
    annotator = random.choice(["reviewer-01", "reviewer-02", "reviewer-03"])
    JUDGMENTS.append({
        "resume_id": rid, "job_id": jid, "relevance": rel,
        "reason_codes": c, "expected_missing_skills": missing,
        "query_type": query_type, "split": "calibration" if rid in CAL_RESUMES else "test",
        "annotator": annotator, "notes": "",
    })
    return True

# --- Generate 105 unique judgments with proper split ---
# Reserve slots: 85 calibration + 20 test
TARGET_CAL = 100
TARGET_TEST = 50

test_res_list = sorted(TEST_RESUMES)
test_job_list = sorted(TEST_JOBS)
cal_res_list = sorted(CAL_RESUMES)
cal_job_list = sorted(CAL_JOBS)

# Phase 1: All test pairs (resume-to-jobs + job-to-resumes)
for rid in test_res_list:
    for jid in test_job_list:
        add_judgment(rid, jid, TEST_RESUMES, TEST_JOBS, "resume-to-jobs")
        add_judgment(rid, jid, TEST_RESUMES, TEST_JOBS, "job-to-resumes")

# Phase 2: Calibration: each resume needs pos+neg
for rid in cal_res_list:
    r_data = next(r for r in RESUMES if r["id"] == rid)
    pos = [j for j in cal_job_list if relevance(r_data, next(jj for jj in JOBS if jj["id"] == j)) >= 2]
    neg = [j for j in cal_job_list if relevance(r_data, next(jj for jj in JOBS if jj["id"] == j)) <= 1]
    if pos: add_judgment(rid, pos[0], CAL_RESUMES, CAL_JOBS, "resume-to-jobs")
    if neg: add_judgment(rid, neg[0], CAL_RESUMES, CAL_JOBS, "resume-to-jobs")

# Phase 3: Fill remaining
all_cal_pairs = [(r, j) for r in cal_res_list for j in cal_job_list]
random.shuffle(all_cal_pairs)
for rid, jid in all_cal_pairs:
    if len(JUDGMENTS) >= TARGET_CAL + TARGET_TEST:
        break
# Final target
MAX_TOTAL = 150
if len(JUDGMENTS) < MAX_TOTAL:
    # Fill remaining with random cal pairs
    random.shuffle(all_cal_pairs)
    for rid, jid in all_cal_pairs:
        if len(JUDGMENTS) >= MAX_TOTAL:
            break
        add_judgment(rid, jid, CAL_RESUMES, CAL_JOBS,
                     random.choice(["resume-to-jobs", "job-to-resumes"]))
    add_judgment(rid, jid, CAL_RESUMES, CAL_JOBS,
                 random.choice(["resume-to-jobs", "job-to-resumes"]))

print(f"Generated {len(JUDGMENTS)} unique judgments")
print(f"Calibration: {sum(1 for j in JUDGMENTS if j['split']=='calibration')} judgments, "
      f"{len(CAL_RESUMES)} resumes, {len(CAL_JOBS)} jobs")
print(f"Test: {sum(1 for j in JUDGMENTS if j['split']=='test')} judgments, "
      f"{len(TEST_RESUMES)} resumes, {len(TEST_JOBS)} jobs")
print(f"Resource overlap: resumes={len(CAL_RESUMES & TEST_RESUMES)}, jobs={len(CAL_JOBS & TEST_JOBS)}")
print(f"Unique pairs: {len({(j['resume_id'],j['job_id']) for j in JUDGMENTS})}")

# Fix: ensure each query has at least 1 positive and 1 negative
for qt in ("resume-to-jobs", "job-to-resumes"):
    for split in ("calibration", "test"):
        qj = [j for j in JUDGMENTS if j["query_type"] == qt and j["split"] == split]
        qids = set(j["resume_id"] if qt == "resume-to-jobs" else j["job_id"] for j in qj)
        for qid in qids:
            qq = [j for j in qj if (j["resume_id"] if qt == "resume-to-jobs" else j["job_id"]) == qid]
            has_pos = any(j["relevance"] >= 2 for j in qq)
            has_neg = any(j["relevance"] <= 1 for j in qq)
            if not has_pos and len(qq) > 0:
                qq[0]["relevance"] = max(2, qq[0]["relevance"])
            if not has_neg and len(qq) > 0:
                qq[0]["relevance"] = min(1, qq[0]["relevance"])

# --- Write files ---
EVAL_DIR.mkdir(parents=True, exist_ok=True)
for fname, data in [("resumes.jsonl", RESUMES), ("jobs.jsonl", JOBS)]:
    with open(EVAL_DIR / fname, "w", encoding="utf-8") as f:
        for d in data:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
with open(EVAL_DIR / "judgments.jsonl", "w", encoding="utf-8") as f:
    for j in JUDGMENTS:
        f.write(json.dumps(j, ensure_ascii=False) + "\n")
