"""Verify memory isolation and the eval harness with a scripted provider, without paid calls."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from vera_agent.evals.cases import load_cases
from vera_agent.evals.profile import AgentProfile
from vera_agent.evals.runner import run_case
from vera_agent.memory.backend import SqliteMemoryBackend
from vera_agent.memory.service import MemoryService
from vera_agent.models.litellm_model import LitellmModel

EXAMPLE_DIR = Path(__file__).resolve().parent
MODEL_ID = "scripted-example"


def verify_memory(root: Path) -> dict[str, bool]:
    """Exercise real SQLite recall, project isolation, confirmation and version restore."""
    backend = SqliteMemoryBackend(root / "memory.db")
    memory = MemoryService(backend, backend)
    original = memory.add(
        scope="project", scope_id="example-a", kind="preference", content="北京项目使用 unittest 验证。", source="user"
    )
    assert backend.keyword_search("北京", [("project", "example-a")], 10)
    assert not backend.keyword_search("北京", [("project", "example-b")], 10)
    change = memory.propose_change("update", memory_id=original.memory_id, content="北京项目先运行完整测试。")
    assert backend.get(original.memory_id).content == original.content
    memory.resolve_change(change["change_id"], True)
    assert backend.get(original.memory_id).content == "北京项目先运行完整测试。"
    rejected = memory.propose_change("delete", memory_id=original.memory_id)
    memory.resolve_change(rejected["change_id"], False)
    assert backend.get(original.memory_id).status == "active"
    restored = memory.restore_version(original.memory_id, 1)
    assert restored.content == original.content
    assert restored.version > 1
    return {"chinese_recall": True, "project_isolation": True, "accept_reject": True, "version_restore": True}


def scripted_provider():
    """Replace only the provider transport; permissions, tools and acceptance commands stay real."""
    responses = iter(
        [
            {
                "content": "Apply the fixture repair.",
                "extra": {
                    "actions": [
                        {"tool_name": "edit", "path": "calc.py", "edits": [{"oldText": "a - b", "newText": "a + b"}]}
                    ]
                },
            },
            {"content": "Run verification.", "extra": {"actions": [{"command": "python -m unittest -q"}]}},
            {"content": "The fixture repair is complete.", "extra": {"actions": []}},
        ]
    )

    def stream(_model, _messages, tools=None, *, on_text, **_kwargs):
        response = next(responses)
        on_text(response["content"])
        return {"role": "assistant", **response}

    return patch.object(LitellmModel, "query_stream", new=stream)


def verify_evaluation() -> dict:
    """Run the shipped case through run_turn in a fresh sandbox and require its acceptance script."""
    case = load_cases([EXAMPLE_DIR / "cases"])[0]
    models = {
        "models": [
            {
                "id": MODEL_ID,
                "name": "deepseek/deepseek-chat",
                "provider": "deepseek",
                "api_key": "example-placeholder",
                "enabled": True,
            }
        ]
    }
    result = run_case(case, AgentProfile(), models, MODEL_ID, model_factory=scripted_provider)
    if not result.passed:
        raise RuntimeError(f"Example acceptance failed: {result.error}\n{result.acceptance_output}")
    assert result.steps == 3
    assert any(score["name"] == "verification" and score["value"] == 1 for score in result.trace["scores"])
    return {"case_id": case.case_id, "passed": result.passed, "steps": result.steps, "verification": 1}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="vera-learning-example-") as temporary:
        memory = verify_memory(Path(temporary))
        evaluation = verify_evaluation()
    print(
        json.dumps(
            {"provider": "scripted", "paid_model_calls": 0, "memory": memory, "evaluation": evaluation}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
