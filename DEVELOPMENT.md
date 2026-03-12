# Development

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-test.txt
```

## Running Tests

```bash
# All tests
pytest -v

# Single blueprint's tests
pytest blueprints/automation/zooz_zen35_powerview/tests -v

# By name
pytest -k "test_button_1_opens_scene" -v
```

## Lint

```bash
ruff check .
```

## Architecture

### Blueprint Structure

Each blueprint lives in `blueprints/automation/<name>/` with:
- `<name>.yaml` — the blueprint definition
- `tests/conftest.py` — shared fixtures for this blueprint's tests
- `tests/topology.py` — `hass_topology` fixture defining the test HA environment
- `tests/simulations.py` — simulated hardware (ZEN35 switch, PowerView hub HTTP server)
- `tests/test_*.py` — test files

The root `conftest.py` imports all blueprint-level topology modules to make fixtures available globally. Each blueprint's `tests/` directory and all parent directories up to the root have `__init__.py` files so pytest can resolve fully-qualified module names.

### Test Architecture

**Simulations** (`simulations.py`):
- `SimulatedZEN35`: registers a real `zwave_js.set_config_parameter` HA service and records all calls for assertion
- `SimulatedPowerViewHub`: runs a real aiohttp HTTP server on 127.0.0.1 implementing the Gen 2 PowerView REST API (`/api/scenes`, `/api/scheduledEvents`, etc.), tracks scene activations and event state

**Topology** (`topology.py`): The `hass_topology` fixture sets up a realistic HA environment:
- Two areas (Living Room, Kitchen), three scene labels
- One ZEN35 device in Living Room
- Real `hunterdouglas_powerview` integration loaded against `SimulatedPowerViewHub`, creating real scene entities
- REST sensor for scheduled event state
- `rest_command.powerview_set_scheduled_event` wired to the sim hub
- Two "noise" entities (wrong area, or no label) to verify discovery precision

**Tests** (`test_zen35_powerview_blueprint.py`): Fire real Z-Wave events into HA and assert on simulation state — hub scene activations, scheduled event enabled/disabled, and LED parameter values — rather than on service call arguments.

### Key Fixture Chain

`hass_topology` → `load_blueprint` → test assertions

- `hass_topology` sets up areas, labels, devices, real integration, REST sensor
- `load_blueprint` copies the blueprint YAML and registers an automation with specific label inputs
- Tests fire events and assert on `SimulatedZEN35` and `SimulatedPowerViewHub` state
