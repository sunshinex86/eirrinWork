"""10軸ルール + ベクトル埋め込みマッチングスコア関数（REQ-FIX-02）

REQ-06: 10軸統合スコア（必須スキル/歓迎スキル/スキル深度/スキル階層/文脈/ロール/埋め込み）
REQ-05: 全スコア 0.0〜1.0 正常化
v2: degraded mode 明示、重み検証、structured_skills 対応
"""
import datetime
import math
import re
from typing import Optional

from src.utils.vector_utils import (
    generate_embedding,
    compute_cosine_similarity,
    is_available as embedding_available,
)

# ロール分類キーワード
ROLE_KEYWORDS = {
    "SE": {
        "labels": ["システムエンジニア", "SE", "システム開発", "要件定義", "基本設計",
                     "詳細設計", "プログラマ", "エンジニア"],
    },
    "PM": {
        "labels": ["プロジェクトマネージャー", "PM", "プロジェクト管理", "PMO",
                     "プロジェクトリーダー", "PL", "開発リーダー"],
    },
    "アーキテクト": {
        "labels": ["アーキテクト", "システムアーキテクト", "ソリューションアーキテクト",
                     "テクニカルリード", "技術責任者"],
    },
    "データサイエンティスト": {
        "labels": ["データサイエンティスト", "データ分析", "機械学習エンジニア",
                     "AIエンジニア", "データエンジニア"],
    },
    "デザイナー": {
        "labels": ["デザイナー", "UI/UXデザイナー", "Webデザイナー",
                     "グラフィックデザイナー", "フロントエンドエンジニア"],
    },
    "インフラ": {
        "labels": ["インフラエンジニア", "ネットワークエンジニア", "サーバーエンジニア",
                     "DevOps", "SRE", "クラウドエンジニア"],
    },
    "スクラムマスター": {
        "labels": ["スクラムマスター", "アジャイルコーチ", "ファシリテーター"],
    },
    "セキュリティエンジニア": {
        "labels": ["セキュリティエンジニア", "セキュリティアナリスト", "脆弱性診断"],
    },
    "クラウドエンジニア": {
        "labels": ["クラウドエンジニア", "クラウドアーキテクト", "AWSエンジニア"],
    },
}

# 重み設定（config 読み込み前にデフォルト値/10軸）
HYBRID_WEIGHTS = {
    "required_skill": 0.20,
    "preferred_skill": 0.08,
    "skill_depth": 0.12,
    "skill_hierarchy": 0.08,
    "experience": 0.07,
    "location": 0.08,
    "context": 0.10,
    "role": 0.08,
    "unit_price": 0.07,
    "embedding": 0.12,
}


def _get_weights() -> dict:
    """設定ファイルから重みを取得（なければデフォルト）"""
    try:
        import config as cfg
        if hasattr(cfg, "HYBRID_WEIGHTS"):
            return cfg.HYBRID_WEIGHTS
    except (ImportError, AttributeError):
        pass
    return dict(HYBRID_WEIGHTS)


def _validate_weights(weights: dict) -> bool:
    """重みの合計が 1.0 であることを検証"""
    total = sum(weights.values())
    return abs(total - 1.0) < 0.001


# --- 10軸スコアリング関数 ---


