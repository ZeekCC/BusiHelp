"""FastAPI 应用：流式对话（含工具链）、结构化抽取与静态页面。"""

from collections.abc import AsyncIterable
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .chat_service import stream_chat
from .config import settings
from .db import engine
from .llm import structured_llm
from .prompts import render_extraction_prompt
from .schemas import AfterSaleInfo, ChatRequest, ExtractRequest

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="电商智能客服 ch02")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/health")
async def health() -> dict[str, str]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    return {
        "status": "ok",
        "model": settings.model,
        "base_url": settings.base_url,
        "db": db_status,
    }


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.post("/chat/stream", response_class=EventSourceResponse)
async def chat_stream(req: ChatRequest) -> AsyncIterable[ServerSentEvent]:
    async for event, data in stream_chat(req.session_id, req.user_id, req.message):
        yield ServerSentEvent(data=data, event=event)


@app.post("/extract", response_model=AfterSaleInfo)
async def extract(req: ExtractRequest) -> AfterSaleInfo:
    extractor = structured_llm.with_structured_output(
        AfterSaleInfo, method="function_calling"
    )
    result = await extractor.ainvoke(render_extraction_prompt(req.text))
    if result is None:
        raise HTTPException(status_code=502, detail="模型未返回可解析的结构化结果")
    return result
