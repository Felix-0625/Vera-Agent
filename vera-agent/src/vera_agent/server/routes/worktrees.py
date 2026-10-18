"""Git working-tree routes used by the diff viewer.

Routes: GET /api/worktrees/refs, /api/worktrees/diff; POST /api/worktrees/stage,
/api/worktrees/discard, /api/worktrees/checkpoint, /api/worktrees/reset.
"""

from __future__ import annotations

import logging
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState

logger = logging.getLogger("vera_server.worktrees")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _resolve_target_dir(
    state: ServerState, group_id: str | None, wt_path_str: str | None, project_id: str | None = None
) -> Path | None:
    if wt_path_str:
        return Path(wt_path_str).resolve()
    if group_id and state.graph and group_id in state.graph.groups:
        return state.graph.groups[group_id].worktree_path.resolve()
    if project_id:
        history = state.load_json_config("projects_history.json", {"projects": []})
        project = next((item for item in history.get("projects", []) if item.get("id") == project_id), None)
        if not project:
            return None
        folders = project.get("folders") or [project.get("path")]
        target = next((folder for folder in folders if isinstance(folder, str) and Path(folder).is_dir()), None)
        if target:
            return Path(target).resolve()
        return None
    return state.root_path.resolve()


async def get_worktree_refs(request: Request) -> JSONResponse:
    state = _get_state(request)
    target_dir = _resolve_target_dir(state, None, None, request.query_params.get("project_id"))
    if target_dir is None:
        return JSONResponse({"error": "项目不存在或项目目录不可用"}, status_code=404)
    _, branches_text, _ = state.run_git(["branch", "--format=%(refname:short)"], cwd=target_dir)
    _, current_text, _ = state.run_git(["branch", "--show-current"], cwd=target_dir)
    branch = request.query_params.get("branch") or current_text.strip() or "HEAD"
    _, commits_text, _ = state.run_git(["log", branch, "--format=%H%x1f%h%x1f%s%x1f%ct", "-n", "60"], cwd=target_dir)
    commits = []
    for line in commits_text.splitlines():
        parts = line.split("\x1f", 3)
        if len(parts) == 4:
            commits.append({"hash": parts[0], "short_hash": parts[1], "subject": parts[2], "timestamp": int(parts[3])})
    return JSONResponse(
        {
            "branches": [item for item in branches_text.splitlines() if item],
            "current_branch": current_text.strip(),
            "commits": commits,
        }
    )


async def get_worktree_diff(request: Request) -> JSONResponse:
    state = _get_state(request)
    group_id = request.query_params.get("group_id")
    wt_path_str = request.query_params.get("worktree_path")
    project_id = request.query_params.get("project_id")
    base_ref = request.query_params.get("base_ref")
    target_dir = _resolve_target_dir(state, group_id, wt_path_str, project_id)
    if target_dir is None:
        return JSONResponse({"error": "项目不存在或项目目录不可用"}, status_code=404)

    # 1. Status porcelain
    code_st, stdout_st, stderr_st = state.run_git(
        ["-c", "core.quotepath=false", "status", "--porcelain=v1", "--untracked-files=all", "-z"], cwd=target_dir
    )
    _, git_prefix, _ = state.run_git(["rev-parse", "--show-prefix"], cwd=target_dir)
    git_prefix = git_prefix.strip().replace("\\", "/")
    staged: list[dict] = []
    unstaged: list[dict] = []
    untracked: list[str] = []

    status_records = stdout_st.split("\0")
    index = 0
    while index < len(status_records):
        line = status_records[index]
        index += 1
        if len(line) < 4:
            continue
        index_status, worktree_status, filepath = line[0], line[1], line[3:]
        if git_prefix and filepath.replace("\\", "/").startswith(git_prefix):
            filepath = filepath[len(git_prefix) :]
        if "R" in (index_status, worktree_status) or "C" in (index_status, worktree_status):
            index += 1

        if index_status not in (" ", "?"):
            staged.append({"file": filepath, "status": index_status})
        if worktree_status not in (" ", "?"):
            unstaged.append({"file": filepath, "status": worktree_status})
        elif index_status == "?" and worktree_status == "?":
            untracked.append(filepath)

    # 2. Raw diffs
    _, diff_unstaged, _ = state.run_git(
        ["-c", "core.quotepath=false", "diff", "--relative", "--no-color", "--no-ext-diff"], cwd=target_dir
    )
    _, diff_staged, _ = state.run_git(
        ["-c", "core.quotepath=false", "diff", "--cached", "--relative", "--no-color", "--no-ext-diff"], cwd=target_dir
    )

    if base_ref:
        code, resolved_ref, stderr = state.run_git(["rev-parse", "--verify", f"{base_ref}^{{commit}}"], cwd=target_dir)
        if code != 0:
            return JSONResponse({"error": stderr or "无效的对比分支或提交"}, status_code=400)
        base_ref = resolved_ref.strip()
        code, compare_diff, stderr = state.run_git(
            ["-c", "core.quotepath=false", "diff", "--relative", "--no-color", "--no-ext-diff", base_ref, "--"],
            cwd=target_dir,
        )
        if code != 0:
            return JSONResponse({"error": stderr or "无法生成差异"}, status_code=400)
        _, changed_names, _ = state.run_git(
            ["-c", "core.quotepath=false", "diff", "--relative", "--name-only", "-z", base_ref, "--"], cwd=target_dir
        )
        unstaged = [{"file": name, "status": "M"} for name in changed_names.split("\0") if name]
        diff_unstaged = compare_diff
        diff_staged = ""

    numstat_args = ["-c", "core.quotepath=false", "diff", "--relative", "--numstat", "-z"]
    if base_ref:
        numstat_args.extend([base_ref, "--"])
        numstat_outputs = [state.run_git(numstat_args, cwd=target_dir)[1]]
    else:
        numstat_outputs = [
            state.run_git(numstat_args + ["--"], cwd=target_dir)[1],
            state.run_git(numstat_args + ["--cached", "--"], cwd=target_dir)[1],
        ]
    file_stats: dict[str, list[int]] = {}
    for output in numstat_outputs:
        for record in output.split("\0"):
            parts = record.split("\t", 2)
            if len(parts) != 3:
                continue
            try:
                additions, deletions = int(parts[0]), int(parts[1])
            except ValueError:
                additions = deletions = 0
            totals = file_stats.setdefault(parts[2], [0, 0])
            totals[0] += additions
            totals[1] += deletions
    for filepath in untracked:
        try:
            raw = (target_dir / filepath).read_bytes()
            if b"\x00" not in raw and len(raw) <= 2_000_000:
                content = raw.decode("utf-8")
                file_stats[filepath] = [len(content.splitlines()), 0]
        except (OSError, UnicodeDecodeError):
            pass
    for item in staged + unstaged:
        item["additions"], item["deletions"] = file_stats.get(item["file"], [0, 0])
    unstaged.extend(
        {"file": filepath, "status": "?", "additions": file_stats.get(filepath, [0, 0])[0], "deletions": 0}
        for filepath in untracked
    )

    return JSONResponse(
        {
            "cwd": str(target_dir),
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "diff_text": diff_unstaged,
            "diff_staged": diff_staged,
            "base_ref": base_ref,
        }
    )


