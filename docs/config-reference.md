# 配置参考

本文档对应 `config/settings.py` 的当前配置结构，用于说明 `.env` 中可配置项的作用、默认值、影响模块和常见用法。

配置加载规则：

- 配置类：`config/settings.py`
- 默认常量：`config/defaults.py`
- `.env` 文件编码：UTF-8
- 未识别配置：会被忽略，`extra="ignore"`

## 基础配置

| 配置项 | 默认值 | 说明 | 影响范围 |
| --- | --- | --- | --- |
| `APP_NAME` | `aiagent` | 应用名称 | 日志、服务标识 |
| `APP_ENV` | `development` | 运行环境 | 环境区分 |
| `LOG_LEVEL` | `INFO` | 日志级别 | `aiagent.common.logger` |
| `API_HOST` | `127.0.0.1` | API 监听地址 | API 启动脚本 |
| `API_PORT` | `8000` | API 监听端口 | API 启动脚本 |
| `API_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | CORS 白名单，多个地址用逗号分隔 | `apps/api/http_server.py` |

最小 API 配置示例：

```env
API_HOST=127.0.0.1
API_PORT=8000
LOG_LEVEL=INFO
```

## 主聊天 LLM

| 配置项 | 默认值 | 说明 | 影响范围 |
| --- | --- | --- | --- |
| `LLM_PROVIDER` | `mock` | 主回复模型 provider | `aiagent.services.llm_service.LLMService` |
| `LLM_MODEL` | `Qwen/Qwen3-8B` | 主回复模型名称 | 主聊天回复 |
| `ENABLE_MOCK_LLM` | `true` | 是否强制使用 mock LLM | 主聊天回复 |
| `LLM_TIMEOUT_SECONDS` | `20.0` | LLM HTTP 请求超时 | 主聊天、状态、规划等 LLM 调用 |
| `LLM_TEMPERATURE` | `0.7` | 采样温度 | 主聊天回复 |
| `LLM_MAX_TOKENS` | `200` | 最大输出 token 数 | 主聊天回复 |

支持的常用 provider：

| Provider | 说明 | 相关配置 |
| --- | --- | --- |
| `mock` | 本地 mock，不访问外部模型 | `ENABLE_MOCK_LLM=true` |
| `openai` | OpenAI 兼容接口 | `OPENAI_API_KEY`, `OPENAI_BASE_URL` |
| `siliconflow` | SiliconFlow OpenAI 兼容接口 | `SILICONFLOW_API`, `SILICONFLOW_BASE_URL` |
| `lmstudio` | LM Studio 本地服务 | `LMSTUDIO_API_KEY`, `LMSTUDIO_BASE_URL` |

SiliconFlow 示例：

```env
ENABLE_MOCK_LLM=false
LLM_PROVIDER=siliconflow
LLM_MODEL=你的聊天模型名称
SILICONFLOW_API=你的 key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
```

LM Studio 示例：

```env
ENABLE_MOCK_LLM=false
LLM_PROVIDER=lmstudio
LLM_MODEL=local-model
LMSTUDIO_API_KEY=lm-studio
LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
```

## 状态分析 LLM

| 配置项 | 默认值 | 说明 | 影响范围 |
| --- | --- | --- | --- |
| `STATE_PROVIDER` | `mock` | 状态分析模型 provider | `aiagent.services.state_llm_service.StateLLMService` |
| `STATE_MODEL` | `Qwen/Qwen3-8B` | 状态分析模型名称 | `aiagent.graphs.state_graph.StateRunner` |
| `ENABLE_MOCK_STATE` | `true` | 是否强制使用 mock 状态分析 | 情绪、意图、用户状态分析 |

该模块用于分析用户输入中的情绪、状态和对话意图。  
如果主聊天已经接入真实模型，但状态分析仍用 mock，可以保持：

```env
ENABLE_MOCK_STATE=true
STATE_PROVIDER=mock
```

如果希望状态分析也接入真实模型：

```env
ENABLE_MOCK_STATE=false
STATE_PROVIDER=siliconflow
STATE_MODEL=你的状态分析模型名称
```

## 回复规划 LLM

| 配置项 | 默认值 | 说明 | 影响范围 |
| --- | --- | --- | --- |
| `PLANNER_PROVIDER` | `mock` | 回复规划模型 provider | `aiagent.services.planner_llm_service.PlannerLLMService` |
| `PLANNER_MODEL` | `Qwen/Qwen3-8B` | 回复规划模型名称 | `aiagent.graphs.planner_graph.PlannerRunner` |
| `ENABLE_MOCK_PLANNER` | `true` | 是否强制使用 mock planner | 检索决策、回复策略 |

规划模块影响：

- 是否检索 RAG
- 如何组织回复
- 是否需要特殊处理用户意图

真实 planner 示例：

```env
ENABLE_MOCK_PLANNER=false
PLANNER_PROVIDER=siliconflow
PLANNER_MODEL=你的规划模型名称
```

## OpenAI / SiliconFlow / LM Studio

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `OPENAI_API_KEY` | 空 | OpenAI API Key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI 兼容接口地址 |
| `SILICONFLOW_API` | 空 | SiliconFlow API Key |
| `SILICONFLOW_BASE_URL` | `https://api.siliconflow.cn/v1` | SiliconFlow API 地址 |
| `LMSTUDIO_API_KEY` | `lm-studio` | LM Studio API Key，占位即可 |
| `LMSTUDIO_BASE_URL` | `http://127.0.0.1:1234/v1` | LM Studio 本地接口地址 |

