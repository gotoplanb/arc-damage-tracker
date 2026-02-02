# Testing

## Overview

The arc-damage-tracker has two layers of testing:

- **Unit tests** (`tests/test_app.py`) — Standard pytest tests for Flask routes and data loading. No external dependencies.
- **E2E smoke tests** (`tests/test_e2e_otel.py`) — Playwright browser tests instrumented with [smokeshow](https://github.com/gotoplanb/smokeshow), producing traces visible in Grafana/Jaeger.

## E2E Smoke Tests

The E2E suite uses headless Chromium via Playwright to exercise the app as a real user would. Instrumentation is provided by the [smokeshow](https://github.com/gotoplanb/smokeshow) library, which wraps Playwright actions with OpenTelemetry spans. Each suite run produces a single trace capturing the full test session.

### Running

```bash
# Start the app (requires venv setup)
bash scripts/run-otel.sh

# In another terminal, run the E2E suite
source .venv/bin/activate
python tests/test_e2e_otel.py
```

The suite expects the app on `localhost:8080` and exports traces to Alloy on `localhost:4317`.

### Test Cases

| ID | Name | What it tests |
|----|------|---------------|
| TC-ARC-001 | home-page-loads | Home page renders, title is correct, all threat level sections are visible |
| TC-ARC-002 | arc-detail-navigation | Clicking an arc link from the home page navigates to its detail page |
| TC-ARC-003 | arc-detail-content | Arc detail page shows the arc name, threat level, and strategies heading |

### Trace Structure

Each suite run produces one trace with a three-level span hierarchy, following the [smokeshow spec](../smokeshow/SPEC.md):

```
suite("arc-damage-tracker-smoke")                    <- root span
  test("home-page-loads")                            <- test case span
    navigate(http://localhost:8080/)                  <- action span
    assert_visible(h1)                               <- action span
    assert_text(h1)                                  <- action span
    click(label:has(input))                          <- action span
    assert_visible(h2:has-text('Extreme'))            <- action span
    ...
  test("arc-detail-navigation")
    navigate(...)
    toggle_filter(dataOnly=false)
    click(a[href='/arc/matriarch'])
    assert_visible(h2)
    assert_url
  test("arc-detail-content")
    navigate(.../arc/matriarch)
    assert_visible(h2)
    assert_text(h2)
    ...
```

### Span Attributes

#### Suite span

Standard test metadata plus VCS info:

- `test.suite.name`, `test.suite.id`, `test.suite.result`
- `test.suite.total_tests`, `test.suite.passed`, `test.suite.failed`
- `test.target.base_url`, `test.target.environment`
- `test.browser.name`, `test.browser.headless`, `test.viewport.*`
- `vcs.commit.sha` — Git commit SHA at time of run
- `vcs.branch` — Git branch name

#### Test case spans

Standard test case metadata:

- `test.case.name`, `test.case.id`, `test.case.result`
- `test.case.tags`, `test.case.description`
- `test.case.failure_reason` — Error message (on failure only)
- `arc.failure_url` — The page URL where the failure occurred (on failure only). Use this to jump directly to the app state that caused the test to fail.

#### Action spans

Every Playwright action (navigate, click, assert, etc.) gets its own span:

- `test.action.type` — `navigate`, `click`, `assert_visible`, `assert_text`, `assert_url`, etc.
- `test.action.selector` — The CSS/Playwright selector used
- `test.action.page_url` — Current page URL when the action ran
- `test.action.result` — `success` or `failed`

#### Navigation performance timing

Navigate action spans include browser performance metrics:

- `test.navigation.response_status` — HTTP status code
- `test.navigation.dom_content_loaded_ms` — Time to DOMContentLoaded
- `test.navigation.dom_interactive_ms` — Time to DOM interactive
- `test.navigation.load_event_ms` — Time to load event
- `test.navigation.transfer_size_bytes` — Page transfer size

### Domain-Specific Metadata (`arc.*`)

Custom attributes prefixed with `arc.` capture business context from the pages under test:

| Attribute | Test Case | Description |
|-----------|-----------|-------------|
| `arc.home.total_arc_links` | TC-ARC-001 | Number of arc links on the home page |
| `arc.home.visible_threat_sections` | TC-ARC-001 | Number of visible threat level sections |
| `arc.navigated_to.slug` | TC-ARC-002 | URL slug of the arc navigated to |
| `arc.navigated_to.name` | TC-ARC-002 | Display name of the arc navigated to |
| `arc.detail.name` | TC-ARC-003 | Arc name from the detail page heading |
| `arc.detail.page_title` | TC-ARC-003 | Full page title |
| `arc.detail.threat_level` | TC-ARC-003 | Arc's threat level (Extreme, Critical, etc.) |
| `arc.detail.strategy_count` | TC-ARC-003 | Number of strategies found on the page |
| `arc.failure_url` | Any (on failure) | Page URL at the moment of failure |

These attributes let you track content changes over time — for example, alerting if `arc.detail.strategy_count` drops to 0 for a known arc, or if `arc.home.total_arc_links` changes unexpectedly between runs.

### Viewing Traces

Traces are exported to the local Alloy collector and forwarded to Jaeger.

- **Local Jaeger**: Open Grafana at `http://localhost:3000`, go to Explore, select the Jaeger datasource, and search for service `arc-damage-tracker-e2e`.
- **Grafana Cloud**: Traces flow through Alloy to Tempo. Search for service `arc-damage-tracker-e2e` in the Tempo datasource.

The service name `arc-damage-tracker-e2e` distinguishes test telemetry from the app's own telemetry (`arc-damage-tracker`).

#### Example Trace

![E2E smoke test trace in Jaeger](docs/trace-screenshot.png)

A single suite run showing the three-level span hierarchy: the root `suite(arc-damage-tracker-smoke)` span contains three test case spans (`home-page-loads`, `arc-detail-navigation`, `arc-detail-content`), each containing individual action spans (navigate, assert, click, etc.).
