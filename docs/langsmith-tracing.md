# LangSmith Tracing

项目已接入 LangSmith，可追踪完整聊天链路、LangGraph 节点、TTS 和 Live2D。

## 配置

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<your-api-key>
LANGSMITH_PROJECT=aiagent
LANGSMITH_HIDE_INPUTS=true
LANGSMITH_HIDE_OUTPUTS=true
```

不要提交真实 API Key。以上变量必须存在于启动后端的进程环境中；仅将未知的 `LANGSMITH_*` 字段写入 `.env`，不保证 LangSmith SDK 能读取到它们。

## 启动与验证

```powershell
uv sync
uv run python -m uvicorn apps.api.http_server:app --host 127.0.0.1 --port 8000
```

触发 Trace：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/chat" `
  -ContentType "application/json" `
  -Body '{"user_id":"trace-test","username":"tester","text":"你好"}'
```

随后在 LangSmith 中打开：

```text
Tracing → aiagent → 最新的 agent_turn
```

预期结构：

```text
agent_turn
├── LangGraph
│   ├── prepare_context
│   ├── run_vision_graph
│   ├── retrieve_memory
│   ├── run_state_graph
│   ├── run_planner_graph
│   ├── run_rag_graph
│   ├── run_llm_graph
│   ├── store_memory
│   └── build_response_packet
├── tts
└── live2d
```

通过各 Run 的 `Latency` 和错误状态，可以判断瓶颈位于 Vision、Memory、State、Planner、RAG、LLM、TTS 或 Live2D。

纯文本请求会跳过 Vision；Mock/Noop Live2D 不一定产生 `live2d` Run。根 Trace 成功也可能包含可选模块降级，应结合 metadata 和后端日志判断。

## 关闭追踪

```env
LANGSMITH_TRACING=false
```