注意：

- `SILICONFLOW_API` 是当前 `settings.py` 中使用的环境变量名。
- 视觉、RAG、Memory 等模块可以通过单独的 `*_API_KEY_ENV` 指向某个环境变量。
- 例如 `VISION_API_KEY_ENV=SILICONFLOW_API` 表示视觉模块读取 `SILICONFLOW_API` 的值。

## RAG 配置

| 配置项 | 默认值 | 说明 | 影响范围 |
| --- | --- | --- | --- |
| `RAG_EMBEDDING_PROVIDER` | `huggingface` | RAG embedding provider | `aiagent.knowledge.vector_store.LangChainVectorStore` |
| `RAG_EMBEDDING_MODEL_NAME` | `BAAI/bge-small-zh-v1.5` | embedding 模型名 | 向量索引 |
| `RAG_EMBEDDING_MODEL_PATH` | 空 | 本地 embedding 模型路径 | 本地模型加载 |
| `RAG_EMBEDDING_DEVICE` | `cpu` | 运行设备 | embedding 推理 |
| `RAG_EMBEDDING_LOCAL_FILES_ONLY` | `true` | 是否只使用本地文件 | 避免访问 HuggingFace |
| `RAG_EMBEDDING_API_KEY_ENV` | 空 | API embedding key 的环境变量名 | API embedding |
| `RAG_EMBEDDING_BASE_URL` | 空 | API embedding base url | API embedding |
| `RAG_EMBEDDING_BATCH_SIZE` | `64` | embedding 批大小 | 索引构建性能 |
| `RAG_EMBEDDING_DIMENSIONS` | 空 | embedding 维度 | 向量库维度 |
| `RAG_CHUNK_SIZE` | `520` | 文档切块大小 | 文档加载 |
| `RAG_CHUNK_OVERLAP` | `80` | 文档切块重叠 | 文档加载 |
| `RAG_BM25_TOP_K` | `6` | BM25 初筛数量 | 混合检索 |
| `RAG_VECTOR_TOP_K` | `6` | 向量检索数量 | 混合检索 |
| `RAG_FINAL_TOP_K` | `4` | 最终上下文数量 | 注入 LLM 的知识片段数 |

影响文件：

- `aiagent/knowledge/document_loader.py`
- `aiagent/knowledge/vector_store.py`
- `aiagent/knowledge/retriever.py`
- `aiagent/knowledge/rag_pipeline.py`
- `aiagent/graphs/rag_graph.py`
- `apps/api/routes/knowledge.py`

本地 RAG embedding 示例：

```env
RAG_EMBEDDING_PROVIDER=huggingface
RAG_EMBEDDING_MODEL_NAME=BAAI/bge-small-zh-v1.5
RAG_EMBEDDING_MODEL_PATH=data/models/bge-small-zh-v1.5
RAG_EMBEDDING_DEVICE=cpu
RAG_EMBEDDING_LOCAL_FILES_ONLY=true
```

API embedding 示例：

```env
RAG_EMBEDDING_PROVIDER=siliconflow
RAG_EMBEDDING_MODEL_NAME=你的 embedding 模型名称
RAG_EMBEDDING_API_KEY_ENV=SILICONFLOW_API
RAG_EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
```

## 视觉识别配置

