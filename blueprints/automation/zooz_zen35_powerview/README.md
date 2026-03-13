# ZEN35 → PowerView Blueprint

Automatically map Zooz ZEN35 switches to Hunter Douglas PowerView blind scenes using **areas + labels**. No per-room entity selection needed.

| Button | Action |
|--------|--------|
| **Dimmer** | Controls the physical load (light/fan). In confirm mode, pressing it flashes the load LED briefly. |
| **Button 1** | Activate "fully open" PowerView scenes |
| **Button 2** | Activate "partially open" PowerView scenes |
| **Button 3** | Activate "fully close" PowerView scenes |
| **Button 4** | Toggle PowerView scheduled events for the room; **red = opted out** |

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

Three pieces of config are needed: a `rest_command` for toggling scheduled events, a REST sensor for reading their state, and `customize` entries to attach scheduled event IDs to scene entities. Keep them together in a `powerview/` folder under your HA config directory.

> **Note:** HA packages (`!include_dir_named packages/`) do not reliably support `homeassistant: customize:`, `rest_command:`, or list-based `sensor:` in newer HA versions. Use direct `!include` instead.

#### 5a. Wire up `configuration.yaml`

Add these lines (merge with any existing `homeassistant:` block):

```yaml
homeassistant:
  customize: !include powerview/customize.yaml

rest_command: !include powerview/rest_commands.yaml

sensor: !include powerview/sensors.yaml
```

#### 5b. Find your scheduled event IDs

The blueprint discovers which scheduled events belong to a room via a `scheduledEvent_id` attribute on each scene entity. You need to add this attribute manually.

Query your hub to find the IDs:

```
GET http://<hub-ip>/api/scheduledEvents
```

The response contains a `scheduledEventData` array. Each entry has an `id` and a `sceneId` that links it to a scene. Match those scene IDs to your HA scene entities to find which ID to assign to each.

#### 5c. Create `powerview/customize.yaml`

```yaml
scene.living_room_open:
  scheduledEvent_id: 48860
scene.living_room_partial:
  scheduledEvent_id: 21095
scene.living_room_closed:
  scheduledEvent_id: 56009
# Repeat for each room's scenes
```

#### 5d. Create `powerview/rest_commands.yaml`

```yaml
powerview_set_scheduled_event:
  url: "{{ hub }}/api/scheduledEvents/{{ id }}"
  method: PUT
  content_type: application/json
  payload: '{"scheduledEvent": {"enabled": {{ enabled }}}}'
```

#### 5e. Create `powerview/sensors.yaml`

The hub URL is auto-discovered from the PowerView integration. The `availability` template keeps the sensor quiet until the integration is loaded.

```yaml
- platform: rest
  name: "PowerView Scheduled Events"
  unique_id: powerview_scheduled_events
  resource_template: >-
    {% set pv_ents = integration_entities('hunterdouglas_powerview') %}
    {% set base = device_attr(pv_ents | first, 'configuration_url').split('/api/')[0] if pv_ents else '' %}
    {{ base or 'http://127.0.0.1' }}/api/scheduledEvents
  availability: "{{ integration_entities('hunterdouglas_powerview') | length > 0 }}"
  value_template: "{{ value_json.scheduledEventData | length }}"
  json_attributes:
    - scheduledEventData
  scan_interval: 60
```

After saving all files, do a **full HA restart** (not Quick Reload — new integrations require a full restart to register).

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

```
┌─────────────────────┐     ┌─────────────────────┐
│   dimmer  (load)    │     │   dimmer  (load)    │
│         ⚪          │     │         🩷          │
├──────────┬──────────┤     ├──────────┬──────────┤
│   ⚪  1  │   ⚪  2  │     │   🔵  1  │   🟢  2  │
├──────────┼──────────┤     ├──────────┼──────────┤
│   ⚪  3  │   🔴  4  │     │   🟡  3  │   🔴  4  │
└──────────┴──────────┘     └──────────┴──────────┘
      default theme               rainbow theme
```

