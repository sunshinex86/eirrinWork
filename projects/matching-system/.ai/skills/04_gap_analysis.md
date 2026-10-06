# Skill 04: Gap Analysis

## Role
Solution Analyst

## Purpose
現行実装と要求仕様・利用シナリオの差分を特定する。

## Inputs
- Repository Analysis
- Requirement Analysis
- Scenario Analysis

## Rules
- 差分がない箇所を変更対象にしない。
- 証拠のない断定をしない。
- 要件充足だけでなく、主要シナリオが成立するか確認する。
- 変更候補ごとに影響範囲と検証方法を書く。

## Steps
1. 要件ごとに現行対応状況を確認する。
2. シナリオごとに実際の本番経路を確認する。
3. `Satisfied` / `Partial` / `Missing` / `Unknown` に分類する。
4. 必要なsource、test、docs変更候補を整理する。
5. 回帰リスク、旧形式データ、データ互換性、外部依存を確認する。
6. 既存テストが通っても未検証の経路を抽出する。
7. 小さなPoCが必要な技術的不確実性を抽出する。

## Output
`docs/context/gap-analysis.md`
