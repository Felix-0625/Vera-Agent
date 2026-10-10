# README Audit — `vera-agent/README.md`

## BLUF (Bottom line)

The README is a **stale, partially-renamed fork**. A hand-written "VeraAgent" intro banner
(lines 1–13) was prepended onto an otherwise **verbatim copy of the upstream
`mini-swe-agent` README** (lines 14–208). The result is a document that:

1. Contradicts itself immediately (brands itself `VeraAgent` then says `mini is ...`).
2. Describes an architecture ("bash-only, one tool, ~100 lines") that is **false** for the
   actual codebase, which ships a large tool suite, a server, sessions, worktrees, etc.
3. Is littered with dead/broken links, wrong URLs, and mislabeled badges.
4. Retains upstream identity (PyPI name is `vera-agent` but body references `mini-swe-agent`).

**Recommendation:** Treat this as a **rewrite**, not a patch. Expand the intro block into an
accurate project description and delete/rewrite everything below it that refers to
`mini` / `mini-swe-agent` / SWE-bench-leaderboard boilerplate. Budget: small (doc-only change).

---

## Evidence & findings

### A. Identity / branding conflict (severe)

| Item | README says | Reality (verified) |
|---|---|---|
| Title | `# VeraAgent (`vera-agent`)` (L1) | `pyproject.toml` L7 `name = "vera-agent"` OK |
| Self-reference | "`mini` is ..." (L14), "the `mini` agent" (L31, L54) | Package/CLI is `vera` / `vera-agent`; `mini`, `mini-swe-agent`, `mini-extra` are only **aliases** (`pyproject.toml` L89–95) |
| Tagline | "Evolved from mini-swe-agent ..." (L5) | Accurate as lineage, but body never follows through |

The transition `L13 → L14` is abrupt and broken: the reader finishes a 7-bullet feature
list about worktrees/compaction then reads `` `mini` is `` with no antecedent. Clear
signature of a careless copy-paste merge.

### B. Architectural description is factually wrong (severe)

README core claims: L33/L62 *"Does not have any tools other than bash"*; L17 *"Just some 100
lines of python for the agent class"*.

Verified reality:
- `src/vera_agent/tools/` contains **7 tool modules**: `code_tools.py`, `handoff_tools.py`,
  `ops.py`, `primitives.py`, `skill_tools.py`, `subagent_tools.py`, `web_tools.py`.
- `src/vera_agent/agents/default.py` is **346 lines** (not ~100).
- Extra subsystems not mentioned by the "bash-only" narrative:
  `src/vera_agent/server/` (app.py, routes/, state.py), `src/vera_agent/session/`,
  `src/vera_agent/config/`, `src/vera_agent/utils/`.

The two most prominent technical claims in the README are false for this repo.

### C. Broken / wrong internal links (high)

Links in L17–18 point to the **upstream SWE-agent GitHub repo** and use paths that don't
exist (old root path mixed with new `src/` tree):

- `.../SWE-agent/mini-swe-agent/blob/main/src/vera_agent/agents/default.py` — wrong repo
  (SWE-agent, not this fork) AND impossible directory combo.
- Same pattern for `environments/local.py`, `models/litellm_model.py`, `run/hello_world.py`.

None resolve to real files upstream, and none point at this fork.

### D. External URLs / badges (high)

- L23 Codecov badge + link point to `SWE-agent/mini-swe-agent` — not this project.
- `pyproject.toml` L85–87 still carry `mini-swe-agent.com` docs and
  `SWE-agent/mini-swe-agent` repo/bug-tracker URLs (adjacent config defect, same root cause).
- Numerous `mini-swe-agent.com/latest/...` doc deep-links throughout (L41, L45, L67, L99+)
  are upstream docs, not this project's.

### E. Content that does not describe this project (medium)

- `<details>` blocks "Should I use SWE-agent or mini-SWE-agent?" (L73–94) and
  "More motivation (for research)/(as a tool)" (L25–71) are pure upstream boilerplate.
- "Widely adopted: Used by Meta, NVIDIA, Essential AI, IBM, ..." (L16) and
  "Scores >74% on SWE-bench" (L19) are upstream `mini` claims carried over unadapted.
- Upstream typo preserved verbatim: "bublewrap" (L20, should be `bubblewrap`).

### F. Minor style / quality

- L14 `` `mini` is `` — incomplete sentence / dangling subject.
- Raw HTML `<table>` gallery (L96+) and long lines are upstream formatting; screenshot/demo
  assets almost certainly reference upstream images.
- Inconsistent tone: new banner (marketing bullets) vs. old body (research-motivation prose).

---

## Recommendations (ordered, minimal-friction)

1. **Rewrite the body below the banner.** Either delete lines 14–208 and write an accurate
   VeraAgent description (tools, server, sessions, worktrees, models, environments), or keep
   a clearly-labeled trimmed "lineage from mini-swe-agent" section — stripping all
   first-person claims that are false for this repo.
2. **Fix every link** to point at this repo (or remove). Minimum: L17–18, L23, and the
   `mini-swe-agent.com` doc links.
3. **Fix `pyproject.toml` L85–87** project URLs (separate but same-root defect).
4. **Remove/rewrite** the SWE-agent-vs-mini comparison and adoption/benchmark claims.
5. Fix "bublewrap" → "bubblewrap" (L20).

## Scope note (for Main Agent)

Documentation-only change. Touches `vera-agent/README.md` (optionally `pyproject.toml`
`[project.urls]`). No runtime code affected. Suggest a `docs: description` commit per
AGENTS.md conventions.

## Verification commands used

```bat
git rev-parse --show-toplevel            => C:/Users/FAST/Desktop/Multi-agents
git rev-parse --show-prefix              => vera-agent/
git hash-object README.md                => c81654d0... (matches index, no local edits)
git show HEAD:vera-agent/README.md       => 208 lines
dir src\vera_agent\tools                 => 7 tool modules (contradicts "bash only")
find /c /v "" src\vera_agent\agents\default.py   => 346 lines
```
