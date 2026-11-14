"""应用配置：全部来自 .env，遵循 OpenAI 兼容协议。"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    model: str
    temperature: float
    token_budget: int
    disable_thinking: bool


def load_settings() -> Settings:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("缺少 OPENAI_API_KEY，请先在 .env 中配置")
    return Settings(
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1"),
        api_key=api_key,
        model=os.getenv("OPENAI_MODEL", "deepseek-flash"),
        temperature=float(os.getenv("TEMPERATURE", "0.3")),
        token_budget=int(os.getenv("CHAT_TOKEN_BUDGET", "800")),
        disable_thinking=os.getenv("DISABLE_THINKING", "true").lower() == "true",
    )


settings = load_settings()
