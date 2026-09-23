# API 可观测性

本文档说明 API 层的请求追踪、耗时记录、响应结构和排错流程。

第四阶段开始，API 层建议统一加入：

- 请求 ID：`request_id`
- 响应耗时：`latency_ms`
- 响应 Header：`x-request-id`、`x-response-time-ms`
- JSON 响应中的 `request_id`
- 后端日志中的请求完成/失败记录

## 目标

API 可观测性用于解决以下问题：

1. 前端报错时，可以快速定位后端日志。
2. PowerShell 测试失败时，可以知道是哪一次请求失败。
3. 多个模块串联时，可以区分 LLM、RAG、Vision、TTS、Live2D 等阶段的耗时。
4. 避免只看到 500 错误，却无法判断是配置、外部服务、模型加载还是业务代码问题。

## 请求 ID

每个请求都应有一个唯一 `request_id`。

客户端可以主动传入：

```text
x-request-id: manual-test-001
```

如果客户端没有传入，后端中间件会自动生成一个 UUID。

推荐格式：

```text
manual-test-001
qt-chat-20260509-001
vision-batch-yzl-0001
```

## 响应 Header

每个 API 响应应包含：

```text
x-request-id: 当前请求 ID
x-response-time-ms: 请求耗时，单位毫秒
```

示例：

```text
x-request-id: 5b5d2c38a6d249708a6cde93058c9a19
x-response-time-ms: 132.41
```

## JSON 响应中的 request_id

使用 `apps.api.response_utils` 返回的接口会自动附加：

```json
{
  "request_id": "5b5d2c38a6d249708a6cde93058c9a19"
}
```

成功响应示例：

```json
{
  "ok": true,
  "reply": "你好。",
  "metadata": {},
  "request_id": "5b5d2c38a6d249708a6cde93058c9a19"
}
```

失败响应示例：

```json
{
  "ok": false,
  "stage": "vision_analyze",
  "error": "The read operation timed out",
  "traceback": "...",
  "request_id": "5b5d2c38a6d249708a6cde93058c9a19"
}
```

## 聊天响应字段约定

`POST /chat` 和 `POST /chat/multimodal` 应保持同一套核心响应字段，便于 Flutter、Qt 和后续客户端复用同一个解析模型：

```json
{
  "ok": true,
  "output_id": "...",
  "reply": "你好。",
  "base_reply_text": "你好。",
  "emotion": "calm",
  "motion": "soft_idle",
  "expression": "gentle",
  "audio_path": "data/cache/mock_tts/example.txt",
  "audio_url": "/audio/example.txt",
  "audio_segments": [],
  "audio_segment_urls": [],
  "audio_segment_texts": [],
  "live2d_command_path": "",
  "live2d": {},
  "metadata": {},
  "request_id": "5b5d2c38a6d249708a6cde93058c9a19"
}
```

不要新增拼写不同的平行字段，例如 `replt`、`audio_segments_texts`。客户端应以 `reply`、`audio_segment_texts`、`live2d` 为准。

## 日志格式

请求成功或正常返回时：

```text
request completed request_id=5b5d2c38a6d249708a6cde93058c9a19 method=POST path=/chat status_code=200 latency_ms=132.41
```

请求抛出未捕获异常时：

```text
request failed request_id=5b5d2c38a6d249708a6cde93058c9a19 method=POST path=/chat latency_ms=132.41
```

注意：

- 如果 route 内部捕获异常并返回 JSON 500，中间件会记录 `request completed`，状态码为 `500`。
- 如果异常没有被 route 捕获，中间件会记录 `request failed`，并继续抛出异常给 FastAPI。

## 推荐日志字段

后续模块日志建议尽量包含以下字段：

| 字段 | 说明 |
| --- | --- |
| `request_id` | 请求 ID |
| `user_id` | 用户 ID |
| `stage` | 当前阶段 |
| `provider` | 外部服务 provider |
| `model` | 模型名称 |
| `latency_ms` | 阶段耗时 |
| `status` | 阶段状态 |
| `error` | 错误信息 |

图编排相关的 metadata 统一建议遵循同一口径：

```text
<stage>_status
<stage>_latency_ms
<stage>_skip_reason
<stage>_error
```

其中 `status` 只保留少量稳定值，例如 `started`、`done`、`skipped`、`failed`。

