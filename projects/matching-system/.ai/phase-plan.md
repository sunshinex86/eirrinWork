# Phase Plan: 推薦説明システム

> Generated: 2026-07-01
> Status: DRAFT (Pending Planning Gate Approval)
> Skill: 05_planning

## Feature
- 推薦説明システム (Recommendation Explanation System)

## Goal
マッチング結果に対して、推薦理由の分解表示（スキル／業界／経験）、不足要件の詳細分析、リスク提示を構造化して提供する。

## Scope
### In Scope
- 推薦理由の分解表示（スキル一致／業界経験／経験年数）
- 不足要件の詳細分析（不足スキルの程度・レベル差・年数差）
- リスク提示（経験年数不足・業界未経験・レベル不足・鮮度低下）
- 説明生成の共通化（Hybrid/Keyword/Semantic全モード対応）
- 説明データモデルの拡張（後方互換維持）
- UI表示の拡充（カテゴリ別表示・ギャップ表示・リスク警告）

### Out of Scope
- マッチングスコア計算ロジック自体の変更
- 新たなマッチングモードの追加
- 外部AI（Claude API）への新規依存追加
- データベース移行
- 多言語対応
- スキル辞書・ツリーの変更

## Phases

| Phase | Goal | Main Tasks | Exit Criteria | Status |
|---|---|---|---|---|
| Phase 0 | Planning | Repository/Requirement/Scenario/Gap/Plan | Plan approved | **complete** |
| Phase 1 | 説明生成基盤 | 説明データモデル、生成モジュール、既存リファクタ、Keyword対応 | 全テストPASS、構造化説明フィールド追加 | **pending** |
| Phase 2 | リスク分析・ギャップ詳細 | リスク検出ロジック、不足スキル詳細化、説明統合 | 4種リスク検出、不足程度表示、全テストPASS | **pending** |
| Phase 3 | 推薦理由分解表示 | 3カテゴリ評価、全モード共通化、統合 | スキル/業界/経験のカテゴリ別説明、全テストPASS | **pending** |
| Phase 4 | UI表示拡充 | カテゴリ別表示、ギャップ表示、リスク表示 | UI表示完了、既存UI互換維持、全テストPASS | **pending** |

## Dependencies Requiring Approval
- なし（Feature 01完了済み。新規外部依存なし）

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| 後方互換性破壊 | Low | High | Optionalフィールド追加のみ。既存フィールド変更なし |
| パフォーマンス低下 | Low | Medium | ルールベース処理のみ。新規Embedding/API呼び出しなし |
| スコープクリープ | Medium | Medium | Phase Gate承認後にのみ次Phaseへ |