| | Load | Button 1 | Button 2 | Button 3 | Button 4 |
|-|------|----------|----------|----------|----------|
| **Default** | ⚪ white | ⚪ white | ⚪ white | ⚪ white | 🔴 red |
| **Rainbow** | 🩷 pink | 🔵 blue | 🟢 green | 🟡 yellow | 🔴 red |

Colors are applied on HA startup and whenever the automation is saved. Button 4 is always red regardless of theme.

The load LED uses its default HA behavior (on when load is off, off when load is on). The blueprint only sets its color, never its mode — except in confirm mode, where pressing the dimmer briefly overrides it to always-on for `confirm_timeout` seconds.

### LED Behavior

**Persistent mode** (`confirm_timeout = 0`, default) — the active LED stays lit until a different button is pressed.

**Example — scene 2 active, scheduled events disabled:**
```
┌─────────────────────┐
│   dimmer  (load)    │
│         ⚪          │  ← on when load is off (locator behavior)
├──────────┬──────────┤
│   ⬛  1  │   ⚪  2  │  ← scene 2 active
├──────────┼──────────┤
│   ⬛  3  │   🔴  4  │  ← opted out (scheduled events off)
└──────────┴──────────┘
```

**Example — scene 2 active, scheduled events enabled:**
```
┌─────────────────────┐
│   dimmer  (load)    │
│         ⚪          │
├──────────┬──────────┤
│   ⬛  1  │   ⚪  2  │  ← scene 2 active
├──────────┼──────────┤
│   ⬛  3  │   ⬛  4  │  ← opted in (LED4 dark)
└──────────┴──────────┘
```

**Confirm mode** (`confirm_timeout > 0`) — the active LED lights up briefly, then turns off. Button 4 blinks white when opting in, red when opting out.

**Immediately after pressing button 2:**
```
┌─────────────────────┐
│   dimmer  (load)    │
│         ⚪          │
├──────────┬──────────┤
│   ⬛  1  │   ⚪  2  │  ← briefly lit
├──────────┼──────────┤
│   ⬛  3  │   ⬛  4  │
└──────────┴──────────┘
```

**After timeout:**
```
┌─────────────────────┐
│   dimmer  (load)    │
│         ⚪          │
├──────────┬──────────┤
│   ⬛  1  │   ⬛  2  │
├──────────┼──────────┤
│   ⬛  3  │   ⬛  4  │
└──────────┴──────────┘
```

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

## Manual Hardware Checklist

Run this after deploying to a real ZEN35. Open **Developer Tools → States** in a side window to watch entity state changes in real time.

### 1. Startup Colors

Save (or reload) the automation and check that the LEDs immediately update to your chosen theme — no button press required.

| Theme | Expected |
|-------|----------|
| Default | Load ⚪, buttons 1–3 ⚪, button 4 🔴 |
| Rainbow | Load 🩷, button 1 🔵, button 2 🟢, button 3 🟡, button 4 🔴 |

### 2. Buttons 1–3 — Scene Activation

Press each button and verify:
- The corresponding PowerView scene activates (shades move).
- In **persistent mode**: the pressed button's LED stays lit; the others go dark.
- In **confirm mode**: the pressed button's LED flashes briefly, then all go dark.

### 3. Button 4 — Scheduled Events Toggle

| Starting state | Press | Expected LED4 |
|----------------|-------|---------------|
| All events enabled (opted in) | Button 4 | ⬛ dark |
| Any event disabled (opted out) | Button 4 | 🔴 red |

In **confirm mode** the LED flashes (white = opting in, red = opting out) then goes dark regardless of the final state.

### 4. Load / Dimmer Button

- Physical load should switch normally (handled by the switch hardware, not the blueprint).
- **Persistent mode**: load LED follows locator behavior (on when load is off, off when load is on). No change from pressing the dimmer.
- **Confirm mode**: load LED briefly flashes on when the dimmer is pressed, then goes dark.

### 5. Area Isolation

If you have two ZEN35s in different rooms, press a button on one switch and confirm that only the scenes in that switch's area activate — scenes in the other room must not move.
