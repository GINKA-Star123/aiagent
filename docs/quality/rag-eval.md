# RAG 全链路质量评测

本文档说明 AIAgent V2 RAG 评测体系的目标、阶段、数据规范、指标、执行入口和失败处理方式。

旧版只测“文档是否召回”的 32 条 baseline 已废弃；旧的 aiagent/knowledge/rag_eval*.py、tests/rag/test_rag_quality_baseline.py 和旧 cases 已删除。
当前唯一实现是 aiagent/knowledge/evaluation/，数据集在 tests/fixtures/rag_eval/。

## 一、评测范围

本体系覆盖一条完整离线链路：

1. 文档加载与 chunk 切分
2. 索引构建与 metadata 完整性
3. BM25 粗召回 retrieval
4. SimpleReranker 重排 rerank
5. 置信度与注入决策 injection
6. 最终 prompt context、citations 与长度约束 prompt

不包含：

- 最终 LLM 回复文案质量
- groundedness / faithfulness 的 LLM judge
- 真实 embedding / FAISS / hybrid 检索质量
- 多轮改写与指代消解

这些需要单独的答案级或在线评测。

## 二、为什么替换旧体系

旧体系只有 retrieval 一段，且用例绑定旧英文文件名，知识库换成中文文档后整体失真。新体系解决三个问题：

1. 每段独立判定：chunk/index 失败不会被误判成 reranker 问题。
2. 注入决策可测：低相关、负例、citation 来源、prompt 长度都能单独失败。
3. 用例与语料版本绑定：manifest 记录 256 个文件的 sha256，换语料不会拿旧分数比较。

## 三、代码结构

| 路径 | 作用 |
| --- | --- |
| aiagent/knowledge/evaluation/models.py | 用例、阶段结果、报告模型 |
| aiagent/knowledge/evaluation/dataset.py | JSONL 加载、路径/术语校验、语料指纹 |
| aiagent/knowledge/evaluation/pipeline.py | BM25-only 评测管线（NullVectorStore） |
| aiagent/knowledge/evaluation/runner.py | chunk/index/retrieval/rerank/injection/prompt 判定 |
| aiagent/knowledge/evaluation/report.py | JSON / Markdown / failures 报告 |
| aiagent/knowledge/evaluation/cli.py | 命令行入口 |
| tests/fixtures/rag_eval/cases.jsonl | 120 条查询级用例（smoke 30 / core 54 / hard 36） |
| tests/fixtures/rag_eval/chunk_cases.jsonl | 12 条 chunk 级用例 |
| tests/fixtures/rag_eval/manifest.json | 版本、语料指纹、规模 |
| tests/rag/test_rag_eval_*.py | pytest 契约测试 |

## 四、数据规范

查询用例字段：

- case_id：全集唯一
- suite：smoke / core / hard
- category：character / setting / song / fan_chant / group / relation / mixed / negative
- query：用户原始问法
- difficulty：easy / normal / hard
- tags：诊断标签
- stages：本用例要跑的阶段
- retrieval：expected / required / forbidden 文档、内容词、top_k、max_rank
- rerank：expected top1、expected sections、min_section_hits
- injection：should_inject、allowed_levels、allowed_statuses、citation 范围与来源
- prompt：must_contain、must_not_contain、required_terms、max_chars、expect_empty
- note：备注

chunk 用例字段：

- source_path：被检查文档
- expected_character / expected_doc_kind
- required_metadata：必须存在的 metadata 键
- required_alias / required_search_alias
- required_section：至少一个 chunk 包含的 section 标题
- must_keep_together：每组词必须落在同一个 chunk
- min_chunks / max_chunks
- min_chunk_chars / max_chunk_chars
- forbidden_terms

详细字段说明见 tests/fixtures/rag_eval/README.md。

## 五、判定语义

retrieval：

1. forbidden_source_paths 任意命中最终 top-k 即失败。
2. required_source_paths 必须全部出现在粗召回候选集。
3. expected_source_paths 必须出现在粗召回候选集。
4. max_rank 留给 rerank 判定，retrieval 只记录 coarse_best_rank。

rerank：

