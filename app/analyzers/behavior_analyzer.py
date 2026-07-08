"""行为层分析:对单章调用 fast 模型,产出 6 维结构化结果。"""
from typing import NamedTuple

from app.llm.base import LLMClient, LLMError, extract_json
from app.llm.prompts import build_behavior_prompt
from app.utils.logger import get_logger

logger = get_logger("behavior_analyzer")

# 单章送分析的正文上限(过长截断,省 token;6 维分析不需要全文)
MAX_CONTENT_CHARS = 6000


class BehaviorResult(NamedTuple):
    ok: bool
    data: dict | None
    raw: str
    error: str | None


async def analyze_chapter_behavior(client: LLMClient, title: str, content: str) -> BehaviorResult:
    prompt = build_behavior_prompt(title, content[:MAX_CONTENT_CHARS])
    try:
        raw = await client.analyze(prompt, mode="fast", response_format="text")
    except LLMError as exc:
        return BehaviorResult(False, None, "", str(exc))

    try:
        data = extract_json(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("行为分析 JSON 解析失败(%s): %s", title, exc)
        return BehaviorResult(False, None, raw, f"JSON 解析失败: {exc}")

    return BehaviorResult(True, data, raw, None)
