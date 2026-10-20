#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

LAYERS = {
    "retrieval": [
        "chunk_pass_rate",
        "retrieval_recall",
        "retrieval_mrr",
        "rerank_recall",
        "rerank_mrr",
        "rerank_top1_accuracy",
    ],
    "generation": [
        "injection_accuracy",
        "prompt_pass_rate",
    ],
    "system": [
        "pass_rate",
        "end_to_end_pass_rate",
    ],
}


def load_report(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def metric(report: dict[str, Any], name: str) -> float:
    if name == "chunk_pass_rate":
        return float(report.get("chunk_summary", {}).get("pass_rate", 0.0))

    if name == "pass_rate":
        return float(report.get("summary", {}).get("pass_rate", 0.0))

    metrics = report.get("summary", {}).get("metrics", {})
    return float(metrics.get(name, 0.0))


def stage_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["stage"]: item
        for item in report.get("summary", {}).get("stage_summaries", [])
    }


def category_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["category"]: item
        for item in report.get("metadata", {}).get("category_summaries", [])
    }


def case_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["case_id"]: item
        for item in report.get("results", [])
    }


def fmt(value: float) -> str:
    return f"{value:.6f}"


def delta(before: float, after: float) -> str:
    value = after - before
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.6f}"


def print_metric_table(
    title: str,
    before: dict[str, Any],
    after: dict[str, Any],
    names: list[str],
) -> None:
    print(f"\n## {title}\n")
    print("| metric | before | after | delta |")
    print("| --- | ---: | ---: | ---: |")
    for name in names:
        b = metric(before, name)
        a = metric(after, name)
        print(f"| {name} | {fmt(b)} | {fmt(a)} | {delta(b, a)} |")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare two RAG baseline reports by retrieval/generation/system layers."
    )
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--tolerance", type=float, default=0.0)
    parser.add_argument("--fail-on-regression", action="store_true")
    args = parser.parse_args(argv)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    before = load_report(args.before)
    after = load_report(args.after)

    before_suite = before.get("suite")
    after_suite = after.get("suite")
    if before_suite != after_suite:
        print(
            f"WARNING: suite differs: before={before_suite}, after={after_suite}",
            file=sys.stderr,
        )

    print("# RAG A/B Compare")
    print(f"- before: {args.before}")
    print(f"- after : {args.after}")
    print(f"- suite : {before_suite} -> {after_suite}")

    print_metric_table(
        "Retrieval Layer",
        before,
        after,
        LAYERS["retrieval"],
    )
    print_metric_table(
        "Generation Layer (injection / prompt context)",
        before,
        after,
        LAYERS["generation"],
    )
    print_metric_table(
        "System Layer (end-to-end)",
        before,
        after,
        LAYERS["system"],
    )

    before_stages = stage_map(before)
    after_stages = stage_map(after)
    stages = sorted(set(before_stages) | set(after_stages))

    print("\n## Stage Pass Rate\n")
    print("| stage | before | after | delta |")
    print("| --- | ---: | ---: | ---: |")
    for stage in stages:
        b = float(before_stages.get(stage, {}).get("pass_rate", 0.0))
        a = float(after_stages.get(stage, {}).get("pass_rate", 0.0))
        print(f"| {stage} | {fmt(b)} | {fmt(a)} | {delta(b, a)} |")

    before_categories = category_map(before)
    after_categories = category_map(after)
    categories = sorted(set(before_categories) | set(after_categories))

    print("\n## Category Pass Rate\n")
    print("| category | before | after | delta |")
    print("| --- | ---: | ---: | ---: |")
    for category in categories:
        b = float(before_categories.get(category, {}).get("pass_rate", 0.0))
        a = float(after_categories.get(category, {}).get("pass_rate", 0.0))
        print(f"| {category} | {fmt(b)} | {fmt(a)} | {delta(b, a)} |")

    before_cases = case_map(before)
    after_cases = case_map(after)

    improved = []
    regressed = []

    for case_id, before_case in before_cases.items():
        after_case = after_cases.get(case_id)
        if after_case is None:
            continue

        if not before_case.get("passed") and after_case.get("passed"):
            improved.append(after_case)
        elif before_case.get("passed") and not after_case.get("passed"):
            regressed.append(after_case)

    print("\n## Case Flips\n")
    print(f"- improved: {len(improved)}")
    for item in improved:
        print(f"  - {item['case_id']}: {item.get('query', '')}")

    print(f"- regressed: {len(regressed)}")
    for item in regressed:
        print(f"  - {item['case_id']}: {item.get('query', '')}")

    drops: list[str] = []
    for layer, names in LAYERS.items():
        for name in names:
            b = metric(before, name)
            a = metric(after, name)
            if a < b - args.tolerance:
                drops.append(f"{layer}.{name}: {fmt(b)} -> {fmt(a)}")

    print("\n## Regressions\n")
    if drops:
        for item in drops:
            print(f"- metric drop: {item}")
    else:
        print("- no metric drop")

    if args.fail_on_regression and (regressed or drops):
        print("\nRESULT: REGRESSION DETECTED", file=sys.stderr)
        return 1

    print("\nRESULT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())