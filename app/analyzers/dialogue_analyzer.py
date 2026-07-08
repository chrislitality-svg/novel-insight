"""对话精读:对抽取出的单段对话调用 deep 模型逐句拆解。"""
from typing import NamedTuple

from app.llm.base import LLMClient, LLMError, extract_json
from app.llm.prompts import build_dialogue_prompt
from app.utils.logger import get_logger

logger = get_logger("dialogue_analyzer")


class DialogueResult(NamedTuple):
    ok: bool
    data: dict | None
    raw: str
    error: str | None


async def analyze_dialogue(
    client: LLMClient,
    *,
    context: str,
    speaker: str,
    listener: str | None,
    relationship: str,
    original_text: str,
) -> DialogueResult:
    prompt = build_dialogue_prompt(
        context=context,
        speaker=speaker,
        listener=listener or "(未知)",
        relationship=relationship,
        original_text=original_text,
    )
    try:
        raw = await client.analyze(prompt, mode="deep", response_format="text")
    except LLMError as exc:
        return DialogueResult(False, None, "", str(exc))

    try:
        data = extract_json(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("对话精读 JSON 解析失败: %s", exc)
        return DialogueResult(False, None, raw, f"JSON 解析失败: {exc}")

    return DialogueResult(True, data, raw, None)
