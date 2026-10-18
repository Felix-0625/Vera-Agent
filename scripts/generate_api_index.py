"""Generate the HTTP route index in docs/API.md from the Starlette route modules.

The route tables between the ``<!-- routes:begin -->`` and ``<!-- routes:end -->``
markers are generated; prose outside the markers is maintained by hand.

Usage (from the repository root)::

    python scripts/generate_api_index.py          # rewrite docs/API.md
    python scripts/generate_api_index.py --check  # exit 1 if docs/API.md is stale

The script only parses source files with ``ast``; it does not import VeraAgent,
so it runs without the backend virtual environment.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTES_DIR = REPO_ROOT / "vera-agent" / "src" / "vera_agent" / "server" / "routes"
FRONTEND_API_DIR = REPO_ROOT / "frontend" / "src" / "api"
API_DOC = REPO_ROOT / "docs" / "API.md"
BEGIN, END = "<!-- routes:begin -->", "<!-- routes:end -->"


@dataclass(frozen=True)
class RouteInfo:
    module: str
    methods: tuple[str, ...]
    path: str
    handler: str
    line: int
    summary: str
    query: tuple[str, ...]
    statuses: tuple[int, ...]


def _query_params(func: ast.AST) -> tuple[str, ...]:
    keys: list[str] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            owner = node.func.value
            if isinstance(owner, ast.Attribute) and owner.attr == "query_params" and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    keys.append(first.value)
    return tuple(dict.fromkeys(keys))


def _status_codes(func: ast.AST) -> tuple[int, ...]:
    codes = {
        node.value.value
        for node in ast.walk(func)
        if isinstance(node, ast.keyword) and node.arg == "status_code" and isinstance(node.value, ast.Constant)
    }
    return tuple(sorted(codes))


def _find_handler(module_path: Path, local: dict[str, ast.AST], name: str) -> tuple[str, ast.AST]:
    """Return (module file name, function node) for a handler defined locally or in a sibling route module."""
    if name in local:
        return module_path.name, local[name]
    for sibling in sorted(ROUTES_DIR.glob("*.py")):
        tree = ast.parse(sibling.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
                return sibling.name, node
    msg = f"Handler {name} registered in {module_path.name} was not found in server/routes/."
    raise SystemExit(msg)


def collect_routes() -> list[RouteInfo]:
    """Return every Route/WebSocketRoute registered in server/routes/*.py, in file order."""
    routes: list[RouteInfo] = []
    for module_path in sorted(ROUTES_DIR.glob("*.py")):
        if module_path.name == "__init__.py":
            continue
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        functions = {
            node.name: node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"Route", "WebSocketRoute"}
        ]
        for call in sorted(calls, key=lambda node: node.lineno):
            path = call.args[0].value
            handler = call.args[1].id
            methods: tuple[str, ...] = ("WS",)
            for keyword in call.keywords:
                if keyword.arg == "methods":
                    methods = tuple(element.value for element in keyword.value.elts)
            # A route list may register handlers imported from sibling modules (e.g. groups.py -> runs.py).
            defining_module, func = _find_handler(module_path, functions, handler)
            summary = (ast.get_docstring(func) or "").strip().split("\n")[0]
            routes.append(
                RouteInfo(
                    module=defining_module,
                    methods=methods,
                    path=path,
                    handler=handler,
                    line=func.lineno,
                    summary=summary,
                    query=_query_params(func),
                    statuses=_status_codes(func),
                )
            )
    return routes


def _strip_template_expressions(source: str) -> str:
    """Replace `${...}` (with nested braces/parentheses) by `{}` so paths read like `/api/x/{}/y`."""
    result: list[str] = []
    index = 0
    while index < len(source):
        if source.startswith("${", index):
            depth, index = 1, index + 2
            while index < len(source) and depth:
                depth += {"{": 1, "}": -1}.get(source[index], 0)
                index += 1
            result.append("{}")
        else:
            result.append(source[index])
            index += 1
    return "".join(result)


def frontend_callers() -> dict[str, list[str]]:
    """Map a normalized API path (without query string) to exported frontend client functions using it."""
    callers: dict[str, list[str]] = {}
    function_pattern = re.compile(r"^export (?:async )?function (\w+)", re.MULTILINE)
    path_pattern = re.compile(r"/api/[A-Za-z0-9_\-/{}.]*")
    for source_path in sorted(FRONTEND_API_DIR.glob("*.ts")):
        source = _strip_template_expressions(source_path.read_text(encoding="utf-8"))
        matches = list(function_pattern.finditer(source))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
            for raw in path_pattern.findall(source[match.end() : end]):
                # A `${query}` suffix glued to the last segment (`/x{}`) is not a path parameter.
                normalized = re.sub(r"(?<=[^/]){}$", "", raw.rstrip("/"))
                callers.setdefault(normalized, []).append(f"{source_path.name}:{match.group(1)}")
    return callers


def _normalize(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)


def render(routes: list[RouteInfo]) -> str:
    callers = frontend_callers()
    lines = [BEGIN, "", f"_Generated by `scripts/generate_api_index.py` — {len(routes)} routes._", ""]
    by_module: dict[str, list[RouteInfo]] = {}
    for route in routes:
        by_module.setdefault(route.module, []).append(route)
    for module, module_routes in by_module.items():
        lines += [
            f"### `{module}`",
            "",
            "| Method | Path | Handler | Query | Error statuses | Frontend client |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for route in module_routes:
            handler = f"[`{route.handler}`](../vera-agent/src/vera_agent/server/routes/{module}#L{route.line})"
            query = ", ".join(f"`{name}`" for name in route.query) or "—"
            statuses = ", ".join(str(code) for code in route.statuses if code >= 400) or "—"
            used_by = sorted(set(callers.get(_normalize(route.path), [])))
            client = ", ".join(f"`{name.split(':')[1]}`" for name in used_by) or "—"
            path = route.path.replace("|", "\\|")
            lines.append(f"| {'/'.join(route.methods)} | `{path}` | {handler} | {query} | {statuses} | {client} |")
        lines.append("")
    lines.append(END)
    return "\n".join(lines)


def updated_document(current: str, routes: list[RouteInfo]) -> str:
    if BEGIN not in current or END not in current:
        msg = f"{API_DOC} must contain {BEGIN} and {END} markers."
        raise SystemExit(msg)
    head, rest = current.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    return head + render(routes) + tail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="fail if docs/API.md is out of date")
    args = parser.parse_args()
    current = API_DOC.read_text(encoding="utf-8")
    expected = updated_document(current, collect_routes())
    if args.check:
        if current != expected:
            print("docs/API.md route index is stale; run: python scripts/generate_api_index.py", file=sys.stderr)
            return 1
        print("docs/API.md route index is up to date.")
        return 0
    API_DOC.write_text(expected, encoding="utf-8", newline="\n")
    print(f"Wrote {API_DOC.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
