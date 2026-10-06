"""
MCP（Model Context Protocol）Server — fastmcp SDK 準拠

REQ-09: MCP SDK 準拠のサーバーとして起動。
tools/list, tools/call に応答、JSON Schema 検証、stdio/HTTP transport。

提供ツール:
- matching_score
- search_skills
- get_skill_context
- search_knowledge
- analyze_skill_gap
- market_skill_supply_demand
- market_unit_price_trend
- market_tech_trend
"""
import json
import sys
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP
from pydantic import BaseModel, Field

# プロジェクトルート
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# --- サービス層（API/Agent/MCP 共通） ---
from src.utils.skill_dictionary import get_all_skills, search_skills as dict_search, get_skill_by_name
from src.utils.rag_pipeline import search_knowledge_keyword
from src.repository.json_resume_repo import JsonResumeRepository
from src.repository.json_job_repo import JsonJobRepository
import config


# --- MCP Server ---
mcp = FastMCP("matching-system")


# --- 入力スキーマ ---

class MatchingScoreInput(BaseModel):
    resume_id: str = Field(..., description="経歴書ID")
    job_id: str = Field(..., description="案件ID")
    method: str = Field(default="hybrid", pattern="^(keyword|hybrid|semantic)$",
                         description="マッチング方式")


class SearchSkillsInput(BaseModel):
    query: str = Field(..., min_length=1, max_length=200, description="検索クエリ")
    category: Optional[str] = Field(default=None, description="カテゴリフィルタ（任意）")


class SkillContextInput(BaseModel):
    skill_name: str = Field(..., description="スキル名")


class KnowledgeSearchInput(BaseModel):
    query: str = Field(..., min_length=1, max_length=200, description="検索クエリ")


class SkillGapInput(BaseModel):
    resume_id: str = Field(..., description="経歴書ID")
    job_id: str = Field(..., description="案件ID")


class ExtractSkillsInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=20000, description="抽出元テキスト")
    use_rag: bool = Field(default=False, description="RAG補完を使用するか")
    top_k: int = Field(default=20, ge=1, le=100, description="最大候補数")


class RecommendationReasonInput(BaseModel):
    resume_id: str = Field(..., min_length=1, description="経歴書ID")
    job_id: str = Field(..., min_length=1, description="案件ID")


class JdOptimizationInput(BaseModel):
    raw_jd: str = Field(..., min_length=1, max_length=40000, description="最適化対象JD")
    budget_range: Optional[dict] = Field(default=None, description="予算レンジ")


class RecommendationActionsInput(BaseModel):
    resume_id: str = Field(..., min_length=1, description="経歴書ID")
    top_n: int = Field(default=5, ge=1, le=20, description="推薦件数")


class ResumeJobMatchesInput(BaseModel):
    resume_id: str = Field(..., min_length=1, description="経歴書ID")
    top_n: Optional[int] = Field(default=None, ge=1, le=50, description="返却件数上限（未指定なら全件）")


class ScheduleAvailabilityInput(BaseModel):
    candidate_availability: dict = Field(..., description="候補者の稼働状況")
    job_window: dict = Field(..., description="案件の希望時間帯")


class ScheduleConflictInput(BaseModel):
    candidate_availability: dict = Field(..., description="候補者の稼働状況")
    other_events: list[dict] = Field(..., description="競合イベント一覧")


class MarketSkillSupplyDemandInput(BaseModel):
    start_date: Optional[str] = Field(default=None, description="集計開始日（YYYY-MM-DD、省略時は今年1/1）")
    end_date: Optional[str] = Field(default=None, description="集計終了日（YYYY-MM-DD、省略時は本日）")


class MarketUnitPriceTrendInput(BaseModel):
    start_date: Optional[str] = Field(default=None, description="集計開始日（YYYY-MM-DD、省略時は今年1/1）")
    end_date: Optional[str] = Field(default=None, description="集計終了日（YYYY-MM-DD、省略時は本日）")
    skill_id: Optional[str] = Field(default=None, description="スキルIDで絞り込み（任意）")
    job_type: Optional[str] = Field(default=None, description="職種で絞り込み（任意）")


class MarketTechTrendInput(BaseModel):
    start_date: Optional[str] = Field(default=None, description="集計開始日（YYYY-MM-DD、省略時は今年1/1）")
    end_date: Optional[str] = Field(default=None, description="集計終了日（YYYY-MM-DD、省略時は本日）")
    top_n: int = Field(default=10, ge=1, le=50, description="上位/下位何件を返すか")


# --- ツール定義 ---

