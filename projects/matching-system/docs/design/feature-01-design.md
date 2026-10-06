# Technical Design: マッチング品質向上 + スキルタグ標準化

> Feature ID: 01
> Status: **Implemented** ✅

## アーキテクチャ概要

```mermaid
flowchart TD
    A[既存: scorer.py 5軸] --> B[変更なし・維持]
    C[新規: embedding_matcher.py] --> D{compute_embedding_score}
    D --> E[skill_embedding_score]
    D --> F[context_embedding_score]
    D --> G[role_embedding_score]
    D --> H[experience_depth_score]
    E --> I[vector_utils.py]
    F --> I
    G --> J[ルールベースROLE_KEYWORDS]
    H --> K[ルールベース経験年数]

    L[新規API] --> M[/api/match/embedding/...]
    M --> C

    N[新規UI] --> O[タブ3: AI埋め込みマッチング]
    O --> L
```

## 主要モジュール構成

### レイヤー構造
```
API Layer:  routes_match.py（新エンドポイント追加）
    ↓
Logic Layer: embedding_matcher.py（スコアリング）
              rag_pipeline.py（RAG検索）
              agent/skills/matching_skills.py（エージェントスキル）
    ↓
Util Layer:  vector_utils.py（埋め込み生成・類似度計算）
             skill_dictionary.py（辞書操作）
             skill_extractor.py（同義語解決）
             text_utils.py（テキスト正規化・標準化）
    ↓
Data Layer:  skill_dictionary.json / skill_tree.json（スキルデータ）
             knowledge/*.json（RAGナレッジベース）
```

### データフロー（埋め込みマッチング）

```
1. クライアント → POST /api/match/embedding/resume-to-jobs/{id}
2. routes_match.py → JsonResumeRepository / JsonJobRepository からデータ取得
3. → compute_embedding_score(resume, job)
   a. embedding_available() チェック
   b. _build_skill_text() + generate_embedding() → skill_embedding_score
   c. _build_context_text() + generate_embedding() → context_embedding_score
   d. _build_role_text() + generate_embedding() → role_embedding_score
   e. _compute_experience_depth_score() → depth_score（ルールベース）
   f. _compute_role_match_score() → role_match_score（ルールベース）
   g. 重み付き線形和 → total_score + explanation
4. → EmbeddingBreakdown + MatchItem にマッピング
5. → MatchResult として JSON レスポンス
```

## 採用技術

| 技術 | 用途 | 必須/任意 |
|------|------|----------|
| sentence-transformers | ローカル埋め込みモデル実行 | 任意（未インストールでもフォールバック動作） |
| numpy | ベクトル演算 | 必須 |
| scikit-learn | コサイン類似度計算 | 必須 |

## 設計判断

- **既存コードを一切変更しない**: 新機能はすべて独立モジュール・新エンドポイント・新UIタブ
- **Optional フィールド**: データモデル拡張は全フィールド Optional（None 許容）
- **Feature Flag**: RAG_ENABLED で RAG 機能の ON/OFF を制御
- **グレースフルデグラデーション**: embedding_available() が False の場合、フォールバックスコアを返す
