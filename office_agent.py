import time
import random
import pyautogui
from process_prep import launch_process

# CONFIGURATION

word_path = r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"

text_to_type = "Hi team, quick update on the Q3 report. I've reviewed the draft and most sections look solid. The budget numbers still need a second check before we send this out. I'll follow up with finance in the morning and get back to everyone by noon."

nearby_keys = {
    "q": ["w", "a"], "w": ["q", "e", "a", "s"], "e": ["w", "r", "s", "d"],
    "r": ["e", "t", "d", "f"], "t": ["r", "y", "f", "g"], "y": ["t", "u", "g", "h"],
    "u": ["y", "i", "h", "j"], "i": ["u", "o", "j", "k"], "o": ["i", "p", "k", "l"],
    "p": ["o", "l"], "a": ["q", "w", "s", "z"], "s": ["a", "w", "e", "d", "z", "x"],
    "d": ["s", "e", "r", "f", "x", "c"], "f": ["d", "r", "t", "g", "c", "v"],
    "g": ["f", "t", "y", "h", "v", "b"], "h": ["g", "y", "u", "j", "b", "n"],
    "j": ["h", "u", "i", "k", "n", "m"], "k": ["j", "i", "o", "l", "m"],
    "l": ["k", "o", "p"], "z": ["a", "s", "x"], "x": ["z", "s", "d", "c"],
    "c": ["x", "d", "f", "v"], "v": ["c", "f", "g", "b"], "b": ["v", "g", "h", "n"],
    "n": ["b", "h", "j", "m"], "m": ["n", "j", "k"],
}

WORD_TYPO_CHANCE = 0.15

# CANCELLATION HELPER

def should_stop(deadline, stop_event):
    """Returns True if this task should stop now (out of time or cancelled)."""
    if stop_event is not None and stop_event.is_set():
        return True
    if deadline is not None and time.monotonic() >= deadline:
        return True
    return False

# TIMING HELPER FUNCTIONS

def get_fatigue_multiplier(chars_typed_so_far, total_chars):
    if total_chars == 0:
        return 1.0
    progress = chars_typed_so_far / total_chars
    return 1.0 + (progress * 0.3)


def get_pause_time(char, chars_typed_so_far, total_chars):
    if char == ".":
        pause = random.gauss(3, 0.25)
        pause = max(pause, 2.5)
    elif char == " ":
        pause = random.gauss(0.35, 0.075)
        pause = max(pause, 0.2)
    else:
        pause = random.gauss(0.125, 0.0375)
        pause = max(pause, 0.08)

    fatigue = get_fatigue_multiplier(chars_typed_so_far, total_chars)
    return pause * fatigue


def type_char_with_pause(char, chars_typed_state):
    pyautogui.write(char)
    chars_typed_state["count"] += 1
    pause_time = get_pause_time(char, chars_typed_state["count"], chars_typed_state["total"])
    time.sleep(pause_time)


def backspace_n_times(n):
    for _ in range(n):
        pyautogui.press("backspace")
        time.sleep(random.uniform(0.05, 0.15))

# TYPO GENERATION FUNCTIONS

def apply_adjacent_swap_typo(word):
    if len(word) < 2:
        return word
    swap_index = random.randint(0, len(word) - 2)
    before = word[:swap_index]
    first_letter = word[swap_index]
    second_letter = word[swap_index + 1]
    after = word[swap_index + 2:]
    return before + second_letter + first_letter + after


def apply_double_letter_typo(word):
    if len(word) < 1:
        return word
    repeat_index = random.randint(0, len(word) - 1)
    before = word[:repeat_index]
    repeated_letter = word[repeat_index]
    after = word[repeat_index + 1:]
    return before + repeated_letter + repeated_letter + after


def apply_adjacent_key_typo(word):
    eligible_positions = [i for i, c in enumerate(word) if c.lower() in nearby_keys]
    if not eligible_positions:
        return word
    typo_index = random.choice(eligible_positions)
    original_letter = word[typo_index]
    wrong_letter = random.choice(nearby_keys[original_letter.lower()])
    before = word[:typo_index]
    after = word[typo_index + 1:]
    return before + wrong_letter + after

