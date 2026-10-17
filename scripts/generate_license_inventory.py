"""Generate a versioned license inventory from a clean release Python env and npm lockfile."""

from __future__ import annotations

import argparse
from datetime import date
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "THIRD_PARTY_LICENSES.md"


def python_inventory(interpreter: Path) -> list[tuple[str, str, str]]:
    payload = r"""
import json
from importlib import metadata
from pathlib import Path
import re

def license_for(dist):
    expression = dist.metadata.get('License-Expression')
    if expression:
        return expression
    text = (dist.metadata.get('License') or '').strip()
    if text and text.lower() not in {'unknown', 'n/a'}:
        if 'Permission is hereby granted' in text and 'MIT License' in text:
            return 'MIT'
        return text.splitlines()[0][:160]
    classifiers = [c.removeprefix('License :: ') for c in (dist.metadata.get_all('Classifier') or []) if c.startswith('License :: ')]
    if classifiers:
        return '; '.join(classifiers)
    for entry in dist.files or []:
        path_text = str(entry).replace('\\', '/')
        if not re.search(r'(^|/)(licenses?/)?(license|copying|notice)(\.[^/]*)?$', path_text, re.I):
            continue
        try:
            content = dist.locate_file(entry).read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        first = next((line.strip() for line in content.splitlines() if line.strip()), '')
        if 'MIT License' in content[:500] or first.lower() == 'mit license':
            return 'MIT (license file)'
        if 'Apache License' in content[:500]:
            return 'Apache-2.0 (license file)'
        if 'Mozilla Public License' in content[:500]:
            return 'MPL-2.0 (license file)'
        if first:
            return 'See license file: ' + first[:100]
    return 'UNKNOWN — review required'

rows = []
for dist in metadata.distributions():
    name = dist.metadata.get('Name')
    if not name or name.lower().replace('_', '-') == 'vera-agent':
        continue
    rows.append((name, dist.version, license_for(dist)))
print(json.dumps(sorted(rows, key=lambda row: row[0].lower()), ensure_ascii=False))
"""
    completed = subprocess.run(
        [str(interpreter), "-c", payload],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    rows = json.loads(completed.stdout)
    return [(str(name), str(version), str(license_name)) for name, version, license_name in rows]


def frontend_inventory() -> list[tuple[str, str, str, str]]:
    lock = json.loads((ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8"))
    rows = []
    for path, package in lock.get("packages", {}).items():
        if not path.startswith("node_modules/"):
            continue
        name = path.removeprefix("node_modules/")
        rows.append(
            (
                name,
                str(package.get("version", "unknown")),
                str(package.get("license", "UNKNOWN — review required")),
                "development" if package.get("dev") else "runtime",
            )
        )
    return sorted(rows, key=lambda row: row[0].lower())


def markdown_cell(value: str) -> str:
    return value.replace("|", "&#124;")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python",
        required=True,
        type=Path,
        help="Python executable for a clean install of the locked Windows desktop runtime dependencies",
    )
    args = parser.parse_args()

    python_rows = python_inventory(args.python.resolve())
    npm_rows = frontend_inventory()
    lines = [
        "# Third-party dependency license inventory",
        "",
        f"Generated on {date.today().isoformat()} from the locked Windows desktop runtime environment and `frontend/package-lock.json`.",
        "The Python section reflects packages installed in the supplied environment; create that environment from the locked `desktop` extra before regenerating.",
        "The npm section includes every package in the lockfile, including development-only and platform-specific packages.",
        "License strings come from distribution metadata, license files, classifiers, or npm lock metadata. `UNKNOWN` requires maintainer review.",
        "This inventory is not legal advice and does not replace retaining upstream notices in redistributed artifacts.",
        "",
        "## Regenerate on Windows",
        "",
        "Run these commands from the repository root after changing a dependency lockfile:",
        "",
        "```powershell",
        "$auditEnv = Join-Path $env:TEMP 'veraagent-license-audit'",
        "$requirements = Join-Path $env:TEMP 'veraagent-release-requirements.txt'",
        "uv venv $auditEnv --python 3.12",
        "uv export --project vera-agent --locked --no-dev --extra desktop --no-hashes --no-annotate --no-header --format requirements-txt | Set-Content -LiteralPath $requirements -Encoding utf8",
        "uv pip install --directory vera-agent --python (Join-Path $auditEnv 'Scripts/python.exe') -r $requirements",
        "python scripts/generate_license_inventory.py --python (Join-Path $auditEnv 'Scripts/python.exe')",
        "```",
        "",
        f"Python packages: {len(python_rows)}; frontend lockfile packages: {len(npm_rows)}.",
        "",
        "## Python Windows desktop runtime",
        "",
        "| Package | Version | License metadata |",
        "| --- | --- | --- |",
    ]
    lines.extend(f"| `{name}` | `{version}` | {markdown_cell(license_name)} |" for name, version, license_name in python_rows)
    lines.extend(
        [
            "",
            "## Frontend npm lockfile",
            "",
            "| Package | Version | License metadata | Scope |",
            "| --- | --- | --- | --- |",
        ]
    )
    lines.extend(
        f"| `{name}` | `{version}` | {markdown_cell(license_name)} | {scope} |"
        for name, version, license_name, scope in npm_rows
    )
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    unknown_python = [row for row in python_rows if "UNKNOWN" in row[2]]
    unknown_npm = [row for row in npm_rows if "UNKNOWN" in row[2]]
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)} ({len(python_rows)} Python, {len(npm_rows)} npm packages).")
    if unknown_python or unknown_npm:
        print(f"Unknown license metadata: {len(unknown_python)} Python, {len(unknown_npm)} npm packages.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
