from __future__ import annotations

import importlib.util
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "v1_2_baseline.py"

spec = importlib.util.spec_from_file_location("v1_2_baseline", SCRIPT_PATH)
baseline = importlib.util.module_from_spec(spec) # type: ignore
spec.loader.exec_module(baseline)  # type: ignore[union-attr]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_repo(root: Path, *, with_ci: bool = True, with_shared_state: bool = True) -> Path:
    """构造一个最小但"结构完整"的合成仓库，用于验证采集规则。"""
    _write(root / "pyproject.toml", '[project]\nname = "demo"\ndependencies = ["fastapi", "uvicorn"]\n')
    _write(root / "requirements.txt", "fastapi==0.115.0\nuvicorn==0.30.0\n")
    _write(root / "uv.lock", "# lock\n")
    _write(root / ".env.example", "WEB_CONCURRENCY=2\n")
    _write(root / ".gitignore", "apps/flutter_client\ndata/knowledge\n")
    _write(root / "deploy" / "Dockerfile.api", "FROM python:3.11-slim\nUSER app\n")
    _write(
        root / "deploy" / "docker-compose.tencent.yml",
        "services:\n  api:\n    environment:\n      WEB_CONCURRENCY: 2\n",
    )
    _write(root / "tests" / "unit" / "test_a.py", "def test_one():\n    assert True\n\ndef test_two():\n    assert True\n")
    _write(root / "tests" / "fixtures" / "rag_eval" / "cases.jsonl", '{"case_id":"a"}\n{"case_id":"b"}\n')
    _write(
        root / "tests" / "rag" / "test_rag_quality_baseline.py",
        "def test_x():\n    assert summary.pass_rate >= 0.95\n    assert summary.recall_at_1 >= 0.78\n",
    )
    _write(root / "aiagent" / "graphs" / "llm_graph.py", "checkpointer = thread_registry = None\n")
    _write(root / "cloud" / "readiness.py", 'name = "redis"\npurpose = "ops"\nredact_snapshot = 1\n')
    _write(root / "cloud" / "failure_policy.py", "REDIS_FAILURE_POLICY = {RedisDependency.RATE_LIMIT: 1}\n")
    _write(
        root / "cloud" / "task_queue.py",
        "request_id = first_started_at = dead_reason = recover_stale_running = fail_or_retry = 1\n",
    )
    _write(root / "cloud" / "ops_snapshot.py", "cors_loopback_origins_in_cloud_mode = 1\n")
    _write(root / "cloud" / "admin_auth.py", "strong = True\n")
    _write(root / "aiagent" / "common" / "log_safety.py", "Bearer = 1  # base64\nimport re\nre.compile('x')\n")
    _write(root / "aiagent" / "vision" / "image_store.py", "max_pixels = 1\ndef sniff_image_format(): ...\n")
    _write(root / "aiagent" / "persona" / "request_risk.py", "def assess_request_risk(): ...\n")
    _write(root / "aiagent" / "schemas" / "safety.py", "class RiskLevel: ...\n")
    _write(root / "apps" / "api" / "metrics_store.py", "deque(maxlen=10)\n")
    _write(root / "scripts" / "check_config_sync.py", "# x\n")
    _write(root / "scripts" / "check_repo_hygiene.py", "# x\n")
    _write(root / "scripts" / "test_all.ps1", "# x\n")

    if with_ci:
        _write(root / ".github" / "workflows" / "backend.yml", "name: backend\n")

    if with_shared_state:
        _write(root / "aiagent" / "state" / "shared_store.py", "class SharedStore: ...\n")
        _write(root / "aiagent" / "graphs" / "thread_registry.py", "class ThreadRegistry: ...\n")
        _write(root / "aiagent" / "graphs" / "thread_state_mirror.py", "class MirroredThreadSaver: ...\n")

    return root


