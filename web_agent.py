import pyautogui
import random
import time
import re
import math
from playwright.sync_api import sync_playwright

# Teammate's helper (keep stealth_mouse.py in the same folder as this script)
from stealth_mouse import (
    generate_bezier_path,
    distance_between,
    validate_path,
    move_cursor_to,
)

url_list = [
    "https://www.coinmarketcap.com",
    "https://www.coinbase.com",
    "https://coingecko.com",
]

# Direct Bitcoin pages, used only if the Bitcoin link can't be found by clicking
BITCOIN_URLS = {
    "coinmarketcap": "https://coinmarketcap.com/currencies/bitcoin/",
    "coinbase": "https://www.coinbase.com/price/bitcoin",
    "coingecko": "https://www.coingecko.com/en/coins/bitcoin",
}

# Matches hrefs that end with /bitcoin (and not /bitcoin-cash, etc.)
BITCOIN_HREF = re.compile(r"/bitcoin/?(?:[?#].*)?$", re.I)

SCROLL_DOWN_SECONDS = 30
SCROLL_UP_SECONDS = 5


def short_pause():
    time.sleep(random.uniform(0.3, 0.6))


def reading_pause():
    time.sleep(random.uniform(2, 7))


def press_key():
    time.sleep(random.uniform(0.08, 0.8))
    pyautogui.press("enter")

def navigate(url):
    print(f"Navigating to {url}")

    pyautogui.hotkey("ctrl", "l")
    short_pause()

    pyautogui.write(
        url,
        interval=random.uniform(0.03, 0.10)
    )

    short_pause()
    press_key()

    reading_pause()

    print("Navigation completed")

def browse_page():
    scroll_count = random.randint(1,3)
    print(f"Scroll count: {scroll_count}")

    for i in range(scroll_count):
        scroll_amount = random.randint(100, 500)
        print(f"Scroll amount: {scroll_amount}")

        # Scroll down
        wander_mouse()
        pyautogui.scroll(-scroll_amount)
        reading_pause()

        # 15% chance of scrolling upward
        if random.random() < 0.15:
            upward_amount = random.randint(50, 100)
            pyautogui.scroll(upward_amount)

            short_pause()
            time.sleep(random.uniform(0.5, 1.2))


def close_popups_news(page, timeout=10000):
    dialog = page.locator('[role="dialog"], [aria-modal="true"]').first
    try:
        dialog.wait_for(state="visible", timeout=timeout)   # wait for the banner
    except Exception:
        print("No popup appeared.")
        return

    # Click inside the banner (on its container, not a button) to give the page focus
    box = dialog.bounding_box()
    page.mouse.move(box["x"] + 5, box["y"] + 5, steps=random.randint(10, 20))
    page.mouse.click(box["x"] + 5, box["y"] + 5)
    short_pause()

    page.keyboard.press("Escape")
    print("Pressed Escape")


# ---------------------------------------------------------------------------
# Mouse movement (real cursor, curved paths)
# ---------------------------------------------------------------------------

def move_mouse_human(x, y):
    """Move the real cursor to screen position (x, y) along a curved path."""
    screen_width, screen_height = pyautogui.size()

    # Stay away from the screen corners (pyautogui's fail-safe triggers there)
    x = min(max(int(x), 2), screen_width - 3)
    y = min(max(int(y), 2), screen_height - 3)

    current = pyautogui.position()
    start, end = (current.x, current.y), (x, y)
    distance = distance_between(start, end)

    # Too short for a curve: use the plain eased move from the helper
    if distance < 30:
        move_cursor_to(x, y, duration=random.uniform(0.1, 0.3))
        return

    # Two control points, pushed sideways off the straight line
    dx, dy = end[0] - start[0], end[1] - start[1]
    normal = (-dy / distance, dx / distance)
    offset1 = random.uniform(-0.25, 0.25) * distance
    offset2 = random.uniform(-0.25, 0.25) * distance

    control1 = (
        start[0] + dx * 0.3 + normal[0] * offset1,
        start[1] + dy * 0.3 + normal[1] * offset1,
    )
    control2 = (
        start[0] + dx * 0.7 + normal[0] * offset2,
        start[1] + dy * 0.7 + normal[1] * offset2,
    )

    steps = min(max(int(distance / 12), 20), 80)
    path = generate_bezier_path(start, control1, control2, end, steps=steps)
    validate_path(path, start, end)

    duration = (0.3 + distance / 2000) * random.uniform(0.8, 1.3)
    per_step = duration / steps

    for i, (px, py) in enumerate(path):
        px = min(max(px, 2), screen_width - 3)
        py = min(max(py, 2), screen_height - 3)

        # _pause=False skips pyautogui's default 0.1 s delay after each call
        pyautogui.moveTo(px, py, _pause=False)

        # Slower at both ends of the movement, faster in the middle
        time.sleep(per_step * (1.6 - math.sin(math.pi * i / steps)))


