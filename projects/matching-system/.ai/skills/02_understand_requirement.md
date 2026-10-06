# Skill 02: Understand Requirement

## Role
Requirement Analyst

## Purpose
曖昧または不完全な初期依頼を、Repositoryの事実に基づく仮対象範囲と検証可能な要件へ整理する。

## Inputs
- `docs/context/raw-request.md`
- `docs/context/repository-analysis.md`
- Repository内の関連コード、テスト、ドキュメント

## Rules
- まだ実装しない。
- 依頼者が最初から詳細な対象範囲や正式要件を書けることを前提にしない。
- 要件にない機能を勝手に追加しない。
- Repositoryから推定した内容は `[INFERRED]` とする。
- 未確認事項は `[UNKNOWN]` とする。
- 明示された内容とRepositoryで確認できた内容は `[CONFIRMED]` とする。
- 不明点があっても、Planning可能な範囲まで仮説を作成する。
- 実装を止める必要がある不明点だけをGate項目にする。

## Steps
1. Raw Requestを1文の問題定義へ整理する。
2. Repository Analysisから関連機能、主要経路、既存制約を抽出する。
3. `docs/context/target-scope.md` をAI生成する。
4. `docs/context/initial-requirements.md` をAI生成する。
5. 現状、期待動作、非対象を分ける。
6. 機能要件、非機能要件、互換性要件を整理する。
7. 各要件へ確認方法と根拠を付ける。
8. `[UNKNOWN]`、`[INFERRED]`、`[CONFIRMED]` を明示する。
9. 実装前確認が本当に必要な項目だけをGate項目にする。

## Outputs
- `docs/context/target-scope.md`
- `docs/context/initial-requirements.md`
- `docs/context/requirement-analysis.md`
