# Gap Analysis

> Generated: 2026-07-01
> Status: DRAFT
> Skill: 04_gap_analysis

## 1. Requirement Satisfaction Status

### REQ-EX-01: 推薦理由の分解表示

| Aspect | Status | Details |
|--------|--------|---------|
| スキル一致の分解表示 | **Partial** | スコアはHybridBreakdownにある。説明文は閾値ベース短文のみ。カテゴリ別の整理表示がない |
| 業界経験の表示 | **Missing** | context_scoreに業界一致の概念はあるが、ユーザー向け明示的表示なし |
| 経験年数の表示 | **Partial** | experience_scoreはある。説明文に「経験深度が十分/不足気味」の閾値判定あり。年数不足の定量的表示なし |

**Gap:** 3カテゴリへの分解表示機能が未実装。現在は単一説明テキストのみ。

### REQ-EX-02: スキルギャップの詳細分析

| Aspect | Status | Details |
|--------|--------|---------|
| 不足必須スキルの表示 | **Partial** | IDリスト（`missing_required_skills`）はあるが、不足の程度（レベル・年数差）の情報なし |
| 不足歓迎スキルの表示 | **Partial** | IDリストのみで程度情報なし |
| スキル深度のギャップ表示 | **Missing** | `_compute_skill_depth_score()` は計算するが、個別スキルごとの深度ギャップ情報を出力していない |

**Gap:** 不足スキルの「どの程度不足しているか」の情報が不足。スキルIDリストのみ。

### REQ-EX-03: リスク提示

| Aspect | Status | Details |
|--------|--------|---------|
| 経験年数不足の警告 | **Missing** | スコアには影響するが、ユーザー向け警告表示なし |
| 業界経験欠如の警告 | **Missing** | 同左 |
| スキルレベル不足の警告 | **Missing** | 同左 |
| スキル鮮度低下の警告 | **Missing** | 同左 |
| リスク重要度区分 | **Missing** | リスク表示機能自体がない |

**Gap:** リスク提示機能が完全に未実装。

### REQ-EX-04: 説明生成の共通化

| Aspect | Status | Details |
|--------|--------|---------|
| 説明生成の独立関数化 | **Missing** | `compute_hybrid_score()` 内に埋め込まれている |
| Keyword modeでの説明生成 | **Missing** | Keyword modeには説明文生成がない |
| 説明生成のモード共通化 | **Missing** | Hybrid内でのみ生成。他モードと共通化されていない |

**Gap:** 説明生成コードが `compute_hybrid_score()` に密結合。キーワードモードには説明なし。

### REQ-EX-05: 説明データモデルの拡張

| Aspect | Status | Details |
|--------|--------|---------|
| 構造化説明のデータモデル | **Missing** | 現状 `explanation: str` のみ。構造化フィールドなし |
| 後方互換性の維持 | **Satisfied** | Optionalフィールド追加で互換性維持可能 |

**Gap:** 構造化説明のためのデータモデル定義が必要。

### REQ-EX-06: UI表示の拡充

| Aspect | Status | Details |
|--------|--------|---------|
| 推薦説明セクション | **Missing** | マッチング結果UIに推薦説明の専用セクションなし |
| カテゴリ別表示 | **Missing** | 未実装 |
| ギャップ分析表示 | **Missing** | 未実装 |
| リスク表示 | **Missing** | 未実装 |

**Gap:** UI表示の拡充が全面的に必要。

## 2. Scenario Coverage Status

| Scenario | Current Status | Gap | Priority |
|---|---|---|---|
| S-01: Resume→Jobs explanation | ❌ Not supported | 構造化説明なし | High |
| S-02: Job→Resumes explanation | ❌ Not supported | 同上 | High |
| S-03: Keyword mode explanation | ❌ Not supported | 説明なし | Mid |
| S-04: All skills satisfied | △ Partial | リスクなしの表示は非明示的 | Mid |
| S-05: Partial match | △ Partial | カテゴリ別説明なし | High |
| S-06: Skill shortage | △ Partial | 不足リストのみ、程度不明 | High |
| S-07: No industry experience | ❌ Not supported | 警告なし | High |
| S-08: Insufficient experience years | ❌ Not supported | 警告なし | High |
| S-09: Skill level insufficient | ❌ Not supported | 警告なし | High |
| S-10: Skill freshness degraded | ❌ Not supported | 警告なし | Mid |
| S-11: Job with no required skills | △ Partial | 説明なしでスコアのみ | Low |
| S-12: Old format skills only | △ Partial | 互換性はあるが説明不十分 | Mid |
| S-13: Pending skills | △ Partial | Pendingスキルは分析対象外 | Low |
| S-14: Direct API access | △ Partial | 新フィールドで対応可能 | Low |
| EC-01~EC-06: Edge cases | ❌ Not covered | 説明生成の境界テストなし | Mid |

## 3. Required Changes Summary

### Source Code Changes

| # | File | Change | Type | Priority |
|---|---|---|---|---|
| C-01 | `src/models/match_result.py` | 構造化説明のデータモデル追加 | Add | High |
| C-02 | `src/matching/` (new file: `explanation_generator.py`) | 説明生成関数（独立モジュール） | Create | High |
| C-03 | `src/matching/embedding_matcher.py` | `compute_hybrid_score()` から説明生成部分を分離、新関数呼び出しに置換 | Refactor | High |
| C-04 | `src/api/routes_match.py` | Keyword match結果に説明追加 | Modify | Mid |
| C-05 | `src/ui/pages/03_マッチング.py` | UIに推薦説明セクション追加 | Modify | High |
| C-06 | `config.py` | 必要な設定追加（リスク閾値等） | Modify | Low |

### Test Changes

| # | File | Change | Priority |
|---|---|---|---|
| T-01 | New: `tests/test_explanation_generator.py` | 説明生成関数の単体テスト（全リスクパターンカバー） | High |
| T-02 | `tests/test_api.py` | 説明フィールドを含むAPI統合テスト追加 | High |
| T-03 | `tests/test_ui_display.py` | UI表示ユーティリティのテスト追加 | Mid |
| T-04 | `tests/conftest.py` | 新しいフィクスチャ追加（必要な場合） | Low |

### Documentation Changes

| # | File | Change | Priority |
|---|---|---|---|
| D-01 | `docs/context/target-scope.md` | 実装確定後にステータス更新 | Low |
| D-02 | `docs/context/initial-requirements.md` | 要件確定後にステータス更新 | Low |
| D-03 | `data/evaluation/` | 評価データ更新（必要な場合） | Low |

## 4. Regression Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| 既存APIレスポンスの互換性破壊 | Low | High | 新フィールドはOptional。既存フィールド変更なし |
| 既存UIの表示崩れ | Low | Medium | 既存 `m["explanation"]` は維持。新UIセクションは追加のみ |
| `compute_hybrid_score()` リファクタによるスコア変化 | Low | High | 説明生成のみ分離。スコア計算は変更しない |
| 説明生成のパフォーマンス影響 | Low | Medium | ルールベース処理のみ。Embedding/API呼び出しは追加しない |

## 5. Technical Uncertainties (PoC Needed)

| Uncertainty | Reason | Resolution |
|---|---|---|
| 説明生成の出力フォーマット決定 | 構造化の粒度（flat text vs structured JSON vs 両方） | Phase Planで決定 |
| スキルID→表示名変換のパフォーマンス | 大量スキルIDを辞書変換する際のオーバーヘッド | 辞書キャッシュ利用で対応可能 |
| UI表示レイアウトの詳細 | Streamlitの制約内での最適表示 | Phase Planでスケッチ |
