"""结果查询:章节 / 行为 / 对话 / 人物 / 情境 / 长期账 / 卡片 / 检索。"""
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.serializers import (
    behavior_to_dict,
    character_to_dict,
    chapter_to_dict,
    cluster_to_dict,
    dialogue_to_dict,
    rule_to_dict,
)
from app.db import crud
from app.db.database import get_session

router = APIRouter(prefix="/api", tags=["results"])


@router.get("/books/{book_id}/chapters")
async def list_chapters(book_id: int, session: AsyncSession = Depends(get_session)):
    chapters = await crud.list_chapters(session, book_id)
    return [chapter_to_dict(c) for c in chapters]


@router.get("/chapters/{chapter_id}")
async def get_chapter(chapter_id: int, session: AsyncSession = Depends(get_session)):
    ch = await crud.get_chapter(session, chapter_id)
    if not ch:
        raise HTTPException(404, "章节不存在")
    return chapter_to_dict(ch, with_content=True)


@router.get("/chapters/{chapter_id}/behavior")
async def get_chapter_behavior(chapter_id: int, session: AsyncSession = Depends(get_session)):
    b = await crud.get_behavior_by_chapter(session, chapter_id)
    if not b:
        return None
    ch = await crud.get_chapter(session, chapter_id)
    return behavior_to_dict(b, ch)


@router.get("/chapters/{chapter_id}/dialogues")
async def get_chapter_dialogues(chapter_id: int, session: AsyncSession = Depends(get_session)):
    dialogues = await crud.get_dialogues_by_chapter(session, chapter_id)
    ch = await crud.get_chapter(session, chapter_id)
    return [dialogue_to_dict(d, ch) for d in dialogues]


@router.get("/books/{book_id}/characters")
async def list_characters(book_id: int, session: AsyncSession = Depends(get_session)):
    chars = await crud.list_characters(session, book_id)
    return [character_to_dict(c) for c in chars]


@router.get("/characters/{character_id}")
async def get_character(character_id: int, session: AsyncSession = Depends(get_session)):
    c = await crud.get_character(session, character_id)
    if not c:
        raise HTTPException(404, "人物不存在")
    return character_to_dict(c, with_scenes=True)


@router.get("/books/{book_id}/clusters")
async def list_clusters(book_id: int, session: AsyncSession = Depends(get_session)):
    clusters = await crud.list_clusters(session, book_id)
    return [cluster_to_dict(c) for c in clusters]


@router.get("/clusters/{cluster_id}")
async def get_cluster(cluster_id: int, session: AsyncSession = Depends(get_session)):
    c = await crud.get_cluster(session, cluster_id)
    if not c:
        raise HTTPException(404, "情境聚类不存在")
    return cluster_to_dict(c, with_instances=True)


@router.get("/books/{book_id}/tally-timeline")
async def tally_timeline(book_id: int, session: AsyncSession = Depends(get_session)):
    meta = await crud.get_metadata(session, book_id)
    return (meta.tally_timeline if meta else None) or {"timeline": [], "summary": ""}


