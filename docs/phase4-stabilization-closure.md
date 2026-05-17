# 第四阶段收尾报告：稳定化与工程收敛

第四阶段目标是把前三阶段已经完成的能力收敛成可诊断、可测试、可排错、可继续扩展的工程系统。

本阶段不以新增大功能为目标，重点处理：

- 运行时诊断
- 统一测试入口
- API 响应结构统一
- 请求追踪与耗时日志
- 配置文档
- Qt 前端诊断入口
- 后续开发边界说明

## 已完成内容

### 1. 运行时诊断系统

新增：

```text
aiagent/diagnostics/__init__.py
aiagent/diagnostics/models.py
aiagent/diagnostics/runtime_diagnostics.py
apps/api/routes/diagnostics.py
scripts/test_runtime_diagnostics.ps1
```

新增接口：

```text
GET /runtime/diagnostics
```

诊断输出统一使用：

```text
ok
degraded
failed
skipped
```

当前检查范围：

- API 基础配置
- 主聊天 LLM
- State LLM
- Planner LLM
- RAG embedding 配置
- RAG 数据与缓存目录
- Memory 配置
- Qdrant 连通性
- Vision 配置
- Vision 角色图库与索引
- TTS 配置
- ASR 配置
- Live2D provider 配置
- Live2D profile 与模型资源

设计原则：

- 诊断接口不主动构建完整 runtime。
- 可选模块缺失优先标记为 `degraded`，不直接阻断聊天能力。
- 真正影响当前配置运行的缺失项标记为 `failed`。

## 2. 统一测试入口

新增：

```text
scripts/test_all.ps1
```

该脚本用于统一执行：

- `/health`
- `/runtime/diagnostics`
- `/control/status`
- `/knowledge/stats`
- `/vision/characters/stats`
- `/live2d/stats`
- `/live2d/runtime/status`
- 可选完整 smoke 测试
- 可选 Vision 测试
- 可选 Multimodal 测试
- 可选 Live2D 测试

常用命令：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_all.ps1 -ContinueOnFailure
```

完整链路：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_all.ps1 `
  -RunAll `
  -ImagePath "data\characters\luotianyi\images\LUO1.jpg" `
  -ContinueOnFailure
```

## 3. API 响应工具统一

新增：

```text
apps/api/response_utils.py
```

统一方法：

```python
json_response(...)
ok_response(...)
error_response(...)
```

已接入：

```text
apps/api/routes/chat.py
apps/api/routes/multimodal_chat.py
apps/api/routes/vision.py
apps/api/routes/diagnostics.py
apps/api/routes/health.py
```

统一错误结构：

```json
{
  "ok": false,
  "stage": "...",
  "error": "...",
  "traceback": "...",
  "request_id": "..."
}
```

后续新增 route 应直接复用 `apps.api.response_utils`，不要再在 route 内重复写 `_json_response` 或 `_error_response`。

## 4. API 请求追踪与耗时日志

新增：

```text
apps/api/request_context.py
apps/api/middleware.py
docs/api-observability.md
```

接入：

```text
apps/api/http_server.py
```

每个请求会生成或继承：

```text
x-request-id
```

响应 Header：

```text
x-request-id
x-response-time-ms
```

日志字段：

```text
request_id
method
path
status_code
latency_ms
```

用途：

- Qt 前端报错时定位后端日志
- PowerShell 测试失败时定位具体请求
- 后续排查慢请求

## 5. 配置文档

新增并补齐：

```text
docs/config-reference.md
```

覆盖内容：

- 基础配置
- 主聊天 LLM
- State LLM
- Planner LLM
- OpenAI / SiliconFlow / LM Studio
- RAG
- Vision
- Vision 角色识别
- Memory / Qdrant / Neo4j
- TTS
- ASR
- Persona
- Live2D
- 推荐 `.env` 配置组合
- 诊断与测试命令
- 已知编码风险

## 6. Qt 前端诊断入口

修改：

```text
apps/desktop_qt/api_client.py
apps/desktop_qt/chat_window.py
```

新增能力：

- `APIClient.get_runtime_diagnostics()`
- `get_runtime_snapshot()` 包含 diagnostics
- `run_startup_check()` 包含 diagnostics
- Qt 右侧快捷控制新增“运行诊断”按钮
- 诊断结果显示在 `Runtime Snapshot`
- 聊天区展示诊断摘要
- 非 `ok` 项会显示 `name / status / summary / action`

## 当前验收命令

启动 API 后执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_runtime_diagnostics.ps1
```

统一测试：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_all.ps1 -ContinueOnFailure
```

Qt 验证：

```powershell
python apps\desktop_qt\main.py
```

如果系统 PATH 没有 `python`，使用虚拟环境：

```powershell
.\.venv\Scripts\python.exe apps\desktop_qt\main.py
```

## 已知风险

### 1. PowerShell 中文显示乱码

部分中文 Markdown 文件在 PowerShell `Get-Content` 中可能显示乱码，这是终端编码问题。  
文件本身按 UTF-8 保存，建议用 VS Code、PyCharm 或 Typora 查看。

### 2. 源码中仍有历史乱码

当前已发现这些位置可能仍存在历史编码污染：

```text
config/defaults.py
config/settings.py
apps/api/routes/live2d.py
```

建议后续单独做一次“编码清理”任务。

### 3. `__pycache__` 权限问题

当前环境中 `compileall` 可能因为 `__pycache__` 权限报错。  
可用不写 pyc 的源码编译方式做语法检查。

### 4. Live2D 真实模型资源仍缺失

预期路径：

```text
data/live2d/characters/yzl/model/yzl.model3.json
```

如果诊断返回 `degraded` 或 `model3_json_missing`，在模型资源尚未放入时属于预期状态。

## 后续开发边界

新增 HTTP 接口：

```text
apps/api/routes/*
```

新增 API 响应：

```text
apps/api/response_utils.py
```

新增运行时能力：

```text
apps/core/runtime.py
apps/core/bootstrap.py
```

新增图流程：

```text
aiagent/graphs/*
```

新增 Vision 能力：

```text
aiagent/services/vision_service.py
aiagent/vision/*
aiagent/graphs/vision_graph.py
```

新增 Live2D 能力：

```text
aiagent/live2d/*
aiagent/expression/live2d_payload_dispatcher.py
integrations/live2d/*
```

新增 Qt 功能：

```text
apps/desktop_qt/*
```

优先接入现有 `ChatWindow`，不要新建第二个主窗口。

## 第四阶段结论

第四阶段已经完成核心闭环：

- 能诊断
- 能测试
- 能追踪请求
- 能统一错误响应
- 能从 Qt 前端查看诊断
- 有配置文档
- 有可观测性文档

下一阶段不建议继续做大规模横向功能扩展。  
推荐做第五阶段：编码清理、真实资源接入、测试固化与小规模体验优化。
