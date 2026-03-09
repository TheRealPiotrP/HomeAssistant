"""Integration tests for the Zooz ZEN35 → PowerView blueprint.

All services except zwave_js.set_config_parameter run against real HA
components, so assertions are on actual state changes rather than captured
mock calls.  zwave_js.set_config_parameter is the only mocked service because
it requires real Z-Wave hardware.
"""
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service
from homeassistant.helpers import device_registry as dr

from conftest import ZEN35Param, LEDState


@pytest.fixture
def zwave_calls(hass):
    """Capture zwave_js.set_config_parameter calls (no real hardware available)."""
    return async_mock_service(hass, "zwave_js", "set_config_parameter")


def _fire_button(hass, device_id, scene_label):
    hass.bus.async_fire(
        "zwave_js_value_notification",
        {
            "device_id": device_id,
            "command_class_name": "Central Scene",
            "label": scene_label,
            "value": "KeyPressed",
        },
    )


@pytest.mark.parametrize(
    "scene_label, target, other_targets, expected_params",
    [
        (
            "Scene 001",
            "input_boolean.blinds_open_activated",
            ["input_boolean.blinds_partial_activated", "input_boolean.blinds_closed_activated"],
            {ZEN35Param.LED1: LEDState.ON, ZEN35Param.LED2: LEDState.OFF, ZEN35Param.LED3: LEDState.OFF},
        ),
        (
            "Scene 002",
            "input_boolean.blinds_partial_activated",
            ["input_boolean.blinds_open_activated", "input_boolean.blinds_closed_activated"],
            {ZEN35Param.LED1: LEDState.OFF, ZEN35Param.LED2: LEDState.ON, ZEN35Param.LED3: LEDState.OFF},
        ),
        (
            "Scene 003",
            "input_boolean.blinds_closed_activated",
            ["input_boolean.blinds_open_activated", "input_boolean.blinds_partial_activated"],
            {ZEN35Param.LED1: LEDState.OFF, ZEN35Param.LED2: LEDState.OFF, ZEN35Param.LED3: LEDState.ON},
        ),
    ],
    ids=["button1-open-LED1", "button2-partial-LED2", "button3-close-LED3"],
)
async def test_scene_button_activates_scene_and_sets_leds(
    hass,
    hass_topology,
    load_blueprint,
    zwave_calls,
    scene_label,
    target,
    other_targets,
    expected_params,
):
    """Pressing a scene button (1–3) activates the correct scene and updates LEDs.

    Verified via real state changes:
    - The scene's dedicated target input_boolean flips from 'off' to 'on'
      (proving scene.turn_on actually ran against the real scene platform).
    - Noise entities (wrong area or no label) remain 'off', proving the
      blueprint's label+area discovery is correctly scoped.
    - zwave_js LED parameters are set to the expected on/off pattern.
    """
    topology = hass_topology
    await load_blueprint(topology.device, topology.labels)

    assert hass.states.get(target).state == "off", "target must start off"

    _fire_button(hass, topology.device.id, scene_label)
    await hass.async_block_till_done()

    # Scene activated: its target boolean turned on
    assert hass.states.get(target).state == "on", \
        f"{scene_label}: scene target {target} should be 'on' after activation"

    # Other scene targets were not activated
    for other in other_targets:
        assert hass.states.get(other).state == "off", \
            f"{scene_label}: {other} should remain 'off'"

    # Noise entities were not activated
    assert hass.states.get(topology.entities.target_noise_kitchen).state == "off", \
        "kitchen noise scene must not fire (wrong area)"
    assert hass.states.get(topology.entities.target_noise_no_label).state == "off", \
        "unlabeled noise scene must not fire (no label)"

    # LED parameters reflect the active button
    assert len(zwave_calls) == len(expected_params), \
        f"Expected {len(expected_params)} zwave calls, got {len(zwave_calls)}"
    actual = {c.data["parameter"]: c.data["value"] for c in zwave_calls}
    for param, value in expected_params.items():
        assert actual.get(param) == value, \
            f"{scene_label} LED param {param}: expected {value}, got {actual.get(param)}"


@pytest.mark.parametrize(
    "initial_state, expected_led",
    [("off", LEDState.ON), ("on", LEDState.OFF)],
    ids=["button4-was_off-LED4_on", "button4-was_on-LED4_off"],
)
async def test_button4_toggles_central_control_and_updates_led(
    hass,
    hass_topology,
    load_blueprint,
    zwave_calls,
    initial_state,
    expected_led,
):
    """Pressing button 4 toggles the input_boolean and updates LED4.

    Verified via real state changes:
    - input_boolean.living_room_blinds_central actually flips state
      (proving input_boolean.toggle ran against the real platform).
    - zwave_js LED4 parameter is set to reflect the new state.
    - LED1–3 are not touched.
    """
    topology = hass_topology
    switch = topology.entities.switch_auto

    if initial_state == "on":
        await hass.services.async_call(
            "input_boolean", "turn_on", {"entity_id": switch}, blocking=True
        )

    await load_blueprint(topology.device, topology.labels)

    assert hass.states.get(switch).state == initial_state

    _fire_button(hass, topology.device.id, "Scene 004")
    await hass.async_block_till_done()

    expected_new_state = "on" if initial_state == "off" else "off"
    assert hass.states.get(switch).state == expected_new_state, \
        f"input_boolean should have toggled from '{initial_state}' to '{expected_new_state}'"

    assert len(zwave_calls) == 1, \
        f"Expected 1 zwave call (LED4 only), got {len(zwave_calls)}"
    assert zwave_calls[0].data["parameter"] == ZEN35Param.LED4
    assert zwave_calls[0].data["value"] == expected_led, \
        f"LED4: expected {expected_led} for initial state '{initial_state}'"


