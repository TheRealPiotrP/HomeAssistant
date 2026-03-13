# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant automation blueprints with comprehensive pytest-based testing. The primary blueprint connects a Zooz ZEN35 wireless switch to Hunter Douglas PowerView blinds using area + label auto-discovery (no per-room entity selection required).

## Commands

### Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-test.txt
```

### Running Tests
```bash
# All tests
pytest -v

# Single blueprint's tests
pytest blueprints/automation/zooz_zen35_powerview/tests -v

# Single test file
pytest blueprints/automation/zooz_zen35_powerview/tests/test_zen35_powerview_blueprint.py -v

# Single test by name
pytest -k "test_button_1_opens_scene" -v
```

## Testing Preferences

**Use real integrations, not mocks.** Tests run the actual `hunterdouglas_powerview` integration, real HA service dispatch, and a real aiohttp HTTP server (`SimulatedPowerViewHub`). Do not mock services or HTTP calls — use simulated hardware that exercises the full call path.

**Assert on simulation state, not call arguments.** After firing a Z-Wave event, assert on what the simulated hardware observed (which scenes activated, which scheduled events toggled, which LED parameters were set) rather than inspecting mock call counts or arguments.

**Inject state directly to avoid timing races.** Use `hass.states.async_set` to seed sensor state rather than relying on REST sensor polling. Async polling timing is non-deterministic and will cause flaky tests.

## Workflow

Before implementing any non-trivial change, present the plan and wait for explicit approval. Do not start writing code or modifying files until the plan is confirmed.

**Match scope exactly.** "Fix stale content in a file" means edit the file — not replace or delete it. Deleting a file requires explicit instruction to delete, regardless of how outdated its content is.

**Deleting files always requires explicit confirmation.** Even when a file seems redundant or fully superseded, confirm before removing it. Deletion is irreversible without git and the user may have reasons to keep it.

**When asked to remove something from the repo, search all file types.** Use a broad glob (`.py`, `.yaml`, `.md`, `.toml`, etc.) and verify zero matches before declaring it clean. Do not stop after finding and fixing the obvious locations.

## Architecture

See [DEVELOPMENT.md](DEVELOPMENT.md) for full architecture documentation.

**Key points:**
- Each blueprint lives in `blueprints/automation/<name>/` with `<name>.yaml`, `tests/conftest.py`, `tests/topology.py`, `tests/simulations.py`, and `tests/test_*.py`
- Tests use real HA integrations and a real aiohttp HTTP server — no mocks
- Fixture chain: `hass_topology` → `load_blueprint` → test assertions
- `hass_topology` sets `configuration_url` on the hub device manually (the real integration does not set it)
