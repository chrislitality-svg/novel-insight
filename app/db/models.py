"""SQLAlchemy 2.0 async ORM 模型。时间字段统一用 UTC datetime。"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ----- 状态常量 -----
class BookStatus:
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisStatus:
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str] = mapped_column(String(512))
    total_chapters: Mapped[int] = mapped_column(Integer, default=0)
    analyzed_chapters: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default=BookStatus.UPLOADED)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    book_metadata: Mapped["BookMetadata"] = relationship(
        back_populates="book", cascade="all, delete-orphan", uselist=False
    )
    characters: Mapped[list["CharacterProfile"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    clusters: Mapped[list["SituationCluster"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    rules: Mapped[list["SocialRule"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )


class BookMetadata(Base):
    """每本书的元信息:主角识别结果等(由 LLM 在首章识别一次后复用)。"""

    __tablename__ = "book_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), unique=True)
    protagonist: Mapped[str | None] = mapped_column(String(255), nullable=True)
    protagonist_aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    setting: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 题材判断:都市/职场/玄幻...
    tally_timeline: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # 长期账时间线聚合结果
    aggregation_status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    book: Mapped["Book"] = relationship(back_populates="book_metadata")


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    index: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    density_score: Mapped[float] = mapped_column(Float, default=0.0)
    density_meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    should_analyze: Mapped[bool] = mapped_column(Boolean, default=False)
    analysis_status: Mapped[str] = mapped_column(String(32), default=AnalysisStatus.PENDING)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    book: Mapped["Book"] = relationship(back_populates="chapters")
    behavior: Mapped["BehaviorAnalysis"] = relationship(
        back_populates="chapter", cascade="all, delete-orphan", uselist=False
    )
    dialogues: Mapped[list["DialogueAnalysis"]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan"
    )


class BehaviorAnalysis(Base):
    """行为层分析结果(6 维度)。"""

    __tablename__ = "behavior_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    scene_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    characters_involved: Mapped[list[str]] = mapped_column(JSON, default=list)

    loyalty_signaling: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timing_of_alignment: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    leaving_traces: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    relational_read: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    calibration: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    long_term_tally: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # 本章体现的"没人教就不懂"的社会规则/潜规则/常识:[{rule, why, evidence}]
    social_rules: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    # 自由文本分析:自然语言描述这一章发生了什么、主角怎么做的、背后的盘算（替代僵化6维）
    freeform_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)

    core_lesson: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    chapter: Mapped["Chapter"] = relationship(back_populates="behavior")


class DialogueAnalysis(Base):
    """对话层精读。"""

    __tablename__ = "dialogue_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    speaker: Mapped[str | None] = mapped_column(String(255), nullable=True)
    listener: Mapped[str | None] = mapped_column(String(255), nullable=True)
    speaker_role: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 主角/领导/朋友/敌人/下属/同事/路人/家人
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_text: Mapped[str] = mapped_column(Text)

    scenario: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 酒桌应酬/站队表态/求人办事/敲打/拒绝/汇报...
    subtext: Mapped[str | None] = mapped_column(Text, nullable=True)  # 整段潜台词(主角真正想达成的)
    speech_template: Mapped[str | None] = mapped_column(Text, nullable=True)  # 话术公式:剥离具体人物事件的表达框架
    speech_structure: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)  # 话术结构:先说什么→再说什么 [{step, content, purpose}]
    sentence_breakdown: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    techniques: Mapped[list[str]] = mapped_column(JSON, default=list)
    signal_strength: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applicable_scenarios: Mapped[list[str]] = mapped_column(JSON, default=list)
    lesson: Mapped[str | None] = mapped_column(Text, nullable=True)

    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    chapter: Mapped["Chapter"] = relationship(back_populates="dialogues")


class CharacterProfile(Base):
    """跨章节聚合:人物画像。"""

    __tablename__ = "character_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    role_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 主角/重要配角/路人
    behavior_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    appearance_count: Mapped[int] = mapped_column(Integer, default=0)
    scenes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)  # 出场场景索引
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    book: Mapped["Book"] = relationship(back_populates="characters")


class SituationCluster(Base):
    """跨章节聚合:情境聚类。"""

    __tablename__ = "situation_clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    cluster_name: Mapped[str] = mapped_column(String(255))
    instances: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    pattern_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    instance_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    book: Mapped["Book"] = relationship(back_populates="clusters")


class SocialRule(Base):
    """社会规则/潜规则手册:跨章节聚合提炼的"没人教就不懂"的常识。"""

    __tablename__ = "social_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 官场/酒桌/人情往来/职场/婚恋家庭...
    rule: Mapped[str] = mapped_column(Text)  # 一句话规则
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)  # 为什么/怎么用/不懂会怎样
    examples: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)  # [{chapter_index, evidence}]
    occurrence: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    book: Mapped["Book"] = relationship(back_populates="rules")
