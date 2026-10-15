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
    "https://www.coingecko.com",
    "https://www.coinbase.com/en-sg/xsgd",
]

# Direct Bitcoin pages, used only if the Bitcoin link can't be found by clicking
BITCOIN_URLS = {
    "coinmarketcap": "https://coinmarketcap.com/currencies/bitcoin/",
    "coinbase": "https://www.coinbase.com/price/bitcoin",
    "coingecko": "https://www.coingecko.com/en/coins/bitcoin",
}

# Direct RWA page, used only if the RWA link can't be found by clicking
COINGECKO_RWA_URL = "https://www.coingecko.com/en/rwa"

# Matches hrefs that end with /bitcoin (and not /bitcoin-cash, etc.)
BITCOIN_HREF = re.compile(r"/bitcoin/?(?:[?#].*)?$", re.I)

# CoinMarketCap: a coin page that is NOT bitcoin (JavaScript regex source)
CMC_COIN_HREF = r"^(?:https?://[^/]+)?/currencies/(?!bitcoin/?$)[^/?#]+/?$"

# CoinGecko: the RWA menu link, e.g. /en/rwa (JavaScript regex source)
CG_RWA_HREF = r"^(?:https?://[^/]+)?(?:/[a-z]{2}(?:-[a-z]+)?)?/rwa/?(?:[?#].*)?$"

SCROLL_DOWN_SECONDS = 30
SCROLL_UP_SECONDS = 5


def short_pause():
    time.sleep(random.uniform(0.3, 0.6))


def reading_pause(scale=1.0):
    time.sleep(random.uniform(2, 7) * scale)


def human_scroll(amount):
    """Scroll like a mouse wheel: several quick notches of slightly different
    size instead of one big jump. A negative amount scrolls down."""
    direction = -1 if amount < 0 else 1
    remaining = abs(amount)
    while remaining > 0:
        notch = min(remaining, random.randint(60, 140))
        pyautogui.scroll(direction * notch, _pause=False)
        remaining -= notch
        time.sleep(random.uniform(0.02, 0.09))


def press_key():
    time.sleep(random.uniform(0.08, 0.8))
    pyautogui.press("enter")


def site_name(url):
    """'coinmarketcap', 'coingecko' or 'coinbase' for a given url."""
    for site in BITCOIN_URLS:
        if site in url:
            return site
    return None


def navigate(url, pause_scale=1.0):

    pyautogui.hotkey("ctrl", "l")
    short_pause()

    pyautogui.write(
        url,
        interval=random.uniform(0.03, 0.10)
    )

    short_pause()
    press_key()

    reading_pause(pause_scale)



def browse_page(page):
    scroll_count = random.randint(1, 3)

    for i in range(scroll_count):
        # A popup may have jumped out while reading: close it first
        close_popups(page, timeout=0)

        scroll_amount = random.randint(100, 500)

        # Scroll down
        wander_mouse()
        human_scroll(-scroll_amount)
        reading_pause()

        # 15% chance of scrolling upward
        if random.random() < 0.15:
            upward_amount = random.randint(50, 100)
            human_scroll(upward_amount)

            short_pause()
            time.sleep(random.uniform(0.5, 1.2))

    # A popup may have appeared during the last reading pause
    close_popups(page, timeout=0)


