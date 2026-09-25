# AIAgent

AIAgent 是一个统一运行时：对话、长期记忆、RAG 知识检索、视觉理解、
语音输入、TTS 输出、运行时状态与执行一致性，以及多端控制台（HTTP API、Flutter 手机端、Qt 桌面端）
都放在同一个工程里，目标是形成一条从本地开发走到多端交付的完整链路。

- **后端**：FastAPI + LangGraph 图流程；默认 mock provider 即可跑通主链路。
- **手机端**：Flutter，当前 `1.0.0-rc.1+1`。
- **桌面端**：PySide6 + Qt Quick(QML)，可打包成 Windows exe（绿色目录 / 单文件）。
- **Live2D 表现层当前暂停**：桌面端与手机端都不再渲染模型；后端 payload 协议与 `integrations/live2d/`
  原样保留未删除，恢复方式见文末「Live2D 现状」。

## 当前状态

| 项 | 状态 |
| --- | --- |
| 后端 V1.1 | 已收口：智能体质量、云运维可观测性、安全边界 |
| V1.2 十批优化 | 第 1 批（基线与范围）、第 2 批（多 Worker 执行状态一致性）已交付；第 3-10 批见 [十批实施计划](docs/v1.2-ten-batch-implementation-plan.md) |
| 手机端 | `1.0.0-rc.1+1`，文本 / 图片 / 录音 / ASR / TTS / 记忆 / 设置闭环 |
| 桌面端 | QML 版已重写并通过自检；打包脚本就绪（首次打包需先装 MSVC C++ 组件） |
| 测试规模 | `pytest --collect-only` 收集 **352** 个测试；静态基线统计 **343** 个测试函数、8 项缺陷（P0 2）、10 项优化 |

## 项目结构

~~~text
aiagent/              核心智能体：图流程、状态、记忆、知识库、语音、表达
apps/api/             FastAPI HTTP 服务与路由
apps/core/            Runtime 构建与本地命令行入口
apps/desktop_qt/      Qt 桌面端（PySide6 + QML，可打包 exe）         <- 被 .gitignore 忽略
apps/flutter_client/  Flutter 手机端                                  <- 被 .gitignore 忽略
apps/worker/          云端异步任务 worker
cloud/                云模式配置、限流、并发租约、任务队列、对象存储、GPU client
config/               统一配置与默认值
integrations/         LLM / ASR / TTS / Live2D / 音频等外部集成
data/                 本地资源、模型、缓存、上传、日志（各子目录默认不入仓）
deploy/               Dockerfile、docker-compose（腾讯云整栈 + 本地基础服务）、nginx
docs/                 架构、配置、观测性、质量基线与阶段文档
gpu_services/         GPU 服务草稿与占位目录
scripts/              测试、门禁、部署与资源工具（已纳入版本管理）
tests/                Python 单元 / 契约 / 冒烟 / RAG 质量测试
~~~

版本管理现状（根 `.gitignore`）：`apps/desktop_qt/` 与 `apps/flutter_client/` **被忽略**；
`scripts/`、`docs/`、`tests/`、`deploy/` **已入库**；`data/` 下除
`data/characters/README.md` 外全部忽略。

## 能力概览

- **文本聊天**：`POST /chat`，回复可带语音与情绪字段
- **图片多模态聊天**：`POST /chat/multimodal`
- **语音输入**：`/voice/transcribe`、`/voice/turn`，以及实时通话 `/voice/realtime/*`
- **TTS 输出**：GPT-SoVITS / IndexTTS2 / VoxCPM，客户端播放
- **长期记忆**：Mem0 + Qdrant（可选 Neo4j 图谱），可读取、搜索、固定、删除、清空
- **RAG 知识检索**：文档切块、混合检索（向量 + BM25）、重建索引、新鲜度检查
- **视觉理解**：图片分析、角色图库索引、视觉上下文进入对话
- **执行状态一致性**：会话短期上下文与线程归属跨 Worker 共享（V1.2 第 2 批），清理操作对所有 Worker 生效
- **可观测性**：`request_id`、阶段耗时、统一错误结构、运行时诊断、能力注册表、就绪性检查
- **多端入口**：HTTP API、Flutter 手机端、Qt 桌面端；Web 控制台当前不在工作区

## 环境要求

- **Python 3.11+** 运行后端；桌面端使用 PySide6 6.8.2，其 `Requires-Python` 为 `<3.14,>=3.9`，
  因此**桌面端必须用 3.12/3.13**（本项目 venv 为 3.12.7）。
