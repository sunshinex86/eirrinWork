# 🤝 経歴書×案件マッチングシステム

経歴書（人材）と案件（求人）を**双方向**にマッチングするシステムです。  
10軸ハイブリッドマッチング（ルールベース + ベクトル埋め込み）に対応しています。

## 機能

- **経歴書管理**: 候補者の経歴書を登録・管理（保留スキル対応）
- **案件管理**: 求人案件を登録・管理（保留スキル対応）
- **マッチング**: 経歴書→案件 / 案件→経歴書 の双方向マッチング
  - Hybrid 10軸（デフォルト） / Keyword 5軸 / Semantic（Claude API）
- **スキル管理**: スキル辞書・ツリーの管理画面
- **RAGコンテキスト検索**: 業界ナレッジによるスコア補正

## アーキテクチャ

```
matching-system/
├── run.py                  # 起動スクリプト（API + UI 同時起動）
├── config.py               # 設定（重み、パス、フィーチャーフラグ）
├── requirements.txt        # 依存パッケージ
├── .env.example            # 環境変数サンプル
├── data/
│   ├── resumes.json        # 経歴書データ（運用）
│   ├── jobs.json           # 案件データ（運用）
│   ├── sample_*.json       # サンプルデータ
│   ├── skills/             # スキル辞書（136スキル）＋ツリー
│   ├── knowledge/          # RAGナレッジベース
│   └── evaluation/         # マッチング品質評価データ
├── src/
│   ├── models/             # Pydantic データモデル
│   │   ├── resume.py       #   経歴書 + PendingSkill
│   │   ├── job.py          #   案件モデル
│   │   └── match_result.py #   マッチ結果 + RagCorrection
│   ├── matching/           # マッチングエンジン
│   │   ├── scorer.py       #   5軸キーワードスコアラー
│   │   ├── keyword_matcher.py  # 双方向キーワードマッチング
│   │   ├── embedding_matcher.py # 10軸ハイブリッド + embedding
│   │   ├── skill_hierarchy.py   # スキルツリー階層スコア
│   │   └── semantic_matcher.py  # Claude API 意味的マッチング
│   ├── repository/         # データアクセス層（JSON + ファイルロック）
│   │   ├── base.py         #   抽象基底
│   │   ├── json_resume_repo.py
│   │   └── json_job_repo.py
│   ├── utils/
│   │   ├── skill_dictionary.py   # スキル辞書CRUD + ツリー操作
│   │   ├── skill_utils.py        # スキル重複統合
│   │   ├── skill_extraction_service.py # 共通スキル抽出
│   │   ├── skill_extractor.py
│   │   ├── text_utils.py
│   │   ├── vector_utils.py       # Embedding生成
│   │   └── rag_pipeline.py       # RAGナレッジ検索
│   ├── api/                # FastAPI バックエンド
│   │   ├── main.py
│   │   ├── routes_resumes.py     # 経歴書CRUD + pending
│   │   ├── routes_jobs.py        # 案件CRUD + pending
│   │   ├── routes_match.py       # マッチングAPI（hybrid/keyword/semantic）
│   │   └── routes_skills.py      # スキル管理API + pending変換API
│   └── ui/                 # Streamlit フロントエンド
│       ├── app.py
│       └── pages/
│           ├── 01_経歴書管理.py   # 保留スキル操作UI
│           ├── 02_案件管理.py     # 保留スキル操作UI
│           ├── 03_マッチング.py   # 2タブ（埋め込み独立タブ廃止）
│           └── 04_スキル管理.py   # スキル管理画面（新規）
├── scripts/
│   ├── evaluate_matching.py      # マッチング品質評価
│   └── generate_evaluation_data.py
├── mcp_server.py           # MCPサーバ（独立、実験用）
└── tests/                  # 389 tests
```

## マッチングの仕組み

### Hybrid 10軸（デフォルト）

| 評価軸 | 重み | 内容 |
|--------|------|------|
| 🔧 必須スキル一致 | 20% | skill_idベースの必須スキル一致率＋レベルボーナス |
| ⭐ 歓迎スキル一致 | 8% | 歓迎スキルの一致率 |
| 📊 スキル深度 | 12% | レベル・経験年数・最終利用年の総合評価 |
| 🌳 スキル階層 | 8% | スキルツリーの親子関係による部分一致 |
| 📅 経験年数 | 7% | 必要経験年数に対する充足度 |
| 📍 勤務地 | 8% | 居住地・希望勤務地・リモート条件 |
| 📖 文脈 | 10% | 業界・プロジェクト文脈（RAG補正可能） |
| 👤 ロール | 8% | 9種類のロール分類による一致判定 |
| 💰 年収 | 7% | 希望年収と案件年収のオーバーラップ率 |
| 🔬 Embedding | 12% | ベクトル類似度（Hybrid内部評価軸） |

