import pyautogui
import random
import time
import re
from playwright.sync_api import sync_playwright

pyautogui.FAILSAFE = True

url_list = [
    "https://www.coinmarketcap.com",
    "https://www.coursera.org",
    "https://www.coinbase.com",
    "https://coingecko.com",
    "https://www.samsung.com",
    "https://aws.amazon.com",
    "https://www.amazon.com",
    "https://www.apple.com",
    "https://apnews.com",
    "https://www.dell.com"
]

persona = {
    "name": "Finance Explorer",
    "interests": {
        "finance": 5,
        "investment": 5,
        "stock": 5,
        "market": 4,
        "crypto": 5,
        "bitcoin": 5,
        "economy": 4,
        "business": 3,
        "technology": 3,
        "AI": 3
    },
    "avoid": [
        "sign in",
        "sign up",
        "log in",
        "register",
        "contact us",
        "privacy policy",
        "create account",
        "accept cookies"
    ]
}

def short_pause():
    time.sleep(random.uniform(0.3, 0.6))

def reading_pause():
    time.sleep(random.uniform(2, 7))

def press_key():
    time.sleep(random.uniform(0.08, 0.8))
    pyautogui.press("enter")

def move_and_click(page, link):
    x = link["x"]
    y = link["y"]

    print(f"Selected link: {link['text']}")

    # Record tabs before clicking
    context = page.context
    previous_pages = set(context.pages)

    # Move and click
    page.mouse.move(x, y, steps=random.randint(15, 30))
    short_pause()
    original_url = page.url
    page.mouse.click(x, y)

    # Allow navigation or a new tab to begin
    try:
        page.wait_for_url(
            lambda url: str(url) != original_url,
            timeout=5000
        )
    except Exception:
        pass

    # Detect newly opened tabs
    new_pages = [
        p for p in context.pages
        if p not in previous_pages
    ]

    if new_pages:
        page = new_pages[-1]
        print("New tab detected. Switching to it.")
    else:
        print("No new tab. Continuing with original tab.")

    # Wait for the destination page
    try:
        page.wait_for_load_state(
            "domcontentloaded",
            timeout=10000
        )
    except Exception as e:
        print(f"Page loading warning: {e}")

    print("Current URL:", page.url)

    return page

def find_links(page):
    elements = page.locator("a[href]")
    links = []

    viewport = page.viewport_size

    for i in range(elements.count()):
        element = elements.nth(i)

        if not element.is_visible():
            continue

        text = " ".join(element.inner_text().split())

        if not text:
            continue

        # Keep the full text for future persona analysis
        full_text = text

        # Shorten the display text
        display_text = text[:100]

        if len(text) > 100:
            display_text += "..."

        box = element.bounding_box()

        if box is None:
            continue

        x = box["x"] + box["width"] / 2
        y = box["y"] + box["height"] / 2

        # Exclude links outside the current viewport
        if viewport:
            if not (0 <= x < viewport["width"]):
                continue
            if not (0 <= y < viewport["height"]):
                continue

        links.append({
            "text": display_text,
            "full_text": full_text,
            "url": element.get_attribute("href"),
            "x": x,
            "y": y
        })

    return links

def choose_link(links, persona):
    candidates = []
    weights = []

    for link in links:
        text = link["full_text"].lower()
        url = (link["url"] or "").lower()

        # STEP 1: Filter unwanted links
        if any(
            phrase in text
            for phrase in persona["avoid"]
        ):
            continue

        # STEP 2: Calculate persona relevance
        score = 0

        for keyword, weight in persona["interests"].items():
            keyword = keyword.lower()

            # Match whole words or phrases
            pattern = rf"\b{re.escape(keyword)}\b"

            if re.search(pattern, text):
                score += weight

            elif re.search(pattern, url):
                score += weight * 0.5

        # STEP 3: Exclude unrelated links
        if score <= 0:
            continue

        candidates.append(link)
        weights.append(score)

    # STEP 4: Handle no relevant links
    if not candidates:
        print("No persona-relevant links found.")
        return None

    # STEP 5: Weighted random selection
    selected_link = random.choices(
        candidates,
        weights=weights,
        k=1
    )[0]

    print(f"Relevant candidates: {len(candidates)}")
    print(f"Selected relevance score: {weights[candidates.index(selected_link)]}")

    return selected_link


def go_back():
    time.sleep(random.uniform(0.5, 3.1))
    
    pyautogui.hotkey("alt", "left")
    reading_pause()

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

