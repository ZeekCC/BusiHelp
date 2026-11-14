"""接口请求体与结构化输出模型。"""

from typing import Literal

from pydantic import BaseModel, Field

RequestType = Literal["退款", "退货退款", "换货", "补发", "物流异常", "发票", "其他"]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description="用户本轮输入")
    session_id: str | None = Field(default=None, description="会话 id，不传则新建")
    user_id: str = Field(default="web-user", max_length=64, description="用户标识")


class ExtractRequest(BaseModel):
    text: str = Field(min_length=1, description="用户的售后描述原文")


class AfterSaleInfo(BaseModel):
    order_no: str | None = Field(default=None, description="订单号；未提及则为 null")
    request_type: RequestType = Field(description="诉求类型")
    expected_solution: str = Field(description="用户期望的处理方案摘要")
