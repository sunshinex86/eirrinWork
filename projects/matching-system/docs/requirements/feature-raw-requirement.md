# 機能1 残課題修正要件 v6（REQ-RE6）

## 1. 目的
REQ-RE5対応後の再レビューで検出された、NLP誤検出、テスト隔離不足、無効なSampleテスト、並行試験不足、RAG閾値未実装、Embedding検証証跡不足、管理文書不整合を解消する。

## 2. 修正要件

### REQ-RE6-01：Go技能の誤検出防止（High）
Go/Go言語/Golang/golangのみ認識。普通の英単語go/Googleからの誤検出防止。

### REQ-RE6-02：全APIテストの正式JSON分離（High）
isolated_api_storage移行。正式JSON書込禁止。ハッシュ検証。

### REQ-RE6-03：Sample読込テストの実処理化（High）
pass/assert True禁止。一時JSON＋実API。7種必須テスト。

### REQ-RE6-04：並行アクセス試験の厳格化（High）
10件全件保存。CRUD＋bulk_merge 6件。FileLockTimeoutError。

### REQ-RE6-05：RAG信頼度0.85ルールの実装（Mid）
共通関数化。境界テスト。直接根拠フィルタ。

### REQ-RE6-06：Embedding E2E実行方式と証跡（Mid）
pytest.mark.embedding_e2e。RUN_EMBEDDING_E2E。証跡記録。

### REQ-RE6-07：管理文書と実装状態の整合（Mid）
10軸統一。DRAFT/COMPLETED整合。

### REQ-RE6-08：テスト生成物の管理（Low）
.lock/.bak不生成。一時ファイルのみ削除。
