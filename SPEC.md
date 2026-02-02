# Arc Raiders Damage Tracker - Specification

This document describes the application that should be built. It can be used as a prompt to generate the app from scratch.

## Overview

Build a community-sourced damage tracker for the game Arc Raiders. The app displays how many shots or explosives are needed to kill each ARC (enemy type), organized by threat level. Data is stored in a single JSON file with no database.

## Requirements

### Data Model

A single `data.json` file at the project root contains all application data:

**Top-level keys:**
- `arcs` — Array of ARC objects with full strategy data
- `arc_list` — Array of basic ARC info (slug, name, threat_level, type, kill_xp, loot_xp) used for homepage listing
- `weapons` — Reference array of all weapons with name, class, and ammo type
- `explosives` — Reference array of all explosives with name and type
- `meta_notes` — Patch version, last updated date, key balance changes

**ARC object:**
```json
{
  "slug": "bastion",
  "name": "Bastion",
  "threat_level": "critical",
  "type": "Heavy Assault",
  "kill_xp": 500,
  "loot_xp": 250,
  "strategies": [
    {
      "best": true,
      "verified": "2026-01-31",
      "notes": "Throw right underneath",
      "items": [
        { "type": "explosive", "name": "Trailblazer", "units": 3 }
      ]
    }
  ]
}
```

- `hp` is optional (only bosses have it)
- `strategies` is an array; each strategy has `best` (boolean), `verified` (date string or `false`), `notes` (string), and `items` (array)
- Each item has `type` ("weapon" or "explosive"), `name`, and `units` (integer or range string like "8-10")
- Only one strategy per ARC should have `best: true`
- Multi-item strategies are supported (e.g., "1x Wolfpack + 1x Hullcracker") but single-item is the common case

### Routes

**`GET /`** — Homepage
- Load all data from `data.json`
- Group ARCs by threat level: extreme, critical, high, moderate, low
- For each ARC, determine:
  - `has_data`: whether the ARC has any strategies
  - `has_verified`: whether any strategy has a truthy `verified` value
  - `best`: the strategy marked `best: true`, extract its item names and units for display
- For single-item best strategies, display as "3x Trailblazer"
- For multi-item best strategies, display joined names like "1x Wolfpack + 1x Hullcracker"
- Pass grouped ARCs and threat order to the template

**`GET /arc/<slug>`** — Detail page
- Find the ARC in `data.json` by slug
- If not found in the `arcs` array, check `arc_list` for basic info and render with empty strategies
- If not in either list, return 404
- Render all strategies as cards

### Homepage Template (`index.html`)

- Toggle switch (Alpine.js `x-data="{ dataOnly: true }"`): "Show only verified ARCs"
  - When on: hide ARCs without verified strategies, hide threat sections with no verified ARCs
  - When off: show all ARCs
- Each threat level gets a section header with colored text
- Each ARC row shows:
  - Name (linked to detail page)
  - Type label (hidden on mobile)
  - Best strategy summary (units + name) in emerald green monospace
  - Info button that opens a modal with strategy notes
- ARCs with data but no best strategy show a "has data" badge
- ARCs without data show dimmed text
- Rows have colored left border matching threat level
- Rows with data get a tinted background matching threat level

### Detail Template (`arc_detail.html`)

- Back link to homepage
- ARC name, threat level badge (colored), type, kill XP, loot XP
- "Strategies" section header
- Each strategy renders as a card:
  - Items displayed with type badge (blue for weapon, orange for explosive), name, and units
  - Multi-item strategies show items separated by "+"
  - "best" badge (emerald) if applicable
  - Verified date badge if applicable
  - Notes text below items
  - Best strategy card gets emerald border/background tint; others get gray
- Empty state if no strategies: "No strategies documented yet."

### Base Template (`base.html`)

- Tailwind CSS via CDN with custom theme:
  - Threat level colors: extreme (#dc2626), critical (#ef4444), high (#f97316), moderate (#eab308), low (#22c55e)
  - Each has a muted variant for backgrounds
  - Font: Inter for body, JetBrains Mono for monospace
- Alpine.js v3 and HTMX v2 via CDN
- Custom utilities: `.glow-red` (text shadow), `.glass` (frosted backdrop blur)
- Layout: centered column, max-width 2xl, responsive padding
- Header: "Arc Raiders" in red with glow effect, "Damage Tracker" subtitle
- Footer: "Community-sourced data" with GitHub issue link, commit SHA linking to GitHub commit

### Commit SHA Display

- `get_commit_sha()` reads `SOURCE_VERSION` env var (set during deploy) or falls back to `git rev-parse HEAD`
- Truncated to 7 characters, displayed in footer
- Injected via Flask context processor

## Tech Stack

- **Python 3.12+** with Flask
- **Tailwind CSS** via CDN (with inline config)
- **Alpine.js** for toggle and modals
- **HTMX** included for future interactivity
- **Gunicorn** for production (Procfile: `web: gunicorn app:app`)
- **No database** — `data.json` is the single source of truth

## Deployment

- Hosted on Heroku
- GitHub Actions workflow on push to main:
  1. Test job: install flask + pytest, run `pytest test_app.py -v`
  2. Deploy job (depends on test): set `SOURCE_VERSION` config var via Heroku API, git push to Heroku remote
- Requires `HEROKU_API_KEY` secret in GitHub repo settings

## Tests

### Unit tests

Pytest suite (`test_app.py`) covering:
- Homepage returns 200 and contains "Arc Raiders"
- Detail page returns 200 for valid ARC
- Invalid ARC slug returns 404
- `data.json` has required top-level keys and correct ARC count
- Every ARC in `arcs` array has `strategies` key (list) and no legacy `damage` key
- Every strategy has `best`, `items` (non-empty), and valid item structure (type in weapon/explosive, name, units)
- At most one strategy per ARC is marked `best: true`

### E2E smoke tests

Browser-based tests (`tests/test_e2e_otel.py`) using the [smokeshow](https://github.com/gotoplanb/smokeshow) library for Playwright + OpenTelemetry instrumentation. Three test cases verify homepage loading, detail page navigation, and detail page content. Each run produces a single trace with a three-level span hierarchy (suite, test case, action) exported to a local OTEL collector. See [TESTING.md](TESTING.md) for full details.

## Design Principles

1. **Data-driven** — All content comes from `data.json`. No hardcoded ARC data in templates or code.
2. **Community-first** — Footer links to GitHub issues for contributions. Verification dates build trust.
3. **Mobile-friendly** — Responsive layout, touch-friendly modals, hidden type labels on small screens.
4. **Minimal dependencies** — Flask + gunicorn only. Frontend is CDN-only with no build step.
5. **Transparent** — Commit SHA in footer so users know which version they're seeing.
