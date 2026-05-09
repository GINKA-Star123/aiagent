# 项目总览与下一阶段计划

## 当前架构总览

项目当前已经形成一个多模态 AI Agent Runtime，主要分为以下层级。

### 1. 运行时与 API 层

- `apps/core/bootstrap.py`：完整运行时装配入口，负责把 LLM、RAG、记忆、视觉、TTS、ASR、Live2D、输出广播等组件组装起来。
- `apps/core/runtime.py`：API 层调用的核心门面，提供 chat、voice、vision、memory、knowledge、multimodal 等入口。
- `apps/api/http_server.py`：FastAPI 应用注册入口。
- `apps/api/routes/*`：HTTP 边界层。这里应保持轻量，只做请求解析、错误包装和调用 runtime 或集成服务。

### 2. 主 Agent 图流程

- `aiagent/graphs/main_graph.py`：主流程图，负责串联上下文准备、视觉图、记忆检索、状态分析、规划、RAG、LLM、记忆写入和最终 `ResponsePacket` 构建。
- `aiagent/graphs/state_graph.py`、`planner_graph.py`、`rag_graph.py`、`llm_graph.py`、`memory_graph.py`、`vision_graph.py`：各自负责独立子流程。
- `aiagent/graphs/graph_model.py`：图流程共享状态和结果模型。

### 3. Persona 人格系统

- `aiagent/persona/persona_loader.py`：读取 persona YAML。
- `aiagent/persona/persona_manager.py`：管理当前人格。
- `aiagent/persona/persona_runtime.py`：构建运行时人格上下文。
- `aiagent/persona/persona_prompts.py`：人格提示词生成。
- `aiagent/persona/persona_guard.py`：回复归一化和人格防漂移。
- `data/persona/yzl/persona.yaml`：乐正绫人格配置。
- `scripts/generate_yzl_persona_dataset.py`：LoRA 数据集生成脚本。注意它应和 runtime persona 逻辑保持分离。

### 4. 视觉与识图系统

- `aiagent/vision/image_store.py`：保存上传图片。
- `aiagent/vision/character_registry.py`：加载角色图库配置。
- `aiagent/vision/character_retriever.py`：基于本地角色图库进行候选召回。
- `aiagent/services/vision_service.py`：整合本地角色召回和模型视觉分析。
- `aiagent/graphs/vision_graph.py`：把识图结果转换成聊天上下文、记忆提示和 Live2D 建议。
- `apps/api/routes/vision.py`、`apps/api/routes/multimodal_chat.py`：提供直接识图和多模态聊天入口。

### 5. RAG 知识库系统

- `aiagent/knowledge/document_loader.py`：加载知识文档。
- `aiagent/knowledge/retriever.py`：BM25 与向量召回。
- `aiagent/knowledge/vector_store.py`：向量库与 embedding 适配。
- `aiagent/knowledge/reranker.py`：简单重排。
- `aiagent/knowledge/rag_pipeline.py`：索引构建、检索、上下文格式化和 rebuild 状态。
- `aiagent/graphs/rag_graph.py`：决定何时注入知识上下文。
- `apps/api/routes/knowledge.py`：知识库 stats、rebuild、search API。

### 6. 长期记忆系统

- `aiagent/memory/mem0_memory.py`：Mem0、Qdrant、图记忆适配。
- `aiagent/graphs/memory_graph.py`：记忆检索和写入流程。
- `aiagent/services/memory_policy_llm_service.py`：判断一轮对话是否值得写入长期记忆。
- `apps/api/routes/memory.py`：记忆 stats、search、clear API。

### 7. 语音与音频系统

- `integrations/asr/*`：麦克风、VAD、mock ASR、Faster Whisper ASR。
- `aiagent/perception/*`：输入源归一化和语音回合管理。
- `integrations/tts/*`：GPT-SoVITS、IndexTTS2、VoxCPM、mock TTS 和文本清理。
- `aiagent/expression/tts_dispatcher.py`：TTS 调度。
- `aiagent/expression/audio_playback_dispatcher.py`：音频播放调度。
- `apps/api/routes/voice.py`、`audio.py`：语音识别、语音状态和音频访问 API。

### 8. Live2D 系统

- `aiagent/live2d/*`：Live2D 领域层，负责角色 profile、动作映射、表情映射、场景映射和 payload 构建。
- `aiagent/expression/live2d_payload_dispatcher.py`：从 `ResponsePacket` 生成 Live2D 命令文件。
- `integrations/live2d/*`：集成层，负责文件客户端、Python Live2D runtime 检查、模型扫描、profile 生成、模型会话、headless renderer 和 Qt OpenGL 控件。
- `apps/api/routes/live2d.py`：Live2D stats、preview、runtime inspect、model scan、profile generate API。
- `apps/desktop_qt/live2d_view_panel.py`、`integrations/live2d/qt_live2d_widget.py`：Qt 前端 Live2D 面板。

