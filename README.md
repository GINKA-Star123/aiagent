# AIAgent

AIAgent 是一个面向 AI VTuber / Live2D 角色陪伴场景的统一运行时项目。它把对话、长期记忆、RAG、视觉理解、语音输入、TTS、Live2D 表现和多端控制台放在同一个工程里，目标是形成一条可以从本地开发走到移动端 V1.0 的完整链路。

当前手机端已进入 `1.0.0-rc.1+1`。Live2D 过渡模型已能在 Android 真机显示和运动，正式模型资源交付后再替换复测。

## 项目结构

```text
aiagent/              核心智能体、图流程、状态、记忆、知识库、Live2D payload
apps/api/             FastAPI HTTP 服务与路由
apps/core/            Runtime 构建与本地命令行入口
apps/desktop_qt/      Qt 桌面调试端
apps/flutter_client/  Flutter 手机端，当前 V1.0 RC 重点
apps/web/             Next.js Web 控制台
config/               统一配置和默认值
domain/               领域模型和业务规则
integrations/         LLM / ASR / TTS / Live2D / 音频等外部集成
data/                 本地资源、模型、缓存、上传、日志，默认不入仓
docs/                 架构、配置、观测性和阶段文档
scripts/              PowerShell 测试与资源工具，当前本地忽略
tests/                Python 单元和集成测试
```

注意：根 `.gitignore` 当前忽略了 `data/`、`scripts/`、`apps/flutter_client/` 等本地资产目录。它们是当前工作区的重要组成，但默认不会出现在 `git status` 中。

## 能力概览

- 文本聊天：`/chat`
- 图片多模态聊天：`/chat/multimodal`
- 语音转写与语音回合：`/voice/transcribe`、`/voice/turn`
- TTS 输出与手机端播放
- 长期记忆：Mem0 + Qdrant，可读取、搜索、清空
- RAG：本地文档切块、混合检索、重建索引
- 视觉理解：图片分析、角色图库索引、视觉上下文进入对话
- Live2D：后端 payload 协议、资源扫描、预览、移动端 WebView 舞台
- 可观测性：`request_id`、响应耗时、统一错误结构、运行时诊断
- 多端入口：FastAPI、Flutter、Qt、Next.js Web

## 环境要求

- Python `3.11+`
- Flutter SDK，Android 真机或模拟器
- Node.js，供 `apps/web` 使用
- 可选服务：Qdrant、Neo4j、GPT-SoVITS / IndexTTS2 / VoxCPM、faster-whisper、本地或远程 LLM

开发环境建议使用项目根目录的虚拟环境：

```powershell
cd F:\aiagent
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

如果使用 `uv`，也可以按本机习惯同步 `pyproject.toml` / `uv.lock`。

## 配置

复制 `.env.example` 到 `.env`，再按需要切换 mock 或真实 provider：

```powershell
cd F:\aiagent
Copy-Item .env.example .env
```

最小开发配置可以保持 mock：

```env
LLM_PROVIDER=mock
ENABLE_MOCK_LLM=true
TTS_PROVIDER=mock
ENABLE_MOCK_TTS=true
ASR_PROVIDER=mock
ENABLE_MOCK_ASR=true
```

真实模型、RAG、Vision、Memory、TTS、ASR、Live2D 的详细配置见 [docs/config-reference.md](docs/config-reference.md)。

## 启动后端 API

```powershell
cd F:\aiagent
.\.venv\Scripts\Activate.ps1
python -m uvicorn apps.api.http_server:app --host 0.0.0.0 --port 8000 --reload
```

常用检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/runtime/diagnostics | ConvertTo-Json -Depth 80
```

API 入口文件是 [apps/api/http_server.py](apps/api/http_server.py)，运行时构建入口是 [apps/core/bootstrap.py](apps/core/bootstrap.py)。

## Flutter 手机端

手机端是当前 V1.0 RC 的主交付入口：

```powershell
cd F:\aiagent\apps\flutter_client
flutter pub get
flutter run
```

真机调试时，设置页里的 API 地址必须填写电脑局域网 IP，例如：

```text
http://192.168.x.x:8000
```

不要在手机端填 `127.0.0.1`，那会指向手机自己。

RC 检查命令：

```powershell
cd F:\aiagent\apps\flutter_client
dart format lib test
flutter analyze
flutter test
flutter build apk --release
```

手机端文档：

- [apps/flutter_client/README.md](apps/flutter_client/README.md)
- [apps/flutter_client/docs/v1-release-checklist.md](apps/flutter_client/docs/v1-release-checklist.md)
- [apps/flutter_client/docs/v1-rc-release-notes.md](apps/flutter_client/docs/v1-rc-release-notes.md)
- [apps/flutter_client/docs/live2d-mobile-loading.md](apps/flutter_client/docs/live2d-mobile-loading.md)

