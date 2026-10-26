"""Evaluation of the product's real chat pipeline: cases, profiles, a headless runner, and comparisons.

- `cases.py`: YAML eval cases (task, fixture repo, acceptance script, tags, split).
- `profile.py`: versioned agent profiles (prompt overlay, rules, Skills, memory snapshot).
- `sandbox.py`: disposable per-run workspaces with an isolated `.agents` config root.
- `runner.py`: drives `server/chat/turn.py:run_turn` headlessly and runs the acceptance script.
- `compare.py`: paired comparison of two profiles with a bootstrap interval and a verdict.
- `cli.py`: ``vera-eval run --profile baseline --profile candidate --split holdout``.

Built-in cases live in `evals/cases/`; project cases can be added under `<project>/.agents/evals/cases/`.
"""
