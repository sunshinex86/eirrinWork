# Task Backlog

> Generated: 2026-07-01
> Status: DRAFT (Pending Planning Gate Approval)

| ID | Phase | Task | Depends On | Status | Test | Notes |
|---|---|---|---|---|---|---|
| T1.1 | 1 | 説明データモデル定義 (`ExplanationCategory`, `RiskInfo`, `GapDetail`, `StructuredExplanation`) | — | pending | test_models.py | REQ-EX-05 |
| T1.2 | 1 | 説明生成モジュール作成 (`src/matching/explanation_generator.py`) | T1.1 | pending | test_explanation_generator.py | REQ-EX-04 |
| T1.3 | 1 | 既存コードリファクタリング (`compute_hybrid_score()`説明部を分離) | T1.2 | pending | 既存テスト | スコア計算非変更 |
| T1.4 | 1 | Keyword mode説明生成追加 | T1.2 | pending | test_explanation_generator.py | |
| T1.5 | 1 | Phase 1 統合テスト (API説明フィールド確認) | T1.1-T1.4 | pending | test_api.py | |
| T2.1 | 2 | リスク検出ロジック (経験年数/業界/レベル/鮮度) | T1.2 | pending | test_explanation_generator.py | REQ-EX-03 |
| T2.2 | 2 | スキルギャップ詳細化 (レベル差・年数差計算) | T1.2 | pending | test_explanation_generator.py | REQ-EX-02 |
| T2.3 | 2 | リスク・ギャップの説明生成統合 | T2.1, T2.2 | pending | test_explanation_generator.py | |
| T2.4 | 2 | Phase 2 統合テスト | T2.1-T2.3 | pending | test_api.py | |
| T3.1 | 3 | カテゴリ別評価関数（スキル/業界/経験） | T2.3 | pending | test_explanation_generator.py | REQ-EX-01 |
| T3.2 | 3 | 総合StructuredExplanation完全実装 | T3.1 | pending | test_explanation_generator.py | |
| T3.3 | 3 | Semantic mode説明対応 | T3.2 | pending | test_explanation_generator.py | |
| T3.4 | 3 | Phase 3 統合テスト | T3.1-T3.3 | pending | test_api.py | |
| T4.1 | 4 | 推薦説明UIコンポーネント (カテゴリ別表示) | T3.2 | pending | test_ui_display.py | REQ-EX-06 |
| T4.2 | 4 | ギャップ分析UI表示 | T4.1 | pending | test_ui_display.py | |
| T4.3 | 4 | リスクUI表示 | T4.1 | pending | test_ui_display.py | |
| T4.4 | 4 | Phase 4 統合テスト + E2E確認 | T4.1-T4.3 | pending | test_ui_display.py, test_api.py | |
