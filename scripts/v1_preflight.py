# scripts/v1_preflight.py
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

ENV_RE = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*(.*)\s*$")
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

PLACEHOLDER_MARKERS = (
    "change-",
    "your-",
    "replace-",
    "replace_with",
    "example.com",
    "todo",
    "xxx",
)

EXACT_PLACEHOLDERS = {
    "",
    "changeme",
    "change-me",
    "change-this-admin-token",
    "change-me-postgres-password",
    "change-me-neo4j-password",
    "change-me-before-production",
    "change-me-only-if-using-local-compose",
    "your-api-key",
    "your-secret-id",
    "your-secret-key",
    "your-bucket-name",
    "your-gpu-service-token",
    "your-asr-api-key",
    "replace-with-production-admin-token",
}

LOCAL_MOCK_EXPECTED = {
    "CLOUD_MODE": "false",
    "LLM_PROVIDER": "mock",
    "ENABLE_MOCK_LLM": "true",
    "TTS_PROVIDER": "mock",
    "ENABLE_MOCK_TTS": "true",
    "ASR_PROVIDER": "mock",
    "ENABLE_MOCK_ASR": "true",
    "VISION_PROVIDER": "mock",
    "LIVE2D_PROVIDER": "mock",
}

CLOUD_EXPECTED = {
    "CLOUD_MODE": "true",
    "RATE_LIMIT_ENABLED": "true",
    "INFLIGHT_LIMIT_ENABLED": "true",
    "LIMITER_FAIL_OPEN": "false",
}

SENSITIVE_KEYS = {
    "CLOUD_ADMIN_TOKEN",
    "POSTGRES_PASSWORD",
    "NEO4J_PASSWORD",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "GPU_API_TOKEN",
    "OPENAI_API_KEY",
    "SILICONFLOW_API",
    "ASR_API_KEY",
}


@dataclass(frozen=True)
class Issue:
    severity: str
    check: str
    path: str
    message: str
    action: str = ""

    def render(self) -> str:
        suffix = f" 建议：{self.action}" if self.action else ""
        return f"[{self.severity.upper()}] {self.check} {self.path}: {self.message}{suffix}"


@dataclass
class ParsedEnv:
    path: Path
    values: dict[str, str]
    lines: dict[str, int]
    duplicates: list[tuple[str, int]]
    malformed: list[tuple[int, str]]


