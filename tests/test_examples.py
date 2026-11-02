"""Examples stay runnable: the workflow quickstart dry run and its template files."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path
from types import ModuleType

import pytest

EXAMPLE_DIR = Path(__file__).resolve().parents[1] / "examples" / "workflow-quickstart"


def _load_setup_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("workflow_quickstart_setup", EXAMPLE_DIR / "setup_demo.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(("template_path"), sorted((EXAMPLE_DIR / "templates").glob("*.json")), ids=lambda p: p.name)
def test_template_files_are_valid_graphs(template_path: Path):
    template = json.loads(template_path.read_text(encoding="utf-8"))
    node_ids = [node["id"] for node in template["nodes"]]
    assert template["template_id"].startswith("example_")
    assert template["topology_type"] in {"workflow", "architecture"}
    assert len(node_ids) == len(set(node_ids))
    assert all(node_ids)
    assert all(edge["source"] in node_ids and edge["target"] in node_ids for edge in template["edges"])
    for node in template["nodes"]:
        if node["type"] == "condition":
            handles = {
                edge.get("config", {}).get("sourceHandle") for edge in template["edges"] if edge["source"] == node["id"]
            }
            assert handles == {"true", "false"}, f"condition {node['id']} needs YES and NO branches"


def test_quickstart_dry_run_creates_instance_task_and_run(tmp_path: Path):
    setup = _load_setup_module()
    project_copy = tmp_path / "demo-project"
    shutil.copytree(EXAMPLE_DIR / "demo-project", project_copy)

    with setup.in_process_caller(tmp_path / "app-data") as call:
        result = setup.setup_demo(call, project_copy, create_run=True)
        repeated = setup.setup_demo(call, project_copy)
    assert repeated["group_id"] == result["group_id"]
    assert repeated["task_identifier"] == result["task_identifier"]
    assert repeated["reused_instance"] is True

    assert result["template_ids"] == ["example_review_pipeline", "example_small_team"]
    assert result["group_id"].startswith("flow_")
    assert result["task_identifier"].startswith("VA-")
    assert result["run_nodes"] == ["analyst", "reviewer", "check", "writer", "followup"]
    group_file = project_copy / ".agents" / "groups" / f"{result['group_id']}.json"
    run_file = project_copy / ".agents" / "runs" / result["group_id"] / f"{result['run_id']}.json"
    assert json.loads(group_file.read_text(encoding="utf-8"))["goal"] == setup.DEMO_GOAL
    assert json.loads(run_file.read_text(encoding="utf-8"))["status"] == "ready"


def test_quickstart_does_not_write_into_the_example_folder():
    assert not (EXAMPLE_DIR / "demo-project" / ".agents").exists()


def test_learning_example_runs_without_a_paid_provider():
    """The documented example itself verifies real tools, scoring and memory boundaries."""
    folder = EXAMPLE_DIR.parent / "learning-loop"
    spec = importlib.util.spec_from_file_location("learning_example", folder / "verify.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main() == 0
