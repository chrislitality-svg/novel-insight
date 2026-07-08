"""分析任务编排:协程池 + 限流 + 断点续传 + 进度推送 + 完成后聚合。

并发模型:每章一个 worker,受 chapter 级 Semaphore(llm_concurrency) 约束;
LLM 客户端内部还有一层 Semaphore,双重保护账号不被打爆。
单章失败(重试耗尽/JSON 解析失败)只标记该章 failed,不中断整体流程。
"""
import asyncio
import time
from typing import Any

from app.analyzers.aggregator import run_aggregation
from app.analyzers.behavior_analyzer import analyze_chapter_behavior
from app.analyzers.dialogue_analyzer import analyze_dialogue
from app.analyzers.dialogue_extractor import extract_protagonist_dialogues
from app.config import settings
from app.db import crud
from app.db.database import SessionLocal
from app.db.models import AnalysisStatus, BookStatus
from app.llm.base import LLMClient, LLMError, extract_json
from app.llm.deepseek_client import get_llm_client
from app.llm.prompts import build_protagonist_prompt
from app.services.progress import progress_manager
from app.utils.logger import get_logger

logger = get_logger("analysis_service")

# 运行中的书籍任务:book_id -> asyncio.Task
_running: dict[int, asyncio.Task] = {}
# 每本书的运行时统计:book_id -> {start, total, current}
_run_state: dict[int, dict[str, Any]] = {}


def is_running(book_id: int) -> bool:
    task = _running.get(book_id)
    return task is not None and not task.done()


def start_analysis(book_id: int) -> str:
    """启动(或续跑)一本书的分析,返回 task_id。"""
    if is_running(book_id):
        return f"book-{book_id}"
    task = asyncio.create_task(analyze_book(book_id))
    _running[book_id] = task
    return f"book-{book_id}"


async def stop_analysis(book_id: int) -> bool:
    task = _running.get(book_id)
    if task and not task.done():
        task.cancel()
        return True
    return False


async def analyze_book(book_id: int) -> None:
    try:
        client = get_llm_client()
    except LLMError as exc:
        logger.error("启动分析失败:%s", exc)
        await _set_book_status(book_id, BookStatus.UPLOADED)
        await progress_manager.broadcast(
            book_id, {"type": "error", "message": str(exc)}
        )
        _running.pop(book_id, None)
        return

    await _set_book_status(book_id, BookStatus.ANALYZING)

    try:
        await _ensure_protagonist(client, book_id)

        async with SessionLocal() as s:
            meta = await crud.get_metadata(s, book_id)
            aliases = list(meta.protagonist_aliases) if meta else []
            pending = await crud.get_pending_chapters(s, book_id)
            chapter_ids = [c.id for c in pending]

        _run_state[book_id] = {"start": time.monotonic(), "total": len(chapter_ids), "current": ""}
        logger.info("开始分析 book=%d,待分析 %d 章,主角代称=%s", book_id, len(chapter_ids), aliases)

        sem = asyncio.Semaphore(settings.llm_concurrency)
        tasks = [
            asyncio.create_task(_worker(book_id, cid, client, aliases, sem))
            for cid in chapter_ids
        ]
        if tasks:
            await asyncio.gather(*tasks)

        await _finalize(book_id, client)

    except asyncio.CancelledError:
        logger.info("分析被中止 book=%d", book_id)
        await _reset_analyzing(book_id)
        await _set_book_status(book_id, BookStatus.UPLOADED)
        await progress_manager.broadcast(book_id, {"type": "stopped"})
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("分析异常 book=%d: %s", book_id, exc)
        await _set_book_status(book_id, BookStatus.FAILED)
        await progress_manager.broadcast(book_id, {"type": "error", "message": str(exc)})
    finally:
        _running.pop(book_id, None)
        _run_state.pop(book_id, None)


