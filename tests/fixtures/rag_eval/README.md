# RAG 全链路评测体系（V2）

本目录是 AIAgent 的 RAG 全链路离线评测集，覆盖：

1. 切分 chunk
2. 建索引
3. 粗召回 retrieval
4. 重排 rerank
5. 置信度与注入决策 injection
6. 最终 prompt context 与 citations

评测目标是“链路每一段都能被单独判定”，而不是只回答“最终有没有召回正确文档”。

> 旧的 32 条检索集、上一版 88 条 retrieval-only 用例、旧 aiagent/knowledge/rag_eval*.py 和 tests/rag/test_rag_quality_baseline.py 已全部移除。
> 当前数据集是 **v3 rebuild**：从当前 256 篇语料重新按类别配额构造，共 120 条查询用例 + 12 条 chunk 用例；旧基线数字不再适用于本数据集。

## 1. 文件

| 文件 | 用途 |
| --- | --- |
| cases.jsonl | 120 条查询级用例，带 retrieval / rerank / injection / prompt 四段期望 |
| chunk_cases.jsonl | 12 条 chunk 级用例，检查 metadata、section、切分完整性和 chunk 数量 |
| manifest.json | 版本、语料指纹、用例规模、stages |
| thresholds.example.json | 目标阈值模板，不是已测量基线 |
| README.md | 本文件 |

查询用例按 suite 分三组：smoke 30、core 54、hard 36。CLI 用 --suite 过滤，不需要拆文件。

### 1.1 类别与难度分配

| category | smoke | core | hard | total |
| --- | ---: | ---: | ---: | ---: |
| character | 12 | 16 | 12 | 40 |
| setting | 12 | 20 | 0 | 32 |
| song | 2 | 6 | 4 | 12 |
| relation | 1 | 5 | 6 | 12 |
| group | 1 | 1 | 4 | 6 |
| fan_chant | 0 | 4 | 2 | 6 |
| mixed | 0 | 0 | 6 | 6 |
| negative | 2 | 2 | 2 | 6 |
| **total** | **30** | **54** | **36** | **120** |

难度与 suite 对齐：smoke = easy（30）、core = normal（54）、hard = hard（36）。这是有意的分层门禁，不是按每道题主观估难度。

构造方式：

1. 从当前 256 篇语料中按类别配额挑选文档，不沿用上一版 88 条。
2. identity/alias/English/事实/专辑/团体从语料 metadata 和正文抽取；relation、mixed、fan_chant、negative 用固定场景。
3. 所有 expected_source_paths 必须是真实文件；所有 expected_content_terms 必须逐字出现在期望文档中，否则数据集校验失败。
4. chunk 用例覆盖核心 6 人 + 五维 5 人 + 心华，共 12 篇，用来锁住 character/aliases/search_aliases 和基本资料完整性。

## 2. 语料与版本

- 知识库目录：data/knowledge/public
- 文件数：256
- 总字节：1,687,570
- 语料指纹：b397bb1182ec6ac18e8cfb1faaf1b20dbf9f46f1a595906f120e6133666e2c47
- 指纹算法：按 POSIX 相对路径字符串区分大小写排序，对每个文件依次哈希 path + NUL + size + NUL + bytes。文件内容按原始字节读取，不转换换行符；不使用平台相关的 Path 排序，以保持 Windows/Linux 一致。

data/knowledge 被 .gitignore 忽略。换机器或换语料后，先核对：

    (Get-ChildItem data/knowledge/public -Filter *.md).Count

如果不是 256，或 manifest.json 里的 sha256 对不上，评测仍可跑，但结果不能和旧基线直接比较。

## 3. 查询用例 schema

每行一个 JSON object。核心字段：

| 字段 | 说明 |
| --- | --- |
| case_id | 全集唯一 |
| suite | smoke / core / hard |
| category | character / setting / song / fan_chant / group / relation / mixed / negative |
| query | 用户原始问法；执行时先过 normalize_rag_query |
| difficulty | easy / normal / hard |
| tags | 诊断标签 |
| stages | 本用例要跑的阶段；正例是 retrieval/rerank/injection/prompt，负例是 retrieval/injection/prompt |
| retrieval | 粗召回与最终 top-k 的文档期望 |
| rerank | top1、section、内容词期望 |
| injection | should_inject、confidence level/status、citation 数量与来源 |
| prompt | 最终注入文本的结构、术语、长度、空上下文期望 |
| note | 这道题想测什么 |

