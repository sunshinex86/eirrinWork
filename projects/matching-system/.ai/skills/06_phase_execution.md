# Skill 06: Phase Execution

## Role
Implementer

## Purpose
承認済みPhase内のTaskを順番に実装する。

## Rules
- 承認済みPhaseだけを対象にする。
- Open Taskを依存順に選ぶ。
- Task外変更をしない。
- 変更前に関連sourceとtestを読む。
- 既存パターンを優先する。
- 同じ失敗への修正は最大3回。
- 解決不能時はBLOCKERを記録して停止する。

## Loop
1. Open Taskを選ぶ。
2. Task対象ファイルと関連テストを読む。
3. 最小変更を実装する。
4. 対象テストを実行する。
5. 失敗時は原因を分析し修正する。
6. 成功後、Task状態と変更記録を更新する。
7. 次のOpen Taskへ進む。
8. Phase内Task完了後、Phase全体テストを実行する。

## Output
- source/test changes
- updated task file
- updated taskbacklog
- test results
