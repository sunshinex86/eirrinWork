# Requirement Analysis

> Generated: 2026-07-01
> Status: DRAFT
> Skill: 02_understand_requirement

## 1. Problem Definition

**現状の問題:** マッチング結果のスコアや不足スキルリストだけでは、「なぜこの人材が推薦されるのか」「どのようなリスクがあるのか」を一目で理解することが難しい。

**解決すべきこと:** マッチングの推薦理由をスキル・業界・経験の観点に分解し、不足要件の分析とリスク情報を構造化して提示することで、人材紹介・採用の実務判断を支援する。

## 2. Mapping Raw Request → Repository Capabilities

| Raw Request Item | Existing Repository Capability | Gap |
|---|---|---|
| スキルの一致率80%表示 | `required_skill_score` / `preferred_skill_score` in HybridBreakdown（0-1） | 表示UIには生のパーセンテージのみ。説明テキストには閾値評価のみで数値連携なし |
| 業界経験が案件と一致 | `context_score` + `_rule_context_score()` + RAG industry matching | 業界一致/不一致の明示的なユーザー向け説明がない |
| 不足しているスキルや経験 | `missing_required_skills` / `missing_preferred_skills` (ID list) | IDリストのみ。不足の程度（レベル・年数）や重要度が不明 |
| 経験年数不足 | `experience_score`（既存計算済み） | ユーザー向けの明示的な警告表示なし |
| 対象業界での経験がない | `context_score` に業界一致判定あり（_rule_context_score） | 明示的なリスク表示なし。context_scoreが低い場合に間接的にわかるのみ |

## 3. Key Findings from Repository Analysis

### Existing Data Available for Explanation

| Data Source | Location | Format | Can Be Used For |
|---|---|---|---|
| `hybrid_breakdown` 10-axis scores | MatchItem | 0-1 float per axis | Category scoring (skill/industry/experience) |
| `missing_required_skills` | MatchItem | list[str] (skill_ids) | Gap display |
| `missing_preferred_skills` | MatchItem | list[str] (skill_ids) | Gap display |
| `matched_skills` | MatchItem | list[str] (skill_ids) | Skill match display |
| `structured_skills` | Resume | list[ResumeSkill] (id, level, years, last_used) | Depth gap analysis |
| `structured_required_skills` | Job | list[JobSkill] (id, required_level, required_years) | Level/years gap analysis |
| `work_history[].industry` | Resume | str per entry | Industry experience determination |
| `job.industry` | Job | str | Industry target |
| `rag_corrections` | MatchItem | list[RagCorrection] | Supplementary evidence |
| skill_dictionary | data/skills/ | id → name, category, aliases | Display name for skill IDs |

### Existing UI Capabilities

| UI Element | Location | Can Extend For |
|---|---|---|
| `_render_breakdown()` | 03_マッチング.py:23-81 | Add explanation section per match |
| `st.info(m["explanation"])` | 03_マッチング.py:152 | Replace with structured display |
| Metric columns | 03_マッチング.py:52-71 | Add gap/risk indicators |

## 4. Architecture Impact Assessment

### Proposed Change Approach

```
[Current Flow]
Match Request → compute_hybrid_score() → scores + explanation text → Response → UI display

[Proposed Flow]
Match Request → compute_hybrid_score() → scores → generate_explanation() → structured explanation → Response → UI display
                                          ↑
                          (extracted from compute_hybrid_score)
```

### Key Design Decisions Needed

1. **説明生成の配置**: `src/matching/` に新しいモジュール `explanation_generator.py` を作成する案 vs `compute_hybrid_score()` 内で拡張する案
   - Recommendation: 独立モジュール（責任分離、テスタビリティ向上）

2. **説明データの受け渡し**: `MatchItem` の新フィールド vs 別エンドポイント
   - Recommendation: `MatchItem` に `Optional` フィールド追加（後方互換、既存コード非修正）

3. **UIの拡張方法**: `_render_breakdown()` 内で拡張 vs 新規コンポーネント
   - Recommendation: `_render_breakdown()` を拡張し、説明セクション追加

## 5. Technical Risks

| Risk | Mitigation |
|---|---|
| 説明生成処理によるパフォーマンス低下 | 既存スコアからのルールベース変換で計算量はO(1)。embedding呼び出し不要 |
| 後方互換性の破壊 | 新フィールドはOptional、既存フィールドは変更しない |
| テスト不足 | 新規テストで説明生成ロジックの全パターンをカバー |

## 6. Confirmed / Inferred / Unknown Summary

### [CONFIRMED]
- 既存の10軸スコアは説明生成の入力として十分な情報を持つ
- `missing_required_skills` / `missing_preferred_skills` は既存
- skill_dictionary は ID→名称の変換に利用可能
- 現在の `explanation` は閾値ベース短文のみ
- UIは Streamlit、`_render_breakdown()` が表示を担当

### [INFERRED]
- 説明生成は独立関数として抽出可能
- 構造化説明は `MatchItem` のオプショナルフィールドで追加可能
- リスク検出はルールベース（既存スコアの閾値判定）で実装可能
- 推薦理由のカテゴリは「スキル」「業界」「経験」「リスク」の4軸

### [UNKNOWN]
- 説明データの具体的なUI表示レイアウト（要Design Phaseでの決定）
- Semanticモード（Claude API）での説明統合範囲
- 説明生成の正確な出力構造（JSON schema）← **Phase Gate確認項目**

## 7. Phase Gate Check Items

| # | Item | Type | Decision Needed By |
|---|---|---|---|
| 1 | 説明生成の出力構造（flat text vs structured JSON） | Design | Planning Gate |
| 2 | 新フィールド追加の具体的な定義 | Design | Planning Gate |
| 3 | UI表示の具体的なレイアウト | Design | Planning Gate |
| 4 | Semanticモードの説明フォーマット統合要否 | Scope | Planning Gate |
