# 项目全量文件盘点

说明：本文档基于当前工作区自动生成。源码、配置、脚本、Markdown、JSON、YAML 会按文本读取并摘要；图片、音频、压缩包、索引、模型和运行缓存只按路径、扩展名和用途说明，不展开二进制内容。

- 已盘点文件总数：932
- 二进制、资源或生成物：254
- 文本、源码或配置：678

## 高风险重复功能地图

- Live2D 目前分三层：`aiagent/live2d` 负责领域模型和 payload，`aiagent/expression/live2d_payload_dispatcher.py` 负责输出调度，`integrations/live2d/*` 负责文件、Python runtime、Qt 控件等集成。后续应扩展这些文件，不要再新增平行 dispatcher。
- 视觉识图链路已经存在：`aiagent/vision/*`、`aiagent/services/vision_service.py`、`aiagent/graphs/vision_graph.py`、`apps/api/routes/vision.py` 和 `/chat/multimodal`。新增识图能力应挂在 VisionService 或 VisionGraph。
- RAG 链路已经存在：`aiagent/knowledge/*`、`aiagent/graphs/rag_graph.py`、`apps/api/routes/knowledge.py`。不要新增第二套索引或检索实现。
- 记忆链路已经存在：`aiagent/memory/mem0_memory.py`、`aiagent/graphs/memory_graph.py`、`apps/api/routes/memory.py`。新增记忆策略应优先改 MemoryRunner 或 MemoryPolicyLLMService。
- Qt 主调试界面是 `apps/desktop_qt/chat_window.py`。后续 UI 应以 panel/widget 接入，除调试窗口外，不要新增互相割裂的主窗口。

## FastAPI 应用与路由

### `apps/api/__init__.py`
- 大小：0 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `apps/api/http_server.py`
- 大小：1722 bytes
- 类型：文本/源码/配置
- 作用：HTTP API 路由或 FastAPI 应用模块；函数：on_startup、root
- 主要依赖：__future__、apps.api.routes.audio、apps.api.routes.chat、apps.api.routes.control、apps.api.routes.health、apps.api.routes.knowledge、apps.api.routes.live2d、apps.api.routes.memory、apps.api.routes.multimodal_chat、apps.api.routes.vision、apps.api.routes.voice、config.settings、fastapi、fastapi.middleware.cors、logging
- 顶层函数：on_startup、root

### `apps/api/routes/__init__.py`
- 大小：0 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `apps/api/routes/audio.py`
- 大小：1050 bytes
- 类型：文本/源码/配置
- 作用：HTTP API 路由或 FastAPI 应用模块；函数：get_audio
- 主要依赖：__future__、fastapi、fastapi.responses、pathlib
- 顶层函数：get_audio

### `apps/api/routes/chat.py`
- 大小：3592 bytes
- 类型：文本/源码/配置
- 作用：HTTP API 路由或 FastAPI 应用模块；类：ChatRequest；函数：chat、_build_live2d_payload
- 主要依赖：__future__、apps.core.runtime_registry、fastapi、json、logging、pydantic、traceback、typing
- 类 `ChatRequest`：方法 无显式方法
- 顶层函数：chat、_build_live2d_payload

### `apps/api/routes/control.py`
- 大小：3634 bytes
- 类型：文本/源码/配置
- 作用：HTTP API 路由或 FastAPI 应用模块；类：ControlInputRequest、PauseRequest、InterruptRequest；函数：control_input、control_status、pause_control、resume_control、reset_context、interrupt_control
- 主要依赖：apps.core.runtime_registry、fastapi、json、pydantic
- 类 `ControlInputRequest`：方法 无显式方法
- 类 `PauseRequest`：方法 无显式方法
- 类 `InterruptRequest`：方法 无显式方法
- 顶层函数：control_input、control_status、pause_control、resume_control、reset_context、interrupt_control

### `apps/api/routes/health.py`
- 大小：189 bytes
- 类型：文本/源码/配置
- 作用：HTTP API 路由或 FastAPI 应用模块；函数：health_check
- 主要依赖：fastapi
- 顶层函数：health_check

### `apps/api/routes/knowledge.py`
- 大小：2558 bytes
- 类型：文本/源码/配置
- 作用：HTTP API 路由或 FastAPI 应用模块；类：KnowledgeSearchRequest、KnowledgeRebuildRequest；函数：knowledge_stats、knowledge_rebuild_status、knowledge_search、knowledge_rebuild
- 主要依赖：apps.core.runtime_registry、fastapi、json、pydantic
- 类 `KnowledgeSearchRequest`：方法 无显式方法
- 类 `KnowledgeRebuildRequest`：方法 无显式方法
- 顶层函数：knowledge_stats、knowledge_rebuild_status、knowledge_search、knowledge_rebuild

### `apps/api/routes/live2d.py`
- 大小：7578 bytes
- 类型：文本/源码/配置
- 作用：HTTP API 路由或 FastAPI 应用模块；类：Live2DPreviewRequest、Live2DInspectRequest、Live2DLoadRequest、Live2DApplyPayloadRequest、Live2DScanRequest、Live2DGenerateProfileRequest；函数：live2d_stats、live2d_preview、live2d_runtime_status、live2d_runtime_inspect、live2d_runtime_load、live2d_runtime_apply_payload、live2d_models_scan、live2d_profile_generate、_resolve_model3_json、_build_registry、_build_payload_builder、_json_response
- 主要依赖：__future__、aiagent.live2d.motion_mapper、aiagent.live2d.payload_builder、aiagent.live2d.registry、aiagent.live2d.scene_mapper、fastapi、integrations.live2d.live2d_py_runtime、integrations.live2d.model_scanner、integrations.live2d.profile_generator、integrations.live2d.renderer、json、pydantic、traceback、typing
- 类 `Live2DPreviewRequest`：方法 无显式方法
- 类 `Live2DInspectRequest`：方法 无显式方法
- 类 `Live2DLoadRequest`：方法 无显式方法
- 类 `Live2DApplyPayloadRequest`：方法 无显式方法
- 类 `Live2DScanRequest`：方法 无显式方法
- 类 `Live2DGenerateProfileRequest`：方法 无显式方法
- 顶层函数：live2d_stats、live2d_preview、live2d_runtime_status、live2d_runtime_inspect、live2d_runtime_load、live2d_runtime_apply_payload、live2d_models_scan、live2d_profile_generate、_resolve_model3_json、_build_registry、_build_payload_builder、_json_response、_error_response

### `apps/api/routes/memory.py`
- 大小：1801 bytes
- 类型：文本/源码/配置
- 作用：HTTP API 路由或 FastAPI 应用模块；函数：get_user_memory、get_user_memory_stats、search_user_memory、delete_user_memory
- 主要依赖：apps.core.runtime_registry、fastapi、json
- 顶层函数：get_user_memory、get_user_memory_stats、search_user_memory、delete_user_memory
- 注意：属于记忆链路，可能依赖外部向量数据库

### `apps/api/routes/multimodal_chat.py`
- 大小：2901 bytes
- 类型：文本/源码/配置
- 作用：HTTP API 路由或 FastAPI 应用模块；函数：multimodal_chat、_json_response、_error_response
- 主要依赖：__future__、apps.core.runtime_registry、fastapi、json、logging、traceback
- 顶层函数：multimodal_chat、_json_response、_error_response

### `apps/api/routes/vision.py`
- 大小：5511 bytes
- 类型：文本/源码/配置
- 作用：HTTP API 路由或 FastAPI 应用模块；函数：analyze_image、vision_chat、rebuild_character_index、character_index_stats、_json_response、_error_response
- 主要依赖：__future__、apps.core.runtime_registry、fastapi、json、logging、traceback
- 顶层函数：analyze_image、vision_chat、rebuild_character_index、character_index_stats、_json_response、_error_response

### `apps/api/routes/voice.py`
- 大小：7410 bytes
- 类型：文本/源码/配置
- 作用：HTTP API 路由或 FastAPI 应用模块；类：VoiceTurnRequest、InterruptRequest；函数：_runtime_or_error、transcribe_voice、voice_turn、interrupt_voice、voice_state
- 主要依赖：__future__、apps.core.runtime_registry、fastapi、json、logging、pathlib、pydantic、traceback
- 类 `VoiceTurnRequest`：方法 无显式方法
- 类 `InterruptRequest`：方法 无显式方法
- 顶层函数：_runtime_or_error、transcribe_voice、voice_turn、interrupt_voice、voice_state

## LLM、视觉、状态、规划、记忆策略服务

### `aiagent/services/__init__.py`
- 大小：28 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `aiagent/services/llm_service.py`
- 大小：6886 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：LLMService
- 主要依赖：__future__、collections.abc、config.providers、config.settings、httpx、langchain_core.language_models、langchain_core.messages、langchain_openai、logging、typing
- 类 `LLMService`：方法 __init__、_resolve_provider_config、get_chat_model、build_messages、invoke_messages、invoke_with_memory、_invoke_lmstudio、_to_openai_message、_normalize_content

### `aiagent/services/memory_policy_llm_service.py`
- 大小：5476 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：MemoryPolicyLLMService
- 主要依赖：__future__、aiagent.schemas.memory、aiagent.services.llm_service、json、langchain_core.messages、logging、re、typing
- 类 `MemoryPolicyLLMService`：方法 __init__、decide_write、_build_prompt、_parse、_extract_json、_safe_enum
- 注意：属于记忆链路，可能依赖外部向量数据库

### `aiagent/services/planner_llm_service.py`
- 大小：6675 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：PlannerLLMService
- 主要依赖：__future__、aiagent.graphs.graph_model、config.providers、config.settings、httpx、json、logging、typing
- 类 `PlannerLLMService`：方法 __init__、infer_plan、_infer_with_lmstudio、_infer_with_openai、_resolve_openai_like_config、_extract_content、_parse_output、_fallback_plan

### `aiagent/services/state_llm_service.py`
- 大小：5991 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：StateLLMService
- 主要依赖：__future__、aiagent.graphs.graph_model、config.providers、config.settings、httpx、json、logging、typing
- 类 `StateLLMService`：方法 __init__、infer_state、_infer_with_lmstudio、_infer_with_openai、_resolve_openai_like_config、_extract_content、_parse_output、_fallback_state

### `aiagent/services/vision_service.py`
- 大小：17529 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：VisionService
- 主要依赖：PIL、__future__、aiagent.graphs.graph_model、aiagent.vision.character_retriever、aiagent.vision.image_store、base64、httpx、io、json、logging、mimetypes、pathlib、typing
- 类 `VisionService`：方法 __init__、analyze_upload、analyze_local_path、analyze_stored_image、rebuild_character_index、character_index_stats、_analyze_with_model、_openai_compatible_vision、_mock_model_result、_build_result、_normalize_model_characters、_format_candidates_for_prompt、_image_to_data_url、_extract_json
- 注意：属于视觉角色识别链路，避免重复新增检索器

## Live2D 角色、背景配置与资源

### `data/live2d/backgrounds/desk_work.yaml`
- 大小：144 bytes
- 类型：文本/源码/配置
- 作用：YAML 配置文件，用于 persona、Live2D、数据集、背景或服务配置。

### `data/live2d/backgrounds/room_default.yaml`
- 大小：150 bytes
- 类型：文本/源码/配置
- 作用：YAML 配置文件，用于 persona、Live2D、数据集、背景或服务配置。

### `data/live2d/backgrounds/room_night.yaml`
- 大小：145 bytes
- 类型：文本/源码/配置
- 作用：YAML 配置文件，用于 persona、Live2D、数据集、背景或服务配置。

### `data/live2d/characters/yzl/profile.yaml`
- 大小：1831 bytes
- 类型：文本/源码/配置
- 作用：YAML 配置文件，用于 persona、Live2D、数据集、背景或服务配置。

## Live2D 领域模型与 Payload

### `aiagent/live2d/__init__.py`
- 大小：784 bytes
- 类型：文本/源码/配置
- 作用：Live2D 相关模块
- 主要依赖：aiagent.live2d.models、aiagent.live2d.motion_mapper、aiagent.live2d.payload_builder、aiagent.live2d.registry、aiagent.live2d.scene_mapper

### `aiagent/live2d/models.py`
- 大小：2145 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：Live2DExpressionAsset、Live2DMotionAsset、Live2DCharacterProfile、Live2DBackgroundProfile、Live2DCharacterCommand、Live2DSceneCommand、Live2DPayload
- 主要依赖：__future__、pydantic、typing
- 类 `Live2DExpressionAsset`：方法 无显式方法
- 类 `Live2DMotionAsset`：方法 无显式方法
- 类 `Live2DCharacterProfile`：方法 无显式方法
- 类 `Live2DBackgroundProfile`：方法 无显式方法
- 类 `Live2DCharacterCommand`：方法 无显式方法
- 类 `Live2DSceneCommand`：方法 无显式方法
- 类 `Live2DPayload`：方法 无显式方法

### `aiagent/live2d/motion_mapper.py`
- 大小：2165 bytes
- 类型：文本/源码/配置
- 作用：Live2D 相关模块；类：Live2DMotionMapper
- 主要依赖：__future__、aiagent.live2d.models
- 类 `Live2DMotionMapper`：方法 resolve_expression、resolve_motion、_find_expression、_find_motion

### `aiagent/live2d/payload_builder.py`
- 大小：3974 bytes
- 类型：文本/源码/配置
- 作用：Live2D 相关模块；类：Live2DPayloadBuilder
- 主要依赖：__future__、aiagent.live2d.models、aiagent.live2d.motion_mapper、aiagent.live2d.registry、aiagent.live2d.scene_mapper、typing
- 类 `Live2DPayloadBuilder`：方法 __init__、build
- 注意：属于 Live2D 调度链路，避免重复新增 dispatcher

### `aiagent/live2d/registry.py`
- 大小：3936 bytes
- 类型：文本/源码/配置
- 作用：人格或 YAML 配置加载模块；类：Live2DRegistry
- 主要依赖：__future__、aiagent.live2d.models、pathlib、typing、yaml
- 类 `Live2DRegistry`：方法 __init__、load、get_character、get_background、all_characters、all_backgrounds、stats、_load_characters、_load_backgrounds、_read_yaml

### `aiagent/live2d/scene_mapper.py`
- 大小：1277 bytes
- 类型：文本/源码/配置
- 作用：Live2D 相关模块；类：Live2DSceneMapper
- 主要依赖：__future__
- 类 `Live2DSceneMapper`：方法 scene_from_context

## Next.js Web 前端骨架

### `apps/web/next.config.ts`
- 大小：51 bytes
- 类型：文本/源码/配置
- 作用：Next.js Web 前端源码、配置或样式文件。

### `apps/web/package.json`
- 大小：165 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `apps/web/README.md`
- 大小：48 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。aiagent web

### `apps/web/src/app/globals.css`
- 大小：49 bytes
- 类型：文本/源码/配置
- 作用：Next.js Web 前端源码、配置或样式文件。

### `apps/web/src/app/layout.tsx`
- 大小：176 bytes
- 类型：文本/源码/配置
- 作用：Next.js Web 前端源码、配置或样式文件。

### `apps/web/src/app/page.tsx`
- 大小：89 bytes
- 类型：文本/源码/配置
- 作用：Next.js Web 前端源码、配置或样式文件。

### `apps/web/src/components/README.md`
- 大小：58 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Components

### `apps/web/src/features/agent-state/README.md`
- 大小：48 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Agent State

### `apps/web/src/features/dashboard/README.md`
- 大小：44 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Dashboard

### `apps/web/src/features/live-chat/README.md`
- 大小：44 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Live Chat

### `apps/web/src/features/memory-panel/README.md`
- 大小：50 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Memory Panel
- 注意：属于记忆链路，可能依赖外部向量数据库

### `apps/web/src/features/persona-panel/README.md`
- 大小：52 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Persona Panel

### `apps/web/src/features/stream-control/README.md`
- 大小：54 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Stream Control

### `apps/web/src/lib/README.md`
- 大小：48 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Lib

## Qt 桌面调试前端

### `apps/desktop_qt/__init__.py`
- 大小：0 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `apps/desktop_qt/api_client.py`
- 大小：7751 bytes
- 类型：文本/源码/配置
- 作用：外部服务客户端或 API 调用适配模块；类：APIClient
- 主要依赖：__future__、httpx、json、pathlib、typing、urllib.parse
- 类 `APIClient`：方法 __init__、close、_request、_parse_response、get_health、send_chat、transcribe_audio、get_voice_state、interrupt_voice、get_user_memory、get_memory_stats、search_user_memory、send_multimodal_chat、_guess_image_mime、clear_user_memory

