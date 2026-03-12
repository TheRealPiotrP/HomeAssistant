"""Integration tests for the Zooz ZEN35 → PowerView blueprint.

All services run against real HA components. ``SimulatedZEN35`` registers a
real ``zwave_js.set_config_parameter`` service and stores parameter state so
tests assert on LED state rather than call arguments. ``SimulatedPowerViewHub``
runs a real HTTP server so the real ``hunterdouglas_powerview`` integration,
``rest_command``, and the REST sensor all exercise their full network stack;
tests assert on hub state (scene activations, scheduled event toggles) directly.
"""
import pytest
from homeassistant.helpers import device_registry as dr

from .conftest import LEDColor, LEDState, ZEN35Param
from .simulations import SimulatedPowerViewHub as Hub


def _fire_button(hass, device_id, button_id):
    hass.bus.async_fire(
        "zwave_js_value_notification",
        {
            "device_id": device_id,
            "command_class_name": "Central Scene",
            "label": button_id,
            "value": "KeyPressed",
        },
    )


@pytest.mark.parametrize(
    "button_id, scene_id, expected_params",
    [
        (
            "Scene 001",
            Hub.SCENE_ID_OPEN,
            {
                ZEN35Param.LED1_COLOR: LEDColor.WHITE,
                ZEN35Param.LED1_MODE: LEDState.ON,
                ZEN35Param.LED2_MODE: LEDState.OFF,
                ZEN35Param.LED3_MODE: LEDState.OFF,
            },
        ),
        (
            "Scene 002",
            Hub.SCENE_ID_PARTIAL,
            {
                ZEN35Param.LED2_COLOR: LEDColor.WHITE,
                ZEN35Param.LED1_MODE: LEDState.OFF,
                ZEN35Param.LED2_MODE: LEDState.ON,
                ZEN35Param.LED3_MODE: LEDState.OFF,
            },
        ),
        (
            "Scene 003",
            Hub.SCENE_ID_CLOSED,
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
    sim_zen35,
    sim_powerview_hub,
    button_id,
    scene_id,
    expected_params,
):
    """Pressing a scene button (1–3) activates the correct scene and sets the correct LEDs."""
    topology = hass_topology
    device_id = topology.zen35_device.id
    await load_blueprint(topology.zen35_device, topology.labels)

    _fire_button(hass, device_id, button_id)
    await hass.async_block_till_done()

    assert sim_powerview_hub.scene_was_activated(scene_id), \
        f"{button_id}: scene {scene_id} should have been activated on the hub"

    # LED parameters reflect the active button
    assert sim_zen35.total_calls == len(expected_params), \
        f"Expected {len(expected_params)} LED calls, got {sim_zen35.total_calls}"
    for param, value in expected_params.items():
        got = sim_zen35.get_param(device_id, param)
        assert got == value, f"{button_id} param {param}: expected {value}, got {got}"

    # LED4 must not be touched by scene buttons
    assert sim_zen35.get_param(device_id, ZEN35Param.LED4_MODE) is None
    assert sim_zen35.get_param(device_id, ZEN35Param.LED4_COLOR) is None


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
    sim_zen35,
    led_theme,
    expected_colors,
):
    """On automation_reloaded, all LED color parameters are set to the theme."""
    topology = hass_topology
    device_id = topology.zen35_device.id
    await load_blueprint(topology.zen35_device, topology.labels, led_theme=led_theme)

    hass.bus.async_fire("automation_reloaded")
    await hass.async_block_till_done()

    for param, value in expected_colors.items():
        got = sim_zen35.get_param(device_id, param)
        assert got == value, f"{led_theme}: param {param} expected {value}, got {got}"


# ---------------------------------------------------------------------------
# Negative tests: label/area mismatches
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "button_id",
    ["Scene 001", "Scene 002", "Scene 003"],
    ids=["button1-no_open_label", "button2-no_partial_label", "button3-no_close_label"],
)
async def test_scene_button_no_matching_label_does_nothing(
    hass,
    hass_topology,
    load_blueprint,
    sim_zen35,
    sim_powerview_hub,
    button_id,
):
    """Buttons 1–3 with no scene carrying the expected label — no scene, no LED change."""
    topology = hass_topology
    no_button_ids = topology.labels._replace(
        open="no_such_label",
        partial="no_such_label",
        closed="no_such_label",
    )
    await load_blueprint(topology.zen35_device, no_button_ids)

    _fire_button(hass, topology.zen35_device.id, button_id)
    await hass.async_block_till_done()

    assert not sim_powerview_hub._activated_scenes, \
        f"{button_id}: no scene should be activated when no entity matches the label"
    assert sim_zen35.total_calls == 0, \
        f"{button_id}: no LED calls expected when no entity matches, got {sim_zen35.total_calls}"