def _compute_required_skill_score(resume: dict, job: dict) -> float:
    """必須スキル一致スコア（skill_id ベース）

    structured_required_skills と structured_skills を比較。
    """
    resume_skills = resume.get("structured_skills", [])
    job_skills = job.get("structured_required_skills", [])

    if not job_skills:
        return 1.0  # 必須スキルなし

    resume_ids = {s["skill_id"] if isinstance(s, dict) else s.skill_id for s in resume_skills}
    required_ids = {s["skill_id"] if isinstance(s, dict) else s.skill_id for s in job_skills}

    if not required_ids:
        return 1.0

    matched = len(resume_ids & required_ids)
    total = len(required_ids)

    score = matched / total if total > 0 else 1.0

    # レベル比較ボーナス
    level_bonus = 0.0
    if matched > 0:
        level_matches = 0
        for rs in resume_skills:
            r_id = rs["skill_id"] if isinstance(rs, dict) else rs.skill_id
            r_level = rs.get("level", 1) if isinstance(rs, dict) else rs.level
            for js in job_skills:
                j_id = js["skill_id"] if isinstance(js, dict) else js.skill_id
                j_level = js.get("required_level", 1) if isinstance(js, dict) else js.required_level
                if r_id == j_id and r_level >= j_level:
                    level_matches += 1
        level_bonus = 0.1 * (level_matches / matched) if matched > 0 else 0

    return min(score + level_bonus, 1.0)


def _compute_preferred_skill_score(resume: dict, job: dict) -> float:
    """歓迎スキル一致スコア（skill_id ベース）"""
    resume_skills = resume.get("structured_skills", [])
    job_skills = job.get("structured_preferred_skills", [])

    if not job_skills:
        return 1.0

    resume_ids = {s["skill_id"] if isinstance(s, dict) else s.skill_id for s in resume_skills}
    preferred_ids = {s["skill_id"] if isinstance(s, dict) else s.skill_id for s in job_skills}

    if not preferred_ids:
        return 1.0

    matched = len(resume_ids & preferred_ids)
    score = matched / len(preferred_ids)
    return score


def _compute_skill_depth_score(resume: dict, job: dict) -> float:
    """スキル深度スコア（REQ-RE2-02: 全必須スキル平均）

    全必須スキルの深度スコア合計 ÷ 必須スキル総数
    - 一致スキル：レベル、経験年数、最終利用年から計算
    - 未一致スキル：0.0
    - structured_skills=[]：全件未一致として 0.0
    - 必須スキルなし：1.0
    - 総経験年数による代替計算は禁止する
    """
    job_req = job.get("structured_required_skills", [])
    if not job_req:
        return 1.0  # 必須スキルなし

    resume_skills = resume.get("structured_skills", [])
    if not resume_skills:
        # 候補者スキルが空 → 全件未一致として 0.0（代替計算禁止）
        return 0.0

    current_year = datetime.datetime.now().year
    total_count = len(job_req)
    score_sum = 0.0

    for js in job_req:
        j_id = js["skill_id"] if isinstance(js, dict) else js.skill_id
        j_level = js.get("required_level", 1) if isinstance(js, dict) else js.required_level
        j_years = js.get("required_years", 0) if isinstance(js, dict) else js.required_years

        matched_depth = None
        for rs in resume_skills:
            r_id = rs["skill_id"] if isinstance(rs, dict) else rs.skill_id
            if r_id != j_id:
                continue

            r_level = rs.get("level", 0) if isinstance(rs, dict) else rs.level
            r_years = rs.get("years", 0) if isinstance(rs, dict) else rs.years
            r_last_used = rs.get("last_used_year", current_year) if isinstance(rs, dict) else getattr(rs, "last_used_year", current_year)

            # レベル比較
            level_score = min(r_level / j_level, 1.0) if j_level > 0 else 1.0
            # 年数比較
            years_score = min(r_years / j_years, 1.0) if j_years > 0 else 1.0
            # last_used_year 鮮度スコア（REQ-RE2-02）
            elapsed = max(0, current_year - r_last_used)
            if elapsed <= 1:
                freshness = 1.0
            elif elapsed <= 3:
                freshness = 0.9
            elif elapsed <= 5:
                freshness = 0.8
            elif elapsed <= 10:
                freshness = 0.5
            else:
                freshness = 0.3

            matched_depth = level_score * 0.5 + years_score * 0.4 + freshness * 0.1
            break

        if matched_depth is not None:
            score_sum += matched_depth
        # 未一致スキル: 0.0 を加算（何もしない）

    # 分母は必須スキル総数（一致件数ではない）
    return score_sum / total_count