### `apps/desktop_qt/chat_window.py`
- 大小：29901 bytes
- 类型：文本/源码/配置
- 作用：Qt 桌面 UI 或控件模块；类：Worker、ChatBubble、ChatWindow
- 主要依赖：PySide6.QtCore、PySide6.QtWidgets、__future__、apps.desktop_qt.api_client、apps.desktop_qt.live2d_view_panel、apps.desktop_qt.recorder、apps.desktop_qt.user_identity、pathlib、traceback
- 类 `Worker`：方法 __init__、run
- 类 `ChatBubble`：方法 __init__
- 类 `ChatWindow`：方法 __init__、closeEvent、_load_or_create_identity、_build_ui、_build_left_panel、_build_right_panel、_build_section_card、_build_text_panel、_set_status、_append_system_message、_append_user_message、_append_agent_message、_append_bubble、_set_busy、select_image_file

### `apps/desktop_qt/live2d_debug_window.py`
- 大小：1482 bytes
- 类型：文本/源码/配置
- 作用：Qt 桌面 UI 或控件模块；类：Live2DDebugWindow；函数：main
- 主要依赖：PySide6.QtWidgets、__future__、apps.desktop_qt.live2d_view_panel、sys
- 类 `Live2DDebugWindow`：方法 __init__
- 顶层函数：main

### `apps/desktop_qt/live2d_view_panel.py`
- 大小：3672 bytes
- 类型：文本/源码/配置
- 作用：Qt 桌面 UI 或控件模块；类：Live2DViewPanel
- 主要依赖：PySide6.QtCore、PySide6.QtWidgets、__future__、aiagent.live2d.registry、integrations.live2d.qt_live2d_widget
- 类 `Live2DViewPanel`：方法 __init__、load_default_character、load_character、apply_payload、set_expression、start_motion、_update_status

### `apps/desktop_qt/main.py`
- 大小：307 bytes
- 类型：文本/源码/配置
- 作用：Qt 桌面 UI 或控件模块；函数：main
- 主要依赖：PySide6.QtWidgets、__future__、apps.desktop_qt.chat_window、sys
- 顶层函数：main

### `apps/desktop_qt/recorder.py`
- 大小：2384 bytes
- 类型：文本/源码/配置
- 作用：音频、TTS 或语音模块；类：AudioRecorder
- 主要依赖：numpy、pathlib、scipy.io.wavfile、sounddevice、uuid
- 类 `AudioRecorder`：方法 __init__、is_recording、start_recording、stop_recording、record

### `apps/desktop_qt/user_identity.py`
- 大小：2279 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：DesktopIdentity、DesktopIdentityStore
- 主要依赖：__future__、json、pathlib、pydantic、uuid
- 类 `DesktopIdentity`：方法 无显式方法
- 类 `DesktopIdentityStore`：方法 __init__、load_identity、create_identity、save_identity、update_username、rebuild_identity、clear_identity、_normalize_username

## RAG 知识库管线

### `aiagent/knowledge/__init__.py`
- 大小：576 bytes
- 类型：文本/源码/配置
- 作用：RAG、Embedding 或检索模块
- 主要依赖：aiagent.knowledge.document_loader、aiagent.knowledge.index_builder、aiagent.knowledge.rag_pipeline、aiagent.knowledge.reranker、aiagent.knowledge.retriever、aiagent.knowledge.vector_store

### `aiagent/knowledge/document_loader.py`
- 大小：10233 bytes
- 类型：文本/源码/配置
- 作用：视觉、图片或角色识别模块；类：DocumentLoader
- 主要依赖：__future__、hashlib、json、langchain_core.documents、langchain_text_splitters、logging、pathlib、typing
- 类 `DocumentLoader`：方法 __init__、load_directory、load_file、split_documents、_load_markdown、_split_markdown_document、_split_plain_document、_split_plain_documents、_load_json、_load_jsonl、_load_pdf、_build_document、_title_from_markdown_metadata、_json_to_text、_infer_title

### `aiagent/knowledge/index_builder.py`
- 大小：1691 bytes
- 类型：文本/源码/配置
- 作用：RAG、Embedding 或检索模块；类：KnowledgeIndexBuilder
- 主要依赖：__future__、aiagent.knowledge.document_loader、aiagent.knowledge.rag_pipeline、aiagent.knowledge.reranker、aiagent.knowledge.retriever、aiagent.knowledge.vector_store、pathlib、typing
- 类 `KnowledgeIndexBuilder`：方法 __init__、build、test_query

### `aiagent/knowledge/rag_pipeline.py`
- 大小：9041 bytes
- 类型：文本/源码/配置
- 作用：视觉、图片或角色识别模块；类：RAGPipeline
- 主要依赖：__future__、aiagent.knowledge.document_loader、aiagent.knowledge.reranker、aiagent.knowledge.retriever、aiagent.knowledge.vector_store、config.paths、datetime、json、langchain_core.documents、pathlib、threading、typing
- 类 `RAGPipeline`：方法 __init__、build_index、rebuild_async、build_status、_rebuild_worker、_build_index_inner、ensure_ready、retrieve、search、format_for_prompt、debug_retrieve、stats、_format_chunk、_save_documents、_load_documents
- 注意：属于 RAG 链路，避免重复新增索引入口

### `aiagent/knowledge/reranker.py`
- 大小：2447 bytes
- 类型：文本/源码/配置
- 作用：RAG、Embedding 或检索模块；类：SimpleReranker
- 主要依赖：__future__、aiagent.knowledge.retriever
- 类 `SimpleReranker`：方法 rerank、_has_exact_term_overlap

### `aiagent/knowledge/retriever.py`
- 大小：5256 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：RetrievedChunk、_Candidate、HybridRetriever
- 主要依赖：__future__、aiagent.knowledge.vector_store、collections、dataclasses、langchain_community.retrievers、langchain_core.documents、pydantic、re
- 类 `RetrievedChunk`：方法 无显式方法
- 类 `_Candidate`：方法 无显式方法
- 类 `HybridRetriever`：方法 __init__、build、retrieve、_fuse、_chunk_id、_tokenize
- 注意：属于 RAG 链路，避免重复新增索引入口

### `aiagent/knowledge/vector_store.py`
- 大小：9343 bytes
- 类型：文本/源码/配置
- 作用：外部服务客户端或 API 调用适配模块；类：OpenAICompatibleEmbeddings、LangChainVectorStore
- 主要依赖：__future__、langchain_community.vectorstores、langchain_core.documents、langchain_core.embeddings、langchain_huggingface、logging、openai、os、pathlib、typing、urllib.parse
- 类 `OpenAICompatibleEmbeddings`：方法 __init__、embed_documents、embed_query、_embed_batch、_batches
- 类 `LangChainVectorStore`：方法 __init__、build、save、load、similarity_search、similarity_search_with_score、count、_build_embeddings、_build_huggingface_embeddings、_resolve_model_name、_distance_to_similarity、_extend_no_proxy
- 注意：属于 RAG 链路，避免重复新增索引入口

## 事件编排、调度与会话管理

### `aiagent/orchestrator/__init__.py`
- 大小：27 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `aiagent/orchestrator/dispatcher.py`
- 大小：3741 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：EventDispatcher
- 主要依赖：aiagent.brain.agent_core、aiagent.brain.dialogue_manager、aiagent.expression.output_broadcaster、aiagent.orchestrator.event_bus、aiagent.orchestrator.interrupt_manager、aiagent.orchestrator.scheduler、aiagent.orchestrator.session_manager、aiagent.persona.persona_manager、aiagent.schemas.events、aiagent.schemas.inputs、aiagent.schemas.outputs、aiagent.state.agent_state、aiagent.state.conversation_state
- 类 `EventDispatcher`：方法 __init__、handle_input

### `aiagent/orchestrator/event_bus.py`
- 大小：635 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。；类：EventBus
- 主要依赖：aiagent.schemas.events、collections、collections.abc
- 类 `EventBus`：方法 __init__、subscribe、publish

### `aiagent/orchestrator/interrupt_manager.py`
- 大小：804 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。；类：InterruptManager
- 类 `InterruptManager`：方法 __init__、request_interrupt、consume_interrupt、snapshot

### `aiagent/orchestrator/scheduler.py`
- 大小：213 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。；类：Scheduler
- 主要依赖：aiagent.schemas.inputs
- 类 `Scheduler`：方法 should_process_now

### `aiagent/orchestrator/session_manager.py`
- 大小：232 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。；类：SessionManager
- 主要依赖：aiagent.schemas.inputs
- 类 `SessionManager`：方法 resolve_session_id

## 人格加载、提示词与人格保护

### `aiagent/persona/__init__.py`
- 大小：733 bytes
- 类型：文本/源码/配置
- 作用：人格或 YAML 配置加载模块
- 主要依赖：aiagent.persona.persona_guard、aiagent.persona.persona_loader、aiagent.persona.persona_models、aiagent.persona.persona_registry、aiagent.persona.persona_runtime

### `aiagent/persona/persona_guard.py`
- 大小：2273 bytes
- 类型：文本/源码/配置
- 作用：数据模型或 Schema 模块；类：PersonaGuardResult、PersonaGuard
- 主要依赖：__future__、dataclasses
- 类 `PersonaGuardResult`：方法 无显式方法
- 类 `PersonaGuard`：方法 normalize、_trim_repeated_prefix、_looks_too_cold、_add_light_persona_tail
- 注意：人格保护核心逻辑，修改后需要回归测试

### `aiagent/persona/persona_loader.py`
- 大小：1459 bytes
- 类型：文本/源码/配置
- 作用：人格或 YAML 配置加载模块；类：PersonaLoader
- 主要依赖：__future__、aiagent.persona.persona_models、pathlib、yaml
- 类 `PersonaLoader`：方法 __init__、load_from_file、load_persona、load_all

### `aiagent/persona/persona_manager.py`
- 大小：1111 bytes
- 类型：文本/源码/配置
- 作用：人格或 YAML 配置加载模块；类：PersonaManager
- 主要依赖：__future__、aiagent.persona.persona_loader、aiagent.persona.persona_runtime
- 类 `PersonaManager`：方法 __init__、load_default_persona、get_active_persona、switch_persona

### `aiagent/persona/persona_models.py`
- 大小：2156 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：PersonaIdentity、PersonaStyle、PersonaRules、PersonaBehavior、PersonaExpression、PersonaVoice、PersonaPrompts、PersonaConfig
- 主要依赖：__future__、pydantic
- 类 `PersonaIdentity`：方法 无显式方法
- 类 `PersonaStyle`：方法 无显式方法
- 类 `PersonaRules`：方法 无显式方法
- 类 `PersonaBehavior`：方法 无显式方法
- 类 `PersonaExpression`：方法 无显式方法
- 类 `PersonaVoice`：方法 无显式方法
- 类 `PersonaPrompts`：方法 无显式方法
- 类 `PersonaConfig`：方法 name、alias

### `aiagent/persona/persona_prompts.py`
- 大小：4161 bytes
- 类型：文本/源码/配置
- 作用：人格或 YAML 配置加载模块；类：PersonaPromptBuilder
- 主要依赖：__future__、aiagent.persona.persona_models
- 类 `PersonaPromptBuilder`：方法 build_system_prompt、build_planner_prompt

### `aiagent/persona/persona_registry.py`
- 大小：1677 bytes
- 类型：文本/源码/配置
- 作用：人格或 YAML 配置加载模块；类：PersonaRegistry
- 主要依赖：__future__、aiagent.persona.persona_loader、aiagent.persona.persona_runtime
- 类 `PersonaRegistry`：方法 __init__、load_all、register_from_id、get、get_active、set_active、list_personas

### `aiagent/persona/persona_runtime.py`
- 大小：2446 bytes
- 类型：文本/源码/配置
- 作用：运行时装配或生命周期模块；类：PersonaRuntime
- 主要依赖：__future__、aiagent.persona.persona_guard、aiagent.persona.persona_models、aiagent.persona.persona_prompts
- 类 `PersonaRuntime`：方法 __init__、persona_id、name、alias、build_system_prompt、build_planner_prompt、get_default_emotion、get_default_motion、get_default_expression、get_motion_for_emotion、get_expression_for_emotion、get_voice_config、normalize_reply、validate_reply、summary

## 人格配置与参考音频

### `data/persona/yzl/persona.yaml`
- 大小：3831 bytes
- 类型：文本/源码/配置
- 作用：YAML 配置文件，用于 persona、Live2D、数据集、背景或服务配置。

### `data/persona/yzl/refaudio.wav`
- 大小：3845920 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

## 公共工具

### `aiagent/common/__init__.py`
- 大小：33 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `aiagent/common/logger.py`
- 大小：320 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。；函数：setup_logger
- 主要依赖：logging、sys
- 顶层函数：setup_logger

## 图流程与工作流状态

### `aiagent/graphs/__init__.py`
- 大小：0 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `aiagent/graphs/graph_model.py`
- 大小：6418 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：StateGraphInput、StateInferenceOutput、StateGraphResult、PlannerGraphInput、PlannerInferenceOutput、PlannerGraphResult、RAGGraphInput、RAGGraphResult、VisionSafetyResult、VisionMemoryCandidate
- 主要依赖：__future__、pydantic、typing
- 类 `StateGraphInput`：方法 无显式方法
- 类 `StateInferenceOutput`：方法 无显式方法
- 类 `StateGraphResult`：方法 无显式方法
- 类 `PlannerGraphInput`：方法 无显式方法
- 类 `PlannerInferenceOutput`：方法 无显式方法
- 类 `PlannerGraphResult`：方法 无显式方法
- 类 `RAGGraphInput`：方法 无显式方法
- 类 `RAGGraphResult`：方法 无显式方法
- 类 `VisionSafetyResult`：方法 无显式方法
- 类 `VisionMemoryCandidate`：方法 无显式方法

### `aiagent/graphs/llm_graph.py`
- 大小：17538 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：LLMGraphState、LLMRunner
- 主要依赖：__future__、aiagent.graphs.graph_model、aiagent.persona.persona_runtime、aiagent.services.llm_service、config.providers、langchain_core.messages、langchain_core.messages.utils、langgraph.checkpoint.memory、langgraph.graph、langmem.short_term、typing
- 类 `LLMGraphState`：方法 无显式方法
- 类 `LLMRunner`：方法 __init__、_build_graph、_create_summarize_node、_mock_summarize_node、_build_prompt_node、_call_llm_node、_normalize_reply_node、run、recent_dialogue_lines、clear_thread、clear_all_threads、_state_input、_get_persona_runtime、_slice_short_term_messages、_prepare_dialogue_messages

### `aiagent/graphs/main_graph.py`
- 大小：17361 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：MainGraphState、MainRunner
- 主要依赖：__future__、aiagent.graphs.llm_graph、aiagent.graphs.memory_graph、aiagent.graphs.planner_graph、aiagent.graphs.rag_graph、aiagent.graphs.state_graph、aiagent.graphs.vision_graph、aiagent.persona.persona_runtime、aiagent.schemas.inputs、aiagent.schemas.outputs、langgraph.graph、typing
- 类 `MainGraphState`：方法 无显式方法
- 类 `MainRunner`：方法 __init__、_build_graph、run、run_debug、clear_thread、clear_all_threads、_prepare_context_node、_run_vision_graph_node、_retrieve_memory_node、_run_state_graph_node、_run_planner_graph_node、_run_rag_graph_node、_run_llm_graph_node、_store_memory_node、_build_response_packet_node

### `aiagent/graphs/memory_graph.py`
- 大小：6279 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：MemoryGraphState、MemoryRunner
- 主要依赖：__future__、aiagent.memory.mem0_memory、aiagent.schemas.memory、aiagent.services.memory_policy_llm_service、langgraph.graph、typing
- 类 `MemoryGraphState`：方法 无显式方法
- 类 `MemoryRunner`：方法 __init__、_build_graph、retrieve_before_reply、run_after_reply、_retrieve_node、_decide_write_node、_route_after_decision、_store_node
- 注意：属于记忆链路，可能依赖外部向量数据库