Android release 构建会读取 `apps/flutter_client/android/key.properties`。没有 release keystore 时会 fallback 到 debug signing，只适合内测安装。

## Web 控制台

```powershell
cd F:\aiagent\apps\web
npm install
npm run dev
```

Web 端目前是控制台骨架，模块文档分布在 `apps/web/src/features/*/README.md`。构建命令：

```powershell
npm run build
```

## Qt 桌面调试端

```powershell
cd F:\aiagent
.\.venv\Scripts\python.exe apps\desktop_qt\main.py
```

Qt 端适合本地调试聊天、运行时快照、Live2D payload 和诊断结果。相关入口：

- [apps/desktop_qt/main.py](apps/desktop_qt/main.py)
- [apps/desktop_qt/chat_window.py](apps/desktop_qt/chat_window.py)
- [apps/desktop_qt/live2d_debug_window.py](apps/desktop_qt/live2d_debug_window.py)

## API 速览

| 路径 | 用途 |
| --- | --- |
| `GET /health` | 健康检查 |
| `GET /runtime/diagnostics` | 运行时诊断 |
| `POST /chat` | 文本聊天 |
| `POST /chat/multimodal` | 图片 + 文本聊天 |
| `GET /memory/user/{user_id}` | 读取用户记忆 |
| `DELETE /memory/user/{user_id}` | 清空用户记忆 |
| `POST /voice/transcribe` | 上传音频转写 |
| `POST /voice/turn` | 语音回合 |
| `POST /vision/analyze` | 图片分析 |
| `POST /vision/characters/rebuild` | 重建角色图库索引 |
| `GET /knowledge/stats` | RAG 状态 |
| `POST /knowledge/rebuild` | 重建 RAG 索引 |
| `GET /live2d/stats` | Live2D 资源状态 |
| `POST /live2d/preview` | Live2D payload 预览 |

API 请求追踪、`request_id` 和错误结构见 [docs/api-observability.md](docs/api-observability.md)。

## 测试与诊断

Python 侧测试：

```powershell
cd F:\aiagent
pytest
```

当前 `tests/` 目录如果没有可见的 `.py` 测试源码，可以跳过 `pytest`，优先使用下面的运行时诊断和 API smoke 脚本。

运行时诊断：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_runtime_diagnostics.ps1
```

统一 API 测试：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_all.ps1 -ContinueOnFailure
```

Live2D payload 测试：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_live2d_payload.ps1
```

Flutter 侧测试见“Flutter 手机端”章节。

## 数据与资源

`data/` 目录用于放本地运行资产，默认不入仓：

```text
data/persona/               角色人格配置
data/live2d/characters/     Live2D 角色模型和 profile
data/live2d/backgrounds/    背景资源
data/vision/characters/     视觉角色图库
data/models/                本地 ASR / embedding / CLIP 等模型
data/uploads/               API 上传文件缓存
data/cache/                 RAG / Vision 等索引缓存
data/logs/                  本地日志
```

当前 Flutter 端也内置了一份过渡 Live2D WebView 资源，路径在：

```text
apps/flutter_client/assets/live2d_web/
```

## 当前 V1.0 RC 状态

已完成：

- 手机端版本进入 `1.0.0-rc.1+1`
- Android 应用名为 `AIAgent`
- Android 应用 ID 为 `com.aiagent.mobile`
- 文本、图片、录音、ASR、TTS、记忆、设置页、关于页已形成手机端闭环
- Live2D 过渡模型已能加载和运动
- Flutter `analyze` / `test` 已通过用户本地验证
- RC 验收清单和 release notes 已补齐

待上线前确认：

- 真机手动验收完整通过
- release keystore 已配置
- 正式 Live2D 模型交付后替换资源并复测
- 真实 provider 的 `.env` 不含 mock-only 配置

## 已知注意事项

- PowerShell 读取 UTF-8 中文文件时偶尔会显示乱码，优先用 VS Code 或设置 `[Console]::OutputEncoding` 查看。
- `data/`、`scripts/`、`apps/flutter_client/` 当前被根 `.gitignore` 忽略，纳入版本管理前需要单独调整。
- RAG、Vision、Memory、TTS、ASR 依赖外部模型或服务；mock 模式可以跑通主流程，但不代表生产效果。
- Qdrant collection 的 embedding 维度必须和实际模型一致，维度变化需要重建 collection。
- 没有 release keystore 时，Flutter release 包 fallback debug signing，不能作为正式外发包。

## 参考文档

- [docs/config-reference.md](docs/config-reference.md)
- [docs/api-observability.md](docs/api-observability.md)
- [docs/phase4-stabilization-closure.md](docs/phase4-stabilization-closure.md)
- [docs/project-file-inventory.md](docs/project-file-inventory.md)
- [docs/project-overview-next-stage.md](docs/project-overview-next-stage.md)
- [stage.md](stage.md)