retrieval 子字段：

| 字段 | 说明 |
| --- | --- |
| expected_source_paths | 期望命中的文档（相对 data/knowledge/public） |
| required_source_paths | 多文档题必须同时命中的文档 |
| forbidden_source_paths | 任意一条进入 top-k 即失败 |
| expected_content_terms | top-k 内容里必须出现的词 |
| top_k | 最终返回条数 |
| max_rank | 正确文档允许的最晚排名 |

rerank 子字段：

| 字段 | 说明 |
| --- | --- |
| expected_top1_source_paths | 期望排在第 1 位的文档，可给多个候选 |
| expected_sections | 期望出现在 top-k 内容里的 section 标题 |
| min_section_hits | 至少命中的 section 数 |
| max_top1_rank | 预留字段，当前按 top1 判定 |

injection 子字段：

| 字段 | 说明 |
| --- | --- |
| should_inject | 期望是否注入 prompt |
| allowed_levels | 允许的 confidence.level |
| allowed_statuses | 允许的 confidence.status |
| min_citations / max_citations | citation 数量范围 |
| required_citation_sources | 必须出现在 citations 里的来源 |
| forbidden_citation_sources | 不允许出现的来源 |

prompt 子字段：

| 字段 | 说明 |
| --- | --- |
| must_contain | 注入文本必须包含的结构串，例如 [知识片段 1]、标题:、来源: |
| must_not_contain | 不允许出现的内容，例如绝对路径 |
| required_terms | 注入文本必须包含的事实词 |
| forbidden_terms | 不允许出现的事实词 |
| max_chars | 注入文本最大字符数 |
| expect_empty | 负例期望空上下文（无相关知识） |

判定语义：

1. retrieval：forbidden 不能命中最终 top-k；required 和 expected 必须出现在粗召回候选集。
2. rerank：top1 必须是期望文档之一；top-k 至少命中 min_section_hits 个 section；expected_content_terms 必须全部出现在 top-k 内容里；最终 rank 不得晚于 max_rank。
3. injection：should_inject、level、status 必须匹配；citation 数量在范围内；required sources 必须出现，forbidden sources 不能出现。
4. prompt：expect_empty 时必须是“无相关知识”；否则检查结构串、事实词、绝对路径和长度。
5. end_to_end：本用例声明的所有 stage 全部通过。

## 4. chunk 用例 schema

chunk_cases.jsonl 只针对关键文档，检查：

| 字段 | 说明 |
| --- | --- |
| source_path | 被检查的文档 |
| expected_character | metadata.character |
| expected_doc_kind | profile / long_form / reference |
| required_metadata | 必须存在的 metadata 键 |
| required_alias | aliases 里必须存在的别名 |
| required_search_alias | search_aliases 里必须存在的英文/拼音标识 |
| required_section | 至少一个 chunk 包含该 section 标题 |
| must_keep_together | 每组词必须出现在同一个 chunk |
| min_chunks / max_chunks | chunk 数量范围 |
| min_chunk_chars / max_chunk_chars | 单 chunk 长度范围 |
| forbidden_terms | 不允许出现的词 |

另外，chunk_global 会自动检查：

- 知识库文件是否全部进入索引
- chunk_id 是否全局唯一
- 是否有空 chunk
- 必需 metadata 是否齐全
- chunk 是否超过 1200 字符
- chunk_index 是否为非负整数（当前 loader 的 index 是 section 局部序号，不按文档全局连续）
- source_path 是否被写成绝对路径

index_audit 会检查：

- chunk_count 与实际 documents 数一致
- chunk_size=520、chunk_overlap=80
- vector_count=0（BM25-only）
- index_stale=false
- build_status=done
- manifest 存在

## 5. 指标

查询级：

| 指标 | 定义 |
| --- | --- |
| retrieval_recall | 正例中，期望文档进入粗召回候选集的比例 |
| retrieval_mrr | 正例中，正确文档在粗召回里的排名倒数均值 |
| rerank_recall | 正例中，期望文档进入最终 top-k 的比例 |
| rerank_mrr | 正例中，正确文档最终排名的倒数均值 |
| rerank_top1_accuracy | 给出 expected_top1 的正例中，top1 命中的比例 |
| injection_accuracy | injection stage 通过率 |
| prompt_pass_rate | prompt stage 通过率 |
| end_to_end_pass_rate | 所有 stage 全通过的比例 |

