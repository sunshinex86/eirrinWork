# Current System Summary

> Created: 2026-06-27
> Target Feature: マッチングスコア改善（Matching Score Improvement）

## Repository Overview

- **対象範囲**: `docs/context/target-scope.md` に定義された範囲（`src/matching/`, `src/models/`, `src/api/`, `src/ui/`, `tests/`, `config.py`）
- **プロジェクト名**: 経歴書×案件マッチングシステム
- **全体構成**: FastAPI（バックエンド API）+ Streamlit（フロントエンド UI）のモノレポ構成 [CONFIRMED]
- **データストア**: JSON ファイルベース（`data/resumes.json`, `data/jobs.json`） [CONFIRMED]

## Tech Stack

| カテゴリ | 技術 | 確認状況 |
|---------|------|---------|
| 言語 | Python 3.11+ | [CONFIRMED]（`.pyc` から推測） |
| API FW | FastAPI (>=0.104) + Uvicorn (>=0.24) | [CONFIRMED]（`requirements.txt`, `run.py`） |
| UI FW | Streamlit (>=1.28) | [CONFIRMED]（`requirements.txt`） |
| データモデル | Pydantic v2 (>=2.4) | [CONFIRMED]（`requirements.txt`, `src/models/*.py`） |
| 形態素解析 | Janome (>=0.5) | [CONFIRMED]（`requirements.txt`, `text_utils.py`） |
| AI API | Anthropic Claude API（オプション） | [CONFIRMED]（`semantic_matcher.py`, `config.py`） |
| HTTP クライアント | httpx (>=0.25) | [CONFIRMED]（`requirements.txt`） |
| データ処理 | pandas (>=1.3) | [CONFIRMED]（`requirements.txt`, `03_マッチング.py`） |
| テスト FW | pytest | [CONFIRMED]（`tests/` 構成、`.pytest_cache`） |
| CORS | FastAPI CORSMiddleware（全許可） | [CONFIRMED]（`src/api/main.py`） |

### 起動方法

- **通常起動**: `python run.py`（API:8000 + UI:8501 同時起動） [CONFIRMED]
- **API のみ**: `python run.py --api` [CONFIRMED]
- **UI のみ**: `python run.py --ui` [CONFIRMED]
- **API ドキュメント**: `http://localhost:8000/docs`（FastAPI Swagger UI） [CONFIRMED]

## Main Features

| 機能 | 概要 | 確認状況 |
|------|------|---------|
| 経歴書管理 | 経歴書の CRUD（一覧・取得・作成・更新・削除）＋スキルフィルタ検索 | [CONFIRMED]（`routes_resumes.py`） |
| 案件管理 | 案件の CRUD（一覧・取得・作成・更新・削除）＋スキルフィルタ検索 | [CONFIRMED]（`routes_jobs.py`） |
| キーワードマッチング | 経歴書→案件・案件→経歴書の双方向スコアリングマッチング | [CONFIRMED]（`keyword_matcher.py`, `scorer.py`） |
| AI 意味的マッチング | Claude API による意味的マッチング（オプション機能、APIキー必須） | [CONFIRMED]（`semantic_matcher.py`） |
| 一括マッチング | 全経歴書 vs 全案件の一括マッチング | [CONFIRMED]（`KeywordMatcher.match_all()`） |
| システム状態確認 | 登録件数・AIマッチング有効状態・重み設定の取得 | [CONFIRMED]（`routes_match.py` `/api/match/status`） |
| スキルシノニム解決 | JS→JavaScript、k8s→Kubernetes などの略称正規化 | [CONFIRMED]（`skill_extractor.py`） |
| 日本語形態素解析 | Janome による日本語テキスト解析（フォールバックあり） | [CONFIRMED]（`text_utils.py`） |

## Current Matching Flow

### キーワードマッチングフロー（コアフロー）

```
経歴書リクエスト (resume_id)
    │
    ▼
JsonResumeRepository から経歴書データ取得
JsonJobRepository から全案件データ取得
    │
    ▼
score_resume_against_job() を各案件に適用
    │
    ├── 1. skill_match (40%)     ← _compute_skill_score()
    │      必須スキル2倍重み、不足時0.6キャップ
    │      シノニム解決・部分一致対応
    │
    ├── 2. experience_match (20%) ← _compute_experience_score()
    │      必要年数以上=1.0、70%以上=比例、未満=半減
    │
    ├── 3. location_match (15%)  ← _compute_location_score()
    │      都道府県一致/希望勤務地/リモート条件
    │
    ├── 4. industry_match (10%)  ← _compute_industry_score()
    │      直近業界一致/業界グループ(INDUSTRY_GROUPS)
    │
    └── 5. salary_match (15%)    ← _compute_salary_score()
           年収帯オーバーラップ率
    │
    ▼
重み付き線形和 → スコア降順ソート → MatchResult 生成
    │
    ▼
クライアントに返却（API or バッチ処理）
```

