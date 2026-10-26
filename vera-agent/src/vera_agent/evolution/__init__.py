"""Evaluation-gated self-improvement: Critic proposals, an eval gate, adoption and monitoring.

Two loops:

- Fast loop (memory layer): facts and preferences are stored as the user works, take effect at
  once and stay undoable (`vera_agent/memory/`).
- Slow loop (this package): rules, Skills and prompt overlays change behaviour for every turn, so
  they must pass the eval gate and get the user's approval before they take effect:

  low-score trace -> `critic.py` proposal -> `gate.py` train/holdout/guard runs -> user review
  -> `adoption.py` (rule memory or `.agents/skills/<name>/`) -> `monitor.py` online check / rollback

`case_drafts.py` turns each low-score trace into an eval case draft that the user completes;
the optimizer never writes `evals/cases/` or the scorers.
"""