- **可选服务**：Redis（限流 / 队列 / 通话状态 / 执行状态共享）、Qdrant（长期记忆向量）、
  Neo4j（记忆图谱）、Docker（一键起上述基础服务）。
- **可选工具链**：Flutter SDK（手机端）、MSVC C++ 生成工具 + Nuitka（桌面端打包 exe）。

依赖安装（venv 由 `uv` 创建，**默认不含 pip**，所以用 `uv pip` 而不是 `pip`）：

~~~powershell
cd F:\aiagent
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
uv pip install --python .venv\Scripts\python.exe -r requirements-cloud.txt   # 云端附加：redis / boto3
~~~

如果习惯用 `uv sync`，注意 `pyproject.toml` 里的依赖是仓库包的子集，Web 依赖（fastapi / uvicorn 等）
在 `requirements.txt` 中声明。

## 快速开始

### 1. 起本地基础服务（可选，但推荐）

~~~powershell
# 一键启动 Redis + Qdrant + Neo4j（只绑定 127.0.0.1；Postgres 为预留，需 --profile reserved）
powershell -ExecutionPolicy Bypass -File scripts\dev_services.ps1 -Action up

# 等价的原生命令
docker compose -f deploy/docker-compose.services.yml --env-file .env up -d
~~~

脚本会等待端口就绪、打印各端点状态，并给出该写进 `.env` 的连接串。详见「本地基础服务（Docker）」。

### 2. 准备配置

~~~powershell
cd F:\aiagent
Copy-Item .env.example .env      # 已存在则不要覆盖
~~~

`.env` 与 `.env.example` 是**同一套分区、同样组内字母序**的 173 个变量，便于两份文件直接 diff。
最小开发配置可以保持 mock：

~~~env
LLM_PROVIDER=mock
ENABLE_MOCK_LLM=true
TTS_PROVIDER=mock
ENABLE_MOCK_TTS=true
ASR_PROVIDER=mock
ENABLE_MOCK_ASR=true
~~~

> `*_API_KEY_ENV` 有两种取值形式：填**环境变量名**（该变量必须存在于进程环境，本项目没有
> `load_dotenv`，只写在 `.env` 里不会进入 `os.environ`），或**直接填密钥本身**（纯 `.env`
> 工作流下唯一能直接生效的形式）。完整说明见两份 env 文件的文件头。

### 3. 启动后端

~~~powershell
cd F:\aiagent
.\.venv\Scripts\python.exe -m uvicorn apps.api.http_server:app --host 0.0.0.0 --port 8000 --reload
~~~

常用检查：

~~~powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/runtime/diagnostics | ConvertTo-Json -Depth 80
~~~

交互式接口文档：`http://127.0.0.1:8000/docs`（FastAPI 自带 Swagger UI）。

API 入口是 [apps/api/http_server.py](apps/api/http_server.py)，运行时构建入口是 [apps/core/bootstrap.py](apps/core/bootstrap.py)，
配置真源是 [config/settings.py](config/settings.py) 与 [cloud/config.py](cloud/config.py)。

### 4. 启动客户端

~~~powershell
# 桌面端（PySide6 + QML，启动约 1-3 秒）
.\.venv\Scripts\python.exe -m apps.desktop_qt.main

# 手机端
cd F:\aiagent\apps\flutter_client
flutter pub get
flutter run
~~~

## 本地基础服务（Docker）

`deploy/docker-compose.services.yml` 只包含后端依赖的基础服务，不包含 api / worker 容器，
适合「服务在 Docker、后端在 venv」的本地开发方式。

| 服务 | 端口（仅 127.0.0.1） | 用途 |
| --- | --- | --- |
| Redis | 6379 | 限流、并发租约、任务队列、通话状态、跨 Worker 执行状态 |
| Qdrant | 6333 / 6334 | 长期记忆向量库 |
| Neo4j | 7474 / 7687 | 记忆图谱（`MEMORY_ENABLE_GRAPH=true` 时才使用） |
| Postgres | 5432 | 预留（`--profile reserved`；当前 Python 代码不依赖） |

~~~powershell
powershell -ExecutionPolicy Bypass -File scripts\dev_services.ps1 -Action status   # 容器状态 + 端口探活
powershell -ExecutionPolicy Bypass -File scripts\dev_services.ps1 -Action logs     # 实时日志
powershell -ExecutionPolicy Bypass -File scripts\dev_services.ps1 -Action down     # 停止（保留数据）
powershell -ExecutionPolicy Bypass -File scripts\dev_services.ps1 -Action reset    # 停止并删数据卷
~~~

