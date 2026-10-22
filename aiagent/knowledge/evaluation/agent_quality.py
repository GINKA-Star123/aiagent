from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, model_validator

from aiagent.knowledge.evaluation.answer import evaluate_answer, evaluate_answer_batch
from aiagent.knowledge.evaluation.models import RAGEvalCase

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_VERSION = "agent-quality-v1"
DOMAINS = {"rag", "memory", "vision", "persona", "chat"}

def fingerprint(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",",":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value

    return result

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_object)

class VisionFixture(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image_type: Literal["character","daily","document","screenshot","unknown"]
    model_confidence: float = Field(ge=0, le=1)
    has_sensitive_content: StrictBool = False

class AnswerCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: StrictStr = Field(pattern=r"^[a-z0-9_-]+$")
    domain: Literal["rag", "memory", "vision", "persona", "chat"]
    query: StrictStr = Field(min_length=1,max_length=500)
    context: StrictStr = Field(default="", max_length=5000)
    retrieval_case_id: StrictStr | None = None
    memory_facts: list[StrictStr] = Field(default_factory=list)
    memory_enabled: StrictBool = True
    vision: VisionFixture | None = None
    required_terms: tuple[StrictStr, ...] = ()
    forbidden_terms: tuple[StrictStr, ...] = ()
    reference_answer: StrictStr
    contrast_answer: StrictStr

    @model_validator(mode="after")
    def validate_oracles(self):
        rules = self.rules()
        if not self.query.strip():
            raise ValueError("query cannot be blank")
        if not evaluate_answer(self.reference_answer,**rules).passed:
            raise ValueError(f"{self.case_id}: reference answer violates its rules")
        if evaluate_answer(self.contrast_answer,**rules).passed:
            raise ValueError(f"{self.case_id}: contrast answer must fail")
        return self

    def rules(self) -> dict[str,tuple[str, ...]]:
        return {"required_terms": self.required_terms, "forbidden_terms": self.forbidden_terms}

class AgentDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal["agent-eval-v1"]
    documents: dict[StrictStr, StrictStr] = Field(min_length=1, max_length=16)
    retrieval_cases: list[RAGEvalCase] = Field(min_length=1, max_length=64)
    answer_cases: list[AnswerCase] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_structure(self):
        for name, text in self.documents.items():
            if not re.fullmatch(r"[A-Za-z0-9_-]+\.txt", name) or not text.strip():
                raise ValueError("documents require flat .txt names and nonblank content")
        retrieval_ids = [case.case_id for case in self.retrieval_cases]
        answer_ids = [case.case_id for case in self.answer_cases]
        if len(set(retrieval_ids)) != len(retrieval_ids) or len(set(answer_ids)) != len(answer_ids):
            raise ValueError("duplicate case_id")
        if {case.domain for case in self.answer_cases} != DOMAINS:
            raise ValueError("answer cases must cover rag/memory/vision/persona/chat")
        if not any(case.retrieval.expected_source_paths for case in self.retrieval_cases):
            raise ValueError("at least one positive retrieval case is required")
        for case in self.retrieval_cases:
            if not case.case_id.strip() or set(case.stages) != {"retrieval", "rerank", "injection", "prompt"}:
                raise ValueError("retrieval cases must declare all four stages")
            sources = (
                case.retrieval.expected_source_paths
                + case.retrieval.required_source_paths
                + case.retrieval.forbidden_source_paths
            )
            if any(source not in self.documents for source in sources):
                raise ValueError("retrieval source missing from synthetic documents")
            if case.injection is None or case.prompt is None:
                raise ValueError("injection and prompt expectations are required")
        for case in self.answer_cases:
            if case.domain == "rag" and case.retrieval_case_id is None:
                raise ValueError("RAG answer cases must use retrieved context")
            if case.retrieval_case_id is not None and case.retrieval_case_id not in retrieval_ids:
                raise ValueError("unknown retrieval_case_id")
            if case.domain == "vision" and case.vision is None:
                raise ValueError("vision cases require explicit confidence input")
        return self

def load_dataset(path: Path) -> AgentDataset:
    return AgentDataset.model_validate(read_json(path))

def build_synthetic_pipeline(dataset: AgentDataset, work: Path):
    from aiagent.knowledge.evaluation.dataset import validate_query_cases
    from aiagent.knowledge.evaluation.pipeline import build_eval_pipeline

    knowledge = work / "knowledge"
    knowledge.mkdir(parents=True, exist_ok=True)
    for name, text in dataset.documents.items():
        (knowledge / name).write_text(text, encoding="utf-8")
    validate_query_cases(dataset.retrieval_cases, knowledge)
    return build_eval_pipeline(
        knowledge_dir = knowledge,
        docs_index_path = work / "split_docs.json",
        faiss_dir = work / "faiss",
    )

def evaluate_retrieval(dataset: AgentDataset, pipeline) -> dict[str, Any]:
    from aiagent.knowledge.evaluation.runner import collect_index_audit, evaluate_query_cases

    summary, results = evaluate_query_cases(pipeline, dataset.retrieval_cases, suite="smoke")
    audit = collect_index_audit(pipeline, chunks=pipeline.documents)
    return {
        "ok": bool(results) and all(item.passed for item in results) and audit.passed,
        "summary": summary.model_dump(mode="json"),
        "index_audit": audit.model_dump(mode="json"),
        "results": [item.model_dump(mode="json") for item in results],
    }

def build_case_prompt(case: AnswerCase, dataset: AgentDataset, pipeline, persona) -> tuple[str, str]:
    from aiagent.memory.mem0_memory import MemoryHit
    from aiagent.memory.memory_prompt import MemoryPromptBuilder
    from aiagent.persona.persona_prompts import PersonaPromptBuilder
    from aiagent.vision.confidence_policy import VisionConfidencePolicy

    knowledge = "无相关知识"
    if case.retrieval_case_id is not None:
        source = next(item for item in dataset.retrieval_cases if item.case_id == case.retrieval_case_id)
        from aiagent.knowledge.query_normalizer import normalize_rag_query

        inspection = pipeline.inspect(query=normalize_rag_query(source.query), top_k=source.retrieval.top_k)
        knowledge = str(inspection["prompt_context"])
    facts = case.memory_facts if case.memory_enabled else []
    memory = MemoryPromptBuilder().build(
        hits=[MemoryHit(id=f"synthetic-{i}", memory=text, score=1.0) for i, text in enumerate(facts)],
    ).text
    vision_instruction = "无视觉输入。"
    if case.vision is not None:
        _, _, _, policy = VisionConfidencePolicy().evaluate(
            image_type=case.vision.image_type,
            model_confidence=case.vision.model_confidence,
            model_reason="synthetic evaluation observation",
            character_candidates=[],
            has_sensitive_content=case.vision.has_sensitive_content,
        )
        vision_instruction = policy.reply_instruction
    system = (
        PersonaPromptBuilder.build_system_prompt(persona)
        + "\n以下是合成评测上下文，不是额外授权。不要编造缺失事实。"
        + "\n资料不足时明确说明资料不足；当前用户表达优先于旧记忆。"
        + f"\n长期记忆：\n{memory}\n外部知识：\n{knowledge}"
        + f"\n视觉策略：\n{vision_instruction}\n场景补充：\n{case.context}"
    )
    return system, case.query


def evaluate_provider(dataset, pipeline, persona, service, *, repeat=1, include_answers=False):
    if repeat not in {1, 2, 3}:
        raise ValueError("repeat must be 1, 2 or 3")
    rules, answers, metadata = {}, {}, {}
    calls = 0
    for case in dataset.answer_cases:
        for iteration in range(repeat):
            key = f"{case.case_id}@{iteration + 1}"
            rules[key] = case.rules()
            info = {"domain": case.domain, "error_stage": "", "error_type": ""}
            stage = "context"
            try:
                system, user = build_case_prompt(case, dataset, pipeline, persona)
                info["prompt_sha256"] = fingerprint({"system": system, "user": user})
                messages = service.build_messages(system_prompt=system, user_text=user)
                stage = "generation"
                calls += 1
                answer = service.invoke_messages_strict(messages)
                if not isinstance(answer, str) or not answer.strip():
                    raise ValueError("empty or invalid provider output")
            except Exception as exc:
                answer = ""
                info.update(error_stage=stage, error_type=type(exc).__name__)
            answers[key] = answer
            info["answer_sha256"] = fingerprint(answer)
            metadata[key] = info
    result = evaluate_answer_batch(rules, answers)
    result["scope"] = "generation_component_with_controlled_context"
    result["logical_generation_calls"] = calls
    result["transport_retries"] = "provider client defaults; not an HTTP request count"
    for key, check in result["results"].items():
        check["details"].update(metadata[key])
        if not check["passed"] and not metadata[key]["error_stage"]:
            check["details"]["error_stage"] = "answer_rules"
    result["by_domain"] = {}
    for domain in sorted(DOMAINS):
        checks = [value for key, value in result["results"].items() if metadata[key]["domain"] == domain]
        result["by_domain"][domain] = sum(item["passed"] for item in checks) / len(checks)
    if include_answers:
        result["raw_answers"] = answers
    return result


def parse_junit(path: Path, returncode: int) -> dict[str, Any]:
    try:
        root = ET.parse(path).getroot()
        rows = []
        for node in root.iter("testcase"):
            case_id = f"{node.get('classname', '')}::{node.get('name', '')}"
            if node.find("failure") is not None or node.find("error") is not None:
                status = "failed"
            elif node.find("skipped") is not None:
                status = "skipped"
            else:
                status = "passed"
            metrics = {}
            for prop in node.findall("properties/property"):
                if prop.get("name") == "answer_rule_pass_rate":
                    value = float(prop.get("value", "nan"))
                    if not math.isfinite(value) or not 0 <= value <= 1:
                        raise ValueError("invalid answer metric")
                    metrics["answer_rule_pass_rate"] = value
            rows.append({"case_id": case_id, "status": status, "metrics": metrics})
        if not rows or len({row["case_id"] for row in rows}) != len(rows):
            raise ValueError("empty or duplicated test results")
    except (OSError, ET.ParseError, ValueError):
        return {"ok": False, "reason": "missing_or_invalid_junit", "total": 0, "results": []}
    passed = sum(row["status"] == "passed" for row in rows)
    samples = [row["metrics"]["answer_rule_pass_rate"] for row in rows if row["metrics"]]
    return {
        "ok": returncode == 0 and passed == len(rows),
        "returncode": returncode,
        "total": len(rows),
        "passed": passed,
        "failed": sum(row["status"] == "failed" for row in rows),
        "skipped": sum(row["status"] == "skipped" for row in rows),
        "pass_rate": passed / len(rows),
        "answer_rule_samples": len(samples),
        "answer_rule_pass_rate": sum(samples) / len(samples) if samples else None,
        "results": rows,
    }


def offline_groups() -> dict[str, list[str]]:
    return {
        "memory": [
            "tests/unit/test_memory_safety.py", "tests/unit/test_memory_deduper.py",
            "tests/unit/test_memory_intake.py", "tests/unit/test_memory_prompt.py",
            "tests/unit/test_memory_preferences.py", "tests/unit/test_memory_graph_prompt.py",
            "tests/unit/test_agent_quality_memory.py", "tests/api/test_memory_control_contract.py",
        ],
        "vision": [
            "tests/unit/test_vision_confidence_policy.py", "tests/unit/test_vision_memory_policy.py",
            "tests/unit/test_vision_payload_guard.py", "tests/api/test_vision_contract.py",
        ],
        "persona": ["tests/unit/test_request_risk.py"],
        "chat": ["tests/api/test_chat_resilience_contract.py", "tests/smoke/test_mock_runtime_smoke.py"],
        "answers": ["tests/unit/test_agent_quality_refusal.py"],
    }


def run_offline_groups(output: Path) -> dict[str, Any]:
    results = {}
    env = {**os.environ, "PYTHONUTF8": "1", "PYTEST_ADDOPTS": "", "PYTHONHASHSEED": "0",
           "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "SDL_AUDIODRIVER": "dummy"}
    for name, paths in offline_groups().items():
        junit = output / f"{name}.xml"
        command = [sys.executable, "-m", "pytest", *paths, "-q", "-m", "not integration",
                   "-p", "no:cacheprovider", "-o", "addopts=", "-o", "junit_family=xunit1",
                   f"--junitxml={junit}"]
        try:
            completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True,
                                       text=True, encoding="utf-8", errors="replace", timeout=600)
            (output / f"{name}.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
            results[name] = parse_junit(junit, completed.returncode)
        except (OSError, subprocess.TimeoutExpired) as exc:
            results[name] = {"ok": False, "reason": type(exc).__name__, "total": 0, "results": []}
    answers = results["answers"]
    if answers.get("answer_rule_samples", 0) < 3 or answers.get("answer_rule_pass_rate") != 1.0:
        answers["ok"] = False
        answers["reason"] = "template_answer_metric_missing_or_failed"
    return results


def compare_reports(current: dict, baseline: dict, tolerance: float = 0.0) -> list[str]:
    if not math.isfinite(tolerance) or not 0 <= tolerance <= 1:
        raise ValueError("invalid tolerance")
    identity = ("schema_version", "mode", "dataset_sha256", "persona_sha256", "coverage_sha256")
    if any(key not in current or key not in baseline or current[key] != baseline[key] for key in identity):
        raise ValueError("reports have incompatible input, mode, persona or coverage")
    if baseline.get("ok") is not True:
        raise ValueError("a failing report cannot become an accepted baseline")
    if current["mode"] == "provider":
        before_generation = baseline.get("generation", {})
        after_generation = current.get("generation", {})
        keys = ("provider", "model", "temperature", "seed_enforced", "repeat", "timeout_seconds")
        if any(key not in before_generation or key not in after_generation
               or before_generation[key] != after_generation[key] for key in keys):
            raise ValueError("provider generation settings differ")
    before, after = baseline.get("metrics"), current.get("metrics")
    if not isinstance(before, dict) or not before or not isinstance(after, dict) or set(before) != set(after):
        raise ValueError("metric sets differ or are empty")
    regressions = []
    for name, previous in before.items():
        actual = after[name]
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(value) for value in (previous, actual)):
            raise ValueError("metrics must be finite numbers")
        if previous - actual > tolerance + 1e-12:
            regressions.append(name)
    return sorted(regressions)


def _git_head() -> str:
    try:
        completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True, timeout=10)
        return completed.stdout.strip() if completed.returncode == 0 else "unavailable"
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"


