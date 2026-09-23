# 配置参考

本文档是 V1.0 收尾阶段的配置索引，目标是让 `.env.example`、`cloud.tencent.example.env`、`config/settings.py`、`cloud/config.py` 和部署脚本保持一致。

## 配置来源

| 来源 | 用途 |
| --- | --- |
| `config/settings.py` | 后端核心运行时配置：LLM、RAG、Vision、Memory、ASR、TTS、Live2D、API |
| `cloud/config.py` | 云部署配置：Redis、限流、并发、对象存储、GPU endpoint |
| `cloud/admin_auth.py` | 管理接口 token：`CLOUD_ADMIN_TOKEN` |
| `cloud/gpu_client.py` | GPU 服务鉴权：`GPU_API_TOKEN` |
| `apps/worker/main.py` | worker 运行参数：`WORKER_CONCURRENCY`、`TASK_QUEUE_NAME` 等 |
| `deploy/Dockerfile.api` | API worker 数：`WEB_CONCURRENCY` |
| `deploy/docker-compose.tencent.yml` | 云端容器网络、Redis、Qdrant、Neo4j、Postgres |
| `apps/desktop_qt/chat_window.py` | Qt 调试端本地环境变量 |

## 示例文件

| 文件 | 用途 | 是否可提交 |
| --- | --- | --- |
| `.env.example` | 本地开发模板，默认 mock，可直接复制为 `.env` | 是 |
| `.env` | 本机真实配置，可能包含密钥 | 否 |
| `cloud.tencent.example.env` | 腾讯云部署模板，生产向配置，占位符需要替换 | 是 |
| `cloud.tencent.env` | 云端真实配置，包含真实 token、bucket、密钥 | 否 |

复制本地配置：

```powershell
Copy-Item .env.example .env
```

复制云端配置：

```powershell
Copy-Item cloud.tencent.example.env cloud.tencent.env
```

## V1.0 推荐配置组合

### 本地 mock 闭环

用于开发、API contract、smoke、Flutter 联调基础链路。不会访问真实模型、外部 Redis、GPU 服务。

```env
APP_ENV=development
CLOUD_MODE=false

LLM_PROVIDER=mock
ENABLE_MOCK_LLM=true

STATE_PROVIDER=mock
ENABLE_MOCK_STATE=true

PLANNER_PROVIDER=mock
ENABLE_MOCK_PLANNER=true

VISION_PROVIDER=mock
TTS_PROVIDER=mock
ENABLE_MOCK_TTS=true
ASR_PROVIDER=mock
ENABLE_MOCK_ASR=true
LIVE2D_PROVIDER=mock
ENABLE_LIVE2D_RUNTIME=false
```

### 本地真实 LLM + 其他 mock

用于只验证文本回复质量，保留 RAG、Vision、TTS、ASR、Live2D 的低成本降级能力。

```env
ENABLE_MOCK_LLM=false
LLM_PROVIDER=siliconflow
LLM_MODEL=your-chat-model
SILICONFLOW_API=your-api-key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

ENABLE_MOCK_STATE=true
ENABLE_MOCK_PLANNER=true
VISION_PROVIDER=mock
ENABLE_MOCK_TTS=true
ENABLE_MOCK_ASR=true
LIVE2D_PROVIDER=mock
```

### 云部署

用于腾讯云 / Docker Compose 生产向运行。必须替换所有 `change-*`、`your-*` 占位符。

```env
APP_ENV=production
CLOUD_MODE=true
CLOUD_ADMIN_TOKEN=change-this-admin-token
REDIS_URL=redis://redis:6379/0
STORAGE_PROVIDER=cos
RATE_LIMIT_ENABLED=true
INFLIGHT_LIMIT_ENABLED=true
LIMITER_FAIL_OPEN=false
```

## 基础配置

