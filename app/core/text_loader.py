"""txt / epub 文本加载。统一返回纯文本字符串。"""
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger("text_loader")


def load_text(file_path: str | Path) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return _load_txt(path)
    if suffix == ".epub":
        return _load_epub(path)
    raise ValueError(f"不支持的文件类型: {suffix}(仅支持 .txt / .epub)")


def _load_txt(path: Path) -> str:
    """尝试多种编码读取 txt(中文常见 utf-8 / gbk / gb18030)。"""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5"):
        try:
            text = raw.decode(enc)
            logger.info("以 %s 解码 txt: %s", enc, path.name)
            return _normalize(text)
        except UnicodeDecodeError:
            continue
    # 兜底:忽略错误字符
    logger.warning("所有编码尝试失败,使用 utf-8 忽略错误模式: %s", path.name)
    return _normalize(raw.decode("utf-8", errors="ignore"))


def _load_epub(path: Path) -> str:
    from bs4 import BeautifulSoup
    from ebooklib import ITEM_DOCUMENT, epub

    book = epub.read_epub(str(path))
    parts: list[str] = []
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "lxml")
        # 用换行分隔块级标签,保留章节标题的行结构
        text = soup.get_text(separator="\n")
        parts.append(text)
    logger.info("epub 解析完成: %s(%d 个文档块)", path.name, len(parts))
    return _normalize("\n\n".join(parts))


def _normalize(text: str) -> str:
    # 统一换行,去除多余空行,去掉零宽字符
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("　", " ").replace("﻿", "")
    return text


def extract_title_author(file_path: str | Path, fallback_title: str) -> tuple[str, str | None]:
    """尽量从 epub 元数据取书名/作者;txt 用文件名兜底。"""
    path = Path(file_path)
    if path.suffix.lower() == ".epub":
        try:
            from ebooklib import epub

            book = epub.read_epub(str(path))
            titles = book.get_metadata("DC", "title")
            authors = book.get_metadata("DC", "creator")
            title = titles[0][0] if titles else fallback_title
            author = authors[0][0] if authors else None
            return title, author
        except Exception as exc:  # noqa: BLE001
            logger.warning("读取 epub 元数据失败: %s", exc)
    return fallback_title, None
