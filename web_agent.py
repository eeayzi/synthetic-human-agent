import pyautogui
import random
import time
import re
from playwright.sync_api import sync_playwright

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
# Scrolling
# ---------------------------------------------------------------------------

def move_cursor_to_page():
    """pyautogui's wheel acts on the window under the OS cursor, so park the
    cursor in the middle of the (maximized) browser window first."""
    width, height = pyautogui.size()
    pyautogui.moveTo(width / 2, height / 2, duration=random.uniform(0.3, 0.8))


def scroll_down_for(seconds):
    """Keep scrolling down in random steps for the given number of seconds."""
    print(f"Scrolling down for {seconds} seconds...")
    end_time = time.monotonic() + seconds

    while time.monotonic() < end_time:
        pyautogui.scroll(-random.randint(100, 400))
        time.sleep(random.uniform(0.5, 2.0))


def scroll_to_top(page, seconds):
    """Scroll back to the top within the given number of seconds."""
    print(f"Scrolling back to the top within {seconds} seconds...")
    end_time = time.monotonic() + seconds

    while time.monotonic() < end_time:
        if page.evaluate("window.scrollY") <= 0:
            break
        pyautogui.scroll(random.randint(500, 900))
        time.sleep(random.uniform(0.2, 0.5))

    # Safety net in case time ran out before reaching the top
    page.evaluate("window.scrollTo(0, 0)")
    short_pause()


# ---------------------------------------------------------------------------
# Clicking
# ---------------------------------------------------------------------------

def move_and_click(page, x, y):
    """Move the mouse to (x, y) in small steps, pause, then click."""
    page.mouse.move(x, y, steps=random.randint(15, 30))
    short_pause()
    page.mouse.click(x, y)


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

    for i in range(min(anchors.count(), 50)):
        anchor = anchors.nth(i)

        try:
            href = anchor.get_attribute("href") or ""
            if not BITCOIN_HREF.search(href):
                continue
            if not anchor.is_visible():
                continue

            anchor.scroll_into_view_if_needed(timeout=2000)
            box = anchor.bounding_box()
            if box is None:
                continue
        except Exception:
            continue

        print(f"Clicking Bitcoin link: {href}")
        original_url = page.url
        move_and_click(
            page,
            box["x"] + box["width"] / 2,
            box["y"] + box["height"] / 2,
        )

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

    # Scroll down for 30 s, then back to the top within 5 s
    move_cursor_to_page()
    scroll_down_for(SCROLL_DOWN_SECONDS)
    scroll_to_top(page, SCROLL_UP_SECONDS)

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
