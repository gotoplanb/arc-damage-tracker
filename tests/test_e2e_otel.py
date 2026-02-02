"""
End-to-end tests for arc-damage-tracker with OpenTelemetry instrumentation.

Uses the smokeshow library for Playwright + OTEL instrumentation.
Three-level span hierarchy: suite -> test case -> action.
"""

import asyncio
from opentelemetry.trace import StatusCode
from smokeshow import InstrumentedBrowser

BASE_URL = "http://localhost:8080"


async def test_home_page(test):
    """TC-ARC-001: Verify home page loads with threat level groups."""
    await test.navigate(BASE_URL)
    await test.assert_visible("h1")
    await test.assert_text("h1", "Arc Raiders")

    # Toggle "Show only verified ARCs" off to reveal all sections
    with test.action_span("click", "label:has(input)") as span:
        span.set_attribute("test.action.page_url", test.page.url)
        await test.page.evaluate(
            "document.querySelector('[x-data]')._x_dataStack[0].dataOnly = false"
        )
        await test.page.wait_for_timeout(300)
        span.set_status(StatusCode.OK)

    # Verify threat level headings are now visible
    for level in ["Extreme", "Critical", "High"]:
        await test.assert_visible(f"h2:has-text('{level}')")

    # Domain metadata: count arcs and threat levels visible on the page
    with test.action_span("extract_metadata") as span:
        arc_count = await test.page.evaluate(
            "document.querySelectorAll('a[href*=\"/arc/\"]').length"
        )
        threat_sections = await test.page.evaluate("""
            Array.from(document.querySelectorAll('h2')).filter(
                el => getComputedStyle(el.closest('section') || el).display !== 'none'
            ).length
        """)
        test.set_attribute("arc.home.total_arc_links", arc_count)
        test.set_attribute("arc.home.visible_threat_sections", threat_sections)
        span.set_attribute("arc.home.total_arc_links", arc_count)
        span.set_status(StatusCode.OK)


async def test_arc_detail_navigation(test):
    """TC-ARC-002: Verify clicking an arc navigates to its detail page."""
    await test.navigate(BASE_URL)

    # Toggle dataOnly off so all arc links are visible
    with test.action_span("toggle_filter", "dataOnly=false") as span:
        await test.page.wait_for_load_state("networkidle")
        await test.page.evaluate(
            "document.querySelector('[x-data]')._x_dataStack[0].dataOnly = false"
        )
        await test.page.wait_for_timeout(300)
        span.set_status(StatusCode.OK)

    # Click the matriarch arc link
    await test.click("a[href='/arc/matriarch']")

    # Verify we're on a detail page
    await test.assert_visible("h2")

    # Verify the URL changed to an arc detail page
    with test.action_span("assert_url") as span:
        span.set_attribute("test.action.page_url", test.page.url)
        assert "/arc/" in test.page.url, f"Expected /arc/ in URL, got {test.page.url}"
        span.set_attribute("test.action.result", "success")
        span.set_status(StatusCode.OK)

    # Domain metadata: record which arc we navigated to
    arc_slug = test.page.url.split("/arc/")[-1].rstrip("/")
    arc_name = await test.page.evaluate(
        "document.querySelector('h2')?.textContent?.trim() || ''"
    )
    test.set_attribute("arc.navigated_to.slug", arc_slug)
    test.set_attribute("arc.navigated_to.name", arc_name)


async def test_arc_detail_content(test):
    """TC-ARC-003: Verify arc detail page shows strategies and items."""
    # Navigate directly to matriarch (known to have data)
    await test.navigate(f"{BASE_URL}/arc/matriarch")
    await test.assert_visible("h2")
    await test.assert_text("h2", "Matriarch")

    # Verify strategy heading is present
    await test.assert_visible("h3")
    await test.assert_text("h3", "Strategies")

    # Domain metadata: extract arc details from the page
    with test.action_span("extract_metadata") as span:
        arc_data = await test.page.evaluate("""() => {
            const name = document.querySelector('h2')?.textContent?.trim() || '';
            const title = document.title || '';
            const strategies = document.querySelectorAll('table tbody tr, .strategy-card, div[class*="strategy"]');
            const threatMatch = document.querySelector('span[class*="text-extreme"], span[class*="text-critical"], span[class*="text-high"], span[class*="text-moderate"], span[class*="text-low"]');
            const threatLevel = threatMatch ? threatMatch.textContent.trim() : '';
            return { name, title, strategyCount: strategies.length, threatLevel };
        }""")
        test.set_attribute("arc.detail.name", arc_data["name"])
        test.set_attribute("arc.detail.page_title", arc_data["title"])
        test.set_attribute("arc.detail.strategy_count", arc_data["strategyCount"])
        if arc_data["threatLevel"]:
            test.set_attribute("arc.detail.threat_level", arc_data["threatLevel"])
        span.set_status(StatusCode.OK)

    # Navigate back to home
    await test.navigate(BASE_URL)
    await test.assert_visible("h1")


async def run_suite():
    async with InstrumentedBrowser(
        service_name="arc-damage-tracker-e2e",
        suite_name="arc-damage-tracker-smoke",
        base_url=BASE_URL,
        otlp_endpoint="http://localhost:4317",
    ) as browser:
        tests = [
            ("home-page-loads", "TC-ARC-001", "smoke,home", "Verify home page loads with all threat level groups", test_home_page),
            ("arc-detail-navigation", "TC-ARC-002", "smoke,navigation", "Verify clicking an arc name navigates to its detail page", test_arc_detail_navigation),
            ("arc-detail-content", "TC-ARC-003", "smoke,detail,content", "Verify arc detail page displays strategy information", test_arc_detail_content),
        ]

        for name, case_id, tags, desc, fn in tests:
            try:
                async with browser.test_case(name=name, case_id=case_id, tags=tags, description=desc) as test:
                    await fn(test)
                print(f"  PASS: {name}")
            except Exception as e:
                print(f"  FAIL: {name} — {e}")

    print(f"\nSuite: {browser.passed} passed, {browser.failed} failed, {browser.total} total")
    return browser.failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_suite())
    exit(0 if success else 1)