def _compute_skill_hierarchy_score(resume: dict, job: dict) -> float:
    """スキル階層スコア（REQ-04: ツリー親子関係を利用）"""
    resume_skills = resume.get("structured_skills", [])
    resume_ids = {s["skill_id"] if isinstance(s, dict) else s.skill_id for s in resume_skills}

    job_req = job.get("structured_required_skills", [])
    if not job_req:
        return 1.0
    required_ids = {s["skill_id"] if isinstance(s, dict) else s.skill_id for s in job_req}

    try:
        from src.utils.skill_dictionary import get_root_categories
        from src.matching.skill_hierarchy import compute_hierarchy_score

        tree_roots = get_root_categories()
        score, _ = compute_hierarchy_score(
            resume_ids, required_ids, tree_roots,
            exact_coeff=1.0, child_parent_coeff=0.5, parent_child_coeff=0.3,
        )
        return score
    except Exception:
        # ツリー未ロード時は必須スキル一致率をフォールバックとして使用
        if not required_ids:
            return 1.0
        matched = len(resume_ids & required_ids)
        return matched / len(required_ids)


def _compute_context_score(resume: dict, job: dict) -> float:
    """業界・プロジェクト文脈スコア（埋め込み類似度ベース）"""
    if not embedding_available():
        return _rule_context_score(resume, job)

    # 文脈テキスト構築
    resume_parts = []
    for wh in resume.get("work_history", []):
        ind = wh.get("industry", "")
        desc = wh.get("description", "")
        resume_parts.append(f"{ind} {desc}")
    resume_text = " ".join(resume_parts)

    job_text = f"{job.get('industry', '')} {job.get('description', '')}"

    if not resume_text.strip() or not job_text.strip():
        return _rule_context_score(resume, job)

    try:
        vec1 = generate_embedding(resume_text)
        vec2 = generate_embedding(job_text)
        return compute_cosine_similarity(vec1, vec2)
    except Exception:
        return _rule_context_score(resume, job)


def _rule_context_score(resume: dict, job: dict) -> float:
    """ルールベースの業界一致スコア（フォールバック用）"""
    job_industry = job.get("industry", "")
    if not job_industry:
        return 1.0

    resume_industries = []
    for wh in resume.get("work_history", []):
        ind = wh.get("industry", "")
        if ind:
            resume_industries.append(ind)
    if not resume_industries:
        return 0.5

    # 直近の業界
    latest = resume_industries[-1]
    if latest == job_industry:
        return 1.0

    # 業界グループ判定
    try:
        from config import INDUSTRY_GROUPS
        for group_name, members in INDUSTRY_GROUPS.items():
            if latest in members and job_industry in members:
                return 0.7
    except ImportError:
        pass

    return 0.3


def _build_role_pattern(label: str) -> Optional[re.Pattern]:
    """ロールラベルからマッチパターンを生成（REQ-11: 単語境界対応）

    英字略称（SE, PM, PL）は英数字境界で判定。
    日本語名称は正規化後部分一致。
    """
    if re.match(r'^[A-Za-z0-9]{2,5}$', label):
        return re.compile(rf"(?<![A-Za-z0-9]){re.escape(label)}(?![A-Za-z0-9])", re.IGNORECASE)
    return re.compile(re.escape(label), re.IGNORECASE)


def _compute_role_score(resume: dict, job: dict) -> float:
    """ロール一致スコア（REQ-11: 単語境界対応）"""
    resume_text = ""
    for wh in resume.get("work_history", []):
        resume_text += f" {wh.get('position', '')} {wh.get('description', '')}"
    job_text = f"{job.get('title', '')} {job.get('job_type', '')} {job.get('description', '')}"

    resume_roles = set()
    job_roles = set()
    for role, info in ROLE_KEYWORDS.items():
        for label in info["labels"]:
            pattern = _build_role_pattern(label)
            if pattern.search(resume_text):
                resume_roles.add(role)
            if pattern.search(job_text):
                job_roles.add(role)

    if not job_roles:
        return 1.0
    if not resume_roles:
        return 0.5
    if resume_roles & job_roles:
        return 1.0

    role_groups = [
        {"SE", "アーキテクト"},
        {"PM", "SE"},
        {"データサイエンティスト", "インフラ"},
    ]
    for group in role_groups:
        if resume_roles & group and job_roles & group:
            return 0.7
    return 0.3