def wander_mouse():
    """Drift the cursor a short way inside the page area, like a reader
    moving the mouse while scrolling."""
    screen_width, screen_height = pyautogui.size()
    current = pyautogui.position()

    x = current.x + random.randint(-150, 150)
    y = current.y + random.randint(-100, 100)

    # Stay inside the page area so the scroll wheel still acts on the page
    x = min(max(x, screen_width * 0.15), screen_width * 0.85)
    y = min(max(y, screen_height * 0.25), screen_height * 0.85)

    move_mouse_human(x, y)


def page_to_screen(page, x, y):
    """Convert a position in the web page (what Playwright reports) into a
    screen position (what pyautogui uses). This is an estimate based on the
    browser window's size and position."""
    window = page.evaluate("""() => ({
        left: window.screenX + (window.outerWidth - window.innerWidth) / 2,
        top: window.screenY + (window.outerHeight - window.innerHeight)
             - (window.outerWidth - window.innerWidth) / 2,
        screenWidth: window.screen.width,
    })""")

    # Handles display scaling (pyautogui pixels vs. browser pixels)
    scale = pyautogui.size().width / window["screenWidth"]

    return (window["left"] + x) * scale, (window["top"] + y) * scale


# ---------------------------------------------------------------------------
# Scrolling
# ---------------------------------------------------------------------------

def move_cursor_to_page():
    """pyautogui's wheel acts on the window under the OS cursor, so park the
    cursor in the middle of the (maximized) browser window first."""
    width, height = pyautogui.size()
    move_mouse_human(
        width / 2 + random.randint(-100, 100),
        height / 2 + random.randint(-50, 50),
    )


def scroll_down_for(seconds):
    """Keep scrolling down in random steps for the given number of seconds."""
    print(f"Scrolling down for {seconds} seconds...")
    end_time = time.monotonic() + seconds

    while time.monotonic() < end_time:
        # Move the mouse a little now and then while reading
        if random.random() < 0.5:
            wander_mouse()

        pyautogui.scroll(-random.randint(100, 400))
        time.sleep(random.uniform(0.5, 2.0))


def scroll_to_bitcoin(page, seconds):
    """Scroll back up (within `seconds`) and stop as soon as the Bitcoin link
    is on screen, wherever it sits on the page. Then wait 2-3 s before the
    link is clicked."""
    print(f"Scrolling back up to the Bitcoin link within {seconds} seconds...")
    end_time = time.monotonic() + seconds

    # Finds the first Bitcoin link (ignoring menus in <header>/<nav>) and
    # reports where its top edge is relative to the visible window.
    find_link_js = """(pattern) => {
        const regex = new RegExp(pattern, 'i');
        for (const a of document.querySelectorAll('a[href*="bitcoin" i]')) {
            if (!regex.test(a.getAttribute('href') || '')) continue;
            if (a.closest('header, nav')) continue;
            const r = a.getBoundingClientRect();
            if (r.width === 0 || r.height === 0) continue;
            if (r.left < 0 || r.right > window.innerWidth) continue;
            return {top: r.top, view: window.innerHeight};
        }
        return null;
    }"""

    while time.monotonic() < end_time:
        link = page.evaluate(find_link_js, BITCOIN_HREF.pattern)
        at_top = page.evaluate("window.scrollY") <= 0

        if link is None:
            # Link not found yet: keep scrolling up until the top
            if at_top:
                break
            pyautogui.scroll(random.randint(500, 900))
        else:
            top, view = link["top"], link["view"]

            # Link is comfortably on screen (or the page can't go higher)
            if 100 <= top <= view - 150 or (at_top and top >= 0):
                break

            if top < 100:
                # Link is above: scroll up fast while far away, slowly when close
                far_away = top < -view
                pyautogui.scroll(
                    random.randint(500, 900) if far_away else random.randint(150, 300)
                )
            else:
                # Overshot: link is below the window, scroll down a little
                pyautogui.scroll(-random.randint(150, 300))

        time.sleep(random.uniform(0.3, 0.5))

        # Occasionally move the mouse while scrolling back up
        if random.random() < 0.25:
            wander_mouse()

    # Stay on the link for a moment before opening it
    time.sleep(random.uniform(2, 3))


