# Skill 07: Phase Review

## Role
Reviewer / Gatekeeper

## Purpose
Phase差分が要件、シナリオ、Task、品質基準を満たすか確認する。

## Review Priority
1. Critical: データ破壊、重大障害、セキュリティ、主要機能不成立
2. Major: 主要経路の不具合、回帰、テスト不足、互換性問題
3. Minor: 可読性、軽微な整理、将来改善

## Steps
1. Phase Plan、Task、diff、tests、Scenario Analysisを読む。
2. 要件外変更を確認する。
3. 正常系、境界値、異常系、旧形式、互換性を確認する。
4. テスト結果と実際の変更経路が一致するか確認する。
5. Production Pathを少なくとも1回、コード入口から保存・出力まで逆追跡する。
6. 実装者の説明を前提にせず、未変換データ、短入力、欠損値、外部依存失敗をAdversarialに確認する。
7. Requirement FidelityとFeature Fidelityを別々に評価する。
8. 指摘をCritical / Major / Minorへ分類する。
9. Critical / Majorを修正し再テストする。
10. Gate結論を出す。

## Gate Result
- Accept
- Accept with recorded Minor issues
- Reject / Blocked

## Required Metrics
- Requirement Fidelity: 明示要件の充足率
- Scenario Coverage: Scenario Analysisの検証率
- Feature Fidelity: 主要利用経路が実際に成立するか
- Unverified Production Paths: 未検証の本番経路数

## Output
`reviews/PHASE-XX_review.md`