def clean_value(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    return value


def parse_env_file(path: Path) -> ParsedEnv:
    values: dict[str, str] = {}
    lines: dict[str, int] = {}
    duplicates: list[tuple[str, int]] = []
    malformed: list[tuple[int, str]] = []

    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        match = ENV_RE.match(line)
        if not match:
            malformed.append((lineno, line))
            continue

        key = match.group(1)
        value = clean_value(match.group(2))

        if key in values:
            duplicates.append((key, lineno))

        values[key] = value
        lines[key] = lineno

    return ParsedEnv(
        path=path,
        values=values,
        lines=lines,
        duplicates=duplicates,
        malformed=malformed,
    )


def norm(value: object | None) -> str:
    return "" if value is None else str(value).strip()


def lower(value: object | None) -> str:
    return norm(value).lower()


def is_true(value: object | None) -> bool:
    return lower(value) in {"1", "true", "yes", "on"}


def is_false(value: object | None) -> bool:
    return lower(value) in {"0", "false", "no", "off"}


def is_placeholder(value: object | None) -> bool:
    text = lower(value)
    if text in EXACT_PLACEHOLDERS:
        return True
    return any(marker in text for marker in PLACEHOLDER_MARKERS)


def add(
    issues: list[Issue],
    severity: str,
    check: str,
    path: Path | str,
    message: str,
    action: str = "",
) -> None:
    issues.append(Issue(severity, check, str(path), message, action))


def require_file(path: Path, issues: list[Issue]) -> bool:
    if path.exists():
        return True
    add(
        issues,
        "error",
        "required_file",
        path,
        "文件不存在。",
        "补齐该文件，或同步更新 README/docs 中的引用。",
    )
    return False


def require_value(
    env: dict[str, str],
    key: str,
    path: Path,
    issues: list[Issue],
    check: str,
) -> None:
    value = env.get(key, "")
    if is_placeholder(value):
        add(
            issues,
            "error",
            check,
            path,
            f"{key} 缺失或仍是占位符。",
            f"在真实配置中替换 {key}，不要使用 change-* / your-* / 空值。",
        )


def require_referenced_secret(
    env: dict[str, str],
    ref_key: str,
    path: Path,
    issues: list[Issue],
    check: str,
) -> None:
    secret_name = norm(env.get(ref_key))
    if not secret_name:
        add(
            issues,
            "error",
            check,
            path,
            f"{ref_key} 未配置，无法知道应该读取哪个 secret。",
        )
        return

    require_value(env, secret_name, path, issues, check)


def check_env_parse_result(parsed: ParsedEnv, issues: list[Issue]) -> None:
    for key, lineno in parsed.duplicates:
        add(
            issues,
            "error",
            "env_duplicate",
            parsed.path,
            f"{key} 在第 {lineno} 行重复定义。",
            "删除重复项，避免后写值覆盖前写值造成误判。",
        )

    for lineno, line in parsed.malformed:
        add(
            issues,
            "warn",
            "env_malformed",
            parsed.path,
            f"第 {lineno} 行不是标准 KEY=value：{line}",
            "如果这是注释，请以 # 开头；如果是配置，请改为 KEY=value。",
        )


def check_expected_values(
    parsed: ParsedEnv,
    expected: dict[str, str],
    issues: list[Issue],
    check: str,
) -> None:
    for key, expected_value in expected.items():
        actual = lower(parsed.values.get(key))
        if actual != expected_value:
            add(
                issues,
                "error",
                check,
                parsed.path,
                f"{key} 期望为 {expected_value}，当前为 {actual or '<empty>'}。",
                "保持模板默认值与 V1.0.1 约定一致。",
            )


def check_docs_key_coverage(
    envs: Iterable[ParsedEnv],
    doc_path: Path,
    issues: list[Issue],
) -> None:
    if not require_file(doc_path, issues):
        return

    text = doc_path.read_text(encoding="utf-8")
    keys = sorted({key for parsed in envs for key in parsed.values})

    for key in keys:
        if key not in text:
            add(
                issues,
                "error",
                "docs_env_coverage",
                doc_path,
                f"{key} 出现在 env 示例中，但未出现在配置文档。",
                "补充 docs/config-reference.md，说明用途、默认值和影响范围。",
            )


def check_markdown_links(root: Path, issues: list[Issue]) -> None:
    sources = [root / "README.md", *sorted((root / "docs").glob("*.md"))]

    for source in sources:
        if not source.exists():
            continue

        for lineno, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
            for raw_target in LINK_RE.findall(line):
                target = raw_target.strip().strip("<>")
                if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                    continue

                target = target.split("#", 1)[0]
                if not target:
                    continue

                resolved = (source.parent / target).resolve()
                if not resolved.exists():
                    add(
                        issues,
                        "error",
                        "markdown_link",
                        source,
                        f"第 {lineno} 行链接不存在：{raw_target}",
                        "修正链接或恢复目标文档。",
                    )


def check_templates(root: Path, issues: list[Issue]) -> None:
    env_example_path = root / ".env.example"
    cloud_example_path = root / "cloud.tencent.example.env"

    if not require_file(env_example_path, issues):
        return
    if not require_file(cloud_example_path, issues):
        return

    env_example = parse_env_file(env_example_path)
    cloud_example = parse_env_file(cloud_example_path)

    check_env_parse_result(env_example, issues)
    check_env_parse_result(cloud_example, issues)

    check_expected_values(env_example, LOCAL_MOCK_EXPECTED, issues, "local_template_defaults")
    check_expected_values(cloud_example, CLOUD_EXPECTED, issues, "cloud_template_defaults")

    for removed_key in {"TASK_MAX_ATTEMPTS"}:
        if removed_key in env_example.values or removed_key in cloud_example.values:
            add(
                issues,
                "error",
                "removed_env_key",
                removed_key,
                f"{removed_key} 已不属于 V1.0.1 env 模板。",
                "删除该字段，任务重试次数由 enqueue 调用传入。",
            )

    check_docs_key_coverage(
        [env_example, cloud_example],
        root / "docs" / "config-reference.md",
        issues,
    )


def check_provider_key(
    env: dict[str, str],
    provider_key: str,
    enable_mock_key: str | None,
    path: Path,
    issues: list[Issue],
    allow_prod_mock: bool,
) -> None:
    provider = lower(env.get(provider_key))

    if enable_mock_key and is_true(env.get(enable_mock_key)):
        severity = "warn" if allow_prod_mock else "error"
        add(
            issues,
            severity,
            "production_mock_provider",
            path,
            f"{enable_mock_key}=true，生产环境仍启用 mock。",
            "真实发布前关闭 mock；如果是有意降级，请记录在 release checklist。",
        )

    if provider == "mock":
        severity = "warn" if allow_prod_mock else "error"
        add(
            issues,
            severity,
            "production_mock_provider",
            path,
            f"{provider_key}=mock，生产环境仍使用 mock provider。",
            "切换到真实 provider；如果是有意降级，请记录原因和影响范围。",
        )
        return

    if provider == "siliconflow":
        require_value(env, "SILICONFLOW_API", path, issues, "provider_secret")
        require_value(env, "SILICONFLOW_BASE_URL", path, issues, "provider_base_url")
    elif provider == "openai":
        require_value(env, "OPENAI_API_KEY", path, issues, "provider_secret")
        require_value(env, "OPENAI_BASE_URL", path, issues, "provider_base_url")
    elif provider == "lmstudio":
        require_value(env, "LMSTUDIO_BASE_URL", path, issues, "provider_base_url")
        if "127.0.0.1" in norm(env.get("LMSTUDIO_BASE_URL")):
            add(
                issues,
                "warn",
                "provider_localhost",
                path,
                f"{provider_key}=lmstudio 且 LMSTUDIO_BASE_URL 指向 127.0.0.1。",
                "云端发布时确认容器内可访问该地址。",
            )


def check_tts(env: dict[str, str], path: Path, issues: list[Issue], allow_prod_mock: bool) -> None:
    provider = lower(env.get("TTS_PROVIDER"))

    if provider == "mock" or is_true(env.get("ENABLE_MOCK_TTS")):
        severity = "warn" if allow_prod_mock else "error"
        add(
            issues,
            severity,
            "production_mock_tts",
            path,
            "生产环境 TTS 仍为 mock。",
            "切换到 gpt_sovits / indextts2 / voxcpm，或记录为有意降级。",
        )
        return

    if provider == "gpt_sovits":
        require_value(env, "GPT_SOVITS_BASE_URL", path, issues, "tts_base_url")
    elif provider == "indextts2":
        require_value(env, "INDEX_TTS2_BASE_URL", path, issues, "tts_base_url")
    elif provider == "voxcpm":
        require_value(env, "VOXCPM_BASE_URL", path, issues, "tts_base_url")
    else:
        add(issues, "warn", "tts_provider", path, f"未识别的 TTS_PROVIDER：{provider}")


def check_asr(env: dict[str, str], path: Path, issues: list[Issue], allow_prod_mock: bool) -> None:
    provider = lower(env.get("ASR_PROVIDER"))

    if provider == "mock" or is_true(env.get("ENABLE_MOCK_ASR")):
        severity = "warn" if allow_prod_mock else "error"
        add(
            issues,
            severity,
            "production_mock_asr",
            path,
            "生产环境 ASR 仍为 mock。",
            "切换到 api 或本地 ASR provider，或记录为有意降级。",
        )
        return

    if provider == "api":
        require_value(env, "ASR_API_BASE_URL", path, issues, "asr_api")
        require_value(env, "ASR_API_KEY", path, issues, "asr_api")
    else:
        if not norm(env.get("ASR_MODEL_SIZE")) and not norm(env.get("ASR_MODEL_PATH")):
            add(
                issues,
                "warn",
                "asr_local_model",
                path,
                "ASR_PROVIDER 不是 api/mock，但没有 ASR_MODEL_SIZE 或 ASR_MODEL_PATH。",
                "确认本地 ASR 初始化所需模型配置。",
            )


def check_rag(env: dict[str, str], path: Path, issues: list[Issue]) -> None:
    provider = lower(env.get("RAG_EMBEDDING_PROVIDER"))

    if provider in {"siliconflow", "openai"}:
        require_referenced_secret(env, "RAG_EMBEDDING_API_KEY_ENV", path, issues, "rag_secret")
        require_value(env, "RAG_EMBEDDING_BASE_URL", path, issues, "rag_base_url")
        if not norm(env.get("RAG_EMBEDDING_DIMENSIONS")):
            add(
                issues,
                "error",
                "rag_dimensions",
                path,
                "API embedding provider 未配置 RAG_EMBEDDING_DIMENSIONS。",
                "填入真实 embedding 维度，并确保 Qdrant collection 一致。",
            )


def check_vision(env: dict[str, str], path: Path, issues: list[Issue], allow_prod_mock: bool) -> None:
    provider = lower(env.get("VISION_PROVIDER"))

    if provider == "mock":
        severity = "warn" if allow_prod_mock else "error"
        add(
            issues,
            severity,
            "production_mock_vision",
            path,
            "生产环境 Vision 仍为 mock。",
            "切换到真实 Vision provider，或记录为有意降级。",
        )
        return

    if provider in {"siliconflow", "openai"}:
        require_value(env, "VISION_MODEL", path, issues, "vision_model")
        require_value(env, "VISION_BASE_URL", path, issues, "vision_base_url")
        require_referenced_secret(env, "VISION_API_KEY_ENV", path, issues, "vision_secret")
    elif provider == "lmstudio":
        require_value(env, "VISION_MODEL", path, issues, "vision_model")
        require_value(env, "VISION_BASE_URL", path, issues, "vision_base_url")


def check_storage(env: dict[str, str], path: Path, issues: list[Issue]) -> None:
    provider = lower(env.get("STORAGE_PROVIDER"))

    if provider in {"cos", "s3"}:
        for key in (
            "S3_ENDPOINT_URL",
            "S3_REGION",
            "S3_BUCKET",
            "S3_ACCESS_KEY_ID",
            "S3_SECRET_ACCESS_KEY",
            "S3_PUBLIC_BASE_URL",
        ):
            require_value(env, key, path, issues, "object_storage")
    elif provider == "local":
        require_value(env, "LOCAL_STORAGE_ROOT", path, issues, "local_storage")
    else:
        add(issues, "error", "storage_provider", path, f"未知 STORAGE_PROVIDER：{provider}")


def check_memory(env: dict[str, str], path: Path, issues: list[Issue]) -> None:
    if is_true(env.get("MEMORY_RESET_VECTOR_STORE")):
        add(
            issues,
            "error",
            "memory_reset",
            path,
            "生产环境 MEMORY_RESET_VECTOR_STORE=true。",
            "生产环境必须设为 false，避免启动时清空长期记忆。",
        )

    if lower(env.get("MEMORY_LLM_PROVIDER")) == "openai":
        require_referenced_secret(env, "MEMORY_LLM_API_KEY_ENV", path, issues, "memory_llm_secret")

    if lower(env.get("MEMORY_EMBEDDER_PROVIDER")) == "openai":
        require_referenced_secret(env, "MEMORY_EMBEDDER_API_KEY_ENV", path, issues, "memory_embedder_secret")

    if is_true(env.get("MEMORY_ENABLE_GRAPH")):
        require_value(env, "NEO4J_PASSWORD", path, issues, "memory_graph")


def check_production_env(
    parsed: ParsedEnv,
    issues: list[Issue],
    allow_prod_mock: bool,
) -> None:
    env = parsed.values
    path = parsed.path

    check_expected_values(parsed, CLOUD_EXPECTED, issues, "cloud_real_defaults")

    require_value(env, "CLOUD_ADMIN_TOKEN", path, issues, "cloud_admin_token")
    require_value(env, "API_PUBLIC_BASE_URL", path, issues, "api_public_url")
    require_value(env, "POSTGRES_PASSWORD", path, issues, "postgres_password")

    if "*" in norm(env.get("API_CORS_ORIGINS")):
        add(
            issues,
            "error",
            "cors",
            path,
            "生产环境 API_CORS_ORIGINS 包含 *。",
            "只保留正式域名和必要调试源。",
        )

    check_provider_key(env, "LLM_PROVIDER", "ENABLE_MOCK_LLM", path, issues, allow_prod_mock)
    check_provider_key(env, "STATE_PROVIDER", "ENABLE_MOCK_STATE", path, issues, allow_prod_mock)
    check_provider_key(env, "PLANNER_PROVIDER", "ENABLE_MOCK_PLANNER", path, issues, allow_prod_mock)

    check_tts(env, path, issues, allow_prod_mock)
    check_asr(env, path, issues, allow_prod_mock)
    check_rag(env, path, issues)
    check_vision(env, path, issues, allow_prod_mock)
    check_storage(env, path, issues)
    check_memory(env, path, issues)

    if lower(env.get("LIVE2D_PROVIDER")) == "mock":
        add(
            issues,
            "warn",
            "live2d_provider",
            path,
            "LIVE2D_PROVIDER=mock。",
            "V1.0 后端 mock 可表示仅输出 payload；确认移动端负责模型加载和动作执行。",
        )


def check_real_env_file(
    path: Path,
    issues: list[Issue],
    allow_missing: bool,
    allow_prod_mock: bool,
) -> None:
    if not path.exists():
        severity = "warn" if allow_missing else "error"
        add(
            issues,
            severity,
            "real_env_missing",
            path,
            "真实配置文件不存在。",
            "本地开发可忽略；发布前必须在目标机器补齐。",
        )
        return

    parsed = parse_env_file(path)
    check_env_parse_result(parsed, issues)

    if is_true(parsed.values.get("CLOUD_MODE")) or path.name == "cloud.tencent.env":
        check_production_env(parsed, issues, allow_prod_mock)

    for key in SENSITIVE_KEYS:
        if key in parsed.values and is_placeholder(parsed.values[key]):
            add(
                issues,
                "warn",
                "placeholder_secret",
                path,
                f"{key} 仍为空或占位符。",
                "如果这是本地 mock 环境可以忽略；发布环境必须替换。",
            )


def check_git_secret_tracking(root: Path, issues: list[Issue]) -> None:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--", ".env", "cloud.tencent.env"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        add(issues, "warn", "git_check", root, "无法执行 git ls-files。")
        return

    tracked = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    for file_name in tracked:
        add(
            issues,
            "error",
            "tracked_secret_file",
            root / file_name,
            "真实配置文件被 Git 跟踪。",
            "从版本管理中移除，仅保留 example 文件。",
        )


def print_summary(issues: list[Issue]) -> int:
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warn"]

    if not issues:
        print("OK: V1.0.1 preflight passed.")
        return 0

    for issue in issues:
        print(issue.render())

    print("")
    print(f"Summary: errors={len(errors)} warnings={len(warnings)}")

    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AIAgent V1.0.1 preflight checks.")
    parser.add_argument(
        "--mode",
        choices=("all", "templates", "docs", "real"),
        default="all",
        help="检查范围。",
    )
    parser.add_argument("--env-file", default=".env", help="真实本地 env 文件。")
    parser.add_argument("--cloud-env-file", default="cloud.tencent.env", help="真实云端 env 文件。")
    parser.add_argument(
        "--allow-missing-real-env",
        action="store_true",
        help="真实 env 文件不存在时只警告，不失败。",
    )
    parser.add_argument(
        "--allow-prod-mock",
        action="store_true",
        help="生产 mock provider 只警告，不失败。仅用于有意降级发布。",
    )

    args = parser.parse_args(argv)

    issues: list[Issue] = []

    if args.mode in {"all", "templates"}:
        check_templates(ROOT, issues)

    if args.mode in {"all", "docs"}:
        check_markdown_links(ROOT, issues)

    if args.mode in {"all", "real"}:
        check_real_env_file(
            ROOT / args.env_file,
            issues,
            allow_missing=args.allow_missing_real_env,
            allow_prod_mock=args.allow_prod_mock,
        )
        check_real_env_file(
            ROOT / args.cloud_env_file,
            issues,
            allow_missing=args.allow_missing_real_env,
            allow_prod_mock=args.allow_prod_mock,
        )
        check_git_secret_tracking(ROOT, issues)

    return print_summary(issues)




if __name__ == "__main__":
    raise SystemExit(main())

