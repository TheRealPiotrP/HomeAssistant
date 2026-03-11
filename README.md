# HomeAssistant

Home Assistant scripts, blueprints, and related.

## Blueprints

### [Zooz ZEN35 → PowerView](blueprints/automation/zooz_zen35_powerview/)

Automatically map a Zooz ZEN35 wireless switch to Hunter Douglas PowerView blind scenes using area + label discovery — no per-room entity selection required. Assign labels to your PowerView scene entities, put the ZEN35 and those entities in the same area, and the blueprint wires everything up.

**Button mapping:**
| Button | Action |
|--------|--------|
| 1 | Activate "fully open" scene |
| 2 | Activate "partially open" scene |
| 3 | Activate "fully close" scene |
| 4 | Toggle PowerView scheduled events (opt in/out of automation) |
| Load | Confirm-mode LED flash (when confirm timeout > 0) |

**Inputs:**
- ZEN35 device
- Labels for each scene type (defaults: `powerview_scenes_open`, `powerview_scenes_partially_open`, `powerview_scenes_closed`)
- LED color theme (default or rainbow)
- Confirm timeout (0 = LEDs stay on permanently after press; >0 = LED flashes then turns off)

**Requirements:** `hunterdouglas_powerview` integration, `rest_command.powerview_set_scheduled_event`, and `sensor.powerview_scheduled_events` configured in your HA instance.

> **Note:** HA stores label IDs with dots replaced by underscores. If a label selector shows "Unknown item", open the dropdown and re-select the label to pick up the correct ID.

## Testing

Blueprint tests use [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component) and run against simulated hardware — no real ZEN35 or PowerView hub required.

### Initial Setup (one-time)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-test.txt
```

### Running Tests

```bash
source venv/bin/activate
pytest -v
```
