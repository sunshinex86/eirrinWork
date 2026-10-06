# RUN ME FIRST

## 1. 既存プロジェクトへ配置

このパックを既存Repositoryのルートへコピーしてください。

既存ファイルを上書きしないでください。すでに `.ai/` がある場合は差分を確認して統合してください。

## 2. 分かっていることだけを書く

`docs/context/raw-request.md` に、現時点で分かっている依頼内容だけを書きます。

- 追加・修正したいこと
- 背景や困っていること
- 分かっている期待結果
- 既知の制約や参考情報

詳細な対象範囲、変更可能ディレクトリ、正式要件、完了条件を最初から書く必要はありません。不明な項目は空欄のままで構いません。

## 3. Planningを開始する

`.ai/prompts/01_start_planning.md` の内容をClaude Code等へ送ります。

AIはRepositoryを調査し、まだ実装を行わず、以下のPlanning成果物を生成・更新します。

- `docs/context/target-scope.md`
- `docs/context/initial-requirements.md`
- `docs/context/requirement-analysis.md`
- `docs/context/scenario-analysis.md`
- `docs/context/gap-analysis.md`
- `.ai/phase-plan.md`
- `tasks/taskbacklog.md`
- `.ai/project-state.md`

## 4. Planning Gate

AIはPlanning成果物を更新した時点で停止します。

この時点では実装していないため、実装成果物や実装後テスト結果は存在しません。人間は以下だけを確認します。

- 対象範囲が依頼意図と合っているか
- 仮要件とScenarioに不足や誤解がないか
- Gap Analysisが既存Repositoryの実態と合っているか
- Phase PlanとTask Backlogの順序・粒度が妥当か
- 最初に実行するPhaseが小さく、実行・検証可能か

修正が必要な場合はPlanning成果物を修正させます。承認できる場合だけ次へ進みます。

## 5. 承認したPhaseを実行する

`.ai/prompts/02_execute_approved_phase.md` の内容をClaude Code等へ送ります。

AIは承認済みの現在Phaseだけを実装し、対象テスト、Review、Phase Summary、状態ファイルを更新して停止します。

## 6. Execution Phase Gate

実装後の各Phase Gateでは、以下を確認します。

- 実装成果物
- テスト結果
- Review結果
- 残リスク
- 未検証Production Path
- 次Phaseへ進める状態か

承認後は再度 `.ai/prompts/02_execute_approved_phase.md` を送り、次の承認済みPhaseを実行します。

## 7. Finalize

全実装Phaseを完了・承認した後、`.ai/prompts/05_finalize.md` を送ります。