**各ステップの確認状況**: [CONFIRMED]（`scorer.py` に全実装あり）

### セマンティックマッチングフロー（オプション）

```
semantic_match(resume_id, job_id)
    │
    ├── CLAUDE_API_KEY 未設定 → エラー返却（グレースフルデグラデーション）
    ├── anthropic パッケージ未インストール → エラー返却
    │
    ▼
build_matching_prompt() で JSON シリアライズした経歴書/案件情報を含むプロンプト構築
    │
    ▼
Claude API 呼び出し → JSON パース → score(0-100) + strengths + gaps + explanation
    │
    ▼
エラー時は score=0 + error メッセージを返却
```

**確認状況**: [CONFIRMED]（`semantic_matcher.py`） / ただし実際の API 呼び出しは環境変数依存

## Existing Data Model

### Resume（経歴書） [CONFIRMED]

| フィールド | 型 | 説明 |
|-----------|------|------|
| id | str | 一意なID |
| name | str | 氏名 |
| age | int | 年齢 |
| email | str | メールアドレス |
| phone | str | 電話番号 |
| location | str | 現在の居住地 |
| desired_locations | list[str] | 希望勤務地 |
| education | list[Education] | 学歴（学校・学部・卒業年・学位） |
| work_history | list[WorkHistory] | 職歴（会社・職位・期間・業務内容・業界） |
| skills | SkillSet | スキルセット（languages/frameworks/tools/certifications/other） |
| years_of_experience | int | 実務経験年数 |
| desired_salary_min | int | 希望最低年収（万円） |
| desired_salary_max | int | 希望最高年収（万円） |
| employment_type | str | 希望雇用形態（デフォルト: 正社員） |
| self_pr | str | 自己PR・備考 |

### Job（案件） [CONFIRMED]

| フィールド | 型 | 説明 |
|-----------|------|------|
| id | str | 一意なID |
| title | str | 案件名/ポジション名 |
| company | str | 企業名 |
| industry | str | 業界 |
| job_type | str | 職種 |
| location | str | 勤務地 |
| remote_policy | str | リモートポリシー |
| required_skills | SkillSet | 必須スキル |
| preferred_skills | SkillSet | 歓迎スキル |
| description | str | 案件概要・業務内容 |
| required_experience_years | int | 必要経験年数 |
| salary_min | int | 最低年収（万円） |
| salary_max | int | 最高年収（万円） |
| employment_type | str | 雇用形態（デフォルト: 正社員） |
| duration | str | 案件期間 |
| headcount | int | 募集人数 |

### MatchResult / MatchItem / MatchBreakdown（マッチ結果） [CONFIRMED]

| モデル | フィールド | 説明 |
|--------|----------|------|
| MatchResult | source_id, source_type, matches[], generated_at | マッチング結果（複数件） |
| MatchItem | target_id, target_name, target_company, total_score, breakdown, matched_skills, missing_required_skills, missing_preferred_skills, explanation | 個別マッチ結果 |
| MatchBreakdown | skill_match, experience_match, location_match, industry_match, salary_match | 5軸の内訳スコア（各0-1） |

### SemanticMatchResponse（AIマッチ結果） [CONFIRMED]

| フィールド | 型 | 説明 |
|-----------|------|------|
| score | float | AI評価スコア (0-100) |
| strengths | list[str] | マッチの強み |
| gaps | list[str] | ギャップ・懸念点 |
| explanation | str | 日本語での総合説明 |
| error | str | エラーメッセージ（エラー時のみ） |

## API Endpoints

| Method | Path | 説明 | 確認状況 |
|--------|------|------|---------|
| GET | /api/health | ヘルスチェック | [CONFIRMED] |
| GET | /api/resumes | 経歴書一覧（?skills= でフィルタ） | [CONFIRMED] |
| GET | /api/resumes/{id} | 経歴書取得 | [CONFIRMED] |
| POST | /api/resumes | 経歴書作成 | [CONFIRMED] |
| PUT | /api/resumes/{id} | 経歴書更新 | [CONFIRMED] |
| DELETE | /api/resumes/{id} | 経歴書削除 | [CONFIRMED] |
| GET | /api/jobs | 案件一覧（?skills= でフィルタ） | [CONFIRMED] |
| GET | /api/jobs/{id} | 案件取得 | [CONFIRMED] |
| POST | /api/jobs | 案件作成 | [CONFIRMED] |
| PUT | /api/jobs/{id} | 案件更新 | [CONFIRMED] |
| DELETE | /api/jobs/{id} | 案件削除 | [CONFIRMED] |
| POST | /api/match/resume-to-jobs/{resume_id} | 経歴書→案件マッチング | [CONFIRMED] |
| POST | /api/match/job-to-resumes/{job_id} | 案件→経歴書マッチング | [CONFIRMED] |
| GET | /api/match/status | マッチングシステム状態 | [CONFIRMED] |
| POST | /api/match/semantic | AI意味的マッチング | [CONFIRMED] |

