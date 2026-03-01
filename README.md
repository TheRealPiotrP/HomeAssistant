# HomeAssistant

Home Assistant scripts, blueprints, and related.

## Blueprints

- [**Zooz ZEN35 → PowerView**](blueprints/automation/zooz_zen35_powerview/) — Automatically map ZEN35 switches to Hunter Douglas PowerView blind scenes using areas and labels. No per-room entity selection.

## Testing

Blueprint tests use [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component). 

### Initial Setup (one-time)

From the repo root:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-test.txt
```

### Running Tests

```bash
source venv/bin/activate
pytest tests/ -v
```
