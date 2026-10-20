import os
from importlib import import_module
from importlib.metadata import distributions


def check(uid, writable, exists):
    checks = {
        "uid": uid == 10001,
        "data_write": writable("/app/data"),
        "code_read_only": not any(
            writable(path)
            for path in (
                "/app", "/app/aiagent", "/app/apps",
                "/app/cloud", "/app/config", "/app/integrations",
            )
        ),
        "clean_image": not any(
            exists(path)
            for path in (
                "/app/.env", "/app/cloud.tencent.env", "/app/tests",
                "/app/docs", "/app/scripts", "/app/data/models",
            )
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        raise RuntimeError("container checks failed: " + ", ".join(failures))


def check_cpu_dependencies(names, cuda_version):
    normalized = {name.lower().replace("_", "-") for name in names}
    forbidden = sorted(
        name for name in normalized
        if name.startswith(("nvidia-", "cuda-"))
        or name in {"triton", "pytorch-triton"}
    )
    if forbidden or cuda_version is not None:
        raise RuntimeError(
            "CPU-only policy failed: "
            f"packages={forbidden}, torch_cuda={cuda_version}"
        )


if __name__ == "__main__":
    check(os.getuid(), lambda path: os.access(path, os.W_OK), os.path.lexists)
    names = [dist.metadata.get("Name", "") for dist in distributions()]
    check_cpu_dependencies(names, None)
    torch = import_module("torch")
    check_cpu_dependencies(names, torch.version.cuda)
    for module in ("apps.core.bootstrap", "apps.api.http_server"):
        import_module(module)
    print(f"CPU-only Torch: {torch.__version__}")
    print("Container permissions and backend imports passed.")