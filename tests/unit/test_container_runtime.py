from contextlib import nullcontext

import pytest

from scripts.check_container_runtime import check, check_cpu_dependencies


@pytest.mark.parametrize("uid,data,code,secret,error", [
    (10001, True, False, False, None),
    (0, True, False, False, "uid"),
    (10001, False, False, False, "data_write"),
    (10001, True, True, False, "code_read_only"),
    (10001, True, False, True, "clean_image"),
])
def test_container_policy_contrast(uid, data, code, secret, error):
    expected = nullcontext() if error is None else pytest.raises(RuntimeError, match=error)
    with expected:
        check(uid, lambda path: data if path == "/app/data" else code, lambda path: secret)


@pytest.mark.parametrize("names,cuda_version,passes", [
    (["torch", "numpy", "ctranslate2"], None, True),
    (["torch", "nvidia-cudnn-cu13"], None, False),
    (["torch", "CUDA_toolkit"], None, False),
    (["torch", "triton"], None, False),
    (["torch"], "13.0", False),
])
def test_cpu_dependencies_contrast(names, cuda_version, passes):
    expected = nullcontext() if passes else pytest.raises(RuntimeError, match="CPU-only")
    with expected:
        check_cpu_dependencies(names, cuda_version)