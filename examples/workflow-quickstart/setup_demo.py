"""Set up the workflow quickstart in a running VeraAgent API, or dry-run it in-process.

The script uses only public HTTP routes (see docs/API.md):

1. POST /api/projects/bind            bind ``demo-project/`` as a project
2. POST /api/templates/topology       save the example templates
3. POST /api/groups/instances         instantiate the workflow template in the project
4. POST /api/taskboard/tasks          create a task board item for the demo
5. POST /api/groups/{id}/runs         create a run record (only with ``--create-run``)

It never calls a model. Executing the run (the Agent turns) happens in the desktop
UI, because the workflow scheduler lives in the frontend.

Usage::

    # against the desktop app's backend (default http://127.0.0.1:8000)
    python examples/workflow-quickstart/setup_demo.py

    # self-contained check: in-process app, temporary data root, no network or model
    python examples/workflow-quickstart/setup_demo.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

EXAMPLE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = EXAMPLE_DIR / "templates"
DEMO_PROJECT = EXAMPLE_DIR / "demo-project"
WORKFLOW_TEMPLATE = "review-pipeline.workflow.json"
DEMO_GOAL = "评审 demo-project/requirements.md 中的登录限流需求，并给出结论。"
DEMO_INPUT = "请评审 requirements.md 中的登录限流需求：列出验收标准与风险，判断是否可以进入开发。"

# (method, path, json_body) -> (status, json_response)
Caller = Callable[[str, str, dict[str, Any] | None], tuple[int, dict[str, Any]]]


def http_caller(base_url: str) -> Caller:
    """Call a running VeraAgent API over HTTP."""

    def call(method: str, path: str, body: dict[str, Any] | None) -> tuple[int, dict[str, Any]]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            base_url.rstrip("/") + path, data=data, method=method, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"{}")

    return call


def in_process_caller(data_root: Path) -> Caller:
    """Call an in-process app whose application data lives in ``data_root``."""
    from starlette.testclient import TestClient
    from vera_agent.server.app import create_app

    client = TestClient(create_app(repo_root=data_root))

    def call(method: str, path: str, body: dict[str, Any] | None) -> tuple[int, dict[str, Any]]:
        response = client.request(method, path, json=body)
        return response.status_code, response.json()

    return call


def load_templates() -> list[dict[str, Any]]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(TEMPLATES_DIR.glob("*.json"))]


def _expect(status: int, payload: dict[str, Any], expected: int, step: str) -> dict[str, Any]:
    if status != expected:
        msg = f"{step} failed with HTTP {status}: {payload.get('error', payload)}"
        raise RuntimeError(msg)
    return payload


def setup_demo(call: Caller, project_path: Path = DEMO_PROJECT, create_run: bool = False) -> dict[str, Any]:
    """Run the quickstart setup steps and return the created identifiers."""
    project = _expect(
        *call("POST", "/api/projects/bind", {"path": str(project_path), "name": "workflow-quickstart-demo"}),
        200,
        "Bind project",
    )
    project_id = project["id"]

    saved: dict[str, dict[str, Any]] = {}
    for template in load_templates():
        response = _expect(*call("POST", "/api/templates/topology", template), 201, f"Save template {template['name']}")
        saved[template["template_id"]] = response["template"]

    workflow = json.loads((TEMPLATES_DIR / WORKFLOW_TEMPLATE).read_text(encoding="utf-8"))
    instance = _expect(
        *call(
            "POST",
            "/api/groups/instances",
            {
                "project_id": project_id,
                "template_id": workflow["template_id"],
                "template_name": workflow["name"],
                "group_mode": "workflow",
                "name": workflow["name"],
                "goal": DEMO_GOAL,
                "background": (project_path / "requirements.md").read_text(encoding="utf-8"),
                "nodes": workflow["nodes"],
                "edges": workflow["edges"],
            },
        ),
        201,
        "Create workflow instance",
    )["group"]

    task = _expect(
        *call(
            "POST",
            "/api/taskboard/tasks",
            {
                "project_id": project_id,
                "title": "评审登录限流需求",
                "description": f"运行工作流「{workflow['name']}」，输入：{DEMO_INPUT}",
                "status": "todo",
                "priority": "medium",
                "labels": ["demo", "workflow"],
            },
        ),
        201,
        "Create task board item",
    )["item"]

    result: dict[str, Any] = {
        "project_id": project_id,
        "template_ids": sorted(saved),
        "group_id": instance["group_id"],
        "task_identifier": task["identifier"],
        "suggested_input": DEMO_INPUT,
    }
    if create_run:
        run = _expect(
            *call(
                "POST",
                f"/api/groups/{instance['group_id']}/runs",
                {"project_id": project_id, "confirmation": "Y", "input": DEMO_INPUT},
            ),
            201,
            "Create run",
        )["run"]
        result["run_id"] = run["run_id"]
        result["run_nodes"] = [node["node_id"] for node in run["nodes"]]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up the VeraAgent workflow quickstart.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="VeraAgent API URL")
    parser.add_argument("--dry-run", action="store_true", help="use an in-process app with a temporary data root")
    parser.add_argument("--create-run", action="store_true", help="also create (not execute) a run record")
    args = parser.parse_args()

    if args.dry_run:
        with tempfile.TemporaryDirectory(prefix="vera-quickstart-") as temporary:
            # Binding writes `<project>/.agents/`, so dry runs work on a copy of the demo project.
            project_copy = Path(temporary) / "demo-project"
            shutil.copytree(DEMO_PROJECT, project_copy)
            result = setup_demo(in_process_caller(Path(temporary) / "app-data"), project_copy, create_run=True)
    else:
        result = setup_demo(http_caller(args.base_url), create_run=args.create_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