@mcp.tool(name="matching_score", annotations={
    "title": "Match Score Calculator",
    "readOnlyHint": True,
    "idempotentHint": True,
})
def matching_score(params: MatchingScoreInput) -> str:
    """経歴書と案件のマッチングスコアを計算する（hybrid/keyword/semantic から選択）"""
    resume_repo = JsonResumeRepository(config.RESUMES_FILE)
    job_repo = JsonJobRepository(config.JOBS_FILE)

    resume = resume_repo.find_by_id(params.resume_id)
    job = job_repo.find_by_id(params.job_id)
    if not resume or not job:
        return json.dumps({"error": "経歴書または案件が見つかりません"}, ensure_ascii=False)

    if params.method == "hybrid":
        from src.matching.embedding_matcher import compute_hybrid_score
        result = compute_hybrid_score(resume, job)
    elif params.method == "keyword":
        from src.matching.scorer import score_resume_against_job
        result = score_resume_against_job(resume, job)
    else:
        from src.matching.semantic_matcher import semantic_match
        result = semantic_match(params.resume_id, params.job_id)

    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(name="search_skills", annotations={
    "title": "Search Skills",
    "readOnlyHint": True,
    "idempotentHint": True,
})
def search_skills(params: SearchSkillsInput) -> str:
    """スキル辞書からスキルを検索する（部分一致対応）"""
    results = dict_search(params.query)
    if params.category:
        results = [r for r in results if r.get("category") == params.category]
    return json.dumps({"results": results[:20]}, ensure_ascii=False, indent=2)