推荐阶段名：

| 阶段 | 说明 |
| --- | --- |
| `main_graph` | 主图总耗时与总状态 |
| `runtime_init` | runtime 初始化 |
| `prepare_context` | 主图上下文准备 |
| `state_graph` | 状态分析 |
| `planner_graph` | 回复规划 |
| `rag_graph` | RAG 检索 |
| `memory_graph` | 记忆检索或写入 |
| `vision_graph` | 视觉分析 |
| `llm_graph` | 主 LLM 回复 |
| `store_memory` | 主图里的记忆写入编排节点 |
| `response_packet` | 主图响应封装 |
| `tts` | 语音合成 |
| `live2d` | Live2D payload 生成 |

## Voice Realtime Metadata

`/voice/realtime/*` 在通用 `request_id` 外，还会返回语音链路专用 metadata。字段命名使用 `voice_` 前缀，避免和主聊天 Graph 的 `tts_status`、`llm_graph_status` 等字段冲突。

核心字段：

| 字段 | 说明 |
| --- | --- |
| `voice_realtime` | 是否为语音实时链路响应 |
| `voice_realtime_call_id` | 当前通话 ID |
| `voice_realtime_turn_id` | 当前语音回合 ID，格式为 `{call_id}:{turn_count}` |
| `voice_realtime_turn_count` | 当前通话内的回合数 |
| `voice_realtime_status` | call 状态：`active`、`ended`、`error` |
| `voice_realtime_phase` | call 阶段：`idle`、`transcribing`、`thinking`、`speaking` 等 |

阶段字段：

| 阶段字段 | 说明 |
| --- | --- |
| `voice_call_start_status` | start 接口状态 |
| `voice_call_end_status` | end 接口状态 |
| `voice_upload_status` / `voice_upload_latency_ms` | 音频上传保存阶段 |
| `voice_asr_status` / `voice_asr_latency_ms` | ASR 转写阶段 |
| `voice_chat_status` / `voice_chat_latency_ms` | 主聊天回复阶段 |
| `voice_tts_status` / `voice_tts_latency_ms` | TTS 输出阶段 |
| `voice_turn_status` / `voice_turn_latency_ms` | 单轮语音 turn 总耗时 |
| `voice_interrupt_status` / `voice_interrupt_latency_ms` | 打断处理阶段 |

空转写约定：

```json
{
  "phase": "empty_turn",
  "transcript": "",
  "reply": "",
  "metadata": {
    "voice_asr_empty": true,
    "voice_turn_empty": true,
    "voice_chat_status": "skipped",
    "voice_chat_skip_reason": "empty_transcript",
    "voice_tts_status": "skipped",
    "voice_tts_skip_reason": "empty_transcript"
  }
}

客户端处理建议：
phase=empty_turn 时不展示助手回复气泡。
voice_tts_status=skipped 时不进入播放状态。
phase=interrupted 时立即停止本地音频播放，并把 UI 状态切回可继续说话。
排障时优先查看 voice_*_status 和 voice_*_latency_ms。

注意：

- 主图的记忆写入编排节点使用 `store_memory_*`，`memory_graph` 内部的真实持久化步骤继续使用 `memory_store_*`。
- 主图和子图都可以在最终返回的 `metadata` 中保留各自的 `*_status` 和 `*_latency_ms`，这样一次请求里可以同时看见“总耗时”和“分阶段耗时”。

## 相关文件

请求上下文：

```text
apps/api/request_context.py
```

请求日志中间件：

```text
apps/api/middleware.py
```

统一响应工具：

```text
apps/api/response_utils.py
```

API 入口：

```text
apps/api/http_server.py
```

运行时诊断：

```text
aiagent/diagnostics/runtime_diagnostics.py
apps/api/routes/diagnostics.py
```

## 验证命令

基础验证：

```powershell
$response = Invoke-WebRequest -Method Get -Uri "http://127.0.0.1:8000/health"
$response.Headers["x-request-id"]
$response.Headers["x-response-time-ms"]
$response.Content
```

传入自定义 request id：

```powershell
$response = Invoke-WebRequest `
  -Method Get `
  -Uri "http://127.0.0.1:8000/health" `
  -Headers @{ "x-request-id" = "manual-test-001" }

$response.Headers["x-request-id"]
$response.Headers["x-response-time-ms"]
$response.Content
```