### `aiagent/graphs/planner_graph.py`
- 大小：5234 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：PlannerGraphState、PlannerRunner
- 主要依赖：__future__、aiagent.cognition.planner_normalizer、aiagent.cognition.planner_prompt、aiagent.cognition.planner_reply、aiagent.graphs.graph_model、aiagent.persona.persona_runtime、langgraph.graph、typing
- 类 `PlannerGraphState`：方法 无显式方法
- 类 `PlannerRunner`：方法 __init__、_build_graph、_build_prompt_node、_analyze_plan_node、_normalize_plan_node、run

### `aiagent/graphs/rag_graph.py`
- 大小：9993 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：RAGGraphState、RAGRunner
- 主要依赖：__future__、aiagent.graphs.graph_model、langgraph.graph、typing
- 类 `RAGGraphState`：方法 无显式方法
- 类 `RAGRunner`：方法 __init__、_build_graph、run、_build_query_node、_retrieve_node、_filter_relevance_node、_pack_context_node、_judge_relevance、_build_search_query、_normalize_aliases、_expand_domain_terms
- 注意：属于 RAG 链路，避免重复新增索引入口

### `aiagent/graphs/state_graph.py`
- 大小：4446 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：StateGraphState、StateRunner
- 主要依赖：__future__、aiagent.cognition.state_analyzer、aiagent.cognition.state_normalizer、aiagent.cognition.state_prompt、aiagent.graphs.graph_model、aiagent.persona.persona_runtime、langgraph.graph、typing
- 类 `StateGraphState`：方法 无显式方法
- 类 `StateRunner`：方法 __init__、_build_graph、_build_prompt_node、_analyze_state_node、_normalize_state_node、run

### `aiagent/graphs/vision_graph.py`
- 大小：8789 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：VisionGraphState、VisionRunner
- 主要依赖：__future__、aiagent.graphs.graph_model、aiagent.services.vision_service、langgraph.graph、typing
- 类 `VisionGraphState`：方法 无显式方法
- 类 `VisionRunner`：方法 __init__、_build_graph、analyze_upload、analyze_path、_analyze_image_node、_build_chat_context_node、_build_memory_hint_node、_build_live2d_suggestion_node

## 早期轻量领域模型

### `domain/__init__.py`
- 大小：31 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `domain/chat/__init__.py`
- 大小：27 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `domain/chat/message.py`
- 大小：45 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `domain/chat/reply_policy.py`
- 大小：45 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `domain/chat/turn.py`
- 大小：50 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `domain/memory/__init__.py`
- 大小：29 bytes
- 类型：文本/源码/配置
- 作用：记忆系统模块
- 注意：属于记忆链路，可能依赖外部向量数据库

### `domain/memory/memory_item.py`
- 大小：44 bytes
- 类型：文本/源码/配置
- 作用：记忆系统模块
- 注意：属于记忆链路，可能依赖外部向量数据库

### `domain/memory/memory_rules.py`
- 大小：32 bytes
- 类型：文本/源码/配置
- 作用：记忆系统模块
- 注意：属于记忆链路，可能依赖外部向量数据库

### `domain/persona/__init__.py`
- 大小：30 bytes
- 类型：文本/源码/配置
- 作用：人格或 YAML 配置加载模块

### `domain/persona/persona_profile.py`
- 大小：48 bytes
- 类型：文本/源码/配置
- 作用：人格或 YAML 配置加载模块

### `domain/persona/speaking_style.py`
- 大小：47 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `domain/stream/__init__.py`
- 大小：29 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `domain/stream/audience_event.py`
- 大小：47 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `domain/stream/scene_policy.py`
- 大小：32 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `domain/stream/stream_scene.py`
- 大小：45 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

## 智能体核心与对话控制

### `aiagent/brain/__init__.py`
- 大小：29 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `aiagent/brain/agent_core.py`
- 大小：2278 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：AgentCore
- 主要依赖：__future__、aiagent.graphs.main_graph、aiagent.persona.persona_runtime、aiagent.schemas.inputs、aiagent.schemas.outputs、aiagent.state.agent_state、aiagent.state.conversation_state、aiagent.state.emotion_state
- 类 `AgentCore`：方法 __init__、process、clear_runtime_context、_build_history_lines

### `aiagent/brain/dialogue_manager.py`
- 大小：2195 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。；类：DialogueManager
- 主要依赖：aiagent.schemas.inputs、aiagent.schemas.outputs、collections、datetime
- 类 `DialogueManager`：方法 __init__、should_accept、record_turn、pause_global、resume_global、pause_user、resume_user、reset_session、snapshot

## 本地脚本与验收工具

### `scripts/build_knowledge_index.py`
- 大小：1418 bytes
- 类型：文本/源码/配置
- 作用：RAG、Embedding 或检索模块；函数：main
- 主要依赖：aiagent.knowledge.document_loader、aiagent.knowledge.rag_pipeline、aiagent.knowledge.reranker、aiagent.knowledge.retriever、aiagent.knowledge.vector_store、config.settings
- 顶层函数：main

### `scripts/generate_live2d_profile.ps1`
- 大小：1370 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。

### `scripts/generate_project_docs_zh.py`
- 大小：22423 bytes
- 类型：文本/源码/配置
- 作用：运行时装配或生命周期模块；函数：iter_files、path_posix、layer_for、is_binary、read_text、py_summary、purpose_for、risk_tags、detail_for、generate_inventory、generate_overview、main
- 主要依赖：__future__、ast、collections、pathlib、re
- 顶层函数：iter_files、path_posix、layer_for、is_binary、read_text、py_summary、purpose_for、risk_tags、detail_for、generate_inventory、generate_overview、main
- 注意：注意区分 mock Live2D 与真实 Live2D 路径；属于记忆链路，可能依赖外部向量数据库

### `scripts/generate_yzl_persona_dataset.py`
- 大小：47890 bytes
- 类型：文本/源码/配置
- 作用：Live2D 相关模块；类：DatasetBuilder；函数：clean_text、make_record、trim_or_fail
- 主要依赖：json、pathlib
- 类 `DatasetBuilder`：方法 __init__、add
- 顶层函数：clean_text、make_record、trim_or_fail

### `scripts/run_persona_state_chat_test.py`
- 大小：3782 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；函数：build_persona_runtime、build_state_runner、build_final_system_prompt、main
- 主要依赖：__future__、aiagent.cognition.state_analyzer、aiagent.cognition.state_normalizer、aiagent.graphs.state_graph、aiagent.persona.persona_loader、aiagent.persona.persona_runtime、aiagent.services.llm_service、aiagent.services.state_llm_service、config.settings
- 顶层函数：build_persona_runtime、build_state_runner、build_final_system_prompt、main

### `scripts/run_persona_state_planner_chat_test.py`
- 大小：5427 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；函数：build_persona_runtime、build_state_runner、build_planner_runner、build_final_system_prompt、main
- 主要依赖：__future__、aiagent.cognition.planner_normalizer、aiagent.cognition.planner_reply、aiagent.cognition.state_analyzer、aiagent.cognition.state_normalizer、aiagent.graphs.planner_graph、aiagent.graphs.state_graph、aiagent.persona.persona_loader、aiagent.persona.persona_runtime、aiagent.services.llm_service、aiagent.services.planner_llm_service、aiagent.services.state_llm_service、config.settings
- 顶层函数：build_persona_runtime、build_state_runner、build_planner_runner、build_final_system_prompt、main

### `scripts/run_state_graph_real.py`
- 大小：2389 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；函数：build_persona_runtime、build_state_runner、main
- 主要依赖：__future__、aiagent.cognition.state_analyzer、aiagent.cognition.state_normalizer、aiagent.graphs.state_graph、aiagent.persona.persona_loader、aiagent.persona.persona_runtime、aiagent.services.state_llm_service、config.settings
- 顶层函数：build_persona_runtime、build_state_runner、main

### `scripts/run_state_planner_llm_graph_real.py`
- 大小：5427 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；函数：build_persona_runtime、build_state_runner、build_planner_runner、build_llm_runner、run_turn、main
- 主要依赖：__future__、aiagent.cognition.planner_normalizer、aiagent.cognition.planner_reply、aiagent.cognition.state_analyzer、aiagent.cognition.state_normalizer、aiagent.graphs.llm_graph、aiagent.graphs.planner_graph、aiagent.graphs.state_graph、aiagent.persona.persona_loader、aiagent.persona.persona_runtime、aiagent.services.llm_service、aiagent.services.planner_llm_service、aiagent.services.state_llm_service、config.settings
- 顶层函数：build_persona_runtime、build_state_runner、build_planner_runner、build_llm_runner、run_turn、main

### `scripts/scan_live2d_models.ps1`
- 大小：744 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。

### `scripts/smoke_api.ps1`
- 大小：3093 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。

### `scripts/test_live2d_model_pipeline.ps1`
- 大小：1385 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。

### `scripts/test_live2d_payload.ps1`
- 大小：2429 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。
- 注意：属于 Live2D 调度链路，避免重复新增 dispatcher

### `scripts/test_live2d_qt_window.ps1`
- 大小：192 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。

### `scripts/test_live2d_runtime_local.ps1`
- 大小：1170 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。

### `scripts/test_live2d_runtime_session.ps1`
- 大小：1320 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。

### `scripts/test_live2d_runtime_session_local.ps1`
- 大小：1857 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。

### `scripts/test_multimodal_chat.ps1`
- 大小：2811 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。

### `scripts/test_peronsa_guard.ps1`
- 大小：1007 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。

### `scripts/test_persona_with_llm.py`
- 大小：1657 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；函数：main
- 主要依赖：__future__、aiagent.persona.persona_loader、aiagent.persona.persona_runtime、aiagent.services.llm_service、config.settings
- 顶层函数：main

### `scripts/test_phase3_live2d.ps1`
- 大小：2679 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。

### `scripts/test_vision.ps1`
- 大小：3813 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。

### `scripts/test_vision_batch.ps1`
- 大小：7365 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。

### `scripts/test_vision_chat.ps1`
- 大小：3603 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。

### `scripts/test_vision_daily.ps1`
- 大小：3364 bytes
- 类型：文本/源码/配置
- 作用：PowerShell 本地操作或验收脚本，用于启动、冒烟测试、索引构建或阶段检查。

## 根目录文件与其他资源

### `.vscode/settings.json`
- 大小：3 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `aiagent.egg-info/dependency_links.txt`
- 大小：1 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `aiagent.egg-info/PKG-INFO`
- 大小：344 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。
- 注意：属于记忆链路，可能依赖外部向量数据库

### `aiagent.egg-info/requires.txt`
- 大小：117 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。
- 注意：属于记忆链路，可能依赖外部向量数据库

### `aiagent.egg-info/SOURCES.txt`
- 大小：4637 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。
- 注意：属于记忆链路，可能依赖外部向量数据库

### `aiagent.egg-info/top_level.txt`
- 大小：40 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `aiagent/__init__.py`
- 大小：28 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `apps/__init__.py`
- 大小：0 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `data/app_state/desktop_user.json`
- 大小：98 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/characters/luotianyi/images/LUO1.jpg`
- 大小：5410228 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO10.jpg`
- 大小：532478 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO11.png`
- 大小：1767687 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO12.png`
- 大小：2771484 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO13.png`
- 大小：961717 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO14.png`
- 大小：1019636 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO15.png`
- 大小：609437 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO16.jpg`
- 大小：9813170 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO17.jpg`
- 大小：16467303 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO18.jpg`
- 大小：3007119 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO19.jpg`
- 大小：3520068 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO2.jpg`
- 大小：1472906 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO20.jpg`
- 大小：895872 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO21.jpg`
- 大小：776600 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO22.jpg`
- 大小：2856393 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO23.png`
- 大小：2394637 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO24.png`
- 大小：2309086 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO25.jpg`
- 大小：364569 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO26.jpg`
- 大小：5438750 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO27.jpg`
- 大小：4347940 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO28.png`
- 大小：11622224 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO29.png`
- 大小：11964467 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO3.png`
- 大小：8399546 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO30.jpg`
- 大小：11257765 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO31.png`
- 大小：12854172 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO32.png`
- 大小：12736895 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO33.png`
- 大小：427501 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO34.png`
- 大小：451454 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO35.jpg`
- 大小：7759635 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO36.jpg`
- 大小：8499216 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO37.jpg`
- 大小：528877 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO38.png`
- 大小：1179898 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO39.jpg`
- 大小：1835133 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO4.png`
- 大小：1281383 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO40.jpg`
- 大小：7919039 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO41.jpg`
- 大小：9009601 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO42.jpg`
- 大小：360032 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO43.png`
- 大小：2611318 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO44.jpg`
- 大小：6291290 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO45.jpg`
- 大小：728347 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO46.png`
- 大小：8555589 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO47.jpg`
- 大小：2547821 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO48.png`
- 大小：9877891 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO49.jpg`
- 大小：1521330 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO5.png`
- 大小：8433213 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO50.png`
- 大小：2760671 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO6.png`
- 大小：4910137 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO7.jpg`
- 大小：597524 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO8.jpg`
- 大小：3251184 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/images/LUO9.jpg`
- 大小：5221571 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/luotianyi/profile.yaml`
- 大小：493 bytes
- 类型：文本/源码/配置
- 作用：YAML 配置文件，用于 persona、Live2D、数据集、背景或服务配置。

### `data/characters/yanhe/images/YAN1.png`
- 大小：16174897 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN10.png`
- 大小：16368663 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN11.jpg`
- 大小：1133973 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN12.jpg`
- 大小：599343 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN13.jpg`
- 大小：1983902 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN14.jpg`
- 大小：329049 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN15.jpg`
- 大小：2228870 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN16.jpg`
- 大小：662480 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN17.jpg`
- 大小：474613 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN18.jpg`
- 大小：2848388 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN19.png`
- 大小：792538 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN2.jpg`
- 大小：642775 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN20.png`
- 大小：1285492 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN21.jpg`
- 大小：777799 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN22.jpg`
- 大小：626579 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN23.jpg`
- 大小：592795 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN24.jpg`
- 大小：544118 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN25.jpg`
- 大小：1160797 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN26.jpg`
- 大小：2242064 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN27.jpg`
- 大小：1030751 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN28.jpg`
- 大小：1013594 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN29.jpg`
- 大小：693896 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN3.jpg`
- 大小：775010 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN4.jpg`
- 大小：3193691 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN5.png`
- 大小：1050945 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN6.png`
- 大小：4901841 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN7.jpg`
- 大小：1602005 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN8.jpg`
- 大小：762107 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/images/YAN9.jpg`
- 大小：737068 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yanhe/profile.yaml`
- 大小：227 bytes
- 类型：文本/源码/配置
- 作用：YAML 配置文件，用于 persona、Live2D、数据集、背景或服务配置。

### `data/characters/yuezhengling/images/YUE1.jpg`
- 大小：905223 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE10.jpg`
- 大小：737530 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE11.jpg`
- 大小：6260435 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE12.png`
- 大小：1095772 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE13.png`
- 大小：6840152 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE14.png`
- 大小：6189490 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE15.jpg`
- 大小：621546 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE16.jpg`
- 大小：638618 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE17.jpg`
- 大小：1656206 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE18.png`
- 大小：3453587 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE19.jpg`
- 大小：2228671 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE2.png`
- 大小：9203674 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE20.jpg`
- 大小：1637409 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE21.png`
- 大小：8290643 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE22.png`
- 大小：1955300 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE23.jpg`
- 大小：2720771 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE24.jpg`
- 大小：1501564 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE25.jpg`
- 大小：3910576 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE26.jpg`
- 大小：784790 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE27.png`
- 大小：373594 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE28.png`
- 大小：7674348 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE29.png`
- 大小：342186 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE3.png`
- 大小：10756526 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE30.png`
- 大小：881680 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE31.jpg`
- 大小：565131 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE32.jpg`
- 大小：761089 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE33.jpg`
- 大小：1023625 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE34.jpg`
- 大小：1510285 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE35.jpg`
- 大小：762434 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE36.jpg`
- 大小：418109 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE37.jpg`
- 大小：567602 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE38.jpg`
- 大小：1969977 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE39.jpg`
- 大小：1338991 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE4.png`
- 大小：6224270 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE40.jpg`
- 大小：1160058 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE41.jpg`
- 大小：1695183 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE42.jpg`
- 大小：1821480 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE43.jpg`
- 大小：1311330 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE44.jpg`
- 大小：1309549 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE45.jpg`
- 大小：2074959 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE46.jpg`
- 大小：1689083 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE47.jpg`
- 大小：381521 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE48.jpg`
- 大小：2003197 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE49.jpg`
- 大小：1855416 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE5.png`
- 大小：5466099 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE50.jpg`
- 大小：694049 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE6.png`
- 大小：5524962 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE7.jpg`
- 大小：5797286 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE8.png`
- 大小：5513768 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/images/YUE9.jpg`
- 大小：573445 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/characters/yuezhengling/profile.yaml`
- 大小：454 bytes
- 类型：文本/源码/配置
- 作用：YAML 配置文件，用于 persona、Live2D、数据集、背景或服务配置。

