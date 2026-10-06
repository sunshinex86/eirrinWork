# Target Scope

> Generated: 2026-07-01 (created from raw-request.md and repository analysis)
> Status: DRAFT — refined by AI after Repository Analysis
> Skill: 02_understand_requirement

## Feature
- **推薦説明システム (Recommendation Explanation System)**

  既存のマッチングシステムに対し、**なぜこの人材／案件を推薦するのか**を構造化して説明する機能を追加する。
  マッチング理由の表示（スキル・業界・経験の観点での分解）、不足要件の分析、リスク提示を可能にする。

## Problem to Solve
- [CONFIRMED] 現在のマッチング結果画面では10軸スコア・一致スキルリスト・不足スキルリスト・簡素な説明文を表示しているが、「なぜこのスコアなのか」を直感的かつ構造的に理解することが難しい。
- [CONFIRMED] 説明文が閾値ベースの短文連結であり、推薦理由をカテゴリ別（スキル／業界／経験／リスク）に整理して提示できていない。
- [INFERRED] 人材紹介・案件推薦の現場では「推薦理由」と「注意点（リスク）」を顧客に説明する必要があるが、現在のシステムではこの説明を一元的に生成・表示できていない。

## In Scope
- [CONFIRMED] **推薦理由の分解表示**: スキル一致、業界経験、経験年数の各観点に分解したマッチング理由の説明
  - スキルの一致率（必須スキル・歓迎スキル）とその内訳
  - 業界経験の一致/不一致の判定と説明
  - 経験年数の充足/不足の判定と説明
- [CONFIRMED] **不足要件の分析表示**: 不足しているスキル・経験を構造化して提示
  - 不足必須スキルの詳細表示（現状はIDリストのみ）
  - 不足歓迎スキルの詳細表示
  - スキル深度（レベル・年数）のギャップ分析
- [CONFIRMED] **リスクの提示**: 推薦に際して注意すべき点を明示
  - 経験年数不足の警告
  - 業界経験欠如の警告
  - レベル不足の警告
  - スキル鮮度（最終利用年が古い）の警告
- [INFERRED] **説明生成の一元化**: 各マッチングモード（hybrid/keyword/semantic）で共通利用可能な説明生成機能
- [INFERRED] **UI表示の拡充**: 構造化された推薦説明をマッチング結果画面に可視化

## Allowed Directories
- [CONFIRMED] `src/` — ソースコード変更全般
- [CONFIRMED] `tests/` — テスト追加・修正
- [CONFIRMED] `docs/` — ドキュメント更新
- [CONFIRMED] `data/` — データファイル（必要な場合のみ）
- [CONFIRMED] `config.py` — 設定追加（必要な場合のみ）

## Out of Scope
- [CONFIRMED] マッチングスコア計算ロジック自体の変更（スコアリング方式は変更しない）
- [CONFIRMED] 新たなマッチングモードの追加
- [CONFIRMED] 外部AI（Claude API）への依存追加（既存のsemantic modeを拡張利用する可能性は含む）
- [CONFIRMED] データベースや新規外部ストレージへの移行
- [INFERRED] 推薦説明の多言語対応（日本語のみ対象）
- [INFERRED] スキル辞書・スキルツリーの変更（既存の辞書を説明に利用するのみ）

## Do Not Change
- [CONFIRMED] 既存マッチングスコア（total_score）の計算式
- [CONFIRMED] 既存データモデルの後方互換性を損なう変更
- [CONFIRMED] 既存APIエンドポイントのシグネチャ変更
- [CONFIRMED] 既存のリポジトリ層（データアクセスパターン）
- [CONFIRMED] 既存テストの動作前提

## Completion Criteria
- [INFERRED] 推薦理由がスキル／業界／経験の3カテゴリに分解されて構造化表示される
- [INFERRED] 不足要件（不足スキル・ギャップ）が詳細表示される
- [INFERRED] リスク情報が明示的に表示される（該当する場合）
- [INFERRED] 既存の全テストがPASSする
- [INFERRED] 新規追加した説明関連のテストがPASSする
- [INFERRED] 既存のマッチング結果UIと互換性がある（破壊的UI変更がない）

## Evidence / Assumptions
- [CONFIRMED] 現在の `MatchItem.explanation` は閾値ベース短文連結（embedding_matcher.py:581-603）
- [CONFIRMED] `HybridBreakdown` の10軸スコアは既存 → 説明生成の入力として利用可能
- [CONFIRMED] `SemanticMatchResponse` に `strengths` / `gaps` / `explanation` の構造化フィールドが既存 → パターンとして参考可能
- [CONFIRMED] 不足スキル情報（`missing_required_skills`, `missing_preferred_skills`）は既存
- [CONFIRMED] UI画面はStreamlitで構築、`_render_breakdown()` が各マッチ結果の表示を担当
- [INFERRED] 推薦説明はマッチング実行時にサーバー側で生成し、レスポンスに含める方式が既存アーキテクチャに適合
