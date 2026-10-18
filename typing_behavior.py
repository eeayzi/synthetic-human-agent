"""Original typo/fatigue model, now seeded, guarded and interruptible.
All text is sent as individual OS keystrokes. No clipboard or COM text insertion.
"""
import re

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


def get_fatigue_multiplier(chars_typed_so_far, total_chars):
    return 1.0 + .3 * min(1, max(0, chars_typed_so_far / max(1, total_chars)))


def get_pause_time(char, count, total, rng):
    if char in ".!?":
        delay = max(2.5, rng.gauss(3, .25))
    elif char in " \n":
        delay = max(.2, rng.gauss(.35, .075))
    else:
        delay = max(.08, rng.gauss(.125, .0375))
    return min(5, delay * get_fatigue_multiplier(count, total))


def make_typo(word, rng):
    kind = rng.choice(("swap", "double", "adjacent_key"))
    if kind == "swap" and len(word) > 1:
        i = rng.randrange(len(word)-1)
        wrong = word[:i] + word[i+1] + word[i] + word[i+2:]
    elif kind == "double":
        i = rng.randrange(len(word))
        wrong = word[:i] + word[i] + word[i:]
    else:
        positions = [i for i, c in enumerate(word) if c.lower() in nearby_keys]
        if not positions:
            return word, kind
        i = rng.choice(positions)
        c = rng.choice(nearby_keys[word[i].lower()])
        wrong = word[:i] + (c.upper() if word[i].isupper() else c) + word[i+1:]
    return wrong, kind


def type_text(text, ui, control, typo_probability=.12):
    if not 0 <= typo_probability <= 1:
        raise ValueError("typo_probability must be between 0 and 1")
    if any((ord(c) < 32 and c != "\n") or ord(c) > 126 for c in text):
        raise ValueError("Unsupported keyboard characters")
    count = 0
    def write_char(char):
        nonlocal count
        control.check()
        ui.press("enter") if char == "\n" else ui.write(char)
        count += 1
        delay = get_pause_time(char, count, len(text), control.rng)
        control.audit.emit("key_sent", backend=getattr(ui, "backend", "pyautogui"), kind="enter" if char == "\n" else "character",
                           sampled_pause_seconds=delay)
        control.pause(delay)
    # Correct an erroneous word before its delimiter, reducing auto-correction interference.
    for token in re.findall(r"[A-Za-z]+|[^A-Za-z]", text):
        corrected_kind = None
        if len(token) >= 2 and token.isalpha() and control.rng.random() < typo_probability:
            wrong, kind = make_typo(token, control.rng)
            if wrong != token:
                control.audit.emit("typo_started", kind=kind, wrong_length=len(wrong), corrected_length=len(token))
                for char in wrong:
                    write_char(char)
                control.pause(control.rng.uniform(.5, 1.3))
                for _ in wrong:
                    ui.press("backspace")
                    control.audit.emit("key_sent", backend=getattr(ui, "backend", "pyautogui"), kind="backspace")
                    control.pause(control.rng.uniform(.05, .15))
                corrected_kind = kind
        for char in token:
            write_char(char)
        if corrected_kind is not None:
            control.audit.emit("typo_corrected", kind=corrected_kind)
    return count