def close_popups(page, timeout=6):
    """Close cookie banners, sign-up popups, dialogs and chat widgets with the
    real mouse. Returns True if something was closed.

    timeout: seconds to keep waiting for a popup to appear (popups often show
             up a few seconds after the page loads). timeout=0 is a quick
             single check, used while scrolling to catch popups that suddenly
             jump out.
    """
    started = time.monotonic()

    # Elements that usually hold a cookie banner or a popup. A match only
    # counts if it is visible and either a dialog or fixed on the screen.
    container_selectors = ", ".join([
        '[role="dialog"]', '[aria-modal="true"]', 'dialog[open]',
        '#onetrust-banner-sdk', '[id*="onetrust" i]', '#CybotCookiebotDialog',
        '[class*="bottom-popup" i]',
        '[id*="cookie" i]', '[class*="cookie" i]',
        '[id*="consent" i]', '[class*="consent" i]',
        '[class*="modal" i]', '[class*="popup" i]',
        '[class*="newsletter" i]', '[class*="signup" i]',
        '[class*="subscribe" i]',
    ])

    # Button labels (JavaScript regex), tried in order: the most
    # privacy-friendly choice first, "accept" only as a last resort.
    # Sign up / subscribe buttons are never matched.
    label_tiers = [
        r"reject|decline|deny|refuse|only (the )?(necessary|essential)|"
        r"(necessary|essential) only",
        r"no,? thanks|not now|maybe later|skip|dismiss|close|"
        r"continue without|^[×✕✖xX]$",
        r"accept|agree|allow all|got it|^ok(ay)?$",
    ]

    # Chat bubbles/greetings have no close button, so they are hidden instead
    chat_widgets = ", ".join([
        "#intercom-container", ".intercom-lightweight-app",
        "#hubspot-messages-iframe-container", "#drift-widget-container",
        "#crisp-chatbox", "#tawk-bubble-container",
        "iframe[title*='chat' i]", "iframe[title*='messaging' i]",
        "[id*='chat-widget' i]", "[class*='chat-widget' i]",
    ])

    # JS 1 - marks iframes that are fixed on the screen (consent / chat
    # iframes). Ad iframes scroll with the page and are never searched.
    mark_iframes_js = r"""() => {
        let count = 0;
        document.querySelectorAll('iframe').forEach(f => {
            f.removeAttribute('data-popup-iframe');
            const r = f.getBoundingClientRect();
            if (r.width < 100 || r.height < 60) return;
            if (r.bottom <= 0 || r.top >= innerHeight) return;
            for (let n = f; n && n !== document.body; n = n.parentElement) {
                if (getComputedStyle(n).position === 'fixed') {
                    f.setAttribute('data-popup-iframe', '1');
                    count++;
                    return;
                }
            }
        });
        return count;
    }"""

    # JS 2 - finds the best dismiss button of the visible popup and returns
    # its position (relative to the frame), or null if there is no popup.
    find_button_js = r"""({selectors, tiers, wholeFrame}) => {
        try {
            const dialogSel = '[role="dialog"], [aria-modal="true"], dialog[open]';
            const probes = [[0.5, 0.5], [0.5, 0.92], [0.85, 0.9], [0.15, 0.9], [0.85, 0.5]];
            const isVisible = (el) => {
                const r = el.getBoundingClientRect();
                if (r.width < 2 || r.height < 2) return false;
                if (r.bottom <= 0 || r.top >= innerHeight) return false;
                if (r.right <= 0 || r.left >= innerWidth) return false;
                const s = getComputedStyle(el);
                return s.visibility !== 'hidden' && s.display !== 'none'
                    && parseFloat(s.opacity) > 0.05;
            };
            const isFixed = (el) => {
                for (let n = el; n && n !== document.body
                        && n !== document.documentElement; n = n.parentElement) {
                    const p = getComputedStyle(n).position;
                    if (p === 'fixed' || p === 'sticky') return true;
                }
                return false;
            };

            document.querySelectorAll('[data-popup-pick]')
                .forEach(e => e.removeAttribute('data-popup-pick'));

            // Popup candidates: known selectors + whatever fixed box is on top
            // at a few points of the screen (middle, bottom, bottom corners)
            const found = new Set(document.querySelectorAll(selectors));
            if (wholeFrame) found.add(document.body);
            for (const [fx, fy] of probes) {
                const top = document.elementsFromPoint(innerWidth * fx, innerHeight * fy)[0];
                for (let n = top; n && n !== document.body
                        && n !== document.documentElement; n = n.parentElement) {
                    if (getComputedStyle(n).position === 'fixed') { found.add(n); break; }
                }
            }
            const candidates = [...found].filter(el => {
                if (el === document.documentElement || el.hasAttribute('data-popup-skip')) return false;
                if (el === document.body) return wholeFrame;
                return !el.closest('header, nav') && isVisible(el)
                    && (el.matches(dialogSel) || isFixed(el));
            });
            if (!candidates.length) return null;

            // Clickable things inside the popups (real buttons, but also
            // divs/spans/icons that look clickable)
            const labelOf = (b) => String(b.getAttribute('aria-label') || b.innerText
                || (typeof b.value === 'string' ? b.value : '') || b.title || '')
                .replace(/\s+/g, ' ').trim();
            const iconClose = (b) => /close|dismiss/i.test(
                String(b.className && b.className.baseVal !== undefined
                       ? b.className.baseVal : b.className) + ' ' + b.id);
            const clickableSel =
                'button, [role="button"], a, input[type="button"], input[type="submit"], [aria-label]';
            const buttons = [];
            for (const box of candidates) {
                for (const b of [...box.querySelectorAll('*')].slice(0, 800)) {
                    if (b.disabled || b.hasAttribute('data-popup-skip')) continue;
                    if (!(b.matches(clickableSel) || getComputedStyle(b).cursor === 'pointer')) continue;
                    if (!isVisible(b)) continue;
                    const label = labelOf(b);
                    if (label.length > 40) continue;   // a sentence, not a button
                    buttons.push({b, box, label});
                }
            }

            const pick = (b, label) => {
                b.setAttribute('data-popup-pick', '1');
                const r = b.getBoundingClientRect();
                return {label: label || '(icon)', x: r.left, y: r.top, w: r.width, h: r.height};
            };

            // 1. Buttons by label: reject, then close, then accept
            const regexes = tiers.map(t => new RegExp(t, 'i'));
            for (let t = 0; t < regexes.length; t++) {
                for (const {b, label} of buttons) {
                    if (regexes[t].test(label) || (t === 1 && iconClose(b))) return pick(b, label);
                }
            }

            // 2. Icon-only button in the top-right corner of a dialog/large popup
            for (const box of candidates) {
                const r = box.getBoundingClientRect();
                let best = null, bestDist = Infinity;
                for (const {b, box: owner, label} of buttons) {
                    if (owner !== box || label) continue;
                    const br = b.getBoundingClientRect();
                    if (br.width > 80 || br.height > 80) continue;
                    if (br.left < r.left + r.width * 0.6 || br.top > r.top + r.height * 0.35) continue;
                    const d = Math.hypot(r.right - br.right, br.top - r.top);
                    if (d < bestDist) { best = b; bestDist = d; }
                }
                if (best) return pick(best, '');
            }

            // 3. A dialog without a usable button: ask for the Escape key
            const dialog = candidates.find(el => el.matches(dialogSel));
            if (dialog) {
                dialog.setAttribute('data-popup-pick', '1');
                const r = dialog.getBoundingClientRect();
                return {label: '(Escape)', escape: true, x: r.left, y: r.top, w: r.width, h: r.height};
            }
            return null;
        } catch (e) {
            return {error: String(e)};
        }
    }"""

    # JS 3 - some popups lock the page scroll (overflow: hidden) and forget to
    # release it when closed; release it if the page is taller than the window
    unlock_scroll_js = r"""() => {
        if (document.documentElement.scrollHeight <= innerHeight + 50) return false;
        let changed = false;
        for (const el of [document.documentElement, document.body]) {
            if (/hidden|clip/.test(getComputedStyle(el).overflowY)) {
                el.style.setProperty('overflow-y', 'auto', 'important');
                changed = true;
            }
        }
        return changed;
    }"""

    deadline = started + min(timeout, 15)
    clicks = 0
    attempts = 0
    seen = {}

    while clicks < 6 and attempts < 12:
        # Where to look: the page itself, plus fixed-position iframes
        frames = [(page.main_frame, False, None)]
        try:
            if page.evaluate(mark_iframes_js):
                for handle in page.locator("iframe[data-popup-iframe]").element_handles():
                    child = handle.content_frame()
                    if child:
                        frames.append((child, True, handle.bounding_box()))
        except Exception:
            pass

        hit, hit_frame = None, None
        for frame, whole_frame, owner in frames:
            try:
                result = frame.evaluate(find_button_js, {
                    "selectors": container_selectors,
                    "tiers": label_tiers,
                    "wholeFrame": whole_frame,
                })
            except Exception:
                continue

            if result and "error" in result:
                continue

            if result:
                hit, hit_frame = result, frame
                if owner:   # positions inside an iframe are relative to it
                    hit["x"] += owner["x"]
                    hit["y"] += owner["y"]
                break

        if hit is None:
            # Nothing (more) to close; keep waiting only if nothing was closed yet
            if clicks or time.monotonic() >= deadline:
                break
            time.sleep(0.5)
            continue

        attempts += 1
        key = (hit["label"], round(hit["x"]), round(hit["y"]))
        seen[key] = seen.get(key, 0) + 1

        if seen[key] >= 3:
            # Clicking again does not help: never pick this element again
            try:
                hit_frame.evaluate(
                    "() => document.querySelectorAll('[data-popup-pick]')"
                    ".forEach(e => e.setAttribute('data-popup-skip', '1'))"
                )
            except Exception:
                pass
            continue

        if hit.get("escape"):
            page.keyboard.press("Escape")
        else:
            # Aim at a random spot inside the button
            click_x = hit["x"] + hit["w"] * random.uniform(0.35, 0.65)
            click_y = hit["y"] + hit["h"] * random.uniform(0.35, 0.65)

            if seen[key] == 1:
                move_and_click(page, click_x, click_y)   # real mouse
            else:
                page.mouse.click(click_x, click_y)       # the real click missed

        clicks += 1
        time.sleep(random.uniform(0.6, 1.0))

    # Closed something: make sure the page can scroll again
    if clicks:
        try:
            page.evaluate(unlock_scroll_js)
        except Exception:
            pass

    if timeout > 0:
        # Hide chat bubbles that have no close button
        try:
            page.add_style_tag(content=chat_widgets + " { display: none !important; }")
        except Exception:
            pass

    return clicks > 0


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


