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

### Blueprint Structure
Each blueprint lives in `blueprints/automation/<name>/` with:
- `<name>.yaml` — the blueprint definition
- `tests/conftest.py` — shared fixtures for this blueprint's tests
- `tests/topology.py` — `hass_topology` fixture defining the test HA environment
- `tests/simulations.py` — simulated hardware (ZEN35 switch, PowerView hub HTTP server)
- `tests/test_*.py` — test files

The root `conftest.py` imports all blueprint-level topology modules to make fixtures available globally. Each blueprint's `tests/` directory and all parent directories up to the root have `__init__.py` files so pytest can resolve fully-qualified module names.

### Blueprint Logic (zooz_zen35_powerview)
Triggers on Z-Wave Central Scene events from the ZEN35 device. For each button press, it:
1. Looks up the device's area via `device_attr(device_id, 'area_id')`
2. Finds entities matching a label via `label_entities(label_id)`
3. Filters to the same area via `area_entities(area_id)`
4. Buttons 1–3: calls `scene.turn_on` on matching PowerView scene entities
5. Button 4: auto-discovers the PowerView hub via `integration_entities('hunterdouglas_powerview')`, reads current scheduled event state from `sensor.powerview_scheduled_events`, then toggles all room events via `rest_command.powerview_set_scheduled_event`
6. Updates LED indicator config via `zwave_js.set_config_parameter`

HA normalizes label IDs by replacing `.` with `_` (e.g. `powerview.scenes.open` → `powerview_scenes_open`). Blueprint defaults use the normalized form.

### Test Architecture

**Simulations** (`simulations.py`):
- `SimulatedZEN35`: registers a real `zwave_js.set_config_parameter` HA service and records all calls for assertion
- `SimulatedPowerViewHub`: runs a real aiohttp HTTP server on 127.0.0.1 implementing the Gen 2 PowerView REST API (`/api/scenes`, `/api/scheduledEvents`, etc.), tracks scene activations and event state

**Topology** (`topology.py`): The `hass_topology` fixture sets up a realistic HA environment:
- Two areas (Living Room, Kitchen), three scene labels
- One ZEN35 device in Living Room
- Real `hunterdouglas_powerview` integration loaded against `SimulatedPowerViewHub`, creating real scene entities
- REST sensor polling the sim hub for scheduled event state
- `rest_command.powerview_set_scheduled_event` wired to the sim hub
- Two "noise" entities (wrong area, or no label) to verify discovery precision
- The `configuration_url` of the hub device is set manually after integration load (the real integration does not set it)

**Tests** (`test_zen35_powerview_blueprint.py`): Fire real Z-Wave events into HA and assert on simulation state — hub scene activations, scheduled event enabled/disabled, and LED parameter values — rather than on service call arguments.

### Key Fixture Chain
`hass_topology` → `load_blueprint` → test assertions
- `hass_topology` sets up areas, labels, devices, real integration, REST sensor
- `load_blueprint` copies the blueprint YAML and registers an automation with specific label inputs
- Tests fire events and assert on `SimulatedZEN35` and `SimulatedPowerViewHub` state
