# 下一阶段优化路线

本文档用于记录 AIAgent 下一阶段的主要优化方向。当前阶段不以继续堆叠新功能为核心，而以稳定主链路、统一协议、提升可观测性、固化测试和收敛工程边界为主要目标。

建议下一阶段命名为：

```text
V1.0 稳定化与协议收敛阶段
```

## 一、阶段判断

AIAgent 当前已经形成了较完整的 AI VTuber / Live2D 角色陪伴运行时，覆盖：

- FastAPI 后端 API
- Flutter 移动端主客户端
- Qt 桌面调试端
- Persona 人格系统
- LangGraph 对话主流程
- RAG 知识库
- Mem0 / Qdrant 长期记忆
- 视觉理解与角色图库识别
- ASR / TTS / 语音通话
- Live2D payload 与移动端舞台
- 云部署、限流、任务队列、对象存储与 worker

项目目前的主要问题不是缺少能力，而是已有能力之间的边界、协议、初始化方式、异常路径和测试覆盖还不够稳定。下一阶段应优先让现有系统变得更清晰、更可靠、更容易排查，而不是继续增加平行模块。

## 二、阶段总目标

下一阶段的目标可以概括为六句话：

1. 主聊天链路稳定可用。
2. Flutter 与后端协议稳定一致。
3. Runtime 初始化不再被可选重型依赖拖垮。
4. Graph 每个阶段可观测、可降级、可排错。
5. RAG、Memory、Vision、TTS、Live2D 等能力有明确质量基线。
6. 测试、文档、配置和部署形成可重复的交付流程。

## 三、基本开发原则

后续优化应遵守以下原则：

- API route 保持薄封装，不在 route 中堆业务流程。
- Runtime 和 Graph 承担主业务编排。
- 外部模型、数据库、音频、Live2D runtime 适配放在 `integrations/` 或 service 层。
- Persona、RAG、Memory、Vision、Live2D 等领域规则放在 `aiagent/` 对应模块。
- Flutter 是当前 V1.0 主交付端，Qt 是调试端。
- Mock 模式必须能跑通主链路，真实 provider 失败时要能降级。
- 新增或修改 API 字段时，同步更新客户端模型和文档。
- 新增核心行为时，至少补充单元测试、API contract test 或 smoke test。

## 四、P0：主链路稳定与协议收敛

P0 是下一阶段最优先的工作。目标是让后端主接口、移动端协议和运行时初始化稳定下来。

### 4.1 API 响应统一

当前 `/chat` 与 `/chat/multimodal` 已经较接近统一响应，但部分 route 仍在手写 JSON。后续应统一使用 `apps.api.response_utils`。

重点接口：

- `GET /health`
- `GET /ready`
- `GET /runtime/diagnostics`
- `POST /session/open`
- `POST /chat`
- `POST /chat/multimodal`
- `POST /voice/transcribe`
- `POST /voice/realtime/start`
- `POST /voice/realtime/turn`
- `POST /voice/realtime/end`
- `GET /memory/user/{user_id}`
- `DELETE /memory/user/{user_id}`
- `GET /live2d/stats`
- `POST /live2d/preview`

统一成功响应应包含：

```json
{
  "ok": true,
  "request_id": "..."
}
```

统一失败响应应包含：

```json
{
  "ok": false,
  "stage": "...",
  "error": "...",
  "request_id": "..."
}
```

聊天类响应字段应继续保持一致：

- `output_id`
- `reply`
- `base_reply_text`
- `emotion`
- `motion`
- `expression`
- `audio_path`
- `audio_url`
- `audio_segments`
- `audio_segment_urls`
- `audio_segment_texts`
- `live2d_command_path`
- `live2d`
- `metadata`
- `request_id`

验收标准：

- Flutter 端可以用同一套模型解析 `/chat`、`/chat/multimodal`、`/voice/realtime/turn` 的核心回复字段。
- 所有核心 API 错误都能在客户端显示 `stage`、`error`、`request_id`。
- 后端日志可以通过 `request_id` 追踪一次请求。