def scroll_down_for(page, seconds, mid_event=None):
    """Keep scrolling down in random steps for the given number of seconds.

    mid_event: optional function(page) that runs once, at a random moment
               during the scroll (e.g. open a random coin and come back).
               The time it takes is not counted against the scroll time.
    """
    end_time = time.monotonic() + seconds
    event_at = None
    if mid_event:
        event_at = time.monotonic() + seconds * random.uniform(0.25, 0.7)

    while time.monotonic() < end_time:
        # Time for the special event of this website
        if event_at is not None and time.monotonic() >= event_at:
            paused_at = time.monotonic()
            event_at = None
            try:
                mid_event(page)
            except Exception as error:
                pass
            end_time += time.monotonic() - paused_at
            continue

        # A popup suddenly jumped out: stop scrolling and close it first.
        # The time spent closing it is not counted against the scroll time.
        paused_at = time.monotonic()
        if close_popups(page, timeout=0):
            end_time += time.monotonic() - paused_at

        # Move the mouse a little now and then while reading
        if random.random() < 0.5:
            wander_mouse()

        # Mostly medium scrolls, sometimes a small nudge, sometimes a flick
        roll = random.random()
        if roll < 0.15:
            amount = random.randint(40, 120)
        elif roll > 0.90:
            amount = random.randint(400, 700)
        else:
            amount = random.randint(150, 400)
        human_scroll(-amount)

        # Now and then scroll back up a little, as if re-reading something
        if random.random() < 0.08:
            time.sleep(random.uniform(0.4, 1.0))
            human_scroll(random.randint(60, 150))

        # Mostly short pauses, sometimes stop for a moment to read
        if random.random() < 0.12:
            time.sleep(random.uniform(2.5, 4.5))
        else:
            time.sleep(random.uniform(0.6, 2.2))


