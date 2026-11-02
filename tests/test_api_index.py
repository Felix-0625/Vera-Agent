"""The generated API reference includes independently specified query parameters."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_generator() -> ModuleType:
    """Load the standalone maintenance script without relying on pytest's sys.path mode."""
    path = Path(__file__).resolve().parents[1] / "scripts" / "generate_api_index.py"
    spec = importlib.util.spec_from_file_location("vera_api_index_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_query_aliases_and_helper_cycles_are_handled():
    tree = ast.parse("""
def helper(request):
    helper(request)
    return request.query_params.get("days")
def handler(request):
    params = request.query_params
    limit = params.get("limit", "50")
    project = params["project_id"]
    return helper(request)
""")
    functions = {node.name: node for node in tree.body}
    assert set(_load_generator()._query_params(functions["handler"], functions)) == {"limit", "project_id", "days"}


def test_learning_query_parameters_cannot_silently_disappear():
    routes = {(route.methods, route.path): route for route in _load_generator().collect_routes()}
    assert set(routes[(("GET",), "/api/memories")].query) == {"scope", "scope_id", "kind", "status"}
    assert set(routes[(("GET",), "/api/traces")].query) == {"limit", "below_score", "thread_id", "project_id", "days"}
    assert set(routes[(("GET",), "/api/traces/summary")].query) == {"days"}