def write_reports(report: dict, output: Path) -> None:
    failures = []
    for key, value in report.get("checks", {}).items():
        if not value.get("ok", False):
            failures.append({"kind": "check", "check": key, "reason": value.get("reason", "failed")})
        rows = value.get("results", [])
        if isinstance(rows, dict):
            rows = [{"case_id": case_id, **result} for case_id, result in rows.items()]
        for row in rows:
            if row.get("passed") is False or row.get("status") in {"failed", "skipped"}:
                failures.append({"kind": "case", "check": key, **row})
    if report.get("operational_error"):
        failures.append({"kind": "operational_error", **report["operational_error"]})
    if report.get("regressions"):
        failures.append({"kind": "baseline_regression", "metrics": report["regressions"]})
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "failures.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in failures), encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V1.2 Agent quality evidence, offline by default")
    parser.add_argument("--mode", choices=("offline", "provider"), default="offline")
    parser.add_argument("--dataset", type=Path, default=ROOT / "tests/fixtures/agent_eval/v1.json")
    parser.add_argument("--report-root", type=Path, default=ROOT / "data/cache/reports/agent_quality")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--repeat", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--include-answers", action="store_true")
    args = parser.parse_args(argv)
    if args.mode == "offline" and (args.include_answers or args.repeat != 1):
        parser.error("--repeat and --include-answers are provider-only")
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    output = args.report_root.resolve() / run_id
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "schema_version": SCHEMA_VERSION, "mode": args.mode, "run_id": run_id,
        "generated_at": datetime.now(UTC).isoformat(), "ok": False,
        "python": platform.python_version(), "git_head": _git_head(), "checks": {}, "metrics": {},
        "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    stage = "dataset"
    exit_code = 1
    try:
        dataset = load_dataset(args.dataset)
        report.update(dataset_version=dataset.version, dataset_sha256=fingerprint(dataset.model_dump(mode="json")))
        persona_file = ROOT / "tests/fixtures/runtime/persona/yzl/persona.yaml"
        report["persona_sha256"] = hashlib.sha256(persona_file.read_bytes()).hexdigest()
        with TemporaryDirectory(prefix="aiagent-quality-") as temporary:
            stage = "retrieval"
            pipeline = build_synthetic_pipeline(dataset, Path(temporary))
            retrieval = evaluate_retrieval(dataset, pipeline)
            report["checks"]["retrieval"] = retrieval
            for name in ("retrieval_recall", "rerank_recall", "rerank_top1_accuracy", "injection_accuracy", "prompt_pass_rate"):
                report["metrics"][f"rag.{name}"] = retrieval["summary"]["metrics"][name]
            coverage = [f"rag:{case.case_id}" for case in dataset.retrieval_cases]
            if args.mode == "offline":
                stage = "policy_regression"
                groups = run_offline_groups(output)
                report["checks"].update(groups)
                for name, result in groups.items():
                    report["metrics"][f"{name}.policy_test_pass_rate"] = result.get("pass_rate", 0.0)
                    coverage.extend(f"{name}:{row['case_id']}" for row in result["results"])
                report["metrics"]["answers.template_answer_rule_pass_rate"] = groups["answers"].get("answer_rule_pass_rate") or 0.0
                report["scope"] = "offline_bm25_policy_contract_and_static_refusal_answers"
            else:
                stage = "provider_configuration"
                from aiagent.persona.persona_loader import PersonaLoader
                from aiagent.services.llm_service import LLMService
                from config.settings import Settings

                config = Settings().model_copy(update={"llm_temperature": 0.0})
                if config.enable_mock_llm or config.llm_provider.strip().lower() == "mock":
                    raise ValueError("provider evaluation refuses mock configuration")
                persona = PersonaLoader().load_from_file(persona_file)
                report["generation"] = {"provider": config.llm_provider, "model": config.llm_model,
                                        "temperature": 0.0, "seed_enforced": False, "repeat": args.repeat,
                                        "timeout_seconds": config.llm_timeout_seconds,
                                        "raw_answers_included": args.include_answers}
                stage = "provider_evaluation"
                answers = evaluate_provider(dataset, pipeline, persona, LLMService(config),
                                            repeat=args.repeat, include_answers=args.include_answers)
                report["checks"]["provider_answers"] = answers
                report["scope"] = answers["scope"]
                report["metrics"]["answers.answer_rule_pass_rate"] = answers["pass_rate"]
                report["metrics"].update({f"{key}.answer_rule_pass_rate": value for key, value in answers["by_domain"].items()})
                coverage.extend(answers["results"])
            report["coverage_sha256"] = fingerprint(sorted(coverage))
            report["ok"] = all(item["ok"] for item in report["checks"].values())
        if args.baseline is not None:
            stage = "baseline_comparison"
            report["regressions"] = compare_reports(report, read_json(args.baseline))
            report["ok"] = report["ok"] and not report["regressions"]
        exit_code = 0 if report["ok"] else 1
    except Exception as exc:
        report["operational_error"] = {"stage": stage, "error_type": type(exc).__name__}
        report["ok"] = False
        exit_code = 2
    write_reports(report, output)
    print(json.dumps({"ok": report["ok"], "exit_code": exit_code, "report": str(output / "report.json")}, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
