"""工具注册与执行：参数校验、超时、重试、错误兜底。"""

import asyncio
import json

from pydantic import ValidationError

from ..config import settings
from .context import current_conversation_id
from .knowledge import query_faq
from .mock_api import query_logistics, query_order, query_product
from .tickets import create_ticket

TOOLS = [query_order, query_product, query_logistics, query_faq, create_ticket]
TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}


async def execute_tool(name: str, args: dict, conversation_id: int) -> tuple[str, bool]:
    """执行单个工具，返回 (回灌给模型的 JSON 文本, 是否成功)。"""
    tool = TOOLS_BY_NAME.get(name)
    if tool is None:
        return json.dumps({"error": f"未知工具：{name}"}, ensure_ascii=False), False

    token = current_conversation_id.set(conversation_id)
    last_error = "工具执行失败"
    try:
        for attempt in range(settings.tool_retries + 1):
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(tool.invoke, args),
                    timeout=settings.tool_timeout,
                )
                return json.dumps(result, ensure_ascii=False, default=str), True
            except ValidationError as exc:
                return (
                    json.dumps(
                        {"error": "参数校验失败", "detail": exc.errors(include_url=False)},
                        ensure_ascii=False,
                    ),
                    False,
                )
            except asyncio.TimeoutError:
                last_error = f"工具 {name} 执行超时"
            except Exception as exc:
                last_error = f"工具 {name} 执行失败：{exc}"

            if attempt < settings.tool_retries:
                await asyncio.sleep(0.2 * (attempt + 1))
    finally:
        current_conversation_id.reset(token)

    return json.dumps({"error": last_error}, ensure_ascii=False), False