# WORD TYPING LOGIC (now cancellation-aware)

def type_word(word, chars_typed_state, deadline, stop_event):
    """Types one word. Returns False if we were told to stop partway through."""

    if len(word) >= 2 and random.random() < WORD_TYPO_CHANCE:
        typo_type = random.choice(["swap", "double", "adjacent_key"])

        if typo_type == "swap":
            wrong_version = apply_adjacent_swap_typo(word)
        elif typo_type == "double":
            wrong_version = apply_double_letter_typo(word)
        else:
            wrong_version = apply_adjacent_key_typo(word)

        for c in wrong_version:
            if should_stop(deadline, stop_event):
                return False
            type_char_with_pause(c, chars_typed_state)

        time.sleep(random.uniform(0.5, 1.3))
        backspace_n_times(len(wrong_version))

        for c in word:
            if should_stop(deadline, stop_event):
                return False
            type_char_with_pause(c, chars_typed_state)

    else:
        for c in word:
            if should_stop(deadline, stop_event):
                return False
            type_char_with_pause(c, chars_typed_state)

    return True

# STANDARD ENTRY POINT

def run_office_task(deadline=None, stop_event=None, logger=None):
    """
    Runs one office-typing task. Stops early and cleans up if the deadline
    is reached or stop_event is set. Returns True on normal completion,
    False if stopped early or an error occurred.
    """
    word_opened = False

    def log(message):
        if logger:
            logger.info(message)
        else:
            print(message)

    try:
        launch_process(word_path)
        word_opened = True
        log("Word launch requested.")
    except Exception as e:
        log(f"Failed to launch Word: {e}")
        return False

    time.sleep(5)

    try:
        words = text_to_type.split(" ")
        total_chars = len(text_to_type)
        chars_typed_state = {"count": 0, "total": total_chars}

        for index, word in enumerate(words):
            if should_stop(deadline, stop_event):
                log("Office task stopped early (deadline or stop_event).")
                break

            completed = type_word(word, chars_typed_state, deadline, stop_event)
            if not completed:
                log("Office task stopped mid-word (deadline or stop_event).")
                break

            if index < len(words) - 1 and not should_stop(deadline, stop_event):
                type_char_with_pause(" ", chars_typed_state)

        log("Typing phase finished (completed or stopped).")

    except Exception as e:
        log(f"An error occurred while typing: {e}")

    # Always try to save and close cleanly, even if we stopped early,
    # so we don't leave an unsaved document or an orphaned Word window.
    try:
        pyautogui.hotkey("ctrl", "s")
        time.sleep(random.uniform(1, 2))
        pyautogui.press("enter")
        time.sleep(random.uniform(1, 2))
        log("Document saved.")
    except Exception as e:
        log(f"Failed to save document: {e}")

    try:
        if word_opened:
            pyautogui.hotkey("alt", "f4")
            log("Word closed.")
    except Exception as e:
        log(f"Failed to close Word: {e}")

    return True


if __name__ == "__main__":
    # Lets you still run this file standalone for testing, without deadline/stop_event
    run_office_task()
def main():
    try:
        launch_process(word_path)
        print("Word launch requested.")
    except Exception as e:
        print(f"Failed to launch Word: {e}")
        return

    time.sleep(5)

    try:
        words = text_to_type.split(" ")
        total_chars = len(text_to_type)
        chars_typed_state = {"count": 0, "total": total_chars}

        for index, word in enumerate(words):
            type_word(word, chars_typed_state)

            if index < len(words) - 1:
                type_char_with_pause(" ", chars_typed_state)

        print("Typing finished.")

    except Exception as e:
        print(f"An error occurred while typing: {e}")
        return

    try:
        pyautogui.hotkey("ctrl", "s")
        time.sleep(random.uniform(1, 2))
        pyautogui.press("enter")
        time.sleep(random.uniform(1, 2))
        print("Document saved.")
    except Exception as e:
        print(f"Failed to save document: {e}")

    try:
        pyautogui.hotkey("alt", "f4")
        print("Word closed.")
    except Exception as e:
        print(f"Failed to close Word: {e}")


if __name__ == "__main__":
    main()
