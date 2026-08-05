# V1.0 最终 Smoke 指令

本文件只收集 V1.0 收尾验证指令。本轮文档收尾不执行这些命令；发布前由人工在目标环境中按需执行。

## 使用约定

- Windows 本地默认使用 PowerShell。
- 本地 smoke 默认使用 mock provider，目标是验证主链路、API contract、响应结构和降级行为。
- RAG baseline 依赖 `data/knowledge/public`。如果该目录不存在，`tests\rag` 会按测试条件跳过。
- 真实 `.env` 与 `cloud.tencent.env` 只能保留在本机或部署机器，不提交到仓库。
- 管理接口读取 `CLOUD_ADMIN_TOKEN`，请求头统一使用 `x-cloud-admin-token`。
- 如果 `CLOUD_ADMIN_TOKEN` 未配置，管理接口应返回 `503`，这是预期的安全行为。

## 1. 本地配置准备

仅当本地还没有 `.env` 时，从模板生成：

```powershell
cd F:\aiagent
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

本地 mock smoke 建议确认 `.env` 至少保持：

```env
CLOUD_MODE=false
LLM_PROVIDER=mock
ENABLE_MOCK_LLM=true
TTS_PROVIDER=mock
ENABLE_MOCK_TTS=true
ASR_PROVIDER=mock
ENABLE_MOCK_ASR=true
VISION_PROVIDER=mock
LIVE2D_PROVIDER=mock
```

如果需要手动验证管理接口，在启动 API 前为本地进程设置临时 token：

```powershell
$env:CLOUD_ADMIN_TOKEN = "local-smoke-admin-token"
```

## 2. 后端 Unit / API Contract / Smoke

```powershell
cd F:\aiagent
.\.venv\Scripts\python.exe -m pytest -q tests\unit tests\api tests\smoke -p no:cacheprovider
```

验收重点：

- `tests\unit` 验证纯函数、schema、metadata、capability、memory、vision、Live2D payload 等局部行为。
- `tests\api` 固化 FastAPI contract，包括 `/health`、`/ready`、`/runtime/*`、`/chat`、`/session/open`、`/voice/realtime/*`、cloud admin 接口。
- `tests\smoke` 验证 mock runtime 能构建并完成最小聊天链路。

## 3. RAG 检索质量基线

```powershell
cd F:\aiagent
.\.venv\Scripts\python.exe -m pytest -q tests\rag -p no:cacheprovider
```

验收重点：

- `tests\fixtures\rag_eval\cases.jsonl` 可以被正常加载。
- `data/knowledge/public` 存在时，BM25 baseline 应满足当前阈值。
- 如果本地没有知识库目录，该组测试跳过，不代表生产 RAG 已验收。

## 4. 启动本地 Mock API

在一个独立 PowerShell 窗口中启动服务：

```powershell
cd F:\aiagent
$env:LLM_PROVIDER = "mock"
$env:ENABLE_MOCK_LLM = "true"
$env:TTS_PROVIDER = "mock"
$env:ENABLE_MOCK_TTS = "true"
$env:ASR_PROVIDER = "mock"
$env:ENABLE_MOCK_ASR = "true"
$env:VISION_PROVIDER = "mock"
$env:LIVE2D_PROVIDER = "mock"
$env:CLOUD_ADMIN_TOKEN = "local-smoke-admin-token"
.\.venv\Scripts\python.exe -m uvicorn apps.api.http_server:app --host 127.0.0.1 --port 8000
```

## 5. 基础健康与 Runtime 状态

在另一个 PowerShell 窗口中执行：

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/live" | ConvertTo-Json -Depth 20
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health" | ConvertTo-Json -Depth 20
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/ready" | ConvertTo-Json -Depth 20
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/runtime/capabilities" | ConvertTo-Json -Depth 40
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/runtime/diagnostics" | ConvertTo-Json -Depth 80
```

验收重点：

- `/live` 返回进程存活。
- `/health` 返回 `status=ok`，并包含 `cloud_mode`。
- `/ready` 返回 readiness checks。
- `/runtime/capabilities` 返回 capability `status`、`summary`、`items`。
- `/runtime/diagnostics` 能说明模块是否 ready、degraded 或 unavailable。

## 6. Chat 最小手动请求

```powershell
$chatBody = @{
  user_id = "smoke-user"
  username = "Smoke"
  text = "你好，请用一句话回应。"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/chat" `
  -ContentType "application/json" `
  -Body $chatBody |
  ConvertTo-Json -Depth 40
```

验收重点：

- 返回结构符合统一 ok response。
- `reply` / `base_reply_text` 不为空。
- `metadata` 中包含 graph/runtime 相关信息。
- mock 模式下允许内容简短，但不应抛出 500。

## 7. Session Open 手动请求

```powershell
$sessionBody = @{
  user_id = "smoke-user"
  username = "Smoke"
  entry = "chat_page"
  recent_topic = ""
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/session/open" `
  -ContentType "application/json" `
  -Body $sessionBody |
  ConvertTo-Json -Depth 40
```

验收重点：

- 返回 `opening`、`presence`、`live2d`、`memory`。
- `opening.text` 可用于首屏开场。
- `live2d.expression` 与 `live2d.motion` 可被移动端消费。

## 8. Voice Realtime Start / State / End

```powershell
$voiceStartBody = @{
  user_id = "smoke-user"
  username = "Smoke"
} | ConvertTo-Json

$call = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/voice/realtime/start" `
  -ContentType "application/json" `
  -Body $voiceStartBody

$call | ConvertTo-Json -Depth 40

$callId = $call.call_id

Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/voice/realtime/state/$callId" |
  ConvertTo-Json -Depth 40

$voiceEndBody = @{
  call_id = $callId
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/voice/realtime/end" `
  -ContentType "application/json" `
  -Body $voiceEndBody |
  ConvertTo-Json -Depth 40
```

验收重点：

- `start` 返回 `call_id`、`status=active`、`phase=idle`。
- `state` 返回同一个 `call_id`，并包含 `turn_count`、`last_seen_at`。
- `end` 返回 `status=ended`、`phase=completed`。

## 9. 管理接口 Smoke

本地 API 启动时必须已经设置同一个 `CLOUD_ADMIN_TOKEN`：

```powershell
$adminHeaders = @{
  "x-cloud-admin-token" = "local-smoke-admin-token"
}

Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/cloud/ops/readiness" `
  -Headers $adminHeaders |
  ConvertTo-Json -Depth 80

Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/cloud/ops/config-snapshot" `
  -Headers $adminHeaders |
  ConvertTo-Json -Depth 40

Invoke-RestMethod `
  -Method Get `
  -Uri "http://127.0.0.1:8000/cloud/tasks/summary" `
  -Headers $adminHeaders |
  ConvertTo-Json -Depth 40
```

任务入队接口示例：

```powershell
$rebuildBody = @{
  force_rebuild = $true
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/cloud/tasks/knowledge/rebuild" `
  -Headers $adminHeaders `
  -ContentType "application/json" `
  -Body $rebuildBody |
  ConvertTo-Json -Depth 40

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/cloud/tasks/vision-characters/rebuild" `
  -Headers $adminHeaders `
  -ContentType "application/json" `
  -Body $rebuildBody |
  ConvertTo-Json -Depth 40
```

验收重点：

- 无 token 时管理接口不可访问。
- 正确 token 必须使用 `x-cloud-admin-token` header。
- readiness、config snapshot、task summary 不泄漏 secret 明文。

## 10. 云部署 Docker Compose 验证

部署机器上先生成并编辑真实配置：

```powershell
cd F:\aiagent
if (-not (Test-Path cloud.tencent.env)) { Copy-Item cloud.tencent.example.env cloud.tencent.env }
```

确认 `cloud.tencent.env` 中所有 `change-*`、`your-*`、空 secret 都已替换后，再执行：

```powershell
cd F:\aiagent
docker compose --env-file cloud.tencent.env -f deploy/docker-compose.tencent.yml config
docker compose --env-file cloud.tencent.env -f deploy/docker-compose.tencent.yml up -d --build
docker compose --env-file cloud.tencent.env -f deploy/docker-compose.tencent.yml ps
docker compose --env-file cloud.tencent.env -f deploy/docker-compose.tencent.yml logs -f api
docker compose --env-file cloud.tencent.env -f deploy/docker-compose.tencent.yml logs -f worker
```

云端接口检查：

```powershell
$baseUrl = "https://your-domain.example.com"
$adminHeaders = @{
  "x-cloud-admin-token" = "replace-with-production-admin-token"
}

Invoke-RestMethod -Method Get -Uri "$baseUrl/health" | ConvertTo-Json -Depth 20
Invoke-RestMethod -Method Get -Uri "$baseUrl/ready" | ConvertTo-Json -Depth 40
Invoke-RestMethod -Method Get -Uri "$baseUrl/cloud/ops/readiness" -Headers $adminHeaders | ConvertTo-Json -Depth 80
Invoke-RestMethod -Method Get -Uri "$baseUrl/cloud/tasks/summary" -Headers $adminHeaders | ConvertTo-Json -Depth 40
```

验收重点：

- `api` 容器 healthcheck 使用 `/ready`。
- `worker` 容器能连接 Redis、Qdrant、Neo4j。
- `cloud.tencent.env` 中 `CLOUD_ADMIN_TOKEN`、`POSTGRES_PASSWORD`、`NEO4J_PASSWORD`、S3/COS、LLM、ASR、GPU token 均不是占位符。
- 生产真实 provider 下不要保留 mock-only 配置，除非在 release checklist 中明确记录为有意降级。

## 11. Flutter 侧最终指令

以下命令只列为 V1.0 收尾验证入口，本轮不执行：

```powershell
cd F:\aiagent\apps\flutter_client
dart format lib test
flutter analyze
flutter test
flutter build apk --release
```

验收重点：

- 设置页 API 地址指向电脑局域网 IP 或正式域名，不使用手机端的 `127.0.0.1`。
- Chat、Multimodal、Voice realtime、Live2D payload 在真实设备上完成手动闭环。
- release keystore 配置完成；如果 fallback 到 debug signing，只能用于内测。

