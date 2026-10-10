import os
import platform
import signal
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from vera_agent.exceptions import Submitted
from vera_agent.tools import edit_file_op, read_file_op, write_file_op
from vera_agent.utils.serialize import recursive_merge


class LocalEnvironmentConfig(BaseModel):
    cwd: str = ""
    env: dict[str, str] = {}
    timeout: int = 30
    allowed_write_prefix: str | None = None
    allow_external_read: bool = False
    max_output_lines: int = 800
    max_output_bytes: int = 40000


class LocalEnvironment:
    def __init__(self, *, config_class: type = LocalEnvironmentConfig, **kwargs):
        """This class executes tools and bash commands directly on the local machine."""
        self.config = config_class(**kwargs)

    def execute(self, action: dict, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        """Execute a tool action (read, write, edit, bash) in the local environment."""
        tool_name = action.get("tool_name")
        cwd_path = Path(cwd or self.config.cwd or os.getcwd()).resolve()

        if tool_name == "read":
            output = read_file_op(
                path=action["path"],
                offset=action.get("offset", 1),
                limit=action.get("limit", 2000),
                base_dir=cwd_path,
                allow_external_read=self.config.allow_external_read,
            )
        elif tool_name == "write":
            target_path_str = str(action.get("path", "")).replace("\\", "/")
            if ".agents/registries" in target_path_str:
                output = {
                    "output": "Permission Denied: Direct modification of .agents/registries/ by agent is strictly prohibited. The registry is exclusively managed by the host system.",
                    "returncode": 1,
                    "exception_info": "Protected system registry",
                }
            else:
                output = write_file_op(
                    path=action["path"],
                    content=action["content"],
                    base_dir=cwd_path,
                    allowed_write_prefix=self.config.allowed_write_prefix,
                )
        elif tool_name == "edit":
            target_path_str = str(action.get("path", "")).replace("\\", "/")
            if ".agents/registries" in target_path_str:
                output = {
                    "output": "Permission Denied: Direct modification of .agents/registries/ by agent is strictly prohibited. The registry is exclusively managed by the host system.",
                    "returncode": 1,
                    "exception_info": "Protected system registry",
                }
            else:
                output = edit_file_op(
                    path=action["path"],
                    edits=action.get("edits", []),
                    base_dir=cwd_path,
                    allowed_write_prefix=self.config.allowed_write_prefix,
                )
        else:
            command = action.get("command", "")
            cwd_str = str(cwd_path)
            try:
                result = _run(command, cwd_str, os.environ | self.config.env, timeout or self.config.timeout)
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

        # Truncation guard for excessively long outputs
        text = output.get("output", "")
        lines = text.splitlines()
        max_lines = self.config.max_output_lines
        max_bytes = self.config.max_output_bytes

        if len(lines) > max_lines or len(text) > max_bytes:
            truncated_lines = lines[:max_lines]
            truncated_text = "\n".join(truncated_lines)
            if len(truncated_text) > max_bytes:
                truncated_text = truncated_text[:max_bytes]
            output["output"] = (
                truncated_text + f"\n\n[... Warning: Tool output truncated. Exceeded limit ({max_lines} lines / {max_bytes} bytes). ...]"
            )

        return output

    def _check_finished(self, output: dict):
        """Raises Submitted if the output indicates task completion."""
        lines = output.get("output", "").lstrip().splitlines(keepends=True)
        if lines and lines[0].strip().strip("'\"") == "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" and output["returncode"] == 0:
            if os.name == "nt":
                submission_lines = []
                for l in lines[1:]:
                    stripped = l.strip()
                    if (stripped.startswith("'") and stripped.endswith("'")) or (stripped.startswith('"') and stripped.endswith('"')):
                        stripped = stripped[1:-1]
                    submission_lines.append(stripped)
                submission = "\n".join(submission_lines) + ("\n" if lines[1:] else "")
            else:
                submission = "".join(lines[1:])
            raise Submitted(
                {
                    "role": "exit",
                    "content": submission,
                    "extra": {"exit_status": "Submitted", "submission": submission},
                }
            )

    def get_template_vars(self, **kwargs) -> dict[str, Any]:
        return recursive_merge(self.config.model_dump(), platform.uname()._asdict(), os.environ, kwargs)

    def serialize(self) -> dict:
        return {
            "info": {
                "config": {
                    "environment": self.config.model_dump(mode="json"),
                    "environment_type": f"{self.__class__.__module__}.{self.__class__.__name__}",
                }
            }
        }


def _run(command: str, cwd: str, env: dict[str, str], timeout: int) -> subprocess.CompletedProcess[str]:
    """Like subprocess.run, but kills the whole process group on timeout so no children are orphaned."""
    if os.name == "nt" and "\n" in command:
        command = " & ".join(line.strip() for line in command.splitlines() if line.strip())
    process = subprocess.Popen(
        command,
        shell=True,
        text=True,
        cwd=cwd,
        env=env,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=os.name == "posix",
    )
    try:
        stdout, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            # With shell=True, killing cmd.exe alone can leave its child process
            # alive with stdout open, which makes communicate() wait past timeout.
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=5,
                )
            except (OSError, subprocess.TimeoutExpired):
                process.kill()
        stdout, _ = process.communicate()
        raise subprocess.TimeoutExpired(command, timeout, output=stdout)
    return subprocess.CompletedProcess(command, process.returncode, stdout=stdout)