# ---------------------------------------------------------------------------
# Clicking
# ---------------------------------------------------------------------------

def move_and_click(page, x, y):
    """Move the real mouse cursor to (x, y) along a curved path, then click.
    (x, y) is a position in the page, as reported by Playwright."""
    screen_x, screen_y = page_to_screen(page, x, y)
    move_mouse_human(screen_x, screen_y)
    short_pause()
    pyautogui.click()


def wait_for_navigation(page, original_url, timeout=10000):
    """Return True once the URL changes and the new page has loaded."""
    try:
        page.wait_for_url(lambda url: str(url) != original_url, timeout=timeout)
        page.wait_for_load_state("domcontentloaded", timeout=timeout)
        return True
    except Exception:
        return False


def click_bitcoin(page):
    """Click the Bitcoin link on a coin market page. Returns True on success."""
    anchors = page.locator('a[href*="bitcoin" i]')
    view_height = page.evaluate("window.innerHeight")

    # First pass: only links already on screen (where the scroll stopped).
    # Second pass: any visible link, scrolled into view if necessary.
    for on_screen_only in (True, False):
        for i in range(min(anchors.count(), 50)):
            anchor = anchors.nth(i)

            try:
                href = anchor.get_attribute("href") or ""
                if not BITCOIN_HREF.search(href):
                    continue
                if not anchor.is_visible():
                    continue
                if anchor.evaluate("el => !!el.closest('header, nav')"):
                    continue

                box = anchor.bounding_box()
                if box is None:
                    continue

                on_screen = box["y"] >= 0 and box["y"] + box["height"] <= view_height
                if on_screen_only and not on_screen:
                    continue

                if not on_screen:
                    anchor.scroll_into_view_if_needed(timeout=2000)
                    box = anchor.bounding_box()
                    if box is None:
                        continue
            except Exception:
                continue

            print(f"Clicking Bitcoin link: {href}")
            original_url = page.url

            # Aim at a random spot inside the link rather than its exact centre
            click_x = box["x"] + box["width"] * random.uniform(0.35, 0.65)
            click_y = box["y"] + box["height"] * random.uniform(0.35, 0.65)
            move_and_click(page, click_x, click_y)

            # If the real mouse click missed, retry with the browser's own click
            if not wait_for_navigation(page, original_url, timeout=5000):
                print("Mouse click did not open the link. Retrying with a browser click.")
                page.mouse.click(click_x, click_y)

                if not wait_for_navigation(page, original_url):
                    print("Click did not navigate to a new page.")
                    return False

            print("Bitcoin page URL:", page.url)
            return True

    print("No Bitcoin link found.")
    return False


# ---------------------------------------------------------------------------
# Visiting the coin market websites
# ---------------------------------------------------------------------------

def open_new_tab(page):
    """Open a new tab and bring it to the front (pyautogui types into it)."""
    short_pause()
    new_page = page.context.new_page()
    new_page.bring_to_front()
    short_pause()
    return new_page


def visit_coin_site(page, url):
    """Open the site, scroll down and back up, open Bitcoin and browse it."""
    # Enter the website
    navigate(url)
    close_popups_news(page, timeout=5000)

    # Scroll down for 30 s, then back up until the Bitcoin link is on screen
    move_cursor_to_page()
    scroll_down_for(SCROLL_DOWN_SECONDS)
    scroll_to_bitcoin(page, SCROLL_UP_SECONDS)

    # Select Bitcoin (fall back to its direct URL if the link isn't found)
    if not click_bitcoin(page):
        for site, bitcoin_url in BITCOIN_URLS.items():
            if site in url:
                print("Falling back to the direct Bitcoin URL.")
                navigate(bitcoin_url)
                break

    # Browse the Bitcoin page
    close_popups_news(page, timeout=3000)
    move_cursor_to_page()
    browse_page()


def main():
    with sync_playwright() as p:
            browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--start-maximized"],
        )

            context = browser.new_context(no_viewport=True)
            page = context.new_page()
            short_pause()

            # Visit all three coin market websites in a random order
            sites = random.sample(url_list, len(url_list))
            print("Visiting order:", sites)

            current_page = page
            for i, url in enumerate(sites):
                if i > 0:
                    current_page = open_new_tab(current_page)

                visit_coin_site(current_page, url)
                print(f"Completed {i + 1}/{len(sites)}: {url}")

            reading_pause()
            browser.close()

if __name__ == "__main__":
    main()
