"""跨章节聚合:一本书分析完成后触发。人物画像 / 情境聚类 / 长期账时间线。"""
from collections import Counter, defaultdict
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.llm.base import LLMClient, LLMError
from app.llm.prompts import (
    build_character_prompt,
    build_rules_prompt,
    build_situation_cluster_prompt,
    build_tally_timeline_prompt,
)
from app.llm.base import extract_json
from app.utils.logger import get_logger

logger = get_logger("aggregator")

MIN_CHARACTER_APPEARANCES = 1
MAX_CHARACTERS = 20
MIN_CLUSTER_INSTANCES = 2
MAX_CLUSTERS = 25
MAX_MATERIAL_ITEMS = 30


async def run_aggregation(session: AsyncSession, book_id: int, client: LLMClient) -> dict[str, int]:
    rows = await crud.list_behavior_cards(session, book_id)
    # 仅保留有实质内容的(core_lesson 非"无显著人情戏")
    cards = [(b, c) for b, c in rows if b.core_lesson and "无显著" not in (b.core_lesson or "")]
    logger.info("聚合开始:book=%d,有效行为卡 %d 张", book_id, len(cards))

    n_char = await _aggregate_characters(session, book_id, client, cards)
    n_cluster = await _aggregate_clusters(session, book_id, client, cards)
    n_rule = await _aggregate_rules(session, book_id, client, cards)
    await _aggregate_tally(session, book_id, client, cards)

    meta = await crud.get_or_create_metadata(session, book_id)
    meta.aggregation_status = "completed"
    await session.commit()
    logger.info("聚合完成:book=%d,人物 %d,情境 %d,规则 %d", book_id, n_char, n_cluster, n_rule)
    return {"characters": n_char, "clusters": n_cluster, "rules": n_rule}


async def _aggregate_characters(session, book_id, client, cards) -> int:
    scenes_by_char: dict[str, list[dict]] = defaultdict(list)
    for b, c in cards:
        for name in b.characters_involved or []:
            scenes_by_char[name].append(
                {"chapter_index": c.index, "scene": b.scene_summary or "", "lesson": b.core_lesson or ""}
            )

    ranked = sorted(scenes_by_char.items(), key=lambda kv: len(kv[1]), reverse=True)
    profiles: list[dict[str, Any]] = []
    for name, scenes in ranked:
        if len(scenes) < MIN_CHARACTER_APPEARANCES:
            continue
        if len(profiles) >= MAX_CHARACTERS:
            break
        material = "\n".join(
            f"[第{s['chapter_index']}章] {s['scene']}（{s['lesson']}）" for s in scenes[:MAX_MATERIAL_ITEMS]
        )
        prompt = build_character_prompt(name, material)
        role_type, pattern = "重要配角", None
        try:
            raw = await client.analyze(prompt, mode="fast", response_format="text")
            data = extract_json(raw)
            role_type = data.get("role_type", "重要配角")
            pattern = data.get("behavior_pattern")
        except (LLMError, Exception) as exc:  # noqa: BLE001
            logger.warning("人物画像生成失败(%s): %s", name, exc)
        profiles.append(
            {
                "name": name,
                "role_type": role_type,
                "behavior_pattern": pattern,
                "appearance_count": len(scenes),
                "scenes": scenes,
            }
        )
    await crud.replace_characters(session, book_id, profiles)
    await session.commit()
    return len(profiles)


async def _aggregate_clusters(session, book_id, client, cards) -> int:
    instances_by_tag: dict[str, list[dict]] = defaultdict(list)
    for b, c in cards:
        for tag in b.tags or []:
            instances_by_tag[tag].append(
                {
                    "chapter_id": c.id,
                    "chapter_index": c.index,
                    "analysis_id": b.id,
                    "summary": b.scene_summary or "",
                }
            )

    ranked = sorted(instances_by_tag.items(), key=lambda kv: len(kv[1]), reverse=True)
    clusters: list[dict[str, Any]] = []
    for tag, instances in ranked:
        if len(instances) < MIN_CLUSTER_INSTANCES:
            continue
        if len(clusters) >= MAX_CLUSTERS:
            break
        material = "\n".join(
            f"[第{i['chapter_index']}章] {i['summary']}" for i in instances[:MAX_MATERIAL_ITEMS]
        )
        pattern = None
        try:
            raw = await client.analyze(build_situation_cluster_prompt(tag, material), mode="fast", response_format="text")
            pattern = extract_json(raw).get("pattern_summary")
        except (LLMError, Exception) as exc:  # noqa: BLE001
            logger.warning("情境聚类生成失败(%s): %s", tag, exc)
        clusters.append({"cluster_name": tag, "instances": instances, "pattern_summary": pattern})
    await crud.replace_clusters(session, book_id, clusters)
    await session.commit()
    return len(clusters)