### 9. Qt 前端

- `apps/desktop_qt/chat_window.py`：当前主调试前端。已经包含聊天、图片上传、语音录制、记忆显示、知识库控制、API Detail、Live2D 面板。
- 新增 Qt 功能应优先做成 panel/widget 并插入该窗口。

### 10. Web 前端

- `apps/web`：Next.js 前端骨架，目前主要是 README 和基础页面。
- 当前主力前端仍是 Qt。

## 当前阶段状态

- 第一阶段：核心聊天、RAG、记忆、Persona 基础能力已经基本成型。
- 第二阶段：识图、多模态聊天、角色图库召回、VisionGraph 接入已经完成。
- 第三阶段：Live2D payload、Python runtime 检查、Qt 面板、模型资源工具已经完成。真实 Cubism 模型资源尚未放入。

## 当前关键缺口

1. 真实 Live2D 模型资源缺失。
   - 预期路径：`data/live2d/characters/yzl/model/yzl.model3.json`
   - 当前 `scripts/test_phase3_live2d.ps1` 返回 `model3_json_missing` 是正确状态，不是代码错误。

2. 工作区存在未提交改动。
   - 当前 `git status` 显示 persona、config、bootstrap、Live2D 相关文件仍有改动。
   - 大改前建议先确认这些改动是否预期，并做一次提交或快照。

3. 运行缓存较多。
   - `data/cache/mock_live2d/*.json`、录音、上传图片、知识库缓存等是运行产物。
   - 后续不要把缓存文件当成源码依赖。

4. `domain/*` 多数是早期占位。
   - 当前有效业务主要在 `aiagent/*`、`apps/*`、`integrations/*`。
   - 不建议把新功能写进 `domain/*`，除非明确要做领域层重构。

## 下一阶段建议

建议第四阶段先做稳定化和工程收敛，不建议立即继续开大功能。

### 优先级 1：运行时稳定性

- 做统一启动诊断，检查 Qdrant、RAG embedding、memory provider、vision provider、TTS、ASR、Live2D 模型资源。
- 可选子系统不可用时应明确降级，而不是直接 500。
- 在 `config/settings.py` 中补 provider 组合校验。

### 优先级 2：测试收敛

应补以下测试：

- `/chat`
- `/chat/multimodal`
- `/vision/analyze`
- `/live2d/preview`
- `/knowledge/rebuild/status`
- `PersonaGuard`
- `Live2DPayloadBuilder`
- `VisionService` mock 与本地召回路径
- `RAGPipeline` rebuild/status

### 优先级 3：真实 Live2D 模型接入

接入顺序：

1. 把真实 Cubism 资源放入 `data/live2d/characters/yzl/model`。
2. 运行 `scripts/scan_live2d_models.ps1`。
3. 使用 `scripts/generate_live2d_profile.ps1` 生成或更新 `profile.yaml`。
4. 运行 `scripts/test_phase3_live2d.ps1`。
5. 打开 Qt 前端验证模型渲染和 payload 驱动。

### 优先级 4：Qt 前端整理

- 把 API Detail、Memory Status、Live2D Payload、Runtime Snapshot 改成 tabs。
- 把图片上传和 Live2D 显示保持在同一调试工作流里。
- 右侧面板不要继续无限纵向堆叠。

### 优先级 5：训练数据工具规范

- 保持 `scripts/generate_yzl_persona_dataset.py` 作为唯一数据集生成入口。
- 增加 dataset lint：
  - 重复 prompt 检查
  - 禁词检查
  - 核心/日常/功能比例检查
  - 过长样本检查
  - 功能问答是否先给正确答案

## 后续开发入口规则

- 新 HTTP 接口：写在 `apps/api/routes/*`，保持薄封装。
- 新 runtime 能力：写在 `apps/core/runtime.py`，必要时在 `apps/core/bootstrap.py` 装配。
- 新图流程行为：写在 `aiagent/graphs/*`。
- 新 LLM prompt 或归一化：写在 `aiagent/cognition/*` 或 `aiagent/persona/*`。
- 新识图能力：写在 `aiagent/services/vision_service.py`、`aiagent/vision/*` 或 `aiagent/graphs/vision_graph.py`。
- 新记忆策略：写在 `aiagent/graphs/memory_graph.py` 或 `aiagent/services/memory_policy_llm_service.py`。
- 新 Live2D 能力：
  - 领域映射：`aiagent/live2d/*`
  - 输出调度：`aiagent/expression/live2d_payload_dispatcher.py`
  - Python/Qt/文件集成：`integrations/live2d/*`
  - Qt UI：`apps/desktop_qt/*`
- 新 Qt UI：优先做 panel/widget 并接入 `apps/desktop_qt/chat_window.py`。

如果一个新文件无法落到上述入口之一，通常说明它在重复已有功能。