@router.get("/books/{book_id}/cards/behavior")
async def behavior_cards(
    book_id: int,
    tag: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    rows = await crud.list_behavior_cards(session, book_id, tag=tag)
    cards = [behavior_to_dict(b, c) for b, c in rows]
    # 同时返回可用标签facet
    all_rows = await crud.list_behavior_cards(session, book_id)
    tag_counter: Counter = Counter()
    char_counter: Counter = Counter()
    for b, _ in all_rows:
        tag_counter.update(b.tags or [])
        char_counter.update(b.characters_involved or [])
    return {
        "cards": cards,
        "facets": {
            "tags": tag_counter.most_common(),
            "characters": char_counter.most_common(30),
        },
    }


@router.get("/books/{book_id}/cards/dialogue")
async def dialogue_cards(
    book_id: int,
    technique: str | None = Query(None),
    speaker: str | None = Query(None),
    speaker_role: str | None = Query(None),
    scenario: str | None = Query(None),
    min_strength: int | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    rows = await crud.list_dialogue_cards(
        session, book_id, technique=technique, speaker=speaker, speaker_role=speaker_role, scenario=scenario, min_strength=min_strength
    )
    cards = [dialogue_to_dict(d, c) for d, c in rows]
    all_rows = await crud.list_dialogue_cards(session, book_id)
    tech_counter: Counter = Counter()
    speaker_counter: Counter = Counter()
    scenario_counter: Counter = Counter()
    role_counter: Counter = Counter()
    for d, _ in all_rows:
        tech_counter.update(d.techniques or [])
        if d.speaker:
            speaker_counter.update([d.speaker])
        if d.scenario:
            scenario_counter.update([d.scenario])
        if d.speaker_role:
            role_counter.update([d.speaker_role])
    return {
        "cards": cards,
        "facets": {
            "techniques": tech_counter.most_common(),
            "speakers": speaker_counter.most_common(20),
            "scenarios": scenario_counter.most_common(),
            "speaker_roles": role_counter.most_common(),
        },
    }


@router.get("/books/{book_id}/scenario-search")
async def scenario_search(
    book_id: int,
    q: str = Query(..., min_length=2, description="输入真实场景，如：其他领导想挖我，怎么回复"),
    session: AsyncSession = Depends(get_session),
):
    """场景调用：用自然语言描述一个真实场景，搜索书中相关的对话卡作为参考。"""
    results = await crud.search_dialogue(session, q, book_id)
    if not results:
        return {"query": q, "cards": [], "behavior_cards": []}

    dialogue_ids = [r["dialogue_id"] for r in results if r.get("dialogue_id")]
    behavior_ids = [r["behavior_id"] for r in results if r.get("behavior_id")]
    chapter_ids = list(set(r.get("chapter_id") for r in results if r.get("chapter_id")))

    from app.db.models import BehaviorAnalysis, Chapter, DialogueAnalysis
    from sqlalchemy import select

    cards = []
    behavior_cards = []

    if dialogue_ids:
        stmt = (
            select(DialogueAnalysis, Chapter)
            .join(Chapter, DialogueAnalysis.chapter_id == Chapter.id)
            .where(DialogueAnalysis.id.in_(dialogue_ids))
        )
        rows = (await session.execute(stmt)).all()
        cards = [dialogue_to_dict(d, c) for d, c in rows]

    if behavior_ids:
        stmt = (
            select(BehaviorAnalysis, Chapter)
            .join(Chapter, BehaviorAnalysis.chapter_id == Chapter.id)
            .where(BehaviorAnalysis.id.in_(behavior_ids))
        )
        rows = (await session.execute(stmt)).all()
        behavior_cards = [behavior_to_dict(b, c) for b, c in rows]

    return {"query": q, "cards": cards, "behavior_cards": behavior_cards}


@router.get("/books/{book_id}/rules")
async def list_rules(book_id: int, session: AsyncSession = Depends(get_session)):
    rules = await crud.list_rules(session, book_id)
    cards = [rule_to_dict(r) for r in rules]
    cat_counter: Counter = Counter(r["category"] for r in cards if r["category"])
    return {"rules": cards, "facets": {"categories": cat_counter.most_common()}}


# ===================== 家庭 · 人情世故专题 =====================
# 分类标签里凡含这些字，视为「家庭」直接命中
_FAMILY_CATEGORY_HINTS = ("家庭", "婚恋", "夫妻", "婚姻")
# 关键词召回：在规则/理念/原文里出现即扩展纳入（口径=标签+家庭关键词）
_FAMILY_KEYWORDS = (
    "父母", "爸", "妈", "母亲", "父亲", "岳父", "岳母", "丈母娘", "婆媳", "婆婆", "公公",
    "儿子", "女儿", "孩子", "妻子", "老婆", "丈夫", "老公", "夫妻", "媳妇", "女婿",
    "结婚", "离婚", "闪婚", "成家", "彩礼", "嫁妆", "相亲", "门当户对", "门第", "高攀",
    "女朋友", "男朋友", "女友", "男友", "对象", "家里", "家人", "亲戚", "亲家", "长辈",
    "外公", "外婆", "爷爷", "奶奶", "婚事", "提亲", "退婚", "未婚妻", "未婚夫", "家族",
)
# 主题归类（按优先级，命中即止）
_FAMILY_THEMES = [
    ("分手 / 止损 / 旧情", ("分手", "挽回", "前任", "前女友", "前男友", "复合", "纠缠", "止损", "甩")),
    ("择偶 / 门第 / 条件", ("门当户对", "门第", "高攀", "攀附", "门不当", "配不配", "层级", "悬殊", "般配", "资本", "背景")),
    ("彩礼 / 物质 / 经济", ("彩礼", "嫁妆", "房", "车", "物质", "买单", "经济", "礼金")),
    ("与父母 / 长辈相处", ("父母", "爸", "妈", "母亲", "父亲", "长辈", "孝", "岳父", "岳母", "丈母娘", "婆", "公公", "家人", "亲家", "外公", "外婆", "爷爷", "奶奶")),
    ("追求 / 示好 / 暧昧", ("表白", "追求", "约会", "接送", "好感", "示好", "受害者", "保护欲", "暧昧", "心动", "相亲")),
    ("婚姻 / 夫妻 / 成家", ("夫妻", "老婆", "妻", "丈夫", "老公", "婚后", "闪婚", "结婚", "成家", "离婚", "媳妇", "嫁", "娶", "婚事", "提亲")),
]


def _is_family_category(cat: str | None) -> bool:
    cat = cat or ""
    return any(h in cat for h in _FAMILY_CATEGORY_HINTS)


def _has_family_keyword(text: str) -> bool:
    return any(k in text for k in _FAMILY_KEYWORDS)


def _classify_family_theme(text: str) -> str:
    for name, kws in _FAMILY_THEMES:
        if any(k in text for k in kws):
            return name
    return "其他 · 婚恋家庭"


@router.get("/books/{book_id}/family")
async def family_insights(book_id: int, session: AsyncSession = Depends(get_session)):
    """家庭·人情世故专题：从做派卡的社会规则里抽取「婚恋家庭」标签条目，
    并用家庭关键词扩展召回其他分类里涉及家庭的规则，按主题归类。
    附跨章沉淀的家庭规则手册。"""
    book = await crud.get_book(session, book_id)
    if not book:
        raise HTTPException(404, "书籍不存在")

    rows = await crud.list_behavior_cards(session, book_id)
    items: list[dict] = []
    seen_rules: set[str] = set()
    tag_count = 0
    keyword_count = 0

    for b, c in rows:
        for sr in (b.social_rules or []):
            if not isinstance(sr, dict):
                continue
            rule = (sr.get("rule") or "").strip()
            if not rule:
                continue
            why = (sr.get("why") or sr.get("explanation") or "").strip()
            evidence = (sr.get("evidence") or "").strip()
            category = sr.get("category")
            blob = " ".join((rule, why, evidence))

            by_tag = _is_family_category(category)
            by_kw = (not by_tag) and _has_family_keyword(blob)
            if not (by_tag or by_kw):
                continue
            if rule in seen_rules:  # 同书去重相同规则
                continue
            seen_rules.add(rule)

            if by_tag:
                tag_count += 1
            else:
                keyword_count += 1

            items.append({
                "chapter_id": c.id,
                "chapter_index": c.index,
                "chapter_title": c.title,
                "theme": _classify_family_theme(blob + " " + (b.scene_summary or "")),
                "category": category,
                "source": "tag" if by_tag else "keyword",
                "rule": rule,
                "why": why,
                "evidence": evidence,
                "scene_summary": b.scene_summary,
                "core_lesson": b.core_lesson,
            })

    # 按主题分组（保持主题既定顺序，其它垫底）
    theme_order = {name: i for i, (name, _) in enumerate(_FAMILY_THEMES)}
    theme_order["其他 · 婚恋家庭"] = 99
    groups: dict[str, list[dict]] = {}
    for it in items:
        groups.setdefault(it["theme"], []).append(it)
    themes = [
        {"name": name, "count": len(its), "items": sorted(its, key=lambda x: x["chapter_index"])}
        for name, its in sorted(groups.items(), key=lambda kv: theme_order.get(kv[0], 50))
    ]

    # 跨章沉淀的家庭规则手册
    rules = await crud.list_rules(session, book_id)
    handbook = [rule_to_dict(r) for r in rules if _is_family_category(r.category)]

    return {
        "book": {"id": book.id, "title": book.title},
        "total": len(items),
        "tag_count": tag_count,
        "keyword_count": keyword_count,
        "themes": themes,
        "handbook": handbook,
    }


@router.get("/books/{book_id}/stats")
async def book_stats(book_id: int, session: AsyncSession = Depends(get_session)):
    """量化分析:话术技巧/场景/表态强度/做派标签/规则分类的频次统计。"""
    book = await crud.get_book(session, book_id)
    if not book:
        raise HTTPException(404, "书籍不存在")
    meta = await crud.get_metadata(session, book_id)
    dlg = await crud.list_dialogue_cards(session, book_id)
    beh = await crud.list_behavior_cards(session, book_id)
    rules = await crud.list_rules(session, book_id)

    tech: Counter = Counter()
    scen: Counter = Counter()
    roles: Counter = Counter()
    strength: dict[int, int] = {i: 0 for i in range(1, 6)}
    s_sum = s_n = 0
    for d, _ in dlg:
        tech.update(d.techniques or [])
        if d.scenario:
            scen.update([d.scenario])
        if d.speaker_role:
            roles.update([d.speaker_role])
        s = d.signal_strength
        if isinstance(s, str) and s.strip().isdigit():
            s = int(s)
        if isinstance(s, int) and 1 <= s <= 5:
            strength[s] += 1
            s_sum += s
            s_n += 1
    tags: Counter = Counter()
    for b, _ in beh:
        tags.update(b.tags or [])
    cats: Counter = Counter(r.category for r in rules if r.category)

    return {
        "id": book.id,
        "title": book.title,
        "protagonist": meta.protagonist if meta else None,
        "setting": meta.setting if meta else None,
        "counts": {"dialogues": len(dlg), "behaviors": len(beh), "rules": len(rules)},
        "techniques": tech.most_common(15),
        "scenarios": scen.most_common(),
        "speaker_roles": roles.most_common(),
        "signal_strength": [[i, strength[i]] for i in range(1, 6)],
        "avg_signal": round(s_sum / s_n, 2) if s_n else 0,
        "tags": tags.most_common(15),
        "rule_categories": cats.most_common(),
    }


@router.get("/compare")
async def compare(a: int, b: int, session: AsyncSession = Depends(get_session)):
    """两本书对比:基本信息、高频标签/场景/技巧、规则分类、主角处世模式,以及标签的共同/差异。"""

    async def stats(bid: int):
        book = await crud.get_book(session, bid)
        if not book:
            return None
        meta = await crud.get_metadata(session, bid)
        beh = await crud.list_behavior_cards(session, bid)
        dlg = await crud.list_dialogue_cards(session, bid)
        rules = await crud.list_rules(session, bid)
        chars = await crud.list_characters(session, bid)
        tagc: Counter = Counter()
        for bh, _ in beh:
            tagc.update(bh.tags or [])
        scenc: Counter = Counter()
        techc: Counter = Counter()
        for d, _ in dlg:
            if d.scenario:
                scenc.update([d.scenario])
            techc.update(d.techniques or [])
        catc: Counter = Counter(r.category for r in rules if r.category)
        protag = next((c for c in chars if c.role_type == "主角"), None)
        return {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "protagonist": meta.protagonist if meta else None,
            "setting": meta.setting if meta else None,
            "total_chapters": book.total_chapters,
            "analyzed_chapters": book.analyzed_chapters,
            "counts": {
                "behavior": len(beh),
                "dialogue": len(dlg),
                "rules": len(rules),
                "characters": len(chars),
            },
            "top_tags": tagc.most_common(15),
            "top_scenarios": scenc.most_common(10),
            "top_techniques": techc.most_common(12),
            "rule_categories": catc.most_common(),
            "protagonist_pattern": protag.behavior_pattern if protag else None,
            "rules_sample": [{"category": r.category, "rule": r.rule} for r in rules[:14]],
        }

    sa = await stats(a)
    sb = await stats(b)
    if not sa or not sb:
        raise HTTPException(404, "书籍不存在")
    ta = {t for t, _ in sa["top_tags"]}
    tb = {t for t, _ in sb["top_tags"]}
    return {
        "a": sa,
        "b": sb,
        "diff": {
            "shared_tags": sorted(ta & tb),
            "only_a_tags": [t for t, _ in sa["top_tags"] if t not in tb][:12],
            "only_b_tags": [t for t, _ in sb["top_tags"] if t not in ta][:12],
        },
    }


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    book_id: int | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    behavior = await crud.search_behavior(session, q, book_id)
    dialogue = await crud.search_dialogue(session, q, book_id)
    return {"query": q, "behavior": behavior, "dialogue": dialogue}