@pytest.mark.parametrize(
    "button_id, lr_scene_id, kitchen_scene_id",
    [
        ("Scene 001", Hub.SCENE_ID_OPEN, Hub.SCENE_ID_KITCHEN_OPEN),
        ("Scene 002", Hub.SCENE_ID_PARTIAL, None),
        ("Scene 003", Hub.SCENE_ID_CLOSED,  None),
    ],
    ids=["button1-device_in_kitchen", "button2-device_in_kitchen", "button3-device_in_kitchen"],
)
async def test_scene_with_right_label_but_wrong_area_is_not_activated(
    hass,
    hass_topology,
    load_blueprint,
    sim_zen35,
    sim_powerview_hub,
    button_id,
    lr_scene_id,
    kitchen_scene_id,
):
    """Scene with matching label in a different area than the device must not activate."""
    topology = hass_topology

    dr.async_get(hass).async_update_device(
        topology.zen35_device.id, area_id=topology.areas.kitchen.id
    )

    await load_blueprint(topology.zen35_device, topology.labels)

    _fire_button(hass, topology.zen35_device.id, button_id)
    await hass.async_block_till_done()

    assert not sim_powerview_hub.scene_was_activated(lr_scene_id), \
        f"{button_id}: Living Room scene must not activate when device is in Kitchen"

    if kitchen_scene_id is not None:
        assert sim_powerview_hub.scene_was_activated(kitchen_scene_id), \
            f"{button_id}: Kitchen scene must activate when device is in Kitchen"




# ---------------------------------------------------------------------------
# Edge case: device has no area assigned
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "button_id",
    ["Scene 001", "Scene 002", "Scene 003", "Scene 004", "Scene 005"],
    ids=["button1-no_area", "button2-no_area", "button3-no_area", "button4-no_area",
         "load-no_area"],
)
async def test_button_does_nothing_when_device_has_no_area(
    hass,
    hass_topology,
    load_blueprint,
    sim_zen35,
    sim_powerview_hub,
    button_id,
):
    """All buttons are no-ops when the ZEN35 device has no area assigned."""
    topology = hass_topology

    dr.async_get(hass).async_update_device(topology.zen35_device.id, area_id=None)
    await load_blueprint(topology.zen35_device, topology.labels)

    _fire_button(hass, topology.zen35_device.id, button_id)
    await hass.async_block_till_done()

    assert not sim_powerview_hub._activated_scenes, \
        f"{button_id}: no scene should activate when device has no area"
    assert sim_zen35.total_calls == 0, \
        f"{button_id}: no LED calls expected when device has no area"


