"""仓库卫生检查。

用法：
    .venv\Scripts\python.exe scripts\check_repo_hygiene.py
    .venv\Scripts\python.exe scripts\check_repo_hygiene.py --strict

退出码：0 = 无 ERROR；1 = 存在 ERROR（--strict 下 WARN 也算失败）。

策略（与 docs/repo-governance.md 一致）：
- 后端源码、运维脚本、测试、示例配置必须入仓；
- 前端（apps/flutter_client、apps/desktop_qt）与 data/ 下全部内容按仓库策略不入仓；
- 因此"被忽略"本身不是问题，"该入仓的源码被误忽略"才是问题。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 必须入仓的源码目录（前端与 data/ 不在其中，属于有意的排除）
SOURCE_DIRS = ("aiagent", "apps/core", "apps/api", "apps/worker", "cloud", "config", "integrations", "scripts", "tests")
SOURCE_SUFFIXES = {".py", ".ps1", ".sh", ".toml", ".yml", ".yaml", ".json", ".md", ".jsonl"}

# 有意不入仓的目录（若出现在"被忽略"清单里，只提示不报错）
INTENTIONALLY_IGNORED_DIRS = ("apps/flutter_client", "apps/desktop_qt", "data")

# clone 之后必须已存在的文件
REQUIRED_SAMPLE_ASSETS = (
    "README.md",
    "pyproject.toml",
    ".env.example",
    "cloud.tencent.example.env",
    "docs/repo-governance.md",
    "docs/config-reference.md",
    "scripts/v1_preflight.py",
    "aiagent/knowledge/character_aliases.py",
    "tests/fixtures/rag_eval/cases.jsonl",
)

# 必须被忽略，否则存在误提交风险
MUST_BE_IGNORED = (
    ".env",
    "cloud.tencent.env",
    "data/knowledge/public/LuoTianyi.md",
    "data/characters/luotianyi",
    "data/cache/",
    "data/uploads/",
    "data/models/",
    "data/runtime/",
    "apps/flutter_client/README.md",
    "apps/desktop_qt/README.md",
    "_tmp/",
)

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"AKID[A-Za-z0-9]{16,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(
        r"(?i)(?:api[_-]?key|apikey|secret|password|passwd|token|access[_-]?key)"
        r"\s*[:=]\s*[\"']([^\"']{16,})[\"']"
    ),
    re.compile(
        r"(?i)(?:api[_-]?key|apikey|secret|password|passwd|token|access[_-]?key)"
        r"\s*[:=]\s*([A-Za-z0-9_\-/+]{20,})"
    ),
)

# 占位符与测试夹具的容忍词
PLACEHOLDER_HINTS = (
    "change", "your", "example", "placeholder", "xxx", "todo",
    "fake", "dummy", "sample", "test", "unit", "local", "strong",
    "abcdef", "<", ">",
)

# 测试/文档/脚本里的"密钥"几乎都是夹具，扫描时跳过（并在报告里说明）
SECRET_SCAN_SKIP_PREFIXES = ("tests/", "docs/", "scripts/")

LARGE_FILE_BYTES = 20 * 1024 * 1024


@dataclass
class Finding:
    level: str          # ERROR / WARN / INFO
    code: str
    message: str
    items: list[str] = field(default_factory=list)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )


def _git_lines(*args: str) -> list[str]:
    result = _git(*args)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _is_intentionally_ignored(relative_path: str) -> bool:
    return relative_path.startswith(INTENTIONALLY_IGNORED_DIRS)


def is_ignored(relative_path: str, *, no_index: bool = True) -> bool:
    """判断路径是否真的会被排除在版本库之外。

    两个坑：
    1. 必须加 --no-index，否则"已跟踪文件"永远返回未忽略；
    2. 必须加 -v 看命中的模式：git check-ignore 对 ! 反选规则同样返回 0，
       只靠退出码会把"被白名单反选进来的文件"误判成被忽略。
    """
    args = ["check-ignore"]
    if no_index:
        args.append("--no-index")
    args += ["-v", relative_path]

    result = _git(*args)
    if result.returncode != 0:
        return False

    line = result.stdout.strip()
    if not line:
        return False

    # 输出格式：<source>:<linenum>:<pattern>	<pathname>
    matched = line.split("\t", 1)[0]
    pattern = matched.split(":", 2)[-1] if ":" in matched else matched
    return not pattern.lstrip().startswith("!")


def candidate_files() -> list[str]:
    """可能被提交的文件 = 已跟踪 + 未跟踪且未被忽略。"""
    tracked = _git_lines("ls-files")
    untracked = _git_lines("ls-files", "--others", "--exclude-standard")
    return sorted(set(tracked) | set(untracked))


def check_source_files_tracked() -> list[Finding]:
    """源码目录下的文件若被规则命中，clone 后会缺文件。

    这里专门防"无前缀通配符误伤源码"这类问题：
    例如 .gitignore 写 live2d/ 会连带命中 aiagent/live2d/ 与 integrations/live2d/。
    """
    ignored: list[str] = []
    intentional: list[str] = []

    for source_dir in SOURCE_DIRS:
        root = PROJECT_ROOT / source_dir
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            if any(part in {"__pycache__", ".ruff_cache", ".pytest_cache"} for part in path.parts):
                continue
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            if not is_ignored(relative):
                continue
            if _is_intentionally_ignored(relative):
                intentional.append(relative)
            else:
                ignored.append(relative)

    findings: list[Finding] = []

    if ignored:
        findings.append(
            Finding(
                level="ERROR",
                code="source_file_ignored",
                message="源码文件被 .gitignore 命中，clone 后会缺失：",
                items=sorted(ignored)[:20],
            )
        )

    if intentional:
        findings.append(
            Finding(
                level="INFO",
                code="intentional_ignore",
                message=f"有意排除的目录（前端/data）共 {len(intentional)} 个文件被忽略，符合仓库策略。",
                items=[],
            )
        )

    return findings


def check_required_assets() -> Finding | None:
    missing = [item for item in REQUIRED_SAMPLE_ASSETS if not (PROJECT_ROOT / item).exists()]
    ignored = [item for item in REQUIRED_SAMPLE_ASSETS if is_ignored(item)]

    if not missing and not ignored:
        return None

    items = [f"缺失: {name}" for name in missing] + [f"被忽略: {name}" for name in ignored]
    return Finding(
        level="ERROR",
        code="required_asset_missing",
        message="必须入仓的文件缺失或被忽略：",
        items=items,
    )


def check_runtime_dirs_ignored() -> Finding | None:
    not_ignored = [item for item in MUST_BE_IGNORED if not is_ignored(item)]
    if not not_ignored:
        return None
    return Finding(
        level="ERROR",
        code="must_be_ignored_not_ignored",
        message="以下文件/目录应当被忽略却没有，存在误提交风险：",
        items=not_ignored,
    )


def _looks_like_real_secret(value: str) -> bool:
    """排除变量名、函数调用与占位符，只保留"像真密钥"的字符串。"""
    if any(hint in value.lower() for hint in PLACEHOLDER_HINTS):
        return False
    if "(" in value or ")" in value:
        return False
    if re.fullmatch(r"[a-z_][a-z0-9_]*", value):          # embedding_api_key 这类标识符
        return False
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):     # 纯单词
        return False
    has_digit = any(ch.isdigit() for ch in value)
    has_alpha = any(ch.isalpha() for ch in value)
    return has_digit and has_alpha and len(value) >= 16


def check_secrets_in_candidate_files() -> Finding | None:
    hits: list[str] = []

    for relative in candidate_files():
        if relative.startswith(SECRET_SCAN_SKIP_PREFIXES):
            continue
        path = PROJECT_ROOT / relative
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".wav", ".m4a", ".pdf", ".index", ".faiss", ".dill"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for pattern in SECRET_PATTERNS:
            matched = False
            for match in pattern.finditer(text):
                value = match.group(1) if match.groups() else match.group(0)
                if _looks_like_real_secret(value):
                    hits.append(f"{relative}: {value[:32]}...")
                    matched = True
                    break
            if matched:
                break

    if not hits:
        return None
    return Finding(
        level="ERROR",
        code="secret_in_committable_file",
        message="可能被提交的文件中发现疑似真实密钥（tests/docs/scripts 已排除）：",
        items=sorted(set(hits))[:20],
    )


def check_large_files() -> Finding | None:
    oversized: list[str] = []

    for relative in candidate_files():
        path = PROJECT_ROOT / relative
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > LARGE_FILE_BYTES:
            oversized.append(f"{relative} ({size / 1024 / 1024:.1f}MB)")

    if not oversized:
        return None
    return Finding(
        level="WARN",
        code="large_file_committable",
        message=f"可提交文件中有超过 {LARGE_FILE_BYTES // 1024 // 1024}MB 的大文件：",
        items=sorted(oversized)[:20],
    )


def check_powershell_encoding() -> Finding | None:
    """含非 ASCII 的 .ps1 必须带 UTF-8 BOM。

    Windows PowerShell 5.1 对无 BOM 的脚本按 ANSI 代码页解析，
    中文会被曲解并吞掉引号，报出"字符串缺少终止符"这种与真实原因无关的语法错误。
    """
    offenders: list[str] = []

    for source_dir in ("scripts", "deploy"):
        root = PROJECT_ROOT / source_dir
        if not root.exists():
            continue
        for path in root.rglob("*.ps1"):
            if not path.is_file():
                continue
            raw = path.read_bytes()
            relative = path.relative_to(PROJECT_ROOT).as_posix()

            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                offenders.append(f"{relative}（不是 UTF-8 编码）")
                continue

            has_non_ascii = any(ord(ch) > 127 for ch in text)
            has_bom = raw.startswith(b"\xef\xbb\xbf")

            if has_non_ascii and not has_bom:
                offenders.append(f"{relative}（含中文但缺 UTF-8 BOM）")

    if not offenders:
        return None
    return Finding(
        level="ERROR",
        code="ps1_missing_bom",
        message="PowerShell 脚本含非 ASCII 字符却没有 UTF-8 BOM，PS 5.1 会解析失败：",
        items=offenders,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="仓库卫生检查")
    parser.add_argument("--strict", action="store_true", help="WARN 也视为失败")
    args = parser.parse_args(argv)

    findings: list[Finding] = []
    findings.extend(check_source_files_tracked())

    for check in (
        check_required_assets,
        check_runtime_dirs_ignored,
        check_secrets_in_candidate_files,
        check_powershell_encoding,
        check_large_files,
    ):
        finding = check()
        if finding is not None:
            findings.append(finding)

    errors = [item for item in findings if item.level == "ERROR"]
    warnings = [item for item in findings if item.level == "WARN"]
    infos = [item for item in findings if item.level == "INFO"]

    for finding in findings:
        print(f"[{finding.level}] {finding.code}: {finding.message}")
        for item in finding.items:
            print(f"    - {item}")

    if not errors and not warnings:
        print(f"[repo-hygiene] OK：源码入仓、必需文件齐全、运行资产已忽略、无可疑密钥。（{len(infos)} 条提示）")
        return 0

    print(f"[repo-hygiene] ERROR {len(errors)} 项，WARN {len(warnings)} 项。")
    if errors:
        return 1
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