## Key Configuration（config.py） [CONFIRMED]

| 設定項目 | デフォルト値 | 説明 |
|---------|------------|------|
| MATCHING_WEIGHTS.skill_match | 0.40 | スキル一致重み |
| MATCHING_WEIGHTS.experience_match | 0.20 | 経験年数重み |
| MATCHING_WEIGHTS.location_match | 0.15 | 勤務地重み |
| MATCHING_WEIGHTS.industry_match | 0.10 | 業界重み |
| MATCHING_WEIGHTS.salary_match | 0.15 | 年収重み |
| CLAUDE_ENABLED | False（API_KEY未設定時） | AIマッチング有効フラグ |
| CLAUDE_MODEL | claude-sonnet-4-6 | Claude モデル |
| CLAUDE_MAX_TOKENS | 1024 | Claude 最大トークン数 |
| INDUSTRY_GROUPS | 6業種グループ | 業界関連性マッピング |

## Existing Tests

| テストファイル | テストクラス | テストケース数 | 確認状況 |
|-------------|------------|-------------|---------|
| `tests/test_models.py` | TestResumeModel, TestJobModel, TestMatchResultModels | 19 tests | [CONFIRMED] |
| `tests/test_scorer.py` | TestSkillScore, TestExperienceScore, TestLocationScore, TestIndustryScore, TestSalaryScore, TestScoreResumeAgainstJob | 19 tests | [CONFIRMED] |
| `tests/test_keyword_matcher.py` | TestKeywordMatcher | 10 tests | [CONFIRMED] |
| `tests/test_semantic_matcher.py` | TestIsAvailable, TestBuildMatchingPrompt, TestSemanticMatch, TestBuildMatchingPromptEdgeCases | 9 tests | [CONFIRMED] |
| `tests/test_api.py` | TestAPI | 22 tests | [CONFIRMED] |
| `tests/test_repository.py` | TestJsonResumeRepository, TestJsonJobRepository | 19 tests | [CONFIRMED] |
| `tests/test_utils.py` | TestNormalizeSkillName, TestTokenizeJapanese, TestExtractSkillsFromText, TestComputeTextSimilarity, TestSkillExtractor, TestMatchSkills, TestFlattenSkills | 21 tests | [CONFIRMED] |

- **総テストケース数**: 119 テスト [CONFIRMED]（テストファイルからカウント）
- **テスト FW**: pytest + FastAPI TestClient [CONFIRMED]
- **フィクスチャ**: `conftest.py` に 7 つの共有フィクスチャ（sample_resume, sample_job, sample_resume_2, sample_job_2, temp_json_file, temp_resumes_file, temp_jobs_file） [CONFIRMED]

## Important Files

| ファイル | 役割 | 確認状況 |
|---------|------|---------|
| `run.py` | 起動スクリプト（API+UI 同時 or 個別起動） | [CONFIRMED] |
| `config.py` | 設定（マッチング重み、ファイルパス、フィーチャーフラグ） | [CONFIRMED] |
| `src/matching/scorer.py` | **マッチングスコアラー（コアエンジン）**：5軸重み付き線形和 | [CONFIRMED] |
| `src/matching/keyword_matcher.py` | **キーワードマッチングファサード**：双方向マッチング・ソート | [CONFIRMED] |
| `src/matching/semantic_matcher.py` | **Claude API 意味的マッチング**：プロンプト構築・API呼び出し | [CONFIRMED] |
| `src/models/resume.py` | 経歴書データモデル（Pydantic） | [CONFIRMED] |
| `src/models/job.py` | 案件データモデル（Pydantic） | [CONFIRMED] |
| `src/models/match_result.py` | マッチ結果データモデル（Pydantic） | [CONFIRMED] |
| `src/api/main.py` | FastAPI アプリ定義・CORS・ルーター登録 | [CONFIRMED] |
| `src/api/routes_resumes.py` | 経歴書 CRUD API | [CONFIRMED] |
| `src/api/routes_jobs.py` | 案件 CRUD API | [CONFIRMED] |
| `src/api/routes_match.py` | マッチング API（キーワード + セマンティック） | [CONFIRMED] |
| `src/ui/app.py` | Streamlit メインページ・システム状態表示 | [CONFIRMED] |
| `src/ui/pages/01_経歴書管理.py` | 経歴書管理 UI（一覧・登録・削除） | [CONFIRMED] |
| `src/ui/pages/02_案件管理.py` | 案件管理 UI（一覧・登録・削除） | [CONFIRMED] |
| `src/ui/pages/03_マッチング.py` | マッチング UI（双方向・スコア表示） | [CONFIRMED] |
| `src/utils/skill_extractor.py` | スキル抽出・シノニム解決・一致判定 | [CONFIRMED] |
| `src/utils/text_utils.py` | テキスト処理（正規化・形態素解析・類似度） | [CONFIRMED] |