async def _worker(book_id: int, chapter_id: int, client: LLMClient, aliases: list[str], sem: asyncio.Semaphore) -> None:
    async with sem:
        try:
            await _process_chapter(book_id, chapter_id, client, aliases)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("章节处理异常 chapter=%d: %s", chapter_id, exc)
            async with SessionLocal() as s:
                await crud.set_chapter_status(s, chapter_id, AnalysisStatus.FAILED, str(exc)[:500])
                await s.commit()
        finally:
            await _broadcast_progress(book_id)


async def _process_chapter(book_id: int, chapter_id: int, client: LLMClient, aliases: list[str]) -> None:
    async with SessionLocal() as s:
        ch = await crud.get_chapter(s, chapter_id)
        if ch is None:
            return
        title, content = ch.title, ch.content
        await crud.set_chapter_status(s, chapter_id, AnalysisStatus.ANALYZING)
        await s.commit()
    if book_id in _run_state:
        _run_state[book_id]["current"] = title

    # --- 行为层(fast)---
    res = await analyze_chapter_behavior(client, title, content)
    async with SessionLocal() as s:
        if not res.ok:
            await crud.upsert_behavior(s, chapter_id, {}, res.raw or "")
            await crud.set_chapter_status(s, chapter_id, AnalysisStatus.FAILED, res.error)
            await s.commit()
            return
        await crud.upsert_behavior(s, chapter_id, res.data, res.raw)
        await s.commit()

    # --- 对话层(deep,best-effort)---
    dialogues = extract_protagonist_dialogues(content, aliases)
    if dialogues:
        async with SessionLocal() as s:
            await crud.clear_dialogues(s, chapter_id)
            await s.commit()
        for d in dialogues:
            dres = await analyze_dialogue(
                client,
                context=d["context"],
                speaker=d["speaker"],
                listener=d["listener"],
                relationship="(根据上下文情境推断)",
                original_text=d["original_text"],
            )
            if not dres.ok:
                continue
            async with SessionLocal() as s:
                await crud.add_dialogue(
                    s,
                    chapter_id,
                    speaker=d["speaker"],
                    listener=d["listener"],
                    context=d["context"],
                    original_text=d["original_text"],
                    data=dres.data,
                    raw_response=dres.raw,
                )
                await s.commit()

    async with SessionLocal() as s:
        await crud.set_chapter_status(s, chapter_id, AnalysisStatus.COMPLETED)
        await crud.refresh_book_progress(s, book_id)
        await s.commit()


async def _ensure_protagonist(client: LLMClient, book_id: int) -> None:
    """主角识别:每本书只跑一次,结果存 BookMetadata。"""
    async with SessionLocal() as s:
        meta = await crud.get_or_create_metadata(s, book_id)
        if meta.protagonist:
            return
        chapters = await crud.get_first_n_chapters(s, book_id, 3)
        sample = "\n\n".join(c.content for c in chapters)[:6000]
        await s.commit()

    if not sample:
        return
    try:
        raw = await client.analyze(build_protagonist_prompt(sample), mode="fast", response_format="text")
        data = extract_json(raw)
    except (LLMError, Exception) as exc:  # noqa: BLE001
        logger.warning("主角识别失败,继续(对话抽取将退化): %s", exc)
        return

    async with SessionLocal() as s:
        meta = await crud.get_or_create_metadata(s, book_id)
        meta.protagonist = data.get("protagonist")
        aliases = data.get("aliases") or []
        if meta.protagonist and meta.protagonist not in aliases:
            aliases = [meta.protagonist, *aliases]
        meta.protagonist_aliases = aliases
        meta.setting = data.get("setting")
        await s.commit()
    logger.info("主角识别:%s,代称 %s", data.get("protagonist"), data.get("aliases"))


_reaggregating: dict[int, asyncio.Task] = {}


def is_reaggregating(book_id: int) -> bool:
    task = _reaggregating.get(book_id)
    return task is not None and not task.done()


def start_reaggregate(book_id: int, scope: str = "rules") -> str:
    """后台触发重聚合（不重跑章节分析），返回 task_id。
    scope: "rules" 仅重跑规则手册；"all" 跑全部 4 项。
    """
    if is_reaggregating(book_id):
        return f"reagg-{book_id}"
    task = asyncio.create_task(_reaggregate(book_id, scope))
    _reaggregating[book_id] = task
    return f"reagg-{book_id}"


