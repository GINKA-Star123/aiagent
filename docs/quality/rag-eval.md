# RAG 质量评测

本文档说明 AIAgent V1.1 阶段 RAG 检索质量评测的目标、入口、指标、报告结构和失败处理方式。

RAG 评测只验证“检索是否能稳定召回正确知识”，不直接评测最终 LLM 回复文案。LLM 回复质量需要另行通过 persona 回归、回答事实性检查和人工验收评估。

## 评测目标

RAG 质量评测用于回答以下问题：

- 用户问题能否召回正确知识文档。
- 正确文档是否出现在足够靠前的位置。
- 别名、简称、角色关系等中文查询是否能被正确扩展。
- 不相关或禁止来源是否被错误召回。
- 文档、chunk、query normalizer、reranker 改动后，检索质量是否退化。

当前 baseline 默认使用 BM25-only 评测管线，目的是让质量基线不依赖 embedding 模型、FAISS 缓存或外部网络。真实 hybrid/vector/reranker 质量可以在后续阶段增加独立 baseline。

## 当前可用入口

当前仓库已有 Python CLI，可以直接运行基础 RAG baseline。

```powershell
cd F:\aiagent
.\.venv\Scripts\python.exe -m aiagent.knowledge.rag_eval `
  --cases tests\fixtures\rag_eval\cases.jsonl `
  --knowledge-dir data\knowledge\public `
  --show-results