| 配置项 | 默认值 | 说明 | 影响范围 |
| --- | --- | --- | --- |
| `VISION_PROVIDER` | `mock` | 视觉模型 provider | `aiagent.services.vision_service.VisionService` |
| `VISION_MODEL` | 空 | 视觉模型名称 | 图片理解 |
| `VISION_API_KEY_ENV` | 空 | 视觉 API key 的环境变量名 | API 视觉模型 |
| `VISION_BASE_URL` | 空 | 视觉模型接口地址 | API 视觉模型 |
| `VISION_TIMEOUT_SECONDS` | `60.0` | 视觉模型请求超时 | 图片理解 |
| `VISION_UPLOAD_DIR` | `data/uploads/images` | 上传图片缓存目录 | `aiagent.vision.image_store.ImageStore` |
| `VISION_MAX_IMAGE_BYTES` | `12582912` | 最大图片大小，约 12 MB | 上传限制 |

视觉模型示例：

```env
VISION_PROVIDER=siliconflow
VISION_MODEL=你的视觉模型名称
VISION_API_KEY_ENV=SILICONFLOW_API
VISION_BASE_URL=https://api.siliconflow.cn/v1
VISION_TIMEOUT_SECONDS=180
```

## 视觉角色识别配置

| 配置项 | 默认值 | 说明 | 影响范围 |
| --- | --- | --- | --- |
| `VISION_CHARACTER_ROOT_DIR` | `data/vision/characters` | 角色图库根目录 | `aiagent.vision.character_registry.CharacterRegistry` |
| `VISION_CHARACTER_INDEX_DIR` | `data/cache/vision/character_index` | FAISS 索引缓存目录 | `aiagent.vision.character_retriever.CharacterRetriever` |
| `VISION_CHARACTER_EMBEDDING_MODEL_NAME` | `clip-ViT-B-32` | 角色图像 embedding 模型名 | 角色相似度检索 |
| `VISION_CHARACTER_EMBEDDING_MODEL_PATH` | 空 | 本地 CLIP 模型路径 | 本地模型加载 |
| `VISION_CHARACTER_EMBEDDING_DEVICE` | `cpu` | 运行设备 | embedding 推理 |
| `VISION_CHARACTER_EMBEDDING_LOCAL_FILES_ONLY` | `false` | 是否只使用本地模型 | 避免联网下载 |
| `VISION_CHARACTER_CONFIDENT_SCORE` | `0.78` | 角色识别置信阈值 | 是否确认角色 |

项目早期测试中常用的角色目录是：

```text
data/characters
```

如果你的图库实际放在这里，需要显式配置：

```env
VISION_CHARACTER_ROOT_DIR=data/characters
VISION_CHARACTER_INDEX_DIR=data/cache/vision/character_index
VISION_CHARACTER_EMBEDDING_MODEL_PATH=data/models/clip
VISION_CHARACTER_EMBEDDING_LOCAL_FILES_ONLY=true
```

索引重建：

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/vision/characters/rebuild?force_rebuild=true"
```

角色识别相关文件：

- `aiagent/vision/character_registry.py`
- `aiagent/vision/character_retriever.py`
- `aiagent/vision/image_store.py`
- `aiagent/services/vision_service.py`
- `aiagent/graphs/vision_graph.py`
- `apps/api/routes/vision.py`

## 长期记忆配置

| 配置项 | 默认值 | 说明 | 影响范围 |
| --- | --- | --- | --- |
| `MEMORY_LLM_PROVIDER` | `openai` | 记忆整理 LLM provider | `aiagent.memory.mem0_memory.Mem0LongTermMemory` |
| `MEMORY_LLM_MODEL` | `gpt-4o-mini` | 记忆整理模型 | 记忆抽取和整理 |
| `MEMORY_LLM_API_KEY_ENV` | `OPENAI_API_KEY` | 记忆 LLM API key 环境变量名 | 记忆 LLM |
| `MEMORY_EMBEDDER_PROVIDER` | `openai` | 记忆 embedding provider | 长期记忆向量化 |
| `MEMORY_EMBEDDER_MODEL` | `text-embedding-3-small` | 记忆 embedding 模型 | 长期记忆向量化 |
| `MEMORY_EMBEDDER_API_KEY_ENV` | `OPENAI_API_KEY` | 记忆 embedding API key 环境变量名 | 长期记忆向量化 |
| `MEMORY_VECTOR_PROVIDER` | `qdrant` | 记忆向量库 provider | 长期记忆存储 |
| `MEMORY_VECTOR_COLLECTION` | `aiagent_long_term_memory` | Qdrant collection 名称 | 长期记忆存储 |
| `MEMORY_EMBEDDING_DIMS` | `1536` | 记忆 embedding 维度 | Qdrant collection 维度 |
| `MEMORY_RESET_VECTOR_STORE` | `false` | 启动时是否重置向量库 | 调试时谨慎使用 |

Qdrant：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `QDRANT_HOST` | `localhost` | Qdrant 地址 |
| `QDRANT_PORT` | `6333` | Qdrant 端口 |

图记忆：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `MEMORY_ENABLE_GRAPH` | `false` | 是否启用图记忆 |
| `MEMORY_GRAPH_PROVIDER` | `neo4j` | 图数据库 provider |
| `NEO4J_URL` | `bolt://localhost:7687` | Neo4j 地址 |
| `NEO4J_USERNAME` | `neo4j` | Neo4j 用户名 |
| `NEO4J_PASSWORD` | 空 | Neo4j 密码 |
| `NEO4J_DATABASE` | `neo4j` | Neo4j 数据库 |

