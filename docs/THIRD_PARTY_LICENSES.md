# Third-party dependency license inventory

Generated on 2026-10-18 from the locked Windows desktop runtime environments and `frontend/package-lock.json`.
The Python sections cover the declared minimum runtime and the current release-test Python version; both environments are resolved from the locked `desktop` extra.
The npm section includes every package in the lockfile, including development-only and platform-specific packages.
License strings come from distribution metadata, license files, classifiers, or npm lock metadata. `UNKNOWN` requires maintainer review.
This inventory is not legal advice and does not replace retaining upstream notices in redistributed artifacts.

## Vendored website dependency

The static documentation viewer vendors Marked v18.1.1 at
`website/assets/vendor/marked.umd.js`. Its MIT copyright and license notices are retained in
[marked-LICENSE.txt](../website/assets/vendor/marked-LICENSE.txt). This vendored browser asset is
separate from the generated Python/npm inventories below.

## Regenerate on Windows

If only the frontend lockfile changes, run `python scripts/generate_license_inventory.py --frontend-only`.
This refreshes npm rows and keeps the dated Python inventory unchanged. For backend changes, use
the clean runtime environments below.

Run these commands from the repository root after changing a dependency lockfile:

```powershell
$python310 = Join-Path $env:TEMP 'veraagent-license-audit-310'
$python312 = Join-Path $env:TEMP 'veraagent-license-audit-312'
$env:UV_PROJECT_ENVIRONMENT = $python310
uv sync --project vera-agent --locked --no-dev --extra desktop --python 3.10
$env:UV_PROJECT_ENVIRONMENT = $python312
uv sync --project vera-agent --locked --no-dev --extra desktop --python 3.12
Remove-Item Env:UV_PROJECT_ENVIRONMENT
python scripts/generate_license_inventory.py --python (Join-Path $python310 'Scripts/python.exe') (Join-Path $python312 'Scripts/python.exe')
```

Python package rows across supported runtimes: 200; frontend lockfile packages: 122.

## Python 3.10 Windows desktop runtime