@pytest.mark.parametrize(
    "button_id",
    ["Scene 001", "Scene 002", "Scene 003"],
    ids=["button1", "button2", "button3"],
)
async def test_scene_buttons_do_not_affect_led4(
    hass,
    hass_topology,
    load_blueprint,
    sim_zen35,
    button_id,
):
    """Pressing a scene button (1–3) must not touch LED4."""
    topology = hass_topology
    device_id = topology.zen35_device.id
    await load_blueprint(topology.zen35_device, topology.labels)

    _fire_button(hass, device_id, button_id)
    await hass.async_block_till_done()

    assert sim_zen35.get_param(device_id, ZEN35Param.LED4_MODE) is None, \
        f"{button_id}: LED4 mode must not be touched by a scene button"
    assert sim_zen35.get_param(device_id, ZEN35Param.LED4_COLOR) is None, \
        f"{button_id}: LED4 color must not be touched by a scene button"


# ---------------------------------------------------------------------------
# Rainbow theme: button press colors
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "button_id, scene_id, expected_color_param, expected_color",
    [
        ("Scene 001", Hub.SCENE_ID_OPEN,    ZEN35Param.LED1_COLOR, LEDColor.BLUE),
        ("Scene 002", Hub.SCENE_ID_PARTIAL, ZEN35Param.LED2_COLOR, LEDColor.GREEN),
        ("Scene 003", Hub.SCENE_ID_CLOSED,  ZEN35Param.LED3_COLOR, LEDColor.YELLOW),
    ],
    ids=["button1-rainbow-blue", "button2-rainbow-green", "button3-rainbow-yellow"],
)
async def test_scene_button_rainbow_theme_sets_correct_color(
    hass,
    hass_topology,
    load_blueprint,
    sim_zen35,
    sim_powerview_hub,
    button_id,
    scene_id,
    expected_color_param,
    expected_color,
):
    """Rainbow theme: each scene button lights up in its assigned color."""
    topology = hass_topology
    device_id = topology.zen35_device.id
    await load_blueprint(topology.zen35_device, topology.labels, led_theme="rainbow")

    _fire_button(hass, device_id, button_id)
    await hass.async_block_till_done()

    assert sim_powerview_hub.scene_was_activated(scene_id), \
        f"{button_id}: scene {scene_id} should have been activated on the hub"
    assert sim_zen35.get_param(device_id, expected_color_param) == expected_color, \
        f"{button_id}: expected color {expected_color} on param {expected_color_param}"


# ---------------------------------------------------------------------------
# Confirm mode: LED turns on then off after timeout
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "button_id, active_mode_param, active_color_param",
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
    sim_zen35,
    button_id,
    active_mode_param,
    active_color_param,
):
    """Confirm mode: scene button LED turns on then off after confirm_timeout elapses."""
    topology = hass_topology
    device_id = topology.zen35_device.id
    await load_blueprint(topology.zen35_device, topology.labels, confirm_timeout=0.001)

    _fire_button(hass, device_id, button_id)
    await hass.async_block_till_done()

    # Active LED was set ON then OFF (confirm sequence)
    assert sim_zen35.param_history(device_id, active_mode_param) == [LEDState.ON, LEDState.OFF], \
        f"{button_id}: active LED must go ON then OFF after timeout"

    assert sim_zen35.get_param(device_id, active_color_param) == LEDColor.WHITE


@pytest.mark.parametrize(
    "initial_all_enabled, expected_led4_color",
    [
        (True,  LEDColor.RED),    # all enabled → toggle to disabled → blink red
        (False, LEDColor.WHITE),  # all disabled → toggle to enabled → blink white
    ],
    ids=["button4-confirm-toggle-off", "button4-confirm-toggle-on"],
)
async def test_button4_confirm_mode_led_turns_off_after_timeout(
    hass,
    hass_topology,
    load_blueprint,
    sim_zen35,
    sim_powerview_hub,
    initial_all_enabled,
    expected_led4_color,
):
    """Confirm mode: button 4 blinks (white when opting in, red when opting out) then goes dark."""
    topology = hass_topology
    device_id = topology.zen35_device.id

    if not initial_all_enabled:
        sim_powerview_hub.seed_events([
            {"id": 48860, "enabled": False, "sceneId": 36156},
            {"id": 21095, "enabled": False, "sceneId": 16652},
            {"id": 56009, "enabled": False, "sceneId": 46041},
        ])

    await load_blueprint(topology.zen35_device, topology.labels, confirm_timeout=0.001)

    _fire_button(hass, device_id, "Scene 004")
    await hass.async_block_till_done()

    # LED4 color set once to signal the new state
    assert sim_zen35.get_param(device_id, ZEN35Param.LED4_COLOR) == expected_led4_color

    # LED4 mode went ON (flash) then OFF (timeout)
    assert sim_zen35.param_history(device_id, ZEN35Param.LED4_MODE) == [
        LEDState.ON, LEDState.OFF
    ], "LED4 must go ON then OFF after confirm timeout"


