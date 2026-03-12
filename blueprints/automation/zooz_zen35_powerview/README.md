# ZEN35 → PowerView Blueprint

Automatically map Zooz ZEN35 switches to Hunter Douglas PowerView blind scenes using **areas + labels**. No per-room entity selection needed.

## Button layout

```
┌─────────────────────┐
│   dimmer  (load)    │
│         💡          │
├──────────┬──────────┤
│   💡  1  │   💡  2  │
├──────────┼──────────┤
│   💡  3  │   💡  4  │
└──────────┴──────────┘
```

| Button | Action |
|--------|--------|
| **Dimmer** | Controls the physical load (light/fan). In confirm mode, pressing it flashes the load LED briefly. |
| **Button 1** | Activate "fully open" PowerView scenes |
| **Button 2** | Activate "partially open" PowerView scenes |
| **Button 3** | Activate "fully close" PowerView scenes |
| **Button 4** | Toggle PowerView scheduled events for the room; **red = opted out** |

## LED indicators

### Color themes

Colors are applied to the device on HA startup and whenever the automation is saved.

```
┌─────────────────────┐     ┌─────────────────────┐
│   dimmer  (load)    │     │   dimmer  (load)    │
│         ⚪          │     │         🩵          │
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
| **Rainbow** | 🩵 cyan | 🔵 blue | 🟢 green | 🟡 yellow | 🔴 red |

The load LED normally uses its default HA behavior (mode 0): on when the load is off, off when it is on. The blueprint only sets its color — it never overrides the mode. Exception: in confirm mode, pressing the dimmer button briefly overrides the load LED to always-on for `confirm_timeout` seconds, then turns it off.

### Persistent mode (`confirm_timeout = 0`, default)

The active LED stays lit until a different button is pressed.

**Example — scene 2 active, scheduled events disabled (opted out):**

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

**Example — scene 2 active, scheduled events enabled (opted in):**

```
┌─────────────────────┐
│   dimmer  (load)    │
│         ⚪          │  ← on when load is off (locator behavior)
├──────────┬──────────┤
│   ⬛  1  │   ⚪  2  │  ← scene 2 active
├──────────┼──────────┤
│   ⬛  3  │   ⬛  4  │  ← opted in (scheduled events on, LED4 dark)
└──────────┴──────────┘
```

### Confirm mode (`confirm_timeout > 0`)

The active LED lights up briefly to acknowledge the press, then turns off.
Button 4 blinks **white** when opting in (enabling scheduled events), **red** when opting out (disabling scheduled events).
The dimmer/load button also flashes its LED briefly in this mode.

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

**After timeout — steady state:**

```
┌─────────────────────┐
│   dimmer  (load)    │
│         ⚪          │  ← unchanged (load LED not affected)
├──────────┬──────────┤
│   ⬛  1  │   ⬛  2  │
├──────────┼──────────┤
│   ⬛  3  │   ⬛  4  │
└──────────┴──────────┘
```

## Setup

See the [root README](../../../README.md) for full setup instructions. Quick summary:

### 1. Create labels

In **Settings → Labels**, create these labels:

- `powerview_scenes_open` — scenes that fully open shades
- `powerview_scenes_partially_open` — scenes that partially open shades (e.g. 50%)
- `powerview_scenes_closed` — scenes that fully close shades

### 2. Assign labels to scene entities

Assign each label to the matching PowerView `scene.*` entities (e.g. `scene.living_room_open`).

### 3. Use areas

Put each ZEN35 device in the same area as its PowerView scenes.
Example: ZEN35 in "Living Room" + PowerView scenes in "Living Room".

### 4. Add required YAML configuration

Add `rest_command.powerview_set_scheduled_event` and `sensor.powerview_scheduled_events` to `configuration.yaml`. See the [root README](../../../README.md#5-add-required-yaml-configuration) for the exact YAML.

### 5. Create one automation per switch

- Import the blueprint (or copy `zooz_zen35_powerview.yaml` to `config/blueprints/automation/zooz_zen35_powerview/`)
- Create an automation from the blueprint
- Select the ZEN35 device
- Choose your **LED Color Theme** (`default` or `rainbow`)
- Set **Confirm Timeout** if you want LEDs to go dark after a press (0 = stay on)
- Optionally change the label IDs if you used different ones
- Save — no entity selection needed; discovery is automatic per area

## Testing

### Automated tests

From the repo root, install test deps and run pytest:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-test.txt
pytest -v
```

Tests fire `zwave_js_value_notification` events into a real Home Assistant instance and verify actual state changes — scenes activate, scheduled events toggle, and `zwave_js.set_config_parameter` calls are captured to verify LED parameter values.

### Manual hardware checklist

Run this after deploying to a real ZEN35. Open **Developer Tools → States** in a side window to watch entity state changes in real time.

#### 1. Startup colors

Save (or reload) the automation and check that the LEDs immediately update to your chosen theme — no button press required.

| Theme | Expected |
|-------|----------|
| Default | Load ⚪, buttons 1–3 ⚪, button 4 🔴 |
| Rainbow | Load 🩵, button 1 🔵, button 2 🟢, button 3 🟡, button 4 🔴 |

#### 2. Buttons 1–3 — scene activation

Press each button and verify:
- The corresponding PowerView scene activates (shades move).
- In **persistent mode**: the pressed button's LED stays lit; the others go dark.
- In **confirm mode**: the pressed button's LED flashes briefly, then all go dark.

#### 3. Button 4 — scheduled events toggle

| Starting state | Press | Expected LED4 |
|----------------|-------|---------------|
| All events enabled (opted in) | Button 4 | ⬛ dark |
| Any event disabled (opted out) | Button 4 | 🔴 red |

In **confirm mode** the LED flashes (white = opting in, red = opting out) then goes dark regardless of the final state.

#### 4. Load / dimmer button

- Physical load should switch normally (this is handled by the switch hardware, not the blueprint).
- **Persistent mode**: load LED follows locator behavior (on when load is off, off when load is on). No change from pressing the dimmer.
- **Confirm mode**: load LED briefly flashes on when the dimmer is pressed, then goes dark.

#### 5. Area isolation

If you have two ZEN35s in different rooms, press a button on one switch and confirm that only the scenes in that switch's area activate — scenes in the other room must not move.
