"""Tests for the Zooz ZEN35 → PowerView blueprint."""
import pytest

from homeassistant.components import automation
from homeassistant.setup import async_setup_component

from tests.conftest import BLUEPRINT_PATH
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    label_registry as lr,
)
from pytest_homeassistant_custom_component.common import async_mock_service


@pytest.fixture
def scene_calls(hass):
    """Capture scene.turn_on calls."""
    return async_mock_service(hass, "scene", "turn_on")


@pytest.fixture
def zwave_calls(hass):
    """Capture zwave_js.set_config_parameter calls."""
    return async_mock_service(hass, "zwave_js", "set_config_parameter")


@pytest.fixture
def input_boolean_calls(hass):
    """Capture input_boolean.toggle calls."""
    return async_mock_service(hass, "input_boolean", "toggle")


# ---------------------------------------------------------------------------
# helpers shared between tests
# ---------------------------------------------------------------------------

def _create_area_and_device(hass):
    """Create a Living Room area and register a ZEN35 device there.

    Returns a tuple ``(device, area)`` so callers can reference the
    area_id when updating entities.
    """

    area_reg = ar.async_get(hass)
    area = area_reg.async_create("Living Room")

    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_or_create(
        config_entry_id="test-zwave",
        identifiers={("zwave_js", "zen35-node-5")},
        manufacturer="Zooz",
        model="ZEN35",
        name="ZEN35 Switch",
    )
    dev_reg.async_update_device(device.id, area_id=area.id)
    return device, area


def _create_standard_labels(hass):
    """Return ordered list of label IDs: open, partial, closed, automated."""

    label_reg = lr.async_get(hass)
    label_open = label_reg.async_create("Fully open", icon="mdi:blinds-open", color="blue")
    label_partial = label_reg.async_create("Partial", icon="mdi:blinds", color="green")
    label_closed = label_reg.async_create("Closed", icon="mdi:blinds", color="red")
    label_automated = label_reg.async_create("Automated", icon="mdi:robot", color="yellow")
    return [
        label_open.label_id,
        label_partial.label_id,
        label_closed.label_id,
        label_automated.label_id,
    ]


async def _load_blueprint(hass, device, label_ids):
    """Set up the automation using the blueprint and given inputs."""

    assert await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "use_blueprint": {
                    "path": BLUEPRINT_PATH,
                    "input": {
                        "zen35_device": device.id,
                        "label_fully_open": label_ids[0],
                        "label_partially_open": label_ids[1],
                        "label_fully_close": label_ids[2],
                        "label_central_control": label_ids[3],
                    },
                }
            }
        },
    )
    await hass.async_block_till_done()


async def test_blueprint_button1_fully_open(
    hass,
    copy_blueprint_to_config,
    mock_zwave_config_entry,
    scene_calls,
    zwave_calls,
):
    """Pressing button 1 (Scene 001) activates fully-open scenes and sets LED."""
    copy_blueprint_to_config

    # common setup
    device, area = _create_area_and_device(hass)
    label_ids = _create_standard_labels(hass)

    ent_reg = er.async_get(hass)
    scene_entry = ent_reg.async_get_or_create(
        "scene",
        "powerview",
        "scene-open-1",
        suggested_object_id="living_room_open",
    )
    ent_reg.async_update_entity(
        scene_entry.entity_id, area_id=area.id, labels={label_ids[0]}
    )
    hass.states.async_set(scene_entry.entity_id, "idle")

    # the central control input boolean is only used to get an entity ID
    input_bool_entry = ent_reg.async_get_or_create(
        "input_boolean",
        "input_boolean",
        "central-1",
        suggested_object_id="living_room_blinds_central",
    )
    ent_reg.async_update_entity(
        input_bool_entry.entity_id, area_id=area.id, labels={label_ids[3]}
    )
    hass.states.async_set(input_bool_entry.entity_id, "off")

    # configure automation
    await _load_blueprint(hass, device, label_ids)

    # simulate the button press
    hass.bus.async_fire(
        "zwave_js_value_notification",
        {
            "device_id": device.id,
            "command_class_name": "Central Scene",
            "label": "Scene 001",
            "value": "KeyPressed",
        },
    )
    await hass.async_block_till_done()

    assert len(scene_calls) == 1
    assert scene_calls[0].data["entity_id"] == [scene_entry.entity_id]

    assert len(zwave_calls) == 4
    params = {c.data["parameter"]: c.data["value"] for c in zwave_calls}
    assert params == {2: 3, 3: 2, 4: 2, 5: 2}


async def test_blueprint_button4_toggle_central_control(
    hass,
    copy_blueprint_to_config,
    mock_zwave_config_entry,
    input_boolean_calls,
    zwave_calls,
):
    """Pressing button 4 (Scene 004) toggles input_boolean and updates LED."""
    copy_blueprint_to_config

    device, area = _create_area_and_device(hass)
    label_ids = _create_standard_labels(hass)

    ent_reg = er.async_get(hass)
    input_bool_entry = ent_reg.async_get_or_create(
        "input_boolean",
        "input_boolean",
        "central-1",
        suggested_object_id="living_room_blinds_central",
    )
    ent_reg.async_update_entity(
        input_bool_entry.entity_id, area_id=area.id, labels={label_ids[3]}
    )
    hass.states.async_set(input_bool_entry.entity_id, "off")

    await _load_blueprint(hass, device, label_ids)

    hass.bus.async_fire(
        "zwave_js_value_notification",
        {
            "device_id": device.id,
            "command_class_name": "Central Scene",
            "label": "Scene 004",
            "value": "KeyPressed",
        },
    )
    await hass.async_block_till_done()

    assert len(input_boolean_calls) == 1
    assert input_boolean_calls[0].data["entity_id"] == [input_bool_entry.entity_id]