### `data/knowledge/public/streaming_basics.md`
- 大小：47260 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Vsinger六子

### `data/memory/long_term_memory.json`
- 大小：18021 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。
- 注意：属于记忆链路，可能依赖外部向量数据库

### `data/models/clip/config.json`
- 大小：4186 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/clip/configuration.json`
- 大小：88 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/clip/flax_model.msgpack`
- 大小：605123003 bytes
- 类型：二进制/资源/生成物
- 作用：二进制、模型、索引或缓存文件，不是源码，主要由运行时或工具读取。

### `data/models/clip/merges.txt`
- 大小：524657 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/models/clip/preprocessor_config.json`
- 大小：316 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/clip/pytorch_model.bin`
- 大小：605247071 bytes
- 类型：二进制/资源/生成物
- 作用：二进制、模型、索引或缓存文件，不是源码，主要由运行时或工具读取。

### `data/models/clip/README.md`
- 大小：7942 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Model Card: CLIP

### `data/models/clip/special_tokens_map.json`
- 大小：389 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/clip/tf_model.h5`
- 大小：605551040 bytes
- 类型：二进制/资源/生成物
- 作用：二进制、模型、索引或缓存文件，不是源码，主要由运行时或工具读取。

### `data/models/clip/tokenizer.json`
- 大小：2224041 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/clip/tokenizer_config.json`
- 大小：592 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/clip/vocab.json`
- 大小：862328 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/embedding/1_Pooling/config.json`
- 大小：313 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/embedding/config.json`
- 大小：727 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/embedding/config_sentence_transformers.json`
- 大小：215 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/embedding/configuration.json`
- 大小：73 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/embedding/generation_config.json`
- 大小：117 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/embedding/merges.txt`
- 大小：1671853 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/models/embedding/model-00001-of-00002.safetensors`
- 大小：4965826464 bytes
- 类型：二进制/资源/生成物
- 作用：二进制、模型、索引或缓存文件，不是源码，主要由运行时或工具读取。

### `data/models/embedding/model-00002-of-00002.safetensors`
- 大小：3077765624 bytes
- 类型：二进制/资源/生成物
- 作用：二进制、模型、索引或缓存文件，不是源码，主要由运行时或工具读取。

### `data/models/embedding/model.safetensors.index.json`
- 大小：30431 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/embedding/modules.json`
- 大小：349 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/embedding/README.md`
- 大小：17276 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Qwen3-Embedding-4B

### `data/models/embedding/tokenizer.json`
- 大小：11422947 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/embedding/tokenizer_config.json`
- 大小：7256 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/embedding/vocab.json`
- 大小：2776833 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/faster-whisper/models--Systran--faster-whisper-medium/refs/main`
- 大小：40 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。

### `data/models/faster-whisper/models--Systran--faster-whisper-medium/snapshots/08e178d48790749d25932bbc082711ddcfdfbc4f/config.json`
- 大小：2257 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/faster-whisper/models--Systran--faster-whisper-medium/snapshots/08e178d48790749d25932bbc082711ddcfdfbc4f/model.bin`
- 大小：1527906378 bytes
- 类型：二进制/资源/生成物
- 作用：二进制、模型、索引或缓存文件，不是源码，主要由运行时或工具读取。

### `data/models/faster-whisper/models--Systran--faster-whisper-medium/snapshots/08e178d48790749d25932bbc082711ddcfdfbc4f/tokenizer.json`
- 大小：2203239 bytes
- 类型：文本/源码/配置
- 作用：JSON 配置、结构化数据或生成结果。

### `data/models/faster-whisper/models--Systran--faster-whisper-medium/snapshots/08e178d48790749d25932bbc082711ddcfdfbc4f/vocabulary.txt`
- 大小：459861 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `pyproject.toml`
- 大小：601 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。
- 注意：属于记忆链路，可能依赖外部向量数据库

### `README.md`
- 大小：519 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。aiagent

### `requirements.txt`
- 大小：295 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `stage.md`
- 大小：5221 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。记录项目说明、设计或阶段计划。
- 注意：属于记忆链路，可能依赖外部向量数据库

### `uv.lock`
- 大小：344561 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。
- 注意：属于记忆链路，可能依赖外部向量数据库

## 根目录隐藏配置

### `.env`
- 大小：3983 bytes
- 类型：文本/源码/配置
- 作用：环境变量配置文件，包含模型供应商、API Key、端口、路径等运行参数。

### `.env.example`
- 大小：353 bytes
- 类型：文本/源码/配置
- 作用：环境变量配置文件，包含模型供应商、API Key、端口、路径等运行参数。

### `.gitignore`
- 大小：169 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。

### `data/knowledge/personal/.gitkeep`
- 大小：1 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。

### `data/knowledge/stream/.gitkeep`
- 大小：1 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。

### `data/logs/.gitkeep`
- 大小：1 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。

### `data/memory/sessions/.gitkeep`
- 大小：1 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。
- 注意：属于记忆链路，可能依赖外部向量数据库

### `data/memory/summaries/.gitkeep`
- 大小：1 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。
- 注意：属于记忆链路，可能依赖外部向量数据库

### `data/memory/users/.gitkeep`
- 大小：1 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。
- 注意：属于记忆链路，可能依赖外部向量数据库

### `data/models/clip/.msc`
- 大小：878 bytes
- 类型：二进制/资源/生成物
- 作用：二进制、模型、索引或缓存文件，不是源码，主要由运行时或工具读取。

### `data/models/clip/.mv`
- 大小：36 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。

### `data/models/embedding/.msc`
- 大小：1073 bytes
- 类型：二进制/资源/生成物
- 作用：二进制、模型、索引或缓存文件，不是源码，主要由运行时或工具读取。

### `data/models/embedding/.mv`
- 大小：36 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。

### `data/models/faster-whisper/.gitkeep`
- 大小：1 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。

### `data/models/live2d/.gitkeep`
- 大小：1 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。

## 测试套件

### `tests/e2e/__init__.py`
- 大小：32 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `tests/integration/__init__.py`
- 大小：33 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `tests/integration/test_chat_flow.py`
- 大小：449 bytes
- 类型：文本/源码/配置
- 作用：运行时装配或生命周期模块；函数：test_chat_flow_runs
- 主要依赖：apps.core.bootstrap
- 顶层函数：test_chat_flow_runs

### `tests/unit/__init__.py`
- 大小：26 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `tests/unit/test_persona_module.py`
- 大小：1437 bytes
- 类型：文本/源码/配置
- 作用：人格或 YAML 配置加载模块；函数：test_persona_loader_can_load_yzl、test_persona_runtime_builds_prompts、test_persona_guard_normalizes_reply、test_persona_registry_switching
- 主要依赖：aiagent.persona
- 顶层函数：test_persona_loader_can_load_yzl、test_persona_runtime_builds_prompts、test_persona_guard_normalizes_reply、test_persona_registry_switching

### `tests/unit/test_state_graph.py`
- 大小：0 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

## 用户上传文件

### `data/uploads/images/img_0b06cee3b75744be9a11305a3058170e.png`
- 大小：6840152 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_0cbf8cf21edc464e8327a4d0b90e14b0.jpg`
- 大小：905223 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_0f7d5bb59f91412ab3557959d655a0a7.png`
- 大小：1019636 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_0fab6ce50ff04b1b971f5342c3c4da81.jpg`
- 大小：4347940 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_178fca4dbe5146a0891eef4eb03d2392.jpg`
- 大小：1472906 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_189fdeeb37bf4f179fb609b921a92f32.jpg`
- 大小：5410228 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_1e22b988751e4774920650e8dd1b68c7.jpg`
- 大小：6260435 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_1ea51729f013479991cca5ffd490b7b9.jpg`
- 大小：694049 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_20102af39a9e4b4f91f12255534821ae.jpg`
- 大小：905223 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_2cdf4c26129c4e9d942639db814c0539.jpg`
- 大小：776600 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_303390ca18da4fc1865f9bf5e10fd288.jpg`
- 大小：9813170 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_316681d484ee481db3a5327e6818a33e.png`
- 大小：9203674 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_342eab2497b547228d9519e60ae42179.png`
- 大小：2309086 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_3560046eb4d4431d829884ec92a21aa4.png`
- 大小：10756526 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_3753fa1a71494aa8a52b1e557d4c8153.jpg`
- 大小：905223 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_38b29983ef0c44ec84db9f1024d196e0.jpg`
- 大小：5438750 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_39b8c6ed2f5e479b8f53c4c17e566e7a.png`
- 大小：1767687 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_3ee30105ad7e4e71a92baf006040ad54.png`
- 大小：9203674 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_497f69d782124f75afececafe1af266d.jpg`
- 大小：5410228 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_4a404bd57fb04849bf3a1f1d08538b8d.png`
- 大小：12582912 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_4c119086af924f7b9f11cc1dbcfcaaf6.jpg`
- 大小：2856393 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_4d005c604e464ddb987c6b15bb09b4ff.jpg`
- 大小：2856393 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_53516a40a9674b5893d6afe92f9a5567.jpg`
- 大小：3007119 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_5b4da70b5e2b49ae9bc6916bb370c05e.png`
- 大小：11964467 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_5b719596bc5344c0993a33fdd1553919.jpg`
- 大小：905223 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_5eb33c2ce905482698d2e23a55bce503.png`
- 大小：1281383 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_60aab381111f42faaba9cfd3841584dd.png`
- 大小：12582912 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_6454a2bf4b604c868ac045bbeda5a608.png`
- 大小：1767687 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_68288dabc52943e5a8e46dace05ea73e.jpg`
- 大小：532478 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_688e38d95eed4a559b6f7e8544d246ec.jpg`
- 大小：905223 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_6d8f51892024454dbd0020fede0e1d9a.jpg`
- 大小：364569 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_71d7ce88da64429281fe573aa2c2b2ff.png`
- 大小：11622224 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_71e4fcc7c649496a8907e6c39e8b060d.jpg`
- 大小：1133973 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_759a101b41cd409bbd1192e8fcfa0fc3.jpg`
- 大小：905223 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_78b9499374b3416086c5c7dfd55b5379.png`
- 大小：1281383 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_79f441356ad74f7ebaafc9fdd945c950.jpg`
- 大小：5410228 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_7a5e14e0a9074a5da7f18e4b2d1ac040.jpg`
- 大小：905223 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_7bf40ba4ebc940b3b79e37c74cdb64c9.jpg`
- 大小：532478 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_818f837d7d8a4cef8335b39a3e8b65b8.jpg`
- 大小：5410228 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_829dc3827ca14f34b8041889fb2fdd7f.png`
- 大小：9203674 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_85789258f1ee43559f209eb09fc594ce.jpg`
- 大小：905223 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_89e5b9dda46d46949d01ae71c4e34a7c.jpg`
- 大小：5410228 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_8a99660d6b614d7c9927fd0eefd141f0.jpg`
- 大小：599343 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_8af5ba3b218a4658a056a4bfa4a0a548.jpg`
- 大小：3007119 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_8c4cd98604be409abeed07463095e21a.png`
- 大小：961717 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_8de80c5a726144fcbc16871b52fd4927.jpg`
- 大小：694049 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_92eeb07a0ada4bc79d8ac47b3663fe43.png`
- 大小：1281383 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_9427330b2c944132ae81ed4682c033ac.jpg`
- 大小：905223 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_95490b2cdfb44b95882cef79b6fe71de.png`
- 大小：12582912 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_9e523b5b1e4c48a2999815a63dfea8d7.jpg`
- 大小：12582912 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_a3c3b2da336640d184e1dbdcde07daef.jpg`
- 大小：1983902 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_ab360da09d944349ab4cbc10568223d9.png`
- 大小：2394637 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_ab756f98a54e4b95bc56e87cd23f49a6.jpg`
- 大小：905223 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_ad1583b85ed24144bed66df902f7b08c.jpg`
- 大小：532478 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_ae0f8284a49844729e40b8145a1f8195.jpg`
- 大小：895872 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_b0d7d4fea93949a6be49c2e5ffed257d.png`
- 大小：2771484 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_b0eb39bb62624939b96cb2fc67fa26d2.jpg`
- 大小：5410228 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_b3a40dc669ca4a07a5834a935b72ad39.png`
- 大小：1281383 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_bed94d0b6f67465e9dd185c000f69fb9.png`
- 大小：9203674 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_bf31e7bbe87e4326a05cd70f6cd592bd.png`
- 大小：9203674 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_c05d9cd38b6e49b9bd88124a519a68dd.jpg`
- 大小：905223 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_c1a2355d14cd4438ba5e830b26055b22.jpg`
- 大小：599343 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_c7332f93587347acbbcbd51b25259d0b.jpg`
- 大小：5410228 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_c99db9daa1234a159bf79024495c7291.png`
- 大小：2771484 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_ca7a7678842d44739376c00f630c68d1.png`
- 大小：12582912 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_cbd3c17a9dcf469a87de54b4cef0f299.jpg`
- 大小：1133973 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_cc6370edf684432e9c841c67caca01e0.png`
- 大小：2771484 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_cda26ab63153422a942134d518415d53.png`
- 大小：1767687 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_cfda9de318f74e64b52a9cc9914d5ba9.png`
- 大小：609437 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_d1d580bfba43419096d25bca06d90cfe.jpg`
- 大小：12582912 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_d2719d29a4314e8da0afa840abddf635.jpg`
- 大小：905223 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_d6c3649dd8814f4c93f9d9420ee340f5.jpg`
- 大小：905223 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_d9819e45b9a1409dbc3be50c97972b93.png`
- 大小：1095772 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_dd8ebe90cced42e996ebe1bafbf865a0.png`
- 大小：1019636 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_e69bb0de787b490aac4e94cee3d2c14d.jpg`
- 大小：329049 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_e6a4e5d2e04d4fd3bfcf22da0c9ee8c6.jpg`
- 大小：1983902 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_e9e72dc7dd5441a9bc1399c15f1a4904.png`
- 大小：961717 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_ec717eaa1ab0402f9f2b01976653c68e.jpg`
- 大小：2856393 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_ef8786a7bf99408c9198f1f63ddfefe7.png`
- 大小：961717 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_f204e54b92a547e1aa844eedf84be19e.jpg`
- 大小：9813170 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_f311ad47d8674bf6beac88a4e07674ce.jpg`
- 大小：737530 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_f4d8b4e2a8a544efb8deaafbfa0b0d30.jpg`
- 大小：694049 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_f8233ff3526c46758718c19a6a222616.jpg`
- 大小：905223 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_faae99c1b8b0481f922f2c1214456e15.jpg`
- 大小：3520068 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_fc45dc4649644864aebb248b30bedb61.png`
- 大小：609437 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

### `data/uploads/images/img_fd7ac2310ea549c98765b1d7cb8ca0b7.png`
- 大小：12582912 bytes
- 类型：二进制/资源/生成物
- 作用：图片资源，用于视觉角色图库、Live2D 背景、上传样例或前端资源。

## 第三方服务与外部库适配

### `integrations/__init__.py`
- 大小：37 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `integrations/asr/__init__.py`
- 大小：31 bytes
- 类型：文本/源码/配置
- 作用：ASR、麦克风或 VAD 模块

### `integrations/asr/faster_whisper_client.py`
- 大小：1912 bytes
- 类型：文本/源码/配置
- 作用：外部服务客户端或 API 调用适配模块；类：FasterWhisperClient
- 主要依赖：faster_whisper、logging、pathlib
- 类 `FasterWhisperClient`：方法 __init__、transcribe

### `integrations/asr/microphone.py`
- 大小：2438 bytes
- 类型：文本/源码/配置
- 作用：音频、TTS 或语音模块；类：StreamingMicrophone
- 主要依赖：integrations.asr.vad、numpy、pathlib、queue、scipy.io.wavfile、sounddevice、uuid
- 类 `StreamingMicrophone`：方法 __init__、record_until_silence

### `integrations/asr/mock_asr_client.py`
- 大小：135 bytes
- 类型：文本/源码/配置
- 作用：外部服务客户端或 API 调用适配模块；类：MockASRClient
- 类 `MockASRClient`：方法 transcribe