async def _reaggregate(book_id: int, scope: str) -> None:
    from app.analyzers.aggregator import (
        _aggregate_rules,
        _aggregate_characters,
        _aggregate_clusters,
        _aggregate_tally,
    )
    try:
        client = get_llm_client()
    except LLMError as exc:
        logger.error("重聚合启动失败 book=%d: %s", book_id, exc)
        _reaggregating.pop(book_id, None)
        return
    try:
        async with SessionLocal() as s:
            rows = await crud.list_behavior_cards(s, book_id)
            cards = [(b, c) for b, c in rows if b.core_lesson and "无显著" not in (b.core_lesson or "")]
            logger.info("重聚合开始 book=%d scope=%s,有效行为卡 %d 张", book_id, scope, len(cards))

            if scope in ("rules", "all"):
                n = await _aggregate_rules(s, book_id, client, cards)
                logger.info("重聚合 rules 完成 book=%d: %d 条", book_id, n)
            if scope == "all":
                n1 = await _aggregate_characters(s, book_id, client, cards)
                n2 = await _aggregate_clusters(s, book_id, client, cards)
                await _aggregate_tally(s, book_id, client, cards)
                logger.info("重聚合 all 完成 book=%d: 人物 %d 情境 %d", book_id, n1, n2)
    except Exception as exc:  # noqa: BLE001
        logger.warning("重聚合失败 book=%d: %s", book_id, exc)
    finally:
        _reaggregating.pop(book_id, None)


async def _finalize(book_id: int, client: LLMClient) -> None:
    await _set_book_status(book_id, BookStatus.COMPLETED)
    await progress_manager.broadcast(book_id, {"type": "aggregating", "message": "正在生成人物画像与情境聚类…"})
    try:
        async with SessionLocal() as s:
            await run_aggregation(s, book_id, client)
    except Exception as exc:  # noqa: BLE001
        logger.warning("聚合失败(不影响章节结果): %s", exc)
    async with SessionLocal() as s:
        prog = await crud.chapter_progress(s, book_id)
    await progress_manager.broadcast(
        book_id,
        {
            "type": "completed",
            "total": prog["total_analyzable"],
            "analyzed": prog["completed"],
            "failed": prog["failed"],
        },
    )
    logger.info("分析全部完成 book=%d: %s", book_id, prog)


async def _broadcast_progress(book_id: int) -> None:
    async with SessionLocal() as s:
        prog = await crud.chapter_progress(s, book_id)
    state = _run_state.get(book_id, {})
    est = _estimate_remaining(state, prog)
    await progress_manager.broadcast(
        book_id,
        {
            "type": "progress",
            "total": prog["total_analyzable"],
            "analyzed": prog["completed"],
            "failed": prog["failed"],
            "current_chapter": state.get("current", ""),
            "estimated_remaining_seconds": est,
        },
    )


def _estimate_remaining(state: dict, prog: dict) -> int | None:
    start = state.get("start")
    done = prog["completed"] + prog["failed"]
    if not start or done <= 0:
        return None
    elapsed = time.monotonic() - start
    remaining = prog["pending"]
    if remaining <= 0:
        return 0
    return int(elapsed / done * remaining)


async def _set_book_status(book_id: int, status: str) -> None:
    async with SessionLocal() as s:
        await crud.set_book_status(s, book_id, status)
        await s.commit()


async def _reset_analyzing(book_id: int) -> None:
    """把本书 analyzing 中的章节回滚为 pending(中止/异常时)。"""
    from sqlalchemy import text

    async with SessionLocal() as s:
        await s.execute(
            text(
                "UPDATE chapters SET analysis_status=:p WHERE book_id=:b AND analysis_status=:a"
            ),
            {"p": AnalysisStatus.PENDING, "b": book_id, "a": AnalysisStatus.ANALYZING},
        )
        await s.commit()
