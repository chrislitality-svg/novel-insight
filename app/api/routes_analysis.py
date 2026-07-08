"""分析控制:启动 / 进度 / 中止 / 续传。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.database import get_session
from app.services import analysis_service
from app.services.analysis_service import _estimate_remaining, _run_state

router = APIRouter(prefix="/api/books", tags=["analysis"])


@router.post("/{book_id}/analyze")
async def start_analyze(book_id: int, session: AsyncSession = Depends(get_session)):
    book = await crud.get_book(session, book_id)
    if not book:
        raise HTTPException(404, "书籍不存在")
    if analysis_service.is_running(book_id):
        return {"task_id": f"book-{book_id}", "already_running": True}
    task_id = analysis_service.start_analysis(book_id)
    return {"task_id": task_id, "already_running": False}


@router.post("/{book_id}/resume")
async def resume_analyze(book_id: int, session: AsyncSession = Depends(get_session)):
    book = await crud.get_book(session, book_id)
    if not book:
        raise HTTPException(404, "书籍不存在")
    if analysis_service.is_running(book_id):
        return {"task_id": f"book-{book_id}", "already_running": True}
    task_id = analysis_service.start_analysis(book_id)
    return {"task_id": task_id, "resumed": True}


@router.post("/{book_id}/stop")
async def stop_analyze(book_id: int):
    stopped = await analysis_service.stop_analysis(book_id)
    return {"stopped": stopped}


@router.post("/{book_id}/reaggregate")
async def reaggregate(book_id: int, scope: str = "rules", session: AsyncSession = Depends(get_session)):
    """重新触发聚合（不重跑章节分析）。
    scope=rules 仅重跑规则手册（最常用）；scope=all 跑全部 4 项。
    """
    if scope not in ("rules", "all"):
        raise HTTPException(400, "scope 只能是 rules 或 all")
    book = await crud.get_book(session, book_id)
    if not book:
        raise HTTPException(404, "书籍不存在")
    if analysis_service.is_reaggregating(book_id):
        return {"task_id": f"reagg-{book_id}", "already_running": True}
    task_id = analysis_service.start_reaggregate(book_id, scope)
    return {"task_id": task_id, "scope": scope, "started": True}


@router.get("/{book_id}/progress")
async def progress(book_id: int, session: AsyncSession = Depends(get_session)):
    book = await crud.get_book(session, book_id)
    if not book:
        raise HTTPException(404, "书籍不存在")
    prog = await crud.chapter_progress(session, book_id)
    state = _run_state.get(book_id, {})
    return {
        "status": book.status,
        "running": analysis_service.is_running(book_id),
        "total": prog["total_analyzable"],
        "analyzed": prog["completed"],
        "failed": prog["failed"],
        "pending": prog["pending"],
        "current_chapter": state.get("current", ""),
        "estimated_remaining_seconds": _estimate_remaining(state, prog),
    }
