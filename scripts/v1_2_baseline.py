"""V1.2 基线采集：把"现在到底是什么状态"变成一条命令 + 一份机器可读报告。

用法：
    .venv\Scripts\python.exe scripts\v1_2_baseline.py
    .venv\Scripts\python.exe scripts\v1_2_baseline.py --print
    .venv\Scripts\python.exe scripts\v1_2_baseline.py --output data/cache/reports/v1.2-baseline.json
    .venv\Scripts\python.exe scripts\v1_2_baseline.py --markdown data/cache/reports/v1.2-baseline.md

设计约束（对应第 1 批"本批不做"）：
1. 只读采集，不修改任何文件（--output/--markdown 只写你显式给出的路径）；
2. 不联网、不启动服务、不导入重型依赖，全部靠文件系统与静态扫描；
3. 单个采集器失败不影响整体：失败项写成 error 字段，报告始终可产出；
4. 只做"事实采集 + 规则判定"，不在这里做优化或重构。

报告结构（机器可读）：
    schema_version / generated_at / repo / runtime / tracks（六类）/ defects / optimizations / summary
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

TRACK_KEYS = (
    "agent_quality",
    "performance_cost",
    "execution_state",
    "cloud_reliability",
    "security",
    "governance",
)


# ============================================================
# 基础工具
# ============================================================

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def count_matches(text: str, pattern: str, flags: int = 0) -> int:
    return len(re.findall(pattern, text, flags))


def iter_files(
    root: Path,
    pattern: str,
    skip: tuple[str, ...] = (".venv", "node_modules", "__pycache__", "_tmp", "build", "dist"),
):
    """按模式遍历文件，跳过依赖与产物目录。

    注意：过滤必须基于"相对扫描根"的路径分段，不能基于绝对路径。
    否则仓库只要检出在含 _tmp / build 的目录下（例如临时工作区），
    所有结果都会被静默过滤成 0，报告看起来"一切正常"实则完全失真。
    """
    root = Path(root)
    if not root.exists():
        return

    for path in root.rglob(pattern):
        if not path.is_file():
            continue

        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            relative_parts = path.parts

        if any(part in skip for part in relative_parts):
            continue

        yield path


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _grep_count(root: Path, relative_dirs: tuple[str, ...], pattern: str) -> int:
    total = 0
    for relative in relative_dirs:
        base = root / relative
        if not base.exists():
            continue
        for path in iter_files(base, "*.py"):
            total += count_matches(read_text(path), pattern)
    return total


# ============================================================
# 采集器：仓库与运行时
# ============================================================

def collect_repo(root: Path) -> dict[str, Any]:
    status = _git(root, "status", "--porcelain")
    return {
        "root": str(root),
        "branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "head": _git(root, "rev-parse", "--short", "HEAD"),
        "dirty_files": len([line for line in status.splitlines() if line.strip()]),
    }


def collect_runtime(root: Path) -> dict[str, Any]:
    dockerfile = read_text(root / "deploy" / "Dockerfile.api")
    compose = read_text(root / "deploy" / "docker-compose.tencent.yml")
    env_example = read_text(root / ".env.example")

    image_python = ""
    match = re.search(r"^FROM\s+(\S+)", dockerfile, re.MULTILINE)
    if match:
        image_python = match.group(1)

    workers = ""
    for text in (dockerfile, compose, env_example):
        found = re.search(r"WEB_CONCURRENCY[:=\s]+\$?\{?([0-9]+)", text)
        if found:
            workers = found.group(1)
            break

    return {
        "python_local": ".".join(str(part) for part in sys.version_info[:3]),
        "python_image": image_python,
        "workers": int(workers) if workers.isdigit() else None,
        "image_runs_as_root": bool(dockerfile) and "USER " not in dockerfile,
        "dockerfile_present": bool(dockerfile),
    }


# ============================================================
# 采集器：六类主线
# ============================================================

def collect_agent_quality(root: Path) -> dict[str, Any]:
    tests_dir = root / "tests"
    test_functions: dict[str, int] = {}
    for group in ("unit", "api", "smoke", "rag"):
        base = tests_dir / group
        test_functions[group] = (
            sum(
                count_matches(read_text(path), r"^def test_", re.MULTILINE)
                for path in iter_files(base, "*.py")
            )
            if base.exists()
            else 0
        )

    cases_file = tests_dir / "fixtures" / "rag_eval" / "cases.jsonl"
    rag_cases = len([line for line in read_text(cases_file).splitlines() if line.strip()])

    baseline_test = read_text(tests_dir / "rag" / "test_rag_quality_baseline.py")
    thresholds = {
        name: float(value)
        for name, value in re.findall(
            r"summary\.(pass_rate|recall_at_1|recall_at_3|mrr)\s*>=\s*([0-9.]+)",
            baseline_test,
        )
    }

    fixtures = tests_dir / "fixtures"
    fixture_groups = sorted(item.name for item in fixtures.iterdir() if item.is_dir()) if fixtures.exists() else []

    gaps: list[str] = []
    if rag_cases == 0:
        gaps.append("RAG 评测集为空")
    if not thresholds:
        gaps.append("RAG 基线缺少阈值断言")
    for name, label in (("memory", "Memory"), ("vision", "Vision"), ("persona", "Persona/主聊天")):
        if name not in fixture_groups:
            gaps.append(f"{label} 没有独立评测 fixture 目录")
    if count_matches(baseline_test, r"grounded|faithful|answer_level") == 0:
        gaps.append("缺少答案级指标（groundedness / 引用可追溯 / 拒答）")

    scripts_dir = root / "scripts"
    return {
        "test_functions": test_functions,
        "test_functions_total": sum(test_functions.values()),
        "rag_eval_cases": rag_cases,
        "rag_thresholds": thresholds,
        "fixture_groups": fixture_groups,
        "eval_entry_scripts": sorted(path.name for path in scripts_dir.glob("*rag*") if path.is_file())
        if scripts_dir.exists()
        else [],
        "gaps": gaps,
    }


def collect_performance_cost(root: Path) -> dict[str, Any]:
    latency_hits = _grep_count(root, ("aiagent", "apps"), r"_latency_ms")
    timeout_fields = _grep_count(root, ("config",), r"timeout_seconds")

    scripts_dir = root / "scripts"
    benchmark_scripts = sorted(path.name for path in scripts_dir.glob("*bench*")) if scripts_dir.exists() else []

    gaps: list[str] = []
    if not benchmark_scripts:
        gaps.append("没有可重复的性能基准脚本")
    if _grep_count(root, ("aiagent",), r"token_usage|cost_") == 0:
        gaps.append("没有 Token/成本代理指标采集")

    return {
        "stage_latency_metadata_hits": latency_hits,
        "timeout_settings": timeout_fields,
        "benchmark_scripts": benchmark_scripts,
        "gaps": gaps,
    }


def collect_execution_state(root: Path) -> dict[str, Any]:
    in_memory_saver = _grep_count(root, ("aiagent",), r"InMemorySaver")
    module_level_caches = _grep_count(root, ("aiagent", "apps"), r"^_[a-z_]+: dict\[|^_[a-z_]+ = \{\}")
    instance_cache_hits = _grep_count(root, ("aiagent",), r"self\._[a-z_]+_cache")
    process_local_metrics = count_matches(read_text(root / "apps" / "api" / "metrics_store.py"), r"deque\(")

    shared_modules = {
        name: (root / relative).exists()
        for name, relative in (
            ("shared_store", "aiagent/state/shared_store.py"),
            ("thread_registry", "aiagent/graphs/thread_registry.py"),
            ("thread_state_mirror", "aiagent/graphs/thread_state_mirror.py"),
        )
    }

    llm_graph = read_text(root / "aiagent" / "graphs" / "llm_graph.py")
    injection_wired = "thread_registry" in llm_graph and "checkpointer" in llm_graph

    runtime = collect_runtime(root)
    multi_worker = bool(runtime.get("workers") and int(runtime["workers"]) > 1)

    gaps: list[str] = []
    if multi_worker and not all(shared_modules.values()):
        gaps.append("多 Worker 部署但缺少共享状态模块")
    if multi_worker and not injection_wired:
        gaps.append("LLM 线程仍使用进程内 checkpointer 且未接入共享注册表")
    if instance_cache_hits:
        gaps.append(f"仍有 {instance_cache_hits} 处实例级进程内缓存（persona/线程映射等）需评估是否共享")
    if process_local_metrics:
        gaps.append("指标为进程内 deque，多 Worker 下每进程各算一份")

    return {
        "workers": runtime.get("workers"),
        "multi_worker": multi_worker,
        "in_memory_saver_hits": in_memory_saver,
        "module_level_cache_hits": module_level_caches,
        "instance_cache_hits": instance_cache_hits,
        "process_local_metric_deques": process_local_metrics,
        "shared_state_modules": shared_modules,
        "llm_injection_wired": injection_wired,
        "gaps": gaps,
    }


def collect_cloud_reliability(root: Path) -> dict[str, Any]:
    readiness = read_text(root / "cloud" / "readiness.py")
    failure_policy = read_text(root / "cloud" / "failure_policy.py")
    task_queue = read_text(root / "cloud" / "task_queue.py")

    return {
        "readiness_checks": sorted(set(re.findall(r'name="([a-z_]+)"', readiness))),
        "readiness_has_purpose": "purpose" in readiness,
        "readiness_has_redaction": "redact_snapshot" in readiness,
        "failure_policy_entries": count_matches(failure_policy, r"RedisDependency\.[A-Z_]+:"),
        "task_queue_features": {
            "request_id": "request_id" in task_queue,
            "first_started_at": "first_started_at" in task_queue,
            "dead_letter": "dead_reason" in task_queue,
            "stale_recovery": "recover_stale_running" in task_queue,
            "retry": "fail_or_retry" in task_queue,
        },
        "gaps": [],
    }


def collect_security(root: Path) -> dict[str, Any]:
    log_safety = read_text(root / "aiagent" / "common" / "log_safety.py")
    image_store = read_text(root / "aiagent" / "vision" / "image_store.py")
    ops_snapshot = read_text(root / "cloud" / "ops_snapshot.py")
    admin_auth = read_text(root / "cloud" / "admin_auth.py")

    features = {
        "log_redaction_patterns": count_matches(log_safety, r"re\.compile\("),
        "bearer_redaction": "Bearer" in log_safety,
        "base64_redaction": "base64" in log_safety,
        "request_risk_gate": (root / "aiagent" / "persona" / "request_risk.py").exists(),
        "safety_models": (root / "aiagent" / "schemas" / "safety.py").exists(),
        "upload_pixel_limit": "max_pixels" in image_store,
        "upload_magic_bytes": "sniff_image_format" in image_store,
        "cors_risk_check": "cors_loopback_origins_in_cloud_mode" in ops_snapshot,
        "admin_token_strength": "strong" in admin_auth,
    }

    return {
        "features": features,
        "gaps": [name for name, ok in features.items() if not ok],
    }


def _pyproject_dependencies(root: Path) -> list[str]:
    """精确读取 [project].dependencies 与 optional-dependencies。

    不能用"匹配所有引号开头的行"来数依赖：ruff 的 exclude/select 列表
    同样以引号开头，会把工具配置误算成运行依赖。
    """
    path = root / "pyproject.toml"
    if not path.exists():
        return []

    try:
        import tomllib

        data = tomllib.loads(read_text(path))
    except Exception:
        return []

    project = data.get("project") or {}
    entries: list[str] = list(project.get("dependencies") or [])
    for group in (project.get("optional-dependencies") or {}).values():
        entries.extend(group or [])

    names: list[str] = []
    for entry in entries:
        match = re.match(r"^\s*([A-Za-z0-9_.\-]+)", str(entry))
        if match:
            names.append(match.group(1).lower())
    return names


def collect_governance(root: Path) -> dict[str, Any]:
    workflows = list(iter_files(root / ".github", "*.yml")) + list(iter_files(root / ".github", "*.yaml"))
    requirements = [
        line for line in read_text(root / "requirements.txt").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    declared = _pyproject_dependencies(root)
    pinned = [line for line in requirements if "==" in line]

    gitignore = read_text(root / ".gitignore")
    dockerfile = read_text(root / "deploy" / "Dockerfile.api")
    scripts_dir = root / "scripts"

    return {
        "ci_workflows": sorted(path.name for path in workflows),
        "dependency_sources": {
            "pyproject": (root / "pyproject.toml").exists(),
            "requirements_txt": bool(requirements),
            "uv_lock": (root / "uv.lock").exists(),
            "requirements_entries": len(requirements),
            "requirements_pinned": len(pinned),
            "pyproject_declared": len(declared),
            "declares_web_framework": any(name in {"fastapi", "uvicorn"} for name in declared),
        },
        "container": {
            "non_root": "USER " in dockerfile,
            "python_image": (
                re.search(r"^FROM\s+(\S+)", dockerfile, re.MULTILINE).group(1) # type: ignore
                if dockerfile and re.search(r"^FROM\s+(\S+)", dockerfile, re.MULTILINE)
                else ""
            ),
        },
        "ignore_rules": {
            "ignores_frontend": "apps/flutter_client" in gitignore,
            "ignores_knowledge_docs": "data/knowledge" in gitignore,
        },
        "checks_present": {
            "config_sync": (scripts_dir / "check_config_sync.py").exists(),
            "repo_hygiene": (scripts_dir / "check_repo_hygiene.py").exists(),
            "test_all": (scripts_dir / "test_all.ps1").exists(),
        },
        "gaps": [],
    }


# ============================================================
# 判定：缺陷（已存在）vs 优化项
# ============================================================

def build_defects(report: dict[str, Any]) -> list[dict[str, Any]]:
    tracks = report["tracks"]
    runtime = report["runtime"]
    execution = tracks["execution_state"]
    governance = tracks["governance"]
    agent_quality = tracks["agent_quality"]
    deps = governance["dependency_sources"]

    defects: list[dict[str, Any]] = []

    if execution["multi_worker"] and not execution["llm_injection_wired"]:
        defects.append(
            {
                "id": "multi_worker_thread_state_split",
                "severity": "P0",
                "batch": 2,
                "title": "多 Worker 下 LLM 线程状态仍是进程内，短期记忆会断裂",
                "evidence": {
                    "workers": execution["workers"],
                    "in_memory_saver_hits": execution["in_memory_saver_hits"],
                },
            }
        )

    if execution["process_local_metric_deques"]:
        defects.append(
            {
                "id": "metrics_process_local",
                "severity": "P1",
                "batch": 2,
                "title": "指标为进程内 deque，多 Worker 下面板只看到部分流量",
                "evidence": {"deques": execution["process_local_metric_deques"]},
            }
        )

    if not governance["ci_workflows"]:
        defects.append(
            {
                "id": "no_ci_gate",
                "severity": "P0",
                "batch": 3,
                "title": "没有任何 CI 流水线，测试与检查无法自动执行",
                "evidence": {"workflows": governance["ci_workflows"]},
            }
        )

    if deps["requirements_txt"] and deps["requirements_pinned"] == 0:
        defects.append(
            {
                "id": "dependencies_unpinned",
                "severity": "P1",
                "batch": 3,
                "title": "requirements.txt 完全未锁定版本，且与 pyproject/uv.lock 并存",
                "evidence": deps,
            }
        )

    if not deps["declares_web_framework"]:
        defects.append(
            {
                "id": "pyproject_missing_web_deps",
                "severity": "P1",
                "batch": 3,
                "title": "pyproject.toml 未声明 Web 框架依赖，包元数据与实际运行不符",
                "evidence": {"declared": deps["pyproject_declared"]},
            }
        )

    if runtime.get("image_runs_as_root"):
        defects.append(
            {
                "id": "image_runs_as_root",
                "severity": "P1",
                "batch": 3,
                "title": "生产镜像以 root 运行",
                "evidence": {"image_python": runtime.get("python_image")},
            }
        )

    image_python = str(runtime.get("python_image") or "")
    if image_python:
        local_minor = ".".join(str(part) for part in sys.version_info[:2])
        if local_minor not in image_python:
            defects.append(
                {
                    "id": "python_version_drift",
                    "severity": "P2",
                    "batch": 3,
                    "title": "本地解释器版本与镜像基础镜像不一致",
                    "evidence": {"local": runtime["python_local"], "image": image_python},
                }
            )

    if any("答案级" in gap for gap in agent_quality["gaps"]):
        defects.append(
            {
                "id": "no_answer_level_metric",
                "severity": "P1",
                "batch": 4,
                "title": "只有检索级指标，缺少答案级判定（是否被内容支撑、是否该拒答）",
                "evidence": {"rag_cases": agent_quality["rag_eval_cases"]},
            }
        )

    return defects


def build_optimizations(report: dict[str, Any]) -> list[dict[str, Any]]:
    tracks = report["tracks"]
    items: list[dict[str, Any]] = []

    for gap in tracks["agent_quality"]["gaps"]:
        items.append({"area": "agent_quality", "batch": 4, "item": gap})
    for gap in tracks["performance_cost"]["gaps"]:
        items.append({"area": "performance_cost", "batch": 5, "item": gap})
    for gap in tracks["security"]["gaps"]:
        items.append({"area": "security", "batch": 7, "item": gap})
    for gap in tracks["execution_state"]["gaps"]:
        if "指标为进程内" not in gap:
            items.append({"area": "execution_state", "batch": 2, "item": gap})

    return items


# ============================================================
# 报告组装
# ============================================================

def build_report(root: Path | str = PROJECT_ROOT) -> dict[str, Any]:
    root_path = Path(root).resolve()

    tracks: dict[str, Any] = {}
    for key, collector in (
        ("agent_quality", collect_agent_quality),
        ("performance_cost", collect_performance_cost),
        ("execution_state", collect_execution_state),
        ("cloud_reliability", collect_cloud_reliability),
        ("security", collect_security),
        ("governance", collect_governance),
    ):
        try:
            tracks[key] = collector(root_path)
        except Exception as exc:
            tracks[key] = {"error": f"{type(exc).__name__}: {exc}", "gaps": ["采集失败"]}

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": collect_repo(root_path),
        "runtime": collect_runtime(root_path),
        "tracks": tracks,
    }

    defects = build_defects(report)
    optimizations = build_optimizations(report)
    report["defects"] = defects
    report["optimizations"] = optimizations
    report["summary"] = {
        "tracks": len(TRACK_KEYS),
        "test_functions_total": tracks.get("agent_quality", {}).get("test_functions_total", 0),
        "defects": len(defects),
        "defects_p0": len([item for item in defects if item["severity"] == "P0"]),
        "optimizations": len(optimizations),
        "prerequisite_batches": sorted({item["batch"] for item in defects if item["severity"] == "P0"}),
    }
    return report


def render_markdown(report: dict[str, Any]) -> str:
    """渲染人工可读摘要。

    这里刻意用字符串拼接而不是 f-string 嵌套引号，避免在 md 表格里
    出现难以阅读的转义；输出只包含事实与结论，不写主观评价。
    """
    runtime = report["runtime"]
    tracks = report["tracks"]

    lines: list[str] = [
        "# V1.2 基线报告",
        "",
        "> 本文件由 scripts/v1_2_baseline.py --markdown 生成，可重复覆盖。",
        "> 生成时间：" + str(report["generated_at"]),
        "> 采集版本：schema " + str(report["schema_version"])
        + "｜提交 " + str(report["repo"]["head"])
        + "｜分支 " + str(report["repo"]["branch"]),
        "",
        "## 一、运行时与部署基线",
        "",
        "| 项 | 值 |",
        "| --- | --- |",
        "| 本机 Python | " + str(runtime["python_local"]) + " |",
        "| 镜像基础镜像 | " + (str(runtime["python_image"]) or "未知") + " |",
        "| 生产默认 Worker 数 | " + str(runtime["workers"]) + " |",
        "| 镜像是否 root 运行 | " + ("是" if runtime["image_runs_as_root"] else "否") + " |",
        "| 未提交文件数 | " + str(report["repo"]["dirty_files"]) + " |",
        "",
        "## 二、六类主线现状",
        "",
    ]

    for key in TRACK_KEYS:
        track = tracks.get(key, {})
        lines.append("### " + key)
        lines.append("")
        if "error" in track:
            lines.append("- 采集失败：" + str(track["error"]))
        else:
            for name, value in track.items():
                if name == "gaps":
                    continue
                lines.append("- " + name + ": " + json.dumps(value, ensure_ascii=False))
        for gap in track.get("gaps") or []:
            lines.append("- 缺口：" + gap)
        lines.append("")

    lines.extend(["## 三、已存在缺陷（与优化项分离）", ""])
    if report["defects"]:
        lines.append("| ID | 级别 | 批次 | 说明 |")
        lines.append("| --- | --- | --- | --- |")
        for item in report["defects"]:
            lines.append(
                "| " + item["id"] + " | " + item["severity"] + " | 第 "
                + str(item["batch"]) + " 批 | " + item["title"] + " |"
            )
    else:
        lines.append("当前未检出结构性缺陷。")
    lines.append("")

    lines.extend(["## 四、优化项（非缺陷）", ""])
    if report["optimizations"]:
        for item in report["optimizations"]:
            lines.append("- [第 " + str(item["batch"]) + " 批][" + item["area"] + "] " + item["item"])
    else:
        lines.append("无。")
    lines.append("")

    lines.extend(
        [
            "## 五、本版本非目标",
            "",
            "- Flutter、Qt、Web 控制台与其它前端分支。",
            "- 将 API / RAG / Memory / Runtime 整体重写为 Rust。",
            "- 在威胁模型完成前预设必须开发某一种 Rust 安全工具。",
            "- 新增第二套 RAG / Memory / 多 Agent 架构或缺少质量基线的新 Provider。",
            "",
        ]
    )

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V1.2 基线采集")
    parser.add_argument("--root", default=str(PROJECT_ROOT), help="仓库根目录")
    parser.add_argument("--output", default="", help="JSON 报告输出路径")
    parser.add_argument("--markdown", default="", help="同时生成 Markdown 摘要")
    parser.add_argument("--print", dest="print_report", action="store_true", help="打印 JSON 报告")
    args = parser.parse_args(argv)

    report = build_report(args.root)

    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[baseline] JSON 报告已写入 " + str(target))

    if args.markdown:
        target = Path(args.markdown)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_markdown(report), encoding="utf-8")
        print("[baseline] Markdown 已写入 " + str(target))

    if args.print_report or not (args.output or args.markdown):
        print(json.dumps(report, ensure_ascii=False, indent=2))

    summary = report["summary"]
    print(
        "[baseline] 测试函数 " + str(summary["test_functions_total"])
        + "｜缺陷 " + str(summary["defects"]) + "（P0 " + str(summary["defects_p0"]) + "）"
        + "｜优化项 " + str(summary["optimizations"])
        + "｜前置批次 " + str(summary["prerequisite_batches"])
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())