async def _aggregate_rules(session, book_id, client, cards) -> int:
    """收集各章 social_rules,LLM 归并去重归类成规则手册。
    分批聚合：按章节分桶（每桶约 300 章），每桶单独 LLM 聚合，再二次合并去重。
    避免早期把 raw_items[:200] 截断导致只覆盖前 60-90 章的问题。
    """
    # 收集 (chapter_index, text) 二元组，按章节分桶
    raw_with_ch: list[tuple[int, str]] = []
    for b, c in cards:
        for r in b.social_rules or []:
            if isinstance(r, dict) and r.get("rule"):
                why = r.get("why") or r.get("explanation") or ""
                ev = r.get("evidence") or ""
                raw_with_ch.append((c.index, f"[第{c.index}章] {r['rule']}|因为:{why}|证据:{ev}"))
    if not raw_with_ch:
        return 0

    raw_with_ch.sort(key=lambda x: x[0])
    max_ch = raw_with_ch[-1][0]

    # 分桶：每 300 章一桶；每桶最多 80 条原始条目，避免 LLM 输出超 max_tokens 被截断
    BUCKET_SPAN = 300
    MAX_ITEMS_PER_BUCKET = 80
    buckets: list[list[str]] = []
    for start in range(1, max_ch + 1, BUCKET_SPAN):
        end = start + BUCKET_SPAN
        bucket = [t for ch, t in raw_with_ch if start <= ch < end]
        if not bucket:
            continue
        # 桶内若超过 200 条，等距下采样保持覆盖均匀
        if len(bucket) > MAX_ITEMS_PER_BUCKET:
            step = len(bucket) / MAX_ITEMS_PER_BUCKET
            bucket = [bucket[int(i * step)] for i in range(MAX_ITEMS_PER_BUCKET)]
        buckets.append(bucket)
    logger.info("book=%d 规则聚合分桶: 共 %d 桶, 章节范围 1-%d", book_id, len(buckets), max_ch)

    async def _llm_rules(material: str) -> list[dict]:
        resp = None
        try:
            resp = await client.analyze(build_rules_prompt(material), mode="fast", response_format="text")
            return extract_json(resp).get("rules") or []
        except (LLMError, Exception) as exc:  # noqa: BLE001
            r = resp or ""
            codepoints = [f"U+{ord(c):04X}" for c in r[:8]]
            head_repr = repr(r[:150])
            tail_repr = repr(r[-80:])
            logger.warning("规则聚合 LLM 调用失败: %s | 前8码点: %s | head: %s | tail: %s",
                           exc, codepoints, head_repr, tail_repr)
            return []

    # 用字符 bigram 做相似度匹配，比连续长 token 更适合中文短句
    def _bigrams(s: str) -> set[str]:
        s = (s or "").strip()
        s = "".join(ch for ch in s if ch.isalnum() or '一' <= ch <= '鿿')
        if len(s) < 2:
            return set()
        return {s[i:i+2] for i in range(len(s) - 1)}

    # 一桶情况，直接出最终结果
    if len(buckets) <= 1:
        rules_raw = await _llm_rules("\n".join(buckets[0])) if buckets else []
    else:
        # 多桶：每桶独立聚合
        partial_rules: list[dict] = []
        for i, bucket in enumerate(buckets):
            chunk = await _llm_rules("\n".join(bucket))
            logger.info("book=%d 规则桶 %d/%d: 抽出 %d 条", book_id, i + 1, len(buckets), len(chunk))
            partial_rules.extend(chunk)

        if not partial_rules:
            # 所有桶 LLM 全失败，绝不清空数据库——直接 return 不动旧数据
            logger.warning("book=%d 所有桶 LLM 都失败，保留旧规则不更新", book_id)
            return 0
        elif len(partial_rules) <= 50:
            # 桶汇总数量不大，直接用，不再二次 LLM
            rules_raw = partial_rules
        else:
            # 二次合并：把 partial_rules 作为新材料再过一次 LLM 去重归类
            merge_material = "\n".join(
                f"[第{','.join(str(ch) for ch in (r.get('chapters') or [])) or '?'}章] {r.get('rule','')}|因为:{r.get('explanation','')}|证据:"
                for r in partial_rules
            )
            logger.info("book=%d 规则二次合并: 输入 %d 条", book_id, len(partial_rules))
            merged = await _llm_rules(merge_material)
            if merged:
                # 代码后处理：LLM 合并去重时常常只挑代表 chapter。
                # 用 rule 文本字符 bigram 重叠回填——对每条 merged rule，找出所有 partial_rules
                # 中 rule 文本足够相似的源条目，把它们的 chapters 全部合并进来。
                partial_with_grams = [(p, _bigrams(p.get("rule", ""))) for p in partial_rules]
                for m in merged:
                    m_grams = _bigrams(m.get("rule", ""))
                    if not m_grams:
                        continue
                    extra_chs: set[int] = {int(ch) for ch in (m.get("chapters") or []) if isinstance(ch, (int, str)) and str(ch).isdigit()}
                    for p, p_grams in partial_with_grams:
                        if not p_grams:
                            continue
                        overlap = len(m_grams & p_grams) / max(1, min(len(m_grams), len(p_grams)))
                        if overlap >= 0.35:  # bigram 阈值 0.35，对短句也合理
                            for ch in (p.get("chapters") or []):
                                if isinstance(ch, int):
                                    extra_chs.add(ch)
                                elif isinstance(ch, str) and ch.isdigit():
                                    extra_chs.add(int(ch))
                    m["chapters"] = sorted(extra_chs)
                    m["occurrence"] = max(m.get("occurrence") or 0, len(extra_chs))
                # 统计回填效果
                covered = {ch for m in merged for ch in (m.get("chapters") or [])}
                logger.info("book=%d 二次合并+回填: 输出 %d 条, chapter 覆盖 %d 章 (min=%d max=%d)",
                            book_id, len(merged), len(covered), min(covered) if covered else 0, max(covered) if covered else 0)
                rules_raw = merged
            else:
                # 二次合并 LLM 失败，使用 partial_rules（保证不丢数据）
                logger.warning("book=%d 二次合并失败，使用 partial_rules %d 条", book_id, len(partial_rules))
                rules_raw = partial_rules

    # 兜底：如果 rules_raw 为空，绝不清空数据库
    if not rules_raw:
        logger.warning("book=%d 聚合结果为空，保留旧规则不更新", book_id)
        return 0

    rules: list[dict[str, Any]] = []
    for r in rules_raw:
        chapters = r.get("chapters") or []
        rules.append(
            {
                "rule": r.get("rule", ""),
                "category": r.get("category"),
                "explanation": r.get("explanation"),
                "examples": [{"chapter_index": ch} for ch in chapters],
                "occurrence": r.get("occurrence") or len(chapters) or 1,
            }
        )
    await crud.replace_rules(session, book_id, rules)
    await session.commit()
    return len(rules)


async def _aggregate_tally(session, book_id, client, cards) -> None:
    items = []
    for b, c in cards:
        tally = b.long_term_tally
        if isinstance(tally, dict) and tally.get("description"):
            items.append(
                f"[第{c.index}章] 记账:{tally.get('description')};预期兑现:{tally.get('expected_payoff', '未注明')}"
            )
    if not items:
        return
    material = "\n".join(items[:80])
    try:
        raw = await client.analyze(build_tally_timeline_prompt(material), mode="fast", response_format="text")
        timeline = extract_json(raw)
    except (LLMError, Exception) as exc:  # noqa: BLE001
        logger.warning("长期账时间线生成失败: %s", exc)
        return
    meta = await crud.get_or_create_metadata(session, book_id)
    meta.tally_timeline = timeline
    await session.commit()
