# 会话与回合边界（session / turn）

对应 `docs/next-stage-optimization-roadmap.md` 5.3。

## 一、五个标识

| 标识 | 含义 | 生成方 | 生命周期 | 典型值 |
| --- | --- | --- | --- | --- |
| `user_id` | 用户身份，长期记忆的 owner | 客户端 / 路由入参 | 长期 | `test-user` |
| `session_id` | 一次会话 | 路由显式传入，缺省由 SessionManager 推导 | 一次会话 | `s-2026-07-01-001` |
| `turn_id` | 一次输入输出回合 | `SessionManager.resolve_turn_id()` | 一轮 | `s-2026-07-01-001:9f3c1a2b` |
| `request_id` | 一次 HTTP 请求 | `apps/api` 中间件 | 单请求 | 32 位 hex |
| `output_id` | 一次输出事件 | `OutputEvent` 默认 uuid | 单输出 | uuid4 |

关系：一个 `user_id` 可有多个 `session_id`；一个 `session_id` 有多个 `turn_id`；
一次 `turn_id` 通常对应一次 `request_id`，但语音链路的多个请求可能属于同一回合。

## 二、解析优先级

`session_id`：

1. `InputEvent.session_id`（显式，推荐）
2. `InputEvent.metadata["session_id"]`（旧客户端兼容）
3. `f"{event.source}:{event.user_id}"`（历史行为，兜底）

`turn_id`：

1. `InputEvent.turn_id`（显式，语音链路传 `{call_id}:{turn_count}`）
2. `InputEvent.metadata["turn_id"]`（兼容）
3. `f"{session_id}:{uuid4().hex[:8]}"`（自动生成）

## 三、各端映射

| 端 | session_id | turn_id |
| --- | --- | --- |
| Flutter 文本聊天 | 客户端生成并持久化（"新会话"时更换） | 留空，服务端生成 |
| Flutter 多模态 | 同上 | 留空 |
| 语音通话 | `call_id` | `{call_id}:{turn_count}`（与 VoiceRealtimeCallStore 的 `last_turn_id` 一致） |
| Qt 调试端 | `qt-debug` | 留空 |

## 四、落地位置

- 契约字段：`aiagent/schemas/inputs.py`
- 解析逻辑：`aiagent/orchestrator/session_manager.py`
- 贯穿点：`aiagent/orchestrator/dispatcher.py` → `aiagent/graphs/main_graph.py`
- 记忆写入：`aiagent/graphs/memory_graph.py`（`session_id` / `turn_id` 已是其 state 字段）
- 响应回显：`main_graph.run_debug()` 写入 `metadata["session_id"] / metadata["turn_id"]`

## 五、短期上下文的隔离策略（已实现）

- **隔离键是 `session_id`**：`user_id` 只用于身份与长期记忆；
- `dispatcher.handle_input()` 解析出 `session_id` / `turn_id` 后**回填到 `InputEvent`**，
  下游统一读 `event.session_id` / `event.turn_id`；
- `ConversationState.recent_dialogue_pairs(session_id=...)` 按会话过滤，
  并优先按 `turn_id` 配对（当前轮尚未产生回复时会被跳过）；
- `LLMRunner` 的 LangGraph `thread_id` = `session_id`，
  因此短期摘要与消息历史按会话隔离；
- `LLMRunner` 维护 `thread_id -> user_id` 映射，
  `clear_user_threads(user_id)` 可一次清掉该用户的所有会话上下文，
  `runtime.clear_user_memories()` 已切到这个新接口。

## 六、已知限制（下一阶段处理）

1. **checkpointer 是进程内 `InMemorySaver`**：
   云模式 `uvicorn --workers 2`（见 `deploy/Dockerfile.api`）下同一会话的不同请求
   可能落到不同 worker，短期上下文会"跳"。解决方向：换成 Redis/SQLite checkpointer，
   或在网关做会话粘性路由（归入 roadmap 第九节 云部署优化）。
2. **`ConversationState` 仍是单进程内存**：多实例部署时会话话题/关键词状态同样不共享。
3. **长期记忆不受影响**：它在 Qdrant/Mem0 里按 `user_id` 存储，天然跨会话、跨实例。