@mcp.tool(name="get_skill_context", annotations={
    "title": "Get Skill Context",
    "readOnlyHint": True,
    "idempotentHint": True,
})
def get_skill_context(params: SkillContextInput) -> str:
    """スキルに関連する業界知識・ロール情報をナレッジベースから取得する"""
    skill = get_skill_by_name(params.skill_name)
    knowledge = search_knowledge_keyword(params.skill_name)
    result = {
        "skill": skill,
        "related_knowledge": [
            {"id": k["id"], "content": k["content"][:200], "category": k.get("category")}
            for k in knowledge[:3]
        ],
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(name="search_knowledge", annotations={
    "title": "Search Knowledge Base",
    "readOnlyHint": True,
    "idempotentHint": True,
})
def search_knowledge(params: KnowledgeSearchInput) -> str:
    """ナレッジベースからキーワード検索する"""
    results = search_knowledge_keyword(params.query)
    return json.dumps(
        [{"id": r["id"], "content": r["content"][:200], "category": r.get("category")} for r in results[:5]],
        ensure_ascii=False, indent=2,
    )


@mcp.tool(name="analyze_skill_gap", annotations={
    "title": "Analyze Skill Gap",
    "readOnlyHint": True,
    "idempotentHint": True,
})
def analyze_skill_gap(params: SkillGapInput) -> str:
    """経歴書と案件のスキルギャップを分析する"""
    resume_repo = JsonResumeRepository(config.RESUMES_FILE)
    job_repo = JsonJobRepository(config.JOBS_FILE)
    resume = resume_repo.find_by_id(params.resume_id)
    job = job_repo.find_by_id(params.job_id)

    if not resume or not job:
        return json.dumps({"error": "経歴書または案件が見つかりません"}, ensure_ascii=False)

    resume_ids = {s["skill_id"] if isinstance(s, dict) else s.skill_id
                  for s in resume.get("structured_skills", [])}
    req_ids = {s["skill_id"] if isinstance(s, dict) else s.skill_id
               for s in job.get("structured_required_skills", [])}
    pref_ids = {s["skill_id"] if isinstance(s, dict) else s.skill_id
                for s in job.get("structured_preferred_skills", [])}

    matched = resume_ids & req_ids
    missing = req_ids - resume_ids
    extra = resume_ids - req_ids - pref_ids

    return json.dumps({
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "extra_skills": sorted(extra),
        "match_rate": round(len(matched) / len(req_ids) * 100, 1) if req_ids else 100.0,
    }, ensure_ascii=False, indent=2)


@mcp.tool(name="extract_skills", annotations={
    "title": "Extract Skills",
    "readOnlyHint": True,
    "idempotentHint": True,
})
def mcp_extract_skills(params: ExtractSkillsInput) -> str:
    """自由記述テキストからスキルを抽出する（共通サービス利用）"""
    from src.utils.skill_extraction_service import extract_skills_service
    result = extract_skills_service(text=params.text, use_rag=params.use_rag, top_k=params.top_k)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(name="recommendation_reason", annotations={
    "title": "Recommendation Reason",
    "readOnlyHint": True,
    "idempotentHint": True,
})
def recommendation_reason(params: RecommendationReasonInput) -> str:
    """候補者と案件の推薦理由をスキル・業界・経験の観点で分解する"""
    from src.utils.recommendation_reasoning_service import build_recommendation_reason
    result = build_recommendation_reason(resume_id=params.resume_id, job_id=params.job_id)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(name="optimize_jd", annotations={
    "title": "Optimize JD",
    "readOnlyHint": True,
    "idempotentHint": True,
})
def optimize_jd(params: JdOptimizationInput) -> str:
    """JDを自動最適化し、技能抽出と予算妥当性判断を返す"""
    from src.utils.jd_optimization_service import optimize_jd as optimize_jd_service
    result = optimize_jd_service(raw_jd=params.raw_jd, budget_range=params.budget_range)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(name="recommendation_actions", annotations={
    "title": "Recommendation Actions",
    "readOnlyHint": True,
    "idempotentHint": True,
})
def recommendation_actions(params: RecommendationActionsInput) -> str:
    """推薦順位・連絡優先度・自動コミュニケーション生成を行う"""
    from src.utils.recommendation_action_service import build_recommendation_actions
    result = build_recommendation_actions(resume_id=params.resume_id, top_n=params.top_n)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(name="resume_job_matches", annotations={
    "title": "Resume Job Matches Summary",
    "readOnlyHint": True,
    "idempotentHint": True,
})
def resume_job_matches(params: ResumeJobMatchesInput) -> str:
    """経歴書に対する全案件のマッチング結果を軽量サマリで返す（案件名・総合スコア・一致/不足スキルのみ）"""
    from src.matching.embedding_matcher import compute_hybrid_score

    resume_repo = JsonResumeRepository(config.RESUMES_FILE)
    job_repo = JsonJobRepository(config.JOBS_FILE)

    resume = resume_repo.find_by_id(params.resume_id)
    if resume is None:
        return json.dumps({"error": f"経歴書ID '{params.resume_id}' が見つかりません"}, ensure_ascii=False)

    jobs = job_repo.find_all()
    summaries = []
    for job in jobs:
        result = compute_hybrid_score(resume, job)
        summaries.append({
            "job_id": job.get("id"),
            "job_title": job.get("title", ""),
            "company": job.get("company", ""),
            "total_score": result["total_score"],
            "matched_skills": result["matched_skills"],
            "missing_required_skills": result["missing_required_skills"],
            "missing_preferred_skills": result["missing_preferred_skills"],
        })

    summaries.sort(key=lambda m: m["total_score"], reverse=True)
    if params.top_n:
        summaries = summaries[:params.top_n]

    return json.dumps({
        "resume_id": params.resume_id,
        "resume_name": resume.get("name", ""),
        "matches": summaries,
    }, ensure_ascii=False, indent=2)


@mcp.tool(name="schedule_availability", annotations={
    "title": "Schedule Availability",
    "readOnlyHint": True,
    "idempotentHint": True,
})
def schedule_availability(params: ScheduleAvailabilityInput) -> str:
    """availability モデリングと時間マッチングを行う"""
    from src.utils.schedule_management_service import model_availability
    result = model_availability(candidate_availability=params.candidate_availability, job_window=params.job_window)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(name="schedule_conflicts", annotations={
    "title": "Schedule Conflicts",
    "readOnlyHint": True,
    "idempotentHint": True,
})
def schedule_conflicts(params: ScheduleConflictInput) -> str:
    """スケジュール競合を検知する"""
    from src.utils.schedule_management_service import detect_schedule_conflicts
    result = detect_schedule_conflicts(candidate_availability=params.candidate_availability, other_events=params.other_events)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(name="market_skill_supply_demand", annotations={
    "title": "Market Skill Supply/Demand",
    "readOnlyHint": True,
    "idempotentHint": True,
})
def market_skill_supply_demand(params: MarketSkillSupplyDemandInput) -> str:
    """スキル別の需要案件数と保有経歴書数を比較する"""
    from src.utils.market_analysis_service import analyze_skill_supply_demand, default_date_range

    default_start, default_end = default_date_range()
    start_date = params.start_date or default_start
    end_date = params.end_date or default_end

    result = analyze_skill_supply_demand(start_date=start_date, end_date=end_date)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(name="market_unit_price_trend", annotations={
    "title": "Market Unit Price Trend",
    "readOnlyHint": True,
    "idempotentHint": True,
})
def market_unit_price_trend(params: MarketUnitPriceTrendInput) -> str:
    """月次の単価推移を集計する（スキル・職種で絞り込み可能）"""
    from src.utils.market_analysis_service import analyze_unit_price_trend, default_date_range

    default_start, default_end = default_date_range()
    start_date = params.start_date or default_start
    end_date = params.end_date or default_end

    result = analyze_unit_price_trend(
        start_date=start_date, end_date=end_date,
        skill_id=params.skill_id, job_type=params.job_type,
    )
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(name="market_tech_trend", annotations={
    "title": "Market Tech Trend",
    "readOnlyHint": True,
    "idempotentHint": True,
})
def market_tech_trend(params: MarketTechTrendInput) -> str:
    """月次のスキル出現頻度推移から上昇/下降トレンドを抽出する"""
    from src.utils.market_analysis_service import analyze_tech_trend, default_date_range

    default_start, default_end = default_date_range()
    start_date = params.start_date or default_start
    end_date = params.end_date or default_end

    result = analyze_tech_trend(start_date=start_date, end_date=end_date, top_n=params.top_n)
    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # stdio transport で起動（デフォルト）
    mcp.run()
