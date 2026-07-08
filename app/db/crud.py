"""增删改查。所有函数接收 AsyncSession,不自行管理事务边界(调用方决定 commit)。"""
import json
from typing import Any, Sequence

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    AnalysisStatus,
    BehaviorAnalysis,
    Book,
    BookMetadata,
    BookStatus,
    Chapter,
    CharacterProfile,
    DialogueAnalysis,
    SituationCluster,
    SocialRule,
)


# ===================== Book =====================
async def create_book(session: AsyncSession, *, title: str, author: str | None, file_path: str) -> Book:
    book = Book(title=title, author=author, file_path=file_path, status=BookStatus.UPLOADED)
    session.add(book)
    await session.flush()
    return book


async def get_book(session: AsyncSession, book_id: int) -> Book | None:
    return await session.get(Book, book_id)


async def list_books(session: AsyncSession) -> Sequence[Book]:
    result = await session.execute(
        select(Book)
        .options(selectinload(Book.book_metadata))
        .order_by(Book.created_at.desc())
    )
    return result.scalars().all()


async def delete_book(session: AsyncSession, book_id: int) -> bool:
    book = await session.get(Book, book_id)
    if not book:
        return False
    # FTS 表无外键级联,手动清理
    await session.execute(text("DELETE FROM behavior_fts WHERE book_id = :bid"), {"bid": book_id})
    await session.execute(text("DELETE FROM dialogue_fts WHERE book_id = :bid"), {"bid": book_id})
    await session.delete(book)
    return True


async def set_book_status(session: AsyncSession, book_id: int, status: str) -> None:
    await session.execute(update(Book).where(Book.id == book_id).values(status=status))


async def refresh_book_progress(session: AsyncSession, book_id: int) -> None:
    """重算 analyzed_chapters。"""
    count = await session.scalar(
        select(func.count(Chapter.id)).where(
            Chapter.book_id == book_id,
            Chapter.analysis_status == AnalysisStatus.COMPLETED,
        )
    )
    await session.execute(
        update(Book).where(Book.id == book_id).values(analyzed_chapters=count or 0)
    )


# ===================== BookMetadata =====================
async def get_or_create_metadata(session: AsyncSession, book_id: int) -> BookMetadata:
    result = await session.execute(select(BookMetadata).where(BookMetadata.book_id == book_id))
    meta = result.scalar_one_or_none()
    if meta is None:
        meta = BookMetadata(book_id=book_id, protagonist_aliases=[])
        session.add(meta)
        await session.flush()
    return meta


async def get_metadata(session: AsyncSession, book_id: int) -> BookMetadata | None:
    result = await session.execute(select(BookMetadata).where(BookMetadata.book_id == book_id))
    return result.scalar_one_or_none()


# ===================== Chapter =====================
async def bulk_create_chapters(
    session: AsyncSession, book_id: int, chapters: list[dict[str, Any]]
) -> int:
    objs = []
    for ch in chapters:
        objs.append(
            Chapter(
                book_id=book_id,
                index=ch["index"],
                title=ch["title"],
                content=ch["content"],
                char_count=ch["char_count"],
                density_score=ch.get("density_score", 0.0),
                density_meta=ch.get("density_meta"),
                should_analyze=ch.get("should_analyze", False),
                analysis_status=(
                    AnalysisStatus.PENDING if ch.get("should_analyze") else AnalysisStatus.SKIPPED
                ),
            )
        )
    session.add_all(objs)
    await session.flush()
    return len(objs)


async def get_chapter(session: AsyncSession, chapter_id: int) -> Chapter | None:
    return await session.get(Chapter, chapter_id)


async def list_chapters(session: AsyncSession, book_id: int) -> Sequence[Chapter]:
    result = await session.execute(
        select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.index)
    )
    return result.scalars().all()


async def get_pending_chapters(session: AsyncSession, book_id: int) -> Sequence[Chapter]:
    """需要分析且还未完成的章节(支持断点续传:pending + failed 都会被取出)。"""
    result = await session.execute(
        select(Chapter)
        .where(
            Chapter.book_id == book_id,
            Chapter.should_analyze.is_(True),
            Chapter.analysis_status.in_([AnalysisStatus.PENDING, AnalysisStatus.FAILED]),
        )
        .order_by(Chapter.index)
    )
    return result.scalars().all()


