# V1.0 Release Checklist

本清单用于 V1.0 发布前最终确认。每一项都应在目标发布环境中勾选；未完成项需要明确记录为阻塞、延期或有意降级。

## 配置与密钥

- [ ] `.env.example` 已覆盖本地开发所需配置，默认 mock provider 可以跑通主链路。
- [ ] `cloud.tencent.example.env` 已覆盖腾讯云部署所需配置，不包含源码未读取的历史字段。
- [ ] 真实 `.env` 未提交，且不包含测试用 secret。
- [ ] 真实 `cloud.tencent.env` 未提交，且只存在于部署机器或受控密钥系统。
- [ ] `CLOUD_ADMIN_TOKEN` 已替换为强随机值，不使用 `change-*`、`your-*`、空值或公开示例值。
- [ ] 管理接口客户端统一使用 `x-cloud-admin-token` header。
- [ ] `POSTGRES_PASSWORD`、`NEO4J_PASSWORD`、S3/COS secret、`GPU_API_TOKEN`、`OPENAI_API_KEY`、`SILICONFLOW_API`、`ASR_API_KEY` 均已替换。
- [ ] 生产环境确认 `CLOUD_MODE=true`。
- [ ] 生产环境确认 `RATE_LIMIT_ENABLED=true`、`INFLIGHT_LIMIT_ENABLED=true`、`LIMITER_FAIL_OPEN=false`。
- [ ] 真实 provider 环境下未保留 mock-only 配置；如保留 mock provider，已记录为有意降级和可接受范围。
- [ ] `API_PUBLIC_BASE_URL` 与正式域名一致。
- [ ] `API_CORS_ORIGINS` 只包含允许访问的正式域名和必要调试源。

## 后端 API Contract

- [ ] 已执行 `tests\api`，所有 API contract tests 通过。
- [ ] `/health` 返回 `status=ok`，并包含 `cloud_mode`。
- [ ] `/ready` 返回 readiness checks，可用于容器 healthcheck 和负载均衡探测。
- [ ] `/runtime/diagnostics` 返回 `ok`、`status`、`checks`、`summary`。
- [ ] `/runtime/capabilities` 返回 capability `status`、`summary`、`items`。
- [ ] `/chat` 返回统一 ok response，`reply` 不为空。
- [ ] `/chat/multimodal` 在 mock 或真实 Vision provider 下返回统一响应结构。
- [ ] 统一错误结构包含 `ok=false`、`stage`、`error`、`request_id` 或等价追踪信息。

## Runtime 能力状态

- [ ] Runtime 初始化失败不会导致无解释的 500，诊断接口可以展示失败原因。
- [ ] LLM、TTS、ASR、Vision、RAG、Memory、Live2D 的 capability 状态可区分 `ready`、`degraded`、`unavailable`。
- [ ] mock provider 下 capability 不误报为生产 ready。
- [ ] 真实 provider 缺失 token、base url 或模型路径时，可以在 diagnostics 中定位原因。
- [ ] `/runtime/capabilities` 可被客户端用于功能开关或降级提示。

## Graph Metadata

- [ ] Graph 每个阶段都记录标准化 metadata。
- [ ] 阶段耗时字段使用统一单位，例如 `duration_ms`。
- [ ] 主链路 metadata 不泄漏 API key、token、文件系统敏感路径或用户隐私原文。
- [ ] metadata 中可定位 LLM、RAG、Memory、Vision、TTS、Live2D 等阶段是否启用和是否降级。
- [ ] Graph metadata 单元测试已覆盖成功、跳过、异常和降级场景。

## RAG Baseline

- [ ] `tests\fixtures\rag_eval\cases.jsonl` 已固定为 V1.0 基线评测集。
- [ ] `tests\rag` 在存在 `data/knowledge/public` 时可以运行并达到当前阈值。
- [ ] 知识库文档来源、版本和更新时间已记录。
- [ ] embedding 模型、embedding 维度、Qdrant collection 配置一致。
- [ ] embedding 模型或维度发生变化时，已重建对应 collection 或索引。
- [ ] 检索质量指标低于阈值时，不发布真实 RAG 能力。

## Memory Safety 与去重

- [ ] 长期记忆写入前经过敏感信息过滤。
- [ ] 记忆写入前经过去重或相似度合并策略。
- [ ] 高风险敏感内容不会进入长期记忆。
- [ ] mock memory 与真实 Mem0/Qdrant 模式的降级边界已明确。
- [ ] `MEMORY_RESET_VECTOR_STORE=false` 已在生产环境确认。
- [ ] Memory 相关单元测试覆盖 intake、dedup、safety 和 policy rules。

## Vision 低置信度策略

- [ ] Vision 输出 schema 已稳定，客户端可以按固定字段解析。
- [ ] 角色识别低于 `VISION_CHARACTER_CONFIDENT_SCORE` 时，不强行给出确定身份。
- [ ] 低置信度结果会进入降级表达或提示，而不是伪造高置信结论。
- [ ] 图片大小限制 `VISION_MAX_IMAGE_BYTES` 已符合部署环境容量。
- [ ] 真实 Vision provider 的 token、base url、model 已配置。
- [ ] Vision confidence policy 单元测试通过。