SiliconFlow 记忆 embedding 示例：

```env
MEMORY_LLM_PROVIDER=siliconflow
MEMORY_LLM_MODEL=你的记忆整理模型
MEMORY_LLM_API_KEY_ENV=SILICONFLOW_API

MEMORY_EMBEDDER_PROVIDER=siliconflow
MEMORY_EMBEDDER_MODEL=你的 embedding 模型
MEMORY_EMBEDDER_API_KEY_ENV=SILICONFLOW_API
MEMORY_VECTOR_PROVIDER=qdrant
MEMORY_VECTOR_COLLECTION=aiagent_long_term_memory
MEMORY_EMBEDDING_DIMS=1024
```

注意：

- `MEMORY_EMBEDDING_DIMS` 必须和实际 embedding 模型输出维度一致。
- Qdrant collection 已创建后，如果维度变了，需要重建 collection。
- `MEMORY_RESET_VECTOR_STORE=true` 可能清空已有记忆，只建议测试环境使用。

影响文件：

- `aiagent/memory/mem0_memory.py`
- `aiagent/graphs/memory_graph.py`
- `aiagent/services/memory_policy_llm_service.py`
- `apps/api/routes/memory.py`

## TTS 配置

| 配置项 | 默认值 | 说明 | 影响范围 |
| --- | --- | --- | --- |
| `TTS_PROVIDER` | `mock` | TTS provider | `aiagent.expression.tts_dispatcher.TTSDispatcher` |
| `ENABLE_MOCK_TTS` | `true` | 是否强制使用 mock TTS | 语音合成 |
| `TTS_TIMEOUT_SECONDS` | `60.0` | TTS 请求超时 | 外部 TTS 服务 |

### GPT-SoVITS

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `GPT_SOVITS_BASE_URL` | `http://127.0.0.1:9880` | GPT-SoVITS 服务地址 |
| `GPT_SOVITS_REF_AUDIO_PATH` | 空 | 参考音频路径 |
| `GPT_SOVITS_PROMPT_TEXT` | 当前源码里该默认值存在乱码，建议在 `.env` 中覆盖 | 参考音频文本 |
| `GPT_SOVITS_PROMPT_LANG` | `zh` | prompt 语言 |
| `GPT_SOVITS_TEXT_LANG` | `zh` | 输入文本语言 |

示例：

```env
ENABLE_MOCK_TTS=false
TTS_PROVIDER=gpt_sovits
GPT_SOVITS_BASE_URL=http://127.0.0.1:9880
GPT_SOVITS_REF_AUDIO_PATH=data/audio/ref/yzl.wav
GPT_SOVITS_PROMPT_TEXT=你好，欢迎来到直播间。
GPT_SOVITS_PROMPT_LANG=zh
GPT_SOVITS_TEXT_LANG=zh
```

### IndexTTS2

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `INDEX_TTS2_BASE_URL` | `http://127.0.0.1:8000` | IndexTTS2 服务地址 |
| `INDEX_TTS2_REF_AUDIO_PATH` | 空 | 参考音频路径 |
| `INDEX_TTS2_EMO_ALPHA` | `0.6` | 情绪强度 |
| `INDEX_TTS2_USE_EMO_TEXT` | `true` | 是否使用情绪文本 |
| `INDEX_TTS2_MAX_SEGMENT_LENGTH` | `20` | 最大分段长度 |

