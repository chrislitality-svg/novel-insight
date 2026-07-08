"""配置加载,全部来自 .env(pydantic-settings)。代码里严禁硬编码 API Key。"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录(本文件位于 app/ 下,父目录的父目录即根)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BOOKS_DIR = DATA_DIR / "books"
EXPORTS_DIR = DATA_DIR / "exports"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # provider 选择
    llm_provider: str = "deepseek"

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_fast_model: str = "deepseek-chat"
    deepseek_deep_model: str = "deepseek-reasoner"

    # OpenAI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_fast_model: str = "gpt-4o-mini"
    openai_deep_model: str = "gpt-4o"

    # Claude(OpenAI 兼容端点)
    claude_api_key: str = ""
    claude_base_url: str = "https://api.anthropic.com/v1"
    claude_fast_model: str = "claude-haiku-4-5"
    claude_deep_model: str = "claude-sonnet-4-6"

    # Qwen(阿里云 DashScope OpenAI 兼容端点)
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_fast_model: str = "qwen3.6-plus"
    qwen_deep_model: str = "qwen3.6-plus"

    # 调用控制
    llm_concurrency: int = 5
    llm_timeout: int = 120
    llm_max_retries: int = 3

    # 分析参数
    density_threshold: float = 30.0

    # 数据库
    database_url: str = "sqlite+aiosqlite:///./data/novel_insight.db"


@lru_cache
def get_settings() -> Settings:
    # 确保数据目录存在
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return Settings()


settings = get_settings()
