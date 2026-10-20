from contextlib import nullcontext
from importlib.metadata import PackageNotFoundError

import pytest

from scripts.check_dependency_runtime import check


@pytest.mark.parametrize("actual,passes", [("7.4.0", True), ("5.2.1", False), ("8.0.0", False)])
def test_version_contrast(actual, passes):
    expected = nullcontext() if passes else pytest.raises(RuntimeError, match="redis")
    with expected:
        check(["redis>=7.4,<8"], installed=lambda name: actual)


def test_missing_dependency_and_inactive_marker():
    def missing(name):
        raise PackageNotFoundError(name)

    with pytest.raises(RuntimeError, match="missing dependency: redis"):
        check(["redis>=7.4,<8"], installed=missing)
    check(["redis; python_version < '3.0'"], installed=missing)