### `integrations/asr/vad.py`
- 大小：570 bytes
- 类型：文本/源码/配置
- 作用：音频、TTS 或语音模块；类：VoiceActivityDetector
- 主要依赖：numpy
- 类 `VoiceActivityDetector`：方法 __init__、is_speech

### `integrations/audio/__init__.py`
- 大小：0 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `integrations/audio/audio_player.py`
- 大小：6678 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：AudioPlayer
- 主要依赖：__future__、logging、pathlib、pygame、threading、time、wave
- 类 `AudioPlayer`：方法 __init__、_ensure_mixer、play、play_sequence、play_async、play_sequence_async、stop、is_busy、get_current_audio_path、get_current_playlist、get_duration_seconds、get_total_duration_seconds、_validate_audio_file、_validate_wav

### `integrations/audio/microphone_recorder.py`
- 大小：1262 bytes
- 类型：文本/源码/配置
- 作用：音频、TTS 或语音模块；类：MicrophoneRecorder
- 主要依赖：logging、numpy、pathlib、scipy.io.wavfile、sounddevice、uuid
- 类 `MicrophoneRecorder`：方法 __init__、record

### `integrations/live2d/__init__.py`
- 大小：34 bytes
- 类型：文本/源码/配置
- 作用：Live2D 相关模块

### `integrations/live2d/expression_mapper.py`
- 大小：44 bytes
- 类型：文本/源码/配置
- 作用：Live2D 相关模块

### `integrations/live2d/file_live2d_client.py`
- 大小：1597 bytes
- 类型：文本/源码/配置
- 作用：外部服务客户端或 API 调用适配模块；类：FileLive2DClient
- 主要依赖：__future__、aiagent.live2d.payload_builder、json、pathlib、uuid
- 类 `FileLive2DClient`：方法 __init__、dispatch

### `integrations/live2d/live2d_py_runtime.py`
- 大小：5163 bytes
- 类型：文本/源码/配置
- 作用：运行时装配或生命周期模块；类：Live2DPyRuntime
- 主要依赖：__future__、importlib、integrations.live2d.model_loader、integrations.live2d.model_session、logging、pathlib、typing
- 类 `Live2DPyRuntime`：方法 __init__、status、inspect_model、prepare_model、_load_module、_try_runtime_initialize、create_session、load_model_session

### `integrations/live2d/mock_live2d_client.py`
- 大小：648 bytes
- 类型：文本/源码/配置
- 作用：外部服务客户端或 API 调用适配模块；类：MockLive2DClient
- 主要依赖：json、pathlib、uuid
- 类 `MockLive2DClient`：方法 __init__、dispatch
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `integrations/live2d/model_loader.py`
- 大小：5477 bytes
- 类型：文本/源码/配置
- 作用：Live2D 相关模块；类：Live2DModelLoader
- 主要依赖：__future__、json、pathlib、typing
- 类 `Live2DModelLoader`：方法 inspect_model3、_resolve、_asset_entry、_append_missing、_summary

### `integrations/live2d/model_scanner.py`
- 大小：1599 bytes
- 类型：文本/源码/配置
- 作用：Live2D 相关模块；类：Live2DModelScanner
- 主要依赖：__future__、integrations.live2d.model_loader、pathlib、typing
- 类 `Live2DModelScanner`：方法 __init__、scan_root、find_first_model

### `integrations/live2d/model_session.py`
- 大小：8343 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：Live2DSessionState、Live2DModelSession
- 主要依赖：__future__、dataclasses、logging、pathlib、typing
- 类 `Live2DSessionState`：方法 无显式方法
- 类 `Live2DModelSession`：方法 __init__、load、update、set_expression、start_motion、drag、resize、snapshot、_select_model_class、_refresh_static_info、_safe_list

### `integrations/live2d/profile_generator.py`
- 大小：8445 bytes
- 类型：文本/源码/配置
- 作用：Live2D 相关模块；类：Live2DProfileGenerator
- 主要依赖：__future__、json、pathlib、typing、yaml
- 类 `Live2DProfileGenerator`：方法 generate_character_profile、_extract_expressions、_extract_motions、_default_expression、_default_motion、_emotion_expression_map、_emotion_motion_map、_expression_aliases、_motion_aliases、_motion_priority、_normalize_id

### `integrations/live2d/qt_live2d_widget.py`
- 大小：6568 bytes
- 类型：文本/源码/配置
- 作用：Qt 桌面 UI 或控件模块；类：QtLive2DWidget
- 主要依赖：PySide6.QtCore、PySide6.QtOpenGLWidgets、__future__、importlib、logging、pathlib、typing
- 类 `QtLive2DWidget`：方法 __init__、load_model、set_expression、start_motion、apply_payload、snapshot、initializeGL、resizeGL、paintGL、mouseMoveEvent、closeEvent、_ensure_live2d_ready、_resize_model、_tick

### `integrations/live2d/renderer.py`
- 大小：3901 bytes
- 类型：文本/源码/配置
- 作用：Live2D 相关模块；类：HeadlessLive2DRenderer
- 主要依赖：__future__、integrations.live2d.live2d_py_runtime、integrations.live2d.model_session、pathlib、typing
- 类 `HeadlessLive2DRenderer`：方法 __init__、load、apply_payload、drag、resize、update、snapshot

### `integrations/tts/__init__.py`
- 大小：31 bytes
- 类型：文本/源码/配置
- 作用：音频、TTS 或语音模块

### `integrations/tts/audio_player.py`
- 大小：34 bytes
- 类型：文本/源码/配置
- 作用：音频、TTS 或语音模块

### `integrations/tts/gpt_sovits_client.py`
- 大小：3188 bytes
- 类型：文本/源码/配置
- 作用：外部服务客户端或 API 调用适配模块；类：GPTSoVITSClient
- 主要依赖：httpx、logging、pathlib、uuid
- 类 `GPTSoVITSClient`：方法 __init__、synthesize、_looks_like_wav

### `integrations/tts/indextts2_client.py`
- 大小：6287 bytes
- 类型：文本/源码/配置
- 作用：外部服务客户端或 API 调用适配模块；类：IndexTTS2Client
- 主要依赖：__future__、httpx、logging、math、pathlib、re、uuid
- 类 `IndexTTS2Client`：方法 __init__、synthesize、synthesize_streaming、synthesize_segment、normalize_text、split_text_streaming、_normalize_timeout、_looks_like_wav

### `integrations/tts/mock_tts_client.py`
- 大小：447 bytes
- 类型：文本/源码/配置
- 作用：外部服务客户端或 API 调用适配模块；类：MockTTSClient
- 主要依赖：pathlib、uuid
- 类 `MockTTSClient`：方法 __init__、synthesize

### `integrations/tts/text_cleaner.py`
- 大小：39 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `integrations/tts/voxcpm_client.py`
- 大小：3614 bytes
- 类型：文本/源码/配置
- 作用：外部服务客户端或 API 调用适配模块；类：VoxCPMClient
- 主要依赖：__future__、httpx、logging、math、pathlib、re、uuid
- 类 `VoxCPMClient`：方法 __init__、synthesize、normalize_text、_normalize_timeout、_looks_like_wav

## 认知分析与回复规划

### `aiagent/cognition/__init__.py`
- 大小：0 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `aiagent/cognition/planner_normalizer.py`
- 大小：3109 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：PlannerNormalizer
- 主要依赖：__future__、aiagent.graphs.graph_model
- 类 `PlannerNormalizer`：方法 normalize、_default_motion_for_emotion、_default_expression_for_emotion

### `aiagent/cognition/planner_prompt.py`
- 大小：4427 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：PlannerPromptBuilder
- 主要依赖：__future__、aiagent.persona.persona_runtime
- 类 `PlannerPromptBuilder`：方法 build

### `aiagent/cognition/planner_reply.py`
- 大小：488 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：ReplyPlanner
- 主要依赖：__future__、aiagent.graphs.graph_model、aiagent.services.planner_llm_service
- 类 `ReplyPlanner`：方法 __init__、infer

### `aiagent/cognition/state_analyzer.py`
- 大小：486 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：StateAnalyzer
- 主要依赖：__future__、aiagent.graphs.graph_model、aiagent.services.state_llm_service
- 类 `StateAnalyzer`：方法 __init__、infer

### `aiagent/cognition/state_normalizer.py`
- 大小：1919 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：StateNormalizer
- 主要依赖：__future__、aiagent.graphs.graph_model
- 类 `StateNormalizer`：方法 normalize、_default_motion_for_emotion

### `aiagent/cognition/state_prompt.py`
- 大小：2120 bytes
- 类型：文本/源码/配置
- 作用：人格或 YAML 配置加载模块；类：StateInferencePromptBuilder
- 主要依赖：__future__、aiagent.persona.persona_runtime
- 类 `StateInferencePromptBuilder`：方法 build

## 训练与微调数据集

### `data/datasets.zip`
- 大小：34904 bytes
- 类型：二进制/资源/生成物
- 作用：压缩归档，通常用于数据集打包或外部资源备份。

### `data/datasets/.gitattributes`
- 大小：3818 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。

### `data/datasets/.msc`
- 大小：318 bytes
- 类型：二进制/资源/生成物
- 作用：二进制、模型、索引或缓存文件，不是源码，主要由运行时或工具读取。

### `data/datasets/.mv`
- 大小：6 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。

### `data/datasets/dataset_info.json`
- 大小：15425 bytes
- 类型：文本/源码/配置
- 作用：数据集元信息或微调训练数据。

### `data/datasets/muice-dataset-train.catgirl.json`
- 大小：360339 bytes
- 类型：文本/源码/配置
- 作用：数据集元信息或微调训练数据。

### `data/datasets/README.md`
- 大小：707 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。记录项目说明、设计或阶段计划。

## 识图、图片存储与角色图库检索

### `aiagent/vision/__init__.py`
- 大小：72 bytes
- 类型：文本/源码/配置
- 作用：视觉、图片或角色识别模块

### `aiagent/vision/character_registry.py`
- 大小：2925 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：CharacterProfile、CharacterRegistry
- 主要依赖：__future__、dataclasses、pathlib、typing、yaml
- 类 `CharacterProfile`：方法 无显式方法
- 类 `CharacterRegistry`：方法 __init__、load、all_profiles、get、_load_profile
- 注意：属于视觉角色识别链路，避免重复新增检索器

### `aiagent/vision/character_retriever.py`
- 大小：8613 bytes
- 类型：文本/源码/配置
- 作用：工作流图或图执行器模块；类：CharacterRetriever
- 主要依赖：PIL、__future__、aiagent.graphs.graph_model、aiagent.vision.character_registry、faiss、json、logging、numpy、pathlib、sentence_transformers、typing
- 类 `CharacterRetriever`：方法 __init__、build_index、retrieve、stats、_ensure_loaded、_load_index、_save_records、_get_model、_embed_image
- 注意：属于视觉角色识别链路，避免重复新增检索器；属于 RAG 链路，避免重复新增索引入口

### `aiagent/vision/image_store.py`
- 大小：3320 bytes
- 类型：文本/源码/配置
- 作用：数据模型或 Schema 模块；类：StoredImage、ImageStore
- 主要依赖：PIL、__future__、dataclasses、hashlib、pathlib、shutil、uuid
- 类 `StoredImage`：方法 无显式方法
- 类 `ImageStore`：方法 __init__、save_upload、save_local_copy、_validate_and_describe

## 输入、输出、事件 Schema

### `aiagent/schemas/__init__.py`
- 大小：22 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `aiagent/schemas/events.py`
- 大小：549 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：SystemEventType、SystemEvent
- 主要依赖：datetime、enum、pydantic、uuid
- 类 `SystemEventType`：方法 无显式方法
- 类 `SystemEvent`：方法 无显式方法

### `aiagent/schemas/inputs.py`
- 大小：1087 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：InputSource、EventPriority、InputAttachment、InputEvent
- 主要依赖：__future__、datetime、enum、pydantic、typing、uuid
- 类 `InputSource`：方法 无显式方法
- 类 `EventPriority`：方法 无显式方法
- 类 `InputAttachment`：方法 无显式方法
- 类 `InputEvent`：方法 无显式方法

### `aiagent/schemas/memory.py`
- 大小：729 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：MemoryCategory、MemoryImportance、MemoryWriteDecision
- 主要依赖：__future__、enum、pydantic、typing
- 类 `MemoryCategory`：方法 无显式方法
- 类 `MemoryImportance`：方法 无显式方法
- 类 `MemoryWriteDecision`：方法 无显式方法
- 注意：属于记忆链路，可能依赖外部向量数据库

### `aiagent/schemas/outputs.py`
- 大小：1195 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：EmotionLabel、ResponsePacket、OutputEvent
- 主要依赖：datetime、enum、pydantic、typing、uuid
- 类 `EmotionLabel`：方法 无显式方法
- 类 `ResponsePacket`：方法 无显式方法
- 类 `OutputEvent`：方法 无显式方法

## 输入感知与语音回合管理

### `aiagent/perception/__init__.py`
- 大小：24 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `aiagent/perception/asr_listener.py`
- 大小：1470 bytes
- 类型：文本/源码/配置
- 作用：外部服务客户端或 API 调用适配模块；类：ASRListener
- 主要依赖：integrations.asr.faster_whisper_client、integrations.asr.mock_asr_client、integrations.audio.microphone_recorder、logging
- 类 `ASRListener`：方法 __init__、transcribe_file、listen_once

### `aiagent/perception/input_normalizer.py`
- 大小：2379 bytes
- 类型：文本/源码/配置
- 作用：ASR、麦克风或 VAD 模块；类：InputNormalizer
- 主要依赖：aiagent.schemas.inputs
- 类 `InputNormalizer`：方法 normalize_chat、normalize_asr_text、normalize_system、parse_priority

### `aiagent/perception/source_router.py`
- 大小：3467 bytes
- 类型：文本/源码/配置
- 作用：视觉、图片或角色识别模块；类：SourceRouter
- 主要依赖：__future__、aiagent.perception.input_normalizer、aiagent.schemas.inputs
- 类 `SourceRouter`：方法 __init__、route、_normalize_source、_infer_modality

### `aiagent/perception/voice_session_controller.py`
- 大小：2768 bytes
- 类型：文本/源码/配置
- 作用：音频、TTS 或语音模块；类：VoiceSessionController
- 主要依赖：aiagent.expression.audio_playback_dispatcher、aiagent.state.speaking_state、aiagent.state.stream_state、datetime、logging
- 类 `VoiceSessionController`：方法 __init__、prepare_for_listening、finish_listening、interrupt_listening、mark_processing、finish_processing

### `aiagent/perception/voice_turn_manager.py`
- 大小：2001 bytes
- 类型：文本/源码/配置
- 作用：音频、TTS 或语音模块；类：VoiceTurnManager
- 主要依赖：aiagent.perception.asr_listener、aiagent.perception.voice_session_controller、aiagent.state.stream_state、integrations.asr.microphone、logging
- 类 `VoiceTurnManager`：方法 __init__、capture_turn

## 输出表达、TTS、音频与 Live2D 调度

### `aiagent/expression/__init__.py`
- 大小：24 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `aiagent/expression/audio_playback_dispatcher.py`
- 大小：6580 bytes
- 类型：文本/源码/配置
- 作用：音频、TTS 或语音模块；类：AudioPlaybackDispatcher
- 主要依赖：__future__、aiagent.schemas.outputs、aiagent.state.speaking_state、datetime、integrations.audio.audio_player、pathlib
- 类 `AudioPlaybackDispatcher`：方法 __init__、dispatch、_dispatch_single、_dispatch_segments、interrupt、refresh_state

### `aiagent/expression/live2d_payload_dispatcher.py`
- 大小：2062 bytes
- 类型：文本/源码/配置
- 作用：外部服务客户端或 API 调用适配模块；类：Live2DPayloadDispatcher
- 主要依赖：__future__、aiagent.schemas.outputs、integrations.live2d.file_live2d_client、integrations.live2d.mock_live2d_client
- 类 `Live2DPayloadDispatcher`：方法 __init__、dispatch
- 注意：注意区分 mock Live2D 与真实 Live2D 路径；属于 Live2D 调度链路，避免重复新增 dispatcher