## Voice Realtime

- [ ] `/voice/realtime/start` 返回 `call_id`、`status=active`、`phase=idle`。
- [ ] `/voice/realtime/state/{call_id}` 返回 call 状态、`turn_count`、`last_seen_at`。
- [ ] `/voice/realtime/end` 返回 `status=ended`、`phase=completed`。
- [ ] 缺失或过期 `call_id` 返回统一错误结构。
- [ ] ASR mock、本地或 API provider 的配置与当前发布目标一致。
- [ ] 移动端实时语音开始、状态刷新、结束流程完成真机验收。

## Cloud Readiness / Admin / Task Queue

- [ ] `/cloud/ops/readiness` 必须携带 `x-cloud-admin-token` 才可访问。
- [ ] `/cloud/ops/config-snapshot` 不返回 secret 明文。
- [ ] `/cloud/tasks/summary` 可以返回当前队列摘要。
- [ ] `/cloud/tasks/knowledge/rebuild` 可以入队，且重复任务不会无限堆积。
- [ ] `/cloud/tasks/vision-characters/rebuild` 可以入队，且重复任务不会无限堆积。
- [ ] Redis 连接正常，`REDIS_PREFIX` 已按环境区分。
- [ ] worker 能读取 `TASK_QUEUE_NAME` 并消费默认队列。
- [ ] dead task 查询和 retry 行为已通过 contract tests。
- [ ] docker compose 中 api、worker、redis、qdrant、neo4j、postgres 状态正常。

## Live2D Payload

- [ ] 后端 Live2D payload schema 已通过 contract tests。
- [ ] `/live2d/preview` 返回移动端可消费 payload。
- [ ] `/session/open` 返回的 `live2d.expression` 与 `live2d.motion` 可被移动端使用。
- [ ] Chat、Voice、Vision 场景下 Live2D payload 字段不缺失关键结构。
- [ ] 正式 Live2D 模型交付后，已替换过渡资源并完成真机复测。
- [ ] `LIVE2D_PROVIDER=mock` 在 V1.0 后端只表示 payload 输出，不表示服务端负责模型渲染。

## Flutter 客户端

- [ ] `dart format lib test` 通过。
- [ ] `flutter analyze` 通过。
- [ ] `flutter test` 通过。
- [ ] `flutter build apk --release` 成功生成 release 包。
- [ ] Android 应用名、应用 ID、版本号符合当前 V1.0 发布要求。
- [ ] 设置页 API 地址指向正式域名或局域网后端，不使用手机自己的 `127.0.0.1`。
- [ ] Chat、Multimodal、Voice realtime、TTS 播放、Live2D 显示已完成真机手动验收。
- [ ] release keystore 已配置；debug signing fallback 只用于内测。

## 数据与资源

- [ ] `data/persona` 中正式 persona 已确认。
- [ ] `data/live2d/characters` 与 `data/live2d/backgrounds` 的发布资源已确认。
- [ ] `data/characters` 的视觉角色图库已确认。
- [ ] `data/knowledge/public` 的 RAG 知识库已确认。
- [ ] `data/models` 中本地模型路径与 `.env` 配置一致。
- [ ] `data/uploads`、`data/cache`、`data/logs` 不作为发布源码提交。
- [ ] 生产对象存储 provider 与 `S3_*` / COS 配置一致。

## 发布前冻结项

- [ ] 不再合入非 V1.0 阻塞修复。
- [ ] 不再修改 API response contract，除非同步更新 tests 和客户端解析。
- [ ] 不再变更 `.env.example`、`cloud.tencent.example.env` 字段名，除非同步更新 `docs/config-reference.md`。
- [ ] 不再变更 Live2D payload schema，除非同步更新移动端和 contract tests。
- [ ] 不再变更 RAG baseline 阈值，除非记录原因。
- [ ] 已确认 `docs\v1-final-smoke.md` 中最终 smoke 指令可覆盖发布前检查入口。

## Go / No-Go 标准

- [ ] Go：后端 unit、API contract、mock smoke 通过。
- [ ] Go：RAG baseline 在目标知识库存在时通过；如跳过，已明确该发布不承诺真实 RAG 质量。
- [ ] Go：`/health`、`/ready`、`/runtime/capabilities`、`/runtime/diagnostics` 在目标环境可访问。
- [ ] Go：管理接口必须有 token 保护，且 `x-cloud-admin-token` 验证通过。
- [ ] Go：Flutter analyze、test、release build 通过。
- [ ] Go：真机主链路验收通过。
- [ ] No-Go：真实 provider 仍使用 mock-only 配置且没有降级说明。
- [ ] No-Go：任一 secret 仍为 `change-*`、`your-*` 或空值。
- [ ] No-Go：API contract tests 失败。
- [ ] No-Go：云端 `/ready` 不可用。
- [ ] No-Go：移动端无法完成 Chat 或 Voice realtime 基础链路。

