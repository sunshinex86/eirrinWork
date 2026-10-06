# Skill 03: Scenario Analysis

## Role
Scenario Analyst / Adversarial Reviewer

## Purpose
要件一覧だけでは見落としやすい実利用経路、旧データ、境界値、異常系、回帰経路を先に洗い出す。

## Inputs
- Repository Analysis
- Target Scope
- Initial Requirements
- Requirement Analysis
- Existing tests and production entry points

## Rules
- 実装前に行う。
- 要件文の言い換えだけで終わらせない。
- 実際の保存、読込、変換、API、バッチ、UIなどの入口から追跡する。
- テスト済み経路と未検証の本番経路を区別する。
- 根拠のない機能追加はしない。

## Steps
1. 主要ユーザーシナリオとシステムシナリオを列挙する。
2. 新規データ、旧形式データ、欠損データ、短い入力、境界値を確認する。
3. 正常系、異常系、互換性、移行、再実行、外部依存のシナリオを整理する。
4. 各シナリオを実際のコード入口と保存経路へ対応付ける。
5. 既存テストが通っても未検証となる経路を明示する。
6. 要件に書かれていないが機能成立に必須の暗黙条件を `[INFERRED]` として記録する。
7. Gap Analysisで確認すべきBlind Spotを作成する。

## Output
`docs/context/scenario-analysis.md`
