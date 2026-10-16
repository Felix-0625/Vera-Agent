# Repository checks

The maintained backend tests are in `../vera-agent/tests/`; frontend checks are defined by `../frontend/package.json`. This directory contains only cross-project validation entry points so tests remain close to the code they exercise.

Run `./check-all.ps1` from the repository root. It does not install packages or call live model services. Read [the testing guide](../docs/TESTING.md) before interpreting its results.