def browse_page(page):
    scroll_count = random.randint(3, 7)
    print(f"Scroll count: {scroll_count}")

    for i in range(scroll_count):
        scroll_amount = random.randint(50, 500)
        print(f"Scroll amount: {scroll_amount}")
        page.mouse.wheel(0, scroll_amount)

        reading_pause()

        if random.random() < 0.15:
            upward_amount = random.randint(50, 300)
            page.mouse.wheel(0, -upward_amount)
            short_pause()

            time.sleep(random.uniform(1.5, 4))

def close_popups(page):
    print("Checking for popups...")

    handled = False

    for frame in page.frames:

        # STEP 1: Find cookie-consent containers
        cookie_containers = frame.locator(
            '[id*="cookie" i], '
            '[class*="cookie" i], '
            '[id*="consent" i], '
            '[class*="consent" i]'
        )

        for i in range(min(cookie_containers.count(), 15)):
            container = cookie_containers.nth(i)

            try:
                if not container.is_visible():
                    continue

                # Prefer rejecting optional cookies
                reject = container.get_by_role(
                    "button",
                    name=re.compile(
                        r"reject|decline|necessary only|essential only",
                        re.I
                    )
                )

                if reject.count() > 0 and reject.first.is_visible():
                    reject.first.click(timeout=2000)
                    print("Cookie preferences handled.")
                    handled = True
                    break

            except Exception:
                continue

        if handled:
            continue

        # STEP 2: Find visible dialogs
        dialogs = frame.locator(
            '[role="dialog"], [aria-modal="true"]'
        )

        for i in range(min(dialogs.count(), 10)):
            dialog = dialogs.nth(i)

            try:
                if not dialog.is_visible():
                    continue

                # First attempt: named close button
                close_button = dialog.get_by_role(
                    "button",
                    name=re.compile(
                        r"^(close|dismiss|no thanks|not now)$",
                        re.I
                    )
                )

                if close_button.count() > 0 and close_button.first.is_visible():
                    close_button.first.click(timeout=2000)
                    print("Dialog closed using button.")
                    handled = True
                    break

                # Second attempt: Escape key
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)

                if not dialog.is_visible():
                    print("Dialog closed using Escape.")
                    handled = True
                    break

            except Exception:
                continue

    if not handled:
        print("No dismissible popup recognized.")

    return handled

def inspect_popups(page):
    print("\n--- Popup inspection ---")

    for frame in page.frames:
        dialogs = frame.locator(
            '[role="dialog"], '
            '[aria-modal="true"], '
            '[class*="cookie" i], '
            '[id*="cookie" i], '
            '[class*="consent" i], '
            '[id*="consent" i]'
        )

        try:
            count = min(dialogs.count(), 20)

            for i in range(count):
                dialog = dialogs.nth(i)

                if dialog.is_visible():
                    text = " ".join(dialog.inner_text().split())

                    print("Visible popup candidate:")
                    print(text[:300])

        except Exception as e:
            print("Inspection warning:", e)

    print("--- Inspection complete ---\n")
            
def main():
    SESSION_DURATION = 60

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome"
        )

        try:
            page = browser.new_page(
                viewport={"width": 1280, "height": 800}
            )

            start_time = time.monotonic()
            end_time = start_time + SESSION_DURATION

            start_url = "https://www.amazon.com"
            print(f"Starting website: {start_url}")

            page.goto(start_url, wait_until="domcontentloaded")

            inspect_popups(page)
            close_popups(page)

            visit_count = 0

            while time.monotonic() < end_time:
                visit_count += 1

                print(f"\n--- Browsing cycle {visit_count} ---")
                print("Current URL:", page.url)

                # Handle any new cookie banners
                close_popups(page)

                # Browse the current page
                print("Scrolling webpage...")
                browse_page(page)

                # Soft deadline: finish the current action
                if time.monotonic() >= end_time:
                    print("Session time reached. Stopping.")
                    break

                print("Finding links...")
                links = find_links(page)

                print(f"Found {len(links)} visible links")

                if not links:
                    page.goto(
                        random.choice(url_list),
                        wait_until="domcontentloaded"
                    )
                    continue

                selected_link = choose_link(links, persona)

                if selected_link is None:
                    print("No suitable links found.")
                    page.goto(
                        random.choice(url_list),
                        wait_until="domcontentloaded"
                    )
                    continue

                print("Persona selected:", selected_link["text"])

                page = move_and_click(page, selected_link)

                print("Now browsing:", page.url)

            elapsed = time.monotonic() - start_time

            print("\n--- Session finished ---")
            print(f"Elapsed time: {elapsed:.1f} seconds")
            print(f"Browsing cycles: {visit_count}")

        finally:
            browser.close()


if __name__ == "__main__":
    main()
