# Skill 01: Understand Repository

## Role
System Analyst

## Purpose
既存Repositoryの構成、実装済み機能、テスト、制約を確認する。

## Inputs
- `docs/context/target-scope.md`
- 対象範囲内のsource、tests、docs、settings

## Rules
- 新規プロジェクトを作らない。
- 要件分析、Planning、実装はまだ行わない。
- 既存ソースを正とする。
- 各事実へ `[CONFIRMED]` / `[INFERRED]` / `[UNKNOWN]` を付ける。

## Steps
1. 対象範囲と変更禁止範囲を読む。
2. Repository構成を確認する。
3. 起動方法、主要技術、依存管理を確認する。
4. 対象機能の入口、主要処理、保存先、出力を追う。
5. 関連テストと既存ドキュメントを確認する。
6. 変更影響候補と未確認点を整理する。

## Output
`docs/context/repository-analysis.md`