| 配置项 | 默认值 | 说明 | 影响范围 |
| --- | --- | --- | --- |
| `APP_NAME` | `aiagent` | 应用名称 | 日志、服务标识 |
| `APP_ENV` | `development` | 运行环境 | 日志、诊断、部署识别 |
| `LOG_LEVEL` | `INFO` | 日志级别 | API、worker、运行时日志 |
| `API_HOST` | `127.0.0.1` | API 监听地址 | 本地启动脚本 |
| `API_PORT` | `8000` | API 监听端口 | 本地启动脚本 |
| `API_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | CORS 白名单，多个地址用逗号分隔 | `apps/api/http_server.py` |

生产环境中 `API_CORS_ORIGINS` 必须显式配置真实前端域名，不建议使用宽松默认值。

### 日志与 HTTP 边界（V1.1 补充）

| 配置项 | 默认值 | 影响范围 |
| --- | --- | --- |
| `LOG_FORMAT` | `text` | `text` = 本地可读；`json` = 生产 JSON Lines，采集系统可直接按 `request_id` 检索。API 与 worker 共用同一套日志管线 |
| `API_CORS_ALLOW_CREDENTIALS` | `true` | 是否允许浏览器跨域携带 Cookie/credentials。生产若用固定域名，建议配合白名单收紧 `API_CORS_ORIGINS` |
| `API_TRUSTED_PROXIES` | `127.0.0.1,::1` | 允许携带 `X-Forwarded-For` 的代理地址；配错会导致客户端 IP 被伪造，直接影响限流与审计 |

## 云与运维配置

| 配置项 | 默认值 | 说明 | 影响范围 |
| --- | --- | --- | --- |
| `CLOUD_MODE` | `false` | 是否启用云模式语义 | readiness、限流、任务队列、云部署 |
| `CLOUD_DEPLOY_REGION` | `tencent-cn` | 部署区域标识 | config snapshot、诊断 |
| `API_PUBLIC_BASE_URL` | 空 | 对外 API 根地址 | 客户端配置、对象 URL 生成参考 |
| `CLOUD_ADMIN_TOKEN` | 空 | 管理接口 token | `/cloud/ops/*`、`/cloud/tasks/*`、rebuild 管理接口 |
| `REDIS_URL` | 空 | Redis 连接地址 | 限流、并发租约、任务队列、分布式锁 |
| `REDIS_PREFIX` | `aiagent:v1` | Redis key 前缀 | 多环境隔离 |

管理接口推荐 header：

```text
x-cloud-admin-token: <CLOUD_ADMIN_TOKEN>
```

旧 header `x-admin-token` 仍可兼容，但 V1.0 后续文档和客户端都以 `x-cloud-admin-token` 为准。

### 限流与并发

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `RATE_LIMIT_ENABLED` | `false` | 是否启用频率限制 |
| `INFLIGHT_LIMIT_ENABLED` | `false` | 是否启用并发请求限制 |
| `LIMITER_FAIL_OPEN` | `true` | Redis 不可用时是否放行限流检查 |
| `RATE_LIMIT_DEFAULT_PER_MINUTE` | `60` | 默认每分钟请求数 |
| `RATE_LIMIT_CHAT_PER_MINUTE` | `20` | `/chat` 每分钟请求数 |
| `RATE_LIMIT_MULTIMODAL_PER_MINUTE` | `5` | 多模态每分钟请求数 |
| `RATE_LIMIT_VOICE_PER_MINUTE` | `5` | 语音每分钟请求数 |
| `RATE_LIMIT_REBUILD_PER_MINUTE` | `1` | 重建类接口每分钟请求数 |
| `GLOBAL_INFLIGHT_LIMIT` | `100` | 全局并发上限 |
| `CHAT_INFLIGHT_LIMIT` | `40` | 聊天并发上限 |
| `MULTIMODAL_INFLIGHT_LIMIT` | `10` | 多模态并发上限 |
| `VOICE_INFLIGHT_LIMIT` | `8` | 语音并发上限 |
| `REBUILD_INFLIGHT_LIMIT` | `1` | 重建任务并发上限 |
| `INFLIGHT_LEASE_SECONDS` | `120` | 并发租约 TTL |

云端建议：

```env
RATE_LIMIT_ENABLED=true
INFLIGHT_LIMIT_ENABLED=true
LIMITER_FAIL_OPEN=false
```

本地建议：

```env
RATE_LIMIT_ENABLED=false
INFLIGHT_LIMIT_ENABLED=false
```

### 对象存储

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `STORAGE_PROVIDER` | `local` | `local`、`cos` 或 `s3` |
| `LOCAL_STORAGE_ROOT` | `data/cloud_storage` | 本地对象存储根目录 |
| `UPLOAD_MAX_BYTES` | `26214400` | 直传最大字节数，默认 25 MB |
| `S3_ENDPOINT_URL` | 空 | S3/COS endpoint |
| `S3_REGION` | `ap-guangzhou` | S3/COS region |
| `S3_BUCKET` | 空 | bucket 名称 |
| `S3_ACCESS_KEY_ID` | 空 | access key id |
| `S3_SECRET_ACCESS_KEY` | 空 | secret access key |
| `S3_PUBLIC_BASE_URL` | 空 | 对外访问 base URL |

`S3_ACCESS_KEY_ID` 和 `S3_SECRET_ACCESS_KEY` 只允许写入真实私有 env，不要写入文档、日志或提交记录。

### GPU 服务

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `GPU_LLM_BASE_URL` | 空 | 云 GPU LLM endpoint |
| `GPU_TTS_BASE_URL` | 空 | 云 GPU TTS endpoint |
| `GPU_ASR_BASE_URL` | 空 | 云 GPU ASR endpoint |
| `GPU_API_TOKEN` | 空 | GPU 服务 Bearer token |

当前 GPU circuit breaker 阈值在源码中固定，不读取 `GPU_CIRCUIT_*` 环境变量。因此 V1.0 示例文件不再提供这些未接入字段。

## LLM 配置

| 配置项 | 默认值 | 说明 | 影响范围 |
| --- | --- | --- | --- |
| `LLM_PROVIDER` | `mock` | 主回复模型 provider | `LLMService` |
| `LLM_MODEL` | `Qwen/Qwen3-8B` | 主回复模型名称 | 主聊天回复 |
| `ENABLE_MOCK_LLM` | `true` | 是否强制 mock LLM | 主聊天回复 |
| `LLM_TIMEOUT_SECONDS` | `20.0` | HTTP 调用超时 | 主聊天、状态、规划等 |
| `LLM_TEMPERATURE` | `0.7` | 采样温度 | 主聊天回复 |
| `LLM_MAX_TOKENS` | `200` | 最大输出 token 数 | 主聊天回复 |
| `OPENAI_API_KEY` | 空 | OpenAI-compatible API key | OpenAI provider |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible base URL | OpenAI provider |
| `SILICONFLOW_API` | 空 | SiliconFlow API key | SiliconFlow provider |
| `SILICONFLOW_BASE_URL` | `https://api.siliconflow.cn/v1` | SiliconFlow base URL | SiliconFlow provider |
| `LMSTUDIO_API_KEY` | `lm-studio` | LM Studio token 占位 | LM Studio provider |
| `LMSTUDIO_BASE_URL` | `http://127.0.0.1:1234/v1` | LM Studio base URL | LM Studio provider |

`STATE_PROVIDER`、`STATE_MODEL`、`ENABLE_MOCK_STATE` 控制状态分析 LLM。`PLANNER_PROVIDER`、`PLANNER_MODEL`、`ENABLE_MOCK_PLANNER` 控制回复规划 LLM。V1.0 稳定性优先，生产前可以先只切主 LLM，状态和规划保留 mock。

## RAG 配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `RAG_EMBEDDING_PROVIDER` | `huggingface` | embedding provider |
| `RAG_EMBEDDING_MODEL_NAME` | `BAAI/bge-small-zh-v1.5` | embedding 模型名 |
| `RAG_EMBEDDING_MODEL_PATH` | 空 | 本地 embedding 模型路径 |
| `RAG_EMBEDDING_DEVICE` | `cpu` | 运行设备 |
| `RAG_EMBEDDING_LOCAL_FILES_ONLY` | `true` | 是否只使用本地文件 |
| `RAG_EMBEDDING_API_KEY_ENV` | 空 | API key 所在环境变量名 |
| `RAG_EMBEDDING_BASE_URL` | 空 | API embedding base URL |
| `RAG_EMBEDDING_BATCH_SIZE` | `64` | embedding 批大小 |
| `RAG_EMBEDDING_DIMENSIONS` | 空 | embedding 维度 |
| `RAG_CHUNK_SIZE` | `520` | 文档切块大小 |
| `RAG_CHUNK_OVERLAP` | `80` | 文档切块重叠 |
| `RAG_BM25_TOP_K` | `6` | BM25 初筛数量 |
| `RAG_VECTOR_TOP_K` | `6` | 向量检索数量 |
| `RAG_FINAL_TOP_K` | `4` | 最终注入 LLM 的片段数 |

注意事项：

- `RAG_EMBEDDING_DIMENSIONS` 为空时由 provider 或索引实现自行处理。
- 维度变化后必须重建索引。
- mock 主链路 smoke 不要求真实 RAG embedding 可用。

### RAG 索引生命周期（V1.1 新增）

| 配置项 | 默认值 | 影响范围 |
| --- | --- | --- |
| `RAG_AUTO_REBUILD_ON_STALE` | `false` | 检测到索引过期时是否自动后台重建。`false` 只告警并写 `index_freshness` |
| `RAG_INDEX_MANIFEST_PATH` | 空 | 索引清单位置；空值 = `docs_index_path` 同目录的 `index_manifest.json` |

索引清单记录 `embedding_provider` / `embedding_model` / `embedding_dimensions` / `faiss_dimension` /
`chunk_size` / `chunk_overlap` / `tokenizer_version` 以及每个知识文件的 `size+mtime+sha1`。

`GET /knowledge/index/freshness` 的机器可读原因码：

| reason_code | 含义 | 是否必须重建 |
| --- | --- | --- |
| `manifest_missing` | 没有清单（首次运行或清单被删） | 建议 |
| `embedding_dimension_changed` | embedding 维度与索引不一致 | **必须**，否则检索直接失败 |
| `embedding_model_changed` / `embedding_provider_changed` | 换模型或换提供方 | 建议 |
| `tokenizer_version_changed` | 分词实现升级 | 建议 |
| `chunk_policy_changed` | `RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP` 变化 | 建议 |
| `knowledge_files_added` / `_modified` / `_removed` | 知识库文件变化 | 建议 |

> `tokenizer_version` 与 `HybridRetriever._searchable_text/_tokenize` 的实现绑定。
> 改动分词或标识头构造方式时，必须同步提升 `aiagent/knowledge/index_manifest.py` 的 `TOKENIZER_VERSION`，
> 否则旧索引不会被判定为过期。

## Vision 配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `VISION_PROVIDER` | `mock` | Vision provider |
| `VISION_MODEL` | 空 | 视觉模型名称 |
| `VISION_API_KEY_ENV` | 空 | Vision API key 所在环境变量名 |
| `VISION_BASE_URL` | 空 | Vision base URL |
| `VISION_TIMEOUT_SECONDS` | `60.0` | Vision HTTP 超时 |
| `VISION_UPLOAD_DIR` | `data/uploads/images` | 上传图片保存目录 |
| `VISION_MAX_IMAGE_BYTES` | `12582912` | 图片最大字节数，约 12 MB |
| `VISION_CHARACTER_ROOT_DIR` | `data/characters` | 角色图库根目录 |
| `VISION_CHARACTER_INDEX_DIR` | `data/cache/vision/character_index` | 角色图库索引缓存目录 |
| `VISION_CHARACTER_EMBEDDING_MODEL_NAME` | `clip-ViT-B-32` | 角色图片 embedding 模型名 |
| `VISION_CHARACTER_EMBEDDING_MODEL_PATH` | 空 | 本地 CLIP 模型路径 |
| `VISION_CHARACTER_EMBEDDING_DEVICE` | `cpu` | 运行设备 |
| `VISION_CHARACTER_EMBEDDING_LOCAL_FILES_ONLY` | `false` | 是否只使用本地模型 |
| `VISION_CHARACTER_CONFIDENT_SCORE` | `0.78` | 角色确认阈值 |

V1.0 Vision 已区分：

- `character_candidates`：候选角色，低置信度时可保守展示。
- `recognized_characters`：已达确认阈值的角色。
- `confidence_report`：视觉可信度报告。
- `low_confidence_policy`：低置信度表达与记忆/Live2D 降级策略。

### Vision 输出契约

- `result.schema_version`：当前固定为 `1.0`
- `result.identity_confirmed`：角色身份是否已确认
- `result.is_confident`：整体视觉分析是否可直接用于回复
- `result.confidence_report.source`：`character_identity` / `scene_understanding` / `unknown_image_type`
- `result.low_confidence_policy.active`：是否启用保守策略
- `result.low_confidence_policy.avoid_identity_assertion`：是否禁止把候选写成已确认
- `result.low_confidence_policy.defer_memory_hint`：是否延迟记忆建议
- `result.low_confidence_policy.suppress_live2d_override`：是否抑制 Live2D 覆盖
- `result.metadata.vision_*`：给 API / Graph / 测试共用的稳定追踪字段

这些策略字段目前没有独立 env 开关，统一由 `VISION_CHARACTER_CONFIDENT_SCORE` 和代码内默认策略控制。

## Memory 配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `MEMORY_LLM_PROVIDER` | `openai` | 记忆策略 LLM provider |
| `MEMORY_LLM_MODEL` | `gpt-4o-mini` | 记忆策略模型 |
| `MEMORY_LLM_API_KEY_ENV` | `OPENAI_API_KEY` | 记忆 LLM key 所在环境变量名 |
| `MEMORY_EMBEDDER_PROVIDER` | `openai` | 记忆 embedding provider |
| `MEMORY_EMBEDDER_MODEL` | `text-embedding-3-small` | 记忆 embedding 模型 |
| `MEMORY_EMBEDDER_API_KEY_ENV` | `OPENAI_API_KEY` | 记忆 embedding key 所在环境变量名 |
| `MEMORY_VECTOR_PROVIDER` | `qdrant` | 记忆向量库 provider |
| `MEMORY_VECTOR_COLLECTION` | `aiagent_long_term_memory` | Qdrant collection |
| `MEMORY_EMBEDDING_DIMS` | `1536` | 记忆 embedding 维度 |
| `MEMORY_RESET_VECTOR_STORE` | `false` | 启动时是否重置向量库 |
| `MEMORY_LONG_TERM_DEFAULT_ENABLED` | `true` | 新用户默认是否启用长期记忆自动检索与写入 |
| `MEMORY_PREFERENCES_PATH` | `data/runtime/memory_preferences.json` | 用户级长期记忆开关持久化文件 |
| `MEMORY_PROMPT_MAX_CHARS` | `1200` | 长期记忆注入 LLM prompt 的最大字符数 |
| `MEMORY_PROMPT_PINNED_LIMIT` | `4` | 每轮最多强制注入的置顶记忆数量 |
| `MEMORY_PROMPT_RELEVANT_LIMIT` | `6` | 每轮最多注入的普通检索记忆数量 |
| `MEMORY_PROMPT_ITEM_MAX_CHARS` | `120` | 单条记忆压缩后的最大字符数 |
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `MEMORY_ENABLE_GRAPH` | `false` | 是否启用图记忆 |
| `MEMORY_GRAPH_PROVIDER` | `neo4j` | 图数据库 provider |
| `NEO4J_URL` | `bolt://localhost:7687` | Neo4j 地址 |
| `NEO4J_USERNAME` | `neo4j` | Neo4j 用户名 |
| `NEO4J_PASSWORD` | 空 | Neo4j 密码 |
| `NEO4J_DATABASE` | `neo4j` | Neo4j database |

V1.0 Memory 已有写入前策略：

- `MemorySafetyFilter`：敏感内容过滤。
- `MemoryDeduper`：重复记忆过滤。
- `MemoryIntakeService`：生成最终写入计划。

生产环境切换 embedding 模型时，`MEMORY_EMBEDDING_DIMS` 必须同步调整，并重建 Qdrant collection。

V1.1 Memory 用户可控能力：

- 用户可以编辑自己的长期记忆。
- 用户可以置顶或取消置顶长期记忆。
- 用户可以把多条冲突记忆手动合并成一条最终版本。
- 用户可以关闭长期记忆自动使用；关闭后主聊天不会自动检索或写入长期记忆，但已存在的记忆仍可查看、编辑、删除和合并。
- 用户长期记忆开关默认值由 `MEMORY_LONG_TERM_DEFAULT_ENABLED` 控制，用户单独偏好保存在 `MEMORY_PREFERENCES_PATH`。

V1.1 第三批后，长期记忆进入 prompt 前会经过压缩：

- 置顶记忆不依赖相似度检索，会优先进入 prompt。
- 普通检索记忆会按相关度、重要度、分层信息筛选。
- prompt 会按身份、边界、偏好、目标等层级组织。
- 如果记忆与用户当前表达冲突，以用户当前表达为准。
- metadata 会记录 `memory_prompt_chars`、`memory_pinned_count`、`memory_prompt_truncated` 等字段。

### V1.1 Memory Prompt 注入规则

- 置顶记忆永远先于检索记忆进入 prompt。
- 记忆层级顺序建议固定为：`profile -> boundary -> preference -> episode -> other`。
- prompt 过长时优先保留置顶和高重要度记忆。
- metadata 会记录 `memory_prompt_layer_counts`、`memory_prompt_selected_ids`、`memory_prompt_selected_layers`、`memory_prompt_compression_reason`。
- 本批次不新增新的 env 开关，先用代码内默认策略收口。

### 记忆写入异步化与审计（V1.1 新增）

| 配置项 | 默认值 | 影响范围 |
| --- | --- | --- |
| `MEMORY_WRITE_ASYNC_ENABLED` | `true` | 回复生成后，记忆抽取/去重/落盘放入单线程池，回复链路不再等待 |
| `MEMORY_WRITE_MAX_PENDING` | `16` | 后台写入队列上限；满则丢弃本次写入并记录 `memory_write_queue_full` |
| `MEMORY_WRITE_AUDIT_TAIL_LIMIT` | `200` | 写入审计单次读取上限 |

失败行为：写入异常只记日志与审计（`status=failed`），**不影响已经返回的回复**。
观测入口：`GET /memory/write/status`、`GET /memory/user/{user_id}/audit`。
审计落盘：`data/runtime/memory_write_audit.jsonl`（JSONL 追加写，属本地运行资产，不入仓）。

## TTS 配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `TTS_PROVIDER` | `mock` | TTS provider |
| `ENABLE_MOCK_TTS` | `true` | 是否强制 mock TTS |
| `ENABLE_LOCAL_AUDIO_PLAYBACK` | `false` | 后端是否本地播放音频 |
| `TTS_TIMEOUT_SECONDS` | `60.0` | TTS 超时 |
| `GPT_SOVITS_BASE_URL` | `http://127.0.0.1:9880` | GPT-SoVITS base URL |
| `GPT_SOVITS_REF_AUDIO_PATH` | 空 | 参考音频路径 |
| `GPT_SOVITS_PROMPT_TEXT` | `你好，欢迎来到直播间。` | 参考音频文本 |
| `GPT_SOVITS_PROMPT_LANG` | `zh` | prompt 语言 |
| `GPT_SOVITS_TEXT_LANG` | `zh` | 输入文本语言 |
| `INDEX_TTS2_BASE_URL` | `http://127.0.0.1:8000` | IndexTTS2 base URL |
| `INDEX_TTS2_REF_AUDIO_PATH` | 空 | 参考音频路径 |
| `INDEX_TTS2_EMO_ALPHA` | `0.6` | 情绪强度 |
| `INDEX_TTS2_USE_EMO_TEXT` | `true` | 是否使用情绪文本 |
| `INDEX_TTS2_MAX_SEGMENT_LENGTH` | `20` | 最大分段长度 |
| `VOXCPM_BASE_URL` | 远程默认值 | VoxCPM base URL |

V1.0 建议移动端播放音频，后端保留 `ENABLE_LOCAL_AUDIO_PLAYBACK=false`。

## ASR 与语音配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `ASR_PROVIDER` | `mock` | ASR provider |
| `ENABLE_MOCK_ASR` | `true` | 是否强制 mock ASR |
| `ASR_API_BASE_URL` | 空 | API ASR base URL |
| `ASR_API_KEY` | 空 | API ASR key |
| `ASR_MODEL` | `whisper-large-v3` | ASR 模型 |
| `ASR_TIMEOUT_SECONDS` | `60.0` | ASR 超时 |
| `ASR_MODEL_SIZE` | `medium` | faster-whisper 模型规格 |
| `ASR_MODEL_PATH` | 空 | 本地 ASR 模型路径 |
| `ASR_DEVICE` | `cpu` | 运行设备 |
| `ASR_COMPUTE_TYPE` | `int8` | 计算类型 |
| `ASR_LANGUAGE` | `zh` | 识别语言 |
| `ASR_SAMPLE_RATE` | `16000` | 录音采样率 |
| `ASR_RECORD_SECONDS` | `10` | 固定录音秒数 |
| `VOICE_CHUNK_SECONDS` | `0.25` | 流式录音块长度 |
| `VOICE_MAX_RECORD_SECONDS` | `8.0` | 最大回合录音时长 |
| `VOICE_SILENCE_SECONDS` | `1.2` | 静音结束阈值 |
| `VOICE_ENERGY_THRESHOLD` | `0.015` | VAD 能量阈值 |
| `VOICE_MAX_UPLOAD_BYTES` | `2621440` | 单个语音上传体积上限（字节） |

### ASR provider 选择

| `ASR_PROVIDER` | 实际实现 | 必需配置 | 适用场景 |
| --- | --- | --- | --- |
| `mock`（默认） | `integrations/asr/mock_asr_client.py` | 无 | 本地开发、CI、主链路 smoke |
| `api` | `integrations/asr/api_asr_client.py`（OpenAI 兼容 `/audio/transcriptions`） | `ASR_API_BASE_URL`、`ASR_API_KEY`、`ASR_MODEL` | 云端 ASR 或自建 whisper 服务 |
| 其他值 | `integrations/asr/faster_whisper_client.py` 本地模型 | `ASR_MODEL_SIZE` / `ASR_MODEL_PATH` / `ASR_DEVICE` / `ASR_COMPUTE_TYPE` | 离线本地识别 |

失败行为：ASR 不可用只影响语音输入，文本聊天与 RAG 不受影响。

### 语音通话状态存储（V1.1 补充）

| 配置项 | 默认值 | 影响范围 |
| --- | --- | --- |
| `VOICE_CALL_STORE_PROVIDER` | `auto` | `auto` = 配了 `REDIS_URL` 就用 Redis，否则用内存；`memory` 仅限单进程；`redis` 强制 Redis |
| `VOICE_CALL_STORE_FAIL_OPEN` | `false` | Redis 故障时是否降级到本机内存。多实例生产必须 `false`，否则通话状态会分叉 |
| `VOICE_CALL_TTL_SECONDS` | `1800` | 活跃通话状态 TTL（最小 60） |
| `VOICE_CALL_ENDED_TTL_SECONDS` | `300` | 已结束通话状态保留时间（最小 60） |
| `VOICE_CALL_LOCK_TTL_SECONDS` | `15` | 分布式状态写锁 TTL（最小 3） |
| `VOICE_CALL_LOCK_WAIT_SECONDS` | `2.0` | 获取同一 call 状态锁的最长等待（最小 0.1） |

Redis 不可用时的整体取舍见 `GET /cloud/ops/readiness` 的 `details.redis_failure_policy`。

V1.0 语音实时接口使用标准 call 状态：

- `status`：`active`、`ended`、`error`
- `phase`：`idle`、`uploaded`、`transcribing`、`thinking`、`speaking`、`empty_turn`、`interrupted`、`completed`、`failed`

## Live2D 配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `LIVE2D_PROVIDER` | `mock` | Live2D 输出 provider |
| `ENABLE_LIVE2D_RUNTIME` | `false` | 是否启用 Python Live2D runtime |

V1.0 后端重点是稳定输出 payload schema，移动端负责模型加载和动作执行。正式 Live2D 资源路径约定：

```text
data/live2d/characters/{character_id}/profile.yaml
data/live2d/characters/{character_id}/model/*.model3.json
data/live2d/backgrounds/
```

## Persona 配置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `PERSONA_NAME` | `config/defaults.py` | fallback persona 名称 |
| `PERSONA_DESCRIPTION` | `config/defaults.py` | fallback persona 描述 |
| `PERSONA_STYLE` | `config/defaults.py` | fallback 说话风格 |
| `PERSONA_RULES` | `config/defaults.py` | fallback 角色规则 |

优先使用 `data/persona/{persona_id}/persona.yaml` 管理正式 persona。`.env` 中的 persona 字段仅作为 fallback。

## Worker 与部署脚本变量

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `WEB_CONCURRENCY` | `2` | API 容器 uvicorn worker 数 |
| `WORKER_CONCURRENCY` | `1` | worker 并发任务循环数 |
| `TASK_QUEUE_NAME` | `default` | worker 监听队列名 |
| `TASK_POP_TIMEOUT_SECONDS` | `5` | worker pop 阻塞超时 |
| `TASK_STALE_SECONDS` | `1800` | stale running task 恢复阈值 |
| `POSTGRES_PASSWORD` | `change-me-before-production` | docker compose Postgres 密码 |

当前代码没有读取 `TASK_MAX_ATTEMPTS` 环境变量。任务最大重试次数由 enqueue 调用传入，V1.0 env 示例不再提供该字段。

## Qt 调试端变量

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `AIAGENT_API_BASE_URL` | `http://127.0.0.1:8000` | Qt 调试端 API 地址 |
| `AIAGENT_API_TIMEOUT` | `120` | Qt 调试端请求超时 |
| `AIAGENT_DESKTOP_USER_ID` | `desktop-user` | Qt 调试端 user id |
| `AIAGENT_DESKTOP_USERNAME` | `Desktop` | Qt 调试端用户名 |
| `AIAGENT_LIVE2D_MODEL3` | 空 | Qt 调试端 Live2D model3 路径 |

这些字段只影响 Qt 调试端，不影响 FastAPI 后端。

## Readiness 与诊断

| 接口 | 用途 | 认证 |
| --- | --- | --- |
| `GET /live` | 进程存活检查 | 无 |
| `GET /health` | API 基础健康检查 | 无 |
| `GET /ready` | 平台 readiness，判断是否可接流量 | 无 |
| `GET /cloud/ops/readiness` | 管理端详细 readiness | `x-cloud-admin-token` |
| `GET /runtime/diagnostics` | 运行时诊断 | 无 |
| `GET /runtime/capabilities` | 能力状态快照 | 无 |

`/ready` 用于负载均衡和容器 healthcheck。`/cloud/ops/readiness` 用于管理员排障，包含更多部署细节，因此需要 admin token。

### 两个就绪端点的输出范围（V1.1 收紧）

| 端点 | 认证 | `purpose` | 内容 |
| --- | --- | --- | --- |
| `GET /ready` | 无 | `public` | 只有 `ok` / `status` / `checks` / `summary` / `items[{name,ok,required,summary}]` / `cloud_mode`；**不含 details 与 action** |
| `GET /cloud/ops/readiness` | `x-cloud-admin-token` | `ops` | 额外含 `details.redis`（含错误串）、`details.gpu`（含各端点地址）、`details.risk_summary`、`details.redis_failure_policy` |

V1.1 新增两个只读检查：

| 检查名 | 含义 |
| --- | --- |
| `gpu_circuit` | 任一 GPU 熔断器处于 `open` 即判 `degraded`；`details.open_circuits` 列出具体服务 |
| `redis_failure_policy` | 展示每个 Redis 依赖的 fail-open / fail-closed 取舍（见下表） |

| Redis 依赖 | 失败策略 | 理由 |
| --- | --- | --- |
| `rate_limit`、`concurrency_limit` | `fail_open` | 宁可放宽限流也不能拒绝正常用户 |
| `task_queue`、`unique_lock` | `fail_closed` | 宁可拒绝任务也不能重复执行破坏一致性 |
| `voice_call_store` | `fallback_memory` | 可退化为单进程内存，但多实例下必须告警 |
| `metrics_store` | `ignore` | 只影响可观测性 |

## 安全要求

- 真实 `.env`、`cloud.tencent.env` 不提交。
- `CLOUD_ADMIN_TOKEN`、`GPU_API_TOKEN`、`OPENAI_API_KEY`、`SILICONFLOW_API`、S3/COS secret 不写入日志。
- 生产环境不要使用 `change-*`、`your-*` 占位符。
- 生产环境确认 `CLOUD_MODE=true`、`RATE_LIMIT_ENABLED=true`、`INFLIGHT_LIMIT_ENABLED=true`。
- 如果 `MEMORY_RESET_VECTOR_STORE=true`，启动时可能清空现有记忆，只能用于测试环境。

## 最终验证入口

V1.0 最终 smoke 指令见：

- [v1-final-smoke.md](v1-final-smoke.md)

V1.0 release checklist 见：

- [v1-release-checklist.md](v1-release-checklist.md)

## V1.1 配置模板补充

### 多模态调试（图片对话）

```dotenv
VISION_PROVIDER=openai
VISION_MODEL=gpt-4o-mini
VISION_API_KEY_ENV=OPENAI_API_KEY
VISION_MAX_IMAGE_BYTES=12582912
VISION_CHARACTER_CONFIDENT_SCORE=0.78
```

验证：`POST /vision/analyze`、`GET /vision/schema`。
`VISION_PROVIDER=mock` 时只验证角色图库召回，不做通用图片理解。

### 本地语音闭环（mock ASR + mock TTS）

```dotenv
ASR_PROVIDER=mock
ENABLE_MOCK_ASR=true
TTS_PROVIDER=mock
ENABLE_MOCK_TTS=true
VOICE_CALL_STORE_PROVIDER=memory
VOICE_CALL_STORE_FAIL_OPEN=false
```

多实例部署必须把 `VOICE_CALL_STORE_PROVIDER` 改成 `redis` 并配置 `REDIS_URL`，
否则通话状态只存在于单个进程内。

### Live2D 调试

```dotenv
LIVE2D_PROVIDER=mock
ENABLE_LIVE2D_RUNTIME=false
AIAGENT_LIVE2D_MODEL3=
```

验证：`GET /live2d/preview`、`GET /live2d/stats`、`scripts/test_live2d_payload.ps1`。

### 云模式（腾讯云）

```dotenv
CLOUD_MODE=true
REDIS_URL=redis://redis:6379/0
CLOUD_ADMIN_TOKEN=<强随机 32 位以上>
STORAGE_PROVIDER=cos
S3_BUCKET=<bucket>
GPU_LLM_BASE_URL=<gpu service>
LIMITER_FAIL_OPEN=true
VOICE_CALL_STORE_PROVIDER=redis
RATE_LIMIT_ENABLED=true
INFLIGHT_LIMIT_ENABLED=true
LOG_FORMAT=json
```

### 索引过期后的重建

```powershell
# 1) 看是否过期、为什么过期
GET /knowledge/index/freshness

# 2) 非云模式：进程内后台重建，立刻返回
POST /knowledge/rebuild  {"force_rebuild": true, "async_rebuild": true}
GET  /knowledge/rebuild/status

# 3) 云模式：进入分布式任务队列（带发起方 request_id，可在 worker 日志检索）
POST /knowledge/rebuild  {"force_rebuild": true}
```

### 配置一致性自检

```powershell
# settings.py / cloud/config.py ↔ .env.example ↔ 本文档 三方比对
.venv\Scripts\python.exe scripts\check_config_sync.py
```