- 与 `deploy/docker-compose.tencent.yml`（整栈部署）**互不冲突**：项目名与数据卷都不同，但不要混用数据。
- Neo4j 密码取 `.env` 的 `NEO4J_PASSWORD`，脚本会显式 `--env-file .env`，保证容器与后端读同一份密码。
- Redis 不可用时，依赖它的能力按既定策略降级（限流放行、执行状态退化为单进程并暴露 degraded），
  降级状态在 `/runtime/capabilities` 与 `/cloud/ops/readiness` 中可见。

## 桌面端（Qt / QML）

~~~powershell
# 运行（两种写法都可用）
.\.venv\Scripts\python.exe -m apps.desktop_qt.main
.\.venv\Scripts\python.exe apps\desktop_qt\main.py

# 自检（三阶段：Python 层 / QML 层 / 桥接链路，离屏运行不弹窗）
.\.venv\Scripts\python.exe -m apps.desktop_qt.tools.smoke_check
~~~

- 功能：聊天（气泡流 / Enter 发送 / Shift+Enter 换行）、语音播报、长期记忆浏览与删除、运行诊断、设置页。
- 配置文件：源码运行在 `apps/desktop_qt/runtime/config.json`；打包后在 **exe 同目录**（绿色便携）。
- 样式入口：所有颜色 / 圆角 / 间距 / 字号集中在 `apps/desktop_qt/bridge/theme_bridge.py`，
  QML 侧统一引用 `Theme.palette.xxx`。
- 打包 exe（首次需先装 MSVC 组件 `Microsoft.VisualStudio.Component.VC.Tools.x86.x64` 与 Nuitka）：

~~~powershell
uv pip install --python .venv\Scripts\python.exe nuitka ordered-set
powershell -ExecutionPolicy Bypass -File apps\desktop_qt\packaging\build.ps1                 # 绿色目录
powershell -ExecutionPolicy Bypass -File apps\desktop_qt\packaging\build.ps1 -Mode onefile  # 单文件
~~~

细节与故障排查见 [apps/desktop_qt/README.md](apps/desktop_qt/README.md)。

## Flutter 手机端

手机端是 V1.0 RC 的主交付入口：

~~~powershell
cd F:\aiagent\apps\flutter_client
flutter pub get
flutter run
~~~

真机调试时，设置页里的 API 地址必须填电脑的局域网 IP（例如 `http://192.168.x.x:8000`），
不要填 `127.0.0.1`，那会指向手机自己。

RC 检查命令：

~~~powershell
cd F:\aiagent\apps\flutter_client
dart format lib test
flutter analyze
flutter test
flutter build apk --release
~~~

Android release 构建读取 `apps/flutter_client/android/key.properties`；没有 release keystore 时会
fallback 到 debug signing，只适合内测安装。

手机端文档：见 `apps/flutter_client/README.md` 与 `apps/flutter_client/docs/` 目录
（release checklist、RC release notes、Live2D 移动端加载说明——后者当前暂停中）。

## Web 控制台

当前工作区没有 `apps/web` 目录。早期文档里提到的 Next.js 控制台不属于当前可运行代码；
如果后续恢复 Web 控制台，需要重新补齐目录、依赖和构建说明。
（仓库里另有一个运维向的只读页面：`GET /dashboard`，需要 `CLOUD_ADMIN_TOKEN`。）

## API 速览

健康与诊断：

| 路径 | 用途 |
| --- | --- |
| `GET /live` / `GET /health` / `GET /ready` | 存活 / 健康 / 就绪 |
| `GET /runtime/diagnostics` | 运行时诊断（逐项检查） |
| `GET /runtime/capabilities` | 能力注册表与降级状态 |
| `GET /dashboard` / `GET /dashboard/api/snapshot` | 运维面板（需 admin token） |

对话与控制：

| 路径 | 用途 |
| --- | --- |
| `POST /chat` | 文本聊天 |
| `POST /chat/multimodal` | 图片 + 文本聊天 |
| `POST /session/open` | 会话开场与 presence 初始化 |
| `POST /control/input` / `pause` / `resume` / `reset-context` / `interrupt` | 运行时控制 |
| `GET /control/status` | 控制面状态 |

语音：

| 路径 | 用途 |
| --- | --- |
| `POST /voice/transcribe` / `POST /voice/turn` / `POST /voice/interrupt` | 转写 / 语音回合 / 打断 |
| `GET /voice/state` | 语音链路状态 |
| `POST /voice/realtime/start` / `end` / `turn` / `interrupt` | 实时通话控制 |
| `GET /voice/realtime/state/{call_id}` | 通话状态（Redis 共享） |

