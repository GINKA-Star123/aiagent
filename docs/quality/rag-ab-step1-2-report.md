# RAG A/B 实验报告：Step 1 + Step 2

- 实验日期：2026-10-19
- 数据集：v3 rebuild，120 条查询用例 + 12 条 chunk 用例
- 实验范围：character/aliases 元数据修复 + 中文实体 tokenizer
- 对比报告：
  - before: data/cache/knowledge/reports/rag_eval_v2/rag_eval_ab_before_report.json
  - after: data/cache/knowledge/reports/rag_eval_v2/rag_eval_ab_after_report.json
- 结论：检索层大幅改善，必须保留；下一主瓶颈是 section/内容词与 negative 注入。

> 说明：本次 A/B 实际是 Step 1（元数据）和 Step 2（tokenizer）合并后的对比，不是严格的分步隔离。  
> 报告中的 ok:true 仍然是因为运行时阈值是 -1，不代表质量通过。

## 1. 实验背景

v3 基线的主要问题：

- chunk 用例只有 4/13 通过；
- retrieval_recall 0.632，114 个正例中 42 条粗召回完全没命中；
- rerank_recall 0.500，粗召回命中后又被 reranker 丢掉 15 条；
- rerank_top1_accuracy 0.298；
- end_to_end 只有 15/120。

根因集中在两层：

1. character/aliases 元数据错配：洛天依/言和/乐正龙牙/墨清弦/徵羽摩柯被标成乐正绫，赤羽/海伊/诗岸/星尘被标成苍穹；
2. 中文 tokenizer 缺 2 字/4 字实体 token：赤羽、海伊、诗岸、星尘、苍穹、言和、乐正龙牙、初音未来、镜音铃·连无法稳定命中。

## 2. 改动代码

### 2.1 character_aliases.py：补中文文件名映射

文件：aiagent/knowledge/character_aliases.py

    CHARACTER_FILE_KEYS.update(
        {
            "乐正绫": "乐正绫",
            "洛天依": "洛天依",
            "言和": "言和",
            "乐正龙牙": "乐正龙牙",
            "墨清弦": "墨清弦",
            "徵羽摩柯": "徵羽摩柯",
            "苍穹": "苍穹",
            "赤羽": "赤羽",
            "海伊": "海伊",
            "诗岸": "诗岸",
            "星尘": "星尘",
            "心华": "心华",
            "永夜minus": "永夜Minus",
            "乐正零": "乐正零",
            "东方栀子": "东方栀子",
            "三色零歌": "三色零歌",
            "诗明空": "诗明空",
            "天崎默": "天崎默",
            "初音未来": "初音未来",
            "镜音铃·连": "镜音铃·连",
        }
    )

关键点：document_loader 使用 path.stem.strip().lower() 查表，所以永夜Minus 的 key 是 永夜minus。

### 2.2 document_loader.py：文件名/标题优先，正文兜底

修改 _infer_document_metadata 中的角色解析：

    file_key = path.stem.strip().lower()
    title = self._infer_title(text, path.stem)
    character = (
        CHARACTER_FILE_KEYS.get(file_key, "")
        or self._character_from_title(title)
        or self._match_character_by_text(text)
    )

新增 _character_from_title：

    def _character_from_title(self, title: str) -> str:
        normalized = str(title or "").strip().lstrip("#").strip()
        if not normalized:
            return ""

        for canonical, variants in CHARACTER_ALIASES.items():
            for variant in (canonical, *variants):
                if variant and normalized == variant:
                    return canonical

        for canonical, variants in CHARACTER_ALIASES.items():
            for variant in (canonical, *variants):
                if variant and normalized.startswith(variant):
                    return canonical

        return ""

替换 _match_character_by_text，改为最早出现优先：

    def _match_character_by_text(self, text: str) -> str:
        head = text[:2000]
        best_character = ""
        best_index = len(head) + 1
        best_variant_length = 0

        for canonical, variants in CHARACTER_ALIASES.items():
            for variant in (canonical, *variants):
                if not variant:
                    continue

                index = head.find(variant)
                if index < 0:
                    continue

                if index < best_index or (
                    index == best_index
                    and len(variant) > best_variant_length
                ):
                    best_character = canonical
                    best_index = index
                    best_variant_length = len(variant)

        return best_character

### 2.3 retriever.py：实体词原子 token

文件：aiagent/knowledge/retriever.py

新增 import：

    from aiagent.knowledge.character_aliases import (
        CHARACTER_ALIASES,
        CHARACTER_FILE_KEYS,
    )

新增实体词表：

    def _build_entity_terms() -> tuple[str, ...]:
        terms: set[str] = set()

        for canonical, variants in CHARACTER_ALIASES.items():
            terms.add(canonical)
            terms.update(variants)

        for key, value in CHARACTER_FILE_KEYS.items():
            terms.add(key)
            terms.add(value)

        normalized = {
            str(term).strip().lower()
            for term in terms
            if str(term).strip() and len(str(term).strip()) >= 2
        }
        return tuple(sorted(normalized, key=lambda item: (-len(item), item)))

    _ENTITY_TERMS = _build_entity_terms()

