"""Git branch and topology routes.

Routes: GET /api/gitflow/topology, POST /api/branches, DELETE /api/branches/{name},
POST /api/branches/checkout, /api/branches/merge, /api/merge-review.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState, get_git_branch

logger = logging.getLogger("vera_server.gitflow")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


def _project_root(state: ServerState, project_id: str | None):
    if not project_id:
        return None
    history = state.load_json_config("projects_history.json", {"projects": []})
    project = next((item for item in history.get("projects", []) if item.get("id") == project_id), None)
    if not project:
        return None
    candidates = [project.get("path"), *(project.get("folders") or [])]
    return next((Path(path).resolve() for path in candidates if isinstance(path, str) and Path(path).is_dir()), None)


async def get_gitflow_topology(request: Request) -> JSONResponse:
    state = _get_state(request)
    root = _project_root(state, request.query_params.get("project_id"))
    if root is None:
        return JSONResponse({"error": "请绑定有效项目后使用 GitFlow"}, status_code=404)
    inside_code, _, _ = state.run_git(["rev-parse", "--is-inside-work-tree"], cwd=root)
    if inside_code != 0:
        return JSONResponse(
            {"repo_name": root.name, "is_git": False, "current_branch": "", "branches": [], "commits": []}
        )
    code, stdout, stderr = state.run_git(
        ["log", "--all", "--topo-order", "-n", "100", "--format=%H%x1f%P%x1f%h%x1f%ct%x1f%s"], cwd=root
    )
    if code != 0:
        return JSONResponse({"error": stderr or "当前项目不是可用的 Git 仓库"}, status_code=400)
    commits = []
    for line in stdout.splitlines():
        values = line.split("\x1f", 4)
        if len(values) != 5:
            continue
        commit, parents, short_hash, timestamp, subject = values
        commits.append(
            {
                "hash": commit,
                "short_hash": short_hash,
                "parents": parents.split() if parents else [],
                "timestamp": int(timestamp),
                "subject": subject,
            }
        )
    _, refs, _ = state.run_git(
        [
            "for-each-ref",
            "--format=%(refname)%09%(objectname)%09%(HEAD)%09%(upstream:short)",
            "refs/heads",
            "refs/remotes",
        ],
        cwd=root,
    )
    branches = []
    for line in refs.splitlines():
        columns = line.split("\t")
        if len(columns) < 3:
            continue
        refname, commit, marker = columns[:3]
        upstream = columns[3] if len(columns) > 3 else ""
        is_remote = refname.startswith("refs/remotes/")
        name = refname.removeprefix("refs/remotes/").removeprefix("refs/heads/")
        if not name or name.endswith("/HEAD"):
            continue
        branch = {"name": name, "head": commit, "is_current": marker == "*", "is_remote": is_remote}
        if not is_remote and upstream:
            ahead_code, counts, _ = state.run_git(
                ["rev-list", "--left-right", "--count", f"{name}...{upstream}"], cwd=root
            )
            if ahead_code == 0:
                ahead, behind = (int(value) for value in counts.split())
                branch.update({"upstream": upstream, "ahead": ahead, "behind": behind})
        branches.append(branch)

    # Annotate a GitFlow parent only when both refs exist and share real Git history.
    local_names = {branch["name"] for branch in branches if not branch["is_remote"]}
    roots = [name for name in ("main", "master") if name in local_names]
    preferred_parent: dict[str, str] = {}
    for name in local_names:
        lower = name.lower()
        if lower in {"develop", "development"}:
            parent = next((root_name for root_name in roots), "")
        elif lower.startswith(("feature/", "feat/", "bugfix/", "fix/", "release/")):
            parent = next((candidate for candidate in ("develop", "development") if candidate in local_names), "")
        elif lower.startswith("hotfix/"):
            parent = next((root_name for root_name in roots), "")
        else:
            parent = ""
        if parent:
            merge_base_code, _, _ = state.run_git(["merge-base", parent, name], cwd=root)
            if merge_base_code == 0:
                preferred_parent[name] = parent
    for branch in branches:
        if not branch["is_remote"] and branch["name"] in preferred_parent:
            branch["parent"] = preferred_parent[branch["name"]]
    return JSONResponse(
        {
            "repo_name": root.name,
            "is_git": True,
            "current_branch": get_git_branch(root),
            "branches": branches,
            "commits": commits,
        }
    )


async def create_branch(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    branch_name = body.get("branch_name")
    start_point = body.get("start_point", "HEAD")
    root = _project_root(state, body.get("project_id"))
    if root is None:
        return JSONResponse({"error": "请绑定有效项目后使用 GitFlow"}, status_code=404)
    if not branch_name:
        return JSONResponse({"error": "branch_name is required"}, status_code=400)

    valid, _, validation_error = state.run_git(["check-ref-format", "--branch", branch_name], cwd=root)
    if valid != 0:
        return JSONResponse({"error": validation_error or "Invalid branch name"}, status_code=400)
    code, stdout, stderr = state.run_git(["branch", "--", branch_name, start_point], cwd=root)
    if code != 0:
        return JSONResponse({"error": stderr or "Failed to create branch"}, status_code=500)

    return JSONResponse({"status": "created", "branch_name": branch_name, "start_point": start_point})


async def delete_branch(request: Request) -> JSONResponse:
    state = _get_state(request)
    root = _project_root(state, request.query_params.get("project_id"))
    if root is None:
        return JSONResponse({"error": "请绑定有效项目后使用 GitFlow"}, status_code=404)
    branch_name = request.path_params.get("branch_name", "")
    if not branch_name:
        return JSONResponse({"error": "branch_name is required"}, status_code=400)

    if branch_name == get_git_branch(root):
        return JSONResponse({"error": "不能删除当前检出的分支"}, status_code=409)
    code, stdout, stderr = state.run_git(["branch", "-d", "--", branch_name], cwd=root)
    if code != 0:
        status = 409 if "not fully merged" in stderr else 400
        return JSONResponse({"error": stderr or f"Failed to delete branch {branch_name}"}, status_code=status)

    return JSONResponse({"status": "deleted", "branch_name": branch_name})


async def checkout_branch(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    branch_name = body.get("branch_name")
    root = _project_root(state, body.get("project_id"))
    if root is None:
        return JSONResponse({"error": "请绑定有效项目后使用 GitFlow"}, status_code=404)
    if not branch_name:
        return JSONResponse({"error": "branch_name is required"}, status_code=400)

    code, stdout, stderr = state.run_git(["switch", "--", branch_name], cwd=root)
    if code != 0:
        return JSONResponse({"error": stderr or f"Failed to checkout {branch_name}"}, status_code=500)

    return JSONResponse({"status": "checked_out", "branch_name": branch_name})


async def merge_branch(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    source = body.get("source_branch")
    root = _project_root(state, body.get("project_id"))
    if root is None:
        return JSONResponse({"error": "请绑定有效项目后使用 GitFlow"}, status_code=404)
    if not source:
        return JSONResponse({"error": "source_branch is required"}, status_code=400)

    if source == get_git_branch(root):
        return JSONResponse({"error": "不能将当前分支合并到自身"}, status_code=400)
    code, stdout, stderr = state.run_git(["merge", "--no-ff", "--", source], cwd=root)
    return JSONResponse(
        {
            "status": "merged" if code == 0 else "conflict_or_error",
            "returncode": code,
            "stdout": stdout,
            "stderr": stderr,
        }
    )


async def merge_review(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    source = body.get("source_branch")
    target = body.get("target_branch", "main")
    root = _project_root(state, body.get("project_id"))
    if root is None:
        return JSONResponse({"error": "请绑定有效项目后使用 GitFlow"}, status_code=404)

    if not source:
        return JSONResponse({"error": "source_branch required"}, status_code=400)

    code, stdout, stderr = state.run_git(["merge-tree", "--write-tree", target, source], cwd=root)
    conflicts = re.findall(r"CONFLICT .*? in (.+)", stdout + "\n" + stderr)
    can_merge = code == 0
    return JSONResponse(
        {
            "source_branch": source,
            "target_branch": target,
            "can_merge": can_merge,
            "has_conflict": not can_merge,
            "conflict_files": conflicts,
            "summary": "可无冲突合并，工作区未被修改。"
            if can_merge
            else (
                "存在合并冲突：" + (", ".join(conflicts) if conflicts else stderr.strip() or "请检查分支和 Git 版本。")
            ),
            "diff_summary": stdout[:1500],
            "test_passed": False,
            "action_items": ["审查差异并运行项目测试"],
        }
    )


gitflow_routes = [
    Route("/api/gitflow/topology", get_gitflow_topology, methods=["GET"]),
    Route("/api/branches", create_branch, methods=["POST"]),
    Route("/api/branches/{branch_name:path}", delete_branch, methods=["DELETE"]),
    Route("/api/branches/checkout", checkout_branch, methods=["POST"]),
    Route("/api/branches/merge", merge_branch, methods=["POST"]),
    Route("/api/merge-review", merge_review, methods=["POST"]),
]