def _compute_embedding_similarity_score(resume: dict, job: dict) -> float:
    """意味類似度スコア（埋め込みベース）"""
    if not embedding_available():
        return 0.0

    # スキルテキスト
    resume_skill_text = " ".join(
        s["skill_id"] if isinstance(s, dict) else s.skill_id
        for s in resume.get("structured_skills", [])
    ) or " ".join(
        str(v) for v in resume.get("skills", {}).values() if isinstance(v, list)
    )
    job_skill_text = " ".join(
        s["skill_id"] if isinstance(s, dict) else s.skill_id
        for s in job.get("structured_required_skills", [])
    ) or " "

    if not resume_skill_text.strip() or not job_skill_text.strip():
        return 0.5

    try:
        vec1 = generate_embedding(resume_skill_text)
        vec2 = generate_embedding(job_skill_text)
        return compute_cosine_similarity(vec1, vec2)
    except Exception:
        return 0.0


# --- 追加評価軸（REQ-FIX-02）---


def _compute_experience_score(resume: dict, job: dict) -> float:
    """総経験年数スコア（補助評価軸）"""
    ry = resume.get("years_of_experience", 0)
    jy = job.get("required_experience_years", 0)
    if jy == 0:
        return 1.0
    ratio = ry / jy
    if ratio >= 1.0:
        return 1.0
    elif ratio >= 0.7:
        return ratio
    elif ratio >= 0.5:
        return ratio * 0.8
    return ratio * 0.5


def _compute_location_score(resume: dict, job: dict) -> float:
    """勤務地一致スコア（scorer.py 委譲）"""
    from src.matching.scorer import _compute_location_score as f
    return f(resume.get("location", ""), resume.get("desired_locations", []),
             job.get("location", ""), job.get("remote_policy", ""))


def _compute_unit_price_score(resume: dict, job: dict) -> float:
    """単価一致スコア（scorer.py 委譲）"""
    from src.matching.scorer import _compute_unit_price_score as f
    return f(resume.get("desired_unit_price_min", 0), resume.get("desired_unit_price_max", 0),
             job.get("unit_price_min", 0), job.get("unit_price_max", 0))


# --- 統合スコア関数（10軸）---