### 4.2 Runtime 初始化解耦

当前 runtime 装配会集中创建 LLM、RAG、Memory、Vision、ASR、TTS、Live2D 等组件。后续应减少冷启动失败面。

优化方向：

- 将重型依赖改为 lazy init。
- RAG embedding、Vision CLIP、Mem0/Qdrant、ASR 模型不应在普通文本聊天冷启动时全部强制加载。
- 每个能力模块暴露状态：`available`、`degraded`、`disabled`、`error`。
- 主聊天在 RAG、Memory、Vision、TTS、Live2D 不可用时仍可返回文本。
- Runtime 初始化错误按模块记录，不要全部折叠成 `runtime_init`。
- 给 runtime 单例增加并发冷启动保护，避免多请求同时初始化。

验收标准：

- Mock 配置下 API 冷启动可以稳定完成。
- 关闭或缺失 RAG / Vision / Live2D 资源时，文本聊天仍可返回。
- `/runtime/diagnostics` 能说明哪个模块不可用，以及建议动作。

### 4.3 主聊天 smoke 固化

下一阶段应优先建立 mock 模式下的主链路 smoke。

最低覆盖：

- runtime 能构建。
- `/health` 返回成功。
- `/ready` 返回合理状态。
- `/chat` 能返回统一字段。
- `/chat/multimodal` 在 mock vision 下能返回统一字段。
- `/session/open` 能返回 presence opening。
- TTS mock 不阻断聊天。
- Live2D mock / noop 不阻断聊天。

验收标准：

- 本地执行一条命令即可完成主链路 smoke。
- CI 或本地测试失败时能明确指出阶段。

## 五、P1：Graph 可观测性与流程优化

P1 的重点是让主图流程更可控。当前主图是线性流程，结构清晰，但耗时、失败、跳过和降级还需要更细粒度表达。

### 5.1 Graph 阶段耗时

建议为以下阶段记录耗时：

- `prepare_context_ms`
- `vision_graph_ms`
- `memory_retrieve_ms`
- `state_graph_ms`
- `planner_graph_ms`
- `rag_graph_ms`
- `llm_graph_ms`
- `memory_store_ms`
- `response_packet_ms`
- `tts_ms`
- `live2d_ms`

这些字段可进入 `metadata`，也可逐步进入结构化日志。

验收标准：

- 一次 `/chat` 响应能看到主要阶段状态。
- 一次慢请求可以判断慢在 LLM、RAG、Vision、TTS 还是其他阶段。

### 5.2 条件分支与降级

当前主图虽然可以跳过 Vision，但整体仍偏线性。后续应逐步使用更明确的条件分支。

优化方向：

- 文本轮次不进入视觉分析。
- Planner 明确不需要 RAG 时跳过 RAG。
- RAG 检索失败时返回空上下文并记录 `rag_error`。
- Memory 检索失败时返回 `无长期记忆。` 并记录 `memory_error`。
- Memory 写入失败不影响当前回复。
- TTS 失败不影响文字和 Live2D payload。
- Live2D dispatch 失败不影响文字和音频。

验收标准：

- 任一可选模块失败时，主聊天可以降级返回。
- 响应 metadata 中可以看到失败模块和原因。

### 5.3 会话与线程边界

当前短期 LLM 记忆主要按 `user_id` 作为 thread id。后续需要明确以下概念：

- `user_id`：用户身份。
- `session_id`：一次会话。
- `turn_id`：一次输入输出回合。
- `request_id`：一次 HTTP 请求。
- `output_id`：一次输出事件。

优化方向：

- 避免所有上下文都只挂在 `user_id` 上。
- 移动端 session open 与聊天 session 关系应明确。
- 语音通话 call id 与普通聊天上下文关系应明确。

验收标准：

- 同一用户不同 session 的短期上下文策略明确。
- 长期记忆和短期对话不会混用身份字段。

## 六、P1：智能体质量优化

这一部分目标是提升角色回复质量、知识准确性、记忆可靠性和多模态可信度。

### 6.1 Persona 质量