记忆 / 知识 / 视觉：

| 路径 | 用途 |
| --- | --- |
| `GET /memory/user/{user_id}` / `snapshot` / `stats` / `search` / `audit` | 记忆读取与审计 |
| `GET /memory/user/{user_id}/layers/{layer}` / `preferences`（`PUT`） | 分层记忆与偏好 |
| `DELETE /memory/user/{user_id}` / `memories/{memory_id}` / `layers/{layer}` | 清空用户记忆 / 删除单条 / 删除分层 |
| `POST /memory/user/{user_id}/memories/{memory_id}/pin`（`DELETE` 取消） | 固定 / 取消固定 |
| `GET /memory/write/status` / `GET /memory/graph/status` | 异步写入与图谱状态 |
| `GET /knowledge/stats` / `rebuild/status` / `index/freshness`，`POST /knowledge/search` / `rebuild` | RAG 状态、检索与重建 |
| `POST /vision/analyze` / `chat`，`GET /vision/characters/stats` / `schema`，`POST /vision/characters/rebuild` | 视觉分析与角色图库 |

任务、云端与媒体：

| 路径 | 用途 |
| --- | --- |
| `GET /cloud/tasks` / `dead` / `summary` / `/cloud/tasks/{task_id}`，`POST /cloud/tasks/...` | 异步任务队列与重建任务 |
| `GET /cloud/ready` / `limits` / `ops/readiness` / `ops/config-snapshot` | 云端就绪与运维快照 |
| `GET /cloud/gpu/health` / `POST /cloud/gpu/llm-smoke` | GPU 服务健康与连通性 |
| `POST /cloud/storage/upload` / `presign-upload` | 对象存储上传 |
| `GET /audio/{filename}` | TTS 音频文件 |

请求追踪、`request_id` 与统一错误结构见 [docs/api-observability.md](docs/api-observability.md)；
全量端点以运行中的 `/docs` 为准。Live2D 相关端点（`/live2d/*`）仍然保留可用，但当前不在使用。

## 自检与门禁

| 命令 | 作用 |
| --- | --- |
| `.venv\Scripts\python.exe scripts\check_config_sync.py` | 配置三方一致性：源码 ↔ `.env.example` ↔ `docs/config-reference.md` |
| `.venv\Scripts\python.exe scripts\v1_preflight.py --mode all --env-file .env` | 发布前检查（占位符、mock、真实 provider 配置） |
| `.venv\Scripts\python.exe scripts\v1_2_baseline.py --root . --print` | V1.2 基线快照（测试函数 / 缺陷 / 优化项 / 前置批次） |
| `.venv\Scripts\python.exe scripts\check_repo_hygiene.py` | 仓库卫生检查 |
| `powershell -File scripts\test_runtime_diagnostics.ps1` | 运行时诊断链路 |
| `.venv\Scripts\python.exe -m apps.desktop_qt.tools.smoke_check` | 桌面端三阶段自检 |

## 测试

Python 侧：

~~~powershell
cd F:\aiagent
.\.venv\Scripts\python.exe -m pytest -q tests\unit tests\api tests\smoke -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest --collect-only -q tests      # 当前收集 352 个测试
~~~

RAG 检索质量基线：

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q tests\rag -p no:cacheprovider
~~~

`tests\rag` 依赖 `data\knowledge\public`；本地没有知识库目录时会按条件跳过。
质量基线与阈值说明见 [docs/quality/rag-eval.md](docs/quality/rag-eval.md)。

测试分层标记（`pytest -m <标记>` 可按层筛选）：`unit` / `api` / `smoke` / `rag` / `integration`。

统一入口（含 PowerShell 侧测试）：

~~~powershell
powershell -ExecutionPolicy Bypass -File scripts\test_all.ps1 -ContinueOnFailure
~~~

V1.0 最终 smoke 指令见 [docs/v1-final-smoke.md](docs/v1-final-smoke.md)，发布前勾选项见
[docs/v1-release-checklist.md](docs/v1-release-checklist.md)。

## 数据与资源

`data/` 用于放本地运行资产，**默认不入仓**（`data/characters/*` 除外，只保留其中的 README）：

~~~text
data/persona/           角色人格配置
data/characters/        视觉角色图库（图片等大文件）
data/live2d/            Live2D 模型与背景（表现层暂停中，资源保留）
data/models/            本地 ASR / embedding / CLIP 等模型
data/uploads/           API 上传文件缓存
data/cache/             RAG / Vision 等索引缓存
data/knowledge/         本地知识库文档
data/logs/              本地日志
~~~