async def get_first_n_chapters(session: AsyncSession, book_id: int, n: int) -> Sequence[Chapter]:
    result = await session.execute(
        select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.index).limit(n)
    )
    return result.scalars().all()


async def set_chapter_status(
    session: AsyncSession, chapter_id: int, status: str, failure_reason: str | None = None
) -> None:
    await session.execute(
        update(Chapter)
        .where(Chapter.id == chapter_id)
        .values(analysis_status=status, failure_reason=failure_reason)
    )


async def chapter_progress(session: AsyncSession, book_id: int) -> dict[str, int]:
    """返回 {total_analyzable, completed, failed, pending}。"""
    rows = await session.execute(
        select(Chapter.analysis_status, func.count(Chapter.id))
        .where(Chapter.book_id == book_id, Chapter.should_analyze.is_(True))
        .group_by(Chapter.analysis_status)
    )
    counts = {status: n for status, n in rows.all()}
    total = sum(counts.values())
    return {
        "total_analyzable": total,
        "completed": counts.get(AnalysisStatus.COMPLETED, 0),
        "failed": counts.get(AnalysisStatus.FAILED, 0),
        "pending": counts.get(AnalysisStatus.PENDING, 0)
        + counts.get(AnalysisStatus.ANALYZING, 0),
    }


# ===================== BehaviorAnalysis =====================
async def upsert_behavior(
    session: AsyncSession, chapter_id: int, data: dict[str, Any], raw_response: str
) -> BehaviorAnalysis:
    # 删除旧记录(失败重跑场景)
    await session.execute(
        delete(BehaviorAnalysis).where(BehaviorAnalysis.chapter_id == chapter_id)
    )
    chapter = await session.get(Chapter, chapter_id)
    obj = BehaviorAnalysis(
        chapter_id=chapter_id,
        scene_summary=data.get("scene_summary"),
        characters_involved=data.get("characters_involved") or [],
        loyalty_signaling=data.get("loyalty_signaling"),
        timing_of_alignment=data.get("timing_of_alignment"),
        leaving_traces=data.get("leaving_traces"),
        relational_read=data.get("relational_read"),
        calibration=data.get("calibration"),
        long_term_tally=data.get("long_term_tally"),
        social_rules=data.get("social_rules") or [],
        freeform_analysis=data.get("freeform_analysis"),
        core_lesson=data.get("core_lesson"),
        tags=data.get("tags") or [],
        raw_response=raw_response,
    )
    session.add(obj)
    await session.flush()
    # 同步 FTS
    await session.execute(
        text("DELETE FROM behavior_fts WHERE behavior_id = :id"), {"id": obj.id}
    )
    await session.execute(
        text(
            """INSERT INTO behavior_fts
               (book_id, chapter_id, behavior_id, chapter_title, scene_summary, core_lesson, tags, body)
               VALUES (:book_id, :chapter_id, :behavior_id, :title, :scene, :lesson, :tags, :body)"""
        ),
        {
            "book_id": chapter.book_id if chapter else None,
            "chapter_id": chapter_id,
            "behavior_id": obj.id,
            "title": chapter.title if chapter else "",
            "scene": obj.scene_summary or "",
            "lesson": obj.core_lesson or "",
            "tags": " ".join(obj.tags or []),
            "body": _behavior_searchable_body(data),
        },
    )
    return obj


def _behavior_searchable_body(data: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "loyalty_signaling",
        "timing_of_alignment",
        "leaving_traces",
        "relational_read",
        "calibration",
        "long_term_tally",
    ):
        val = data.get(key)
        if isinstance(val, dict):
            parts.append(" ".join(str(v) for v in val.values() if v))
    for r in data.get("social_rules") or []:
        if isinstance(r, dict):
            parts.append(" ".join(str(v) for v in (r.get("rule"), r.get("why")) if v))
    parts.extend(data.get("characters_involved") or [])
    return " ".join(parts)


async def get_behavior_by_chapter(session: AsyncSession, chapter_id: int) -> BehaviorAnalysis | None:
    result = await session.execute(
        select(BehaviorAnalysis).where(BehaviorAnalysis.chapter_id == chapter_id)
    )
    return result.scalar_one_or_none()


