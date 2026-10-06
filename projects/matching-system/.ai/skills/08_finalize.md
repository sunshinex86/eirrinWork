# Skill 08: Finalize

## Role
Release Finisher

## Purpose
実装完了後の全体確認と引継ぎ成果物を作成する。

## Rules
- 未完了要件を隠さない。
- 実行していないテストを成功扱いしない。
- 実装と一致しない設計書を書かない。
- Requirement Fidelity 100%だけで機能完了と判定しない。
- Handoffを最優先成果物とする。

## Steps
1. 全要件とTask状態を照合する。
2. Scenario Analysisの主要経路、旧形式、境界値、異常系を照合する。
3. 主要ユーザーフローを実際のProduction Pathで確認する。
4. 全体テストまたは実行可能な最大範囲を実行する。
5. テスト件数ではなく、変更した本番経路が検証されたか確認する。
6. Requirement Fidelity、Scenario Coverage、Feature Fidelityを記録する。
7. 変更概要、設定変更、データ互換性を整理する。
8. 未検証Production Path、残課題、既知リスクを分類する。
9. Final ReportとHandoffを作成する。

## Output
- `handoff/FINAL_REPORT.md`
- `handoff/SESSION_SUMMARY.md`
- updated `.ai/project-state.md`
