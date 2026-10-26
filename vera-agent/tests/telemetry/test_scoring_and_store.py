"""Outcome scoring rules, the SQLite trace store, and traces written by real chat turns."""

from __future__ import annotations

import json
from pathlib import Path

from starlette.testclient import TestClient

from tests.chat_helpers import TEST_MODEL_ID, make_chat_repo, parse_sse, reply, scripted_stream, set_permissions
from vera_agent.server.app import create_app
from vera_agent.telemetry.exporters.langfuse import build_ingestion_batch
from vera_agent.telemetry.scoring import classify_followup, score_finished_trace
from vera_agent.telemetry.store import TraceStore
from vera_agent.telemetry.trace import Span, Trace, classify_task_type


def _bash_span(trace: Trace, command: str, returncode: int, approval: str | None = None) -> Span:
    metadata = {"returncode": returncode, **({"approval": approval} if approval else {})}
    return Span(trace.trace_id, "tool", "bash", input={"command": command}, metadata=metadata, status="ok")


def _scores(trace: Trace) -> dict[str, float]:
    return {score.name: score.value for score in score_finished_trace(trace)}


def test_clean_turn_scores_one():
    trace = Trace(thread_id="t", exit_status="finish")
    assert _scores(trace) == {"turn_signal": 1.0, "outcome": 1.0}


def test_failed_final_test_run_decides_outcome_even_if_earlier_runs_passed():
    trace = Trace(thread_id="t", exit_status="finish")
    trace.spans = [_bash_span(trace, "python -m pytest", 0), _bash_span(trace, "npm run build", 2)]
    scores = _scores(trace)
    assert scores["verification"] == 0.0 and scores["outcome"] == 0.0 and scores["turn_signal"] == 1.0


def test_returncode_of_non_verification_commands_is_ignored():
    trace = Trace(thread_id="t", exit_status="finish")
    trace.spans = [_bash_span(trace, "grep missing file.txt", 1)]
    assert _scores(trace)["outcome"] == 1.0


def test_rejections_corrections_and_interruptions_lower_the_signal():
    trace = Trace(thread_id="t", exit_status="interrupted")
    trace.spans = [_bash_span(trace, "rm x", 1, "rejected"), _bash_span(trace, "ls", 1, "corrected")]
    assert _scores(trace)["turn_signal"] == 0.0
    assert _scores(Trace(thread_id="t", exit_status="error"))["outcome"] == 0.0


def test_followup_classification():
    assert classify_followup("不对，回滚这个改动") == 0.0
    assert classify_followup("That's wrong, please revert") == 0.0
    assert classify_followup("好的，继续下一步") == 1.0
    assert classify_followup("Thanks, looks great") == 1.0
    assert classify_followup("把端口改成 8080") is None


def test_task_type_classification():
    assert classify_task_type("修复登录报错", None, "main") == "fix"
    assert classify_task_type("x", "supervisor_review", "main") == "workflow:supervisor_review"
    assert classify_task_type("hello", None, "main") == "chat"


def test_store_round_trip_and_latest_score_wins(tmp_path: Path):
    store = TraceStore(tmp_path / "traces.db")
    trace = Trace(thread_id="t", task_type="fix", exit_status="finish", end_time=1.0, start_time=0.5)
    trace.spans = [_bash_span(trace, "pytest", 0)]
    score_finished_trace(trace)
    store.save_trace(trace)
    loaded = store.get_trace(trace.trace_id)
    assert loaded["spans"][0]["input"] == {"command": "pytest"}
    assert {score["name"] for score in loaded["scores"]} == {"turn_signal", "verification", "outcome"}
    assert store.list_traces(thread_id="t")[0]["outcome"] == 1.0
    assert store.success_by_task_type()[0] == {
        "task_type": "fix",
        "traces": 1,
        "scored": 1,
        "mean_outcome": 1.0,
        "success_rate": 1.0,
    }


def test_langfuse_batch_maps_model_spans_to_generations():
    trace = Trace(thread_id="t", exit_status="finish")
    trace.spans = [Span(trace.trace_id, "model", "deepseek/deepseek-chat", metadata={"prompt_tokens": 3})]
    score_finished_trace(trace)
    types = [event["type"] for event in build_ingestion_batch(trace)]
    assert types[0] == "trace-create" and "generation-create" in types and types.count("score-create") == 2


def _turn(client: TestClient, responses, content: str) -> list:
    with scripted_stream(responses):
        response = client.post(
            "/api/chat/stream", json={"thread_id": "th_trace", "model_id": TEST_MODEL_ID, "content": content}
        )
    return parse_sse(response.text)


def test_streamed_turn_writes_a_scored_trace_and_secrets_are_redacted(tmp_path: Path):
    repo = make_chat_repo(tmp_path / "repo")
    set_permissions(repo, "allow_all")
    client = TestClient(create_app(repo_root=repo))
    events = _turn(
        client,
        [reply("Testing.", {"command": "echo api_key=sk-abcdefghijklmnop && exit 3"}), reply("Done.")],
        "run the tests",
    )
    trace_id = events[-1][1]["trace_id"]
    trace = TraceStore(repo / ".agents" / "traces.db").get_trace(trace_id)
    assert trace["exit_status"] == "finish" and trace["task_type"] == "test"
    assert [span["kind"] for span in trace["spans"]] == ["model", "tool", "model"]
    assert "sk-abcdefghijklmnop" not in json.dumps(trace["spans"])
    assert trace["spans"][1]["metadata"]["returncode"] == 3


def test_next_message_scores_the_previous_turn(tmp_path: Path):
    repo = make_chat_repo(tmp_path / "repo")
    client = TestClient(create_app(repo_root=repo))
    first_trace_id = _turn(client, [reply("Changed it.")], "改一下标题")[-1][1]["trace_id"]
    _turn(client, [reply("Reverting.")], "不对，回滚")
    scores = TraceStore(repo / ".agents" / "traces.db").trace_scores(first_trace_id)
    assert scores["user_followup"]["value"] == 0.0 and scores["user_followup"]["source"] == "heuristic"
    assert scores["outcome"]["value"] == 1.0
