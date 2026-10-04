import pyautogui
import random
import time

pyautogui.FAILSAFE = True

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
    scroll_count = random.randint(3, 7)
    print(f"Scroll count: {scroll_count}")

    for i in range(scroll_count):
        scroll_amount = random.randint(20, 50)
        print(f"Scroll amount: {scroll_amount}")
        pyautogui.scroll(-scroll_amount)

        short_pause()

        if random.random() < 0.15:
            upward_amount = random.randint(1, 3)
            pyautogui.scroll(upward_amount)
            short_pause()

            time.sleep(random.uniform(1.5, 4))
            
print("Agent starts in 5 seconds...")
print("Switch to your browser now!")
time.sleep(5)

navigate("https://en.wikipedia.org/wiki/Lee_Zii_Jia")
browse_page()

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