## Already Implemented

- キーワードベースの双方向マッチング（経歴書→案件 / 案件→経歴書） [CONFIRMED]
- 5軸の重み付きスコアリング（スキル40%・経験20%・勤務地15%・業界10%・年収15%） [CONFIRMED]
- 必須スキル不足時のスコアキャップ（0.6上限） [CONFIRMED]
- スキルシノニム解決（JS→JavaScript, k8s→Kubernetes など） [CONFIRMED]
- 部分文字列マッチング（「REST API」↔「REST API設計経験」） [CONFIRMED]
- 業界グループによる関連性判定（6業種グループ） [CONFIRMED]
- Claude API による意味的マッチング（オプション） [CONFIRMED]
- 全経歴書 vs 全案件の一括バッチマッチング [CONFIRMED]
- スコア降順ソート [CONFIRMED]
- 日本語説明文の自動生成 [CONFIRMED]
- マッチングスコアの Streamlit 可視化（棒グラフ・スコア内訳・色分け） [CONFIRMED]

## Architecture Decisions & Notable Patterns

- **JSON ファイルベースの永続化**: DB 未使用。データは `data/resumes.json` と `data/jobs.json` に保存 [CONFIRMED]
- **sys.path.insert によるパス解決**: 多くのモジュールで `sys.path.insert(0, ...)` を使用（Streamlit 非経由起動のため） [CONFIRMED]
- **フィーチャーフラグ**: `CLAUDE_ENABLED` による AI 機能の ON/OFF 切り替え [CONFIRMED]
- **グレースフルデグラデーション**: API キー未設定・パッケージ未インストール時もエラーメッセージを返して停止しない [CONFIRMED]
- **Pydantic v2**: バリデーション・シリアライゼーションに Pydantic v2 を使用 [CONFIRMED]
- **Streamlit のローカル呼び出し**: UI 画面は API 経由でデータ取得（直接データベース参照しない） [CONFIRMED]
- **マッチング重みは config.py で一元管理**: 環境変数で上書き可能 [CONFIRMED]
- **全テストケースで実 JSON ファイル（または一時ファイル）を使用**: モックではなく実際のリポジトリを使用（APIテストのみ実際のデータファイルを使用） [CONFIRMED]

## Not Confirmed（＝ [UNKNOWN] の一覧）

- 実際の運用データ量（何件の経歴書・案件が登録されているか） [UNKNOWN]
- 実際の Claude API 応答速度・精度（API キー未設定のため未確認） [UNKNOWN]
- CI/CD パイプラインの有無・設定 [UNKNOWN]
- フロントエンド（Streamlit）のテストは未実装 [UNKNOWN]
- パフォーマンスベンチマーク（N件の経歴書 vs M件の案件のスコアリング時間） [UNKNOWN]
- マッチングスコアの閾値設定（UI 上で 70%/50% の色分けがあるが設定ファイルにはない） [UNKNOWN]
- `skills/`, `handoff/`, `tasks/`, `workflows/`, `templates/`, `knowledge/`, `reviews/` ディレクトリの内容（対象外のため未確認） [UNKNOWN]

## Risks for Feature Addition

1. **スコアリングロジックの変更による既存テストの修正量**（根拠: 119 テストの約半数がスコアラー・マッチングに関連） [CONFIRMED]
2. **重みバランスの調整**: 5軸の重みを変更すると全マッチング結果に影響（根拠: `config.py` に固定値で定義） [CONFIRMED]
3. **新たな評価軸の追加によるデータモデル変更**: MatchBreakdown / MatchItem / MatchResult のスキーマ変更が必要（根拠: `match_result.py` に固定5軸） [CONFIRMED]
4. **UI 表示の更新**: スコア軸が増減した場合、`03_マッチング.py` の 5カラム表示を修正する必要あり（根拠: Streamlit ページで5軸固定表示） [CONFIRMED]
5. **API レスポンス互換性**: 既存クライアント（Streamlit UI）が期待するレスポンス形式と乖離しないよう注意（根拠: `routes_match.py` の出力は `MatchResult.model_dump()` に依存） [CONFIRMED]
6. **新しい外部依存の追加**: AI 関連の新機能追加により新しいライブラリ・API キーが必要になる可能性（根拠: セマンティックマッチングが既に `anthropic` パッケージをオプション依存として持つ） [INFERRED]