当前默认 persona 是乐正绫，风格配置已经较完整。后续应从 prompt 配置升级为可测试行为。

优化方向：

- 建立 persona 回归测试集。
- 覆盖问候、闲聊、情绪安慰、角色设定、知识问答、多模态图片、拒绝暴露 AI 身份等场景。
- 检查回复是否过长、是否像客服、是否机械复述、是否暴露系统身份。
- Persona 的文本风格、TTS 声音、Live2D 动作应保持一致。
- Mock 回复不应只是简单回显用户输入，可逐步变成角色化 fallback。

验收标准：

- 典型输入下能保持乐正绫口吻。
- 不使用 emoji。
- 不自称 AI。
- 回复不过度长篇说明。

### 6.2 RAG 知识库质量

当前知识库主要围绕 VSinger / 虚拟歌手资料和直播基础知识。下一阶段应建立检索质量基线。

优化方向：

- 为乐正绫、洛天依、言和、VSinger、歌曲、设定、应援词建立问答评测集。
- 给文档增加 metadata：角色、主题、来源、更新时间、可信等级。
- 优化中文别名，例如阿绫、天依、龙牙、墨姐、清弦等。
- 根据文档类型调整 chunk 策略。
- 索引重建默认异步化。
- 文档变化后标记索引过期。
- embedding 维度变化时提供重建提示。

验收标准：

- 常见角色设定问题能召回正确文档。
- RAG 低相关时不会强行注入。
- 回复不会编造知识库没有的内容。

### 6.3 长期记忆质量

长期记忆是陪伴型 Agent 的核心，但必须少而准。

优化方向：

- 明确记忆类型：用户偏好、身份信息、关系进展、长期目标、边界、最近话题。
- 写入前去重。
- 写入前做敏感内容过滤。
- 写入记录保存 category、importance、reason、source、created_at。
- 记忆检索进入 prompt 前做压缩。
- 记忆写入异步化，失败不影响当前回复。
- 用户可以查看、搜索、清空自己的长期记忆。
- 当前返回空的 profile memory 能力要么实现，要么明确标记为未启用。

验收标准：

- 不该记的内容不写入。
- 已记过的偏好不重复写。
- 用户可以清空长期记忆。
- 记忆不可用时聊天仍可继续。

### 6.4 视觉可信度

视觉链路已经覆盖图片保存、角色图库检索、视觉模型分析、上下文注入和 Live2D 建议。下一步要避免误识别和乱推断。

优化方向：

- 严格校验视觉模型输出 schema。
- 区分角色候选和最终确认。
- 角色识别低置信度时使用保守表达。
- 不把所有图片都强行解释成角色图。
- 图片类型分类保持清晰：character、daily、food、travel、screenshot、document、object 等。
- OCR、场景描述、角色识别分开处理。
- 上传图片限制大小、格式和异常文件。
- 视觉结果进入长期记忆前必须经过策略判断。

验收标准：

- 角色图能识别候选。
- 日常图片能自然描述。
- 低置信度不强行确认角色身份。
- 不推断真实人物身份。

## 七、P1：语音与 Live2D 体验优化

语音和 Live2D 是角色陪伴感的关键表达层。

### 7.1 语音链路

优化方向：

- ASR、LLM、TTS 分别记录耗时。
- 语音通话状态明确：连接中、聆听中、识别中、思考中、播放中、错误。
- 支持用户说话时打断当前播放。
- 空转写不触发无意义回复。
- TTS 分段策略稳定，避免空段和过长段。
- 音频 URL 生成规则统一，Flutter 可直接播放。
- 云部署时 realtime call 状态从内存迁移到 Redis 或其他共享存储。

验收标准：

- 语音通话能稳定 start、turn、end。
- TTS 失败不影响文字回复。
- 播放和后端 speaking state 不明显错位。

### 7.2 Live2D 链路

当前后端 Live2D profile 和背景存在，但真实 `model3.json` 资源尚未完整放入。Flutter 端有内置过渡 Live2D WebView 资源。

优化方向：

