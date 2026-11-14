"""ChatOpenAI 客户端：统一走 OpenAI 兼容协议，配置全部来自 .env。"""

from langchain_openai import ChatOpenAI

from .config import settings

_common = dict(
    model=settings.model,
    api_key=settings.api_key,
    base_url=settings.base_url,
    temperature=settings.temperature,
    timeout=60,
    max_retries=2,
)

llm = ChatOpenAI(**_common)

# DeepSeek 思考模式不支持强制 tool_choice，结构化抽取需要单独关闭思考模式
structured_llm = ChatOpenAI(
    **_common,
    extra_body={"thinking": {"type": "disabled"}} if settings.disable_thinking else None,
)
