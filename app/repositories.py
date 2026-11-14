"""数据访问层：会话、消息、FAQ、工单。"""

import random
from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from .db import SessionLocal
from .models import Conversation, Faq, Message, Ticket


def create_conversation(user_id: str) -> int:
    with SessionLocal() as db:
        conversation = Conversation(user_id=user_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation.id


def get_conversation(conversation_id: int) -> bool:
    with SessionLocal() as db:
        return db.get(Conversation, conversation_id) is not None


def add_message(
    conversation_id: int,
    role: str,
    content: str | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    tool_call_id: str | None = None,
) -> None:
    with SessionLocal() as db:
        db.add(
            Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                tool_calls=tool_calls,
                tool_call_id=tool_call_id,
            )
        )
        db.commit()


def load_history(conversation_id: int) -> list[BaseMessage]:
    with SessionLocal() as db:
        rows = db.scalars(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.role.in_(("user", "assistant")),
            )
            .order_by(Message.id)
        ).all()

    history: list[BaseMessage] = []
    for row in rows:
        # 跳过 assistant 的纯工具调用消息，避免出现孤立的 tool_calls
        if row.tool_calls or not row.content:
            continue
        if row.role == "user":
            history.append(HumanMessage(content=row.content))
        else:
            history.append(AIMessage(content=row.content))
    return history


def search_faq(keyword: str, limit: int = 5) -> list[dict[str, str]]:
    pattern = f"%{keyword}%"
    with SessionLocal() as db:
        rows = db.scalars(
            select(Faq)
            .where(
                or_(
                    Faq.question.like(pattern),
                    Faq.answer.like(pattern),
                    Faq.category.like(pattern),
                )
            )
            .limit(limit)
        ).all()
        return [
            {"question": row.question, "answer": row.answer, "category": row.category}
            for row in rows
        ]


def insert_ticket(conversation_id: int, description: str, ticket_type: str) -> dict[str, str]:
    for _ in range(5):
        ticket_no = f"T{datetime.now():%Y%m%d}{random.randint(0, 9999):04d}"
        with SessionLocal() as db:
            db.add(
                Ticket(
                    ticket_no=ticket_no,
                    conversation_id=conversation_id,
                    description=description,
                    ticket_type=ticket_type,
                    status="待处理",
                )
            )
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                continue
            return {
                "ticket_no": ticket_no,
                "ticket_type": ticket_type,
                "status": "待处理",
            }
    raise RuntimeError("工单号生成冲突，请重试")
