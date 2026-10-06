# Raw Requirement

> Received: 2026-06-27
> Version: 修正Requirement

機能1 修正Requirement
1. 目的
マッチング品質向上機能を、単なるキーワード一致から以下を考慮した仕組みに改善する。
スキル標準化・階層関係
スキルごとのレベル／経験年数
業界・プロジェクト文脈
ロール適合性
ルール＋ベクトル埋め込み
SKILLS／RAG／MCPのシステム内利用
2. 必須修正項目
REQ-01 スキル深度モデル
候補者と案件のスキルを、文字列ではなく属性付きデータとして管理する。
候補者側：
{
  "skill_id": "java",
  "level": 4,
  "years": 5,
  "last_used_year": 2026
}
案件側：
{
  "skill_id": "java",
  "required_level": 3,
  "required_years": 3,
  "required": true
}
受入条件：
スキルごとにレベルと経験年数を比較できる
総経験年数をスキル経験年数の代用にしない
既存データとの後方互換性を保つ
REQ-02 スキル標準化の統合
スキル辞書を唯一の標準化元として利用する。
受入条件：
登録、更新、抽出、検索、マッチングの全経路で標準化する
JS、JavaScript、javascriptを同一IDとして扱う
未登録スキルを識別できる
同義語定義の重複管理を廃止する
スキルIDをマッチングの比較単位とする
REQ-03 スキル辞書とツリーの整合性
辞書とツリーを一貫したオントロジーとして管理する。
受入条件：
ツリー内のスキルIDは辞書に存在する
辞書登録スキルには、原則としてツリー上のパスが存在する
同一名称に複数IDを割り当てない
Java → Spring → Spring Bootの親子関係を取得できる
CIで重複ID、重複名称、孤立ノードを検出する
REQ-04 階層を考慮したマッチング
完全一致以外に親子スキル関係をスコアへ反映する。
例：
Spring Boot経験者はSpring要件に適合する
Java経験のみでSpring Boot要件を完全適合とはしない
受入条件：
完全一致、子→親、親→子で異なる係数を設定する
階層一致の理由を結果に表示する
REQ-05 Embeddingスコアの正常化
コサイン類似度をシステムのスコア仕様に合わせる。
受入条件：
外部公開スコアは必ず0.0～1.0
負のコサイン類似度をそのまま返さない
NaN、無限値、次元不一致を安全に処理する
最終スコアも0.0～1.0に制限する
REQ-06 ルール＋Embedding統合スコア
以下を統合して最終スコアを計算する。
必須スキル一致
歓迎スキル一致
スキル深度
スキル階層
業界・プロジェクト文脈
ロール
意味類似度
受入条件：
重みを設定ファイルから変更できる
重みの合計を検証する
embeddingが利用できない場合は明示的に degraded mode とする
fallback時も必須スキルを評価する
利用した計算方式と内訳をレスポンスに含める
REQ-07 Embedding実行環境
受入条件：
sentence-transformersを正式な依存関係または明確なoptional dependencyとして定義する
モデルを起動時または初回利用時に一度だけロードする
モデル未導入、読込失敗、タイムアウトを区別する
status APIがモデルのダウンロードを開始しない
バッチ埋め込みとベクトルキャッシュを利用する
REQ-08 RAGの業務フロー統合
RAGを次の処理で実際に利用する。
自由記述からのスキル抽出
業界コンテキスト補完
ロール判定
マッチ理由生成
受入条件：
RAG_ENABLED=falseの場合は検索を実行しない
RAG利用有無と参照ナレッジIDを結果に含める
keyword検索とsemantic検索のfallbackを提供する
検索結果がマッチング結果へ反映される
RAGなしでも基本マッチングが動作する
REQ-09 MCP Serverの正式実装
受入条件：
MCP SDK準拠のserverとして起動できる
stdioまたはHTTP/SSE transportを提供する
tools/listとtools/callに応答する
入力をJSON Schemaで検証する
未知のtool／methodをエラーにする
次のツールを提供する
matching_score
search_skills
get_skill_context
search_knowledge
analyze_skill_gap
REQ-10 SKILLS実行基盤
受入条件：
SKILLSを関数置場ではなく、AI Agentから呼び出せるtoolとして登録する
スキル名、説明、入力Schema、出力Schemaを定義する
API、Agent、MCPから同じサービス層を利用する
ランキング前にスコア順へソートする
実行ログとエラー情報を記録する
3. API要件
マッチングレスポンスに以下を追加する。
{
  "mode": "hybrid",
  "degraded": false,
  "total_score": 0.82,
  "breakdown": {
    "required_skill_score": 0.9,
    "preferred_skill_score": 0.7,
    "skill_depth_score": 0.8,
    "skill_hierarchy_score": 0.75,
    "context_score": 0.8,
    "role_score": 0.9,
    "embedding_score": 0.78
  },
  "matched_skills": [],
  "missing_skills": [],
  "rag_sources": [],
  "explanation": ""
}
4. テスト要件
必須テスト：
スキル別レベル／経験年数
同義語・全角半角・大小文字
親子スキル判定
辞書とツリーの整合性
cosine負値とゼロベクトル
実embeddingモデルを使った統合テスト
RAG有効／無効テスト
RAGが結果へ反映されること
MCP起動、tools/list、tools/call
Agent SKILLS呼び出し
embedding障害時のfallback
APIスコアが常に0～1
5. 優先順位
P1：スコア正常化、スキル深度、標準化統合
P1：RAG主処理統合、MCP正式実装
P2：辞書・ツリー整合性、階層マッチング
P2：SKILLS実行基盤
P2：性能改善、キャッシュ、監視、統合テスト
完了条件は「モジュールが存在すること」ではなく、API／UI／Agent／MCPから実際に利用され、テストで確認できることです。
