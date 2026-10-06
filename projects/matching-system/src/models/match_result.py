"""マッチング結果データモデル

REQ-06: 10軸ブレークダウン + mode/degraded/rag_sources に対応
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class RagCorrection(BaseModel):
    """RAGスコア補正情報"""
    source_id: str = ""
    before_score: float = 0.0
    after_score: float = 0.0
    reason: str = ""


class MatchBreakdown(BaseModel):
    """マッチング内訳スコア（旧5軸）- 後方互換性のため維持"""
    skill_match: float = Field(default=0.0, description="スキル一致スコア (0-1)")
    experience_match: float = Field(default=0.0, description="経験年数一致スコア (0-1)")
    location_match: float = Field(default=0.0, description="勤務地一致スコア (0-1)")
    industry_match: float = Field(default=0.0, description="業界一致スコア (0-1)")
    unit_price_match: float = Field(default=0.0, description="単価一致スコア (0-1)")


class HybridBreakdown(BaseModel):
    """10軸統合スコア内訳（REQ-FIX-02 対応）"""
    required_skill_score: float = Field(default=0.0, description="必須スキル一致スコア (0-1)")
    preferred_skill_score: float = Field(default=0.0, description="歓迎スキル一致スコア (0-1)")
    skill_depth_score: float = Field(default=0.0, description="スキル深度スコア (0-1)")
    skill_hierarchy_score: float = Field(default=0.0, description="スキル階層スコア (0-1)")
    experience_score: float = Field(default=0.0, description="総経験年数スコア (0-1)")
    location_score: float = Field(default=0.0, description="勤務地一致スコア (0-1)")
    context_score: float = Field(default=0.0, description="業界・プロジェクト文脈スコア (0-1)")
    role_score: float = Field(default=0.0, description="ロール一致スコア (0-1)")
    unit_price_score: float = Field(default=0.0, description="単価一致スコア (0-1)")
    embedding_score: float = Field(default=0.0, description="意味類似度スコア (0-1)")


class ScheduleMatch(BaseModel):
    """スケジュール適合情報（候補者の稼働可能日と案件開始日の比較）"""
    status: str = Field(default="unknown", description="適合状況: match | conflict | unknown")
    score: float = Field(default=0.0, description="スケジュール適合度スコア (0-1)")
    candidate_available_from: str = Field(default="", description="候補者の稼働可能日")
    project_start_date: str = Field(default="", description="案件のプロジェクト開始日")
    message: str = Field(default="", description="判定メッセージ")


class MatchItem(BaseModel):
    """個別マッチ結果

    REQ-06: mode/degraded/hybrid_breakdown/rag_sources を追加。
    既存フィールドは後方互換性のため維持。
    """
    target_id: str = Field(..., description="マッチ先のID")
    target_name: str = Field(default="", description="マッチ先の名称（氏名または案件名）")
    target_company: str = Field(default="", description="所属会社名（案件の場合は企業名）")
    total_score: float = Field(default=0.0, description="総合スコア (0-1)")
    breakdown: MatchBreakdown = Field(default_factory=MatchBreakdown, description="内訳スコア（旧形式）")
    mode: str = Field(default="keyword", description="マッチング方式: keyword | hybrid")
    weights: dict[str, float] = Field(default_factory=dict, description="使用した重み（軸名→値）")
    degraded: bool = Field(default=False, description="Embedding利用不可時のdegraded mode")
    hybrid_breakdown: Optional[HybridBreakdown] = Field(default=None, description="10軸統合スコア内訳")
    matched_skills: list[str] = Field(default_factory=list, description="一致したスキル")
    missing_required_skills: list[str] = Field(default_factory=list, description="不足している必須スキル")
    missing_preferred_skills: list[str] = Field(default_factory=list, description="不足している歓迎スキル")
    rag_sources: list[str] = Field(default_factory=list, description="参照したRAGナレッジID一覧")
    rag_corrections: list[RagCorrection] = Field(default_factory=list, description="RAGスコア補正情報一覧")
    schedule: Optional[ScheduleMatch] = Field(default=None, description="スケジュール適合情報（案件開始日 x 候補者稼働可能日）")
    explanation: str = Field(default="", description="マッチング説明文")


class MatchResult(BaseModel):
    """マッチング結果（複数件）"""
    source_id: str = Field(..., description="マッチ元のID")
    source_type: str = Field(..., description="マッチ元の種類 (resume/job)")
    matches: list[MatchItem] = Field(default_factory=list, description="マッチ結果一覧（スコア降順）")
    generated_at: str = Field(default="", description="生成日時（ISO 8601）")


class SemanticMatchRequest(BaseModel):
    """AI意味的マッチングリクエスト"""
    resume_id: str = Field(..., description="経歴書ID")
    job_id: str = Field(..., description="案件ID")


class SemanticMatchResponse(BaseModel):
    """AI意味的マッチングレスポンス"""
    score: float = Field(default=0.0, description="AI評価スコア (0-100)")
    strengths: list[str] = Field(default_factory=list, description="マッチの強み")
    gaps: list[str] = Field(default_factory=list, description="ギャップ・懸念点")
    explanation: str = Field(default="", description="日本語での総合説明")
    error: str = Field(default="", description="エラーメッセージ（エラー時のみ）")
