# HomeAssistant

Home Assistant automation blueprints and related configurations.

---

## Zooz ZEN35 → Hunter Douglas PowerView

Control Hunter Douglas PowerView blinds from a Zooz ZEN35 wireless switch using area + label auto-discovery. Place the ZEN35 and your PowerView scene entities in the same HA area, attach the right labels, and the blueprint wires everything up — no per-room entity selection needed.

### Button Mapping

| Button | Action |
|--------|--------|
| **1** | Activate "fully open" scene |
| **2** | Activate "partially open" scene |
| **3** | Activate "fully close" scene |
| **4** | Toggle PowerView scheduled events (opt the room in/out of its automated schedule) |
| **Load** | (No blinds action) Flashes the load LED briefly when Confirm Timeout > 0 |

### LED Behavior

After any button 1–3 press, the corresponding LED turns **on** and the others turn **off**, giving visual confirmation of the current shade position.

- **Persistent mode** (`Confirm Timeout = 0`, default): the active LED stays on until a different button is pressed.
- **Confirm mode** (`Confirm Timeout > 0`): the active LED turns on for the configured number of seconds, then turns off automatically.

Button 4 LED reflects the scheduled-event state for the room:
- **Off** — all room events are enabled (room is following its schedule).
- **On (red)** — one or more events are disabled (room has opted out of the schedule).

---

## Quick Start

### 1. Prerequisites

You need:

- A **Zooz ZEN35** switch added to Home Assistant via **Z-Wave JS**
- The **Hunter Douglas PowerView** integration installed and connected to your hub
- PowerView **scenes** already configured in the PowerView app and visible in HA as `scene.*` entities

### 2. Create an Area for the Room

In **Settings → Areas & Zones → Areas**, create an area for the room (e.g., *Living Room*).

Assign the **ZEN35 device** to that area:
- Go to **Settings → Devices & Services → Z-Wave JS**
- Find the ZEN35 device → click it → click **Edit** → set the Area to *Living Room*

### 3. Create the Scene Labels

Labels are how the blueprint discovers which scenes to activate. You need three labels — one per scene type.

Go to **Settings → Labels** and create the following. When creating each label, set the **Name** exactly as shown so HA generates the matching label ID automatically:

| Label Name | Generated Label ID | Purpose |
|------------|--------------------|---------|
| `powerview_scenes_open` | `powerview_scenes_open` | Fully open scenes |
| `powerview_scenes_partially_open` | `powerview_scenes_partially_open` | Partially open scenes |
| `powerview_scenes_closed` | `powerview_scenes_closed` | Fully closed scenes |

> **Tip:** You can use any label names you like. If you choose different names, enter their generated label IDs in the blueprint inputs when creating the automation. The defaults above match the blueprint's pre-filled values.
>
> **HA quirk:** HA replaces dots in label names with underscores when generating the label ID (e.g. `powerview.scenes.open` becomes `powerview_scenes_open`). If a label selector in the blueprint shows "Unknown item", open the dropdown and re-select the label to pick up the correct ID.

### 4. Label and Place Your PowerView Scene Entities

For **each room**, assign each relevant `scene.*` entity to the room's area and attach the appropriate label.

Go to **Settings → Entities**, search for your PowerView scenes, and for each one:
1. Click the entity → click **Edit**
2. Set **Area** to the room's area (e.g., *Living Room*)
3. Add the matching label (e.g., `powerview_scenes_open` for the fully-open scene)

Repeat for the partially-open and closed scenes.

> The blueprint uses both area *and* label to match entities, so scenes in other rooms that share the same labels are safely ignored.

### 5. Add Required YAML Configuration

The blueprint uses a `rest_command` to enable/disable PowerView scheduled events, and a REST sensor to read their current state. Add the following to your `configuration.yaml`, replacing `YOUR_HUB_IP` with your PowerView hub's IP address:

```yaml
rest_command:
  powerview_set_scheduled_event:
    url: "{{ hub }}/api/scheduledEvents/{{ id }}"
    method: PUT
    content_type: application/json
    payload: '{"scheduledEvent": {"enabled": {{ enabled }}}}'

sensor:
  - platform: rest
    name: "PowerView Scheduled Events"
    unique_id: powerview_scheduled_events
    resource: "http://YOUR_HUB_IP/api/scheduledEvents"
    value_template: "{{ value_json.scheduledEventData | length }}"
    json_attributes:
      - scheduledEventData
    scan_interval: 60
```

Restart Home Assistant after saving.

> **Note:** The hub URL in `rest_command` is passed dynamically by the blueprint — it auto-discovers the hub address from the PowerView integration, so no hardcoded IP is needed there. The REST sensor does require the hub IP directly.