1. 若配置 expected_top1_source_paths，最终第 1 位必须命中其中之一。
2. 若配置 expected_sections，top-k 中至少 min_section_hits 个 chunk 包含 section。
3. expected_content_terms 必须全部出现在 top-k 内容里。
4. 最终 rank 仍不得超过 max_rank。
5. forbidden_source_paths 在最终 top-k 再检查一次。

injection：

1. should_inject 必须匹配。
2. confidence.level 必须在 allowed_levels。
3. confidence.status 必须在 allowed_statuses。
4. citation 数量在 min/max 之间。
5. required_citation_sources 必须出现，forbidden_citation_sources 不能出现。

prompt：

1. expect_empty=true 时，上下文必须是“无相关知识”。
2. 否则检查 must_contain、must_not_contain、required_terms、forbidden_terms、max_chars。

end_to_end：

本用例声明的所有 stage 全部通过。

## 六、指标

| 指标 | 含义 |
| --- | --- |
| pass_rate | end_to_end 通过率 |
| retrieval_recall | 正例中正确文档进入粗召回候选集的比例 |
| retrieval_mrr | 正例中正确文档在粗召回里的排名倒数均值 |
| rerank_recall | 正例中正确文档进入最终 top-k 的比例 |
| rerank_mrr | 正例中正确文档最终排名的倒数均值 |
| rerank_top1_accuracy | 配置 top1 期望的正例中，top1 命中比例 |
| injection_accuracy | injection stage 通过率 |
| prompt_pass_rate | prompt stage 通过率 |
| chunk_pass_rate | chunk_global + chunk 用例通过率 |
| index_audit | 索引结构契约 |

## 七、执行流程

所有命令在 F:\aiagent 下执行。

### 1. 记录基线

脚本默认阈值 -1（不启用），先记录：

    powershell -ExecutionPolicy Bypass -File scripts/test_rag_quality_report.ps1 -Suite smoke -ReportPrefix rag_eval_smoke

然后：

    powershell -ExecutionPolicy Bypass -File scripts/test_rag_quality_report.ps1 -Suite core -ReportPrefix rag_eval_core
    powershell -ExecutionPolicy Bypass -File scripts/test_rag_quality_report.ps1 -Suite hard -ReportPrefix rag_eval_hard
    powershell -ExecutionPolicy Bypass -File scripts/test_rag_quality_report.ps1 -Suite all -ReportPrefix rag_eval_all

报告目录：

    data/cache/knowledge/reports/rag_eval_v2/

每套三个文件：

    rag_eval_smoke_report.json
    rag_eval_smoke_report.md
    rag_eval_smoke_failures.jsonl

### 2. 检查报告

    Get-Content data/cache/knowledge/reports/rag_eval_v2/rag_eval_smoke_report.md -Encoding UTF8

失败样例：

    Get-Content data/cache/knowledge/reports/rag_eval_v2/rag_eval_smoke_failures.jsonl -Encoding UTF8 | ForEach-Object { $_ | ConvertFrom-Json } | Select-Object kind, case_id, error | Format-Table -AutoSize

### 3. 设置门禁

第一次基线后，阈值先取“基线 - 0.02”，防止退化；确认提升后再抬。示例：

    powershell -ExecutionPolicy Bypass -File scripts/test_rag_quality_report.ps1 -Suite smoke -ReportPrefix rag_eval_smoke -MinPassRate 0.50 -MinRetrievalRecall 0.60 -MinRerankRecall 0.55 -MinRerankTop1 0.35 -MinInjectionAccuracy 0.60 -MinPromptPassRate 0.55 -MinChunkPassRate 0.90

阈值模板：

    tests/fixtures/rag_eval/thresholds.example.json

模板是目标值，不是当前基线。

### 4. pytest

    .venv/Scripts/python.exe -m pytest -q tests/rag -p no:cacheprovider

默认质量阈值为 0.0，只验证机制；要启用质量门禁，设置环境变量：

    $env:RAG_EVAL_MIN_CHUNK_PASS_RATE="0.90"
    $env:RAG_EVAL_MIN_RETRIEVAL_RECALL="0.60"
    $env:RAG_EVAL_MIN_RERANK_RECALL="0.55"
    $env:RAG_EVAL_MIN_RERANK_TOP1="0.35"
    $env:RAG_EVAL_MIN_INJECTION_ACCURACY="0.60"
    $env:RAG_EVAL_MIN_PROMPT_PASS_RATE="0.55"
    $env:RAG_EVAL_MIN_PASS_RATE="0.50"
    .venv/Scripts/python.exe -m pytest -q tests/rag -p no:cacheprovider

