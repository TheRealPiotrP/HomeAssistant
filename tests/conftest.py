"""Pytest fixtures for ZEN35 PowerView blueprint tests."""
import shutil
from pathlib import Path

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant

# Blueprint path relative to repo root
BLUEPRINT_DIR = (
    Path(__file__).resolve().parent.parent / "blueprints" / "automation" / "zooz_zen35_powerview"
)
BLUEPRINT_PATH = "zooz_zen35_powerview/zooz_zen35_powerview.yaml"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


@pytest.fixture
def copy_blueprint_to_config(hass):
    """Copy the ZEN35 PowerView blueprint into the HA config dir so it can be loaded."""
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
def mock_zwave_config_entry(hass: HomeAssistant) -> ConfigEntry:
    """Create a mock Z-Wave config entry for device linking."""
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
    # Clean up the entry after the test
    hass.config_entries._entries.pop(entry.entry_id, None)