def scroll_to_top(page, max_seconds=8):
    """Scroll back up to the top of the page with the mouse wheel."""
    end_time = time.monotonic() + max_seconds
    while time.monotonic() < end_time:
        if page.evaluate("window.scrollY") <= 0:
            break
        pyautogui.scroll(random.randint(500, 900))
        time.sleep(random.uniform(0.3, 0.5))
    short_pause()


def scroll_to_bitcoin(page, seconds):
    """Scroll back up (within `seconds`) and stop as soon as the Bitcoin link
    is on screen, wherever it sits on the page. Then wait 2-3 s before the
    link is clicked."""
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
        # A popup suddenly jumped out: stop scrolling and close it first
        paused_at = time.monotonic()
        if close_popups(page, timeout=0):
            end_time += time.monotonic() - paused_at

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


def click_box(page, box):
    """Click a link given its box {x, y, w, h} (page coordinates) with the
    real mouse and wait for the page to change. Falls back to a browser click
    if the real click missed. Returns True if a new page opened."""
    original_url = page.url

    # Aim at a random spot inside the link rather than its exact centre
    click_x = box["x"] + box["w"] * random.uniform(0.35, 0.65)
    click_y = box["y"] + box["h"] * random.uniform(0.35, 0.65)
    move_and_click(page, click_x, click_y)

    if wait_for_navigation(page, original_url, timeout=5000):
        return True

    page.mouse.click(click_x, click_y)
    if wait_for_navigation(page, original_url):
        return True

    return False


