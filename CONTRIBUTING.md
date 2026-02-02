# Contributing

Thanks for helping build the Arc Raiders damage database. Every verified strategy makes the tracker more useful.

## Submitting Damage Data

The fastest way to contribute is to [open a GitHub issue](https://github.com/gotoplanb/arc-damage-tracker/issues/new) with:

1. **ARC name** (e.g., Bastion)
2. **Weapon or explosive** used
3. **Units to kill** (exact number or range like "8-10")
4. **Notes** (weak points, timing, positioning tips)
5. **Patch version** you tested on (check in-game settings)

We'll add it to the tracker and credit you in the commit.

## Verifying Existing Data

If you can confirm an existing strategy still works on the current patch:

1. Open an issue titled "Verify: [ARC name] - [Strategy]"
2. Include the patch version and any notes about changes

Verified strategies get a date badge on the detail page and are included in the "verified only" homepage filter.

## Code Contributions

### Setup

```bash
git clone https://github.com/gotoplanb/arc-damage-tracker.git
cd arc-damage-tracker
pip install flask pytest
python app.py
```

For E2E tests, install the additional dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

### Making Changes

1. Fork the repo and create a branch
2. Make your changes
3. Run `pytest test_app.py -v` and ensure all tests pass
4. Submit a pull request

### Editing `data.json`

When adding or modifying strategies, follow the existing schema:

```json
{
  "best": false,
  "verified": false,
  "notes": "Your strategy notes here",
  "items": [
    { "type": "weapon", "name": "Anvil", "units": "8-10" }
  ]
}
```

Rules:
- `type` must be `"weapon"` or `"explosive"`
- `units` can be a number (`3`) or range string (`"8-10"`)
- `verified` is `false` until tested, then a date string (`"2026-01-31"`)
- Only one strategy per ARC should have `"best": true`
- `notes` describe the overall approach, not individual items

### Project Structure

```
app.py                  Flask routes and data loading
data.json               All ARC and strategy data
test_app.py             Pytest unit tests
tests/
  test_e2e_otel.py      E2E smoke tests (uses smokeshow library)
templates/
  base.html             Layout, Tailwind config, shared styles
  index.html            Homepage with threat-level grouping
  arc_detail.html       Individual ARC strategy cards
Procfile                Heroku web process
requirements.txt        Python dependencies
TESTING.md              E2E test documentation and trace structure
.github/workflows/
  deploy.yml            CI test + Heroku deploy pipeline
```

## Reporting Bugs

Open an issue describing what you expected vs. what happened. Screenshots are helpful, especially for layout or display issues.