### 6. Install the Blueprint

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FTheRealPiotrP%2FHomeAssistant%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fzooz_zen35_powerview%2Fzooz_zen35_powerview.yaml)

Or manually: go to **Settings → Automations & Scenes → Blueprints → Import Blueprint** and paste the raw URL to `zooz_zen35_powerview.yaml` from this repository.

### 7. Create the Automation

Go to **Settings → Automations & Scenes → Blueprints**, find *Zooz ZEN35 → PowerView (Auto-Configuring)*, and click **Create Automation**.

Fill in the inputs:

| Input | Description | Default |
|-------|-------------|---------|
| **ZEN35 Switch** | Select the ZEN35 device for this room | — |
| **Label for "fully open" scenes** | Label ID applied to fully-open scenes | `powerview_scenes_open` |
| **Label for "partially open" scenes** | Label ID applied to partially-open scenes | `powerview_scenes_partially_open` |
| **Label for "fully close" scenes** | Label ID applied to fully-closed scenes | `powerview_scenes_closed` |
| **LED Color Theme** | Color of scene button LEDs | Default (white) |
| **Confirm Timeout** | Seconds the active LED stays lit (0 = permanent) | `0` |

Save the automation. The blueprint initializes the ZEN35 LEDs immediately on the next HA start or automation reload.

> **One automation per room.** Each ZEN35 gets its own automation instance. All rooms can share the same label IDs — the area filter keeps them isolated.

---

## Multi-Room Setup

Repeat steps 2–7 for each room. Each room gets:

- Its own area
- Its own ZEN35 device assigned to that area
- Scene entities assigned to that area, each with the appropriate label
- Its own automation instance pointing at the room's ZEN35

The label IDs are **shared across rooms** — `powerview_scenes_open` can be applied to scenes in the living room, bedroom, and office simultaneously. The blueprint only activates entities that match both the label *and* the ZEN35's area.

---

## Configuration Reference

### LED Color Themes

| Theme | Load | Button 1 | Button 2 | Button 3 | Button 4 |
|-------|------|----------|----------|----------|----------|
| **Default** | White | White | White | White | Red |
| **Rainbow** | Cyan | Blue | Green | Yellow | Red |

Button 4 is always red regardless of theme (indicates scheduled-events opt-out state).

### Confirm Timeout

- **0 (default):** Active LED stays on until replaced by another button press. Best for rooms where you want a persistent visual indicator of shade position.
- **1–60 seconds:** Active LED turns on for that many seconds, then turns off. The load button LED also flashes in this mode when pressed.

### Button 4 / Scheduled Events

Button 4 reads the `scheduledEventData` attribute from `sensor.powerview_scheduled_events` to determine whether all events in the room are currently enabled. It then calls `rest_command.powerview_set_scheduled_event` for each event to toggle them all.

The blueprint identifies which scheduled events belong to the room by looking for scene entities in the area that have a `scheduledEvent_id` state attribute (set by the PowerView integration on scenes that have an associated scheduled event). If no scenes in the area have this attribute, button 4 does nothing.

---

## Troubleshooting

**Label selector shows "Unknown item"**
Open the dropdown and re-select the label. This is a known HA bug where stored dot-to-underscore label IDs can appear stale until re-selected.

**Button press activates wrong room's scenes**
Check that the ZEN35 device and all scene entities are assigned to the *same* area. Area assignment is the primary isolation mechanism.

**Button 4 does nothing**
1. In **Developer Tools → States**, check that `sensor.powerview_scheduled_events` exists and its attributes include a `scheduledEventData` list with entries.
2. Confirm `rest_command.powerview_set_scheduled_event` is in `configuration.yaml` and HA has been restarted since adding it.
3. Check that at least one scene entity in the ZEN35's area has a `scheduledEvent_id` attribute — visible in **Developer Tools → States** by clicking the scene entity.

**LEDs show wrong colors after HA restart**
The blueprint re-applies LED colors and turns button LEDs off on every HA start and automation reload. If colors look wrong, verify the `led_theme` input in the automation, then reload the automation via **Settings → Automations** → the automation's three-dot menu → **Reload**.

**Scene not activating on button press**
1. In **Developer Tools → States**, confirm the scene entity has the correct area and label assigned.
2. In **Developer Tools → Events**, listen for `zwave_js_value_notification` and press the button to verify the event fires with `command_class_name: Central Scene`.
3. Confirm the automation is enabled.

---

## Testing (Development)

Blueprint tests use [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component) and run against simulated hardware — no real ZEN35 or PowerView hub required.

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

# By name
pytest -k "test_button_1_opens_scene" -v
```

### Lint

```bash
ruff check .
```