def pick_link_on_screen(page, pattern, include_nav=False, min_top=110):
    """Pick a random link whose href matches `pattern` (JavaScript regex)
    that is fully on screen, has a text label and is not covered by anything.
    Returns its box {x, y, w, h, href}, or None."""
    js = r"""({pattern, includeNav, minTop}) => {
        const re = new RegExp(pattern, 'i');
        const out = [];
        for (const a of document.querySelectorAll('a[href]')) {
            const href = a.getAttribute('href') || '';
            if (!re.test(href)) continue;
            if (!includeNav && a.closest('header, nav')) continue;
            if (!(a.innerText || '').trim()) continue;
            const r = a.getBoundingClientRect();
            if (r.width < 10 || r.height < 8) continue;
            if (r.top < minTop || r.bottom > innerHeight - 40) continue;
            if (r.left < 0 || r.right > innerWidth) continue;
            // Make sure nothing (popup, sticky bar) covers the link
            const el = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            if (!el || !a.contains(el)) continue;
            out.push({x: r.left, y: r.top, w: r.width, h: r.height, href});
        }
        return out;
    }"""
    try:
        links = page.evaluate(js, {
            "pattern": pattern,
            "includeNav": include_nav,
            "minTop": min_top,
        })
    except Exception:
        return None
    return random.choice(links) if links else None


def go_back(page):
    """Press Alt+Left (browser Back) and wait for the previous page."""
    from_url = page.url
    time.sleep(random.uniform(0.5, 1.5))
    pyautogui.hotkey("alt", "left")

    if not wait_for_navigation(page, from_url, timeout=5000):
        try:
            page.go_back(wait_until="domcontentloaded", timeout=10000)
        except Exception:
            pass

    time.sleep(random.uniform(1.0, 2.0))


def click_bitcoin(page):
    """Click the Bitcoin link on a coin market page. Returns True on success."""
    # Make sure no popup is covering the link
    close_popups(page, timeout=0)

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

            original_url = page.url

            # Aim at a random spot inside the link rather than its exact centre
            click_x = box["x"] + box["width"] * random.uniform(0.35, 0.65)
            click_y = box["y"] + box["height"] * random.uniform(0.35, 0.65)
            move_and_click(page, click_x, click_y)

            # If the real mouse click missed, retry with the browser's own click
            if not wait_for_navigation(page, original_url, timeout=5000):
                page.mouse.click(click_x, click_y)

                if not wait_for_navigation(page, original_url):
                    return False

            return True

    return False


# ---------------------------------------------------------------------------
# Special events
# ---------------------------------------------------------------------------

def cmc_random_currency_event(page):
    """CoinMarketCap: while scrolling, click a random coin (not Bitcoin) that
    is on screen, browse its page, then go back to the list."""
    close_popups(page, timeout=0)

    box = pick_link_on_screen(page, CMC_COIN_HREF)
    if box is None:
        return

    if not click_box(page, box):
        return

    move_cursor_to_page()
    close_popups(page, timeout=8)
    browse_page(page)

    go_back(page)
    move_cursor_to_page()
    close_popups(page, timeout=0)


