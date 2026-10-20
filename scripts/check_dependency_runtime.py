import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from packaging.requirements import Requirement


def check(requirements, installed=version):
    for raw in requirements:
        requirement = Requirement(raw)
        if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
            continue
        try:
            actual = installed(requirement.name)
        except PackageNotFoundError:
            raise RuntimeError(f"missing dependency: {requirement.name}") from None
        if not requirement.specifier.contains(actual, prereleases=None):
            raise RuntimeError(f"{requirement.name}: installed={actual}, required={requirement.specifier}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    check(project["project"]["dependencies"])
    print("运行环境直接依赖检查通过")