# ---------------------------------------------------------------------------
# Load button (Scene 005)
# ---------------------------------------------------------------------------

async def test_load_button_confirm_mode_led_turns_on_then_off(
    hass,
    hass_topology,
    load_blueprint,
    sim_zen35,
):
    """Confirm mode: load button LED turns on briefly then turns off."""
    topology = hass_topology
    device_id = topology.zen35_device.id
    await load_blueprint(topology.zen35_device, topology.labels, confirm_timeout=0.001)

    _fire_button(hass, device_id, "Scene 005")
    await hass.async_block_till_done()

    assert sim_zen35.param_history(device_id, ZEN35Param.LOAD_MODE) == [
        LEDState.ON, LEDState.OFF
    ], "load LED must go ON then OFF in confirm mode"


async def test_rapid_double_press_not_dropped(
    hass,
    hass_topology,
    load_blueprint,
    sim_zen35,
    sim_powerview_hub,
):
    """A second press while the confirm delay is running must not be dropped.

    With mode: restart, the second press cancels the first run and starts fresh.
    Both presses see the same initial hub state (sensor not refreshed between
    them), so both opt out. Hub ends disabled and LED4 ends dark after the
    second run's confirm timeout.
    """
    topology = hass_topology
    device_id = topology.zen35_device.id
    await load_blueprint(topology.zen35_device, topology.labels, confirm_timeout=0.001)

    _fire_button(hass, device_id, "Scene 004")
    _fire_button(hass, device_id, "Scene 004")
    await hass.async_block_till_done()

    # Hub ended disabled (both presses saw all-enabled and opted out)
    for event_id in (48860, 21095, 56009):
        assert sim_powerview_hub.get_event(event_id)["enabled"] is False, \
            f"event {event_id}: expected disabled after double opt-out press"

    # LED4 ends dark after the second run's confirm timeout
    assert sim_zen35.param_history(device_id, ZEN35Param.LED4_MODE)[-1] == LEDState.OFF, \
        "LED4 must be OFF after the second run's confirm timeout"


async def test_load_button_persistent_mode_no_led_change(
    hass,
    hass_topology,
    load_blueprint,
    sim_zen35,
):
    """Persistent mode: pressing the load button does not touch any LED parameter."""
    topology = hass_topology
    await load_blueprint(topology.zen35_device, topology.labels, confirm_timeout=0)

    _fire_button(hass, topology.zen35_device.id, "Scene 005")
    await hass.async_block_till_done()

    assert sim_zen35.total_calls == 0, \
        f"persistent mode: no LED calls expected for load button, got {sim_zen35.total_calls}"