示例：

```env
ENABLE_MOCK_TTS=false
TTS_PROVIDER=indextts2
INDEX_TTS2_BASE_URL=http://127.0.0.1:8001
INDEX_TTS2_REF_AUDIO_PATH=data/audio/ref/yzl.wav
INDEX_TTS2_EMO_ALPHA=0.6
INDEX_TTS2_USE_EMO_TEXT=true
```

### VoxCPM

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `VOXCPM_BASE_URL` | 远程服务地址 | VoxCPM 服务地址 |

示例：

```env
ENABLE_MOCK_TTS=false
TTS_PROVIDER=voxcpm
VOXCPM_BASE_URL=你的 VoxCPM 服务地址
```

影响文件：

- `aiagent/expression/tts_dispatcher.py`
- `integrations/tts/mock_tts_client.py`
- `integrations/tts/gpt_sovits_client.py`
- `integrations/tts/indextts2_client.py`
- `integrations/tts/voxcpm_client.py`

## ASR 配置

| 配置项 | 默认值 | 说明 | 影响范围 |
| --- | --- | --- | --- |
| `ASR_PROVIDER` | `mock` | ASR provider | `aiagent.perception.asr_listener.ASRListener` |
| `ENABLE_MOCK_ASR` | `true` | 是否强制使用 mock ASR | 语音识别 |
| `ASR_MODEL_SIZE` | `medium` | faster-whisper 模型规格 | 本地 ASR |
| `ASR_MODEL_PATH` | 空 | 本地模型路径 | 本地 ASR |
| `ASR_DEVICE` | `cpu` | 运行设备 | 本地 ASR |
| `ASR_COMPUTE_TYPE` | `int8` | 计算类型 | 本地 ASR |
| `ASR_LANGUAGE` | `zh` | 识别语言 | 本地 ASR |
| `ASR_SAMPLE_RATE` | `16000` | 采样率 | 麦克风录音 |
| `ASR_RECORD_SECONDS` | `10` | 单次录音秒数 | 录音控制 |

语音会话参数：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `VOICE_CHUNK_SECONDS` | `0.25` | 音频块长度 |
| `VOICE_MAX_RECORD_SECONDS` | `8.0` | 最大录音时长 |
| `VOICE_SILENCE_SECONDS` | `1.2` | 静音结束阈值 |
| `VOICE_ENERGY_THRESHOLD` | `0.015` | VAD 能量阈值 |

faster-whisper 示例：

```env
ENABLE_MOCK_ASR=false
ASR_PROVIDER=faster_whisper
ASR_MODEL_SIZE=medium
ASR_MODEL_PATH=data/models/faster-whisper-medium
ASR_DEVICE=cpu
ASR_COMPUTE_TYPE=int8
ASR_LANGUAGE=zh
```

影响文件：

- `aiagent/perception/asr_listener.py`
- `aiagent/perception/voice_turn_manager.py`
- `aiagent/perception/voice_session_controller.py`
- `integrations/asr/faster_whisper_client.py`
- `integrations/asr/mock_asr_client.py`
- `integrations/asr/microphone.py`
- `integrations/asr/vad.py`

## Persona 配置

| 配置项 | 默认值 | 说明 | 影响范围 |
| --- | --- | --- | --- |
| `PERSONA_NAME` | `config/defaults.py` 中定义 | 默认 persona 名称 | fallback persona |
| `PERSONA_DESCRIPTION` | `config/defaults.py` 中定义 | 默认 persona 描述 | fallback persona |
| `PERSONA_STYLE` | `config/defaults.py` 中定义 | 默认说话风格 | fallback persona |
| `PERSONA_RULES` | `config/defaults.py` 中定义 | 默认 persona 规则 | fallback persona |

注意：

- 当前 `config/defaults.py` 中 persona 默认文本存在乱码，建议后续修正源码默认值。
- 实际角色配置应优先使用 `data/persona/{persona_id}/persona.yaml`。

影响文件：

- `aiagent/persona/persona_loader.py`
- `aiagent/persona/persona_manager.py`
- `aiagent/persona/persona_runtime.py`
- `aiagent/persona/persona_guard.py`
- `domain/persona/persona_profile.py`

## Live2D 配置