替换 _tokenize：

    def _tokenize(self, text: str) -> list[str]:
        lowered = text.lower()

        english_terms = re.findall(r"[a-z0-9_./:-]{2,}", lowered)
        entity_terms = [
            term for term in _ENTITY_TERMS
            if term in lowered
        ]

        chinese_blocks = re.findall(r"[\u4e00-\u9fff]+", lowered)
        chinese_terms: list[str] = []

        for block in chinese_blocks:
            if not block:
                continue

            chinese_terms.append(block)

            if len(block) >= 5:
                chinese_terms.extend(
                    block[i : i + 3]
                    for i in range(len(block) - 2)
                )

        seen: set[str] = set()
        output: list[str] = []

        for term in english_terms + entity_terms + chinese_terms:
            if term not in seen:
                seen.add(term)
                output.append(term)

        return output

### 2.4 回归测试

新增：

- tests/unit/test_document_loader_character_metadata.py
- tests/unit/test_retriever_tokenize.py

并复用：

- tests/rag/test_rag_eval_chunking.py
- tests/rag/test_rag_eval_retrieval.py

## 3. A/B 指标对比

### 3.1 三层指标

| 层 | 指标 | before | after | 变化 |
| --- | --- | ---: | ---: | ---: |
| 检索层 | chunk_pass_rate | 0.307692 | 1.000000 | +0.692308 |
| 检索层 | retrieval_recall | 0.631579 | 0.885965 | +0.254386 |
| 检索层 | retrieval_mrr | 0.437194 | 0.762949 | +0.325755 |
| 检索层 | rerank_recall | 0.500000 | 0.842105 | +0.342105 |
| 检索层 | rerank_mrr | 0.380409 | 0.728801 | +0.348392 |
| 检索层 | rerank_top1_accuracy | 0.298246 | 0.640351 | +0.342105 |
| 生成层 | injection_accuracy | 0.466667 | 0.750000 | +0.283333 |
| 生成层 | prompt_pass_rate | 0.341667 | 0.383333 | +0.041666 |
| 系统层 | pass_rate | 0.125000 | 0.150000 | +0.025000 |
| 系统层 | end_to_end_pass_rate | 0.125000 | 0.150000 | +0.025000 |

### 3.2 分 suite

| suite | before pass | after pass | before retrieval pass | after retrieval pass | before top1 | after top1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| smoke | 1/30 | 3/30 | 17 | 27 | 4 | 21 |
| core | 7/54 | 9/54 | 36 | 47 | 16 | 29 |
| hard | 7/36 | 6/36 | 23 | 29 | 14 | 23 |

### 3.3 分 category

| category | before pass | after pass | before ret | after ret | before top1 | after top1 | before section fail | after section fail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| character | 3/40 | 4/40 | 16 | 29 | 10 | 24 | 27 | 34 |
| setting | 0/32 | 2/32 | 21 | 32 | 4 | 21 | 22 | 26 |
| song | 6/12 | 8/12 | 12 | 12 | 8 | 12 | 2 | 1 |
| relation | 2/12 | 0/12 | 7 | 7 | 3 | 4 | 4 | 9 |
| group | 0/6 | 0/6 | 6 | 6 | 4 | 6 | 6 | 6 |
| fan_chant | 3/6 | 3/6 | 5 | 6 | 3 | 3 | 1 | 0 |
| mixed | 1/6 | 1/6 | 3 | 5 | 2 | 3 | 3 | 4 |
| negative | 0/6 | 0/6 | 6 | 6 | - | - | - | - |

### 3.4 阶段通过率

| stage | before | after |
| --- | ---: | ---: |
| retrieval | 76/120（0.633） | 103/120（0.858） |
| rerank | 15/114（0.132） | 19/114（0.167） |
| injection | 56/120（0.467） | 90/120（0.750） |
| prompt | 41/120（0.342） | 46/120（0.383） |
| end_to_end | 15/120（0.125） | 18/120（0.150） |

### 3.5 失败码变化

| stage | failure | before | after |
| --- | --- | ---: | ---: |
| retrieval | no_expected_hit_in_coarse | 42 | 13 |
| retrieval | missing_required_source_paths | 5 | 3 |
| retrieval | forbidden_source_matched | 1 | 1 |
| rerank | top1_source_mismatch | 80 | 41 |
| rerank | section_hits_below_min | 65 | 80 |
| rerank | content_terms_missing | 73 | 68 |
| rerank | final_rank_too_low | 3 | 3 |
| injection | required_citation_sources_missing | 58 | 23 |
| injection | should_inject_mismatch | 6 | 6 |
| injection | citation_count_too_high | 6 | 6 |
| injection | confidence_level/status_not_allowed | 6 | 6 |
| prompt | prompt_term_missing | 77 | 69 |
| prompt | prompt_not_empty | 6 | 6 |

## 4. 指标分析

### 4.1 检索层：Step 1 + Step 2 明确成功

粗召回命中：

- before: 72/114
- after: 101/114
- 42 条 no_expected_hit_in_coarse 降到 13 条

最终 top-k 命中：