chunk 级：

| 指标 | 定义 |
| --- | --- |
| chunk_pass_rate | chunk_global + 12 条 chunk case 的通过率 |
| index_audit | 索引结构是否满足约定 |

失败会保存为 failure code，例如：

- no_expected_hit_in_coarse
- forbidden_source_matched
- missing_required_source_paths
- final_rank_too_low
- top1_source_mismatch
- section_hits_below_min
- content_terms_missing
- should_inject_mismatch
- citation_count_too_low
- required_citation_sources_missing
- prompt_term_missing
- prompt_not_empty
- terms_split
- invalid_chunk_index

## 6. 测试步骤

所有命令在 F:\aiagent 下执行。

### 第一步：记录基线（不设阈值）

v3 数据集还没有基线数值。第一次先完整跑一次，记录 smoke/core/hard/all 四套结果；不要沿用旧 88 条的报告。
脚本默认所有 -Min* 都是 -1，即不启用阈值。先跑 smoke：

    powershell -ExecutionPolicy Bypass -File scripts/test_rag_quality_report.ps1 -Suite smoke -ReportPrefix rag_eval_smoke

再跑 core、hard、all：

    powershell -ExecutionPolicy Bypass -File scripts/test_rag_quality_report.ps1 -Suite core -ReportPrefix rag_eval_core
    powershell -ExecutionPolicy Bypass -File scripts/test_rag_quality_report.ps1 -Suite hard -ReportPrefix rag_eval_hard
    powershell -ExecutionPolicy Bypass -File scripts/test_rag_quality_report.ps1 -Suite all -ReportPrefix rag_eval_all

报告写到：

    data/cache/knowledge/reports/rag_eval_v2/

每次输出三个文件：

    rag_eval_smoke_report.json
    rag_eval_smoke_report.md
    rag_eval_smoke_failures.jsonl

### 第二步：检查报告

    Get-Content data/cache/knowledge/reports/rag_eval_v2/rag_eval_smoke_report.md -Encoding UTF8

失败样例：

    Get-Content data/cache/knowledge/reports/rag_eval_v2/rag_eval_smoke_failures.jsonl -Encoding UTF8 |
      ForEach-Object { $_ | ConvertFrom-Json } |
      Select-Object kind, case_id, error |
      Format-Table -AutoSize

单条 query 失败时，重点看 stages.retrieval.details、stages.rerank.details、stages.injection.details。

### 第三步：设置 ratchet 阈值

第一次基线跑完后，把阈值设成“基线 - 0.02”防退化；确认提升后再抬。示例：

    powershell -ExecutionPolicy Bypass -File scripts/test_rag_quality_report.ps1 -Suite smoke -ReportPrefix rag_eval_smoke -MinPassRate 0.50 -MinRetrievalRecall 0.60 -MinRerankRecall 0.55 -MinRerankTop1 0.35 -MinInjectionAccuracy 0.60 -MinPromptPassRate 0.55 -MinChunkPassRate 0.90

PowerShell 多行续行使用反引号（不是 cmd 的 ^）；这里统一写成一行，避免转义问题。阈值模板见 thresholds.example.json，但那只是目标值，不是基线。

### 第四步：pytest 契约测试

    .venv/Scripts/python.exe -m pytest -q tests/rag -p no:cacheprovider

测试文件：

| 文件 | 检查 |
| --- | --- |
| test_rag_eval_fixtures.py | 数据集结构、路径、术语、唯一 id |
| test_rag_eval_chunking.py | chunk/index 契约 |
| test_rag_eval_retrieval.py | retrieval / rerank 契约 |
| test_rag_eval_injection.py | injection / citation / prompt 契约 |
| test_rag_eval_end_to_end.py | end_to_end 汇总 |
| test_rag_eval_reporting.py | JSON/Markdown/failures 报告生成 |

