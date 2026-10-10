import time
import random
import pyautogui
from process_prep import launch_process

# CONFIGURATION

word_path = r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"

text_to_type = "Hi team, quick update on the Q3 report. I've reviewed the draft and most sections look good."

# Nearby keys on a QWERTY keyboard, used for "adjacent key" typos
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

# Chance (0 to 1) that any given word gets a typo at all
WORD_TYPO_CHANCE = 0.15

# TIMING HELPER FUNCTIONS

def get_fatigue_multiplier(chars_typed_so_far, total_chars):
    """Slowly increases pause durations as typing progresses (1.0 -> ~1.3)."""
    if total_chars == 0:
        return 1.0
    progress = chars_typed_so_far / total_chars
    return 1.0 + (progress * 0.3)


def get_pause_time(char, chars_typed_so_far, total_chars):
    """Bell-curve pause duration based on character type, with a safety floor
    and a fatigue multiplier that grows as typing progresses."""
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
    """Types a single character and pauses an appropriate amount afterward."""
    pyautogui.write(char)
    chars_typed_state["count"] += 1
    pause_time = get_pause_time(char, chars_typed_state["count"], chars_typed_state["total"])
    time.sleep(pause_time)


def backspace_n_times(n):
    """Presses backspace n times, with a small random pause between presses."""
    for _ in range(n):
        pyautogui.press("backspace")
        time.sleep(random.uniform(0.05, 0.15))

# TYPO GENERATION FUNCTIONS

def apply_adjacent_swap_typo(word):
    """Sequencing typo: swaps two adjacent letters. E.g. 'the' -> 'hte'."""
    if len(word) < 2:
        return word

    swap_index = random.randint(0, len(word) - 2)
    before = word[:swap_index]
    first_letter = word[swap_index]
    second_letter = word[swap_index + 1]
    after = word[swap_index + 2:]

    return before + second_letter + first_letter + after


def apply_double_letter_typo(word):
    """Key-repeat typo: duplicates one random letter. E.g. 'hello' -> 'helllo'."""
    if len(word) < 1:
        return word

    repeat_index = random.randint(0, len(word) - 1)
    before = word[:repeat_index]
    repeated_letter = word[repeat_index]
    after = word[repeat_index + 1:]

    return before + repeated_letter + repeated_letter + after


def apply_adjacent_key_typo(word):
    """Adjacent-key typo: replaces one random eligible letter with a nearby key."""
    eligible_positions = [i for i, c in enumerate(word) if c.lower() in nearby_keys]

    if not eligible_positions:
        return word

    typo_index = random.choice(eligible_positions)
    original_letter = word[typo_index]
    wrong_letter = random.choice(nearby_keys[original_letter.lower()])

    before = word[:typo_index]
    after = word[typo_index + 1:]

    return before + wrong_letter + after

# WORD TYPING LOGIC

def type_word(word, chars_typed_state):
    """
    Types a single word. With some probability, first types a misspelled
    version (randomly chosen typo type), pauses as if re-reading, then
    deletes it and types the correct word.
    """
    if len(word) >= 2 and random.random() < WORD_TYPO_CHANCE:
        typo_type = random.choice(["swap", "double", "adjacent_key"])

        if typo_type == "swap":
            wrong_version = apply_adjacent_swap_typo(word)
        elif typo_type == "double":
            wrong_version = apply_double_letter_typo(word)
        else:
            wrong_version = apply_adjacent_key_typo(word)

        # Type the wrong version first
        for c in wrong_version:
            type_char_with_pause(c, chars_typed_state)

        # Pause as if noticing the mistake
        time.sleep(random.uniform(0.5, 1.3))

        # Delete the wrong version and retype the correct word
        backspace_n_times(len(wrong_version))

        for c in word:
            type_char_with_pause(c, chars_typed_state)

    else:
        # No typo - type the word normally
        for c in word:
            type_char_with_pause(c, chars_typed_state)
            
# MAIN SCRIPT

def main():
    # --- Step 1: Open Word ---
    try:
        launch_process(word_path)
        print("Word launch requested.")
    except Exception as e:
        print(f"Failed to launch Word: {e}")
        return

    time.sleep(5)

    # --- Step 2: Type the text word by word, with pauses, fatigue, and typos ---
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

    # --- Step 3: Save the document ---
    try:
        pyautogui.hotkey("ctrl", "s")
        time.sleep(random.uniform(1, 2))
        pyautogui.press("enter")
        time.sleep(random.uniform(1, 2))
        print("Document saved.")
    except Exception as e:
        print(f"Failed to save document: {e}")

    # --- Step 4: Close Word ---
    try:
        pyautogui.hotkey("alt", "f4")
        print("Word closed.")
    except Exception as e:
        print(f"Failed to close Word: {e}")


if __name__ == "__main__":
    main()
