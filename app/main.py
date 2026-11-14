"""FastAPI 应用：流式对话 + 售后信息结构化抽取。"""

from collections.abc import AsyncIterable
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage, SystemMessage

from .config import settings
from .llm import llm, structured_llm
from .prompts import render_extraction_prompt, render_system_prompt
from .schemas import AfterSaleInfo, ChatRequest, ExtractRequest
from .session import SessionStore

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="电商智能客服 ch01")
sessions = SessionStore(token_budget=settings.token_budget)


def _chunk_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "model": settings.model, "base_url": settings.base_url}


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.post("/chat/stream", response_class=EventSourceResponse)
async def chat_stream(req: ChatRequest) -> AsyncIterable[ServerSentEvent]:
    session_id = req.session_id or uuid4().hex
    yield ServerSentEvent(data={"session_id": session_id}, event="meta")

    messages = [
        SystemMessage(content=render_system_prompt()),
        *sessions.history(session_id),
        HumanMessage(content=req.message),
    ]

    parts: list[str] = []
    try:
        async for chunk in llm.astream(messages):
            text = _chunk_text(chunk.content)
            if text:
                parts.append(text)
                yield ServerSentEvent(data={"content": text}, event="token")
    except Exception as exc:
        yield ServerSentEvent(data={"message": f"生成失败：{exc}"}, event="error")
        return

    reply = "".join(parts)
    sessions.append(session_id, req.message, reply)
    yield ServerSentEvent(data={"content": reply}, event="done")


@app.post("/extract", response_model=AfterSaleInfo)
async def extract(req: ExtractRequest) -> AfterSaleInfo:
    extractor = structured_llm.with_structured_output(
        AfterSaleInfo, method="function_calling"
    )
    result = await extractor.ainvoke(render_extraction_prompt(req.text))
    if result is None:
        raise HTTPException(status_code=502, detail="模型未返回可解析的结构化结果")
    return result
