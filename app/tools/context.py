"""工具执行期上下文：把当前会话 id 传给工具，不暴露给模型参数。"""

from contextvars import ContextVar

current_conversation_id: ContextVar[int | None] = ContextVar(
    "current_conversation_id", default=None
)