```

如果只需要在测试体系中运行现有 baseline：

```powershell
cd F:\aiagent
.\.venv\Scripts\python.exe -m pytest -q tests\rag -p no:cacheprovider
```

`tests\rag` 依赖 `data\knowledge\public`。如果该目录不存在，当前测试会按条件跳过；这只表示本地没有知识库样本，不表示生产 RAG 质量已经通过。

## 推荐脚本入口

V1.1 报告化优化完成后，建议提供以下脚本入口：

```powershell
cd F:\aiagent
powershell -ExecutionPolicy Bypass -File scripts\test_rag_quality_report.ps1
```

发布前阻塞式检查建议使用：

```powershell
cd F:\aiagent
powershell -ExecutionPolicy Bypass -File scripts\test_rag_quality_report.ps1 -Required
```

脚本建议行为：

- 检查 `tests\fixtures\rag_eval\cases.jsonl` 是否存在。
- 检查 `data\knowledge\public` 是否存在。
- 默认知识库不存在时跳过。
- 使用 `-Required` 时，知识库不存在直接失败。
- 执行 `python -m aiagent.knowledge.rag_eval`。
- 输出 JSON、Markdown 和 failures JSONL 报告。

## 默认输入

评测集：

```text
tests/fixtures/rag_eval/cases.jsonl
```

知识库目录：

```text
data/knowledge/public
```

临时索引和报告建议输出到：

```text
data/cache/knowledge/
```

该目录属于运行缓存，不应作为源码提交。

## 推荐报告输出

V1.1 报告化后，默认报告目录建议为：

```text
data/cache/knowledge/reports
```

推荐输出文件：

```text
rag_eval_report.json
rag_eval_report.md
rag_eval_failures.jsonl
```

各文件用途：

| 文件 | 用途 |
| --- | --- |
| `rag_eval_report.json` | 机器可读完整报告，适合 CI、回归比对和后续 dashboard |
| `rag_eval_report.md` | 人工可读报告，适合发布前检查和问题复盘 |
| `rag_eval_failures.jsonl` | 只包含失败样例，适合定位 query、文档和 chunk 问题 |

## 指标说明

| 指标 | 含义 | 越高越好 |
| --- | --- | --- |
| `pass_rate` | 通过 case 数 / 总 case 数 | 是 |
| `recall_at_1` | 正确结果出现在第 1 位的比例 | 是 |
| `recall_at_3` | 正确结果出现在前 3 位的比例 | 是 |
| `mrr` | Mean Reciprocal Rank，正确结果排名倒数的平均值 | 是 |
| `avg_best_rank` | 通过样例中最佳命中的平均排名 | 否，越低越好 |

默认阈值建议：

| 指标 | 阈值 |
| --- | ---: |
| `pass_rate` | `0.75` |
| `recall_at_1` | `0.40` |
| `recall_at_3` | `0.80` |
| `mrr` | `0.55` |

阈值含义：

- `pass_rate` 低，说明整体可用性不足。
- `recall_at_1` 低，说明首位命中不稳定，最终回答容易引用次优内容。
- `recall_at_3` 低，说明检索候选池本身质量不足。
- `mrr` 低，说明正确结果经常排得很靠后。

## Case 格式

每一行是一个 JSON object。

```json
{
  "case_id": "yzl_identity",
  "category": "character",
  "query": "乐正绫是谁",
  "expected_source_paths": ["YueZhengling.md"],
  "expected_titles": [],
  "expected_terms": ["乐正绫"],
  "forbidden_source_paths": [],
  "top_k": 4,
  "max_rank": 3,
  "tags": ["profile"],
  "difficulty": "easy",
  "note": "角色身份基础召回"
}
```

字段说明：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `case_id` | 是 | 评测样例唯一 ID |
| `category` | 否 | 分组，例如 `character`、`workflow`、`song`、`negative` |
| `query` | 是 | 用户查询 |
| `expected_source_paths` | 否 | 期望召回的来源文件 |
| `expected_titles` | 否 | 期望召回的标题片段 |
| `expected_terms` | 否 | 期望命中的关键词 |
| `forbidden_source_paths` | 否 | 禁止命中的来源文件 |
| `top_k` | 否 | 检索返回数量 |
| `max_rank` | 否 | 正确命中允许出现的最晚排名 |
| `tags` | 否 | 标签，例如 `alias`、`profile`、`relation`、`negative` |
| `difficulty` | 否 | 难度，例如 `easy`、`normal`、`hard` |
| `note` | 否 | 备注 |

## 通过规则

一个 case 通过需要满足：

- 没有命中 `forbidden_source_paths`。
- top hits 中存在期望来源、期望标题或期望关键词。
- 最佳命中排名不晚于 `max_rank`。
- 如果配置了 `expected_terms`，命中的内容中至少出现一个期望关键词。

通过匹配优先级：

1. 来源路径匹配 `expected_source_paths`。
2. 标题匹配 `expected_titles`。
3. 内容或 preview 匹配 `expected_terms`。

## 失败原因

| reason | 含义 | 常见处理 |
| --- | --- | --- |
| `no_expected_hit` | top_k 内没有命中期望来源、标题或关键词 | 检查 query normalizer、文档内容、chunk 切分 |
| `expected_hit_rank_too_low` | 命中了正确内容，但排名超过 `max_rank` | 检查 reranker、BM25 token、向量召回权重 |
| `expected_source_matched_but_terms_missing` | 来源命中，但期望关键词缺失 | 检查文档是否缺少关键事实或 chunk 是否切散 |
| `forbidden_source_matched` | 命中了禁止来源 | 增加负样本，优化别名和消歧策略 |

## Category 建议

建议至少维护以下 category：

| category | 说明 |
| --- | --- |
| `character` | 角色身份、设定、关系、别名 |
| `song` | 歌曲、专辑、代表作 |
| `workflow` | 直播、producer、互动流程等知识 |
| `persona` | 当前角色人格相关知识 |
| `negative` | 不应命中特定来源的负样本 |
| `mixed` | 多跳或跨文档问题 |

分组指标用于判断退化集中在哪里。例如整体 pass rate 看似正常，但 `character` 分组下降，说明角色设定检索已经变差。

## Tags 建议

建议使用轻量标签辅助后续分析：

| tag | 说明 |
| --- | --- |
| `alias` | 别名、简称、昵称 |
| `profile` | 基础资料 |
| `relation` | 角色关系 |
| `fact` | 单事实问答 |
| `multi-hop` | 多跳或跨文档问题 |
| `negative` | 负样本 |
| `freshness` | 对更新时间敏感 |

当前 baseline 可以只按 `category` 汇总；后续报告可继续扩展 tag 汇总。

## Query Normalizer 检查点

当前 RAG query normalizer 应重点覆盖：

- 乐正绫：`阿绫`、`阿綾`
- 洛天依：`天依`
- 乐正龙牙：`龙牙`、`龍牙`
- 徵羽摩柯：`摩柯`
- 墨清弦：`墨姐`、`清弦`
- 言和：避免错误扩展为无关词

新增别名时，应同步新增或更新 `tests/fixtures/rag_eval/cases.jsonl` 中的 alias case。

## 低置信策略

RAG 低置信时不应强行把知识注入 prompt。

建议规则：

- 无候选：`should_inject=false`。
- 只有低分候选：`should_inject=false`。
- 命中 forbidden source：评测失败。
- BM25 和 vector 同时强命中：高置信。
- BM25-only 强命中：中置信，可作为 baseline 允许注入。

接口和 metadata 中建议保留：

```json
{
  "should_inject": false,
  "confidence": {
    "status": "low_relevance",
    "level": "low",
    "reason": "no_reliable_candidate"
  },
  "citations": []
}
```

## Citations 要求

当 RAG 内容被注入 prompt 时，应生成稳定 citations。

推荐字段：

```json
{
  "citation_id": "rag-1",
  "rank": 1,
  "chunk_id": "chunk-id",
  "doc_id": "doc-id",
  "title": "乐正绫",
  "source_path": "YueZhengling.md",
  "source_name": "YueZhengling.md",
  "score": 0.12,
  "retrieval_sources": ["bm25", "vector"],
  "preview": "短摘要"
}
```

注意事项：

- 不暴露本机绝对路径。
- 不返回过长 chunk 原文给客户端展示。
- 低置信、不注入 prompt 的结果不应生成正式 citations。

## 失败处理流程

当 RAG 评测失败时，建议按顺序排查：

1. 查看 `rag_eval_failures.jsonl` 或 `--show-results` 输出。
2. 判断失败集中在哪个 `category`。
3. 如果是 alias 问题，优先检查 `query_normalizer.py`。
4. 如果正确文档没有进入 top_k，检查文档是否被加载、chunk 是否过短或过散。
5. 如果正确文档进入但排名靠后，检查 reranker 规则。
6. 如果命中 forbidden source，增加负样本并检查别名消歧。
7. 修改后重新运行 RAG baseline。

## 发布要求

涉及以下改动时，必须执行 RAG 评测：

- 修改 `aiagent/knowledge/query_normalizer.py`
- 修改 `aiagent/knowledge/retriever.py`
- 修改 `aiagent/knowledge/reranker.py`
- 修改 `aiagent/knowledge/rag_pipeline.py`
- 修改知识库文档或 chunk 策略
- 替换 embedding 模型或 embedding 维度
- 调整 RAG 注入阈值或低置信策略

推荐发布前命令：

```powershell
cd F:\aiagent
.\.venv\Scripts\python.exe -m pytest -q tests\rag -p no:cacheprovider
```

如果已补齐报告化脚本，则使用：

```powershell
cd F:\aiagent
powershell -ExecutionPolicy Bypass -File scripts\test_rag_quality_report.ps1 -Required
```

如果目标发布暂不承诺真实 RAG 质量，需要在 release checklist 中明确说明：

- RAG baseline 是否跳过。
- 跳过原因。
- 当前是否只承诺 mock 主链路。
- 后续补测时间点。

## 本批次扩容建议

这一轮建议只扩稳定样本，不改阈值：

- alias / identity：`墨姐 -> 墨清弦`、`摩柯 -> 徵羽摩柯`、`ZERO`、`星尘`、`永夜Minus`
- relation / mixed：`墨清弦 + 苍穹`、`海伊 + 诗岸`
- 报告观察：继续优先看 `character`、`mixed` 两类的命中位置
- 负样本：等这一轮稳定后再补，避免过早把 chunk 切分噪音放大成阈值波动

如果某一类开始下滑，先看：
1. `query_normalizer.py`
2. 文档 chunk 切分
3. `reranker.py`