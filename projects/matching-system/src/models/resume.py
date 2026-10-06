"""経歴書（Resume）データモデル"""
import datetime
from typing import Annotated, Literal, Optional
from pydantic import BaseModel, Field, StringConstraints

# 空文字・空白のみを拒否するID型（REQ-RE3-02）
NonEmptyId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Education(BaseModel):
    """学歴"""
    school: str = Field(..., description="学校名")
    department: str = Field(default="", description="学部・学科")
    graduation_year: int = Field(..., description="卒業年")
    degree: str = Field(default="学士", description="学位（学士/修士/博士/短大/専門学校）")


class WorkHistory(BaseModel):
    """職歴"""
    company: str = Field(..., description="会社名")
    position: str = Field(..., description="職位")
    start_date: str = Field(..., description="開始年月（YYYY-MM）")
    end_date: Optional[str] = Field(default=None, description="終了年月（YYYY-MM）。現在就業中の場合はnull")
    description: str = Field(default="", description="業務内容")
    industry: str = Field(default="", description="業界")


class SkillSet(BaseModel):
    """スキルセット（旧形式: 文字列リスト）
    後方互換性のために維持。新形式は list[ResumeSkill] で表現。
    """
    languages: list[str] = Field(default_factory=list, description="プログラミング言語")
    frameworks: list[str] = Field(default_factory=list, description="フレームワーク・ライブラリ")
    tools: list[str] = Field(default_factory=list, description="ツール・インフラ")
    certifications: list[str] = Field(default_factory=list, description="資格")
    other: list[str] = Field(default_factory=list, description="その他スキル（マネジメント、語学など）")


class ResumeSkill(BaseModel):
    """属性付きスキル（REQ-01 対応）
    候補者側のスキルを skill_id/level/years で管理する。
    """
    skill_id: NonEmptyId = Field(..., description="スキルID（skill_dictionary の id と一致）")
    level: int = Field(default=1, ge=1, le=5, description="習熟度レベル (1-5)")
    years: int = Field(default=0, ge=0, le=70, description="経験年数")
    last_used_year: int = Field(default_factory=lambda: datetime.datetime.now().year, ge=1990, le=2100, description="最終使用年")
    estimated: bool = Field(default=False, description="推定値（true=移行スクリプトによる推定）")


class PendingSkill(BaseModel):
    """保留スキル（未登録スキルの一時保存）"""
    pending_id: str = Field(..., description="保留スキルID（UUID等）")
    owner_type: Literal["resume", "job"] = Field(..., description="所有者タイプ")
    owner_id: str = Field(..., description="所有者ID")
    raw_name: str = Field(..., description="入力された生のスキル名")
    usage_type: Literal["resume", "required", "preferred"] = Field(..., description="利用種別")
    level: Optional[int] = Field(default=None, ge=1, le=5, description="習熟度")
    years: Optional[int] = Field(default=None, ge=0, le=70, description="経験年数")
    last_used_year: Optional[int] = Field(default=None, ge=1990, le=2100, description="最終使用年")
    required_level: Optional[int] = Field(default=None, ge=1, le=5, description="要求レベル（案件側）")
    required_years: Optional[int] = Field(default=None, ge=0, le=70, description="要求経験年数（案件側）")
    status: Literal["pending", "registered", "ignored"] = Field(default="pending", description="状態")
    registered_skill_id: Optional[str] = Field(default=None, description="登録済みスキルID")
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat(), description="作成日時")
    resolved_at: Optional[str] = Field(default=None, description="解決日時")


class Resume(BaseModel):
    """経歴書"""
    id: NonEmptyId = Field(..., description="一意なID")
    name: NonEmptyId = Field(..., description="氏名")
    age: int = Field(..., ge=0, le=120, description="年齢")
    email: str = Field(default="", description="メールアドレス")
    phone: str = Field(default="", description="電話番号")
    location: str = Field(default="", description="現在の居住地")
    desired_locations: list[str] = Field(default_factory=list, description="希望勤務地")
    education: list[Education] = Field(default_factory=list, description="学歴")
    work_history: list[WorkHistory] = Field(default_factory=list, description="職歴")
    skills: SkillSet = Field(default_factory=SkillSet, description="スキルセット（旧形式）")
    structured_skills: list[ResumeSkill] = Field(default_factory=list, description="属性付きスキル一覧（REQ-01）")
    pending_skills: list[PendingSkill] = Field(default_factory=list, description="保留スキル一覧（FIX-02）")
    years_of_experience: int = Field(default=0, ge=0, le=70, description="実務経験年数")
    desired_unit_price_min: int = Field(default=0, ge=0, description="希望最低単価（万円/月）")
    desired_unit_price_max: int = Field(default=0, ge=0, description="希望最高単価（万円/月）")
    employment_type: str = Field(default="正社員", description="希望雇用形態")
    self_pr: str = Field(default="", description="自己PR・備考")
    registered_at: str = Field(default_factory=lambda: datetime.date.today().isoformat(), description="経歴書登録日（YYYY-MM-DD）")

    def get_all_skills(self) -> list[str]:
        """全スキルをフラットなリストで取得（マッチング用）"""
        all_skills = []
        for key in ("languages", "frameworks", "tools", "certifications", "other"):
            all_skills.extend(getattr(self.skills, key, []))
        return all_skills

    def get_skill_id_list(self) -> list[str]:
        """属性付きスキルから skill_id のみを取得"""
        return [s.skill_id for s in self.structured_skills]

    def get_latest_industry(self) -> str:
        """直近の職歴の業界を取得"""
        if self.work_history:
            return self.work_history[-1].industry
        return ""
