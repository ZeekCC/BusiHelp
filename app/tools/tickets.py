"""人工工单工具：写入 tickets 表。"""

from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..repositories import insert_ticket
from .context import current_conversation_id


class CreateTicketArgs(BaseModel):
    description: str = Field(description="问题描述，包含用户诉求和已知信息")
    ticket_type: Literal["售后", "投诉", "咨询"] = Field(description="工单类型")


@tool("create_ticket", args_schema=CreateTicketArgs)
def create_ticket(description: str, ticket_type: str) -> dict:
    """创建人工工单并转接人工客服。"""
    conversation_id = current_conversation_id.get()
    if conversation_id is None:
        raise ValueError("缺少会话上下文，无法创建工单")
    ticket = insert_ticket(conversation_id, description, ticket_type)
    return {**ticket, "created": True, "message": "工单已创建，将转接人工客服"}
