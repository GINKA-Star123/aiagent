# 项目总览与下一阶段方向

本文档记录当前项目结构、阶段完成情况、工程边界和下一阶段建议。

## 当前项目定位

本项目已经形成一个多模态 AI Agent Runtime，包含：

- 文本聊天
- Persona 人格系统
- RAG 知识库
- 长期记忆
- 视觉识别
- 多模态聊天
- 语音识别与语音合成
- Live2D payload 与模型检查
- Qt 桌面调试前端
- API 诊断、测试与可观测性基础设施

## 核心分层

### API 层

主要文件：

```text
apps/api/http_server.py
apps/api/routes/*
apps/api/response_utils.py
apps/api/middleware.py
apps/api/request_context.py
```

职责：

- 注册 FastAPI 应用
- 解析 HTTP 请求
- 调用 runtime 或集成服务
- 返回统一 JSON 响应
- 记录 request_id 与请求耗时

新增 route 时应保持轻量，不要把业务流程写进 route。

### Runtime 层

主要文件：

```text
apps/core/bootstrap.py
apps/core/runtime.py
apps/core/runtime_registry.py
```

职责：

- 组装 LLM、RAG、Memory、Vision、TTS、ASR、Live2D 等组件
- 向 API 层提供稳定门面
- 管理运行时单例和初始化错误

### Graph 层

主要文件：

```text
aiagent/graphs/main_graph.py
aiagent/graphs/state_graph.py
aiagent/graphs/planner_graph.py
aiagent/graphs/rag_graph.py
aiagent/graphs/memory_graph.py
aiagent/graphs/vision_graph.py
aiagent/graphs/llm_graph.py
aiagent/graphs/graph_model.py
```

职责：

- 串联一次完整对话流程
- 状态分析
- 回复规划
- RAG 检索
- 记忆检索与写入
- 视觉结果转聊天上下文
- LLM 回复

### Persona 层

主要文件：

```text
aiagent/persona/*
domain/persona/*
data/persona/*
```

职责：

- 加载 persona YAML
- 构建人格运行时上下文
- 生成人格 prompt
- 做回复风格守护和归一化

### Vision 层

主要文件：

```text
aiagent/services/vision_service.py
aiagent/vision/image_store.py
aiagent/vision/character_registry.py
aiagent/vision/character_retriever.py
aiagent/graphs/vision_graph.py
apps/api/routes/vision.py
apps/api/routes/multimodal_chat.py
```

职责：

- 保存上传图片
- 加载角色图库
- 构建角色图像索引
- 调用视觉模型分析图片
- 将图片理解结果接入聊天流程

### RAG 层

主要文件：

```text
aiagent/knowledge/*
aiagent/graphs/rag_graph.py
apps/api/routes/knowledge.py
```

职责：

- 文档加载
- 索引构建
- BM25 和向量混合检索
- 简单 rerank
- 上下文格式化
- rebuild/status API

### Memory 层

主要文件：

```text
aiagent/memory/mem0_memory.py
aiagent/graphs/memory_graph.py
aiagent/services/memory_policy_llm_service.py
apps/api/routes/memory.py
```

职责：

- 长期记忆存储
- 记忆检索
- 记忆写入策略判断
- Qdrant 和可选图记忆适配

### Voice / Audio 层

主要文件：

```text
aiagent/perception/*
integrations/asr/*
integrations/audio/*
integrations/tts/*
aiagent/expression/tts_dispatcher.py
aiagent/expression/audio_playback_dispatcher.py
apps/api/routes/voice.py
apps/api/routes/audio.py
```

职责：

- 麦克风录音
- VAD
- ASR
- TTS
- 音频播放
- 语音会话控制

### Live2D 层

主要文件：

```text
aiagent/live2d/*
aiagent/expression/live2d_payload_dispatcher.py
aiagent/expression/mock_live2d_dispatcher.py
integrations/live2d/*
apps/api/routes/live2d.py
apps/desktop_qt/live2d_view_panel.py
```

职责：