质量阈值通过环境变量控制，默认 0.0（只验证机制，不验证质量）：

    $env:RAG_EVAL_MIN_CHUNK_PASS_RATE="0.90"
    $env:RAG_EVAL_MIN_RETRIEVAL_RECALL="0.60"
    $env:RAG_EVAL_MIN_RERANK_RECALL="0.55"
    $env:RAG_EVAL_MIN_RERANK_TOP1="0.35"
    $env:RAG_EVAL_MIN_INJECTION_ACCURACY="0.60"
    $env:RAG_EVAL_MIN_PROMPT_PASS_RATE="0.55"
    $env:RAG_EVAL_MIN_PASS_RATE="0.50"
    .venv/Scripts/python.exe -m pytest -q tests/rag -p no:cacheprovider

### 第五步：直接调用 CLI（可选）

    .venv/Scripts/python.exe -m aiagent.knowledge.evaluation.cli --suite smoke --cases tests/fixtures/rag_eval/cases.jsonl --chunk-cases tests/fixtures/rag_eval/chunk_cases.jsonl --knowledge-dir data/knowledge/public --write-report --report-prefix rag_eval_smoke --show-category-summary

常用参数：

| 参数 | 作用 |
| --- | --- |
| --suite smoke/core/hard/all | 过滤查询用例 |
| --no-chunk-audit | 跳过 chunk/index 检查，只跑查询 |
| --show-results | 打印逐条结果 |
| --print-markdown | 打印 Markdown 报告 |
| --write-report | 写 JSON/Markdown/failures |
| --min-pass-rate | end_to_end 阈值 |
| --min-retrieval-recall | retrieval recall 阈值 |
| --min-rerank-recall | rerank recall 阈值 |
| --min-rerank-top1 | rerank top1 阈值 |
| --min-injection-accuracy | injection 阈值 |
| --min-prompt-pass-rate | prompt 阈值 |
| --min-chunk-pass-rate | chunk/index 阈值 |

## 7. 优化闭环

1. 先跑 smoke，确认 chunk/index 和核心角色没被打崩。
2. 再跑 core，看跨角色、事实、关系、专辑、应援词。
3. 再跑 hard，看英文标识、双文档关系、别名消歧、长尾。
4. 最后跑 all。
5. 每轮只改一个变量：chunk 策略 / 别名表 / normalizer / reranker / 置信度 / prompt 格式。
6. 记录每轮的 6 个指标和失败 case_id；不要只盯 pass_rate。

推荐的优先顺序：

1. 精确名/别名加权与近似名抑制（解决洛天二、言懿、乐正玄青、蝶音、MOKO、徵羽沐可抢占）。
2. 基本资料 section 先验（生日/代表色/声源）。
3. 英文/拼音标识注入。
4. 双实体关系题的分实体召回与合并。
5. 置信度与负例注入策略。

## 8. 加用例

查询用例：

1. 追加到 cases.jsonl，保证 case_id 与 query 唯一。
2. suite 必须是 smoke/core/hard。
3. 正例给出 expected_source_paths；多文档题用 required_source_paths。
4. expected_content_terms 必须真的出现在期望文档原文里。
5. 负例用 forbidden_source_paths，不写 expected_source_paths。
6. injection/prompt 期望要按实际契约写，不要为了让用例通过而放宽。
7. 更新 manifest.json 的 query_cases 统计。

chunk 用例：

1. 追加到 chunk_cases.jsonl，source_path 必须真实存在。
2. required_section 和 must_keep_together 的字符串必须在原文里逐字出现。
3. 更新 manifest.json 的 chunk_cases 统计。

## 9. 已知限制

- 当前是 BM25-only：NullVectorStore 不产生向量候选，不覆盖 embedding / FAISS / hybrid 的真实质量。
- injection stage 为了与线上一致，会再走一次 pipeline.inspect；索引只构建一次，但每条 query 会多一次检索。
- forbidden 检查覆盖整个 top-k，rank 4 出现 forbidden 也算失败。
- expected_content_terms 和 prompt.required_terms 是严格子串匹配，不做同义词扩展。
- chunk 的 topic metadata 受启发式规则影响，chunk 用例只对 character/doc_kind/metadata 做硬断言，不断言 topic。
- 没有 LLM 答案级评测（groundedness、faithfulness）；本体系只评检索、注入和上下文契约。
- data/knowledge 不入仓；换语料必须重记基线。
