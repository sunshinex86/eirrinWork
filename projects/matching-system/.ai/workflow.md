# Workflow

## Phase 0: Discovery and Planning
1. `01_understand_repository.md`
2. `02_understand_requirement.md`
3. `03_scenario_analysis.md`
4. `04_gap_analysis.md`
5. `05_planning.md`
6. 仮対象範囲、要件、Scenario、Gap、Phase Plan、Task Backlogを作成する
7. `.ai/project-state.md` を `WAITING_PLANNING_APPROVAL` に更新して停止する

## Planning Gate

Planning Gateは実装開始前の承認点です。

確認対象:
- 対象範囲
- 仮要件
- Scenario
- Gap Analysis
- Phase Plan
- Task Backlog

この時点では実装成果物、実装後テスト結果、Phase Reviewは確認対象にしません。
人間の承認後にのみ最初のExecution Phaseへ進みます。

## Phase 1..N: Execution
1. 人間が承認した現在PhaseからOpen Taskを選ぶ
2. `06_phase_execution.md` に従い実装する
3. 対象テストを実行する
4. `07_phase_review.md` に従いReviewする
5. Critical / Majorを修正する
6. Phase全体テストを実行する
7. Phase Summary、Review、Project Stateを更新する
8. `.ai/project-state.md` を `WAITING_PHASE_APPROVAL` に更新して停止する

## Execution Phase Gate

各Execution Phaseの完了後に、以下を確認します。

- 実装成果物
- テスト結果
- Review結果
- 残リスク
- 未検証Production Path
- 次Phaseへ進むための条件

承認されるまで次Phaseを実装しません。

## Final Phase
1. 全Execution Phaseが完了・承認済みであることを確認する
2. 全要件、Scenario、Production Path、テストを確認する
3. `08_finalize.md` を実行する
4. 最終成果物とHandoffを作成して停止する

## Retrospective
1. `09_retrospective.md` を実行する
2. Requirement FidelityとFeature Fidelityの差を確認する
3. 改善点を1つに絞る
4. 次版候補を記録する