**Embedding** はHybrid内部の評価軸としてのみ利用し、独立した画面・APIは持たない。
Embeddingモデルが利用できない場合、自動的に Degraded Mode（重み再配分）へ切り替わる。

### Keyword 5-axis（従来方式）

スキル(40%) / 経験(20%) / 勤務地(15%) / 業界(10%) / 年収(15%) の5軸でスコアリング。

### RAGスコア補正

`RAG_ENABLED=true` 設定時、マッチング時に業界ナレッジベースを検索し、文脈スコアを補正する。

**補正式**: `adjusted = min(1.0, ctx_score + min(0.30, (similarity - 0.70) * 1.0))`

- コサイン類似度 >= 0.70 **かつ** 業界カテゴリ一致 + 両側リソース対応 の場合のみ補正
- Keyword fallback結果は参照情報としてのみ返却（スコア補正に使用しない）
- 最大加点 0.30、上限 1.0
- 補正情報は `rag_corrections` フィールドに記録

## 未登録スキル処理フロー

1. Job/Resume登録時にスキル辞書にないスキル名/IDが含まれていても保存は成功する
2. 未登録スキルは `pending_skills` として保存される（raw_name/レベル/年数保持）
3. APIレスポンスに `warnings` フィールドで未登録スキルが通知される
4. 保存後、UIから以下を選択可能：
   - **新規スキル登録**: 辞書に追加し、structured_skillsへ反映
   - **既存スキル紐付け**: 既存skill_idに紐付け、structured_skillsへ反映
   - **無視**: status=ignored、マッチング対象外
5. 登録/紐付け後、即時マッチングスコアに反映される

## スキル管理画面

左メニューから「スキル管理」で以下の操作が可能：

- スキル一覧表示（テーブル）
- 名称・別名・カテゴリによる検索
- 新規スキル登録（ツリー未指定→「未分類」）
- スキル情報編集
- スキル論理削除（参照ある場合は無効化案内）
- スキルツリー位置確認
- 使用中Job/Resume確認
- 整合性検証

## Degraded Mode

Embeddingモデルが利用できない場合、以下の動作となる：

- Hybridマッチングのembedding重み(12%)を他9軸へ比例配分
- RAG検索はキーワード分割検索にフォールバック（参照情報のみ）
- 画面に Warning 表示
- `hybrid_degraded` モードとして動作

## クイックスタート

### 前提条件

- Python 3.9+
- pip

### インストール

```bash
cd matching-system
pip install -r requirements.txt
cp .env.example .env
```

### 起動

```bash
python run.py
# API: http://localhost:8000
# UI:  http://localhost:8501
```

### Embeddingモデルの有効化（任意）

```bash
# requirements-ai.txt をインストール
pip install -r requirements-ai.txt
# モデルを手動ダウンロード
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"
# .env で有効化
EMBEDDING_ENABLED=true
```

## MCP / AI Agent 対応状況

- **MCPサーバ**: `mcp_server.py` として独立起動可能（FastMCP準拠）。
  6ツール提供（matching_score/search_skills/get_skill_context/search_knowledge/analyze_skill_gap/extract_skills）。
  現在のシステム実行経路（run.py）からは呼び出されない独立した実験用インターフェース。
- **AI Agent**: 6つのAgent Skill実装済み（rank_matches/suggest_improvements等）。
  共通AgentService層は未実装（今後の課題）。

## テスト

```bash
# 全テスト実行
python -m pytest tests/ -q

# テスト数: 389 tests
# 対象: モデル/マッチング/API/ユーティリティ/RAG/スキル辞書/リポジトリ
```

## 評価

マッチング品質評価データを `data/evaluation/` に用意。
自動生成ベースラインによる暫定評価：

| 指標 | Keyword | Hybrid | 改善 |
|------|---------|--------|------|
| Precision@1 (resume→job) | 0.200 | **0.500** | +0.300 |
| Recall@1 (resume→job) | 0.150 | **0.450** | +0.300 |
| nDCG@3 (resume→job) | 0.498 | **0.755** | +0.257 |

```bash
python scripts/evaluate_matching.py
```
