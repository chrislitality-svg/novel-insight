"""章节切分。优先按"第X章/回"等正则;若整本切不出,则按字数兜底。"""
import re

from app.utils.logger import get_logger

logger = get_logger("chapter_splitter")

# 优先级从高到低
CHAPTER_PATTERNS = [
    r"^第[零一二三四五六七八九十百千万\d]+章[\s ]*.{0,40}$",
    r"^第[零一二三四五六七八九十百千万\d]+回[\s ]*.{0,40}$",
    r"^Chapter\s*\d+.{0,40}$",
    r"^\d{1,4}[\.、][\s ]*.{0,40}$",
]

MIN_CHAPTER_CHARS = 100  # 少于此字数的章节丢弃
FALLBACK_CHUNK_CHARS = 3000  # 兜底:每段字数


def split_chapters(text: str) -> list[dict]:
    """返回 [{index, title, content, char_count}]。"""
    lines = text.split("\n")
    pattern = _detect_pattern(lines)

    if pattern is None:
        logger.warning("未匹配到任何章节标记,改用按 %d 字兜底切分", FALLBACK_CHUNK_CHARS)
        chapters = _split_by_length(text)
    else:
        chapters = _split_by_pattern(lines, pattern)

    # 过滤短章节 + 重新编号
    result: list[dict] = []
    for ch in chapters:
        content = ch["content"].strip()
        if len(content) < MIN_CHAPTER_CHARS:
            continue
        result.append(
            {
                "index": len(result) + 1,
                "title": ch["title"].strip() or f"片段 {len(result) + 1}",
                "content": content,
                "char_count": len(content),
            }
        )
    logger.info("切分完成:共 %d 章(过滤短章节后)", len(result))
    return result


def _detect_pattern(lines: list[str]) -> re.Pattern | None:
    """选命中行数最多的那条正则;命中 < 2 视为未命中。"""
    best: tuple[int, re.Pattern] | None = None
    for pat_str in CHAPTER_PATTERNS:
        pat = re.compile(pat_str)
        hits = sum(1 for ln in lines if pat.match(ln.strip()))
        if hits >= 2 and (best is None or hits > best[0]):
            best = (hits, pat)
    if best:
        logger.info("章节正则命中 %d 处: %s", best[0], best[1].pattern)
        return best[1]
    return None


def _split_by_pattern(lines: list[str], pattern: re.Pattern) -> list[dict]:
    chapters: list[dict] = []
    current_title: str | None = None
    buffer: list[str] = []

    def flush():
        if current_title is not None:
            chapters.append({"title": current_title, "content": "\n".join(buffer)})

    for ln in lines:
        stripped = ln.strip()
        if pattern.match(stripped):
            flush()
            current_title = stripped
            buffer = []
        else:
            buffer.append(ln)
    flush()

    # 若第一处章节标记之前还有正文(楔子/序),保留为一章
    return chapters


def _split_by_length(text: str) -> list[dict]:
    """按段落聚合到约 FALLBACK_CHUNK_CHARS 字一段。"""
    paragraphs = [p for p in text.split("\n") if p.strip()]
    chapters: list[dict] = []
    buffer: list[str] = []
    size = 0
    idx = 1
    for para in paragraphs:
        buffer.append(para)
        size += len(para)
        if size >= FALLBACK_CHUNK_CHARS:
            chapters.append({"title": f"片段 {idx}", "content": "\n".join(buffer)})
            idx += 1
            buffer = []
            size = 0
    if buffer:
        chapters.append({"title": f"片段 {idx}", "content": "\n".join(buffer)})
    return chapters
