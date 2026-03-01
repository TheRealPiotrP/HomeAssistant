# ZEN35 → PowerView Blueprint

Automatically map Zooz ZEN35 switches to Hunter Douglas PowerView blind scenes using **areas + labels**. No per-room entity selection needed.

## Button layout

| Button | Action |
|--------|--------|
| **Big button** | Not handled — controls the physical load (light/fan) |
| **Button 1** | Activate "fully open" PowerView scenes |
| **Button 2** | Activate "partially open" PowerView scenes |
| **Button 3** | Activate "fully close" PowerView scenes |
| **Button 4** | Toggle central-control mode (input_boolean) |

## Setup

### 1. Create labels

In **Settings → Labels**, create (or reuse) these labels (IDs must match what you use in the blueprint):

- `powerview.scenes.open` — scenes that fully open shades
- `powerview.scenes.partially_open` — scenes that partially open shades (e.g. 50%)
- `powerview.scenes.closed` — scenes that fully close shades
- `powerview.automated` — input_boolean that enables your central blinds automation

### 2. Assign labels to scenes and helpers

- Assign the scene labels to your PowerView scene entities (e.g. `scene.living_room_open`)
- Assign the central-control label to an `input_boolean` helper (e.g. `input_boolean.living_room_blinds_central`)

### 3. Use areas

- Put each ZEN35 device in the same area as the PowerView scenes and input_boolean for that room
- Example: ZEN35 in "Living Room" + PowerView scenes in "Living Room" + `input_boolean.living_room_blinds_central` in "Living Room"

### 4. Create one automation per switch

- Import the blueprint (or copy `zooz_zen35_powerview.yaml` to `config/blueprints/automation/zooz_zen35_powerview/`)
- Create an automation from the blueprint
- Select the ZEN35 device
- Optionally change the label IDs if you used different ones
- Save — no entity selection needed; discovery is automatic per area

### 5. Central-control automation

Create a separate automation that triggers when `input_boolean.living_room_blinds_central` (or similar) is turned on, and runs your central blinds logic. Button 4 on the ZEN35 toggles that helper.

## Testing

From the repo root, install test deps and run pytest:

```bash
pip install -r requirements-test.txt
pytest tests/ -v
```

Tests fire `zwave_js_value_notification` events and assert on `scene.turn_on`, `input_boolean.toggle`, and `zwave_js.set_config_parameter` calls.