| Package | Version | License metadata |
| --- | --- | --- |
| `aiohappyeyeballs` | `2.7.1` | PSF-2.0 |
| `aiohttp` | `3.14.3` | Apache-2.0 AND MIT |
| `aiosignal` | `1.4.0` | Apache 2.0 |
| `annotated-doc` | `0.0.5` | MIT |
| `annotated-types` | `0.8.0` | MIT |
| `anyio` | `4.15.1` | MIT |
| `async-timeout` | `5.0.1` | Apache 2 |
| `attrs` | `26.1.0` | MIT |
| `boto3` | `1.43.108` | Apache-2.0 |
| `botocore` | `1.43.108` | Apache-2.0 |
| `bottle` | `0.13.4` | MIT |
| `certifi` | `2026.7.22` | MPL-2.0 |
| `cffi` | `2.1.1` | MIT-0 |
| `charset-normalizer` | `3.5.2` | MIT |
| `click` | `8.5.0` | BSD-3-Clause |
| `clr_loader` | `0.3.1` | MIT (license file) |
| `colorama` | `0.4.6` | OSI Approved :: BSD License |
| `cryptography` | `50.0.2` | Apache-2.0 OR BSD-3-Clause |
| `datasets` | `5.0.1` | Apache 2.0 |
| `dill` | `0.4.1` | BSD-3-Clause |
| `distro` | `1.9.0` | Apache License, Version 2.0 |
| `exceptiongroup` | `1.3.1` | OSI Approved :: MIT License |
| `fastuuid` | `0.14.0` | OSI Approved :: BSD License |
| `filelock` | `4.0.9` | MIT |
| `frozenlist` | `1.8.0` | Apache-2.0 |
| `fsspec` | `2026.6.0` | BSD-3-Clause |
| `h11` | `0.16.0` | MIT |
| `h2` | `4.4.1` | MIT |
| `hf-xet` | `1.6.0` | Apache-2.0 |
| `hpack` | `4.2.0` | MIT |
| `httpcore` | `1.0.9` | BSD-3-Clause |
| `httpx` | `0.28.1` | BSD-3-Clause |
| `httpx-sse` | `0.4.3` | MIT |
| `huggingface_hub` | `1.33.0` | Apache-2.0 |
| `hyperframe` | `6.1.0` | MIT |
| `idna` | `3.20` | BSD-3-Clause |
| `importlib_metadata` | `8.9.0` | Apache-2.0 |
| `Jinja2` | `3.1.6` | OSI Approved :: BSD License |
| `jiter` | `0.17.0` | MIT |
| `jmespath` | `1.1.0` | MIT |
| `jsonschema` | `4.26.0` | MIT |
| `jsonschema-specifications` | `2025.9.1` | MIT |
| `linkify-it-py` | `2.2.0` | MIT |
| `litellm` | `1.103.2` | MIT |
| `markdown-it-py` | `4.2.0` | OSI Approved :: MIT License |
| `MarkupSafe` | `3.0.4` | BSD-3-Clause |
| `mcp` | `1.30.0` | MIT |
| `mdit-py-plugins` | `0.6.1` | OSI Approved :: MIT License |
| `mdurl` | `0.1.2` | OSI Approved :: MIT License |
| `multidict` | `6.9.1` | Apache License 2.0 |
| `multiprocess` | `0.70.19` | BSD-3-Clause |
| `numpy` | `2.2.6` | Copyright (c) 2005-2024, NumPy Developers. |
| `openai` | `2.54.0` | Apache-2.0 |
| `packaging` | `26.3` | Apache-2.0 OR BSD-2-Clause |
| `pandas` | `2.3.3` | BSD 3-Clause License |
| `platformdirs` | `4.12.2` | MIT |
| `prompt_toolkit` | `3.0.53` | OSI Approved :: BSD License |
| `propcache` | `0.5.4` | Apache-2.0 |
| `proxy_tools` | `0.1.0` | MIT |
| `pyarrow` | `25.0.1` | Apache-2.0 |
| `pycparser` | `3.11` | BSD-3-Clause |
| `pydantic` | `2.13.5` | MIT |
| `pydantic-settings` | `2.15.0` | MIT |
| `pydantic_core` | `2.46.5` | MIT |
| `Pygments` | `2.21.0` | BSD-2-Clause |
| `PyJWT` | `2.15.1` | MIT |
| `python-dateutil` | `2.9.0.post0` | Dual License |
| `python-dotenv` | `1.2.4` | BSD-3-Clause |
| `python-multipart` | `0.0.32` | Apache-2.0 |
| `pythonnet` | `3.1.0` | MIT |
| `pytz` | `2026.4` | MIT |
| `pywebview` | `6.2.1` | BSD 3-Clause License |
| `pywin32` | `312` | PSF |
| `PyYAML` | `6.0.3` | MIT |
| `referencing` | `0.37.0` | MIT |
| `regex` | `2026.9.29` | Apache-2.0 AND CNRI-Python |
| `requests` | `2.34.2` | Apache-2.0 |
| `rich` | `15.0.0` | MIT |
| `rpds-py` | `0.30.0` | MIT |
| `s3transfer` | `0.19.2` | Apache License 2.0 |
| `shellingham` | `1.5.4` | ISC License |
| `six` | `1.17.0` | MIT |
| `sniffio` | `1.3.1` | MIT OR Apache-2.0 |
| `sse-starlette` | `3.5.0` | BSD-3-Clause |
| `starlette` | `1.7.0` | BSD-3-Clause |
| `tenacity` | `9.1.4` | Apache 2.0 |
| `textual` | `8.2.8` | MIT |
| `tiktoken` | `0.14.0` | MIT |
| `tokenizers` | `0.23.2` | OSI Approved :: Apache Software License |
| `tomli` | `2.4.1` | MIT |
| `tqdm` | `4.70.1` | MPL-2.0 AND MIT |
| `typer` | `0.27.2` | MIT |
| `typing-inspection` | `0.4.4` | MIT |
| `typing_extensions` | `4.16.0` | PSF-2.0 |
| `tzdata` | `2026.4` | Apache-2.0 |
| `urllib3` | `2.8.0` | MIT |
| `uvicorn` | `0.54.0` | BSD-3-Clause |
| `wcwidth` | `0.9.1` | OSI Approved :: MIT License |
| `websockets` | `16.1.1` | BSD-3-Clause |
| `xxhash` | `4.0.1` | BSD-2-Clause |
| `yarl` | `1.25.1` | Apache-2.0 |
| `zipp` | `4.1.0` | MIT |