async def stage_worktree_file(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    files = body.get("files") or ([body.get("file")] if body.get("file") else [])
    if not files:
        return JSONResponse({"error": "files list is required"}, status_code=400)

    target_dir = _resolve_target_dir(state, body.get("group_id"), body.get("worktree_path"), body.get("project_id"))
    if target_dir is None:
        return JSONResponse({"error": "项目不存在或项目目录不可用"}, status_code=404)
    code, stdout, stderr = state.run_git(["add", *files], cwd=target_dir)
    if code != 0:
        return JSONResponse({"error": stderr or "git add failed", "returncode": code}, status_code=500)

    return JSONResponse({"status": "staged", "files": files})


async def discard_worktree_file(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    files = body.get("files") or ([body.get("file")] if body.get("file") else [])
    if not files:
        return JSONResponse({"error": "files list is required"}, status_code=400)

    target_dir = _resolve_target_dir(state, body.get("group_id"), body.get("worktree_path"), body.get("project_id"))
    if target_dir is None:
        return JSONResponse({"error": "项目不存在或项目目录不可用"}, status_code=404)
    # Checkout/restore working tree changes
    code, stdout, stderr = state.run_git(["checkout", "--", *files], cwd=target_dir)
    if code != 0:
        # Fallback to git restore if checkout syntax fails
        code, stdout, stderr = state.run_git(["restore", *files], cwd=target_dir)

    return JSONResponse({"status": "discarded", "files": files, "returncode": code})


async def create_checkpoint(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    wt_path = body.get("worktree_path")
    group_id = body.get("group_id")
    if not wt_path and group_id and state.graph and group_id in state.graph.groups:
        wt_path = str(state.graph.groups[group_id].worktree_path)
    if not wt_path:
        target_dir = _resolve_target_dir(state, group_id, None, body.get("project_id"))
        if target_dir is None:
            return JSONResponse({"error": "项目不存在或项目目录不可用"}, status_code=404)
        wt_path = str(target_dir)

    msg = body.get("message", "automated checkpoint")
    if not wt_path:
        return JSONResponse({"error": "worktree_path required"}, status_code=400)

    if not state.wt_manager:
        return JSONResponse({"error": "WorktreeManager not initialized"}, status_code=500)

    commit = state.wt_manager.create_checkpoint(wt_path, msg)
    return JSONResponse({"success": True, "commit": commit})


async def reset_worktree(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    wt_path = body.get("worktree_path")
    group_id = body.get("group_id")
    if not wt_path and group_id and state.graph and group_id in state.graph.groups:
        wt_path = str(state.graph.groups[group_id].worktree_path)
    if not wt_path:
        target_dir = _resolve_target_dir(state, group_id, None, body.get("project_id"))
        if target_dir is None:
            return JSONResponse({"error": "项目不存在或项目目录不可用"}, status_code=404)
        wt_path = str(target_dir)

    hard = body.get("hard", True)
    if not wt_path:
        return JSONResponse({"error": "worktree_path required"}, status_code=400)

    if not state.wt_manager:
        return JSONResponse({"error": "WorktreeManager not initialized"}, status_code=500)

    success = state.wt_manager.reset_worktree(wt_path, hard=hard)
    return JSONResponse({"success": success})


worktree_routes = [
    Route("/api/worktrees/refs", get_worktree_refs, methods=["GET"]),
    Route("/api/worktrees/diff", get_worktree_diff, methods=["GET"]),
    Route("/api/worktrees/stage", stage_worktree_file, methods=["POST"]),
    Route("/api/worktrees/discard", discard_worktree_file, methods=["POST"]),
    Route("/api/worktrees/checkpoint", create_checkpoint, methods=["POST"]),
    Route("/api/worktrees/reset", reset_worktree, methods=["POST"]),
]
