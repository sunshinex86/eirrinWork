# Gap Analysis — REQ-RE6

> Created: 2026-06-30

| REQ | Classification | Current State | Needed Change |
|-----|--------------|---------------|---------------|
| RE6-01 | **Need Modify** | IGNORECASE付きGo/Go言語/Golangマッチ | 大文字Go/Golangのみ、英単語go禁止 |
| RE6-02 | **Need Modify** | TestAPIの一部クラスのみisolated移行済 | 全クラス移行＋ハッシュ検証 |
| RE6-03 | **Need Modify** | pass/assert True残存 | 一時JSON＋実API＋7種テスト |
| RE6-04 | **Need Modify** | 甘い条件(>=5, >0) | 厳密件数確認＋FileLockTimeoutError |
| RE6-05 | **Need Add** | 信頼度ハードコード | 共通関数＋0.85境界＋テスト6種 |
| RE6-06 | **Need Add** | marker未設定、証跡なし | marker＋RUN_EMBEDDING_E2E＋証跡 |
| RE6-07 | **Need Modify** | 一部7軸表記残存 | 10軸統一 |
| RE6-08 | **Need Add** | lock/bak不変確認あり | 一時ファイルのみ削除 |

**Summary**: 5 Need Modify, 3 Need Add