### `aiagent/expression/mock_live2d_dispatcher.py`
- 大小：1259 bytes
- 类型：文本/源码/配置
- 作用：Live2D 相关模块；类：NoopLive2DDispatcher
- 主要依赖：__future__、aiagent.schemas.outputs
- 类 `NoopLive2DDispatcher`：方法 dispatch
- 注意：注意区分 mock Live2D 与真实 Live2D 路径；属于 Live2D 调度链路，避免重复新增 dispatcher

### `aiagent/expression/motion_policy.py`
- 大小：859 bytes
- 类型：文本/源码/配置
- 作用：音频、TTS 或语音模块；类：MotionPolicy
- 主要依赖：aiagent.schemas.outputs
- 类 `MotionPolicy`：方法 refine

### `aiagent/expression/output_broadcaster.py`
- 大小：2732 bytes
- 类型：文本/源码/配置
- 作用：Live2D 相关模块；类：OutputBroadcaster
- 主要依赖：__future__、aiagent.expression.audio_playback_dispatcher、aiagent.expression.live2d_payload_dispatcher、aiagent.expression.motion_policy、aiagent.expression.tts_dispatcher、aiagent.schemas.outputs、logging、threading
- 类 `OutputBroadcaster`：方法 __init__、broadcast、_run_tts_and_playback

### `aiagent/expression/response_formatter.py`
- 大小：57 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `aiagent/expression/tts_dispatcher.py`
- 大小：5091 bytes
- 类型：文本/源码/配置
- 作用：外部服务客户端或 API 调用适配模块；类：TTSDispatcher
- 主要依赖：__future__、aiagent.schemas.outputs、aiagent.state.speaking_state、datetime、integrations.tts.gpt_sovits_client、integrations.tts.indextts2_client、integrations.tts.mock_tts_client、integrations.tts.voxcpm_client、logging、pathlib
- 类 `TTSDispatcher`：方法 __init__、dispatch、_synthesize、_audio_url、_mark_idle、_now

## 运行时状态模型

### `aiagent/state/__init__.py`
- 大小：19 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `aiagent/state/agent_state.py`
- 大小：499 bytes
- 类型：文本/源码/配置
- 作用：运行时装配或生命周期模块；类：AgentStatus、AgentRuntimeState
- 主要依赖：enum、pydantic
- 类 `AgentStatus`：方法 无显式方法
- 类 `AgentRuntimeState`：方法 无显式方法

### `aiagent/state/conversation_state.py`
- 大小：6269 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：ConversationState
- 主要依赖：__future__、aiagent.schemas.inputs、aiagent.schemas.outputs、pydantic
- 类 `ConversationState`：方法 add_input、add_output、recent_dialogue_pairs、prompt_summary、snapshot、clear、_infer_topic、_infer_user_goal、_infer_user_emotion、_extract_keywords

### `aiagent/state/emotion_state.py`
- 大小：199 bytes
- 类型：文本/源码/配置
- 作用：数据模型或 Schema 模块；类：EmotionState
- 主要依赖：aiagent.schemas.outputs、pydantic
- 类 `EmotionState`：方法 无显式方法

### `aiagent/state/speaking_state.py`
- 大小：833 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：SpeakingState
- 主要依赖：__future__、datetime、pydantic
- 类 `SpeakingState`：方法 无显式方法

### `aiagent/state/stream_state.py`
- 大小：513 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：StreamingState
- 主要依赖：__future__、datetime、pydantic
- 类 `StreamingState`：方法 无显式方法

## 运行时生成缓存

### `data/cache/.gitkeep`
- 大小：1 bytes
- 类型：文本/源码/配置
- 作用：文本资源或其他配置文件。

### `data/cache/desktop_recordings/0eacf8b5ba524289a3059edef7df6278.wav`
- 大小：10028 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/desktop_recordings/3962b607040547479f60636d3e5cb52c.wav`
- 大小：160044 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/desktop_recordings/5722f9b5188344c099ce9fa1e86d8fb2.wav`
- 大小：160044 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/desktop_recordings/b3924ace98724aeba286b29309c2e09a.wav`
- 大小：160044 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/knowledge/faiss_index/index.faiss`
- 大小：1015853 bytes
- 类型：二进制/资源/生成物
- 作用：二进制、模型、索引或缓存文件，不是源码，主要由运行时或工具读取。

### `data/cache/knowledge/faiss_index/index.pkl`
- 大小：61740 bytes
- 类型：二进制/资源/生成物
- 作用：二进制、模型、索引或缓存文件，不是源码，主要由运行时或工具读取。

### `data/cache/knowledge/split_docs.json`
- 大小：78409 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。

### `data/cache/live2d/0cdf9ae0-12e6-4988-8db6-6ceae61c9bfb.json`
- 大小：915 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。

### `data/cache/live2d/2cb7b305-e443-4f63-91cf-929432c33b45.json`
- 大小：891 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。

### `data/cache/live2d/c73c8b96-7ffd-4899-9f61-125d98b51f9b.json`
- 大小：838 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。

### `data/cache/live2d/cf6f49f0-5abf-41df-9969-9685c33ed309.json`
- 大小：1099 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。

### `data/cache/live2d/d1a5feb4-12fe-4604-ac17-72da87a3687f.json`
- 大小：840 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。

### `data/cache/live2d/d8e47fdc-8c52-41ff-8846-dba64ef314c9.json`
- 大小：916 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。

### `data/cache/mock_live2d/01f3a84f52fc46bca976b1dfe7554c02.json`
- 大小：275 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/031d0f502e874838b4bc0f750cb5b7f3.json`
- 大小：424 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/03aac3349e1e419cbcdf58b66a50c0bd.json`
- 大小：297 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/068dadbb01424d52b01139cd6e2b0077.json`
- 大小：184 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/074d6607e82c46419d899ce5d9491a6b.json`
- 大小：320 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/08c6394928d648afa283f5e9a0718331.json`
- 大小：167 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/08ec619fd13140ecbd1af7a92dcf9ab2.json`
- 大小：689 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/0cbd056b993d44fbb825598f52814884.json`
- 大小：350 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/0dcebfbbeadf49a8881e04a808421636.json`
- 大小：143 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/0ef76bec0e3448d289272af28185929b.json`
- 大小：242 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/0f194e19154d44beb2e6c56b31633b32.json`
- 大小：358 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/10522dd1a4674cb9b842aa0af0c6817e.json`
- 大小：209 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/10fec3211ad24c549c974fc9d16bdce6.json`
- 大小：329 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/117c9ac7643046c3b92e5dd394cef82c.json`
- 大小：284 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/13044e52e6494ef9a686660ce9cb039c.json`
- 大小：232 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/137cbe65ee634743b1de1b60c1324055.json`
- 大小：315 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/15ef7335087e479681e61af03d71f8d9.json`
- 大小：136 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/163382dc93de455eb89536286dc5a597.json`
- 大小：204 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/17a382e6e1c440848be84cf4eda1b834.json`
- 大小：137 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/18f028e797264606965c0453d3b34bc1.json`
- 大小：286 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/1957acac040e4b70b4cc82dc2dc8da6a.json`
- 大小：182 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/1a5b180382f34d64bf31f9ff1bda36ae.json`
- 大小：339 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/1a93e9c2ed1c47e9abc55998c569e58b.json`
- 大小：158 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/1b1f9ae8458d42e7b0cd954fe30c52b2.json`
- 大小：295 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/1cfdb7badf194932baf21eb3f9184a2e.json`
- 大小：229 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/1d5c3d9948ce4f3eadb11dcad9fa3dbd.json`
- 大小：169 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/1e0a3740c1424083943f2767ddf6550c.json`
- 大小：186 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/1fe1b9ea98aa4d389e6ae2e62337e285.json`
- 大小：154 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/20ccab8dfbdf4a618b5783a23d1ce56e.json`
- 大小：244 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/2297652252d5466a833113d1f6f0e76c.json`
- 大小：164 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/229f2713972f427e863b11ace864c395.json`
- 大小：137 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/26182d825d1440c8a077e51618267703.json`
- 大小：155 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/28e281e8fe88496b968f63a6ab5ff485.json`
- 大小：128 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/29454e1d28f2444e9b40d3c0193a8657.json`
- 大小：170 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/2cdc02c5d86141dd90031b678a04728b.json`
- 大小：394 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/2d54d92d3a944ff48aec9614529a1eb1.json`
- 大小：256 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/2e47625126464a1f998f742f7895d5e9.json`
- 大小：305 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/3133b10e61a2431ba5722ba24a781a36.json`
- 大小：178 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/3541aa3684b9484fa335c9a36301e294.json`
- 大小：170 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/36bce7e8273244f9b54f4c71670ae01a.json`
- 大小：272 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/374b3640123b47a1852ba6c0eee4f696.json`
- 大小：116 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/38e3e7edb67d4167a977115fafb4f6a5.json`
- 大小：64 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/39a0de694d7d45e4b9e9b43472e738cd.json`
- 大小：209 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/3a87496b684e476cb736866ae23a3aa6.json`
- 大小：416 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/3aed6644b2a34887b3ccbe9061b1013e.json`
- 大小：222 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/3c4678b13d8f40b987b902e9430a2785.json`
- 大小：251 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/3d6e9924d94049b483b0647028506f52.json`
- 大小：326 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/3f0f922b582144b4af571249ac13f3a5.json`
- 大小：113 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/40b7bd9e5897488fb68d0a879f30c87c.json`
- 大小：497 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/40cbf92695b740548057a1674bc8bd08.json`
- 大小：2248 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/40e990f12dd14346a8be21e456d0a6d6.json`
- 大小：336 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/4376c54bfdf54ce3b8eee996df14fb4b.json`
- 大小：107 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/44e303a0b34a46d3b27d9145a20f2b5f.json`
- 大小：230 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/477f71e5f68f4e7f8006e7a386fb3d10.json`
- 大小：232 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/47da1b4d225442299ded864e02ff2c47.json`
- 大小：181 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/4995a710832d4aa792c4a20c763e7174.json`
- 大小：326 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/4b06400d5f8f49ce8f0a7cd1753c5e00.json`
- 大小：409 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/4b1a3c67700346efa7d320b0e2a00f9d.json`
- 大小：263 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/4b4234092d9247709043fde992fd70c5.json`
- 大小：261 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/4c1ce77f3eaf4d8594105ea6566cd109.json`
- 大小：284 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/4c6f18b8581f42978368f6cb45897e60.json`
- 大小：568 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/4f144bb2ca534f3badb422e99e12896f.json`
- 大小：155 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/4f45418182d74a81af7f9b7a71fa2a55.json`
- 大小：117 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/50d2f465962943a69e398f4d59ab3734.json`
- 大小：119 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/52094b0cc263443e8fab2884431f7aa8.json`
- 大小：287 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/53f0d92562214fb8bba3e9dfd54b1c60.json`
- 大小：372 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/54a02bbd126940ab8569c059c591e50a.json`
- 大小：456 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/56fd27f86d7144f2903865976897cf02.json`
- 大小：194 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/582c1819023a43d19493de5e5c0d99cc.json`
- 大小：190 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/5976ba7cbf9f4e2784fbdb7df623340f.json`
- 大小：308 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/59d4bd5f7dac4fa89412e59033c519b3.json`
- 大小：315 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/5a216b190e464111b10eaec19517fe13.json`
- 大小：196 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/5aa61ce4a8b54bc595227c956471e249.json`
- 大小：319 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/5b40f822e6854c369656bd92d773f883.json`
- 大小：97 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/5c3a9ff7c00e411fb6b66c2764b8ad18.json`
- 大小：175 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/5d36e7d743d040dbb48be74d42246fd9.json`
- 大小：301 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/5f014f41d4e14bf09bef4be2710b05f6.json`
- 大小：191 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/630e8fa3c5e6437ba14854f0f81c0d82.json`
- 大小：153 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/6330e47ddb5747ee9bcac56084c92aed.json`
- 大小：253 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/6393bbf2cc264221b6bdc57a3fafba20.json`
- 大小：337 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/6414033202a64bf995961cae3a2585db.json`
- 大小：163 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/64a33bb751d84a66909fe7ac56b04ff2.json`
- 大小：291 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/650488418d4043b2a7dfc975322cd726.json`
- 大小：184 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/6585af62a1c147fb8a203bb703f290d5.json`
- 大小：337 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/667992e063dc4b68ba822cf465c5d90b.json`
- 大小：464 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/66c35034422444659a3d56a2c5865b36.json`
- 大小：140 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/67e98254695149299d422136f3a97071.json`
- 大小：333 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/68be2ec062644b1c889eae7c6cf2f7b1.json`
- 大小：265 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/695ee00f263b495d998163eed3e0de57.json`
- 大小：235 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/69de8b043fc14bf9bb1dd09c66d0c6c0.json`
- 大小：262 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/6a2f34e2751b4ed9afb474c5f93286b7.json`
- 大小：253 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/6a534fbaddac4b5dada5d2d553f87746.json`
- 大小：202 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/6aba3f582cba4528b642cb3c03a5d4b5.json`
- 大小：692 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/6b7b38b54c7f4732ae0d6497091f31ca.json`
- 大小：178 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/6c1c4e073fa641df9daebd644707c010.json`
- 大小：561 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/6c31b704a85a4a6c9cdd6e277abb35a3.json`
- 大小：196 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/6cddea4a0803450e96b6e015785a432e.json`
- 大小：289 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/6d2463931e6f4fdb878cf0aab9e97f80.json`
- 大小：478 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/6d4e2d9c0019442d891630f96365d82b.json`
- 大小：257 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/6f6883e8f99048bfa050cfa56a1fbd3c.json`
- 大小：125 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/703bb4fd46784866b395ce4123e59797.json`
- 大小：196 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/71ad9663791d4503a9cc21fe5286423c.json`
- 大小：130 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/71de39d8e5d24bf5a68584f9297cef30.json`
- 大小：239 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/722795e5923047f8b8fdd4998874eb29.json`
- 大小：229 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/72c7ef5e99e8417e96f4610137eee579.json`
- 大小：282 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/747d104c41d44853b1c526c0c68ca0ef.json`
- 大小：297 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/757946c33baf4f4199bff9bb3204cc88.json`
- 大小：129 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/75d2213c486e4105a27433b1e992a68d.json`
- 大小：563 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/762ecf634b2d4ad1ba7cbb5ca92df8de.json`
- 大小：363 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/78fd82fbf7724cc5bb28a4f8998c9b29.json`
- 大小：372 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/79c267626af34fce9806382d692d7a10.json`
- 大小：181 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/7b42895f533c4e1191cc982592348eac.json`
- 大小：346 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/7c7b41f21ca84de49fb60e141919da28.json`
- 大小：241 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/7d0ed5424d994a6c9aae80b826555b34.json`
- 大小：124 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/7fcd6a6d6cdb462387221ea6ae1cbc8c.json`
- 大小：266 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/7ffbad912bb849319735c24cc7474d5e.json`
- 大小：229 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/82c452e8b3cf4b9e82d21e53c54b1db8.json`
- 大小：268 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/83cde0689a6e457e97f1d6bba6d5dc4f.json`
- 大小：277 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/83ffc74e1dcc489ab335afc17038f0ce.json`
- 大小：61 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/8458360b6ede463d8fc7a4fdff77917d.json`
- 大小：244 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/846be8836264436d932037dd8d78bd16.json`
- 大小：245 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/85539eef63934959832fe27ff9c05301.json`
- 大小：337 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/86fbeffef2e44203aadff033485ec505.json`
- 大小：219 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/87474cc2667a4caa8f5abd3eb0165a9d.json`
- 大小：167 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/883a999c42ea4f338d473b2192e20c16.json`
- 大小：185 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/89fe42e664f14f0ebc31204c909dc7ad.json`
- 大小：202 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/8b09e31fc70c4aeabf91f777f0212bd1.json`
- 大小：151 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/8ba8d3f7ddff48e6af7ef0a24e0faae1.json`
- 大小：326 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/8bec9e1ebd7a4731ba74e29446f89e73.json`
- 大小：107 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/8c00131f42614814b988728e445288f8.json`
- 大小：263 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/8c4310a9b7ea4f9f8f0d6f49b79686d0.json`
- 大小：244 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/8c96c03306634836a9f0a7f5223b2820.json`
- 大小：268 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/8ca9a351f4c04cfeaa01b09244d5a269.json`
- 大小：55 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/9201877bd72f440a93866cc433714d7a.json`
- 大小：252 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/93819693c55746fb9526a5425de69599.json`
- 大小：297 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/93a8529331644a068333955e25a61481.json`
- 大小：372 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/95f12496d79b474cb430cb3fff91b183.json`
- 大小：178 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/961b002d304c4daeb77f337fc9c6efe4.json`
- 大小：137 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/962483a4392b42a98a918a35c35ded3b.json`
- 大小：447 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/9658b7291ec74faeaf6c2d18fbea4da0.json`
- 大小：924 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/9666232ab10e4e58b9da9590913a842d.json`
- 大小：283 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/96681d5e48b54ddd91e6114b15cd26db.json`
- 大小：235 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/96b820bfb2b04d6eb9c3ab4488c107b1.json`
- 大小：161 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/97756f5114834e6586d925597e738d60.json`
- 大小：378 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/987b5451bab64201aa2ea90d8b5a2920.json`
- 大小：116 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/9d703111d49942dd9909c03046819cd1.json`
- 大小：61 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/9dde773a73b64bc0818198143e054502.json`
- 大小：218 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/9e5f727ee232443c90f7b1b363d057bf.json`
- 大小：122 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/a04c711c88d045e0b9c6a59da4d28d4f.json`
- 大小：304 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/a3235100d90642088f35d9c72d34ea40.json`
- 大小：260 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/a3cdbc21d8844f5abdce3c781088a2dd.json`
- 大小：336 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/a7574448f7694c2e8b3ba663cfa73915.json`
- 大小：281 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/ab4ed0963ccc413c976c86d31bcd61d8.json`
- 大小：273 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/aece62194dfe442cb792c966ec35c71c.json`
- 大小：230 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/aedeed49e9e8471f95447a67dd09b77f.json`
- 大小：155 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/b064d957aa2140c8a37f5a326a38144b.json`
- 大小：114 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/b0dec750a7ae4374932ac1f14e34205e.json`
- 大小：217 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/b36977aa1e7a459a90540c8083338794.json`
- 大小：152 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/b4058f6461934e24a4d5830e4bd61e36.json`
- 大小：356 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/b410a35dd13b44a6a8a53f1bc56d250c.json`
- 大小：242 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/b52041718a2b435a8169cf5b95c6511c.json`
- 大小：61 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/b578365ade4248a3ae0ae436865d8e25.json`
- 大小：217 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/b604a4ec4c0643979c7b6255abf04a51.json`
- 大小：232 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/b764fa68d98c465094c5147f23b8efed.json`
- 大小：172 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/b7b23d4f718a4faf993e800ec3218f72.json`
- 大小：205 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/baaaaca5ef92428b8f84428b4657df8f.json`
- 大小：279 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/bb15b9aa24344ba2a73c05ffd4d10a79.json`
- 大小：292 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/bd5575524db84943a2d58befcf96d192.json`
- 大小：353 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/bddad91f47f24dd1abd7ada566792b1d.json`
- 大小：357 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/bdefacd36c52401eaf478c1d0c4723b9.json`
- 大小：171 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/be8fc39fb14b4ba9be279401eb24ef4a.json`
- 大小：287 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/be93cc40a1224b7ca4bc45927883d290.json`
- 大小：365 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/c0f5373fad5342e6bc2cc85cf7150391.json`
- 大小：250 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/c1431a8519de4c1296c274bbea778de1.json`
- 大小：308 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/c16d46a8a5f948efb91e060065b704f9.json`
- 大小：142 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/c1aa5826c58146a692d4da6994270e42.json`
- 大小：282 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/c368ef5a65b746aaa22f11f71439ff55.json`
- 大小：601 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/c3ada8241e1c48fd88c303f1a72a58c2.json`
- 大小：295 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/c692b461237f4d2f943a2471387e3962.json`
- 大小：218 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/c75db68a1d5b46999cd59693029c8090.json`
- 大小：262 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/c82f87e5e3d64b8cbc7b304c89b83449.json`
- 大小：155 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/c83497f7f20847a1bc23bee1043f0b27.json`
- 大小：325 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/c9757d40cccd4adab596c5bf2be7ffab.json`
- 大小：206 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/c98b68eea01e4c1695e5f463aa9c8188.json`
- 大小：304 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/cb0b63b48fc04944bdcf90a927823464.json`
- 大小：113 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/cb9d4698f48b40b59c44cd508fc9cdc5.json`
- 大小：233 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/ccfffc68410e49f8b5c57f145f3429ff.json`
- 大小：242 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/cdb5a5062c274a9cbfbd431d2f22358c.json`
- 大小：224 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/d0853ee621b841a483d41e436cfee2a8.json`
- 大小：130 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/d2904521ee2c401682e3ddd3dbf28b57.json`
- 大小：742 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/d3d8f5e935094f17af1c4a063125b08a.json`
- 大小：241 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/d3e72d0176bb41d49d92b9f048cd09ff.json`
- 大小：214 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/db83b75107e84043bc93986c253aeb47.json`
- 大小：299 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/dbbe6cdb056d460eaba19d28694b43fd.json`
- 大小：127 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/de245c2826804a16a45ad277abd6d42d.json`
- 大小：107 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/dee3dd5f080d47dcaecbc67884a137dc.json`
- 大小：300 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e051d5ab8b82465fa4e67f73d8675007.json`
- 大小：207 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e137bfe0255348c6838f0f6c5f3318d2.json`
- 大小：61 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e15d119287134463860fcf33ebad3720.json`
- 大小：309 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e22cdebbf3db4df292638e734e144932.json`
- 大小：237 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e271568a05574657ac3f6c13f760e3b7.json`
- 大小：251 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e31c1d07cb86456b83dbb18a021eb90b.json`
- 大小：267 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e376f4969e6347df94a81d181419b911.json`
- 大小：232 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e3e0f548b2444540853a10c573066434.json`
- 大小：752 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e433a10c4e9c4f0589bf3482a239c57a.json`
- 大小：97 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e4b5ab3b7a8342a6ab1e63b45fd05828.json`
- 大小：193 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e644a9ef932c45678e33ab7ec5bd9e87.json`
- 大小：399 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e68951dd53ac413d94619b5674ad59b3.json`
- 大小：256 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e6bcb52a53cf45c3b07f465995bd1891.json`
- 大小：275 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e74ed1728cd643ac9dcc880bc374ba31.json`
- 大小：189 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e77c43892145407fbdcb314f1f597fcb.json`
- 大小：221 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e84273a2ddc8443ca89bb3779f60dcce.json`
- 大小：217 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e854db0a75994827a7714bb7d73f26d2.json`
- 大小：297 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/e88c87ea546b4cad8203bd8773f18a2f.json`
- 大小：500 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/ec4a7b657f864f3883bc1bd15556e1d4.json`
- 大小：316 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/efd08a2d3d40408ea8bad82b58d530ba.json`
- 大小：160 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/f21caed19e53433a912ab7daec2ef0ab.json`
- 大小：196 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/f4c59e37697a41b8a0dcff882dfdcca6.json`
- 大小：209 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/f6c3c54cfc624216aae59bf9a8e2c587.json`
- 大小：286 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/fa7c45202c4a43b797a97c2a91280701.json`
- 大小：94 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/fe6c5665c13e4f03997f3dcf694a16f8.json`
- 大小：248 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/ff2b211a9f6d4047989435e237abbbeb.json`
- 大小：333 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_live2d/ffb00c42a4cd44ebb7598fe10c7c73bb.json`
- 大小：149 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：注意区分 mock Live2D 与真实 Live2D 路径

