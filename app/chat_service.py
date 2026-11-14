"""对话编排：模型定工具 → 执行 → 回灌 → 流式收敛，并落库。"""

from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately, trim_messages

from .config import settings
from .llm import llm
from .prompts import render_system_prompt
from .repositories import add_message, create_conversation, get_conversation, load_history
from .tools import TOOLS, execute_tool

model_with_tools = llm.bind_tools(TOOLS)


def _chunk_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


def _trim_history(messages: list) -> list:
    if not messages:
        return []
    return trim_messages(
        messages,
        max_tokens=settings.token_budget,
        token_counter=count_tokens_approximately,
        strategy="last",
        start_on="human",
        include_system=False,
        allow_partial=False,
    )


def _resolve_conversation(
    session_id: str | None, user_id: str, message: str
) -> tuple[int, list]:
    conversation_id: int | None = None
    if session_id:
        try:
            candidate = int(session_id)
        except (TypeError, ValueError):
            candidate = None
        if candidate and get_conversation(candidate):
            conversation_id = candidate

    if conversation_id is None:
        conversation_id = create_conversation(user_id)

    history = _trim_history(load_history(conversation_id))
    add_message(conversation_id, "user", message)
    return conversation_id, history


async def stream_chat(
    session_id: str | None, user_id: str, message: str
) -> AsyncIterator[tuple[str, dict]]:
    conversation_id, history = _resolve_conversation(session_id, user_id, message)
    yield "meta", {"session_id": str(conversation_id)}

    messages = [
        SystemMessage(content=render_system_prompt()),
        *history,
        HumanMessage(content=message),
    ]

    gathered = None
    try:
        async for chunk in model_with_tools.astream(messages):
            gathered = chunk if gathered is None else gathered + chunk
            text = _chunk_text(chunk.content)
            if text:
                yield "token", {"content": text}
    except Exception as exc:
        yield "error", {"message": f"生成失败：{exc}"}
        return

    tool_calls = gathered.tool_calls if gathered is not None else []
    if not tool_calls:
        reply = _chunk_text(gathered.content) if gathered is not None else ""
        add_message(conversation_id, "assistant", content=reply or None)
        yield "done", {"content": reply}
        return

    # 本章只做单轮调用：只执行模型给出的第一个工具
    call = tool_calls[0]
    yield "tool", {"name": call["name"], "args": call["args"], "phase": "start"}
    result, ok = await execute_tool(call["name"], call["args"], conversation_id)
    yield "tool", {"name": call["name"], "phase": "done", "ok": ok}

    preamble = _chunk_text(gathered.content)
    ai_message = AIMessage(content=preamble, tool_calls=[call])
    add_message(
        conversation_id,
        "assistant",
        content=preamble or None,
        tool_calls=[{"id": call["id"], "name": call["name"], "args": call["args"]}],
    )
    add_message(conversation_id, "tool", content=result, tool_call_id=call["id"])

    followup = messages + [
        ai_message,
        ToolMessage(content=result, tool_call_id=call["id"], name=call["name"]),
    ]
    reply_parts: list[str] = []
    try:
        async for chunk in llm.astream(followup):
            text = _chunk_text(chunk.content)
            if text:
                reply_parts.append(text)
                yield "token", {"content": text}
    except Exception as exc:
        yield "error", {"message": f"生成失败：{exc}"}
        return

    reply = "".join(reply_parts)
    add_message(conversation_id, "assistant", content=reply or None)
    yield "done", {"content": reply}