async def list_behavior_cards(
    session: AsyncSession, book_id: int, tag: str | None = None
) -> list[tuple[BehaviorAnalysis, Chapter]]:
    stmt = (
        select(BehaviorAnalysis, Chapter)
        .join(Chapter, BehaviorAnalysis.chapter_id == Chapter.id)
        .where(Chapter.book_id == book_id)
        .order_by(Chapter.index)
    )
    result = await session.execute(stmt)
    rows = result.all()
    if tag:
        rows = [(b, c) for b, c in rows if tag in (b.tags or [])]
    return [(b, c) for b, c in rows]


# ===================== DialogueAnalysis =====================
async def add_dialogue(
    session: AsyncSession,
    chapter_id: int,
    *,
    speaker: str | None,
    listener: str | None,
    context: str | None,
    original_text: str,
    data: dict[str, Any],
    raw_response: str,
) -> DialogueAnalysis:
    chapter = await session.get(Chapter, chapter_id)
    obj = DialogueAnalysis(
        chapter_id=chapter_id,
        speaker=speaker,
        listener=listener,
        speaker_role=data.get("speaker_role"),
        context=context,
        original_text=original_text,
        scenario=data.get("scenario"),
        subtext=data.get("subtext"),
        speech_template=data.get("speech_template"),
        speech_structure=data.get("speech_structure") or [],
        sentence_breakdown=data.get("sentence_breakdown") or [],
        techniques=data.get("overall_techniques") or data.get("techniques") or [],
        signal_strength=data.get("signal_strength"),
        applicable_scenarios=data.get("applicable_scenarios") or [],
        lesson=data.get("lesson"),
        raw_response=raw_response,
    )
    session.add(obj)
    await session.flush()
    await session.execute(
        text(
            """INSERT INTO dialogue_fts
               (book_id, chapter_id, dialogue_id, chapter_title, speaker, listener, original_text, techniques, lesson)
               VALUES (:book_id, :chapter_id, :dialogue_id, :title, :speaker, :listener, :otext, :tech, :lesson)"""
        ),
        {
            "book_id": chapter.book_id if chapter else None,
            "chapter_id": chapter_id,
            "dialogue_id": obj.id,
            "title": chapter.title if chapter else "",
            "speaker": speaker or "",
            "listener": listener or "",
            "otext": original_text,
            "tech": " ".join(obj.techniques or []),
            "lesson": " ".join(x for x in (obj.lesson, obj.subtext, obj.scenario) if x),
        },
    )
    return obj


async def clear_dialogues(session: AsyncSession, chapter_id: int) -> None:
    await session.execute(
        text("DELETE FROM dialogue_fts WHERE chapter_id = :id"), {"id": chapter_id}
    )
    await session.execute(
        delete(DialogueAnalysis).where(DialogueAnalysis.chapter_id == chapter_id)
    )


async def get_dialogues_by_chapter(session: AsyncSession, chapter_id: int) -> Sequence[DialogueAnalysis]:
    result = await session.execute(
        select(DialogueAnalysis).where(DialogueAnalysis.chapter_id == chapter_id)
    )
    return result.scalars().all()


async def list_dialogue_cards(
    session: AsyncSession,
    book_id: int,
    technique: str | None = None,
    speaker: str | None = None,
    speaker_role: str | None = None,
    scenario: str | None = None,
    min_strength: int | None = None,
) -> list[tuple[DialogueAnalysis, Chapter]]:
    stmt = (
        select(DialogueAnalysis, Chapter)
        .join(Chapter, DialogueAnalysis.chapter_id == Chapter.id)
        .where(Chapter.book_id == book_id)
        .order_by(Chapter.index)
    )
    result = await session.execute(stmt)
    rows = result.all()
    out = []
    for d, c in rows:
        if technique and technique not in (d.techniques or []):
            continue
        if speaker and d.speaker != speaker:
            continue
        if speaker_role and d.speaker_role != speaker_role:
            continue
        if scenario and d.scenario != scenario:
            continue
        if min_strength and (d.signal_strength or 0) < min_strength:
            continue
        out.append((d, c))
    return out


# ===================== CharacterProfile =====================
async def replace_characters(session: AsyncSession, book_id: int, profiles: list[dict[str, Any]]) -> None:
    await session.execute(delete(CharacterProfile).where(CharacterProfile.book_id == book_id))
    for p in profiles:
        session.add(
            CharacterProfile(
                book_id=book_id,
                name=p["name"],
                role_type=p.get("role_type"),
                behavior_pattern=p.get("behavior_pattern"),
                appearance_count=p.get("appearance_count", 0),
                scenes=p.get("scenes") or [],
            )
        )
    await session.flush()


