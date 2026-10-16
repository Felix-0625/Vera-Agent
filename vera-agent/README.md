# VeraAgent Python Backend

This directory contains the Python package used by the VeraAgent desktop app: the Agent loop, model adapters, local execution tools, session state, and Starlette API.

## Local development

From this directory, create a Python 3.10+ environment and install the desktop extra:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[desktop,dev]"
```

The desktop UI must be built from `../frontend` before opening the pywebview shell. From the repository root, run `./start-desktop.ps1`. The API alone can be started with:

```powershell
python -m uvicorn vera_agent.server.app:create_app --factory --host 127.0.0.1 --port 8000
```

## Tests

Run `python -m pytest tests` from this directory. The test tree includes API, configuration, model, session, tool, and runtime tests. Some tests use temporary repositories or fake model responses; they do not establish live-provider quality or production readiness. See [../docs/TESTING.md](../docs/TESTING.md).

## Package lineage

This package retains code derived from mini-swe-agent. Preserve the upstream MIT notice in `LICENSE.md`; see the repository-level [NOTICE](../NOTICE.md) and [license notes](../docs/LICENSES.md). Do not infer upstream authorship of VeraAgent-specific additions from the inherited package metadata.