- 补齐正式 Live2D 模型资源。
- 统一 emotion、expression、motion、background 的映射。
- Live2D payload 增加 schema version。
- 后端只负责 payload 时，移动端负责模型加载和动作执行。
- `/live2d/preview`、`/live2d/stats`、`/live2d/runtime/*` 继续作为调试工具。
- 客户端要能处理未知表情、未知动作和缺失字段。
- Presence 开场、聊天回复、视觉建议使用同一套 Live2D 语义。

验收标准：

- 模型能加载。
- idle、说话、表情切换、动作播放、背景切换都可验证。
- Live2D payload 缺字段不会导致客户端崩溃。

## 八、P1：Flutter 主客户端优化

Flutter 是当前 V1.0 RC 主交付端，应优先保证协议一致、错误友好和状态清晰。

优化方向：

- 拆分过大的 `app/app.dart`。
- API model 与后端字段保持一一对应。
- 网络错误展示 `stage`、`error`、`request_id`。
- 设置页加强 API 地址校验，提醒真机不要使用 `127.0.0.1`。
- 聊天历史保存文本、图片、音频、metadata、memory status。
- Live2D payload 使用统一解析模型。
- 语音通话页明确状态流转。
- Release 构建检查签名配置。
- 增加 Flutter model tests。

验收标准：

- 后端错误不会导致 App 崩溃。
- 用户可以理解当前是网络问题、后端问题还是模型问题。
- Live2D、音频、聊天消息状态保持一致。

## 九、P2：云部署与运维优化

云侧已经具备限流、任务队列、对象存储、GPU client、worker 等基础设施。下一阶段应继续提升可恢复性和可排障性。

优化方向：

- 明确 `/ready` 与 `/cloud/ops/readiness` 的不同用途。
- admin API 必须强认证。
- Redis 不可用时按接口决定 fail-open 或 fail-closed。
- 任务队列记录耗时、重试次数、最后错误、dead-letter 原因。
- worker 处理任务时记录 task_id、worker_id、耗时和结果。
- realtime call 状态不要依赖单进程内存。
- 对象存储统一 local / s3 / cos 命名和行为。
- GPU 熔断状态进入 diagnostics。
- 生产日志支持 request_id 检索。

验收标准：

- 云环境可以通过 readiness 判断是否可接流量。
- 重建任务失败后可查看、重试、进入 dead-letter。
- 管理接口不会暴露敏感配置。

## 十、P2：测试体系建设

当前测试数量较少，下一阶段应先补主协议和主链路测试，而不是追求覆盖率数字。

建议测试分层：

### 10.1 Unit Tests

- schema 兼容。
- Persona guard。
- RAG alias 扩展。
- Memory policy。
- Live2D payload builder。
- response_utils。

### 10.2 API Contract Tests

- `/health`
- `/ready`
- `/chat`
- `/chat/multimodal`
- `/session/open`
- `/voice/realtime/start`
- `/voice/realtime/turn`
- `/voice/realtime/end`
- `/memory/user/{user_id}`
- `/live2d/preview`

### 10.3 Runtime Smoke Tests

- mock runtime 构建。
- mock 文本聊天。
- mock 多模态聊天。
- TTS mock。
- Live2D noop。
- RAG 不可用降级。
- Memory 不可用降级。

### 10.4 Client Tests

- Flutter API model parsing。
- degraded response parsing。
- Live2D payload parsing。
- settings 保存和读取。
- chat history 保存和读取。

验收标准：

- 本地一条命令可以跑完后端主链路测试。
- Flutter 一条命令可以跑完客户端 model 和基础 widget 测试。
- 测试失败能定位到 API、Runtime、Graph、Provider 或 Client。

## 十一、配置与文档同步

配置项较多，后续必须防止源码、`.env.example` 和文档不一致。

优化方向：

- `docs/config-reference.md` 与 `config/settings.py` 同步。
- `.env.example` 覆盖源码实际支持的配置项。
- 补充 ASR API provider 配置说明。
- 补充云模式配置组合。
- 补充 mock、本地文本、多模态、本地语音、Live2D 调试、云部署等配置模板。
- 过期文档内容及时清理或标注。
- 新增 API 字段时同步更新 API 协议文档。
- 新增可观测性字段时同步更新观测性文档。