## Python 3.12 Windows desktop runtime

| Package | Version | License metadata |
| --- | --- | --- |
| `aiohappyeyeballs` | `2.7.1` | PSF-2.0 |
| `aiohttp` | `3.14.3` | Apache-2.0 AND MIT |
| `aiosignal` | `1.4.0` | Apache 2.0 |
| `annotated-doc` | `0.0.5` | MIT |
| `annotated-types` | `0.8.0` | MIT |
| `anyio` | `4.15.1` | MIT |
| `attrs` | `26.1.0` | MIT |
| `boto3` | `1.43.108` | Apache-2.0 |
| `botocore` | `1.43.108` | Apache-2.0 |
| `bottle` | `0.13.4` | MIT |
| `certifi` | `2026.7.22` | MPL-2.0 |
| `cffi` | `2.1.1` | MIT-0 |
| `charset-normalizer` | `3.5.2` | MIT |
| `click` | `8.5.0` | BSD-3-Clause |
| `clr_loader` | `0.3.1` | MIT (license file) |
| `colorama` | `0.4.6` | OSI Approved :: BSD License |
| `cryptography` | `50.0.2` | Apache-2.0 OR BSD-3-Clause |
| `datasets` | `5.0.1` | Apache 2.0 |
| `dill` | `0.4.1` | BSD-3-Clause |
| `distro` | `1.9.0` | Apache License, Version 2.0 |
| `fastuuid` | `0.14.0` | OSI Approved :: BSD License |
| `filelock` | `4.0.9` | MIT |
| `frozenlist` | `1.8.0` | Apache-2.0 |
| `fsspec` | `2026.6.0` | BSD-3-Clause |
| `h11` | `0.16.0` | MIT |
| `h2` | `4.4.1` | MIT |
| `hf-xet` | `1.6.0` | Apache-2.0 |
| `hpack` | `4.2.0` | MIT |
| `httpcore` | `1.0.9` | BSD-3-Clause |
| `httpx` | `0.28.1` | BSD-3-Clause |
| `httpx-sse` | `0.4.3` | MIT |
| `huggingface_hub` | `1.33.0` | Apache-2.0 |
| `hyperframe` | `6.1.0` | MIT |
| `idna` | `3.20` | BSD-3-Clause |
| `importlib_metadata` | `8.9.0` | Apache-2.0 |
| `Jinja2` | `3.1.6` | OSI Approved :: BSD License |
| `jiter` | `0.17.0` | MIT |
| `jmespath` | `1.1.0` | MIT |
| `jsonschema` | `4.26.0` | MIT |
| `jsonschema-specifications` | `2025.9.1` | MIT |
| `linkify-it-py` | `2.2.0` | MIT |
| `litellm` | `1.103.2` | MIT |
| `markdown-it-py` | `4.2.0` | OSI Approved :: MIT License |
| `MarkupSafe` | `3.0.4` | BSD-3-Clause |
| `mcp` | `1.30.0` | MIT |
| `mdit-py-plugins` | `0.6.1` | OSI Approved :: MIT License |
| `mdurl` | `0.1.2` | OSI Approved :: MIT License |
| `multidict` | `6.9.1` | Apache License 2.0 |
| `multiprocess` | `0.70.19` | BSD-3-Clause |
| `numpy` | `2.5.3` | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| `openai` | `2.54.0` | Apache-2.0 |
| `packaging` | `26.3` | Apache-2.0 OR BSD-2-Clause |
| `pandas` | `3.0.6` | BSD 3-Clause License |
| `platformdirs` | `4.12.2` | MIT |
| `prompt_toolkit` | `3.0.53` | OSI Approved :: BSD License |
| `propcache` | `0.5.4` | Apache-2.0 |
| `proxy_tools` | `0.1.0` | MIT |
| `pyarrow` | `25.0.1` | Apache-2.0 |
| `pycparser` | `3.11` | BSD-3-Clause |
| `pydantic` | `2.13.5` | MIT |
| `pydantic-settings` | `2.15.0` | MIT |
| `pydantic_core` | `2.46.5` | MIT |
| `Pygments` | `2.21.0` | BSD-2-Clause |
| `PyJWT` | `2.15.1` | MIT |
| `python-dateutil` | `2.9.0.post0` | Dual License |
| `python-dotenv` | `1.2.4` | BSD-3-Clause |
| `python-multipart` | `0.0.32` | Apache-2.0 |
| `pythonnet` | `3.2.1` | MIT |
| `pywebview` | `6.2.1` | BSD 3-Clause License |
| `pywin32` | `312` | PSF |
| `PyYAML` | `6.0.3` | MIT |
| `referencing` | `0.37.0` | MIT |
| `regex` | `2026.9.29` | Apache-2.0 AND CNRI-Python |
| `requests` | `2.34.2` | Apache-2.0 |
| `rich` | `15.0.0` | MIT |
| `rpds-py` | `2026.6.3` | MIT |
| `s3transfer` | `0.19.2` | Apache License 2.0 |
| `shellingham` | `1.5.4` | ISC License |
| `six` | `1.17.0` | MIT |
| `sniffio` | `1.3.1` | MIT OR Apache-2.0 |
| `sse-starlette` | `3.5.0` | BSD-3-Clause |
| `starlette` | `1.7.0` | BSD-3-Clause |
| `tenacity` | `9.1.4` | Apache 2.0 |
| `textual` | `8.2.8` | MIT |
| `tiktoken` | `0.14.0` | MIT |
| `tokenizers` | `0.23.2` | OSI Approved :: Apache Software License |
| `tqdm` | `4.70.1` | MPL-2.0 AND MIT |
| `typer` | `0.27.2` | MIT |
| `typing-inspection` | `0.4.4` | MIT |
| `typing_extensions` | `4.16.0` | PSF-2.0 |
| `tzdata` | `2026.4` | Apache-2.0 |
| `urllib3` | `2.8.0` | MIT |
| `uvicorn` | `0.54.0` | BSD-3-Clause |
| `wcwidth` | `0.9.1` | OSI Approved :: MIT License |
| `websockets` | `17.2` | BSD-3-Clause |
| `xxhash` | `4.0.1` | BSD-2-Clause |
| `yarl` | `1.25.1` | Apache-2.0 |
| `zipp` | `4.1.0` | MIT |