验证诊断接口：

```powershell
Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/runtime/diagnostics" |
  ConvertTo-Json -Depth 80
```

统一测试：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_all.ps1 -ContinueOnFailure
```

## 排错流程

### 前端报错

1. 从前端错误信息中复制 `request_id`。
2. 在后端日志中搜索该 `request_id`。
3. 查看对应 path、status_code、latency_ms。
4. 如果返回体里有 `stage`，优先检查该阶段。

示例：

```text
request_id=qt-chat-20260509-001
path=/chat/multimodal
status_code=500
stage=vision_graph
```

说明问题大概率发生在视觉分析链路。

### 请求很慢

1. 查看 `x-response-time-ms`。
2. 在后端日志搜索 `request_id`。
3. 判断慢请求路径。
4. 如果是 `/chat/multimodal`，优先检查：
   - 视觉模型耗时
   - 主 LLM 耗时
   - RAG 检索耗时
   - TTS 是否阻塞

### 外部服务失败

先运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_runtime_diagnostics.ps1
```

重点查看：

- `llm_provider`
- `vision_config`
- `rag_embedding`
- `qdrant`
- `tts_config`
- `asr_config`
- `live2d_assets`

## 与统一错误响应的关系

API route 应优先使用：

```python
from apps.api.response_utils import error_response, ok_response
```

成功：

```python
return ok_response(result=result)
```

失败：

```python
return error_response(stage="vision_analyze", exc=exc, status_code=500)
```

这样可以保证：

- JSON 编码统一
- 中文不被转义
- 错误结构统一
- 自动附加 `request_id`

## 注意事项

1. 不要在业务代码里手动生成新的 `request_id`。
2. 不要把 API key、完整 Authorization header 写入日志。
3. 不要在日志里输出完整图片 base64。
4. 大模型 prompt 如需记录，应只记录摘要、长度或 hash。
5. 生产环境可以关闭 traceback 返回，但保留后端日志。

## 后续改进方向

当前第四阶段只做 API 层请求追踪。后续可以继续增加：

1. Graph 阶段耗时统计：
   - `state_graph`
   - `planner_graph`
   - `rag_graph`
   - `vision_graph`
   - `llm_graph`

2. 外部 provider 耗时统计：
   - LLM
   - embedding
   - vision
   - TTS
   - ASR

3. Qt 前端显示：
   - 最近一次请求 ID
   - 最近一次请求耗时
   - failed/degraded 诊断项

4. 文件日志：
   - `logs/api.log`
   - `logs/runtime.log`
   - `logs/errors.log`

5. 结构化 JSON 日志：
   - 方便后续接入 Loki、ELK 或其他日志系统。

## 语音链路与表达层耗时字段（V1.1 新增）

### 语音阶段（由 `mark_voice_stage_done/skipped/failed` 产出）

| 字段 | 含义 | 出现时机 |
| --- | --- | --- |
| `voice_upload_latency_ms` | 音频落盘耗时 | turn 成功上传后 |
| `voice_asr_latency_ms` | ASR 转写耗时 | turn 转写完成后 |
| `voice_chat_latency_ms` | 主图（含 LLM）耗时 | turn 生成回复后 |
| `voice_turn_latency_ms` | 单轮总耗时 | turn 结束时 |
| `voice_tts_latency_ms` | TTS 合成耗时（来源见 `voice_tts_latency_source`） | turn 结束后 |
| `voice_llm_latency_ms` | LLM 节点耗时（来源见 `voice_llm_latency_source`） | turn 结束后 |
| `voice_live2d_latency_ms` | Live2D payload 派发耗时 | turn 结束后 |

### 表达层（由 `TTSDispatcher` / Live2D dispatcher 写入 packet.metadata）

| 字段 | 取值 | 说明 |
| --- | --- | --- |
| `tts_status` | `ok` / `skipped` / `failed` | TTS 结果，失败时 `tts_error` 有效 |
| `tts_latency_ms` | 毫秒字符串 | TTS 合成耗时 |
| `tts_segments` | 整数字符串 | 清理后的实际段数 |
| `tts_empty_segments_dropped` | 整数字符串 | 被丢弃的空段数量 |
| `tts_segment_overlong_count` | 整数字符串 | 超过 `tts_max_segment_chars` 的段数（仅标注，未硬切） |
| `live2d_status` | `ok` / `skipped` / `failed` | Live2D 派发结果 |
| `live2d_latency_ms` | 毫秒字符串 | Live2D 派发耗时 |

