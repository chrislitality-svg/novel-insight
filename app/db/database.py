"""SQLAlchemy async engine / session / 初始化。"""
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.models import Base
from app.utils.logger import get_logger

logger = get_logger("db")

engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入用的 session。"""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """建表 + 建立 FTS5 全文检索虚拟表与触发器。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # FTS5:对行为分析的可检索文本建索引
        await conn.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS behavior_fts USING fts5(
                    book_id UNINDEXED,
                    chapter_id UNINDEXED,
                    behavior_id UNINDEXED,
                    chapter_title,
                    scene_summary,
                    core_lesson,
                    tags,
                    body
                );
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS dialogue_fts USING fts5(
                    book_id UNINDEXED,
                    chapter_id UNINDEXED,
                    dialogue_id UNINDEXED,
                    chapter_title,
                    speaker,
                    listener,
                    original_text,
                    techniques,
                    lesson
                );
                """
            )
        )
        # Migration: add speaker_role column if it doesn't exist (SQLAlchemy create_all won't add to existing tables)
        try:
            await conn.execute(text("ALTER TABLE dialogue_analyses ADD COLUMN speaker_role VARCHAR(32)"))
        except Exception:
            pass  # column already exists
        # Migration: add speech_template column
        try:
            await conn.execute(text("ALTER TABLE dialogue_analyses ADD COLUMN speech_template TEXT"))
        except Exception:
            pass
        try:
            await conn.execute(text("ALTER TABLE behavior_analyses ADD COLUMN freeform_analysis TEXT"))
        except Exception:
            pass
    logger.info("数据库初始化完成(含 FTS5)")


async def reset_in_progress_chapters() -> int:
    """启动时把所有 analyzing 状态的章节回滚到 pending,支持断点续传。返回回滚数量。"""
    from app.db.models import AnalysisStatus, Book, BookStatus, Chapter

    async with SessionLocal() as session:
        result = await session.execute(
            text(
                "UPDATE chapters SET analysis_status = :pending WHERE analysis_status = :analyzing"
            ),
            {"pending": AnalysisStatus.PENDING, "analyzing": AnalysisStatus.ANALYZING},
        )
        # analyzing 状态的书回滚为 uploaded(等待用户再次 resume)
        await session.execute(
            text("UPDATE books SET status = :uploaded WHERE status = :analyzing"),
            {"uploaded": BookStatus.UPLOADED, "analyzing": BookStatus.ANALYZING},
        )
        await session.commit()
        count = result.rowcount or 0
    if count:
        logger.info("断点续传:回滚 %d 个 analyzing 章节为 pending", count)
    return count
