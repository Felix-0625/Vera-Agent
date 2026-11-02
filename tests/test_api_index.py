"""The generated API reference includes independently specified query parameters."""

from __future__ import annotations

import ast

from scripts.generate_api_index import _query_params, collect_routes


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
    assert set(_query_params(functions["handler"], functions)) == {"limit", "project_id", "days"}


def test_learning_query_parameters_cannot_silently_disappear():
    routes = {(route.methods, route.path): route for route in collect_routes()}
    assert set(routes[(("GET",), "/api/memories")].query) == {"scope", "scope_id", "kind", "status"}
    assert set(routes[(("GET",), "/api/traces")].query) == {"limit", "below_score", "thread_id", "project_id", "days"}
    assert set(routes[(("GET",), "/api/traces/summary")].query) == {"days"}