| 配置项 | 默认值 | 说明 | 影响范围 |
| --- | --- | --- | --- |
| `LIVE2D_PROVIDER` | `mock` | Live2D 输出 provider | `aiagent.expression.live2d_payload_dispatcher` |
| `ENABLE_LIVE2D_RUNTIME` | `false` | 是否启用 Python Live2D runtime | `integrations/live2d/live2d_py_runtime.py` |

当前 Live2D 资源约定：

```text
data/live2d/characters/{character_id}/profile.yaml
data/live2d/characters/{character_id}/model/*.model3.json
data/live2d/backgrounds/
```

常见配置：

```env
LIVE2D_PROVIDER=file
ENABLE_LIVE2D_RUNTIME=true
```

如果只需要 mock 输出：

```env
LIVE2D_PROVIDER=mock
ENABLE_LIVE2D_RUNTIME=false
```

影响文件：

- `aiagent/live2d/models.py`
- `aiagent/live2d/registry.py`
- `aiagent/live2d/payload_builder.py`
- `aiagent/live2d/motion_mapper.py`
- `aiagent/live2d/scene_mapper.py`
- `aiagent/expression/live2d_payload_dispatcher.py`
- `aiagent/expression/mock_live2d_dispatcher.py`
- `integrations/live2d/*`
- `apps/api/routes/live2d.py`

## 推荐配置组合

### 纯文本开发

```env
ENABLE_MOCK_LLM=false
LLM_PROVIDER=siliconflow
LLM_MODEL=你的聊天模型名称
SILICONFLOW_API=你的 key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

ENABLE_MOCK_STATE=true
ENABLE_MOCK_PLANNER=true
ENABLE_MOCK_TTS=true
ENABLE_MOCK_ASR=true
VISION_PROVIDER=mock
LIVE2D_PROVIDER=mock
```

### 多模态开发

```env
ENABLE_MOCK_LLM=false
LLM_PROVIDER=siliconflow
LLM_MODEL=你的聊天模型名称
SILICONFLOW_API=你的 key

VISION_PROVIDER=siliconflow
VISION_MODEL=你的视觉模型名称
VISION_API_KEY_ENV=SILICONFLOW_API
VISION_BASE_URL=https://api.siliconflow.cn/v1
VISION_TIMEOUT_SECONDS=180

VISION_CHARACTER_ROOT_DIR=data/characters
VISION_CHARACTER_INDEX_DIR=data/cache/vision/character_index
VISION_CHARACTER_EMBEDDING_MODEL_PATH=data/models/clip
VISION_CHARACTER_EMBEDDING_LOCAL_FILES_ONLY=true
```

### 本地语音开发

```env
ENABLE_MOCK_ASR=false
ASR_PROVIDER=faster_whisper
ASR_MODEL_PATH=data/models/faster-whisper-medium
ASR_DEVICE=cpu
ASR_COMPUTE_TYPE=int8

ENABLE_MOCK_TTS=false
TTS_PROVIDER=gpt_sovits
GPT_SOVITS_BASE_URL=http://127.0.0.1:9880
GPT_SOVITS_REF_AUDIO_PATH=data/audio/ref/yzl.wav
GPT_SOVITS_PROMPT_TEXT=你好，欢迎来到直播间。
```

### Live2D 调试

```env
LIVE2D_PROVIDER=file
ENABLE_LIVE2D_RUNTIME=true
```

并确认存在：

```text
data/live2d/characters/yzl/profile.yaml
data/live2d/characters/yzl/model/yzl.model3.json
```

## 诊断与测试

运行时诊断：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_runtime_diagnostics.ps1
```

统一测试：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_all.ps1 -ContinueOnFailure
```

视觉单测：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_vision.ps1 `
  -ImagePath "data\characters\luotianyi\images\LUO1.jpg"
```

多模态单测：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_multimodal_chat.ps1 `
  -ImagePath "data\characters\luotianyi\images\LUO1.jpg"
```

Live2D 单测：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_live2d_payload.ps1
```

## 已知配置风险

当前代码中有几处默认中文文本疑似因编码问题变成乱码：

- `config/defaults.py` 中的 persona 默认文本
- `config/settings.py` 中的 `GPT_SOVITS_PROMPT_TEXT`
- 个别 API route 旧版本中出现过乱码 prompt

建议后续单独做一次编码清理：

1. 统一以 UTF-8 保存源码。
2. 修正默认中文文本。
3. 避免 PowerShell 非 UTF-8 输出污染文件。
4. 对中文配置优先放入 `.env` 或 YAML 数据文件。
