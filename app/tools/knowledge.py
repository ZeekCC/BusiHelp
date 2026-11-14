"""FAQ 工具：按关键词走 SQL LIKE 查询。"""

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..repositories import search_faq


class QueryFaqArgs(BaseModel):
    keyword: str = Field(description="从用户问题中提取的关键词，例如 退货政策、发票、物流时效")


@tool("query_faq", args_schema=QueryFaqArgs)
def query_faq(keyword: str) -> dict:
    """按关键词查询常见问题库，返回匹配的问答对。"""
    items = search_faq(keyword)
    if not items:
        return {
            "keyword": keyword,
            "found": False,
            "items": [],
            "hint": "知识库没有匹配的问答，请如实告知用户未查到，并建议转人工",
        }
    return {"keyword": keyword, "found": True, "items": items}
