"""配置三方一致性检查。

真源：config/settings.py 的 Settings、cloud/config.py 的 CloudSettings，
     外加 worker / 部署脚本里直接 os.getenv / $env: / ${VAR} 的变量。

比对方：.env.example、cloud.tencent.example.env、docs/config-reference.md

用法：
    .venv\\Scripts\\python.exe scripts\\check_config_sync.py
    .venv\\Scripts\\python.exe scripts\\check_config_sync.py --strict
    .venv\\Scripts\\python.exe scripts\\check_config_sync.py --report-env-example   # 打印可直接粘贴的缺失项

退出码：0 = 无缺失；1 = 存在缺失（--strict 时多余项也算失败）。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
CLOUD_ENV_EXAMPLE = PROJECT_ROOT / "cloud.tencent.example.env"
CONFIG_REFERENCE = PROJECT_ROOT / "docs" / "config-reference.md"

# Settings 之外、由代码直接读取的环境变量（新增时在此登记）
EXTRA_ENV_SOURCES = {
    "LOG_LEVEL": "apps/worker/main.py",
    "TASK_QUEUE_NAME": "apps/worker/main.py",
    "TASK_POP_TIMEOUT_SECONDS": "apps/worker/main.py",
    "TASK_STALE_SECONDS": "apps/worker/main.py",
    "WORKER_CONCURRENCY": "apps/worker/main.py",
    "WEB_CONCURRENCY": "deploy/Dockerfile.api",
    "GPU_API_TOKEN": "cloud/gpu_client.py",
    "POSTGRES_PASSWORD": "deploy/docker-compose.tencent.yml",
    "AIAGENT_API_BASE_URL": "apps/desktop_qt",
    "AIAGENT_API_TIMEOUT": "apps/desktop_qt",
    "AIAGENT_DESKTOP_USER_ID": "apps/desktop_qt",
    "AIAGENT_DESKTOP_USERNAME": "apps/desktop_qt",
    "AIAGENT_LIVE2D_MODEL3": "apps/desktop_qt",
}

# 系统级/第三方环境变量，不属于本项目的配置面，检查时忽略
SYSTEM_ENV_IGNORE = {
    "NO_PROXY", "no_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "PYTHONPATH", "PYTHONIOENCODING", "PYTHONUNBUFFERED",
    "PATH", "HOME", "TZ", "LANG", "TMPDIR", "CUDA_VISIBLE_DEVICES",
}

ENV_LINE_PATTERN = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]{2,})\s*=")
DOC_TOKEN_PATTERN = re.compile(r"`([A-Z][A-Z0-9_]{2,})`")
GETENV_PATTERN = re.compile(r"""os\.(?:getenv|environ\.get)\(\s*["']([A-Z][A-Z0-9_]{2,})["']""")
POWERSHELL_ENV_PATTERN = re.compile(r"\$env:([A-Z][A-Z0-9_]{2,})")
COMPOSE_ENV_PATTERN = re.compile(r"\$\{([A-Z][A-Z0-9_]{2,})")


def _env_name(field_name: str, field_info) -> str:
    alias = getattr(field_info, "alias", None)
    if isinstance(alias, str) and alias.strip():
        return alias.strip()
    return field_name.upper()


def collect_settings_env() -> dict[str, str]:
    """返回 {环境变量名: 来源说明}。"""
    from config.settings import Settings
    from cloud.config import CloudSettings

    mapping: dict[str, str] = {}
    for model, label in ((Settings, "config/settings.py"), (CloudSettings, "cloud/config.py")):
        for field_name, field_info in model.model_fields.items():
            mapping[_env_name(field_name, field_info)] = f"{label}:{field_name}"
    mapping.update(EXTRA_ENV_SOURCES)
    return mapping


def collect_scanned_env() -> dict[str, str]:
    """从源码里正则扫描直接读取的环境变量，作为兜底发现机制。"""
    found: dict[str, str] = {}
    for path in PROJECT_ROOT.rglob("*.py"):
        if any(part in {".venv", "__pycache__", "node_modules", "_tmp"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in GETENV_PATTERN.finditer(text):
            found.setdefault(match.group(1), path.relative_to(PROJECT_ROOT).as_posix())

    for path in PROJECT_ROOT.rglob("*.ps1"):
        if any(part in {".venv", "_tmp"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in POWERSHELL_ENV_PATTERN.finditer(text):
            found.setdefault(match.group(1), path.relative_to(PROJECT_ROOT).as_posix())

    for pattern in ("*.yml", "*.yaml"):
        for path in PROJECT_ROOT.rglob(pattern):
            if any(part in {".venv", "_tmp", "node_modules"} for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for match in COMPOSE_ENV_PATTERN.finditer(text):
                found.setdefault(match.group(1), path.relative_to(PROJECT_ROOT).as_posix())

    return found


def parse_env_file(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = ENV_LINE_PATTERN.match(line)
        if match:
            keys.add(match.group(1))
    return keys


def parse_doc_reference(path: Path) -> set[str]:
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8", errors="ignore")
    keys = set(DOC_TOKEN_PATTERN.findall(text))
    for line in text.splitlines():
        match = ENV_LINE_PATTERN.match(line)
        if match:
            keys.add(match.group(1))
    return keys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="配置三方一致性检查")
    parser.add_argument("--strict", action="store_true", help="多余项也视为失败")
    parser.add_argument(
        "--report-env-example",
        action="store_true",
        help="打印可直接追加到 .env.example 的缺失项",
    )
    args = parser.parse_args(argv)

    declared = collect_settings_env()
    scanned = collect_scanned_env()
    for name, source in scanned.items():
        declared.setdefault(name, f"scanned:{source}")

    # 系统级环境变量不参与本项目配置面的一致性检查
    for name in SYSTEM_ENV_IGNORE:
        declared.pop(name, None)

    env_example_keys = parse_env_file(ENV_EXAMPLE)
    cloud_example_keys = parse_env_file(CLOUD_ENV_EXAMPLE)
    doc_keys = parse_doc_reference(CONFIG_REFERENCE)

    missing_in_env_example = sorted(name for name in declared if name not in env_example_keys)
    missing_in_docs = sorted(name for name in declared if name not in doc_keys)
    stale_in_env_example = sorted(
        name
        for name in env_example_keys
        if name not in declared and name not in cloud_example_keys
    )

    print(f"[config-sync] 声明项 {len(declared)} 个")
    print(f"[config-sync] .env.example {len(env_example_keys)} 项 / cloud.tencent.example.env {len(cloud_example_keys)} 项 / config-reference.md {len(doc_keys)} 项")

    for title, items, show_source in (
        (".env.example 缺失", missing_in_env_example, True),
        ("docs/config-reference.md 缺失", missing_in_docs, True),
        (".env.example 可能多余（源码未声明）", stale_in_env_example, False),
    ):
        if not items:
            continue
        print(f"\n[{title}] 共 {len(items)} 项：")
        for name in items:
            source = f"  <- {declared.get(name, '')}" if show_source else ""
            print(f"  - {name}{source}")

    if args.report_env_example and missing_in_env_example:
        print("\n# 可直接追加到 .env.example：")
        for name in missing_in_env_example:
            print(f"{name}=")

    failed = bool(missing_in_env_example or missing_in_docs)
    if args.strict and stale_in_env_example:
        failed = True

    if not failed and not stale_in_env_example:
        print("\n[config-sync] OK：源码、.env.example 与配置文档一致。")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())