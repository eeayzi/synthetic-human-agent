import pyautogui
import random
import time
import requests
import websocket
import json

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

def move_and_click(x, y):
    pyautogui.moveTo(
        x,
        y,
        duration=random.uniform(0.4, 1.5)
    )

    time.sleep(random.uniform(1, 3))

    pyautogui.click()

def get_tabs():
    response = requests.get("http://localhost:9222/json")
    return response.json()

def get_current_page():
    tabs = get_tabs()

    for tab in tabs:
        if tab.get("type") == "page":
            url = tab.get("url", "")

            if url.startswith("http"):
                return tab

    return None

def find_links():
    page = get_current_page()

    if page is None:
        return []

    ws_url = page["webSocketDebuggerUrl"]
    ws = websocket.create_connection(ws_url)

    command = {
        "id": 1,
        "method": "Runtime.evaluate",
        "params": {
            "expression": """
                Array.from(document.querySelectorAll('a'))
                    .map(link => {
                        const rect = link.getBoundingClientRect();

                        return {
                            text: link.innerText.trim(),
                            url: link.href,

                            x: window.screenX +
                            (window.outerWidth - window.innerWidth) / 2 +
                            rect.left +
                            rect.width / 2,

                            y: window.screenY +
                            (window.outerHeight - window.innerHeight) +
                            rect.top +
                            rect.height / 2,

                            width: rect.width,
                            height: rect.height
                        };
                    })
                    .filter(link =>
                        link.text.length > 0 &&
                        link.width > 0 &&
                        link.height > 0
                    )
            """,
            "returnByValue": True
        }
    }

    ws.send(json.dumps(command))

    response = json.loads(ws.recv())

    ws.close()

    links = response["result"]["result"]["value"]

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
    print("Agent starts in 5 seconds...")
    print("Switch to your browser now!")
    time.sleep(5)

    navigate(random.choice(url_list))
    browse_page()
    print(pyautogui.position())

    links = find_links()

    for link in links:
        print(
            link["text"],
            link["x"],
            link["y"]
        )

if __name__ == "__main__":
    main()

#Next Step
#Research the human behaviour vs agent behaviour
#implementing states to consider whether what action the agent will conduct according to the situation
#generate the agent's personality
# Reading speed      224 WPM
# Patience           medium
# Scrolling          moderately fast
# Backtracking       occasional
# Typing             medium
# Curiosity          high

#browser
#typing url
#browsing
