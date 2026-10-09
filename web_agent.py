import pyautogui
import random
import time
import requests
import playwright
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

    # Move cursor to the hyperlink
    page.mouse.move(x, y, steps=random.randint(15, 30))

    short_pause()

    # Click the hyperlink
    page.mouse.click(x, y)

    reading_pause()

    print(f"Current URL: {page.url}")

def find_links(page):
    elements = page.locator("a[href]")
    links = []

    viewport = page.viewport_size

    for i in range(elements.count()):
        element = elements.nth(i)

        if not element.is_visible():
            continue

        text = element.inner_text().strip()

        if not text:
            continue

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
            "text": text,
            "url": element.get_attribute("href"),
            "x": x,
            "y": y
        })

    return links


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

def browse_page():
    scroll_count = random.randint(3, 7)
    print(f"Scroll count: {scroll_count}")

    for i in range(scroll_count):
        scroll_amount = random.randint(20, 50)
        print(f"Scroll amount: {scroll_amount}")
        pyautogui.scroll(-scroll_amount)

        reading_pause()

        if random.random() < 0.15:
            upward_amount = random.randint(10, 30)
            pyautogui.scroll(upward_amount)
            short_pause()

            time.sleep(random.uniform(1.5, 4))
            
def main():
    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False,
            channel="chrome"
        )

        page = browser.new_page(
            viewport={"width": 1280, "height": 800}
        )

        page.goto(random.choice(url_list))

        print("Browser opened successfully")
        print(page.title())

        print("Scrolling webpage...")
        browse_page()

        print("Finding links after scrolling...")
        links = find_links(page)

        if links:
            selected_link = random.choice(links)

            move_and_click(page, selected_link)

            print("Page after clicking:", page.title())
            print(f"Found {len(links)} visible links")

        for link in links[:10]:
            print(
                link["text"],
                link["x"],
                link["y"]
            )

        input("Press Enter to close the browser...")

        browser.close()

if __name__ == "__main__":
    main()

