# Initial Requirements

> Generated: 2026-07-01 (created from raw-request.md and repository analysis)
> Status: DRAFT
> Skill: 02_understand_requirement

## Background
- [CONFIRMED] 本システムは経歴書と案件のマッチングシステムであり、現在Hybridモード（10軸）がデフォルトで動作している。
- [CONFIRMED] マッチング結果には総合スコア・軸別スコア・一致スキル・不足スキル・簡易説明文が含まれている。
- [CONFIRMED] Feature 01（マッチング品質向上＋スキルタグ標準化）は実装完了済み。
- [INFERRED] 次のステップとして、マッチング結果の**説明品質**を向上させ、ユーザー（人材紹介会社・採用企業）が推薦理由を直感的に理解できるようにする必要がある。

## Current Behavior
- [CONFIRMED] マッチング結果の `explanation` は数値閾値ベースで短文連結されている（例：「必須スキルを十分満たしている。経験深度が十分。意味的類似度が高い。」）
- [CONFIRMED] 不足スキルはIDリストとして表示される（不足理由の説明はない）
- [CONFIRMED] 業界経験の有無に関する明示的な表示・説明はない
- [CONFIRMED] 経験年数不足のリスク表示はない（ただしスコアには影響）
- [CONFIRMED] スキル深度（レベル・年数・最終利用年）のギャップは総合スコアに組み込まれているが、ユーザー向けに明示されていない

## Expected Behavior
- [CONFIRMED] 推薦理由を**スキル一致／業界経験／経験年数**のカテゴリに分解して表示する
- [CONFIRMED] 不足要件を詳細に分析・表示する（不足スキル名＋その重要度）
- [CONFIRMED] リスク情報を明示する（経験不足・業界未経験・レベル不足・鮮度低下）
- [INFERRED] 説明は既存のスコアリング結果から生成し、新たな外部AI呼び出しを必須としない
- [INFERRED] 説明内容は人材紹介の実務で使える粒度を持つ

## Functional Requirements

### REQ-EX-01: 推薦理由の分解表示 [INFERRED]
- マッチング結果において、「スキル一致」「業界経験」「経験年数」の3カテゴリに分解した推薦理由を表示する
- 各カテゴリの評価（一致/不一致/部分的）をテキストと視覚的要素で示す
- 根拠として対応するスコア値を参照可能にする

### REQ-EX-02: スキルギャップの詳細分析 [INFERRED]
- 不足必須スキルについて、どの程度不足しているか（スキルレベル・年数）を表示する
- 不足歓迎スキルも同様に表示する
- 保有スキルと要求スキルのレベル差・年数差を明示する

### REQ-EX-03: リスク提示 [INFERRED]
- 以下のリスクを検出し、重要度と共に表示する
  - 経験年数不足（要求年数に対して不足）
  - 業界経験欠如（案件の業界と人材の経験業界に一致なし）
  - スキルレベル不足（要求レベルに達していないスキル）
  - スキル鮮度低下（最終利用年が古いスキル）
- リスクは major / minor の区分で表示する

### REQ-EX-04: 説明生成の共通化 [INFERRED]
- `compute_hybrid_score()` 内の説明生成を独立したサービス/関数として抽出する
- keyword mode でも基本的な推薦説明を生成可能にする
- 生成された説明は `MatchItem.explanation` に反映する（後方互換維持）

### REQ-EX-05: 説明データモデルの拡張 [INFERRED]
- 既存の `MatchItem` を拡張し、構造化された説明情報を保持する方法を検討する
- 後方互換性を維持する（既存の `explanation` フィールドは維持）

### REQ-EX-06: UI表示の拡充 [INFERRED]
- マッチング結果画面に推薦説明セクションを追加する
- カテゴリ別表示、ギャップ分析表示、リスク表示を視覚的に行う

## Non-Functional Requirements
- [INFERRED] 説明生成は既存マッチング実行時間に有意な遅延を加えない（計算量増加を最小限に）
- [INFERRED] 既存の全APIエンドポイントとの互換性を維持する
- [INFERRED] 新規テストを追加し、現行テストが全てPASSすることを確認する
- [INFERRED] 説明生成はFeature Flag制御可能とする必要はない（常時生成でよい）

## Compatibility Requirements
- [CONFIRMED] 既存の全マッチングAPIレスポンスは後方互換性を維持する（新しいフィールドは optional で追加）
- [CONFIRMED] Existing behavior must remain compatible unless explicitly changed.
- [CONFIRMED] Use the existing project structure.
- [CONFIRMED] Keep development and verification lightweight.

## Known Constraints
- [CONFIRMED] 新規プロジェクトは作成しない
- [CONFIRMED] 大規模リファクタはPhase Gate承認後にのみ行う
- [CONFIRMED] 新規外部接続はPhase Gate承認後にのみ行う
- [CONFIRMED] 既存動作を要件なしに変更しない
- [CONFIRMED] テストは既存のテストパターン（pytest, conftest fixtures）に従う

## Unknowns
- [UNKNOWN] 推薦説明の正確なUI表示形式（Streamlit上での具体的なレイアウト）
- [UNKNOWN] 説明生成を `MatchItem` の新フィールドとして追加するか、別エンドポイントで提供するか
- [UNKNOWN] Semanticモード（Claude API）の説明も統一フォーマットに含めるか
- [UNKNOWN] 説明生成でスキル辞書の表示名（skill_id の代わりに日本語名）を使用するかどうか（現在の skill_id は英数字）

## Inferred Requirements
- [INFERRED] 説明生成関数は `src/matching/` または新規 `src/explanation/` に配置する
- [INFERRED] 説明データは `MatchItem` のオプショナルフィールドとして追加する（後方互換）
- [INFERRED] UI上の説明表示は `_render_breakdown()` を拡張して行う
- [INFERRED] ギャップ分析には既存の `missing_required_skills` / `missing_preferred_skills` に加え、スキル深度・レベル情報を活用する
- [INFERRED] リスク検出は既存スコア（軸別スコア）の低値から判定するルールベースで実装する
