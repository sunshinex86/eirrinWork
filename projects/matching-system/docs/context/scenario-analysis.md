# Scenario Analysis

> Generated: 2026-07-01
> Status: DRAFT
> Skill: 03_scenario_analysis

## 1. User / System Scenarios

### S-01: 経歴書→案件の推薦理由表示（正常系）
- **入口**: UI 経歴書選択 → マッチング実行 → 結果表示
- **経路**: `POST /api/match/resume-to-jobs/{resume_id}` (hybrid) → `_run_hybrid_match()` → `compute_hybrid_score()` → `generate_explanation()` → 構造化説明 → UI表示
- **期待**: 各案件に対してスキル一致・業界経験・経験年数のカテゴリ別説明が表示される
- **テスト有無**: 新規

### S-02: 案件→経歴書の推薦理由表示（正常系）
- **入口**: UI 案件選択 → マッチング実行 → 結果表示
- **経路**: `POST /api/match/job-to-resumes/{job_id}` (hybrid) → `_run_hybrid_match()` → `compute_hybrid_score()` → `generate_explanation()` → 構造化説明 → UI表示
- **期待**: S-01と同様の説明が各候補者に対して表示される
- **テスト有無**: 新規

### S-03: キーワードモードでの推薦説明表示
- **入口**: `mode=keyword` でAPI呼び出し
- **経路**: `POST /api/match/resume-to-jobs/{resume_id}?mode=keyword` → `KeywordMatcher.match_resume_to_jobs()` → 5軸スコア → keyword用説明生成
- **期待**: キーワードモードでも基本的な推薦説明が表示される（5軸ベース）
- **制約**: Hybridモードより情報量は少ない
- **テスト有無**: 新規

### S-04: 全スキル充足ケース（完全一致）
- **データ**: 人材が全必須スキルを保有＋レベル・年数要件充足＋業界一致＋経験年数充足
- **期待**: リスクなし。高スコア＋推奨表示
- **テスト有無**: 新規

### S-05: 部分充足ケース（典型的なケース）
- **データ**: 人材が一部の必須スキルを保有。レベルまたは年数が不足。業界経験あり
- **期待**: カテゴリ別に「一致（必須スキル一部充足）」「部分的（業界経験あり）」「リスク（レベル不足）」と表示
- **テスト有無**: 新規

### S-06: スキル不足ケース（リスク顕在化）
- **データ**: 人材が複数の必須スキルを未保有。経験年数不足。業界経験なし
- **期待**: 「不足（スキル不足）」「リスク（経験年数不足）」「リスク（業界未経験）」が明確に表示される
- **テスト有無**: 新規

### S-07: 業界経験がないケース
- **データ**: 人材の経歴業界と案件業界に共通性なし。context_score が低い
- **期待**: 「業界経験なし」のリスク警告が表示される
- **テスト有無**: 新規

### S-08: 経験年数不足ケース
- **データ**: 人材の `years_of_experience` < `job.required_experience_years`
- **期待**: 「経験年数不足（要求X年に対しY年）」のリスク表示
- **テスト有無**: 新規

### S-09: スキルレベル不足ケース
- **データ**: 保有スキルのレベル < 要求レベル
- **期待**: 該当スキルごとにレベル不足の警告表示
- **テスト有無**: 新規

### S-10: スキル鮮度低下ケース
- **データ**: 保有スキルの `last_used_year` が5年以上前
- **期待**: 「スキル最終利用がX年前」のリスク表示
- **テスト有無**: 新規

### S-11: 必須スキルがない案件
- **データ**: `structured_required_skills` が空の案件
- **期待**: スキルギャップの分析表示は行われない。業界・経験ベースの説明のみ
- **テスト有無**: 新規（境界値）

### S-12: 構造化スキルがない人材
- **データ**: `structured_skills` が空だが、旧形式 `skills` のみ保有
- **期待**: `skills` から説明可能な情報を抽出。スキル関連説明は最小限
- **テスト有無**: 新規（旧形式データ互換）

