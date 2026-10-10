"""Batch refactoring script: safely rename minisweagent imports to vera_agent."""

from pathlib import Path

root = Path("vera-agent").resolve()
extensions = {".py", ".yaml", ".yml", ".toml", ".md", ".json", ".sh"}

count = 0
for path in root.rglob("*"):
    if not path.is_file() or path.suffix not in extensions:
        continue
    parts = path.parts
    if any(p in (".venv", ".git", "__pycache__", "build", "dist", "vera_agent.egg-info", "mini_swe_agent.egg-info") for p in parts):
        continue
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        continue
    if "minisweagent" in content:
        new_content = content.replace("minisweagent", "vera_agent")
        path.write_text(new_content, encoding="utf-8")
        count += 1
        print(f"Updated: {path.relative_to(root)}")

print(f"Successfully updated {count} files.")
