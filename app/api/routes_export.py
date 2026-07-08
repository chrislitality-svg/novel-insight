"""Markdown 导出:整本(zip)/ 按人物 / 按标签。"""
import io
import zipfile
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.db.database import get_session

router = APIRouter(prefix="/api/books", tags=["export"])


def _behavior_md(b, ch) -> str:
    lines = [f"### 第{ch.index}章 {ch.title}", ""]
    if b.scene_summary:
        lines.append(f"**场景**:{b.scene_summary}")
    if b.characters_involved:
        lines.append(f"**人物**:{'、'.join(b.characters_involved)}")
    lines.append("")
    dims = [
        ("表态信号", b.loyalty_signaling),
        ("站队时机", b.timing_of_alignment),
        ("留痕做事", b.leaving_traces),
        ("关系定位", b.relational_read),
        ("进退分寸", b.calibration),
        ("长期账", b.long_term_tally),
    ]
    for name, val in dims:
        if isinstance(val, dict) and val:
            desc = val.get("description") or val.get("method") or val.get("type") or ""
            extra = " ".join(
                f"_{k}_:{v}" for k, v in val.items() if k not in ("description",) and v
            )
            lines.append(f"- **{name}**:{desc} {extra}".rstrip())
    if b.core_lesson:
        lines.append("")
        lines.append(f"> 💡 {b.core_lesson}")
    if b.tags:
        lines.append("")
        lines.append("`" + "` `".join(b.tags) + "`")
    lines.append("\n---\n")
    return "\n".join(lines)


def _dialogue_md(d, ch) -> str:
    lines = [f"### 第{ch.index}章 {ch.title}", ""]
    scen = f"【{d.scenario}】" if d.scenario else ""
    lines.append(f"{scen}**{d.speaker or '主角'}** → {d.listener or '(未知)'}　表态强度 {d.signal_strength or '-'}/5")
    if d.context:
        lines.append(f"\n> 情境:{d.context}")
    lines.append(f"\n原文:「{d.original_text}」\n")
    if d.subtext:
        lines.append(f"**潜台词**:{d.subtext}\n")
    if d.speech_structure:
        lines.append("**话术结构**:")
        for st in d.speech_structure:
            lines.append(f"  {st.get('step', '')}. {st.get('content', '')} —— {st.get('purpose', '')}")
        lines.append("")
    for s in d.sentence_breakdown or []:
        lines.append(f"- 「{s.get('sentence','')}」")
        if s.get("real_intent"):
            lines.append(f"  - 意图:{s['real_intent']}")
        if s.get("techniques"):
            lines.append(f"  - 技巧:{'、'.join(s['techniques'])}")
    if d.techniques:
        lines.append("\n技巧:`" + "` `".join(d.techniques) + "`")
    if d.applicable_scenarios:
        lines.append(f"\n适用:{'、'.join(d.applicable_scenarios)}")
    if d.lesson:
        lines.append(f"\n> 💡 {d.lesson}")
    lines.append("\n---\n")
    return "\n".join(lines)


@router.get("/{book_id}/export/markdown")
async def export_markdown(book_id: int, session: AsyncSession = Depends(get_session)):
    book = await crud.get_book(session, book_id)
    if not book:
        raise HTTPException(404, "书籍不存在")

    behavior_rows = await crud.list_behavior_cards(session, book_id)
    behavior_rows = [(b, c) for b, c in behavior_rows if b.core_lesson and "无显著" not in (b.core_lesson or "")]
    dialogue_cards = await crud.list_dialogue_cards(session, book_id)
    characters = await crud.list_characters(session, book_id)
    clusters = await crud.list_clusters(session, book_id)
    rules = await crud.list_rules(session, book_id)
    meta = await crud.get_metadata(session, book_id)

    files: dict[str, str] = {}
    files["00_书籍信息.md"] = (
        f"# 《{book.title}》读书笔记\n\n"
        f"- 作者:{book.author or '未知'}\n"
        f"- 主角:{meta.protagonist if meta else '未识别'}\n"
        f"- 题材:{meta.setting if meta else '未知'}\n"
        f"- 总章节:{book.total_chapters},已分析:{book.analyzed_chapters}\n"
        f"- 导出时间:{datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    )
    files["做派卡.md"] = "# 做派卡(行为层 6 维)\n\n" + "\n".join(_behavior_md(b, c) for b, c in behavior_rows)
    files["对话卡.md"] = "# 对话卡(逐句精读)\n\n" + "\n".join(_dialogue_md(d, c) for d, c in dialogue_cards)

    char_md = ["# 人物画像\n"]
    for c in characters:
        char_md.append(f"## {c.name}({c.role_type or '?'},出场 {c.appearance_count} 章)\n")
        char_md.append((c.behavior_pattern or "(无总结)") + "\n")
    files["人物画像.md"] = "\n".join(char_md)

    cluster_md = ["# 情境聚类\n"]
    for c in clusters:
        cluster_md.append(f"## {c.cluster_name}({c.instance_count} 例)\n")
        cluster_md.append((c.pattern_summary or "(无总结)") + "\n")
    files["情境聚类.md"] = "\n".join(cluster_md)

    if rules:
        from collections import defaultdict

        by_cat = defaultdict(list)
        for r in rules:
            by_cat[r.category or "其他"].append(r)
        rule_md = ["# 社会规则 / 潜规则手册\n"]
        for cat, items in by_cat.items():
            rule_md.append(f"## {cat}\n")
            for r in items:
                chs = "、".join(f"第{e.get('chapter_index','?')}章" for e in (r.examples or [])[:6])
                rule_md.append(f"- **{r.rule}**")
                if r.explanation:
                    rule_md.append(f"  - {r.explanation}")
                if chs:
                    rule_md.append(f"  - 出处:{chs}")
            rule_md.append("")
        files["社会规则手册.md"] = "\n".join(rule_md)

    if meta and meta.tally_timeline:
        tl = meta.tally_timeline
        lines = ["# 长期账时间线\n", (tl.get("summary") or "") + "\n"]
        for item in tl.get("timeline", []):
            lines.append(
                f"- [第{item.get('chapter_index','?')}章] {item.get('event','')} "
                f"({item.get('status','')} — {item.get('payoff_note','')})"
            )
        files["长期账时间线.md"] = "\n".join(lines)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    buf.seek(0)

    safe_title = book.title.replace("/", "_").replace("\\", "_")
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{safe_title}.zip"
    }
    return StreamingResponse(buf, media_type="application/zip", headers=headers)


@router.get("/{book_id}/export/character/{character_id}")
async def export_character(book_id: int, character_id: int, session: AsyncSession = Depends(get_session)):
    c = await crud.get_character(session, character_id)
    if not c:
        raise HTTPException(404, "人物不存在")
    lines = [f"# {c.name}({c.role_type or '?'})\n", (c.behavior_pattern or "") + "\n", "## 出场场景\n"]
    for s in c.scenes or []:
        lines.append(f"- [第{s.get('chapter_index','?')}章] {s.get('scene','')}（{s.get('lesson','')}）")
    md = "\n".join(lines)
    return Response(md, media_type="text/markdown; charset=utf-8")


@router.get("/{book_id}/export/tag/{tag}")
async def export_tag(book_id: int, tag: str, session: AsyncSession = Depends(get_session)):
    rows = await crud.list_behavior_cards(session, book_id, tag=tag)
    lines = [f"# 标签:{tag}（{len(rows)} 例）\n"]
    for b, c in rows:
        lines.append(_behavior_md(b, c))
    md = "\n".join(lines)
    return Response(md, media_type="text/markdown; charset=utf-8")