def compute_hybrid_score(
    resume: dict,
    job: dict,
) -> dict:
    """10軸統合スコアを計算（REQ-FIX-02）

    REQ-RE2-01: 遅延ロード失敗時も degraded mode へ切替＋重み再配分
    """
    degraded = not embedding_available()
    weights = _get_weights()
    if not _validate_weights(weights):
        weights = dict(HYBRID_WEIGHTS)

    # 防御的重複統合（FIX-04: 既存不正データ対策）
    from src.utils.skill_utils import deduplicate_skills_defensive
    if resume.get("structured_skills"):
        resume = dict(resume)
        resume["structured_skills"] = deduplicate_skills_defensive(resume["structured_skills"])
    for key in ("structured_required_skills", "structured_preferred_skills"):
        if job.get(key):
            job = dict(job)
            job[key] = deduplicate_skills_defensive(job[key])

    # 10軸スコア計算（embedding以外）
    req_score = _compute_required_skill_score(resume, job)
    pref_score = _compute_preferred_skill_score(resume, job)
    depth_score = _compute_skill_depth_score(resume, job)
    hier_score = _compute_skill_hierarchy_score(resume, job)
    exp_score = _compute_experience_score(resume, job)
    loc_score = _compute_location_score(resume, job)
    ctx_score = _compute_context_score(resume, job)
    role_score = _compute_role_score(resume, job)
    unit_price_score = _compute_unit_price_score(resume, job)

    # Embedding類似度スコア（内部で例外処理、遅延ロード失敗は後続の_status確認で検出）
    emb_score = _compute_embedding_similarity_score(resume, job) if not degraded else 0.0

    # 遅延ロード失敗検出: embedding_available=True でも emb_score=0 なら degraded へ
    if not degraded and emb_score == 0.0:
        from src.utils.vector_utils import get_model_status as _get_status
        _st = _get_status()
        if _st in ("not_downloaded", "load_failure", "not_installed"):
            degraded = True

    # Degraded mode: 比例配分（embedding_available と遅延ロード失敗の両方を考慮）
    if degraded:
        ew = weights.get("embedding", 0.12)
        if ew > 0:
            s = 1.0 / (1.0 - ew)
            weights = {k: v * s for k, v in weights.items() if k != "embedding"}
            weights["embedding"] = 0.0

    # RAG コンテキスト検索 → context score 補正（FIX-03）
    rag_ids = []
    rag_corrections: list[dict] = []
    resume_industries = {wh.get("industry", "") for wh in resume.get("work_history", []) if wh.get("industry")}
    job_industry = job.get("industry", "")
    try:
        from config import RAG_ENABLED, RAG_CONTEXT_SIMILARITY_THRESHOLD
        if RAG_ENABLED:
            from src.utils.rag_pipeline import search_matching_context
            rag_results = search_matching_context(resume, job, top_k=2)
            base_ctx_score = ctx_score
            total_rag_boost = 0.0
            for r in rag_results:
                rid = r.get("id", "")
                if not rid:
                    continue
                rag_ids.append(rid)
                sim = r.get("similarity_score")
                if sim is not None and sim >= RAG_CONTEXT_SIMILARITY_THRESHOLD:
                    cat = r.get("category", "")
                    # 業界/文脈関連性: category=="industry" かつ両側業界がエントリのtags/contentに対応
                    if cat == "industry":
                        entry_tags = set(r.get("tags", []))
                        entry_content = r.get("content", "").lower()
                        resume_matches = any(ind in entry_tags or ind.lower() in entry_content for ind in resume_industries if ind)
                        job_matches = bool(job_industry) and (
                            job_industry in entry_tags or job_industry.lower() in entry_content
                        )
                        if resume_matches and job_matches:
                            boost = min(max(0.30 - total_rag_boost, 0.0), (sim - RAG_CONTEXT_SIMILARITY_THRESHOLD) * 1.0)
                            if boost > 0:
                                total_rag_boost += boost
                                ctx_score = min(1.0, base_ctx_score + total_rag_boost)
                                rag_corrections.append({
                                    "source_id": rid,
                                    "before_score": round(base_ctx_score, 4),
                                    "after_score": round(ctx_score, 4),
                                    "reason": f"業界ナレッジ一致（類似度{sim:.2f}）+{boost:.2f}",
                                })
                                continue
                            else:
                                rag_corrections.append({
                                    "source_id": rid,
                                    "before_score": round(base_ctx_score, 4),
                                    "after_score": round(ctx_score, 4),
                                    "reason": "上限0.30に達したため参照のみ",
                                })
                                continue
                        # 条件不一致: 業界/案件関連性が不十分
                        rag_corrections.append({
                            "source_id": rid,
                            "before_score": round(base_ctx_score, 4),
                            "after_score": round(base_ctx_score, 4),
                            "reason": "業界/案件関連性が不十分なため参照のみ",
                        })
                        continue
                    else:
                        rag_corrections.append({
                            "source_id": rid,
                            "before_score": round(base_ctx_score, 4),
                            "after_score": round(base_ctx_score, 4),
                            "reason": f"カテゴリ'{cat}'は補正対象外のため参照のみ",
                        })
                        continue
                else:
                    # Keyword fallback または 類似度不足 → 参照情報としてのみ返却
                    rag_corrections.append({
                        "source_id": rid,
                        "before_score": round(base_ctx_score, 4),
                        "after_score": round(base_ctx_score, 4),
                        "reason": "類似度不足または類似度不明のため参照のみ",
                    })
                    continue
    except Exception as e:
        import logging
        _logger = logging.getLogger(__name__)
        _logger.error(f"RAG search failed: {e}")

    # 統合（10軸、補正後ctx_scoreを使用）
    total = (
        req_score * weights["required_skill"] +
        pref_score * weights["preferred_skill"] +
        depth_score * weights["skill_depth"] +
        hier_score * weights["skill_hierarchy"] +
        exp_score * weights["experience"] +
        loc_score * weights["location"] +
        ctx_score * weights["context"] +
        role_score * weights["role"] +
        unit_price_score * weights["unit_price"] +
        emb_score * weights["embedding"]
    )
    total = max(0.0, min(1.0, total))

    # スキルギャップ（REQ-07: 必須/歓迎を分離 + 重複除去）
    resume_ids = {
        s["skill_id"] if isinstance(s, dict) else s.skill_id
        for s in resume.get("structured_skills", [])
    }
    required_ids = {
        s["skill_id"] if isinstance(s, dict) else s.skill_id
        for s in job.get("structured_required_skills", [])
    }
    preferred_ids = {
        s["skill_id"] if isinstance(s, dict) else s.skill_id
        for s in job.get("structured_preferred_skills", [])
    }
    matched_req = list(resume_ids & required_ids)
    matched_pref = [s for s in (resume_ids & preferred_ids) if s not in required_ids]  # 重複除去
    missing_req = list(required_ids - resume_ids)
    missing_pref = list(preferred_ids - resume_ids)

    # モード名
    if degraded:
        mode_name = "hybrid_degraded"
    elif emb_score > 0:
        mode_name = "hybrid"
    else:
        mode_name = "hybrid"

    # 説明文生成
    explanation_parts = []
    if req_score >= 0.8:
        explanation_parts.append("必須スキルを十分満たしている")
    elif req_score >= 0.5:
        explanation_parts.append("必須スキルが概ね一致")
    else:
        explanation_parts.append("必須スキルの不足がある")

    if depth_score >= 0.8:
        explanation_parts.append("経験深度が十分")
    elif depth_score < 0.5:
        explanation_parts.append("経験深度が不足気味")

    if emb_score >= 0.7:
        explanation_parts.append("意味的類似度が高い")
    elif emb_score >= 0.4:
        explanation_parts.append("意味的類似度は中程度")

    if rag_ids:
        explanation_parts.append(f"（ナレッジ参照: {', '.join(rag_ids[:2])}）")

    if degraded:
        explanation_parts.append("（埋め込みモデル未導入のためdegraded mode）")

    return {
        "mode": mode_name,
        "degraded": degraded,
        "total_score": round(total, 4),
        "weights": {k: round(v, 4) for k, v in weights.items()},
        "breakdown": {
            "required_skill_score": round(req_score, 4),
            "preferred_skill_score": round(pref_score, 4),
            "skill_depth_score": round(depth_score, 4),
            "skill_hierarchy_score": round(hier_score, 4),
            "experience_score": round(exp_score, 4),
            "location_score": round(loc_score, 4),
            "context_score": round(ctx_score, 4),
            "role_score": round(role_score, 4),
            "unit_price_score": round(unit_price_score, 4),
            "embedding_score": round(emb_score, 4),
        },
        "matched_skills": matched_req + matched_pref,
        "missing_required_skills": missing_req,
        "missing_preferred_skills": missing_pref,
        "rag_sources": rag_ids,
        "rag_corrections": rag_corrections,
        "explanation": "。".join(explanation_parts) + "。",
    }
