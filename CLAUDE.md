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

## Architecture

### Blueprint Structure
Each blueprint lives in `blueprints/automation/<name>/` with:
- `<name>.yaml` — the blueprint definition
- `tests/conftest.py` — shared fixtures for this blueprint's tests
- `tests/topology.py` — `hass_topology` fixture defining the test HA environment
- `tests/test_*.py` — test files

The root `conftest.py` imports all blueprint-level conftest modules to make fixtures available globally.

### Blueprint Logic (zooz_zen35_powerview)
Triggers on Z-Wave Central Scene events from the ZEN35 device. For each button press, it:
1. Looks up the device's area via `device_attr(device_id, 'area_id')`
2. Finds entities matching a label via `label_entities(label_id)`
3. Filters to the same area via `area_entities(area_id)`
4. Calls `scene.turn_on` or `input_boolean.toggle`
5. Updates LED indicator config via `zwave_js.set_config_parameter`

### Test Patterns

**Integration tests** (`test_zen35_powerview_blueprint.py`): Fire real Z-Wave events into HA, capture service calls with `async_mock_service()`, assert exact calls and parameters.

**Functional tests** (`test_functional_logic.py`): Register fake service handlers that mutate state, verify end state rather than call args.

**topology.py**: Defines a `hass_topology` fixture that creates a realistic HA environment with two areas, four labels, one ZEN35 device, three scene entities + one input_boolean in the primary area, and "noise" entities in other areas/without labels to verify discovery precision.

### Key Fixture Chain
`hass_topology` → `load_blueprint` → test assertions
- `hass_topology` sets up areas, labels, devices, entities
- `load_blueprint` loads the blueprint YAML and registers an automation with specific label inputs
- Tests fire events and assert service calls
