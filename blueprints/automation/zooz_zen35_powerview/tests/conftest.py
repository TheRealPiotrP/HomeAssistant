"""Local fixtures for the ZEN35 PowerView blueprint tests."""
from pathlib import Path
import shutil
from enum import IntEnum

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.components import automation
from homeassistant.setup import async_setup_component


class ZEN35Param(IntEnum):
    LED1 = 2
    LED2 = 3
    LED3 = 4
    LED4 = 5


class LEDState(IntEnum):
    OFF = 2
    ON = 3


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
def load_blueprint(hass, copy_blueprint_to_config):
    """Load the blueprint into HA. Accepts a Labels namedtuple from hass_topology."""

    async def _load(device, labels):
        assert await async_setup_component(
            hass,
            automation.DOMAIN,
            {
                automation.DOMAIN: {
                    "use_blueprint": {
                        "path": BLUEPRINT_PATH,
                        "input": {
                            "zen35_device": device.id,
                            "label_fully_open": labels.open,
                            "label_partially_open": labels.partial,
                            "label_fully_close": labels.closed,
                            "label_central_control": labels.auto,
                        },
                    }
                }
            },
        )
        await hass.async_block_till_done()

    return _load
