"""Module 2: Project workspace binding and projects history management."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import shutil
import subprocess

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from vera_agent.server.state import ServerState, get_git_branch

logger = logging.getLogger("vera_server.projects")


def _get_state(request: Request) -> ServerState:
    return request.app.state.server_state


async def get_projects(request: Request) -> JSONResponse:
    state = _get_state(request)
    proj_hist = state.load_json_config("projects_history.json", {"projects": []})
    return JSONResponse(proj_hist)


async def get_current_project(request: Request) -> JSONResponse:
    state = _get_state(request)
    current_root = state.root_path
    projects = state.load_json_config("projects_history.json", {"projects": []}).get("projects", [])
    current = next((project for project in projects if project.get("path") == str(current_root)), {})
    return JSONResponse({
        "id": current.get("id"),
        "repo_root": str(current_root),
        "name": current.get("name") or current_root.name,
        "folders": current.get("folders") or [str(current_root)],
        "is_git": (current_root / ".git").exists(),
        "active_branch": get_git_branch(current_root),
    })


def _choose_directory() -> str | None:
    if os.name == "nt":
        powershell = shutil.which("powershell.exe") or shutil.which("pwsh.exe") or "powershell.exe"
        script = (
            "Add-Type -AssemblyName System.Windows.Forms;\n"
            "Add-Type -AssemblyName System.Drawing;\n"
            "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false);\n"
            "$dialog = [System.Windows.Forms.FolderBrowserDialog]::new();\n"
            "$dialog.Description = '选择项目文件夹';\n"
            "$dialog.ShowNewFolderButton = $false;\n"
            "$owner = [System.Windows.Forms.Form]::new();\n"
            "$owner.TopMost = $true;\n"
            "$owner.ShowInTaskbar = $false;\n"
            "$owner.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None;\n"
            "$owner.StartPosition = [System.Windows.Forms.FormStartPosition]::Manual;\n"
            "$owner.Size = [System.Drawing.Size]::new(1, 1);\n"
            "$owner.Opacity = 0;\n"
            "$screen = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea;\n"
            "$owner.Location = [System.Drawing.Point]::new($screen.X + [int]($screen.Width / 2), $screen.Y + [int]($screen.Height / 2));\n"
            "try {\n"
            "    $owner.Show();\n"
            "    $owner.Activate();\n"
            "    if ($dialog.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) {\n"
            "        [Console]::Out.Write($dialog.SelectedPath);\n"
            "    }\n"
            "} finally { $owner.Dispose(); }\n"
        )
        try:
            completed = subprocess.run(
                [powershell, "-NoProfile", "-STA", "-Command", script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=120,
            )
            if completed.returncode:
                logger.warning("PowerShell folder picker failed: %s", completed.stderr.strip())
                raise RuntimeError(completed.stderr.strip() or "系统文件夹选择器启动失败")
            return completed.stdout.strip() or None
        except Exception as exc:
            logger.warning(f"PowerShell folder picker error: {exc}")
            return None

    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(parent=root, title="选择项目文件夹", mustexist=True)
        return selected or None
    finally:
        root.destroy()


async def select_project_folder(request: Request) -> JSONResponse:
    try:
        # Windows dialogs need an STA thread. Run the native picker in a
        # dedicated PowerShell process so it doesn't block the ASGI loop.
        path = await asyncio.to_thread(_choose_directory)
        return JSONResponse({"path": path})
    except Exception as exc:
        logger.exception("Unable to open the native folder picker")
        return JSONResponse({"error": f"无法打开本地文件夹选择器: {exc}"}, status_code=500)


async def bind_project(request: Request) -> JSONResponse:
    state = _get_state(request)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    raw_folders = body.get("folders") or [body.get("repo_root") or body.get("path")]
    if not isinstance(raw_folders, list) or not raw_folders or not all(isinstance(folder, str) and folder.strip() for folder in raw_folders):
        return JSONResponse({"error": "At least one folder path is required"}, status_code=400)
    folders = list(dict.fromkeys(str(Path(folder).expanduser().resolve()) for folder in raw_folders))
    new_repo_root = body.get("repo_root") or body.get("path") or folders[0]
    if not new_repo_root:
        return JSONResponse({"error": "repo_root is required"}, status_code=400)

    target_path = Path(new_repo_root).resolve()
    folders = [str(target_path), *[folder for folder in folders if folder != str(target_path)]]
    for folder in folders:
        folder_path = Path(folder)
        if not folder_path.exists() or not folder_path.is_dir():
            return JSONResponse({"error": f"Path '{folder}' does not exist or is not a directory"}, status_code=400)

    project_name = str(body.get("name") or target_path.name).strip()
    state.init_workspace(target_path, body.get("project_id"), project_name, folders)
    state.sessions.clear()
    project = next((item for item in state.load_json_config("projects_history.json", {"projects": []}).get("projects", []) if item.get("path") == str(target_path)), {})
    return JSONResponse({
        "status": "ok",
        "id": project.get("id"),
        "repo_root": str(state.root_path),
        "name": project.get("name") or state.root_path.name,
        "folders": project.get("folders") or folders,
        "active_branch": get_git_branch(state.root_path),
    })


async def update_project(request: Request) -> JSONResponse:
    state = _get_state(request)
    project_id = request.path_params.get("project_id", "")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    history = state.load_json_config("projects_history.json", {"projects": []})
    project = next((item for item in history.get("projects", []) if item.get("id") == project_id), None)
    if not project:
        return JSONResponse({"error": f"Project '{project_id}' not found"}, status_code=404)

    old_path = str(Path(project.get("path", "")).resolve())
    folders = project.get("folders") or [old_path]
    if "folders" in body:
        raw_folders = body["folders"]
        if not isinstance(raw_folders, list) or not raw_folders or not all(isinstance(folder, str) and folder.strip() for folder in raw_folders):
            return JSONResponse({"error": "At least one folder path is required"}, status_code=400)
        folders = list(dict.fromkeys(str(Path(folder).expanduser().resolve()) for folder in raw_folders))
        for folder in folders:
            folder_path = Path(folder)
            if not folder_path.exists() or not folder_path.is_dir():
                return JSONResponse({"error": f"Path '{folder}' does not exist or is not a directory"}, status_code=400)

    name = body.get("name", project.get("name", ""))
    if not isinstance(name, str) or not name.strip():
        return JSONResponse({"error": "Project name is required"}, status_code=400)

    new_path = folders[0]
    project.update({"name": name.strip(), "path": new_path, "folders": folders})
    if "is_pinned" in body:
        project["is_pinned"] = bool(body["is_pinned"])
    history["projects"] = [project if item.get("id") == project_id else item for item in history["projects"]]
    state.save_json_config("projects_history.json", history)

    if old_path == str(state.root_path.resolve()) and new_path != old_path:
        state.init_workspace(Path(new_path), project_id, name.strip(), folders)
        state.sessions.clear()

    return JSONResponse({"project": project})


async def delete_project(request: Request) -> JSONResponse:
    state = _get_state(request)
    proj_id = request.path_params.get("project_id", "")
    proj_hist = state.load_json_config("projects_history.json", {"projects": []})
    projects = proj_hist.get("projects", [])
    before_len = len(projects)
    projects = [p for p in projects if p.get("id") != proj_id]
    if len(projects) == before_len:
        return JSONResponse({"error": f"Project '{proj_id}' not found"}, status_code=404)

    proj_hist["projects"] = projects
    state.save_json_config("projects_history.json", proj_hist)
    return JSONResponse({"status": "deleted", "project_id": proj_id})


project_routes = [
    Route("/api/projects", get_projects, methods=["GET"]),
    Route("/api/projects/current", get_current_project, methods=["GET"]),
    Route("/api/projects/bind", bind_project, methods=["POST"]),
    Route("/api/projects/select-folder", select_project_folder, methods=["POST"]),
    Route("/api/projects/{project_id}", delete_project, methods=["DELETE"]),
    Route("/api/projects/{project_id}", update_project, methods=["PATCH"]),
]