async def list_characters(session: AsyncSession, book_id: int) -> Sequence[CharacterProfile]:
    result = await session.execute(
        select(CharacterProfile)
        .where(CharacterProfile.book_id == book_id)
        .order_by(CharacterProfile.appearance_count.desc())
    )
    return result.scalars().all()


async def get_character(session: AsyncSession, character_id: int) -> CharacterProfile | None:
    return await session.get(CharacterProfile, character_id)


# ===================== SituationCluster =====================
async def replace_clusters(session: AsyncSession, book_id: int, clusters: list[dict[str, Any]]) -> None:
    await session.execute(delete(SituationCluster).where(SituationCluster.book_id == book_id))
    for c in clusters:
        session.add(
            SituationCluster(
                book_id=book_id,
                cluster_name=c["cluster_name"],
                instances=c.get("instances") or [],
                pattern_summary=c.get("pattern_summary"),
                instance_count=len(c.get("instances") or []),
            )
        )
    await session.flush()


async def list_clusters(session: AsyncSession, book_id: int) -> Sequence[SituationCluster]:
    result = await session.execute(
        select(SituationCluster)
        .where(SituationCluster.book_id == book_id)
        .order_by(SituationCluster.instance_count.desc())
    )
    return result.scalars().all()


async def get_cluster(session: AsyncSession, cluster_id: int) -> SituationCluster | None:
    return await session.get(SituationCluster, cluster_id)


# ===================== SocialRule =====================
async def replace_rules(session: AsyncSession, book_id: int, rules: list[dict[str, Any]]) -> None:
    await session.execute(delete(SocialRule).where(SocialRule.book_id == book_id))
    for r in rules:
        session.add(
            SocialRule(
                book_id=book_id,
                category=r.get("category"),
                rule=r.get("rule", ""),
                explanation=r.get("explanation"),
                examples=r.get("examples") or [],
                occurrence=r.get("occurrence", 1),
            )
        )
    await session.flush()


async def list_rules(session: AsyncSession, book_id: int) -> Sequence[SocialRule]:
    result = await session.execute(
        select(SocialRule)
        .where(SocialRule.book_id == book_id)
        .order_by(SocialRule.occurrence.desc(), SocialRule.id)
    )
    return result.scalars().all()


# ===================== 全文检索 (FTS5) =====================
async def search_behavior(session: AsyncSession, query: str, book_id: int | None = None) -> list[dict[str, Any]]:
    sql = (
        "SELECT book_id, chapter_id, behavior_id, chapter_title, scene_summary, core_lesson, tags "
        "FROM behavior_fts WHERE behavior_fts MATCH :q"
    )
    params: dict[str, Any] = {"q": _fts_query(query)}
    if book_id is not None:
        sql += " AND book_id = :bid"
        params["bid"] = book_id
    sql += " LIMIT 100"
    result = await session.execute(text(sql), params)
    return [dict(r._mapping) for r in result]


async def search_dialogue(session: AsyncSession, query: str, book_id: int | None = None) -> list[dict[str, Any]]:
    sql = (
        "SELECT book_id, chapter_id, dialogue_id, chapter_title, speaker, listener, original_text, techniques, lesson "
        "FROM dialogue_fts WHERE dialogue_fts MATCH :q"
    )
    params: dict[str, Any] = {"q": _fts_query(query)}
    if book_id is not None:
        sql += " AND book_id = :bid"
        params["bid"] = book_id
    sql += " LIMIT 100"
    result = await session.execute(text(sql), params)
    return [dict(r._mapping) for r in result]


def _fts_query(query: str) -> str:
    """中文无空格分词,FTS5 默认按 unicode61。用 jieba 切词后以 OR 连接,提升中文召回。
    同时追加原始 query 的每个字为前缀匹配,提高短查询覆盖率。"""
    import jieba

    tokens = [t.strip() for t in jieba.lcut(query) if t.strip()]
    if not tokens:
        return f'"{query}"'
    # 原词 + 每个 token 的前缀匹配(带 *),提升短查询召回
    parts = [f'"{t}"' for t in tokens] + [f'"{t}"*' for t in tokens if len(t) >= 2]
    return " OR ".join(parts)