### 语音会话标识

| 字段 | 含义 |
| --- | --- |
| `voice_realtime_session_id` | 等于 `call_id`；与主图写入的 `metadata["session_id"]` 一致 |
| `voice_realtime_turn_id` | 等于 `{call_id}:{turn_count}`；与 `metadata["turn_id"]` 一致 |

> 数据流：`TTSDispatcher` → `packet.metadata` → `attach_voice_*` → `VoiceRealtimeCall.metadata` → `/voice/realtime/turn` 响应 `metadata`。

## 视觉可信度与记忆写入字段（V1.1 新增）

### 视觉链路（`/vision/analyze`、`/vision/chat`）

响应体新增：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `result.channels.ocr/scene/character` | object | 三条链路的独立状态：`status`(ok/partial/missing/skipped)、`confidence`、`item_count`、`reason` |
| `result.schema_violations` | array | 视觉模型输出不符合 schema 的记录：`path` / `code` / `detail`（**记录并自动修复，不报错**） |
| `result.memory_decision` | object | 视觉结果能否进长期记忆：`allow` / `reason_code` / `reason` / `categories` |

对应 metadata 键：

| 键 | 含义 |
| --- | --- |
| `vision_schema_violation_count` / `vision_schema_violation_codes` | 违规条数与去重后的 code 列表 |
| `vision_channel_ocr_status` / `_scene_status` / `_character_status` | 三通道状态 |
| `vision_memory_decision_allow` / `_reason_code` / `_reason` | 记忆闸门结论 |
| `vision_safety_sensitive` | 是否判定含敏感内容 |
| `vision_confidence_source` | `character_identity` / `character_candidate_only` / `scene_understanding` / `unknown_image_type` |

角色候选来源：`character_candidates[].source` = `model_confirmed` / `model_only` / `retrieval_only`。
**只有非 `retrieval_only` 的候选才可能进入 `recognized_characters`**——纯图库相似度不再能确认身份。

记忆闸门 `reason_code`：`confirmed_character_identity`、`scene_preference_signal`、`sensitive_content`、
`unknown_image_type`、`unconfirmed_character_identity`、`transient_document_image`、
`possible_real_person_identity`、`model_not_considering`、`low_confidence_scene`、`unsupported_image_type`。

契约自描述：`GET /vision/schema` 返回 schema 版本、支持的图片类型、通道与全部 reason_code。

### 记忆写入链路

| 键 / 端点 | 含义 |
| --- | --- |
| `memory_write_status` / `memory_write_task_id` / `memory_write_async` | 异步写入的入队状态与任务号 |
| `memory_store_dispatch_status` | 调度阶段标记 |
| `GET /memory/write/status` | 队列 `pending` / `running` / `last` / `recent` |
| `GET /memory/user/{user_id}/audit` | 写入审计：`category` / `importance` / `reason` / `source` / `created_at` |

### 索引新鲜度

| 键 | 含义 |
| --- | --- |
| `index_stale` | 索引是否过期 |
| `index_freshness.status` | `fresh` / `stale` / `missing` / `unknown` |
| `index_freshness.reasons[]` | 机器可读原因码（见配置文档） |
| `index_freshness.hint` | 人话建议 |
| `index_manifest_path` / `index_tokenizer_version` | 清单位置与分词版本 |

### 任务队列的 request_id（跨进程链路）

`POST /knowledge/rebuild`（云模式）与 `POST /vision/characters/rebuild` 入队时携带发起方的 `request_id`。

- 任务记录新增：`request_id`、`first_started_at`
- worker 日志：`task succeeded task_id=... worker_id=... attempts=... duration_ms=... result_keys=... [request_id=...]`
- worker 与 API 共用 `setup_logger()`；`LOG_FORMAT=json` 时可直接用同一个 `request_id` 串联两端日志

### 就绪度端点的输出差异

`GET /ready` 为脱敏公共探针（`purpose=public`，无 details/action）；
`GET /cloud/ops/readiness` 为运维详情（`purpose=ops`，需 `x-cloud-admin-token`）。详见 `docs/config-reference.md`。