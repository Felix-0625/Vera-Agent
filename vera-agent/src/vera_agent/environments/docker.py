"""Execute agent commands inside Docker containers."""

import base64
import json
import logging
import os
import platform
import shlex
import subprocess
import uuid
from typing import Any

from pydantic import BaseModel

from vera_agent.exceptions import Submitted
from vera_agent.utils.serialize import recursive_merge


class DockerEnvironmentConfig(BaseModel):
    image: str
    cwd: str = "/"
    """Working directory in which to execute commands."""
    env: dict[str, str] = {}
    """Environment variables to set in the container."""
    forward_env: list[str] = []
    """Environment variables to forward to the container.
    Variables are only forwarded if they are set in the host environment.
    In case of conflict with `env`, the `env` variables take precedence.
    """
    timeout: int = 30
    """Timeout for executing commands in the container."""
    executable: str = os.getenv("MSWEA_DOCKER_EXECUTABLE", "docker")
    """Path to the docker/container executable."""
    run_args: list[str] = ["--rm"]
    """Additional arguments to pass to the docker/container executable.
    Default is ["--rm"], which removes the container after it exits.
    """
    container_timeout: str = "2h"
    """Max duration to keep container running. Uses the same format as the sleep command."""
    pull_timeout: int = 120
    """Timeout in seconds for pulling images."""
    interpreter: list[str] = ["bash", "-lc"]
    """Interpreter to use to execute commands. Default is ["bash", "-lc"].
    The actual command will be appended as argument to this. Override this to e.g., modify shell flags
    (e.g., to remove the `-l` flag to disable login shell) or to use python instead of bash to interpret commands.
    """


