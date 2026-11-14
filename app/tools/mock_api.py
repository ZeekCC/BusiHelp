"""订单 / 商品 / 物流工具：演示用 mock 数据，不接真实系统。"""

import random

from langchain_core.tools import tool
from pydantic import BaseModel, Field


class QueryOrderArgs(BaseModel):
    order_id: str = Field(description="订单号，例如 1001")


class QueryProductArgs(BaseModel):
    product_name: str = Field(description="商品名称或关键词，例如 蓝牙耳机")


class QueryLogisticsArgs(BaseModel):
    order_id: str = Field(description="订单号，例如 1001")


@tool("query_order", args_schema=QueryOrderArgs)
def query_order(order_id: str) -> dict:
    """查询订单的当前状态、商品、金额和下单时间。"""
    rng = random.Random(f"order:{order_id}")
    return {
        "order_id": order_id,
        "status": rng.choice(["待发货", "已发货", "已签收", "退款中"]),
        "product": rng.choice(["蓝牙耳机", "机械键盘", "保温杯", "双肩包", "智能手表"]),
        "amount": round(rng.uniform(39, 899), 2),
        "created_at": (
            f"2026-11-{rng.randint(1, 13):02d} "
            f"{rng.randint(9, 21):02d}:{rng.randint(0, 59):02d}"
        ),
    }


@tool("query_product", args_schema=QueryProductArgs)
def query_product(product_name: str) -> dict:
    """查询商品的售价、库存、分类和卖点。"""
    rng = random.Random(f"product:{product_name}")
    return {
        "product_name": product_name,
        "price": round(rng.uniform(29, 699), 2),
        "stock": rng.randint(0, 500),
        "category": rng.choice(["数码配件", "家居日用", "出行装备", "智能穿戴"]),
        "highlights": rng.choice(
            [
                "支持 7 天无理由退货，全国联保一年",
                "现货直发，满 99 元包邮",
                "官方正品，支持开具电子发票",
            ]
        ),
    }


@tool("query_logistics", args_schema=QueryLogisticsArgs)
def query_logistics(order_id: str) -> dict:
    """查询订单对应的快递公司、运单号、当前位置和物流轨迹。"""
    rng = random.Random(f"logistics:{order_id}")
    location = rng.choice(["广州分拨中心", "杭州转运中心", "上海航空部", "北京分拨中心"])
    status = rng.choice(["已揽件", "运输中", "派送中", "已签收"])
    return {
        "order_id": order_id,
        "carrier": rng.choice(["顺丰速运", "中通快递", "圆通速递"]),
        "tracking_no": f"SF{rng.randint(10**11, 10**12 - 1)}",
        "current_status": status,
        "current_location": location,
        "events": [
            {"time": "今天 09:12", "desc": f"快件已到达{location}"},
            {"time": "昨天 21:40", "desc": "快件已从上一站发出"},
            {"time": "昨天 15:05", "desc": "快递员已揽收"},
        ],
    }
