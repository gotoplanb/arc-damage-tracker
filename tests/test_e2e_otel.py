"""
End-to-end tests for arc-damage-tracker with OpenTelemetry instrumentation.

Follows the smokeshow spec: one trace = one test suite run.
Three-level span hierarchy: suite → test case → action.
"""

import asyncio
import subprocess
import uuid
from datetime import datetime, timezone

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import StatusCode
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:8080"
OTLP_ENDPOINT = "http://localhost:4317"
SERVICE_NAME = "arc-damage-tracker-e2e"
SUITE_NAME = "arc-damage-tracker-smoke"

# --- OTEL Setup ---

resource = Resource.create({
    "service.name": SERVICE_NAME,
    "telemetry.sdk.name": "smokeshow",
    "deployment.environment": "development",
})

provider = TracerProvider(resource=resource)
exporter = OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("smokeshow", "0.1.0")


# --- VCS Helpers ---

def get_git_info():
    """Get git commit SHA and branch for VCS metadata."""
    info = {}
    try:
        info["vcs.commit.sha"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        pass
    try:
        info["vcs.branch"] = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        pass
    return info


# --- Helpers ---

def action_span(parent_ctx, action_type, selector=None, **extra_attrs):
    """Create an action-level span (grandchild)."""
    name = f"{action_type}({selector})" if selector else action_type
    attrs = {"test.action.type": action_type}
    if selector:
        attrs["test.action.selector"] = selector
    attrs.update(extra_attrs)
    return tracer.start_as_current_span(name, context=parent_ctx, attributes=attrs)


async def traced_navigate(page, url, parent_ctx):
    with action_span(parent_ctx, "navigate", target_url=url, **{"test.action.target_url": url}) as span:
        span.set_attribute("test.action.page_url", page.url)
        response = await page.goto(url, wait_until="domcontentloaded")
        if response:
            span.set_attribute("test.navigation.response_status", response.status)
        # Capture navigation performance timing from the browser
        try:
            timing = await page.evaluate("""() => {
                const entries = performance.getEntriesByType('navigation');
                if (entries.length === 0) return null;
                const nav = entries[0];
                return {
                    domContentLoaded: nav.domContentLoadedEventEnd - nav.startTime,
                    loadEvent: nav.loadEventEnd - nav.startTime,
                    transferSize: nav.transferSize || 0,
                    domInteractive: nav.domInteractive - nav.startTime,
                };
            }""")
            if timing:
                span.set_attribute("test.navigation.dom_content_loaded_ms", timing["domContentLoaded"])
                span.set_attribute("test.navigation.load_event_ms", timing["loadEvent"])
                span.set_attribute("test.navigation.transfer_size_bytes", timing["transferSize"])
                span.set_attribute("test.navigation.dom_interactive_ms", timing["domInteractive"])
        except Exception:
            pass  # navigation timing not available (e.g. same-page navigation)
        span.set_status(StatusCode.OK)


async def traced_click(page, selector, parent_ctx):
    with action_span(parent_ctx, "click", selector) as span:
        span.set_attribute("test.action.page_url", page.url)
        await page.click(selector)
        span.set_status(StatusCode.OK)


async def traced_assert_visible(page, selector, parent_ctx):
    with action_span(parent_ctx, "assert_visible", selector) as span:
        span.set_attribute("test.action.page_url", page.url)
        await page.wait_for_selector(selector, state="visible", timeout=5000)
        span.set_attribute("test.action.result", "success")
        span.set_status(StatusCode.OK)


async def traced_assert_text(page, selector, expected, parent_ctx):
    with action_span(parent_ctx, "assert_text", selector) as span:
        span.set_attribute("test.action.page_url", page.url)
        element = await page.wait_for_selector(selector, state="visible", timeout=5000)
        text = await element.text_content()
        if expected.lower() in text.lower():
            span.set_attribute("test.action.result", "success")
            span.set_status(StatusCode.OK)
        else:
            span.set_attribute("test.action.result", "failed")
            span.set_status(StatusCode.ERROR, f"Expected '{expected}' in '{text}'")
            raise AssertionError(f"Expected '{expected}' in '{text}'")


async def traced_assert_count(page, selector, expected_count, parent_ctx):
    with action_span(parent_ctx, "assert_count", selector) as span:
        span.set_attribute("test.action.page_url", page.url)
        elements = await page.query_selector_all(selector)
        actual = len(elements)
        span.set_attribute("test.action.result", "success" if actual == expected_count else "failed")
        if actual == expected_count:
            span.set_status(StatusCode.OK)
        else:
            span.set_status(StatusCode.ERROR, f"Expected {expected_count} elements, got {actual}")
            raise AssertionError(f"Expected {expected_count} elements matching '{selector}', got {actual}")


# --- Test Cases ---

async def test_home_page(page, suite_ctx):
    """TC-ARC-001: Verify home page loads with threat level groups."""
    with tracer.start_as_current_span(
        'test("home-page-loads")',
        context=suite_ctx,
        attributes={
            "test.case.name": "home-page-loads",
            "test.case.id": "TC-ARC-001",
            "test.case.tags": "smoke,home",
            "test.case.description": "Verify home page loads with all threat level groups",
        },
    ) as case_span:
        ctx = trace.set_span_in_context(case_span)
        try:
            await traced_navigate(page, BASE_URL, ctx)
            await traced_assert_visible(page, "h1", ctx)
            await traced_assert_text(page, "h1", "Arc Raiders", ctx)
            # Toggle "Show only verified ARCs" off to reveal all sections
            with action_span(ctx, "click", "label:has(input)") as span:
                span.set_attribute("test.action.page_url", page.url)
                await page.evaluate("document.querySelector('[x-data]')._x_dataStack[0].dataOnly = false")
                await page.wait_for_timeout(300)
                span.set_status(StatusCode.OK)
            # Verify threat level headings are now visible
            for level in ["Extreme", "Critical", "High"]:
                await traced_assert_visible(page, f"h2:has-text('{level}')", ctx)
            # Domain metadata: count arcs and threat levels visible on the page
            with action_span(ctx, "extract_metadata") as span:
                arc_count = await page.evaluate("document.querySelectorAll('a[href*=\"/arc/\"]').length")
                threat_sections = await page.evaluate("""
                    Array.from(document.querySelectorAll('h2')).filter(
                        el => getComputedStyle(el.closest('section') || el).display !== 'none'
                    ).length
                """)
                case_span.set_attribute("arc.home.total_arc_links", arc_count)
                case_span.set_attribute("arc.home.visible_threat_sections", threat_sections)
                span.set_attribute("arc.home.total_arc_links", arc_count)
                span.set_status(StatusCode.OK)
            case_span.set_attribute("test.case.result", "passed")
            case_span.set_status(StatusCode.OK)
        except Exception as e:
            case_span.set_attribute("test.case.result", "failed")
            case_span.set_attribute("test.case.failure_reason", str(e))
            case_span.set_attribute("arc.failure_url", page.url)
            case_span.set_status(StatusCode.ERROR, str(e))
            case_span.record_exception(e)
            raise
    return "passed"


async def test_arc_detail_navigation(page, suite_ctx):
    """TC-ARC-002: Verify clicking an arc navigates to its detail page."""
    with tracer.start_as_current_span(
        'test("arc-detail-navigation")',
        context=suite_ctx,
        attributes={
            "test.case.name": "arc-detail-navigation",
            "test.case.id": "TC-ARC-002",
            "test.case.tags": "smoke,navigation",
            "test.case.description": "Verify clicking an arc name navigates to its detail page",
        },
    ) as case_span:
        ctx = trace.set_span_in_context(case_span)
        try:
            await traced_navigate(page, BASE_URL, ctx)
            # Toggle dataOnly off so all arc links are visible
            with action_span(ctx, "toggle_filter", "dataOnly=false") as span:
                await page.wait_for_load_state("networkidle")
                await page.evaluate("document.querySelector('[x-data]')._x_dataStack[0].dataOnly = false")
                await page.wait_for_timeout(300)
                span.set_status(StatusCode.OK)
            # Click the matriarch arc link
            await traced_click(page, "a[href='/arc/matriarch']", ctx)
            # Verify we're on a detail page
            await traced_assert_visible(page, "h2", ctx)
            # Verify the URL changed to an arc detail page
            with action_span(ctx, "assert_url") as span:
                span.set_attribute("test.action.page_url", page.url)
                assert "/arc/" in page.url, f"Expected /arc/ in URL, got {page.url}"
                span.set_attribute("test.action.result", "success")
                span.set_status(StatusCode.OK)
            # Domain metadata: record which arc we navigated to
            arc_slug = page.url.split("/arc/")[-1].rstrip("/")
            arc_name = await page.evaluate("document.querySelector('h2')?.textContent?.trim() || ''")
            case_span.set_attribute("arc.navigated_to.slug", arc_slug)
            case_span.set_attribute("arc.navigated_to.name", arc_name)
            case_span.set_attribute("test.case.result", "passed")
            case_span.set_status(StatusCode.OK)
        except Exception as e:
            case_span.set_attribute("test.case.result", "failed")
            case_span.set_attribute("test.case.failure_reason", str(e))
            case_span.set_attribute("arc.failure_url", page.url)
            case_span.set_status(StatusCode.ERROR, str(e))
            case_span.record_exception(e)
            raise
    return "passed"


async def test_arc_detail_content(page, suite_ctx):
    """TC-ARC-003: Verify arc detail page shows strategies and items."""
    with tracer.start_as_current_span(
        'test("arc-detail-content")',
        context=suite_ctx,
        attributes={
            "test.case.name": "arc-detail-content",
            "test.case.id": "TC-ARC-003",
            "test.case.tags": "smoke,detail,content",
            "test.case.description": "Verify arc detail page displays strategy information",
        },
    ) as case_span:
        ctx = trace.set_span_in_context(case_span)
        try:
            # Navigate directly to matriarch (known to have data)
            await traced_navigate(page, f"{BASE_URL}/arc/matriarch", ctx)
            await traced_assert_visible(page, "h2", ctx)
            await traced_assert_text(page, "h2", "Matriarch", ctx)
            # Verify strategy heading is present
            await traced_assert_visible(page, "h3", ctx)
            await traced_assert_text(page, "h3", "Strategies", ctx)
            # Domain metadata: extract arc details from the page
            with action_span(ctx, "extract_metadata") as span:
                arc_data = await page.evaluate("""() => {
                    const name = document.querySelector('h2')?.textContent?.trim() || '';
                    const title = document.title || '';
                    const strategies = document.querySelectorAll('table tbody tr, .strategy-card, div[class*="strategy"]');
                    const threatMatch = document.querySelector('span[class*="text-extreme"], span[class*="text-critical"], span[class*="text-high"], span[class*="text-moderate"], span[class*="text-low"]');
                    const threatLevel = threatMatch ? threatMatch.textContent.trim() : '';
                    return { name, title, strategyCount: strategies.length, threatLevel };
                }""")
                case_span.set_attribute("arc.detail.name", arc_data["name"])
                case_span.set_attribute("arc.detail.page_title", arc_data["title"])
                case_span.set_attribute("arc.detail.strategy_count", arc_data["strategyCount"])
                if arc_data["threatLevel"]:
                    case_span.set_attribute("arc.detail.threat_level", arc_data["threatLevel"])
                span.set_status(StatusCode.OK)
            # Navigate back to home
            await traced_navigate(page, BASE_URL, ctx)
            await traced_assert_visible(page, "h1", ctx)
            case_span.set_attribute("test.case.result", "passed")
            case_span.set_status(StatusCode.OK)
        except Exception as e:
            case_span.set_attribute("test.case.result", "failed")
            case_span.set_attribute("test.case.failure_reason", str(e))
            case_span.set_attribute("arc.failure_url", page.url)
            case_span.set_status(StatusCode.ERROR, str(e))
            case_span.record_exception(e)
            raise
    return "passed"


# --- Suite Runner ---

async def run_suite():
    suite_id = str(uuid.uuid4())
    passed = 0
    failed = 0
    results = {}

    suite_attrs = {
        "test.suite.name": SUITE_NAME,
        "test.suite.id": suite_id,
        "test.run.trigger": "manual",
        "test.run.timestamp": datetime.now(timezone.utc).isoformat(),
        "test.target.base_url": BASE_URL,
        "test.target.environment": "development",
        "test.browser.name": "chromium",
        "test.browser.headless": True,
        "test.viewport.width": 1280,
        "test.viewport.height": 720,
    }
    suite_attrs.update(get_git_info())

    with tracer.start_as_current_span(
        f"suite({SUITE_NAME})",
        attributes=suite_attrs,
    ) as suite_span:
        suite_ctx = trace.set_span_in_context(suite_span)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1280, "height": 720})
            page = await context.new_page()

            test_cases = [
                ("home-page-loads", test_home_page),
                ("arc-detail-navigation", test_arc_detail_navigation),
                ("arc-detail-content", test_arc_detail_content),
            ]

            for name, test_fn in test_cases:
                try:
                    result = await test_fn(page, suite_ctx)
                    results[name] = result
                    passed += 1
                    print(f"  PASS: {name}")
                except Exception as e:
                    results[name] = "failed"
                    failed += 1
                    print(f"  FAIL: {name} — {e}")

            await browser.close()

        suite_span.set_attribute("test.suite.total_tests", len(test_cases))
        suite_span.set_attribute("test.suite.passed", passed)
        suite_span.set_attribute("test.suite.failed", failed)
        suite_span.set_attribute(
            "test.suite.result",
            "passed" if failed == 0 else ("failed" if passed == 0 else "partial"),
        )

    # Force flush to ensure all spans are exported
    provider.force_flush()

    print(f"\nSuite: {passed} passed, {failed} failed, {len(test_cases)} total")
    print(f"Trace ID: {suite_id}")
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_suite())
    exit(0 if success else 1)
