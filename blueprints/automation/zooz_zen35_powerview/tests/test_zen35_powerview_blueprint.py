"""Integration tests for the Zooz ZEN35 → PowerView blueprint.

All services except zwave_js.set_config_parameter run against real HA
components, so assertions are on actual state changes rather than captured
mock calls.  zwave_js.set_config_parameter is the only mocked service because
it requires real Z-Wave hardware.
"""
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service
from homeassistant.helpers import device_registry as dr

from conftest import ZEN35Param, LEDState, LEDColor


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
            {
                ZEN35Param.LED1_COLOR: LEDColor.WHITE,
                ZEN35Param.LED1_MODE: LEDState.ON,
                ZEN35Param.LED2_MODE: LEDState.OFF,
                ZEN35Param.LED3_MODE: LEDState.OFF,
            },
        ),
        (
            "Scene 002",
            "input_boolean.blinds_partial_activated",
            ["input_boolean.blinds_open_activated", "input_boolean.blinds_closed_activated"],
            {
                ZEN35Param.LED2_COLOR: LEDColor.WHITE,
                ZEN35Param.LED1_MODE: LEDState.OFF,
                ZEN35Param.LED2_MODE: LEDState.ON,
                ZEN35Param.LED3_MODE: LEDState.OFF,
            },
        ),
        (
            "Scene 003",
            "input_boolean.blinds_closed_activated",
            ["input_boolean.blinds_open_activated", "input_boolean.blinds_partial_activated"],
            {
                ZEN35Param.LED3_COLOR: LEDColor.WHITE,
                ZEN35Param.LED1_MODE: LEDState.OFF,
                ZEN35Param.LED2_MODE: LEDState.OFF,
                ZEN35Param.LED3_MODE: LEDState.ON,
            },
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
    - zwave_js LED4 parameter is set to reflect the new (post-toggle) state.
    - LED1–3 are also reset to OFF.
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

    assert len(zwave_calls) == 5, \
        f"Expected 5 zwave calls (LED1-3 mode + LED4 color + LED4 mode), got {len(zwave_calls)}"
    actual = {c.data["parameter"]: c.data["value"] for c in zwave_calls}
    assert actual[ZEN35Param.LED4_MODE] == expected_led, \
        f"LED4 mode: expected {expected_led} for initial state '{initial_state}'"
    assert actual[ZEN35Param.LED4_COLOR] == LEDColor.RED, \
        f"LED4 color: expected RED in default theme for initial state '{initial_state}'"
    assert actual[ZEN35Param.LED1_MODE] == LEDState.OFF
    assert actual[ZEN35Param.LED2_MODE] == LEDState.OFF
    assert actual[ZEN35Param.LED3_MODE] == LEDState.OFF


# ---------------------------------------------------------------------------
# Initialization: theme colors applied on startup / automation reload
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "led_theme, expected_colors",
    [
        (
            "default",
            {
                ZEN35Param.LOAD_COLOR: LEDColor.WHITE,
                ZEN35Param.LED1_COLOR: LEDColor.WHITE,
                ZEN35Param.LED2_COLOR: LEDColor.WHITE,
                ZEN35Param.LED3_COLOR: LEDColor.WHITE,
                ZEN35Param.LED4_COLOR: LEDColor.RED,
            },
        ),
        (
            "rainbow",
            {
                ZEN35Param.LOAD_COLOR: LEDColor.CYAN,
                ZEN35Param.LED1_COLOR: LEDColor.BLUE,
                ZEN35Param.LED2_COLOR: LEDColor.GREEN,
                ZEN35Param.LED3_COLOR: LEDColor.YELLOW,
                ZEN35Param.LED4_COLOR: LEDColor.RED,
            },
        ),
    ],
    ids=["init-default-theme", "init-rainbow-theme"],
)
async def test_init_sets_led_colors(
    hass,
    hass_topology,
    load_blueprint,
    led_theme,
    expected_colors,
):
    """On startup or automation reload, all LED color parameters are set to the theme.

    zwave_calls is created inline after load_blueprint so it only captures
    the manually-fired automation_reloaded event, not any setup activity.
    """
    topology = hass_topology
    await load_blueprint(topology.device, topology.labels, led_theme=led_theme)

    zwave_calls = async_mock_service(hass, "zwave_js", "set_config_parameter")

    hass.bus.async_fire("automation_reloaded")
    await hass.async_block_till_done()

    assert len(zwave_calls) == 5, \
        f"Expected 5 color param calls on init, got {len(zwave_calls)}"
    actual = {c.data["parameter"]: c.data["value"] for c in zwave_calls}
    for param, value in expected_colors.items():
        assert actual.get(param) == value, \
            f"{led_theme}: param {param} expected {value}, got {actual.get(param)}"


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
async def test_scene_button_no_matching_label_does_nothing(
    hass,
    hass_topology,
    load_blueprint,
    zwave_calls,
    scene_label,
    target,
):
    """Buttons 1–3 with no scene carrying the expected label in the area.

    The whole button sequence (scene + LEDs) is gated on finding at least one
    entity, so neither the scene nor any LED parameter should be updated.
    """
    topology = hass_topology
    no_scene_labels = topology.labels._replace(
        open="no_such_label",
        partial="no_such_label",
        closed="no_such_label",
    )
    await load_blueprint(topology.device, no_scene_labels)

    _fire_button(hass, topology.device.id, scene_label)
    await hass.async_block_till_done()

    assert hass.states.get(target).state == "off", \
        f"{scene_label}: scene target must stay 'off' when no entity matches the label"
    assert len(zwave_calls) == 0, \
        f"{scene_label}: no zwave calls expected when no entity matches the label, got {len(zwave_calls)}"


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