- Live2D profile 加载
- 表情、动作、场景映射
- payload 构建
- payload 文件输出
- Python Live2D runtime 检查
- 模型扫描与 profile 生成
- Qt Live2D 面板

### Qt 前端

主要文件：

```text
apps/desktop_qt/chat_window.py
apps/desktop_qt/api_client.py
apps/desktop_qt/live2d_view_panel.py
apps/desktop_qt/main.py
```

职责：

- 文本聊天
- 图片上传
- 语音录制
- 知识库调试
- 记忆调试
- Live2D 调试
- 运行时诊断

新增 Qt 功能应优先作为 panel/widget 接入 `ChatWindow`，不要另起一套主窗口。

## 阶段状态

### 第一阶段：核心对话能力

已完成：

- Runtime 基础装配
- 主聊天接口
- Persona 基础
- RAG 基础
- Memory 基础
- Qt 基础调试前端

### 第二阶段：视觉与多模态

已完成：

- 图片上传
- 视觉分析
- 角色图库识别
- VisionGraph
- 多模态聊天接口
- Qt 图片上传

### 第三阶段：Live2D

已完成：

- Live2D payload builder
- 表情、动作、场景映射
- Live2D API
- Python runtime 检查
- 模型扫描
- profile 生成
- Qt Live2D 面板

当前真实 Live2D 模型资源仍需补充：

```text
data/live2d/characters/yzl/model/yzl.model3.json
```

### 第四阶段：稳定化与工程收敛

已完成：

- `/runtime/diagnostics`
- `scripts/test_runtime_diagnostics.ps1`
- `scripts/test_all.ps1`
- `scripts/test_phase4_closure.ps1`
- `apps/api/response_utils.py`
- `apps/api/middleware.py`
- `apps/api/request_context.py`
- `docs/config-reference.md`
- `docs/api-observability.md`
- `docs/phase4-stabilization-closure.md`
- Qt “运行诊断”入口

第四阶段目标已经达成。

## 当前优先风险

1. 源码中仍有历史乱码，需要单独清理。
2. `__pycache__` 存在权限问题，影响 `compileall`。
3. 真实 Live2D 模型资源尚未放入。
4. 部分 route 仍可继续接入统一响应工具，例如 knowledge、memory、voice、live2d。
5. Graph 内部阶段耗时还没有细粒度统计。

## 第五阶段建议

第五阶段建议命名为：

```text
编码清理、真实资源接入与测试固化
```

建议顺序：

1. 编码清理
   - 修复 `config/defaults.py`
   - 修复 `config/settings.py`
   - 修复 `apps/api/routes/live2d.py`
   - 确认所有中文源码为 UTF-8

2. 真实资源接入
   - 放入真实 Live2D 模型
   - 修正 `profile.yaml`
   - 跑 Live2D runtime inspect/load

3. 测试固化
   - 把关键脚本纳入统一测试
   - 增加 Python unit tests
   - 覆盖 diagnostics、response_utils、Live2D payload、Vision mock path

4. Route 收敛
   - knowledge、memory、voice、live2d 继续接入 `response_utils`
   - 统一错误结构

5. Graph 细粒度可观测性
   - 给 state/planner/rag/memory/vision/llm 阶段记录耗时
   - 将关键耗时写入 metadata

6. Qt 体验整理
   - 右侧面板改 tabs
   - Runtime Snapshot、API Detail、Memory Status、Live2D Payload 分区更清晰
   - 显示最近 request_id 和 response time

## 后续开发原则

1. 新功能先查已有模块，避免重复写同类能力。
2. API route 保持薄封装。
3. 业务流程优先放 runtime 或 graph。
4. 外部服务适配放 integrations。
5. 领域映射放 aiagent 对应模块。
6. Qt 新功能优先接入现有主窗口。
7. 新增接口必须有测试脚本或单元测试。
8. 新增配置必须同步更新 `docs/config-reference.md`。
9. 新增可观测性约定必须同步更新 `docs/api-observability.md`。