验收标准：

- 新人可以只读 README 和 docs 完成本地 mock 启动。
- 配置项在文档中能找到用途、默认值和影响范围。

## 十二、仓库治理与清理

当前工作区存在一些历史状态和本地资产目录，需要明确治理方式。

优化方向：

- 决定 Flutter 是否继续作为内嵌独立仓库，或正式纳入 monorepo。
- 决定 Qt 调试端是否纳入版本管理。
- 清理 `pyproject.toml` 中不存在的历史包路径。
- 处理 `stage.md` 当前删除状态。
- 清理或修复 `.pytest_cache` 权限问题。
- 明确 `data/` 下哪些是示例资产，哪些是本地私有数据。
- 大模型、缓存、音频生成物、上传文件保持不入仓。
- 建立格式化和 lint 约定。

验收标准：

- `git status` 不再混杂无解释的历史状态。
- 文档能解释哪些目录被忽略但仍是运行资产。
- 开发者不会误把缓存、模型、密钥或用户数据提交。

## 十三、安全与隐私

AIAgent 会处理文本、图片、音频和长期记忆，安全与隐私需要前置。

优化方向：

- 日志不输出 API key、Authorization、完整图片 base64。
- prompt 如需记录，只记录摘要、长度或 hash。
- 上传文件限制大小、类型和路径。
- 用户长期记忆支持查看、删除、清空。
- 敏感个人信息不自动写入长期记忆。
- admin API 强认证。
- 生产环境 CORS 不使用宽松默认值。
- 云配置快照不暴露 secret。
- 视觉不推断真实人物身份。
- 高风险请求同时做系统级拒绝和角色内温和拒绝。

验收标准：

- 日志可排障但不泄露密钥和隐私。
- 用户可以控制自己的长期记忆。
- 管理接口不会被普通客户端调用。

## 十四、建议执行顺序

建议按以下顺序推进：

1. API 响应统一。
2. Runtime 初始化解耦。
3. Mock 主链路 smoke。
4. Graph 阶段耗时与 metadata。
5. Flutter API model 对齐。
6. Live2D 真实资源状态确认。
7. RAG 评测集与检索质量。
8. Memory 策略、去重和删除能力。
9. Vision schema 与低置信度策略。
10. 语音通话状态与打断。
11. 云 readiness、任务队列和 admin 安全。
12. 文档、配置、仓库治理收尾。

## 十五、暂不建议优先做的事项

下一阶段暂不建议优先投入：

- 新增第二套 Web 控制台。
- 新增平行 Live2D dispatcher。
- 新增第二套 RAG 或 Memory 实现。
- 直接上复杂多 Agent 架构。
- 在协议未稳定前做大规模 UI 改版。
- 在测试未固化前继续增加大量 provider。
- 在真实模型资源未交付前深度优化后端 Live2D runtime。

这些事项并非不重要，而是当前投入产出比不如主链路稳定化。

## 十六、阶段完成标准

当以下条件满足时，可以认为本阶段基本完成：

- Mock 模式下后端主链路稳定通过测试。
- Flutter 可以稳定调用 `/session/open`、`/chat`、`/chat/multimodal`、`/voice/realtime/*`。
- 核心 API 响应字段统一，错误响应都带 `stage` 和 `request_id`。
- Runtime 可以在部分外部能力不可用时降级。
- Graph metadata 能显示主要阶段状态和耗时。
- RAG、Memory、Vision 至少各有一组质量回归样例。
- Live2D payload schema 稳定，客户端能容错。
- 配置文档和 `.env.example` 与源码一致。
- 云 readiness、任务队列和 admin 接口有清晰安全边界。
- 项目文档能指导新人完成本地 mock 启动、后端 smoke 和 Flutter 调试。

完成这一阶段后，项目才适合继续进入更高质量的真实模型联调、正式 Live2D 资源接入、移动端正式发布和云端长期运行优化。
