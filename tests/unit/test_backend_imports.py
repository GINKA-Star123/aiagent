from importlib import import_module

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "langmem.short_term",
        "aiagent.graphs.llm_graph",
        "apps.core.bootstrap",
        "apps.api.http_server",
    ],
)
def test_backend_modules_are_importable(module_name):
    assert import_module(module_name) is not None


def test_langmem_summary_interfaces_are_available():
    module = import_module("langmem.short_term")
    assert hasattr(module, "RunningSummary")
    assert callable(module.SummarizationNode)
