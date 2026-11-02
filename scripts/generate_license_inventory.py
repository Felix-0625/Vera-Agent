"""Generate a versioned license inventory from a clean release Python env and npm lockfile."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "THIRD_PARTY_LICENSES.md"


def python_inventory(interpreter: Path) -> tuple[str, list[tuple[str, str, str]]]:
    payload = r"""
import json
from importlib import metadata
from pathlib import Path
import re
import sys

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
print(json.dumps({
    'python': '.'.join(map(str, sys.version_info[:2])),
    'packages': sorted(rows, key=lambda row: row[0].lower()),
}, ensure_ascii=False))
"""
    completed = subprocess.run(
        [str(interpreter), "-c", payload],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    result = json.loads(completed.stdout)
    rows = result["packages"]
    return str(result["python"]), [(str(name), str(version), str(license_name)) for name, version, license_name in rows]


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


def update_frontend_only() -> None:
    """Refresh npm metadata without claiming to re-audit unchanged Python environments."""
    rows = frontend_inventory()
    current = REPORT_PATH.read_text(encoding="utf-8")
    marker = "## Frontend npm lockfile"
    if marker not in current:
        raise SystemExit("Existing Python inventory missing; run the full generator first.")
    head = current.split(marker, 1)[0]
    head = re.sub(r"frontend lockfile packages: \d+", f"frontend lockfile packages: {len(rows)}", head)
    lines = [
        marker,
        "",
        f"npm metadata refreshed on {date.today().isoformat()}; Python inventory above is unchanged.",
        "",
        "| Package | Version | License metadata | Scope |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| `{name}` | `{version}` | {markdown_cell(license_name)} | {scope} |"
        for name, version, license_name, scope in rows
    )
    REPORT_PATH.write_text(head + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"Refreshed {len(rows)} npm rows; retained the dated Python inventory.")
    if any("UNKNOWN" in row[2] for row in rows):
        raise SystemExit("Unknown npm license metadata requires review.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--python",
        nargs="+",
        type=Path,
        help="Python executables for clean installs of the locked Windows desktop runtime dependencies",
    )
    parser.add_argument(
        "--frontend-only", action="store_true", help="Refresh npm rows and retain the existing Python inventory."
    )
    args = parser.parse_args()
    if args.frontend_only:
        if args.python:
            parser.error("Use either --frontend-only or --python, not both.")
        update_frontend_only()
        return
    if not args.python:
        parser.error("--python is required unless --frontend-only is selected.")

    python_inventories = [python_inventory(interpreter.resolve()) for interpreter in args.python]
    npm_rows = frontend_inventory()
    total_python_rows = sum(len(rows) for _, rows in python_inventories)
    lines = [
        "# Third-party dependency license inventory",
        "",
        f"Generated on {date.today().isoformat()} from the locked Windows desktop runtime environments and `frontend/package-lock.json`.",
        "The Python sections cover the declared minimum runtime and the current release-test Python version; both environments are resolved from the locked `desktop` extra.",
        "The npm section includes every package in the lockfile, including development-only and platform-specific packages.",
        "License strings come from distribution metadata, license files, classifiers, or npm lock metadata. `UNKNOWN` requires maintainer review.",
        "This inventory is not legal advice and does not replace retaining upstream notices in redistributed artifacts.",
        "",
        "## Regenerate on Windows",
        "",
        "Run these commands from the repository root after changing a dependency lockfile:",
        "",
        "```powershell",
        "$python310 = Join-Path $env:TEMP 'veraagent-license-audit-310'",
        "$python312 = Join-Path $env:TEMP 'veraagent-license-audit-312'",
        "$env:UV_PROJECT_ENVIRONMENT = $python310",
        "uv sync --project vera-agent --locked --no-dev --extra desktop --python 3.10",
        "$env:UV_PROJECT_ENVIRONMENT = $python312",
        "uv sync --project vera-agent --locked --no-dev --extra desktop --python 3.12",
        "Remove-Item Env:UV_PROJECT_ENVIRONMENT",
        "python scripts/generate_license_inventory.py --python (Join-Path $python310 'Scripts/python.exe') (Join-Path $python312 'Scripts/python.exe')",
        "```",
        "",
        f"Python package rows across supported runtimes: {total_python_rows}; frontend lockfile packages: {len(npm_rows)}.",
    ]
    for version, rows in python_inventories:
        lines.extend(
            [
                "",
                f"## Python {version} Windows desktop runtime",
                "",
                "| Package | Version | License metadata |",
                "| --- | --- | --- |",
            ]
        )
        lines.extend(
            f"| `{name}` | `{package_version}` | {markdown_cell(license_name)} |"
            for name, package_version, license_name in rows
        )
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
    unknown_python = [row for _, rows in python_inventories for row in rows if "UNKNOWN" in row[2]]
    unknown_npm = [row for row in npm_rows if "UNKNOWN" in row[2]]
    print(
        f"Wrote {REPORT_PATH.relative_to(ROOT)} "
        f"({total_python_rows} Python rows across {len(python_inventories)} runtimes, "
        f"{len(npm_rows)} npm packages)."
    )
    if unknown_python or unknown_npm:
        print(f"Unknown license metadata: {len(unknown_python)} Python, {len(unknown_npm)} npm packages.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
