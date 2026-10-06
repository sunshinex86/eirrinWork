# AI Development Policy

## Goal
既存システムへ機能を安全かつ短いサイクルで追加する。

## Mandatory Rules
- 新規プロジェクトを作らない。
- 最初に対象範囲内の既存 `src`、`tests`、`docs`、設定ファイルを読む。
- 現在のPhaseとTask範囲外を変更しない。
- 関係のないリファクタをしない。
- 既存動作を要件なしに変更しない。
- 大規模リファクタ、新規外部接続、DB追加、主要依存追加はPhase Gate承認なしに行わない。
- 推測は `[INFERRED]`、未確認は `[UNKNOWN]`、確認済みは `[CONFIRMED]` と記録する。
- Critical / Majorは修正対象、Minorは原則記録対象とする。
- 実行可能なテストを実行し、コマンドと結果を記録する。
- 同じ失敗への自動修正は最大3回まで。解決しない場合はBLOCKERとして停止する。
- Phase終了時は成果物を更新し、次Phaseへ自動で進まない。

## Required Output After Changes
- 変更概要
- 変更ファイル
- 実行テスト
- テスト結果
- 未解決リスク
- 次のPhase Gate確認項目

## Discovery Rules
- 初期入力は曖昧でもよい。依頼者に最初から正式要件や変更範囲の確定を要求しない。
- Repository調査後にAIが仮対象範囲、仮要件、Scenarioを作成する。
- Requirement Fidelity 100%だけで機能完了と判断しない。
- Reviewでは主要Production Path、旧形式データ、境界値、異常系、未検証経路を確認する。
