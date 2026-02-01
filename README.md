# Arc Raiders Damage Tracker

Community-sourced database of shots and explosives needed to kill each ARC in [Arc Raiders](https://www.embark-studios.com/games/arcraiders). Strategies are verified in-game and contributed via GitHub issues.

**Live site:** https://arc-damage-tracker-3bf88c91527f.herokuapp.com

## Features

- All 17 ARCs grouped by threat level (Extreme through Low)
- Best strategy callout per ARC on the homepage
- Toggle to show only ARCs with verified data
- Detail pages with all known strategies, type badges, and verification dates
- Info modals for quick strategy notes without leaving the homepage

## Tech Stack

- **Backend:** Flask (Python)
- **Frontend:** Tailwind CSS (CDN), Alpine.js, HTMX
- **Data:** Single `data.json` file (no database)
- **Hosting:** Heroku (gunicorn)
- **CI/CD:** GitHub Actions (test + deploy on push to main)

## Local Development

```bash
pip install flask pytest
python app.py
```

The app runs at `http://localhost:5000` with debug mode enabled.

## Running Tests

```bash
pytest test_app.py -v
```

Tests validate data structure integrity, route behavior, strategy schema, and business rules (e.g., max one "best" strategy per ARC).

## Data Model

All ARC damage data lives in `data.json`. Each ARC has a `strategies` array:

```json
{
  "best": true,
  "verified": "2026-01-31",
  "notes": "Throw right underneath",
  "items": [
    { "type": "explosive", "name": "Trailblazer", "units": 3 }
  ]
}
```

- **best** — One per ARC, shown on the homepage
- **verified** — Date string when tested in-game, `false` if unverified
- **notes** — Strategy-level tips (not per-item)
- **items** — Array of weapons/explosives; supports multi-item combos

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to submit verified damage data, report bugs, or propose changes.

## License

This project is not affiliated with Embark Studios. Arc Raiders is a trademark of Embark Studios AB.
