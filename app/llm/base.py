"""LLM 抽象层。业务层只依赖 LLMClient,不感知具体 provider。"""
import json
import re
from abc import ABC, abstractmethod
from typing import Any

from app.utils.logger import get_logger

logger = get_logger("llm")


class LLMError(Exception):
    pass


class LLMClient(ABC):
    @abstractmethod
    async def analyze(
        self,
        prompt: str,
        mode: str = "fast",  # 'fast' / 'deep'
        response_format: str = "json",  # 'json' / 'text'
        max_retries: int = 3,
    ) -> dict | str:
        """调用 LLM。response_format='json' 时返回 dict,否则返回 str。"""
        ...


def extract_json(text: str) -> dict[str, Any]:
    """从 LLM 响应中提取 JSON。兼容 ```json``` 包裹、思维过程前缀、裸 JSON。"""
    if not text or not text.strip():
        raise ValueError("空响应,无法提取 JSON")

    # 1) ```json ... ``` 或 ``` ... ``` 代码块
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        return _loads(fence.group(1))

    # 2) 第一个 { 到最后一个 } (适配 R1 带思维过程文本)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return _loads(text[start : end + 1])

    raise ValueError(f"无法从响应中提取 JSON: {text[:200]}")


def _loads(s: str) -> dict[str, Any]:
    try:
        return json.loads(s, strict=False)
    except json.JSONDecodeError:
        pass

    # 容错 1: 剥离 markdown 加粗/斜体 + 去尾随逗号 + 转义控制字符
    cleaned = re.sub(r"\*\*([^*\n]+?)\*\*", r"\1", s)
    cleaned = re.sub(r"(?<![*\w])\*([^*\n]+?)\*(?![*\w])", r"\1", cleaned)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    cleaned = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", lambda m: "\\u{:04x}".format(ord(m.group())), cleaned)
    try:
        return json.loads(cleaned, strict=False)
    except json.JSONDecodeError:
        pass

    # 容错 2: 模型返回了字面 \n / \t / \" (双重 escape) —— 把 JSON 结构空白还原
    # 仅在结构位置（key 前后、值前后、逗号前后）还原，避免破坏字符串内部的 \n
    cleaned2 = cleaned.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"')
    try:
        return json.loads(cleaned2, strict=False)
    except json.JSONDecodeError:
        pass

    # 容错 3: 最后尝试把裸换行替换为 \n（与上一步相反方向）
    cleaned3 = re.sub(r"([^\\])\n", r"\1\\n", cleaned)
    return json.loads(cleaned3, strict=False)
