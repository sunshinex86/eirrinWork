# Requirement Summary

> Created: 2026-06-30
> Status: **CONFIRMED — P1-P5 IMPLEMENTED / P6 PENDING**
> Raw Source: 機能1 残課題修正要件 v6（8 REQs: REQ-RE6-01～REQ-RE6-08）

## Goals
| Goal | REQ |
|------|-----|
| Go/Go言語/Golangのみ認識、英単語goは抽出しない | RE6-01 |
| 全APIテストを一時JSON分離し正式JSON不変 | RE6-02 |
| Sample読込テストをpass/assert Trueなし実処理化 | RE6-03 |
| multiprocessing並行試験を厳密件数確認に強化 | RE6-04 |
| RAG信頼度0.85ルールを共通関数化＋テスト | RE6-05 |
| Embedding E2Eにmarker＋証跡＋専用実行方式 | RE6-06 |
| 管理文書10軸統一＋状態整合 | RE6-07 |
| テスト生成物の管理（lock/bak不生成） | RE6-08 |

## Clarifying Questions
| # | Priority | Question | REQ |
|---|----------|----------|-----|
| 1 | High | Goパターンの大文字要件：IGNORECASEを外すのか（GO/goもマッチ禁止？） | RE6-01 |
| 2 | Mid | RAG信頼度共通関数の配置先（skill_extraction_service.py or rag_pipeline.py） | RE6-05 |
| 3 | Mid | Embedding E2E証跡の保存形式（JSON file or test output） | RE6-06 |
