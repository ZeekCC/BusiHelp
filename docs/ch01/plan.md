# ch01 开发计划

## 目录结构

```text
BusiHelp/
├─ app/
│  ├─ __init__.py
│  ├─ config.py      # .env 读取与配置项
│  ├─ prompts.py     # PromptTemplate 系统提示词
│  ├─ schemas.py     # 请求体与结构化输出模型
│  ├─ session.py     # 内存会话 + token 预算裁剪
│  ├─ llm.py         # ChatOpenAI 工厂
│  └─ main.py        # FastAPI 路由与 SSE
├─ docs/ch01/        # spec.md、plan.md
├─ dev-notes/ch01.md # 过程留痕
├─ requirements.txt
├─ .env.example
└─ .env              # 本地密钥，不提交
```

## 任务拆解

| 编号 | 任务 | 完成标准 |
| --- | --- | --- |
| T1 | 配置层：`.env` / `.env.example` / `config.py` / `requirements.txt` | 启动时能读到 base_url、model、key |
| T2 | Prompt 层：客服角色与行为约束模板 | 模板可渲染出 system 文本 |
| T3 | 会话层：内存存储 + `trim_messages` token 裁剪 | 超预算历史被裁剪且以 human 开头 |
| T4 | 对话接口：`POST /chat/stream` SSE | 逐 token 输出，事件顺序 meta → token* → done |
| T5 | 结构化接口：`POST /extract` | 返回三字段 JSON，方法为 function_calling |
| T6 | 验收测试 | 三条验收标准全部通过并留证据 |

## 验证方式

1. 启动：`.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000`
2. 流式：`curl -N -X POST http://127.0.0.1:8000/chat/stream -H "Content-Type: application/json" -d "{\"message\":\"你好\"}"`
3. 两轮上下文：同一 `session_id` 先报名字再追问
4. 结构化：`curl -X POST http://127.0.0.1:8000/extract ...`

## 评审要点

- 不引入本阶段不需要的抽象与依赖
- 所有外部库用法以 Context7 / 实际安装版本签名为准
- 错误必须通过 SSE `error` 事件或 HTTP 状态码显式暴露