- before: 57/114
- after: 96/114
- reranker 丢文档从 15 条降到 5 条

top1：

- before: 34/114
- after: 73/114

这说明：

1. 元数据修复让 character/aliases/search_aliases 不再污染 BM25 header；
2. 实体 tokenizer 让 2 字/4 字角色名和英文/拼音标识进入检索；
3. reranker “把正确文档丢掉”的问题已经大幅缓解。

### 4.2 生成层：citation 明显改善，prompt 仍受 section 拖累

injection：

- 0.467 → 0.750
- required_citation_sources_missing 58 → 23

原因：

- 文档级来源正确后，citation 来源也跟着正确；
- 正例 injection 从约 49% 提升到约 79%。

prompt：

- 0.342 → 0.383
- prompt_term_missing 77 → 69

原因：

- 文档对了，但 top-k 片段经常不是 基本资料/官方专辑/相关人士；
- 事实词没有进入最终上下文。

### 4.3 section 成为新的主瓶颈

section_hits_below_min：

- before: 65
- after: 80

这不是“section 变差”，而是：

- 以前大量用例在粗召回/top1 阶段就错了；
- 现在正确文档大量进入 top-k，甚至 top1 正确，但排到的 chunk 不是目标 section；
- section 失败从“被上游错误掩盖”变成“主要矛盾”。

当前漏斗：

    114 正例
      ↓ 粗召回命中 101
      ↓ 最终 top-k 命中 96
      ↓ top1 正确 73
      ↓ rerank 全通过 19
      ↓ end-to-end 通过 18

73 条 top1 正确里，有 54 条因为 section/内容词没通过 rerank。  
因此 end-to-end 只从 15 涨到 18。

### 4.4 negative 完全没有改善

6 条 negative：

- retrieval 6/6 通过；
- injection 0/6 通过；
- 全部 should_inject=true、medium、citation_count=4。

这是独立的置信度策略问题，Step 1/2 不会修它。

### 4.5 两条回退用例

improved：5 条

- smoke_ident_04 乐正龙牙是谁
- smoke_color_01 乐正绫的代表色是什么
- core_color_02 墨清弦的代表色是什么
- core_song_04 墨清弦的首张官方专辑是什么
- hard_song_11 诗岸的首张官方专辑是什么

regressed：2 条

- hard_rel_01 乐正绫和洛天依是什么关系
- hard_rel_06 乐正零是乐正绫的什么人

hard_rel_01：

- after 粗召回缺 洛天依.md；
- top-k 是 5 个 乐正绫.md + 战音Lorra.md；
- 单 query BM25 没有“两个实体各召回一份”的约束。

hard_rel_06：

- after 粗召回缺 乐正零.md；
- 乐正零 metadata 已正确，但 CHARACTER_ALIASES 还没有 乐正零/阿零/ZERO 的别名扩展；
- 同时需要分实体召回。

这两条回退不是元数据修复错了，而是暴露了多文档 relation 和别名表的缺口。

## 5. 实验结论

1. Step 1 + Step 2 必须保留，不能回退。  
   检索层提升非常大，chunk 从 4/13 到 13/13，retrieval_recall 从 0.632 到 0.886。

2. reranker 的“丢文档”问题已经基本解决。  
   丢失从 15 条降到 5 条；top1 从 34 到 73。

3. 新的主瓶颈是 section/内容词，不是文档召回。  
   section 失败 80 条；54 条 top1 正确但 rerank 不通过。

4. setting/group 是 section 问题的典型。  
   setting 粗召回 32/32、top1 21/32，但只通过 2/32；  
   group 粗召回 6/6、top1 6/6，但 0/6 通过。

5. negative 注入仍未修。  
   6/6 负例仍被注入 4 条 citation。

6. relation 出现 2 条回退。  
   需要别名表 + 分实体召回，不应靠回退元数据修复。

## 6. 下一步优先级

1. Step 3：section 先验 / chunk 级 rerank  
   目标：setting 从 2/32 提升，group 从 0/6 提升，section 失败从 80 下降。

2. Step 4：规范名/近似名 reranker 清理  
   top1 已到 73，但仍有 41 条 top1 mismatch；避免 section 修好后 top1 回退。

3. Step 5：negative 置信度  
   6/6 负例注入必须修。

4. Step 6：relation/group 分实体召回  
   修复 hard_rel_01、hard_rel_06 及 3 条 required 缺失。

## 7. 复现命令

改后基线：

    powershell -ExecutionPolicy Bypass -File scripts/test_rag_quality_report.ps1 -Suite all -ReportPrefix rag_eval_ab_after

A/B 对比：

    .venv/Scripts/python.exe scripts/rag_ab_compare.py --before data/cache/knowledge/reports/rag_eval_v2/rag_eval_ab_before_report.json --after data/cache/knowledge/reports/rag_eval_v2/rag_eval_ab_after_report.json

## 8. 报告来源

- before: rag_eval_ab_before_report.json
- after: rag_eval_ab_after_report.json
- after failures: rag_eval_ab_after_failures.jsonl
- chunk 结果来自 after report 的 chunk_results
- 本次没有重新运行评测；以上数字均来自两份报告。
