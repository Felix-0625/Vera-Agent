"""``vera-eval``: run eval cases against one or more profiles and compare them.

Examples::

    vera-eval list
    vera-eval run --profile baseline --split guard
    vera-eval run --profile baseline --profile candidate --split holdout --repeats 3

Runs call the configured model and cost money; they are never part of `tests/check-all.ps1`.
``--config-root`` is the folder whose `.agents/models_config.json` holds the model settings
(default: the current directory, as for the desktop backend). Reports are saved under
`<config root>/.agents/evals/reports/`.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from vera_agent.evals.cases import SPLITS, load_cases
from vera_agent.evals.profile import ProfileStore
from vera_agent.evals.report import build_report, render_markdown, save_report
from vera_agent.evals.runner import run_suite
from vera_agent.server.model_profile import resolve_model_profile
from vera_agent.server.state import ServerState

app = typer.Typer(rich_markup_mode="rich", help="Evaluate VeraAgent's chat pipeline on eval cases.")
console = Console()


def _case_dirs(config_root: Path, extra: list[Path] | None) -> list[Path]:
    from vera_agent.evals.cases import BUILTIN_CASES_DIR

    project_cases = config_root / ".agents" / "evals" / "cases"
    return [BUILTIN_CASES_DIR, *([project_cases] if project_cases.is_dir() else []), *(extra or [])]


@app.command("list")
def list_cases(
    config_root: Path = typer.Option(Path.cwd(), help="Folder holding .agents/ settings."),
    split: list[str] = typer.Option(None, help="Only these splits."),
) -> None:
    """List the available eval cases."""
    for case in load_cases(_case_dirs(config_root, None), splits=split or None):
        console.print(f"[bold]{case.case_id}[/bold] [{case.split}] {', '.join(case.tags)} - {case.task[:80]}")


@app.command("run")
def run(
    profile: list[str] = typer.Option(["baseline"], help="Profile ids; the first is the baseline."),
    split: list[str] = typer.Option(None, help=f"Splits to run ({', '.join(SPLITS)}); default all."),
    case: list[str] = typer.Option(None, help="Only these case ids."),
    cases_dir: list[Path] = typer.Option(None, help="Additional case directories."),
    repeats: int = typer.Option(1, min=1, max=10, help="Runs per case and profile."),
    model_id: str = typer.Option("", help="Model id from 设置 → 模型; default model when empty."),
    config_root: Path = typer.Option(Path.cwd(), help="Folder holding .agents/ settings."),
) -> None:
    """Run cases for each profile, then print and save the comparison report."""
    for value in split or []:
        if value not in SPLITS:
            raise typer.BadParameter(f"Unknown split {value!r}")
    cases = load_cases(_case_dirs(config_root, cases_dir), splits=split or None)
    if case:
        cases = [item for item in cases if item.case_id in set(case)]
    if not cases:
        raise typer.BadParameter("No eval cases matched.")
    state = ServerState(repo_root=config_root)
    resolved = resolve_model_profile(state, model_id or None)
    models_config = state.load_json_config("models_config.json", {"models": []})
    profiles = [ProfileStore.for_config_root(config_root).load(profile_id) for profile_id in profile]
    console.print(
        f"Running {len(cases)} case(s) x {repeats} repeat(s) x {len(profiles)} profile(s) on {resolved['name']}"
    )

    def show(result) -> None:
        mark = "[green]pass[/green]" if result.passed else "[red]fail[/red]"
        console.print(f"  {result.case_id} [{result.profile_id} #{result.repeat}] {mark} {result.error}")

    results = run_suite(
        cases, profiles, models_config, resolved["config"].get("id", ""), repeats=repeats, on_result=show
    )
    report = build_report(
        results, [item.profile_id for item in profiles], splits=split or list(SPLITS), repeats=repeats
    )
    path = save_report(config_root, report)
    console.print(render_markdown(report))
    console.print(f"Report saved to {path}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
