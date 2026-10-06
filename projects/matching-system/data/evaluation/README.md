# Matching Quality Evaluation Dataset

## Overview

評価用データセット。架空のJob/Resumeペアに対してスキル一致ルールに基づいてrelevanceを**自動生成**したもの。
**本データセットは人手レビュー未実施の自動生成ベースラインである。**

**制約**:
- 本データセットは人手ではなくアルゴリズム（スキル一致数ベースのヒューリスティック）で生成している
- 精度の客観的証明ではなく、回帰防止と相対比較のためのベースラインとして扱う
- 本番運用時には人手レビューによりrelevanceを確認・修正する必要がある
- 人手レビュー済み評価セットの作成は今後の課題

## Algorithm

relevance判定ルール:
- relevance 3: 必須スキル2件以上一致
- relevance 2: 必須スキル1件＋歓迎スキル一致
- relevance 1: 必須スキル1件のみ、または歓迎スキルのみ一致
- relevance 0: 一致スキルなし

**生成手順**:
1. `scripts/generate_evaluation_data.py` を実行（seed=42固定）
2. 各ペアのrelevanceを上記ルールで自動算出
3. calibration/test分割（リソース単位、重複なし）
4. 全queryに正例(>=2)・負例(<=1)を保証する補正

## Format

JSONL形式（1行1JSON）。

### resumes.jsonl

評価用経歴書データ。フィールドは本番のResumeと同一構造。

### jobs.jsonl

評価用案件データ。フィールドは本番のJobと同一構造。

### judgments.jsonl

| Field | Type | Description |
|-------|------|-------------|
| resume_id | str | 経歴書ID |
| job_id | str | 案件ID |
| relevance | int | 0=不適合, 1=一部適合, 2=適合, 3=強く適合 |
| reason_codes | list[str] | 適合理由コード |
| expected_missing_skills | list[str] | 不足が期待されるスキル |
| query_type | str | "resume-to-jobs" または "job-to-resumes" |
| split | str | "calibration" または "test" |
| annotator | str | アノテーター名 |
| notes | str | 備考 |

## Test Cases

| Case | Description | Coverage |
|------|-------------|----------|
| exact_match | 完全スキル一致 | ✅ |
| synonym_match | 同義語一致(JS/JavaScript) | ✅ |
| hierarchy_match | 親子スキル一致 | ✅ |
| level_mismatch | スキルレベル不足 | ✅ |
| years_mismatch | 経験年数不足 | ✅ |
| industry_match | 業界一致 | ✅ |
| industry_mismatch | 業界不一致 | ✅ |
| role_match | ロール一致 | ✅ |
| role_mismatch | ロール不一致 | ✅ |
| unregistered_skill | 未登録スキル含む | ✅ |

## Split

**ResumeとJobの両方で分割**。calibrationのqueryはcalibrationリソースのみ、testのqueryはtestリソースのみをランキング対象とする。
calibration 80%/test 20%。同一リソースが両方のsplitに入らない。

## Version

v1.0 - 2026-06-30
