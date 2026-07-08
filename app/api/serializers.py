"""ORM -> dict 序列化(JSON 响应用)。"""
from typing import Any

from sqlalchemy import inspect as sa_inspect

from app.db.models import (
    BehaviorAnalysis,
    Book,
    Chapter,
    CharacterProfile,
    DialogueAnalysis,
    SituationCluster,
    SocialRule,
)


def book_to_dict(book: Book) -> dict[str, Any]:
    # 仅在关系已预加载时读取,避免 async 下触发惰性加载报错
    meta = None if "book_metadata" in sa_inspect(book).unloaded else book.book_metadata
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "total_chapters": book.total_chapters,
        "analyzed_chapters": book.analyzed_chapters,
        "status": book.status,
        "created_at": book.created_at.isoformat() if book.created_at else None,
        "updated_at": book.updated_at.isoformat() if book.updated_at else None,
        "protagonist": meta.protagonist if meta else None,
        "setting": meta.setting if meta else None,
    }


def chapter_to_dict(ch: Chapter, with_content: bool = False) -> dict[str, Any]:
    d = {
        "id": ch.id,
        "book_id": ch.book_id,
        "index": ch.index,
        "title": ch.title,
        "char_count": ch.char_count,
        "density_score": ch.density_score,
        "should_analyze": ch.should_analyze,
        "analysis_status": ch.analysis_status,
        "failure_reason": ch.failure_reason,
    }
    if with_content:
        d["content"] = ch.content
    return d


def behavior_to_dict(b: BehaviorAnalysis, chapter: Chapter | None = None) -> dict[str, Any]:
    d = {
        "id": b.id,
        "chapter_id": b.chapter_id,
        "scene_summary": b.scene_summary,
        "characters_involved": b.characters_involved or [],
        "social_rules": b.social_rules or [],
        "freeform_analysis": b.freeform_analysis,
        "core_lesson": b.core_lesson,
        "tags": b.tags or [],
    }
    if chapter is not None:
        d["chapter_index"] = chapter.index
        d["chapter_title"] = chapter.title
    return d


def dialogue_to_dict(dlg: DialogueAnalysis, chapter: Chapter | None = None) -> dict[str, Any]:
    d = {
        "id": dlg.id,
        "chapter_id": dlg.chapter_id,
        "speaker": dlg.speaker,
        "listener": dlg.listener,
        "speaker_role": dlg.speaker_role,
        "context": dlg.context,
        "original_text": dlg.original_text,
        "scenario": dlg.scenario,
        "subtext": dlg.subtext,
        "speech_template": dlg.speech_template,
        "speech_structure": dlg.speech_structure or [],
        "sentence_breakdown": dlg.sentence_breakdown or [],
        "techniques": dlg.techniques or [],
        "signal_strength": dlg.signal_strength,
        "applicable_scenarios": dlg.applicable_scenarios or [],
        "lesson": dlg.lesson,
    }
    if chapter is not None:
        d["chapter_index"] = chapter.index
        d["chapter_title"] = chapter.title
    return d


def character_to_dict(c: CharacterProfile, with_scenes: bool = False) -> dict[str, Any]:
    d = {
        "id": c.id,
        "book_id": c.book_id,
        "name": c.name,
        "role_type": c.role_type,
        "behavior_pattern": c.behavior_pattern,
        "appearance_count": c.appearance_count,
    }
    if with_scenes:
        d["scenes"] = c.scenes or []
    return d


def cluster_to_dict(c: SituationCluster, with_instances: bool = False) -> dict[str, Any]:
    d = {
        "id": c.id,
        "book_id": c.book_id,
        "cluster_name": c.cluster_name,
        "pattern_summary": c.pattern_summary,
        "instance_count": c.instance_count,
    }
    if with_instances:
        d["instances"] = c.instances or []
    return d


def rule_to_dict(r: SocialRule) -> dict[str, Any]:
    return {
        "id": r.id,
        "book_id": r.book_id,
        "category": r.category,
        "rule": r.rule,
        "explanation": r.explanation,
        "examples": r.examples or [],
        "occurrence": r.occurrence,
    }
