"""案件（Job）データモデル"""
import datetime
from typing import Annotated, Optional
from pydantic import BaseModel, Field, StringConstraints
from src.models.resume import PendingSkill

# 空文字・空白のみを拒否するID型（REQ-RE3-02）
NonEmptyId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SkillSet(BaseModel):
    """スキルセット（旧形式: 文字列リスト）"""
    languages: list[str] = Field(default_factory=list, description="プログラミング言語")
    frameworks: list[str] = Field(default_factory=list, description="フレームワーク・ライブラリ")
    tools: list[str] = Field(default_factory=list, description="ツール・インフラ")
    certifications: list[str] = Field(default_factory=list, description="資格")
    other: list[str] = Field(default_factory=list, description="その他スキル")


class JobSkill(BaseModel):
    """属性付きスキル（案件側、REQ-FIX-11: required削除済み）

    必須/歓迎の判定は所属リスト（structured_required_skills /
    structured_preferred_skills）で管理する。
    """
    skill_id: NonEmptyId = Field(..., description="スキルID")
    required_level: int = Field(default=1, ge=1, le=5, description="要求レベル (1-5)")
    required_years: int = Field(default=0, ge=0, le=70, description="要求経験年数")


class Job(BaseModel):
    """案件"""
    id: NonEmptyId = Field(..., description="一意なID")
    title: NonEmptyId = Field(..., description="案件名/ポジション名")
    company: NonEmptyId = Field(..., description="企業名")
    industry: str = Field(default="", description="業界")
    job_type: str = Field(default="", description="職種")
    location: str = Field(default="", description="勤務地")
    remote_policy: str = Field(default="", description="リモートポリシー")
    required_skills: SkillSet = Field(default_factory=SkillSet, description="必須スキル（旧形式）")
    preferred_skills: SkillSet = Field(default_factory=SkillSet, description="歓迎スキル（旧形式）")
    structured_required_skills: list[JobSkill] = Field(default_factory=list, description="属性付き必須スキル一覧（REQ-01）")
    structured_preferred_skills: list[JobSkill] = Field(default_factory=list, description="属性付き歓迎スキル一覧（REQ-01）")
    pending_skills: list[PendingSkill] = Field(default_factory=list, description="保留スキル一覧（FIX-02）")
    description: str = Field(default="", description="案件概要・業務内容")
    required_experience_years: int = Field(default=0, ge=0, le=70, description="必要経験年数")
    unit_price_min: int = Field(default=0, ge=0, description="最低単価（万円/月）")
    unit_price_max: int = Field(default=0, ge=0, description="最高単価（万円/月）")
    employment_type: str = Field(default="正社員", description="雇用形態")
    duration: str = Field(default="", description="案件期間（例: 長期, 6ヶ月〜）")
    headcount: int = Field(default=1, ge=1, le=999, description="募集人数")
    project_start_date: str = Field(default="", description="プロジェクト開始日（稼働開始日、YYYY-MM-DD）")
    posted_date: str = Field(default_factory=lambda: datetime.date.today().isoformat(), description="掲載日（募集開始日、YYYY-MM-DD）")

    def get_all_required_skills(self) -> list[str]:
        """必須スキルをフラットなリストで取得"""
        all_skills = []
        for key in ("languages", "frameworks", "tools", "certifications", "other"):
            all_skills.extend(getattr(self.required_skills, key, []))
        return all_skills

    def get_all_preferred_skills(self) -> list[str]:
        """歓迎スキルをフラットなリストで取得"""
        all_skills = []
        for key in ("languages", "frameworks", "tools", "certifications", "other"):
            all_skills.extend(getattr(self.preferred_skills, key, []))
        return all_skills

    def get_required_skill_ids(self) -> list[str]:
        """属性付き必須スキルから skill_id のみを取得"""
        return [s.skill_id for s in self.structured_required_skills]

    def get_preferred_skill_ids(self) -> list[str]:
        """属性付き歓迎スキルから skill_id のみを取得"""
        return [s.skill_id for s in self.structured_preferred_skills]
