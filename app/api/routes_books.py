"""书籍上传 / 列表 / 详情 / 删除。"""
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import BOOKS_DIR
from app.db import crud
from app.db.database import get_session
from app.api.serializers import book_to_dict, chapter_to_dict
from app.services.book_service import (
    density_histogram,
    process_book_file,
    process_book_folder,
)
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/books", tags=["books"])
logger = get_logger("routes_books")

_ALLOWED = {".txt", ".epub"}


def _safe_filename(name: str) -> str:
    name = Path(name).name
    name = re.sub(r"[^\w一-龥.\- ]", "_", name)
    return name or "book.txt"


@router.post("/upload")
async def upload_book(file: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED:
        raise HTTPException(400, f"仅支持 {', '.join(_ALLOWED)},收到 {suffix or '未知类型'}")

    safe = _safe_filename(file.filename or "book.txt")
    dest = BOOKS_DIR / safe
    # 避免覆盖同名文件
    counter = 1
    while dest.exists():
        dest = BOOKS_DIR / f"{Path(safe).stem}_{counter}{suffix}"
        counter += 1

    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    logger.info("已保存上传文件: %s", dest)

    try:
        book = await process_book_file(session, str(dest), safe)
    except Exception as exc:  # noqa: BLE001
        logger.exception("切分失败")
        raise HTTPException(500, f"切分失败: {exc}") from exc

    chapters = await crud.list_chapters(session, book.id)
    scores = [c.density_score for c in chapters]
    avg_chars = round(sum(c.char_count for c in chapters) / len(chapters)) if chapters else 0
    return {
        **book_to_dict(book),
        "analyzable_chapters": sum(1 for c in chapters if c.should_analyze),
        "avg_char_count": avg_chars,
        "density_histogram": density_histogram(scores),
    }


class FolderImportRequest(BaseModel):
    folder_path: str
    title: str | None = None


@router.post("/import-folder")
async def import_folder(req: FolderImportRequest, session: AsyncSession = Depends(get_session)):
    """文件夹导入:每个 .txt 文件按文件名顺序作为一章(适合已按章切好的书)。"""
    try:
        book = await process_book_folder(session, req.folder_path, req.title)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("文件夹导入失败")
        raise HTTPException(500, f"导入失败: {exc}") from exc

    chapters = await crud.list_chapters(session, book.id)
    scores = [c.density_score for c in chapters]
    avg_chars = round(sum(c.char_count for c in chapters) / len(chapters)) if chapters else 0
    return {
        **book_to_dict(book),
        "analyzable_chapters": sum(1 for c in chapters if c.should_analyze),
        "avg_char_count": avg_chars,
        "density_histogram": density_histogram(scores),
    }


@router.get("")
async def list_books(session: AsyncSession = Depends(get_session)):
    books = await crud.list_books(session)
    return [book_to_dict(b) for b in books]


@router.get("/{book_id}")
async def get_book(book_id: int, session: AsyncSession = Depends(get_session)):
    book = await crud.get_book(session, book_id)
    if not book:
        raise HTTPException(404, "书籍不存在")
    chapters = await crud.list_chapters(session, book_id)
    meta = await crud.get_metadata(session, book_id)
    scores = [c.density_score for c in chapters]
    avg_chars = round(sum(c.char_count for c in chapters) / len(chapters)) if chapters else 0
    return {
        **book_to_dict(book),
        "protagonist": meta.protagonist if meta else None,
        "protagonist_aliases": meta.protagonist_aliases if meta else [],
        "setting": meta.setting if meta else None,
        "analyzable_chapters": sum(1 for c in chapters if c.should_analyze),
        "avg_char_count": avg_chars,
        "density_histogram": density_histogram(scores),
    }


@router.delete("/{book_id}")
async def delete_book(book_id: int, session: AsyncSession = Depends(get_session)):
    book = await crud.get_book(session, book_id)
    if not book:
        raise HTTPException(404, "书籍不存在")
    # 删除原文件(尽力而为)
    try:
        p = Path(book.file_path)
        if p.exists() and p.is_relative_to(BOOKS_DIR):
            p.unlink()
    except Exception:  # noqa: BLE001
        pass
    await crud.delete_book(session, book_id)
    await session.commit()
    return {"ok": True}
