"""Local fixtures for the ZEN35 PowerView blueprint tests."""
from pathlib import Path
import shutil
from enum import IntEnum

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.components import automation
from homeassistant.setup import async_setup_component

from .simulations import SimulatedZEN35, SimulatedPowerViewHub


class ZEN35Param(IntEnum):
    # LED mode parameters (params 1–5): 2=always off, 3=always on
    LOAD_MODE = 1
    LED1_MODE = 2
    LED2_MODE = 3
    LED3_MODE = 4
    LED4_MODE = 5
    # LED color parameters (params 6–10)
    LOAD_COLOR = 6
    LED1_COLOR = 7
    LED2_COLOR = 8
    LED3_COLOR = 9
    LED4_COLOR = 10


class LEDState(IntEnum):
    OFF = 2
    ON = 3


class LEDColor(IntEnum):
    WHITE = 0
    BLUE = 1
    GREEN = 2
    RED = 3
    MAGENTA = 4
    YELLOW = 5
    CYAN = 6


BLUEPRINT_DIR = Path(__file__).resolve().parent.parent
BLUEPRINT_PATH = "zooz_zen35_powerview/zooz_zen35_powerview.yaml"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def copy_blueprint_to_config(hass):
    blueprint_dest = (
        Path(hass.config.config_dir) / "blueprints" / "automation" / "zooz_zen35_powerview"
    )
    blueprint_dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        BLUEPRINT_DIR / "zooz_zen35_powerview.yaml",
        blueprint_dest / "zooz_zen35_powerview.yaml",
    )
    yield


@pytest.fixture
def mock_zwave_config_entry(hass) -> ConfigEntry:
    entry = ConfigEntry(
        version=1,
        domain="zwave_js",
        title="Z-Wave JS",
        data={},
        options={},
        entry_id="test-zwave",
        state=ConfigEntryState.LOADED,
        source="integration_discovery",
        minor_version=1,
        unique_id="mock_zwave",
        discovery_keys=set(),
        subentries_data={},
    )
    hass.config_entries._entries[entry.entry_id] = entry
    yield entry
    hass.config_entries._entries.pop(entry.entry_id, None)



@pytest.fixture
def sim_zen35(hass) -> SimulatedZEN35:
    """Simulated ZEN35: registers a real zwave_js.set_config_parameter service
    and records parameter state for assertion by tests."""
    return SimulatedZEN35(hass)


@pytest.fixture
async def sim_powerview_hub(socket_enabled) -> SimulatedPowerViewHub:
    """Simulated PowerView hub HTTP server on 127.0.0.1 (allowed by pytest-socket).
    Seeds initial state with all events enabled (opted in)."""
    hub = SimulatedPowerViewHub()
    await hub.start()
    yield hub
    await hub.stop()


@pytest.fixture
def load_blueprint(hass, copy_blueprint_to_config):
    """Load the blueprint into HA. Accepts a Labels namedtuple from hass_topology."""

    async def _load(
        device,
        labels,
        *,
        led_theme="default",
        confirm_timeout=0,
        powerview_hub=None,
    ):
        inputs = {
            "zen35_device": device.id,
            "label_fully_open": labels.open,
            "label_partially_open": labels.partial,
            "label_fully_close": labels.closed,
            "label_central_control": labels.auto,
            "led_theme": led_theme,
            "confirm_timeout": confirm_timeout,
        }
        if powerview_hub is not None:
            inputs["powerview_hub"] = powerview_hub.id
        assert await async_setup_component(
            hass,
            automation.DOMAIN,
            {
                automation.DOMAIN: {
                    "use_blueprint": {
                        "path": BLUEPRINT_PATH,
                        "input": inputs,
                    }
                }
            },
        )
        await hass.async_block_till_done()

    return _load
