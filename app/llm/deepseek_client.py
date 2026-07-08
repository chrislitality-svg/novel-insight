"""OpenAI 兼容的 LLM 客户端实现(DeepSeek / OpenAI / Claude 兼容端点共用)。

- fast 模式:走 *_fast_model,支持 JSON mode(response_format=json_object)
- deep 模式:走 *_deep_model(如 deepseek-reasoner),不支持 JSON mode,靠后处理提取 JSON
- 并发:asyncio.Semaphore(settings.llm_concurrency)
- 重试:指数退避(1s/2s/4s),最多 max_retries 次
- 超时:settings.llm_timeout 秒
"""
import asyncio
from typing import Any

from openai import AsyncOpenAI

from app.config import settings
from app.llm.base import LLMClient, LLMError, extract_json
from app.utils.logger import get_logger

logger = get_logger("llm.client")


class OpenAICompatibleClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        fast_model: str,
        deep_model: str,
        provider_name: str = "deepseek",
    ):
        if not api_key:
            raise LLMError(
                f"未配置 {provider_name} 的 API Key,请在 .env 中设置后重启。"
            )
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=settings.llm_timeout)
        self.fast_model = fast_model
        self.deep_model = deep_model
        self.provider_name = provider_name
        self._semaphore = asyncio.Semaphore(settings.llm_concurrency)

    async def analyze(
        self,
        prompt: str,
        mode: str = "fast",
        response_format: str = "json",
        max_retries: int = 3,
    ) -> dict | str:
        model = self.deep_model if mode == "deep" else self.fast_model
        # 仅 fast 模式 + json 时启用原生 JSON mode(reasoner 不支持)
        use_json_mode = mode == "fast" and response_format == "json"

        raw = await self._call_with_retry(prompt, model, use_json_mode, max_retries)

        if response_format == "json":
            try:
                return extract_json(raw)
            except (ValueError, Exception) as exc:  # noqa: BLE001
                # JSON 解析失败:把原始响应抛出,调用方据此标记 failed 并存 raw_response
                raise LLMError(f"JSON 解析失败: {exc}", ) from exc
        return raw

    async def _call_with_retry(
        self, prompt: str, model: str, use_json_mode: bool, max_retries: int
    ) -> str:
        last_exc: Exception | None = None
        async with self._semaphore:
            for attempt in range(1, max_retries + 1):
                try:
                    return await self._call_once(prompt, model, use_json_mode)
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    if attempt >= max_retries:
                        break
                    delay = 1.0 * (2 ** (attempt - 1))
                    logger.warning(
                        "[%s] 第 %d 次调用失败(%s),%.0fs 后重试",
                        model, attempt, exc, delay,
                    )
                    await asyncio.sleep(delay)
        raise LLMError(f"调用 {model} 失败,已重试 {max_retries} 次: {last_exc}") from last_exc

    async def _call_once(self, prompt: str, model: str, use_json_mode: bool) -> str:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 8192,
        }
        if use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = await self._client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content
        if not content:
            raise LLMError("LLM 返回空内容")
        return content


_client_instance: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """按 .env 的 LLM_PROVIDER 返回对应客户端(单例)。"""
    global _client_instance
    if _client_instance is not None:
        return _client_instance

    provider = settings.llm_provider.lower()
    if provider == "deepseek":
        _client_instance = OpenAICompatibleClient(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            fast_model=settings.deepseek_fast_model,
            deep_model=settings.deepseek_deep_model,
            provider_name="deepseek",
        )
    elif provider == "openai":
        _client_instance = OpenAICompatibleClient(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            fast_model=settings.openai_fast_model,
            deep_model=settings.openai_deep_model,
            provider_name="openai",
        )
    elif provider == "claude":
        _client_instance = OpenAICompatibleClient(
            api_key=settings.claude_api_key,
            base_url=settings.claude_base_url,
            fast_model=settings.claude_fast_model,
            deep_model=settings.claude_deep_model,
            provider_name="claude",
        )
    elif provider == "qwen":
        _client_instance = OpenAICompatibleClient(
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            fast_model=settings.qwen_fast_model,
            deep_model=settings.qwen_deep_model,
            provider_name="qwen",
        )
    else:
        raise LLMError(f"未知的 LLM_PROVIDER: {provider}(支持 deepseek/openai/claude/qwen)")

    logger.info("LLM provider = %s", provider)
    return _client_instance