### 5. 整体验收入口

    powershell -ExecutionPolicy Bypass -File scripts/test_all.ps1 -IncludeRag

该入口会执行 tests/rag；只有环境变量阈值和 CLI 阈值都满足时才应视为通过。

## 八、失败归因

| failure code | 归属 | 常见原因 |
| --- | --- | --- |
| no_expected_hit_in_coarse | retrieval | 粗召回候选集没有正确文档，检查 BM25 token、别名、索引 |
| forbidden_source_matched | retrieval/rerank | 近似名/同名角色抢占 |
| missing_required_source_paths | retrieval | 多文档题在粗召回里只出现一份 |
| final_rank_too_low | rerank | 正确文档进入 top-k 但超出 max_rank |
| top1_source_mismatch | rerank | 正确文档被重排到后面 |
| section_hits_below_min | rerank/chunk | 基本资料、专辑等 section 没进 top-k |
| content_terms_missing | rerank | 事实词没有进入上下文 |
| should_inject_mismatch | injection | 置信度策略过松/过严 |
| confidence_level_not_allowed | injection | BM25-only 判定为 low 或 none |
| citation_count_too_low | injection | 注入但无 citation |
| required_citation_sources_missing | injection | citation 来源不含期望文档 |
| prompt_term_missing | prompt | 事实词没进入最终上下文 |
| prompt_not_empty | prompt | 负例仍然注入 |
| prompt_too_long | prompt | 上下文预算超限 |
| terms_split | chunk | 姓名/生日/代表色被切到两个 chunk |
| metadata_missing | chunk | aliases/topic/character 等字段缺失 |
| invalid_chunk_index | index | chunk_index 缺失或为负数 |
| chunk_count_mismatch | index | 实际 chunks 与 stats 不一致 |

## 九、加用例

查询用例：

1. 追加到 cases.jsonl，case_id 与 query 在全集唯一。
2. suite 只能是 smoke/core/hard。
3. 正例必须有 expected_source_paths；多文档题用 required_source_paths。
4. expected_content_terms 必须逐字出现在期望文档中。
5. 负例用 forbidden_source_paths，不写 expected_source_paths。
6. injection/prompt 期望按真实契约写，不要放宽来让用例通过。
7. 更新 manifest.json 的 query_cases 统计。

chunk 用例：

1. 追加到 chunk_cases.jsonl，source_path 必须真实存在。
2. required_section 与 must_keep_together 必须逐字出现在原文。
3. 更新 manifest.json 的 chunk_cases 统计。

## 十、发布要求

涉及以下改动时，必须跑 smoke + core + hard + all：

- aiagent/knowledge/document_loader.py
- aiagent/knowledge/retriever.py
- aiagent/knowledge/reranker.py
- aiagent/knowledge/query_normalizer.py
- aiagent/knowledge/character_aliases.py
- aiagent/knowledge/rag_pipeline.py
- aiagent/knowledge/rag_confidence.py
- aiagent/knowledge/rag_citations.py
- 知识库文档或 chunk 策略
- embedding 模型或维度
- 注入阈值或 prompt 格式

发布前至少满足：

1. chunk_pass_rate = 1.0（chunk/index 契约不允许退化）。
2. smoke 的 retrieval_recall、injection_accuracy、prompt_pass_rate 不低于 ratchet 阈值。
3. all 的失败用例有明确归因，不允许只调阈值。
4. 报告中 corpus.sha256 与当前知识库一致。

## 十一、已知限制

- BM25-only：不覆盖 embedding / FAISS / hybrid。
- injection stage 会重复执行一次 pipeline.inspect。
- forbidden 检查覆盖整个 top-k，rank 4 也算踩。
- 内容词是严格子串匹配，不做同义词扩展。
- chunk topic 受启发式规则影响，chunk 用例不对 topic 做硬断言。
- 没有 LLM 答案级评测。
- data/knowledge 不入仓；换语料必须重记基线。