def find_coingecko_gold(page):
    """CoinGecko RWA page: find every "Gold" label (exact text, so "Tether
    Gold" and the like are ignored) that sits inside a link.
    Returns a list of {x, y, w, h, view, covered, href} (page coordinates)."""
    js = r"""() => {
        const out = [];
        for (const el of document.querySelectorAll('*')) {
            if (el.children.length !== 0) continue;
            if (!/^\s*gold\s*$/i.test(el.textContent)) continue;
            const a = el.closest('a[href]');
            if (!a || a.closest('header, nav')) continue;
            const r = el.getBoundingClientRect();
            if (r.width < 5 || r.height < 5) continue;
            const s = getComputedStyle(el);
            if (s.visibility === 'hidden' || s.display === 'none') continue;

            // Is something (popup, sticky bar) covering the label?
            let covered = false;
            if (r.top >= 0 && r.bottom <= innerHeight) {
                const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
                covered = !top || !a.contains(top);
            }
            out.push({x: r.left, y: r.top, w: r.width, h: r.height,
                      view: innerHeight, covered, href: a.getAttribute('href')});
        }
        out.sort((p, q) => p.y - q.y);
        return out;
    }"""
    try:
        return page.evaluate(js)
    except Exception:
        return []


def coingecko_rwa_event(page):
    """CoinGecko: from the Bitcoin page go back, open RWA, click Gold and
    browse it."""

    # Back from the Bitcoin page to the CoinGecko home page
    go_back(page)
    close_popups(page, timeout=0)

    # The menu is at the top of the page
    move_cursor_to_page()
    scroll_to_top(page)

    # Click RWA in the menu
    box = pick_link_on_screen(page, CG_RWA_HREF, include_nav=True, min_top=0)
    if box and click_box(page, box):
        pass
    else:
        navigate(COINGECKO_RWA_URL)

    move_cursor_to_page()
    close_popups(page, timeout=8)
    reading_pause()

    # Find "Gold" on the RWA page, scrolling when it is not on screen yet
    gold = None
    for _ in range(8):
        close_popups(page, timeout=0)
        candidates = find_coingecko_gold(page)

        on_screen = [
            c for c in candidates
            if 100 <= c["y"] and c["y"] + c["h"] <= c["view"] - 40 and not c["covered"]
        ]
        if on_screen:
            gold = on_screen[0]
            break

        if candidates and candidates[0]["y"] < 100:
            pyautogui.scroll(random.randint(150, 300))     # above: scroll up
        else:
            pyautogui.scroll(-random.randint(200, 350))    # below / not found: scroll down
        time.sleep(random.uniform(0.6, 1.2))

    if gold is None:
        return

    if not click_box(page, gold):
        return

    move_cursor_to_page()
    close_popups(page, timeout=8)
    browse_page(page)


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
    """Open the site, scroll down and back up, open Bitcoin and browse it.
    Each site can also have its own special event."""
    site = site_name(url)

    # CoinMarketCap: click a random coin while scrolling down
    mid_event = cmc_random_currency_event if site == "coinmarketcap" else None

    # CoinGecko showed an unusually long pause before scrolling (page wait +
    # waiting for a popup that never comes), so its waiting time is halved
    wait_scale = 0.5 if site == "coingecko" else 1.0

    # Enter the website
    navigate(url, pause_scale=wait_scale)

    # Move the mouse onto the page and close cookie/sign-up popups first
    move_cursor_to_page()
    close_popups(page, timeout=8 * wait_scale)

    # Scroll down for 30 s, then back up until the Bitcoin link is on screen
    scroll_down_for(page, SCROLL_DOWN_SECONDS, mid_event)
    scroll_to_bitcoin(page, SCROLL_UP_SECONDS)

    # Select Bitcoin (fall back to its direct URL if the link isn't found)
    if not click_bitcoin(page):
        if site:
            navigate(BITCOIN_URLS[site])

    # Browse the Bitcoin page
    move_cursor_to_page()
    close_popups(page, timeout=8)
    browse_page(page)

    # CoinGecko: after Bitcoin, go back, open RWA, then click Gold
    if site == "coingecko":
        coingecko_rwa_event(page)

    # Coinbase: no special event


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

        current_page = page
        for i, url in enumerate(sites):
            if i > 0:
                current_page = open_new_tab(current_page)

            visit_coin_site(current_page, url)

        reading_pause()
        browser.close()


if __name__ == "__main__":
    main()