# ---------------------------------------------------------------------------
# Negative tests: label/area mismatches
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "scene_label, target",
    [
        ("Scene 001", "input_boolean.blinds_open_activated"),
        ("Scene 002", "input_boolean.blinds_partial_activated"),
        ("Scene 003", "input_boolean.blinds_closed_activated"),
    ],
    ids=["button1-no_open_label", "button2-no_partial_label", "button3-no_close_label"],
)
async def test_scene_button_no_matching_label_skips_scene_but_updates_leds(
    hass,
    hass_topology,
    load_blueprint,
    zwave_calls,
    scene_label,
    target,
):
    """Buttons 1–3 with no scene carrying the expected label in the area.

    The blueprint guards scene.turn_on behind an entity-list length check, so
    only the LED update runs — the scene must not activate.
    """
    topology = hass_topology
    # Replace the relevant label with one that doesn't exist in the registry
    no_scene_labels = topology.labels._replace(
        open="no_such_label",
        partial="no_such_label",
        closed="no_such_label",
    )
    await load_blueprint(topology.device, no_scene_labels)

    _fire_button(hass, topology.device.id, scene_label)
    await hass.async_block_till_done()

    # Scene must not have activated
    assert hass.states.get(target).state == "off", \
        f"{scene_label}: scene target must stay 'off' when no entity matches the label"

    # LED parameters still updated (that block is not guarded by the entity check)
    assert len(zwave_calls) == 3, \
        f"{scene_label}: expected 3 LED zwave calls even with no matching scene, got {len(zwave_calls)}"


@pytest.mark.parametrize(
    "scene_label, wrong_area_target, right_area_target",
    [
        ("Scene 001", "input_boolean.blinds_open_activated",   "input_boolean.noise_kitchen_activated"),
        ("Scene 002", "input_boolean.blinds_partial_activated", None),
        ("Scene 003", "input_boolean.blinds_closed_activated",  None),
    ],
    ids=["button1-device_in_kitchen", "button2-device_in_kitchen", "button3-device_in_kitchen"],
)
async def test_scene_with_right_label_but_wrong_area_is_not_activated(
    hass,
    hass_topology,
    load_blueprint,
    zwave_calls,
    scene_label,
    wrong_area_target,
    right_area_target,
):
    """Scene with matching label in a different area than the device must not activate.

    The ZEN35 is moved to Kitchen. 'Kitchen Open' has the open label and is now
    in the device's area, so it activates. 'Living Room Open' has the same label
    but is in Living Room — it must not activate. Buttons 2 and 3 have no
    Kitchen-area scenes at all, so no scene activates for those.
    """
    topology = hass_topology

    # Relocate the ZEN35 to Kitchen — area-based discovery must follow the device
    dr.async_get(hass).async_update_device(
        topology.device.id, area_id=topology.areas.kitchen.id
    )

    await load_blueprint(topology.device, topology.labels)

    _fire_button(hass, topology.device.id, scene_label)
    await hass.async_block_till_done()

    # LR scene has the right label but device is no longer in LR — must not fire
    assert hass.states.get(wrong_area_target).state == "off", \
        f"{scene_label}: LR scene must not activate when device is in Kitchen"

    # Kitchen Open (button 1 only) is now in the device's area and should activate
    if right_area_target:
        assert hass.states.get(right_area_target).state == "on", \
            f"{scene_label}: Kitchen scene must activate when device is in Kitchen"


async def test_button4_no_matching_label_does_nothing(
    hass,
    hass_topology,
    load_blueprint,
    zwave_calls,
):
    """Button 4 with no input_boolean carrying the central-control label.

    The whole button 4 sequence is gated on entities_central_control being
    non-empty, so neither the toggle nor the LED update should fire.
    """
    topology = hass_topology
    no_auto_labels = topology.labels._replace(auto="no_such_label")
    await load_blueprint(topology.device, no_auto_labels)

    switch = topology.entities.switch_auto
    assert hass.states.get(switch).state == "off"

    _fire_button(hass, topology.device.id, "Scene 004")
    await hass.async_block_till_done()

    assert hass.states.get(switch).state == "off", \
        "central-control boolean must not toggle when no entity matches the label"
    assert len(zwave_calls) == 0, \
        f"no zwave calls expected when button 4 condition fails, got {len(zwave_calls)}"


@pytest.mark.parametrize(
    "scene_label",
    ["Scene 001", "Scene 002", "Scene 003"],
    ids=["button1", "button2", "button3"],
)
async def test_scene_buttons_do_not_affect_central_control(
    hass,
    hass_topology,
    load_blueprint,
    zwave_calls,
    scene_label,
):
    """Pressing a scene button (1–3) must not touch the central-control state.

    Verified two ways:
    - The central-control input_boolean state is unchanged after the press.
    - zwave_js is not called with parameter 5 (LED4), which belongs to button 4.
    """
    topology = hass_topology
    switch = topology.entities.switch_auto

    await hass.services.async_call(
        "input_boolean", "turn_on", {"entity_id": switch}, blocking=True
    )
    await load_blueprint(topology.device, topology.labels)

    assert hass.states.get(switch).state == "on"

    _fire_button(hass, topology.device.id, scene_label)
    await hass.async_block_till_done()

    assert hass.states.get(switch).state == "on", \
        f"{scene_label}: central-control boolean must not be toggled by a scene button"

    led4_calls = [c for c in zwave_calls if c.data["parameter"] == ZEN35Param.LED4]
    assert len(led4_calls) == 0, \
        f"{scene_label}: LED4 (button 4) must not be updated by a scene button"
