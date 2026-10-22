from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any

from aiagent.knowledge.evaluation.models import StageCheck


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold().strip()


def evaluate_answer(
    answer: str,
    *,
    required_terms: tuple[str, ...] = (),
    forbidden_terms: tuple[str, ...] = (),
) -> StageCheck:
    required = tuple(map(_normalize, required_terms))
    forbidden = tuple(map(_normalize, forbidden_terms))
    if not (required or forbidden) or any(not t for t in required + forbidden):
        raise ValueError("答案评测必须包含非空规则")
    if set(required) & set(forbidden):
        raise ValueError("必需词与禁止词不能相同")
    text = _normalize(answer)
    missing = [i for i, term in enumerate(required) if term not in text]
    violations = [i for i, term in enumerate(forbidden) if term in text]
    failures = ["answer_empty"] if not text else []
    failures += [f"required_term_missing:{i}" for i in missing]
    failures += [f"forbidden_term_present:{i}" for i in violations]
    return StageCheck(
        passed=not failures,
        failures=failures,
        details={
            "schema_version": "answer-rules-v1",
            "evaluation_mode": "deterministic_rules",
            "required_term_recall": (
                (len(required) - len(missing)) / len(required) if required else None
            ),
        },
    )

def evaluate_answer_batch(
    cases: dict[str, dict[str, tuple[str, ...]]],
    answers: dict[str, str],
) -> dict[str, Any]:
    if not cases or any(not key.strip() for key in cases):
        raise ValueError("评测集不能为空，用例编号不能为空白")
    if set(cases) != set(answers):
        missing = sorted(set(cases) - set(answers))
        unexpected = sorted(set(answers) - set(cases))
        raise ValueError(f"答案集合不匹配：缺失={missing}，多余={unexpected}")
    if any(not isinstance(answer, str) for answer in answers.values()):
        raise TypeError("答案必须是字符串，生成失败不能用 None 代替")
    results = {
        key: evaluate_answer(answers[key], **cases[key]).model_dump()
        for key in sorted(cases)
    }
    passed = sum(result["passed"] for result in results.values())
    dataset = json.dumps(cases, ensure_ascii=False, sort_keys=True)
    return {
        "schema_version": "answer-batch-v1",
        "evaluation_mode": "deterministic_rules",
        "dataset_sha256": hashlib.sha256(dataset.encode("utf-8")).hexdigest(),
        "total": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "pass_rate": passed / len(cases),
        "ok": passed == len(cases),
        "results": results,
    }