def test_baseline_collects_repo_facts(tmp_path):
    repo = _make_repo(tmp_path)

    report = baseline.build_report(repo)

    assert report["schema_version"] == baseline.SCHEMA_VERSION

    # fixture 结构：tests/unit 两个测试函数 + tests/rag 一个（含阈值断言）
    assert report["tracks"]["agent_quality"]["test_functions"]["unit"] == 2
    assert report["tracks"]["agent_quality"]["test_functions"]["rag"] == 1
    assert report["tracks"]["agent_quality"]["test_functions_total"] == 3

    assert report["tracks"]["agent_quality"]["rag_eval_cases"] == 2
    assert report["tracks"]["agent_quality"]["rag_thresholds"]["pass_rate"] == 0.95
    assert report["runtime"]["workers"] == 2
    assert report["runtime"]["image_runs_as_root"] is False
    assert report["tracks"]["governance"]["dependency_sources"]["requirements_pinned"] == 2
    assert report["tracks"]["governance"]["dependency_sources"]["declares_web_framework"] is True
    assert report["tracks"]["governance"]["ci_workflows"] == ["backend.yml"]
    json.dumps(report)  # 报告必须可 JSON 序列化


def test_baseline_flags_missing_ci_and_shared_state(tmp_path):
    repo = _make_repo(tmp_path, with_ci=False, with_shared_state=False)
    # 去掉共享状态接线，模拟"第 2 批尚未落地"
    _write(repo / "aiagent" / "graphs" / "llm_graph.py", "checkpointer = None\n")

    report = baseline.build_report(repo)
    ids = {item["id"] for item in report["defects"]}

    assert "no_ci_gate" in ids
    assert "multi_worker_thread_state_split" in ids
    assert "metrics_process_local" in ids

    p0_batches = report["summary"]["prerequisite_batches"]
    assert 2 in p0_batches and 3 in p0_batches


def test_baseline_reports_unpinned_dependencies(tmp_path):
    repo = _make_repo(tmp_path)
    _write(repo / "requirements.txt", "fastapi\nuvicorn\n")

    report = baseline.build_report(repo)
    ids = {item["id"] for item in report["defects"]}

    assert "dependencies_unpinned" in ids


def test_markdown_render_contains_required_sections(tmp_path):
    repo = _make_repo(tmp_path)

    markdown = baseline.render_markdown(baseline.build_report(repo))

    for heading in (
        "# V1.2 基线报告",
        "## 一、运行时与部署基线",
        "## 二、六类主线现状",
        "## 三、已存在缺陷",
        "## 四、优化项",
        "## 五、本版本非目标",
    ):
        assert heading in markdown


def test_collector_failure_does_not_break_report(monkeypatch, tmp_path):
    repo = _make_repo(tmp_path)

    def _boom(root):
        raise RuntimeError("collector exploded")

    monkeypatch.setattr(baseline, "collect_security", _boom)
    report = baseline.build_report(repo)

    assert "error" in report["tracks"]["security"]
    assert report["summary"]["tracks"] == len(baseline.TRACK_KEYS)

def test_all_regex_patterns_compile():
    """守卫：脚本里每个正则字面量都必须能编译。

    交付或复制这类脚本时，反斜杠很容易被多转义一层：
    例如把 \\s 写成 \\\\s，或在 $ 前多一个反斜杠，
    re 会报 "nothing to repeat" 这类与真实原因无关的错误，很难从堆栈看出是转义问题。
    本测试用 AST 找出所有正则字面量并逐个 compile，失败时直接给出行号、模式与原因。
    """
    import ast
    import re

    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    regex_methods = {"compile", "search", "match", "findall", "finditer", "sub", "split"}
    patterns: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "attr", "") not in regex_methods or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            patterns.append((node.lineno, first.value))

    assert patterns, "没有扫描到任何正则字面量，守卫测试可能已失效"

    failures: list[str] = []
    for lineno, pattern in patterns:
        try:
            re.compile(pattern)
        except re.error as exc:
            failures.append("第 " + str(lineno) + " 行无法编译：" + repr(pattern) + " -> " + str(exc))

    assert not failures, "正则字面量存在转义错误：" + chr(10) + (chr(10).join(failures))