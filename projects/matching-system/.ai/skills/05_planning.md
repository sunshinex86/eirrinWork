# Skill 05: Planning

## Role
Technical Planner

## Purpose
差分を小さなPhaseとTaskへ分割し、実装順とGate条件を決める。

## Rules
- 1 Task = 1目的。
- Taskは独立して確認可能にする。
- MVPを先に成立させる。
- 依存追加と大規模変更は明示する。
- 実装前はPlanning Gate、実装開始後は各Execution Phase終了時に人間確認を行う。
- Planning Gateでは計画成果物だけを確認し、実装成果物や実装後テストを要求しない。

## Steps
1. MVPと後続改善を分ける。
2. 依存関係に沿ってPhaseを作る。
3. Taskごとに対象、非対象、完了条件、テストを書く。
4. Phase Exit Criteriaを定義する。
5. `.ai/phase-plan.md` と `tasks/taskbacklog.md` を更新する。
6. Planning Summaryを作る。
7. `.ai/project-state.md` を `WAITING_PLANNING_APPROVAL` に更新して停止する。

## Output
- `.ai/phase-plan.md`
- `tasks/taskbacklog.md`
- `handoff/PHASE-00_SUMMARY.md`