class DockerEnvironment:
    def __init__(
        self,
        *,
        config_class: type = DockerEnvironmentConfig,
        logger: logging.Logger | None = None,
        **kwargs,
    ):
        """This class executes bash commands in a Docker container using direct docker commands.
        See `DockerEnvironmentConfig` for keyword arguments.
        """
        self.logger = logger or logging.getLogger("vera_agent.environment")
        self.container_id: str | None = None
        self.config = config_class(**kwargs)
        self._start_container()

    def get_template_vars(self, **kwargs) -> dict[str, Any]:
        return recursive_merge(self.config.model_dump(), platform.uname()._asdict(), kwargs)

    def serialize(self) -> dict:
        return {
            "info": {
                "config": {
                    "environment": self.config.model_dump(mode="json"),
                    "environment_type": f"{self.__class__.__module__}.{self.__class__.__name__}",
                }
            }
        }

    def _start_container(self):
        """Start the Docker container and return the container ID."""
        container_name = f"vera_agent-{uuid.uuid4().hex[:8]}"
        cmd = [
            self.config.executable,
            "run",
            "-d",
            "--name",
            container_name,
            "-w",
            self.config.cwd,
            *self.config.run_args,
            self.config.image,
            "sleep",
            self.config.container_timeout,
        ]
        self.logger.debug(f"Starting container with command: {shlex.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.config.pull_timeout,  # docker pull might take a while
            check=True,
        )
        self.logger.info(f"Started container {container_name} with ID {result.stdout.strip()}")
        self.container_id = result.stdout.strip()

    def _execute_tool_in_container(self, action: dict, cwd: str, timeout: int | None = None) -> dict[str, Any]:
        """Execute read, write, or edit inside the Docker container using Python."""
        tool_name = action.get("tool_name")
        payload = {
            "tool_name": tool_name,
            "path": action.get("path"),
            "content": action.get("content"),
            "edits": action.get("edits"),
            "offset": action.get("offset", 1),
            "limit": action.get("limit", 2000),
            "cwd": cwd,
        }
        b64_payload = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
        runner_code = (
            "import base64, json, sys, difflib\n"
            "from pathlib import Path\n"
            f"payload = json.loads(base64.b64decode('{b64_payload}').decode('utf-8'))\n"
            "tool_name = payload['tool_name']\n"
            "cwd_path = Path(payload['cwd']).resolve()\n"
            "target = (cwd_path / payload['path']).resolve()\n"
            "\n"
            "if tool_name == 'read':\n"
            "    if not target.exists():\n"
            "        res = {'output': f\"Error: File '{payload['path']}' not found.\", 'returncode': 1, 'exception_info': 'FileNotFound'}\n"
            "    elif target.is_dir():\n"
            "        res = {'output': f\"Error: '{payload['path']}' is a directory, not a file.\", 'returncode': 1, 'exception_info': 'IsADirectoryError'}\n"
            "    else:\n"
            "        try:\n"
            "            content = target.read_text(encoding='utf-8', errors='replace')\n"
            "            lines = content.splitlines()\n"
            "            start_idx = max(0, payload['offset'] - 1)\n"
            "            limit = payload['limit']\n"
            "            end_idx = len(lines) if limit is None else min(len(lines), start_idx + limit)\n"
            "            numbered = [f'{i+1:6d} | {l}' for i, l in enumerate(lines[start_idx:end_idx], start=start_idx)]\n"
            "            out = f\"[File: {payload['path']} | Total lines: {len(lines)} | Showing lines {start_idx+1}-{end_idx}]\\n\" + '\\n'.join(numbered)\n"
            "            if end_idx < len(lines):\n"
            '                out += f"\\n[... {len(lines) - end_idx} more lines truncated. Use offset={end_idx+1} to continue reading ...]"\n'
            "            res = {'output': out, 'returncode': 0, 'exception_info': ''}\n"
            "        except Exception as e:\n"
            "            res = {'output': f'Error reading file: {e}', 'returncode': 1, 'exception_info': str(e)}\n"
            "\n"
            "elif tool_name == 'write':\n"
            "    try:\n"
            "        target.parent.mkdir(parents=True, exist_ok=True)\n"
            "        target.write_text(payload['content'], encoding='utf-8')\n"
            "        res = {'output': f\"Successfully wrote {len(payload['content'])} characters ({len(payload['content'].splitlines())} lines) to '{payload['path']}'.\", 'returncode': 0, 'exception_info': ''}\n"
            "    except Exception as e:\n"
            "        res = {'output': f'Error writing file: {e}', 'returncode': 1, 'exception_info': str(e)}\n"
            "\n"
            "elif tool_name == 'edit':\n"
            "    if not target.exists():\n"
            "        res = {'output': f\"Error: File '{payload['path']}' not found.\", 'returncode': 1, 'exception_info': 'FileNotFound'}\n"
            "    elif target.is_dir():\n"
            "        res = {'output': f\"Error: '{payload['path']}' is a directory, not a file.\", 'returncode': 1, 'exception_info': 'IsADirectoryError'}\n"
            "    else:\n"
            "        try:\n"
            "            orig = target.read_text(encoding='utf-8', errors='replace')\n"
            "            content = orig.replace('\\r\\n', '\\n')\n"
            "            err = None\n"
            "            for i, ed in enumerate(payload['edits'], start=1):\n"
            "                old_text = ed.get('oldText', '').replace('\\r\\n', '\\n')\n"
            "                new_text = ed.get('newText', '').replace('\\r\\n', '\\n')\n"
            "                if not old_text:\n"
            "                    err = f\"Error in edit #{i}: 'oldText' cannot be empty.\"; break\n"
            "                cnt = content.count(old_text)\n"
            "                if cnt == 0:\n"
            "                    err = f\"Error in edit #{i}: 'oldText' not found in '{payload['path']}'. Ensure exact match.\"; break\n"
            "                if cnt > 1:\n"
            "                    err = f\"Error in edit #{i}: 'oldText' matched {cnt} times in '{payload['path']}'. Provide more context.\"; break\n"
            "                content = content.replace(old_text, new_text, 1)\n"
            "            if err:\n"
            "                res = {'output': err, 'returncode': 1, 'exception_info': 'EditError'}\n"
            "            else:\n"
            "                diff = ''.join(difflib.unified_diff(orig.replace('\\r\\n','\\n').splitlines(True), content.splitlines(True), fromfile=f\"a/{payload['path']}\", tofile=f\"b/{payload['path']}\"))\n"
            "                final_content = content.replace('\\n', '\\r\\n') if '\\r\\n' in orig else content\n"
            "                target.write_text(final_content, encoding='utf-8')\n"
            "                res = {'output': f\"Successfully applied {len(payload['edits'])} edit(s) to '{payload['path']}':\\n\\n```diff\\n{diff}```\", 'returncode': 0, 'exception_info': ''}\n"
            "        except Exception as e:\n"
            "            res = {'output': f'Error editing file: {e}', 'returncode': 1, 'exception_info': str(e)}\n"
            "print('__MSWEA_JSON_START__' + json.dumps(res))\n"
        )
        cmd = [self.config.executable, "exec", self.container_id, "python3", "-c", runner_code]
        try:
            result = subprocess.run(
                cmd,
                text=True,
                timeout=timeout or self.config.timeout,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            stdout = result.stdout or ""
            if "__MSWEA_JSON_START__" in stdout:
                json_part = stdout.split("__MSWEA_JSON_START__", 1)[1].strip()
                return json.loads(json_part)
            return {"output": stdout, "returncode": result.returncode, "exception_info": ""}
        except Exception as e:
            return {
                "output": f"Error running tool '{tool_name}' in container: {e}",
                "returncode": 1,
                "exception_info": str(e),
            }

    def execute(self, action: dict, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        """Execute a tool action (read, write, edit, bash) in the Docker container."""
        tool_name = action.get("tool_name")
        cwd = cwd or self.config.cwd
        assert self.container_id, "Container not started"

        if tool_name in ("read", "write", "edit"):
            return self._execute_tool_in_container(action, cwd, timeout=timeout)

        command = action.get("command", "")
        cmd = [self.config.executable, "exec", "-w", cwd]
        for key in self.config.forward_env:
            if (value := os.getenv(key)) is not None:
                cmd.extend(["-e", f"{key}={value}"])
        for key, value in self.config.env.items():
            cmd.extend(["-e", f"{key}={value}"])
        cmd.extend([self.container_id, *self.config.interpreter, command])

        try:
            result = subprocess.run(
                cmd,
                text=True,
                timeout=timeout or self.config.timeout,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            output = {"output": result.stdout, "returncode": result.returncode, "exception_info": ""}
        except Exception as e:
            raw_output = getattr(e, "output", None)
            raw_output = (
                raw_output.decode("utf-8", errors="replace") if isinstance(raw_output, bytes) else (raw_output or "")
            )
            output = {
                "output": raw_output,
                "returncode": -1,
                "exception_info": f"An error occurred while executing the command: {e}",
                "extra": {"exception_type": type(e).__name__, "exception": str(e)},
            }
        self._check_finished(output)
        return output

    def _check_finished(self, output: dict):
        """Raises Submitted if the output indicates task completion."""
        lines = output.get("output", "").lstrip().splitlines(keepends=True)
        if lines and lines[0].strip() == "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" and output["returncode"] == 0:
            submission = "".join(lines[1:])
            raise Submitted(
                {
                    "role": "exit",
                    "content": submission,
                    "extra": {"exit_status": "Submitted", "submission": submission},
                }
            )

    def cleanup(self):
        """Stop and remove the Docker container."""
        if getattr(self, "container_id", None) is not None:  # if init fails early, container_id might not be set
            if platform.system() == "Windows":
                cmd = [self.config.executable, "rm", "-f", self.container_id]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                cmd = f"(timeout 60 {self.config.executable} stop {self.container_id} || {self.config.executable} rm -f {self.container_id}) >/dev/null 2>&1 &"
                subprocess.Popen(cmd, shell=True)

    def __del__(self):
        """Cleanup container when object is destroyed."""
        self.cleanup()