### `data/cache/mock_tts/0299edfb-5fac-44d8-941b-df753ead9793.txt`
- 大小：360 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/03254b56-50a0-41e1-80c8-01090828ba22.txt`
- 大小：240 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/03779477-6005-4a63-bf40-1a2d675adc58.txt`
- 大小：39 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/044420eb-423b-4896-aa5b-8686b692c208.txt`
- 大小：87 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/06b322cf-b242-49c8-941d-1ce146173820.txt`
- 大小：189 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/06bd7153-280f-4dfd-b6f7-1e0d77245b23.txt`
- 大小：197 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/07a98759-8d5e-463e-a84b-f823c2146b81.txt`
- 大小：195 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/0a12974d-3785-4cd7-ba1d-f17f6238fbe6.txt`
- 大小：123 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/0a7f92ed-f078-47e4-8fc6-9529e2cdb717.txt`
- 大小：78 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/0aadf82e-a869-4f27-8398-8bdbcc65e73e.txt`
- 大小：189 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/0b52a104-605b-469a-b0bd-efa9a8bff01f.txt`
- 大小：96 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/0f49194e-af27-47ee-bd54-7eac5e350fa0.txt`
- 大小：195 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/100d64bb-3054-4c8d-a074-3790080050ec.txt`
- 大小：158 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/10257b3d-0e74-4969-a355-d7cee20a0041.txt`
- 大小：317 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/102d3e9e-cdd9-4d7a-b451-c56a13f95b58.txt`
- 大小：235 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/104d6f30-73e3-496d-8186-a12858c6ef92.txt`
- 大小：87 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/11a0a438-12fd-4d54-9c41-e1fcf067b85c.txt`
- 大小：219 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/12acee05-05b9-4b8a-90e4-da926cbc608b.txt`
- 大小：105 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/132f163b-a226-4956-820b-891561366829.txt`
- 大小：533 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/181791d4-822b-417e-95f9-544d2eb3044d.txt`
- 大小：84 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/1868768d-0644-4bf5-a22d-b179d8210305.txt`
- 大小：110 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/1b07389c-870e-4bd1-953c-063c603c6b5d.txt`
- 大小：194 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/1c9f4986-2fa5-4c22-bc58-11c02b0f18e9.txt`
- 大小：177 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/1cd9fe61-04fb-44ba-84dc-6f697b4e9012.txt`
- 大小：90 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/1ce4876a-3ffb-4f3f-8f84-055a085f7ce3.txt`
- 大小：147 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/1ea512ab-11d4-4435-839c-1a1d0e376d1b.txt`
- 大小：111 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/204a3b92-1f7c-4a83-aaf2-ed226c168e98.txt`
- 大小：6 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/21a0c4f4-ef3f-4cd0-92c4-7cd3bcff502f.txt`
- 大小：269 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/23e69548-46a5-45db-aeef-747f2592a217.txt`
- 大小：282 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/25509300-97d7-4427-a248-aadb9cad4b5e.txt`
- 大小：279 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/256c7cdd-c4ff-4326-86f3-73bc71e56800.txt`
- 大小：42 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/2591f664-60af-43c2-a15d-19516a89de0d.txt`
- 大小：400 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/266aa047-03be-4164-a520-e9298c9c436b.txt`
- 大小：195 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/2a22fa90-e315-46eb-b942-dc4092e0a30e.txt`
- 大小：69 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/2adcbc4a-d755-4955-aa37-2206667a46cd.txt`
- 大小：199 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/2af2c033-e994-489d-a7ff-8541b6ceed2b.txt`
- 大小：679 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/2d822287-fe89-4609-a853-de446ef636d9.txt`
- 大小：123 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/2dbac26e-6da2-4fdd-aa46-653bc8a615ac.txt`
- 大小：126 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/31d20f38-1390-41e1-aaf0-6b7d4d641a9a.txt`
- 大小：261 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/31e133f5-3560-4624-a2d1-d0ed49eac7bb.txt`
- 大小：87 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/341dedb8-fc95-4981-9aa0-fc834174296a.txt`
- 大小：108 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/395701fc-8904-4185-86d2-e9099d1d342d.txt`
- 大小：74 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/3bcd251e-be9e-4199-8c1b-75b7a7896222.txt`
- 大小：624 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/3d9cfe04-44b3-4c27-8a30-c4c895d30e7f.txt`
- 大小：171 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/3e704279-450a-4d2f-83ff-c90155788bed.txt`
- 大小：108 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/3f9bb3c3-fb42-4c75-9aaa-f302c98eb818.txt`
- 大小：116 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/3fc3ce04-d46c-4b7c-b069-a8e67c9e583f.txt`
- 大小：226 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/3ffc87d9-e6a2-4101-886b-e7ec7c6d6dfa.txt`
- 大小：114 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/40262ffc-c962-41a9-b933-72bc043d24b7.txt`
- 大小：178 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/43f4e998-3cd8-409b-913e-73121a1e30fa.txt`
- 大小：213 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/455a9d3c-2f1d-471a-af89-a52172453506.txt`
- 大小：207 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/4609b4e3-add1-4fa2-8f56-0927b361b8a0.txt`
- 大小：99 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/4c593fd4-cec2-484a-a264-0cf1ec635fe5.txt`
- 大小：227 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/4d5dba3d-359a-4217-8135-be8c1ea2e34b.txt`
- 大小：141 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/4e69887b-a09a-438b-9fdb-6fbd1b5d0402.txt`
- 大小：6 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/4e7a1dfc-56e7-40dc-ade0-dfc31bbdc626.txt`
- 大小：292 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/4e97a957-0f8d-47eb-a9be-623f1eb1f707.txt`
- 大小：221 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/508d6618-10cb-43ef-a9ba-9d713e97bfac.txt`
- 大小：225 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/51e34aca-8cd6-4152-a55c-0b319f8b0ce2.txt`
- 大小：496 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/51ea101c-2bec-46c5-a030-bd58a4f83266.txt`
- 大小：70 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/5420c123-1199-4655-b6d1-5712cf93a8ea.txt`
- 大小：194 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/544e2175-78d1-4e6b-8adb-2c76abc6b5d1.txt`
- 大小：687 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/55651b04-e735-4304-80ea-5da62121b8b8.txt`
- 大小：42 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/56119857-159b-4887-8691-eba5181c9377.txt`
- 大小：123 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/586b4826-7152-4d59-bc39-6cb0c5369158.txt`
- 大小：260 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/5909f0d2-5dc6-47b9-86f9-30f0969d5922.txt`
- 大小：81 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/592bb4aa-a2cc-4b62-8183-8f8e102e30f7.txt`
- 大小：201 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/59f21280-e130-4e51-b521-0ad0272e96b0.txt`
- 大小：64 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/5ba9f4de-c0ec-44a2-a315-9e5bfa5a9d0c.txt`
- 大小：504 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/5c6cd7b1-24e4-4fd7-96e1-7b74141a8a0d.txt`
- 大小：218 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/5e1a111c-0ee1-49e8-8b26-68ecfd554814.txt`
- 大小：220 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/60f2875b-4aca-4bde-9eb4-3d81fc4f9557.txt`
- 大小：196 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/65557760-5159-43ca-bc94-c72e19b3fcf8.txt`
- 大小：102 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/65e70e6d-b89b-445c-9145-148154f2b876.txt`
- 大小：247 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/69be5f8d-23ae-4e9f-89d5-25132e6153d1.txt`
- 大小：177 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/6c1191c3-1e1c-4996-9b1b-1689a66b9b5c.txt`
- 大小：117 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/6d7955c1-91fa-4608-b812-5550c0841324.txt`
- 大小：509 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/6fdbd3da-1df3-4c6c-9918-40e82898ee40.txt`
- 大小：99 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/7174442e-bca9-49dc-af56-e71ca83b146d.txt`
- 大小：313 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/71dfa72e-b022-4005-99eb-f58546837b3c.txt`
- 大小：124 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/723fbee1-64e2-4650-bdd4-c4bb428fb9fe.txt`
- 大小：93 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/73b45726-aefa-4c86-af6b-ffc0af1f3458.txt`
- 大小：153 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/73df210a-80fb-4afe-ae2f-ab2568f37060.txt`
- 大小：188 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/742ac1ff-59d4-41b4-b7b5-3da18a2930e2.txt`
- 大小：216 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/74cd4c99-ea54-4676-a169-6ce8b938d3fb.txt`
- 大小：177 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/752f737d-459f-4889-8e8c-ca2fe3ebb898.txt`
- 大小：75 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/791d954e-f046-41f9-ad06-1ba4df7b9508.txt`
- 大小：255 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/7e8b5c75-86b5-49f9-89cf-253f8df6b8fa.txt`
- 大小：72 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/7f804d2b-7c59-4daf-9f23-e247a5118aae.txt`
- 大小：114 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/835860da-9da6-4b8f-9d94-f76beefaf482.txt`
- 大小：224 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/84daa706-98c0-4e10-8241-bc1707f26fed.txt`
- 大小：294 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/86f0964e-92bb-4376-813a-3c035994a2bb.txt`
- 大小：97 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/875e9339-80f7-4923-acb0-572914db9654.txt`
- 大小：39 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/87f7045d-1ae4-42c7-9036-5c1562c65e03.txt`
- 大小：166 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/891308ea-ac15-407f-9d11-1fd32d0115b4.txt`
- 大小：237 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/89ac027c-f16e-4b5a-9b31-b9ff5855a35c.txt`
- 大小：141 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/8aae5b4f-7988-4ec7-8546-eccec8e0dd20.txt`
- 大小：100 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/92445eef-0bc1-4ca5-8155-818a2035ebc1.txt`
- 大小：269 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/9575658b-fe0e-4945-a2e4-0f66aa307f5e.txt`
- 大小：186 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/9687c009-3c4a-4625-bf69-2be2981baa39.txt`
- 大小：114 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/96c2e903-5a77-40c0-84d8-a216b773dee7.txt`
- 大小：6 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/98add22b-c3d3-409f-92bf-e02275161139.txt`
- 大小：145 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/9d9b37fb-7b36-4361-94a8-5976420dbd67.txt`
- 大小：229 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/9e957f0d-bbbc-40d9-855f-07a29294fa3c.txt`
- 大小：84 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/a05ed582-6974-45f0-b628-ea44ff9c9af3.txt`
- 大小：229 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/a1e3fa9c-0b6a-4afc-8ef0-64465c07ffaf.txt`
- 大小：168 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/a1ec301f-0f7d-46dc-a51e-9891c28c5725.txt`
- 大小：141 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/a2414485-0882-4567-a851-0e0bd27dbbd8.txt`
- 大小：158 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/a255857b-4a80-431e-b28b-42e0c05623d4.txt`
- 大小：59 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/a502b128-4501-4955-af26-2e2e6cfa1bce.txt`
- 大小：256 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/a69999dc-0718-4b96-8116-5f38c194a759.txt`
- 大小：167 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/a7467e3f-4d09-4ef5-9c76-c4e26db89769.txt`
- 大小：180 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/a87dc49c-9538-4964-97cd-a577de57730e.txt`
- 大小：103 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/a97f4d6a-8c46-4de7-85bd-fd55656a2f91.txt`
- 大小：134 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/ae0cc417-ef42-4c61-8c0b-170d757adce4.txt`
- 大小：213 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/b2930d1d-bc3f-4c7c-81ff-e9c23df5d32b.txt`
- 大小：633 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/b518c1bb-9cdc-4b62-9640-238434c598b3.txt`
- 大小：237 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/b56b3485-00ac-4b03-bd51-06a122c9738b.txt`
- 大小：52 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/b6dbab39-91ca-46dd-8ca9-ada7f3364b18.txt`
- 大小：240 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/b75e6703-edb7-41c0-95f7-0dc256b76eaf.txt`
- 大小：229 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/b7f5f006-65db-45c1-9174-95ad08a79fb7.txt`
- 大小：42 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/b86a14d5-80c7-4846-b254-e0589b64ea73.txt`
- 大小：93 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/b8907182-f61c-48c5-b798-f2d10dc385b7.txt`
- 大小：236 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/b9467949-39c6-4552-b061-f8392b568633.txt`
- 大小：219 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/b98f332d-9f64-4d61-9792-c70b68ec1373.txt`
- 大小：288 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/bf76ba3c-3d5a-46bf-9998-c5b8774d00e3.txt`
- 大小：151 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/c14bcf5a-04d6-4d77-8424-e6189ca5c0ec.txt`
- 大小：211 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/c200b7fd-e70f-4510-85b9-7d50ede01f23.txt`
- 大小：129 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/c31ebdb0-eebe-4a82-9a77-d61520b93dc4.txt`
- 大小：152 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/c5d83cae-f6d1-42b5-931e-4ecc2d80bb39.txt`
- 大小：150 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/c645bbbc-f69c-45a1-b079-6d91b2ce88a2.txt`
- 大小：171 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/c67e9901-1670-4ae1-af2a-0cdeb48bf6c1.txt`
- 大小：205 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/c6b60f83-db37-4226-8172-1743df94a255.txt`
- 大小：382 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/c6c1055a-63ef-44be-b612-01437538d44a.txt`
- 大小：865 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/c6c107dd-261d-48f3-99e2-4753291474d4.txt`
- 大小：138 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/c84430bd-c890-4f52-9f94-d59bc194237f.txt`
- 大小：180 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/c8c2b151-7a0b-48a3-844d-9ccfad7757fb.txt`
- 大小：165 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/ce159a00-7e10-42f2-a303-ff4ca884d7de.txt`
- 大小：177 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/ce322f60-10af-498f-9866-9147b2f11126.txt`
- 大小：136 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/d16b928c-569b-4aac-8d3e-7b33a7941a2b.txt`
- 大小：162 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/d2772519-c64a-48ce-9991-34c82ae77573.txt`
- 大小：114 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/d2bb8de5-dee1-4c2b-a79e-bf58eea1a878.txt`
- 大小：165 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/d470c63c-0513-40d8-bdad-62d1b8c644a2.txt`
- 大小：162 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/d6ea68c8-9891-4ea3-8055-7b9c8480face.txt`
- 大小：118 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/dbfe96ce-da9b-4e81-91d9-6976f9c2ad99.txt`
- 大小：165 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/dc222d64-d362-48c2-bf17-13b61a9ec593.txt`
- 大小：123 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/dc25020a-8b8f-4720-a429-343d8f1ec210.txt`
- 大小：295 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/dc928183-8354-4e54-a97d-45f114fb7525.txt`
- 大小：156 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/de2f760d-1a62-4456-b1e2-c78b7a976150.txt`
- 大小：75 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/df932805-786a-4565-b746-06c4e11d6e29.txt`
- 大小：233 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/df9cf004-0756-47dd-bc4f-163026b04f8a.txt`
- 大小：96 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/e1a08390-34a2-4d27-a216-db432398f3d6.txt`
- 大小：174 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/e1a9a0f1-420d-4028-886c-6583c8e21e20.txt`
- 大小：248 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/e29264a7-1f62-4594-b8eb-11443bb09618.txt`
- 大小：300 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/e2e81476-0aec-472b-bf76-9b4771833822.txt`
- 大小：129 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/e43b2d05-7515-4954-bc0a-c770d71ada69.txt`
- 大小：78 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/ecadff85-0ca2-4270-ba2e-e5174d6cd0c2.txt`
- 大小：0 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/eda04eba-5a7a-4836-be7b-197d4868a322.txt`
- 大小：141 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/edc2a334-98fd-4112-9787-025e3415004d.txt`
- 大小：258 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/f04d2092-795a-4def-adb0-57ba42d73bba.txt`
- 大小：9 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/f04f3add-5132-4097-a493-56b6d0d59cde.txt`
- 大小：75 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/f05fedc1-0e8e-42be-8ef0-050a96b5c669.txt`
- 大小：136 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/f09775ac-ad19-43f0-ab46-7b011778e268.txt`
- 大小：117 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/f7a4d379-2269-4205-ab63-25ee12715fa4.txt`
- 大小：141 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/f7ec45e4-bbb5-41ea-9425-e267d9f5d875.txt`
- 大小：48 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/faaa6c30-122a-460f-bdda-943175a3b0f0.txt`
- 大小：6 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/fce9a0c4-9c31-4410-8c0e-14063fd4eae8.txt`
- 大小：183 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/fd01daad-883c-4eb7-b9d9-5b1fd061fcd4.txt`
- 大小：202 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/mock_tts/ff8ebc4b-3660-4b9a-9701-72f48b0588b9.txt`
- 大小：334 bytes
- 类型：文本/源码/配置
- 作用：依赖、锁文件、构建或打包配置。

