"""RAG（検索拡張生成）パイプライン

スキル抽出時とマッチング時に、ナレッジベースから関連情報を検索する。
ローカルファイルベースのシンプルな構成で、embedding を使った意味検索を提供する。
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional

import config

_logger = logging.getLogger(__name__)

# ナレッジベースディレクトリ
KNOWLEDGE_DIR = Path(config.RAG_KNOWLEDGE_DIR)

# キャッシュ
_knowledge_base: Optional[list[dict]] = None


def _load_knowledge_base() -> list[dict]:
    """ナレッジベースをロード（キャッシュあり）"""
    global _knowledge_base
    if _knowledge_base is not None:
        return _knowledge_base

    kb = []
    if not KNOWLEDGE_DIR.exists():
        _knowledge_base = kb
        return kb

    for json_file in sorted(KNOWLEDGE_DIR.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    kb.extend(data)
                elif isinstance(data, dict) and "entries" in data:
                    kb.extend(data["entries"])
        except (json.JSONDecodeError, IOError):
            pass

    _knowledge_base = kb
    return kb


def is_available() -> bool:
    """RAG が利用可能かを返す"""
    if not config.RAG_ENABLED:
        return False
    try:
        kb = _load_knowledge_base()
        return len(kb) > 0
    except Exception:
        return False


def get_all_knowledge() -> list[dict]:
    """全ナレッジエントリを取得"""
    return _load_knowledge_base()


def get_knowledge_by_category(category: str) -> list[dict]:
    """カテゴリ別にナレッジを取得"""
    kb = _load_knowledge_base()
    return [entry for entry in kb if entry.get("category") == category]


def search_knowledge_keyword(query: str, top_k: Optional[int] = None) -> list[dict]:
    """キーワードベースでナレッジを検索（REQ-RE4-03: top_k対応）"""
    q = query.lower()
    kb = _load_knowledge_base()
    results = []

    for entry in kb:
        content = entry.get("content", "").lower()
        tags = [t.lower() for t in entry.get("tags", [])]
        title = entry.get("id", "").lower()

        if q in content or q in title or any(q in tag for tag in tags):
            results.append(entry)

    if top_k is not None:
        return results[:top_k]
    return results


def search_knowledge_semantic(query: str, top_k: int = 3) -> list[dict]:
    """埋め込みベースでナレッジを意味検索

    Returns:
        list[dict]: 各エントリに similarity_score を付与した結果のリスト。
        スコア降順。エラー時は空リスト＋ログ。
    """
    kb = _load_knowledge_base()
    if not kb:
        return []

    try:
        from src.utils.vector_utils import generate_embedding, compute_cosine_similarity

        query_vec = generate_embedding(query)
        scored = []

        for entry in kb:
            try:
                content = entry.get("content", "")
                vec = generate_embedding(content)
                score = compute_cosine_similarity(query_vec, vec)
                entry_with_score = dict(entry)
                entry_with_score["similarity_score"] = round(score, 4)
                if score > 0.3:
                    scored.append((score, entry_with_score))
            except Exception as e:
                _logger.warning(f"RAG semantic search entry error: {e}")
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for score, entry in scored[:top_k]]
    except ImportError as e:
        _logger.warning(f"RAG semantic search unavailable, falling back to keyword: {e}")
        return search_knowledge_keyword(query)
    except Exception as e:
        _logger.error(f"RAG semantic search failed: {e}", exc_info=True)
        return search_knowledge_keyword(query)


def search_skill_context(skill_name: str, top_k: int = 2) -> list[dict]:
    """スキルに関連するナレッジを検索（スキル抽出時用、REQ-RE4-03: keyword側もtop_k対応）"""
    results = search_knowledge_keyword(skill_name, top_k=top_k)
    if not results and RAG_ENABLED:
        results = search_knowledge_semantic(skill_name, top_k)
    return results


def _search_matching_context_degraded(resume: dict, job: dict, top_k: int = 2) -> list[dict]:
    """Degraded時のキーワード分割検索（REQ-RE3-05）

    Embedding未使用時に、業界・ロール・スキルごとに個別キーワード検索し
    結果を統合する。長い複合クエリは使用しない。

    Returns:
        関連ナレッジエントリのリスト
    """
    keywords = []

    # 候補者の各業界
    for wh in resume.get("work_history", []):
        ind = wh.get("industry", "")
        if ind:
            keywords.append(ind)

    # 案件の業界
    job_industry = job.get("industry", "")
    if job_industry:
        keywords.append(job_industry)

    # 候補者の各ロール
    for wh in resume.get("work_history", []):
        pos = wh.get("position", "")
        if pos:
            keywords.append(pos)

    # 案件のロール
    job_title = job.get("title", "")
    if job_title:
        keywords.append(job_title)

    # structured skill IDs（候補者）
    for ss in resume.get("structured_skills", []):
        sid = ss.get("skill_id", "") if isinstance(ss, dict) else getattr(ss, "skill_id", "")
        if sid:
            keywords.append(sid)

    # structured skill IDs（案件）
    for key in ("structured_required_skills", "structured_preferred_skills"):
        for ss in job.get(key, []):
            sid = ss.get("skill_id", "") if isinstance(ss, dict) else getattr(ss, "skill_id", "")
            if sid:
                keywords.append(sid)

    # 重複排除して個別検索→統合
    seen_ids = set()
    hit_count = {}  # id -> hit count
    results: list[dict] = []

    for kw in sorted(set(keywords)):
        if not kw:
            continue
        try:
            for entry in search_knowledge_keyword(kw):
                eid = entry.get("id", "")
                if eid and eid not in seen_ids:
                    seen_ids.add(eid)
                    hit_count[eid] = 1
                    results.append(entry)
                elif eid:
                    hit_count[eid] = hit_count.get(eid, 0) + 1
        except Exception:
            continue

    # ヒット回数順にソート
    results.sort(key=lambda x: hit_count.get(x.get("id", ""), 0), reverse=True)
    return results[:top_k]


def search_matching_context(resume: dict, job: dict, top_k: int = 2) -> list[dict]:
    """マッチング時に関連ナレッジを検索

    REQ-RE3-05: Embedding不可時はキーワード分割検索にフォールバック。

    Args:
        resume: 経歴書データ
        job: 案件データ
        top_k: 取得件数

    Returns:
        関連ナレッジエントリのリスト（エラー時は空リスト＋ログ）
    """
    query_parts = []

    industries = []
    for wh in resume.get("work_history", []):
        ind = wh.get("industry", "")
        if ind:
            industries.append(ind)
    if industries:
        query_parts.append("業界:" + " ".join(industries))
    if job.get("industry"):
        query_parts.append("業界:" + job.get("industry", ""))

    for wh in resume.get("work_history", []):
        pos = wh.get("position", "")
        if pos:
            query_parts.append("ロール:" + pos)
    if job.get("title"):
        query_parts.append("役割:" + job.get("title", ""))

    query = " ".join(query_parts)
    if not query.strip():
        return []

    # セマンティック検索を試行、失敗時はDegradedフォールバック
    try:
        results = search_knowledge_semantic(query, top_k)
        if results:
            return results
    except Exception:
        _logger.debug("RAG semantic search unavailable, using degraded keyword split")
        pass

    # Degraded時: キーワード分割検索
    return _search_matching_context_degraded(resume, job, top_k)


def invalidate_cache():
    """キャッシュをクリア"""
    global _knowledge_base
    _knowledge_base = None


# RAG_ENABLED の互換性参照
RAG_ENABLED = config.RAG_ENABLED
