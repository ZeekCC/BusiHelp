# ch01 规格说明：电商智能客服（纯对话）

## 1. 目标

跑通电商智能客服的最小闭环：多轮对话 + SSE 流式输出 + 售后信息结构化抽取。
本阶段只做纯对话，不引入工具调用与 Agent 循环。

## 2. 范围

### 做

| 能力 | 说明 |
| --- | --- |
| 对话接口 | `POST /chat/stream`，SSE 逐 token 推送，支持多轮 |
| Prompt 管理 | 用 `PromptTemplate` 模板化系统提示词，含客服角色设定与行为约束 |
| 结构化输出 | `POST /extract`，用 `with_structured_output` 抽取订单号、诉求类型、期望方案 |
| 上下文控制 | 进程内会话历史 + 基于 token 预算的历史裁剪 |

### 不做

- 工具调用、Agent 循环、RAG、订单系统对接
- 持久化存储（数据库/Redis）
- 鉴权、限流、前端页面

## 3. 技术约束

- Python + FastAPI + LangChain（`langchain-openai`）
- 模型统一走 OpenAI 兼容协议，`base_url` / `model` / `api_key` 全部来自 `.env`
- 当前配置：`https://api.deepseek.com/v1` + `deepseek-flash`
- 会话上下文保存在进程内存，服务重启即清空（本阶段边界）

## 4. 接口契约

### GET /health

返回 `{"status": "ok", "model": "...", "base_url": "..."}`，用于确认配置生效。

### POST /chat/stream

请求：

```json
{"session_id": "可选，不传则新建", "message": "用户输入"}
```

响应：`text/event-stream`

| event | data | 说明 |
| --- | --- | --- |
| `meta` | `{"session_id": "..."}` | 首个事件，回传会话 ID |
| `token` | `{"content": "增量文本"}` | 逐 token 增量 |
| `done` | `{"content": "完整回复"}` | 结束事件 |
| `error` | `{"message": "..."}` | 异常信息 |

### POST /extract

请求：

```json
{"text": "昨天买的耳机左耳没声音，订单号 20241114001，我要换货"}
```

响应：

```json
{
  "order_no": "20241114001",
  "request_type": "换货",
  "expected_solution": "希望更换一副新的耳机"
}
```

字段约定：

- `order_no`：订单号，未提及为 `null`
- `request_type`：退款 / 退货退款 / 换货 / 补发 / 物流异常 / 发票 / 其他
- `expected_solution`：用户期望方案的原文摘要

## 5. 验收标准

1. `curl` 调用 `/chat/stream` 能看到逐 token 流式回复
2. 同一 `session_id` 连续问两轮，第二轮能接住第一轮的上下文
3. 发送售后描述，`/extract` 返回包含三个字段的结构化 JSON

## 6. 关键决策

| 决策 | 结论 | 依据 |
| --- | --- | --- |
| SSE 实现 | FastAPI 原生 `fastapi.sse.EventSourceResponse` | Context7 查到的当前官方接口，自带 keep-alive / 防缓冲头 |
| 结构化输出方法 | `with_structured_output(..., method="function_calling")` | DeepSeek 不支持 `json_schema` |
| 历史裁剪 | `langchain_core.messages.trim_messages` + `count_tokens_approximately` | 官方 token 预算裁剪工具 |
| 会话存储 | 进程内 dict | 本阶段最小实现，重启即失效 |

## 7. 风险

- `deepseek-flash` 的函数调用稳定性需实测；字段缺失时按 `null` / 默认值兜底。
- 进程内会话不支持多 worker 部署，需在后续章节替换。
