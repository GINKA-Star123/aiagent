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

推荐阶段名：

| 阶段 | 说明 |
| --- | --- |
| `runtime_init` | runtime 初始化 |
| `state_graph` | 状态分析 |
| `planner_graph` | 回复规划 |
| `rag_graph` | RAG 检索 |
| `memory_graph` | 记忆检索或写入 |
| `vision_graph` | 视觉分析 |
| `llm_graph` | 主 LLM 回复 |
| `tts` | 语音合成 |
| `live2d` | Live2D payload 生成 |

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