### `data/cache/tts_real/05ede5f3940a4c94ba200cbbca8c5c57.wav`
- 大小：1843244 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/162076a80f024a5bbea49c0b0836cd2a.wav`
- 大小：1038124 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/3413f8d86d354611b9fb3a7f32dee5f2.wav`
- 大小：587564 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/589b2829a31a44f6922e0abefd61aba7.wav`
- 大小：1751084 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/6d5daed6e58a463a94fabd4282489e21.wav`
- 大小：1766444 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/6ebd87cf58124aaea160e622ff4f91b8.wav`
- 大小：1551404 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/713b67d64dca48d7bac0a3a7e8d43403.wav`
- 大小：789804 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/757d8ef77e2f45e7b08bd808fd5d02ef.wav`
- 大小：910124 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/7604c48346414a56abe844b7e45e79bb.wav`
- 大小：2826284 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/7c3d4a11553f4c73bd370499a76dd675.wav`
- 大小：423724 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/9e4dd6b4e14d4a4095538db1b5ffa13f.wav`
- 大小：851244 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/bbca7b3dea4a41f3954bc2479affc173.wav`
- 大小：922924 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/c20db19753b74b11baf53a425b70a116.wav`
- 大小：2534444 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/ca6627d9ba194ca9a8b9b19ce137a2ff.wav`
- 大小：1981484 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/d0dba27335a84b8ba5d81f8c81b5e152.wav`
- 大小：1009964 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/ddb8e2c434f24c64a9effa8b89c96d9b.wav`
- 大小：231468 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/dea664f5566e48948f09d6bd68091bf1.wav`
- 大小：856364 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/e4a69e2ef53c4a9b97be5d1210c65cc4.wav`
- 大小：1013804 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/tts_real/e5cb6593d3e74368a2d8ced7656a8638.wav`
- 大小：783404 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/uploads/upload_asr.wav`
- 大小：10028 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

### `data/cache/vision/character_index/faiss.index`
- 大小：262189 bytes
- 类型：二进制/资源/生成物
- 作用：二进制、模型、索引或缓存文件，不是源码，主要由运行时或工具读取。
- 注意：属于视觉角色识别链路，避免重复新增检索器

### `data/cache/vision/character_index/records.json`
- 大小：84530 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。
- 注意：属于视觉角色识别链路，避免重复新增检索器

### `data/cache/vision/vision_batch_report.json`
- 大小：24158 bytes
- 类型：文本/源码/配置
- 作用：运行时生成的 JSON 缓存或命令输出，不建议作为手写源码依赖。

### `data/cache/voice_turns/1ddd3f66ee914d6aa6708ccdc8f49c37.wav`
- 大小：184044 bytes
- 类型：二进制/资源/生成物
- 作用：音频资源或录音缓存，用于 ASR、TTS 参考音频、桌面录音或运行时测试。

## 运行时装配与核心门面

### `apps/core/__init__.py`
- 大小：0 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `apps/core/bootstrap.py`
- 大小：15318 bytes
- 类型：文本/源码/配置
- 作用：运行时装配或生命周期模块；函数：_resolve_env_secret、build_runtime
- 主要依赖：aiagent.brain.agent_core、aiagent.brain.dialogue_manager、aiagent.cognition.planner_normalizer、aiagent.cognition.planner_reply、aiagent.cognition.state_analyzer、aiagent.cognition.state_normalizer、aiagent.common.logger、aiagent.expression.audio_playback_dispatcher、aiagent.expression.live2d_payload_dispatcher、aiagent.expression.mock_live2d_dispatcher、aiagent.expression.motion_policy、aiagent.expression.output_broadcaster、aiagent.expression.tts_dispatcher、aiagent.graphs.llm_graph、aiagent.graphs.main_graph、aiagent.graphs.memory_graph、aiagent.graphs.planner_graph、aiagent.graphs.rag_graph、aiagent.graphs.state_graph、aiagent.graphs.vision_graph、aiagent.knowledge.document_loader、aiagent.knowledge.rag_pipeline、aiagent.knowledge.reranker、aiagent.knowledge.retriever、aiagent.knowledge.vector_store
- 顶层函数：_resolve_env_secret、build_runtime
- 注意：属于记忆链路，可能依赖外部向量数据库

### `apps/core/main.py`
- 大小：1715 bytes
- 类型：文本/源码/配置
- 作用：运行时装配或生命周期模块；函数：print_section、main
- 主要依赖：__future__、apps.core.bootstrap、config.settings
- 顶层函数：print_section、main

### `apps/core/runtime.py`
- 大小：15893 bytes
- 类型：文本/源码/配置
- 作用：运行时装配或生命周期模块；类：CoreRuntime
- 主要依赖：aiagent.brain.agent_core、aiagent.brain.dialogue_manager、aiagent.graphs.graph_model、aiagent.graphs.memory_graph、aiagent.graphs.vision_graph、aiagent.knowledge.rag_pipeline、aiagent.memory.mem0_memory、aiagent.orchestrator.dispatcher、aiagent.orchestrator.interrupt_manager、aiagent.perception.asr_listener、aiagent.perception.source_router、aiagent.perception.voice_session_controller、aiagent.perception.voice_turn_manager、aiagent.schemas.inputs、aiagent.schemas.outputs、aiagent.services.llm_service、aiagent.services.vision_service、aiagent.state.conversation_state、aiagent.state.speaking_state、aiagent.state.stream_state
- 类 `CoreRuntime`：方法 __init__、handle_input_event、handle_source_payload、handle_chat、handle_chat_full、handle_asr_text、handle_voice_once、handle_voice_turn、handle_multimodal_chat_upload、interrupt_speaking、transcribe_audio_file、get_knowledge_stats、rebuild_knowledge_index、rebuild_knowledge_index_async、get_knowledge_rebuild_status
- 注意：属于记忆链路，可能依赖外部向量数据库

### `apps/core/runtime_registry.py`
- 大小：732 bytes
- 类型：文本/源码/配置
- 作用：运行时装配或生命周期模块；函数：get_runtime、get_runtime_error、reset_runtime
- 主要依赖：__future__、apps.core.bootstrap、apps.core.runtime
- 顶层函数：get_runtime、get_runtime_error、reset_runtime

## 配置、默认值与环境变量

### `config/__init__.py`
- 大小：29 bytes
- 类型：文本/源码/配置
- 作用：Python 模块，提供项目业务逻辑或集成胶水代码。

### `config/defaults.py`
- 大小：1361 bytes
- 类型：文本/源码/配置
- 作用：人格或 YAML 配置加载模块

### `config/paths.py`
- 大小：389 bytes
- 类型：文本/源码/配置
- 作用：视觉、图片或角色识别模块
- 主要依赖：pathlib

### `config/providers.py`
- 大小：449 bytes
- 类型：文本/源码/配置
- 作用：外部服务客户端或 API 调用适配模块；类：LLMProvider、StateProvider、PlannerProvider
- 主要依赖：enum
- 类 `LLMProvider`：方法 无显式方法
- 类 `StateProvider`：方法 无显式方法
- 类 `PlannerProvider`：方法 无显式方法

### `config/settings.py`
- 大小：9584 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：Settings
- 主要依赖：config.defaults、pydantic、pydantic_settings
- 类 `Settings`：方法 _empty_rag_embedding_dimensions_to_none、_empty_memory_embedding_dims_to_default

## 长期记忆适配

### `aiagent/memory/__init__.py`
- 大小：20 bytes
- 类型：文本/源码/配置
- 作用：记忆系统模块
- 注意：属于记忆链路，可能依赖外部向量数据库

### `aiagent/memory/mem0_memory.py`
- 大小：12774 bytes
- 类型：文本/源码/配置
- 作用：应用配置定义模块；类：MemoryHit、Mem0LongTermMemory
- 主要依赖：__future__、dataclasses、logging、mem0、os、threading、typing、urllib.parse
- 类 `MemoryHit`：方法 无显式方法
- 类 `Mem0LongTermMemory`：方法 __init__、search、add_turn、_build_chinese_memory_prompt、get_all、delete_all、format_for_prompt、_normalize_search、_format_relations、_resolve_secret、_normalize_embedder_provider、_extend_no_proxy、_looks_like_secret
- 注意：属于记忆链路，可能依赖外部向量数据库

## 项目设计与说明文档

### `docs/architecture.md`
- 大小：83 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Architecture

### `docs/event-flow.md`
- 大小：92 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Event Flow

### `docs/implementation-plan.md`
- 大小：1585 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。aiagent Implementation Plan

### `docs/migration-plan.md`
- 大小：57 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Migration Plan

### `docs/persona-design.md`
- 大小：96 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Persona Design

### `docs/project-file-inventory.md`
- 大小：212338 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Project File Inventory
- 注意：注意区分 mock Live2D 与真实 Live2D 路径；属于记忆链路，可能依赖外部向量数据库

### `docs/project-overview-next-stage.md`
- 大小：9016 bytes
- 类型：文本/源码/配置
- 作用：Markdown 文档。Project Overview And Next Stage Plan
- 注意：属于记忆链路，可能依赖外部向量数据库