## Frontend npm lockfile

npm metadata refreshed on 2026-11-02; Python inventory above is unchanged.

| Package | Version | License metadata | Scope |
| --- | --- | --- | --- |
| `@jridgewell/sourcemap-codec` | `1.6.0` | MIT | development |
| `@oxc-project/types` | `0.153.0` | MIT | development |
| `@oxlint/binding-android-arm-eabi` | `1.87.0` | MIT | development |
| `@oxlint/binding-android-arm64` | `1.87.0` | MIT | development |
| `@oxlint/binding-darwin-arm64` | `1.87.0` | MIT | development |
| `@oxlint/binding-darwin-x64` | `1.87.0` | MIT | development |
| `@oxlint/binding-freebsd-x64` | `1.87.0` | MIT | development |
| `@oxlint/binding-linux-arm-gnueabihf` | `1.87.0` | MIT | development |
| `@oxlint/binding-linux-arm-musleabihf` | `1.87.0` | MIT | development |
| `@oxlint/binding-linux-arm64-gnu` | `1.87.0` | MIT | development |
| `@oxlint/binding-linux-arm64-musl` | `1.87.0` | MIT | development |
| `@oxlint/binding-linux-ppc64-gnu` | `1.87.0` | MIT | development |
| `@oxlint/binding-linux-riscv64-gnu` | `1.87.0` | MIT | development |
| `@oxlint/binding-linux-riscv64-musl` | `1.87.0` | MIT | development |
| `@oxlint/binding-linux-s390x-gnu` | `1.87.0` | MIT | development |
| `@oxlint/binding-linux-x64-gnu` | `1.87.0` | MIT | development |
| `@oxlint/binding-linux-x64-musl` | `1.87.0` | MIT | development |
| `@oxlint/binding-openharmony-arm64` | `1.87.0` | MIT | development |
| `@oxlint/binding-win32-arm64-msvc` | `1.87.0` | MIT | development |
| `@oxlint/binding-win32-ia32-msvc` | `1.87.0` | MIT | development |
| `@oxlint/binding-win32-x64-msvc` | `1.87.0` | MIT | development |
| `@rolldown/binding-android-arm-eabi` | `1.2.13` | MIT | development |
| `@rolldown/binding-android-arm64` | `1.2.13` | MIT | development |
| `@rolldown/binding-darwin-arm64` | `1.2.13` | MIT | development |
| `@rolldown/binding-darwin-x64` | `1.2.13` | MIT | development |
| `@rolldown/binding-freebsd-x64` | `1.2.13` | MIT | development |
| `@rolldown/binding-linux-arm-gnueabihf` | `1.2.13` | MIT | development |
| `@rolldown/binding-linux-arm64-gnu` | `1.2.13` | MIT | development |
| `@rolldown/binding-linux-arm64-musl` | `1.2.13` | MIT | development |
| `@rolldown/binding-linux-ppc64-gnu` | `1.2.13` | MIT | development |
| `@rolldown/binding-linux-s390x-gnu` | `1.2.13` | MIT | development |
| `@rolldown/binding-linux-x64-gnu` | `1.2.13` | MIT | development |
| `@rolldown/binding-linux-x64-musl` | `1.2.13` | MIT | development |
| `@rolldown/binding-openharmony-arm64` | `1.2.13` | MIT | development |
| `@rolldown/binding-win32-arm64-msvc` | `1.2.13` | MIT | development |
| `@rolldown/binding-win32-x64-msvc` | `1.2.13` | MIT | development |
| `@rolldown/pluginutils` | `1.0.1` | MIT | development |
| `@standard-schema/spec` | `1.1.0` | MIT | development |
| `@types/chai` | `5.2.3` | MIT | development |
| `@types/d3-color` | `3.1.3` | MIT | runtime |
| `@types/d3-drag` | `3.0.7` | MIT | runtime |
| `@types/d3-interpolate` | `3.0.4` | MIT | runtime |
| `@types/d3-selection` | `3.0.12` | MIT | runtime |
| `@types/d3-transition` | `3.0.9` | MIT | runtime |
| `@types/d3-zoom` | `3.0.9` | MIT | runtime |
| `@types/deep-eql` | `4.0.2` | MIT | development |
| `@types/estree` | `1.0.9` | MIT | development |
| `@types/node` | `24.19.1` | MIT | development |
| `@types/react` | `19.3.0` | MIT | runtime |
| `@types/react-dom` | `19.3.0` | MIT | runtime |
| `@vitejs/plugin-react` | `6.1.2` | MIT | development |
| `@vitest/expect` | `4.1.12` | MIT | development |
| `@vitest/mocker` | `4.1.12` | MIT | development |
| `@vitest/pretty-format` | `4.1.12` | MIT | development |
| `@vitest/runner` | `4.1.12` | MIT | development |
| `@vitest/snapshot` | `4.1.12` | MIT | development |
| `@vitest/spy` | `4.1.12` | MIT | development |
| `@vitest/utils` | `4.1.12` | MIT | development |
| `@xyflow/react` | `12.12.0` | MIT | runtime |
| `@xyflow/react/node_modules/zustand` | `4.5.7` | MIT | runtime |
| `@xyflow/system` | `0.0.83` | MIT | runtime |
| `assertion-error` | `2.0.1` | MIT | development |
| `chai` | `6.3.0` | MIT | development |
| `classcat` | `5.0.5` | MIT | runtime |
| `convert-source-map` | `2.0.0` | MIT | development |
| `csstype` | `3.2.3` | MIT | runtime |
| `d3-color` | `3.1.0` | ISC | runtime |
| `d3-dispatch` | `3.0.1` | ISC | runtime |
| `d3-drag` | `3.0.0` | ISC | runtime |
| `d3-ease` | `3.0.1` | BSD-3-Clause | runtime |
| `d3-interpolate` | `3.0.1` | ISC | runtime |
| `d3-selection` | `3.0.0` | ISC | runtime |
| `d3-timer` | `3.0.1` | ISC | runtime |
| `d3-transition` | `3.0.1` | ISC | runtime |
| `d3-zoom` | `3.0.0` | ISC | runtime |
| `detect-libc` | `2.1.2` | Apache-2.0 | development |
| `es-module-lexer` | `2.3.2` | MIT | development |
| `estree-walker` | `3.0.3` | MIT | development |
| `expect-type` | `1.4.0` | Apache-2.0 | development |
| `fdir` | `6.5.0` | MIT | development |
| `fsevents` | `2.3.3` | MIT | development |
| `lightningcss` | `1.33.0` | MPL-2.0 | development |
| `lightningcss-android-arm64` | `1.33.0` | MPL-2.0 | development |
| `lightningcss-darwin-arm64` | `1.33.0` | MPL-2.0 | development |
| `lightningcss-darwin-x64` | `1.33.0` | MPL-2.0 | development |
| `lightningcss-freebsd-x64` | `1.33.0` | MPL-2.0 | development |
| `lightningcss-linux-arm-gnueabihf` | `1.33.0` | MPL-2.0 | development |
| `lightningcss-linux-arm64-gnu` | `1.33.0` | MPL-2.0 | development |
| `lightningcss-linux-arm64-musl` | `1.33.0` | MPL-2.0 | development |
| `lightningcss-linux-x64-gnu` | `1.33.0` | MPL-2.0 | development |
| `lightningcss-linux-x64-musl` | `1.33.0` | MPL-2.0 | development |
| `lightningcss-win32-arm64-msvc` | `1.33.0` | MPL-2.0 | development |
| `lightningcss-win32-x64-msvc` | `1.33.0` | MPL-2.0 | development |
| `lucide-react` | `1.53.0` | ISC | runtime |
| `magic-string` | `0.30.21` | MIT | development |
| `nanoid` | `3.3.20` | MIT | development |
| `obug` | `2.2.1` | MIT | development |
| `oxlint` | `1.87.0` | MIT | development |
| `pathe` | `2.0.3` | MIT | development |
| `picocolors` | `1.1.1` | ISC | development |
| `picomatch` | `4.0.7` | MIT | development |
| `postcss` | `8.5.29` | MIT | development |
| `prettier` | `3.9.10` | MIT | development |
| `react` | `19.3.0` | MIT | runtime |
| `react-dom` | `19.3.0` | MIT | runtime |
| `rolldown` | `1.2.13` | MIT | development |
| `scheduler` | `0.28.0` | MIT | runtime |
| `siginfo` | `2.0.0` | ISC | development |
| `source-map-js` | `1.2.2` | BSD-3-Clause | development |
| `stackback` | `0.0.2` | MIT | development |
| `std-env` | `4.3.0` | MIT | development |
| `tinybench` | `2.9.0` | MIT | development |
| `tinyexec` | `1.3.1` | MIT | development |
| `tinyglobby` | `0.2.17` | MIT | development |
| `tinyrainbow` | `3.2.0` | MIT | development |
| `typescript` | `6.0.3` | Apache-2.0 | development |
| `undici-types` | `7.24.6` | MIT | development |
| `use-sync-external-store` | `1.7.0` | MIT | runtime |
| `vite` | `8.3.3` | MIT | development |
| `vitest` | `4.1.12` | MIT | development |
| `why-is-node-running` | `2.3.0` | MIT | development |
| `zustand` | `5.0.15` | MIT | runtime |