### S-13: スキル辞書にない未登録スキルを含むケース
- **データ**: `pending_skills` が存在する人材/案件
- **期待**: 未登録スキルはギャップ分析の対象外とし、その旨を注記
- **テスト有無**: 新規

### S-14: API直接利用（Postman/curlなど）
- **入口**: APIエンドポイントへの直接リクエスト
- **経路**: `POST /api/match/resume-to-jobs/{resume_id}` → JSONレスポンス
- **期待**: 新フィールドがJSONに含まれる（Optional）。既存フィールドは変更なし
- **テスト有無**: 既存APIテストで後方互換確認

## 2. Edge Cases & Boundary Values

### EC-01: 空データセット
- 人材も案件もない状態でのマッチング → 説明生成なしで早期リターン

### EC-02: 必須スキルが1件のみ
- 説明生成に必要な最小データ（1スキル）での動作確認

### EC-03: 全スキル完全不一致
- 保有スキルと要求スキルに一切共通性がない → リスク重大表示

### EC-04: 全スコア最大値（1.0）/ 最小値（0.0）
- 説明文章が適切に生成されることの確認

### EC-05: 経験年数が0年 / 要求年数が0年
- 0除算が発生しないこと。スコアは1.0扱い

### EC-06: 最終利用年がcurrent_yearと同一 / 極端に古い（20年前）
- 鮮度スコアの境界値確認

## 3. Compatibility Scenarios

### CP-01: 既存レスポンスの後方互換性
- `MatchItem` に新フィールド追加後も、新フィールドなしの既存レスポンスと互換性があること
- 新フィールドは `Optional` でデフォルト None

### CP-02: 既存UI（変更前）との互換性
- `m["explanation"]` は引き続きテキスト文字列として利用可能
- 新フィールドを参照しない既存コードがエラーにならないこと

### CP-03: 旧形式データ（skill_set）の互換
- 旧形式 `skills`（`languages/frameworks/tools/certifications/other`）のみを持つデータでも説明が生成されること

## 4. Implicit Conditions [INFERRED]

| Condition | Reason |
|---|---|
| 説明はルールベースで生成し、新たなEmbedding/API呼び出しを必須としない | 既存スコアリング結果のみから生成可能 |
| スキルIDの代わりに表示名を使用する際はskill_dictionaryを参照 | ユーザー可読性向上のため |
| 説明文は日本語で生成する | 既存システムの言語設定に準拠 |
| リスク重要度は major / minor の2段階 | 過度に複雑な区分を避ける |

## 5. Blind Spots for Gap Analysis

- **BS-01**: Keyword mode用の説明生成 — Hybrid modeと違い10軸Breakdownがない場合のフォールバック
- **BS-02**: 業界経験の有無判定 — `work_history[].industry` の欠損値や空文字への対応
- **BS-03**: スキルID→表示名変換 — skill_dictionaryに存在しないIDがある場合のハンドリング
- **BS-04**: UI上でスキル表示に使用する名称 — skill_id（英数字）vs skill_dictionary上のname（日本語）
- **BS-05**: 説明生成が大量マッチング結果（100件以上）のパフォーマンスに与える影響

## 6. Test Coverage Map

| Scenario | Existing Tests | New Tests Needed |
|---|---|---|
| S-01: Resume→Jobs explanation | API integration (test_api.py) | Explanation content verification |
| S-02: Job→Resumes explanation | API integration (test_api.py) | Explanation content verification |
| S-03: Keyword mode explanation | Keyword matcher tests | Keyword explanation generation test |
| S-04~S-10: Various risk scenarios | None | New test class: TestExplanationGeneration |
| EC-01~EC-06: Edge cases | Some boundary tests exist | Additional boundary tests for explanation |
| CP-01~CP-03: Compatibility | backward compat tests in test_api.py | Verify optional field behavior |