## Live2D 现状

- **前端不再渲染 Live2D**：桌面端已移除模型面板（旧 `chat_window.py` / `live2d_view_panel.py` 已删除），
  手机端的 Live2D WebView 舞台也不再是主链路。
- **后端不删除、不影响**：`integrations/live2d/`、`aiagent/live2d/` 与 `/live2d/*` 端点原样保留，
  既有测试脚本也留在 `scripts/` 下（例如 `test_live2d_payload.ps1`、`scan_live2d_models.ps1`）。
- **回复里的情绪仍然有用**：`emotion` / `expression` 由客户端以「情绪胶囊」形式轻量展示，不依赖模型渲染。
- **如果要恢复**：后端契约无需改动，客户端重新引入渲染层即可（Qt 端可走 QtWebEngine + 现有
  `apps/flutter_client/assets/live2d_web/` 舞台，或原生 `live2d` Python 包 + `QOpenGLWidget`）。

## 已知注意事项

- **PowerShell 读取 UTF-8 中文**偶尔显示乱码：用 VS Code 查看，或先设置 `[Console]::OutputEncoding = [Text.Encoding]::UTF8`。
  含中文的 `.ps1` 必须保存为 **UTF-8 with BOM**，否则 Windows PowerShell 5.1 会解析失败。
- **venv 没有 pip**：本项目 venv 由 `uv` 创建，安装依赖请用 `uv pip install --python .venv\Scripts\python.exe ...`。
- **系统 Python 是 3.14**：PySide6 6.8.2 不支持 3.14，桌面端务必使用项目 venv（3.12.7）。
- **系统代理会拦截本机请求**：Windows 注册表级代理会把 `127.0.0.1` 请求变成 `HTTP 502`；
  桌面端默认忽略系统代理，只有后端确实在代理之后时才在设置页打开开关。
- `apps/desktop_qt/` 与 `apps/flutter_client/` 被根 `.gitignore` 忽略，改动不会出现在 `git status` 中。
- RAG / Vision / Memory / TTS / ASR 依赖外部模型或服务；mock 模式能跑通主流程，不代表生产效果。
- Qdrant collection 的 embedding 维度必须与实际模型一致（`RAG_EMBEDDING_DIMENSIONS` / `MEMORY_EMBEDDING_DIMS`），
  维度变化需要重建 collection。
- 没有 release keystore 时，Flutter release 包 fallback debug signing，不能作为正式外发包。
- 多实例部署必须让执行状态共享（`REDIS_URL` + `LLM_THREAD_STATE_BACKEND=auto`），
  否则同一用户在不同 Worker 上会看到两套上下文。

## 参考文档

配置与观测：

- [docs/config-reference.md](docs/config-reference.md) —— 全量环境变量与默认值
- [docs/api-observability.md](docs/api-observability.md) —— 请求追踪、耗时与错误结构
- [docs/session-and-turn-boundary.md](docs/session-and-turn-boundary.md) —— 会话 / 轮次边界
- [docs/repo-governance.md](docs/repo-governance.md) —— 仓库治理约定
- [docs/quality/rag-eval.md](docs/quality/rag-eval.md) —— RAG 质量基线与阈值

阶段与路线：

- [docs/next-stage-optimization-roadmap.md](docs/next-stage-optimization-roadmap.md) —— 下一阶段优化路线
- [docs/v1.2-ten-batch-implementation-plan.md](docs/v1.2-ten-batch-implementation-plan.md) —— V1.2 十批实施计划
- [docs/v1.2-scope-and-baseline.md](docs/v1.2-scope-and-baseline.md) —— V1.2 范围与基线
- [docs/v1.2-batch-02-code-delivery.md](docs/v1.2-batch-02-code-delivery.md) —— 第 2 批交付说明
- [docs/v1-final-smoke.md](docs/v1-final-smoke.md)、[docs/v1-release-checklist.md](docs/v1-release-checklist.md) —— V1.0 冒烟与发布清单

客户端：

- [apps/desktop_qt/README.md](apps/desktop_qt/README.md) —— 桌面端运行、打包、故障排查

> 说明：客户端目录 `apps/desktop_qt/` 与 `apps/flutter_client/` 被根 `.gitignore` 忽略，
> 因此桌面端与手机端的文档只存在于本地工作区，克隆仓库后不会出现（手机端文档位置见「Flutter 手机端」）。