# ---------------------------------------------------------------------------
# Edge case: device has no area assigned
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "scene_label, target",
    [
        ("Scene 001", "input_boolean.blinds_open_activated"),
        ("Scene 002", "input_boolean.blinds_partial_activated"),
        ("Scene 003", "input_boolean.blinds_closed_activated"),
        ("Scene 004", "input_boolean.living_room_blinds_central"),
    ],
    ids=["button1-no_area", "button2-no_area", "button3-no_area", "button4-no_area"],
)
async def test_button_does_nothing_when_device_has_no_area(
    hass,
    hass_topology,
    load_blueprint,
    zwave_calls,
    scene_label,
    target,
):
    """All buttons are no-ops when the ZEN35 device has no area assigned.

    The blueprint guards every entity list with `if aid else []`, so removing
    the device's area must prevent any scene activation, boolean toggle, or
    LED update.
    """
    topology = hass_topology

    dr.async_get(hass).async_update_device(topology.device.id, area_id=None)
    await load_blueprint(topology.device, topology.labels)

    _fire_button(hass, topology.device.id, scene_label)
    await hass.async_block_till_done()

    assert hass.states.get(target).state == "off", \
        f"{scene_label}: target must stay 'off' when device has no area"
    assert len(zwave_calls) == 0, \
        f"{scene_label}: no zwave calls expected when device has no area"


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
    """Pressing a scene button (1–3) must not toggle the central-control boolean.

    Verified two ways:
    - The central-control input_boolean state is unchanged after the press.
    - LED4 is set to OFF (reflecting a reset, not a toggle of the boolean).
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

    led4_calls = [c for c in zwave_calls if c.data["parameter"] in (ZEN35Param.LED4_MODE, ZEN35Param.LED4_COLOR)]
    assert len(led4_calls) == 0, \
        f"{scene_label}: LED4 (button 4) must not be touched by a scene button"


# ---------------------------------------------------------------------------
# Rainbow theme: button press colors
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "scene_label, target, expected_color_param, expected_color",
    [
        ("Scene 001", "input_boolean.blinds_open_activated",  ZEN35Param.LED1_COLOR, LEDColor.BLUE),
        ("Scene 002", "input_boolean.blinds_partial_activated", ZEN35Param.LED2_COLOR, LEDColor.GREEN),
        ("Scene 003", "input_boolean.blinds_closed_activated", ZEN35Param.LED3_COLOR, LEDColor.YELLOW),
    ],
    ids=["button1-rainbow-blue", "button2-rainbow-green", "button3-rainbow-yellow"],
)
async def test_scene_button_rainbow_theme_sets_correct_color(
    hass,
    hass_topology,
    load_blueprint,
    zwave_calls,
    scene_label,
    target,
    expected_color_param,
    expected_color,
):
    """Rainbow theme: each scene button lights up in its assigned color."""
    topology = hass_topology
    await load_blueprint(topology.device, topology.labels, led_theme="rainbow")

    _fire_button(hass, topology.device.id, scene_label)
    await hass.async_block_till_done()

    assert hass.states.get(target).state == "on", \
        f"{scene_label}: scene target should activate"

    actual = {c.data["parameter"]: c.data["value"] for c in zwave_calls}
    assert actual.get(expected_color_param) == expected_color, \
        f"{scene_label}: expected color {expected_color} on param {expected_color_param}"


# ---------------------------------------------------------------------------
# Confirm mode: LED turns on then off after timeout
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "scene_label, active_mode_param, active_color_param",
    [
        ("Scene 001", ZEN35Param.LED1_MODE, ZEN35Param.LED1_COLOR),
        ("Scene 002", ZEN35Param.LED2_MODE, ZEN35Param.LED2_COLOR),
        ("Scene 003", ZEN35Param.LED3_MODE, ZEN35Param.LED3_COLOR),
    ],
    ids=["button1-confirm", "button2-confirm", "button3-confirm"],
)
async def test_scene_button_confirm_mode_led_turns_off_after_timeout(
    hass,
    hass_topology,
    load_blueprint,
    scene_label,
    active_mode_param,
    active_color_param,
):
    """Confirm mode: scene button LED turns on then off after confirm_timeout seconds.

    In the test environment the delay resolves within async_block_till_done, so
    the full sequence (ON → delay → OFF) completes before we assert. We verify
    both the ON and OFF calls appear in order in the call list.
    """
    topology = hass_topology
    await load_blueprint(topology.device, topology.labels, confirm_timeout=5)

    zwave_calls = async_mock_service(hass, "zwave_js", "set_config_parameter")

    _fire_button(hass, topology.device.id, scene_label)
    await hass.async_block_till_done()

    # Total calls: color(1) + active-mode-ON(1) + 2×other-mode-OFF(2) + active-mode-OFF-after-timeout(1) = 5
    assert len(zwave_calls) == 5, \
        f"{scene_label}: expected 5 zwave calls in confirm mode, got {len(zwave_calls)}"

    mode_calls = [c for c in zwave_calls if c.data["parameter"] == active_mode_param]
    assert len(mode_calls) == 2, \
        f"{scene_label}: expected 2 calls on active mode param (ON then OFF)"
    assert mode_calls[0].data["value"] == LEDState.ON, \
        f"{scene_label}: first active-mode call must be ON"
    assert mode_calls[-1].data["value"] == LEDState.OFF, \
        f"{scene_label}: last active-mode call must be OFF (timeout)"

    color_calls = [c for c in zwave_calls if c.data["parameter"] == active_color_param]
    assert len(color_calls) == 1
    assert color_calls[0].data["value"] == LEDColor.WHITE


@pytest.mark.parametrize(
    "initial_state, expected_led4_color",
    [
        ("off", LEDColor.WHITE),   # toggle to on → blink white
        ("on",  LEDColor.RED),     # toggle to off → blink red
    ],
    ids=["button4-confirm-toggle-on", "button4-confirm-toggle-off"],
)
async def test_button4_confirm_mode_led_turns_off_after_timeout(
    hass,
    hass_topology,
    load_blueprint,
    initial_state,
    expected_led4_color,
):
    """Confirm mode: button 4 blinks (white when toggling on, red when off) then goes dark.

    The full sequence completes within async_block_till_done. We verify both the
    ON and the timeout OFF calls appear on LED4_MODE in order.
    """
    topology = hass_topology
    switch = topology.entities.switch_auto

    if initial_state == "on":
        await hass.services.async_call(
            "input_boolean", "turn_on", {"entity_id": switch}, blocking=True
        )

    await load_blueprint(topology.device, topology.labels, confirm_timeout=5)

    zwave_calls = async_mock_service(hass, "zwave_js", "set_config_parameter")

    _fire_button(hass, topology.device.id, "Scene 004")
    await hass.async_block_till_done()

    # Total: LED1-3 mode OFF(3) + LED4 color(1) + LED4 mode ON(1) + LED4 mode OFF after timeout(1) = 6
    assert len(zwave_calls) == 6, \
        f"expected 6 zwave calls in confirm mode for button 4, got {len(zwave_calls)}"

    led4_color_calls = [c for c in zwave_calls if c.data["parameter"] == ZEN35Param.LED4_COLOR]
    assert len(led4_color_calls) == 1
    assert led4_color_calls[0].data["value"] == expected_led4_color, \
        f"LED4 color: expected {expected_led4_color} when toggling from '{initial_state}'"

    led4_mode_calls = [c for c in zwave_calls if c.data["parameter"] == ZEN35Param.LED4_MODE]
    assert len(led4_mode_calls) == 2, \
        "expected 2 LED4 mode calls (ON then OFF after timeout)"
    assert led4_mode_calls[0].data["value"] == LEDState.ON
    assert led4_mode_calls[1].data["value"] == LEDState.OFF


# ---------------------------------------------------------------------------
# Load button (Scene 005)
# ---------------------------------------------------------------------------

async def test_load_button_confirm_mode_led_turns_on_then_off(
    hass,
    hass_topology,
    load_blueprint,
):
    """Confirm mode: load button LED turns on briefly then turns off.

    In confirm mode the blueprint sets param 1 (LOAD_MODE) to 3 (always on),
    waits confirm_timeout seconds, then sets it to 2 (always off). The delay
    resolves synchronously in the test environment so we capture both calls.
    """
    topology = hass_topology
    await load_blueprint(topology.device, topology.labels, confirm_timeout=5)

    zwave_calls = async_mock_service(hass, "zwave_js", "set_config_parameter")

    _fire_button(hass, topology.device.id, "Scene 005")
    await hass.async_block_till_done()

    assert len(zwave_calls) == 2, \
        f"expected 2 zwave calls for load button confirm mode, got {len(zwave_calls)}"

    load_mode_calls = [c for c in zwave_calls if c.data["parameter"] == ZEN35Param.LOAD_MODE]
    assert len(load_mode_calls) == 2, \
        "expected 2 LOAD_MODE calls (ON then OFF)"
    assert load_mode_calls[0].data["value"] == LEDState.ON, \
        "first LOAD_MODE call must be ON (always on)"
    assert load_mode_calls[1].data["value"] == LEDState.OFF, \
        "second LOAD_MODE call must be OFF (always off) after timeout"


async def test_load_button_persistent_mode_no_led_change(
    hass,
    hass_topology,
    load_blueprint,
    zwave_calls,
):
    """Persistent mode: pressing the load button does not touch any LED parameter.

    In persistent mode (confirm_timeout == 0) the blueprint has no branch for
    Scene 005, so the load LED stays at its hardware default (mode 0 = locator).
    """
    topology = hass_topology
    await load_blueprint(topology.device, topology.labels, confirm_timeout=0)

    _fire_button(hass, topology.device.id, "Scene 005")
    await hass.async_block_till_done()

    assert len(zwave_calls) == 0, \
        f"persistent mode: no zwave calls expected for load button, got {len(zwave_calls)}"