# ---------------------------------------------------------------------------
# PowerView scheduled event integration
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "initial_all_enabled, expected_enabled, expected_led4",
    [
        # Opted in (all enabled) → press → opt out: events disabled, LED4 ON (red)
        (True,  False, LEDState.ON),
        # Opted out (all disabled) → press → opt in: events enabled, LED4 OFF
        (False, True,  LEDState.OFF),
    ],
    ids=["button4-powerview-opts-out", "button4-powerview-opts-in"],
)
async def test_button4_powerview_toggles_scheduled_events(
    hass,
    hass_topology,
    load_blueprint,
    sim_zen35,
    sim_powerview_hub,
    initial_all_enabled,
    expected_enabled,
    expected_led4,
):
    """Button 4 with PowerView hub: PUTs to the hub for each event and updates LED4.

    Verified via real HTTP calls to SimulatedPowerViewHub:
    - Hub event state is updated to the expected enabled value.
    - LED4 mode reflects the new opted-in state.
    """
    topology = hass_topology
    device_id = topology.zen35_device.id

    if not initial_all_enabled:
        sim_powerview_hub.seed_events([
            {"id": 48860, "enabled": False, "sceneId": 36156},
            {"id": 21095, "enabled": False, "sceneId": 16652},
            {"id": 56009, "enabled": False, "sceneId": 46041},
        ])

    await load_blueprint(topology.zen35_device, topology.labels)

    _fire_button(hass, device_id, "Scene 004")
    await hass.async_block_till_done()

    # All three hub events updated via real HTTP PUT
    for event_id in (48860, 21095, 56009):
        event = sim_powerview_hub.get_event(event_id)
        assert event is not None
        assert event["enabled"] == expected_enabled, \
            f"event {event_id}: expected enabled={expected_enabled}, got {event['enabled']}"

    # LED4 reflects the new opted-in state
    assert sim_zen35.get_param(device_id, ZEN35Param.LED4_MODE) == expected_led4


async def test_init_sets_led4_from_powerview_sensor(
    hass,
    hass_topology,
    load_blueprint,
    sim_zen35,
    sim_powerview_hub,
):
    """On automation_reloaded with PowerView hub, LED4 reflects the sensor's enabled state.

    When all events are disabled (opted out), LED4 should be ON (red).
    Seeding the hub before load_blueprint is sufficient; load_blueprint injects
    the sensor state directly from the hub.
    """
    topology = hass_topology
    device_id = topology.zen35_device.id

    # Seed hub with all disabled; load_blueprint will inject sensor state from hub.
    sim_powerview_hub.seed_events([
        {"id": 48860, "enabled": False, "sceneId": 36156},
        {"id": 21095, "enabled": False, "sceneId": 16652},
        {"id": 56009, "enabled": False, "sceneId": 46041},
    ])

    await load_blueprint(topology.zen35_device, topology.labels)

    hass.bus.async_fire("automation_reloaded")
    await hass.async_block_till_done()

    assert sim_zen35.get_param(device_id, ZEN35Param.LED4_MODE) == LEDState.ON, \
        "LED4 must be ON (red) when all events are disabled (opted out)"
    assert sim_zen35.get_param(device_id, ZEN35Param.LED1_MODE) == LEDState.OFF
    assert sim_zen35.get_param(device_id, ZEN35Param.LED2_MODE) == LEDState.OFF
    assert sim_zen35.get_param(device_id, ZEN35Param.LED3_MODE) == LEDState.OFF


async def test_init_sets_led4_off_when_powerview_enabled(
    hass,
    hass_topology,
    load_blueprint,
    sim_zen35,
    sim_powerview_hub,
):
    """On automation_reloaded with PowerView hub, LED4 is OFF when all events are enabled."""
    topology = hass_topology
    device_id = topology.zen35_device.id
    # Topology seeds hub with all enabled; REST sensor polled during topology setup.

    await load_blueprint(topology.zen35_device, topology.labels)

    hass.bus.async_fire("automation_reloaded")
    await hass.async_block_till_done()

    assert sim_zen35.get_param(device_id, ZEN35Param.LED4_MODE) == LEDState.OFF, \
        "LED4 must be OFF when all events are enabled (opted in)"
    assert sim_zen35.get_param(device_id, ZEN35Param.LED1_MODE) == LEDState.OFF
    assert sim_zen35.get_param(device_id, ZEN35Param.LED2_MODE) == LEDState.OFF
    assert sim_zen35.get_param(device_id, ZEN35Param.LED3_MODE) == LEDState.OFF


