"""书籍处理流程编排:加载 → 切分 → 密度评分 → 入库。"""
import re
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.chapter_splitter import MIN_CHAPTER_CHARS, split_chapters
from app.core.density_filter import calculate_density_score
from app.core.text_loader import extract_title_author, load_text
from app.db import crud
from app.db.models import Book
from app.utils.logger import get_logger

logger = get_logger("book_service")


async def process_book_file(session: AsyncSession, file_path: str, original_filename: str) -> Book:
    """处理一个已落盘的书籍文件,返回入库后的 Book。"""
    stem = Path(original_filename).stem
    title, author = extract_title_author(file_path, fallback_title=stem)

    book = await crud.create_book(session, title=title, author=author, file_path=file_path)

    text = load_text(file_path)
    chapters = split_chapters(text)

    threshold = settings.density_threshold
    enriched = []
    for ch in chapters:
        d = calculate_density_score(ch["content"], threshold)
        enriched.append(
            {
                **ch,
                "density_score": d["score"],
                "density_meta": d["metadata"],
                "should_analyze": d["should_analyze"],
            }
        )

    await crud.bulk_create_chapters(session, book.id, enriched)
    book.total_chapters = len(enriched)
    await session.commit()
    await session.refresh(book)

    analyzable = sum(1 for e in enriched if e["should_analyze"])
    logger.info(
        "书籍入库:《%s》 共 %d 章,其中 %d 章待分析(阈值 %.0f)",
        title, len(enriched), analyzable, threshold,
    )
    return book


def _natural_key(name: str):
    """自然排序:让 '第2章' 排在 '第10章' 前面。"""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def _derive_chapter(filename_stem: str, text: str) -> tuple[str, str]:
    """从单个章节文件推断 (标题, 正文)。首行像标题(<=40字)就用首行,否则用文件名。"""
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if lines and len(lines[0].strip()) <= 40:
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip() or text.strip()
        return title, body
    title = re.sub(r"^[\d\s_\-.、]+", "", filename_stem).strip() or filename_stem
    return title, text.strip()


async def process_book_folder(
    session: AsyncSession, folder_path: str, title: str | None = None
) -> Book:
    """文件夹导入:每个 .txt 文件按文件名自然排序后,各自作为一章(适合已按章切好的书)。"""
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"文件夹不存在或不是目录: {folder_path}")

    files = sorted(folder.glob("*.txt"), key=lambda p: _natural_key(p.name))
    if not files:
        raise ValueError(f"文件夹内没有 .txt 文件: {folder_path}")

    book_title = title or folder.name
    book = await crud.create_book(session, title=book_title, author=None, file_path=str(folder))

    threshold = settings.density_threshold
    enriched = []
    for f in files:
        try:
            text = load_text(f)
        except Exception as exc:  # noqa: BLE001
            logger.warning("跳过无法读取的文件 %s: %s", f.name, exc)
            continue
        ch_title, content = _derive_chapter(f.stem, text)
        if len(content) < MIN_CHAPTER_CHARS:
            continue
        d = calculate_density_score(content, threshold)
        enriched.append(
            {
                "index": len(enriched) + 1,
                "title": ch_title or f.stem,
                "content": content,
                "char_count": len(content),
                "density_score": d["score"],
                "density_meta": d["metadata"],
                "should_analyze": d["should_analyze"],
            }
        )

    if not enriched:
        raise ValueError("文件夹内所有文件都太短或无法读取,未能导入任何章节")

    await crud.bulk_create_chapters(session, book.id, enriched)
    book.total_chapters = len(enriched)
    await session.commit()
    await session.refresh(book)

    analyzable = sum(1 for e in enriched if e["should_analyze"])
    logger.info(
        "文件夹导入:《%s》 %d 个文件 → %d 章,其中 %d 章待分析",
        book_title, len(files), len(enriched), analyzable,
    )
    return book


def density_histogram(scores: list[float], bin_size: int = 10) -> dict[str, int]:
    """生成密度分布直方图,供前端展示。"""
    hist: dict[str, int] = {}
    for s in scores:
        low = min(int(s // bin_size) * bin_size, 100 - bin_size)
        key = f"{low}-{low + bin_size}"
        hist[key] = hist.get(key, 0) + 1
    return dict(sorted(hist.items(), key=lambda kv: int(kv[0].split("-")[0])))
