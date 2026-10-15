"""One scoped Playwright browser adapter using a controlled local fixture."""
from scenario import brief_html
from runtime import artifact


def read_brief(data, workspace, control, *, headless=False):
    from playwright.sync_api import sync_playwright
    control.check()
    path = workspace / "brief.html"
    path.write_text(brief_html(data), encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless, timeout=control.timeout_ms())
        try:
            context = browser.new_context(accept_downloads=False, service_workers="block")
            # The fixture is fulfilled locally. All other page requests are denied.
            url = "https://synthetic.invalid/brief"
            def route_request(route):
                if route.request.url == url and route.request.is_navigation_request():
                    route.fulfill(status=200, content_type="text/html", body=path.read_text(encoding="utf-8"))
                else:
                    control.audit.emit("network_request_blocked", backend="playwright")
                    route.abort()
            context.route("**/*", route_request)
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=control.timeout_ms())
            heading = page.locator("h1").inner_text(timeout=control.timeout_ms())
            if heading != data["title"]:
                raise RuntimeError("Brief title verification failed")
            observed = page.locator("table tr").count() - 1
            if observed != len(data["items"]):
                raise RuntimeError("Brief row verification failed")
            for _ in range(3):
                control.check()
                page.mouse.wheel(0, control.rng.randint(120, 320))  # Playwright uses pixels.
                control.pause()
            page.get_by_role("link", name="Read instructions").click(timeout=control.timeout_ms())
            if page.locator("#instructions h2").inner_text(timeout=control.timeout_ms()) != "Instructions":
                raise RuntimeError("Instructions verification failed")
            control.audit.emit("brief_verified", backend="playwright", rows=observed,
                               source="local_fixture", artifact=artifact(path))
        finally:
            browser.close()
            control.audit.emit("browser_closed", backend="playwright")
    control.check()
    return {"title": heading, "rows": observed}
