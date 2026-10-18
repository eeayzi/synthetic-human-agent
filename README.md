# Synthetic Human Agent

A Windows desktop agent that runs a 15-minute, five-phase "research session" using real OS input: it launches a browser through File Explorer, types URLs and browses public websites with curved mouse movement and wheel scrolling, then types a report into Microsoft Word with realistic typos and corrections, saves it, and verifies the saved file. Every action is written to an audit log.

The browser keeps its automation markers (`--enable-automation`, `navigator.webdriver === true`). The agent does not hide that it is automated, does not solve CAPTCHAs, and stops when a site restricts access.

**Status:** logic is covered by mocked unit tests. Real Windows runs are still being tuned (cookie banners and popups on public sites were the most recent fixes). Treat any live result as unverified until you have checked its `audit.jsonl`.

---

## Quick start

### Option A: packaged .exe (no Python needed on the run machine)

1. On a Windows machine with Python 3.10+ installed (tick "Add to PATH"), extract this project and double-click **`build_exe.bat`**.
2. When it finishes you get:
   - `dist\SyntheticHumanAgent\SyntheticHumanAgent.exe`
   - `dist\SyntheticHumanAgent.zip`, the same folder zipped, ready to copy to other machines/VMs
3. On the run machine, extract the zip and double-click **`SyntheticHumanAgent.exe`**.
   - The first run downloads Playwright's Chromium once (about 150 MB, needs internet).
   - It runs the prerequisite check, then the live session, then waits for Enter before closing.

The exe is a folder build (the `.exe` plus its support files), not a single-file exe. Keep the whole folder together. `config.json` and `scenario.json` sit next to the exe and can be edited without rebuilding. Run outputs go to `runs\` in the same folder.

Command-line use is the same as `main.py`:

```powershell
SyntheticHumanAgent.exe                         # live session (same as RUN_LIVE.bat)
SyntheticHumanAgent.exe --mode live --check     # prerequisite check only
SyntheticHumanAgent.exe --mode simulation       # virtual-clock dry run, no desktop actions
SyntheticHumanAgent.exe install-browser         # (re)download Playwright's Chromium
```

### Option B: run from source

From this folder in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe main.py --mode live --check
.\.venv\Scripts\python.exe main.py --mode live
```

After setup, double-clicking `RUN_LIVE.bat` does the check and the live run.

---

## Machine requirements (live mode)

- Windows 10/11 with an **interactive, visible desktop**
- Microsoft Word installed, activated, with first-run dialogs already dismissed
- **US English** keyboard layout
- Primary monitor at **100% display scaling**, browser zoom 100% (the agent refuses to start otherwise)
- Nobody touching the mouse/keyboard or the run windows during the session

### Running in a Proxmox Windows VM

- Watch the VM through the Proxmox console (noVNC/SPICE), or keep an RDP window **open and not minimised**. If an RDP session disconnects, Windows locks the desktop and OS input fails mid-run.
- RDP often sets display scaling to 125% or more automatically. Set it back to 100%.
- Each VM needs its own activated Word.
- Build the exe once, then copy `dist\SyntheticHumanAgent.zip` to the other VMs.

---

## Session plan

| Phase | Share of 900 s | What happens |
|---|---|---|
| `read_brief` | 0–2 min | Launch browser via File Explorer, type a URL, browse and read |
| `draft_report` | 2–6 min | Open a new Word document, type the draft from `scenario.json`, save |
| `check_reference` | 6–9 min | Return to the browser, type another URL, browse and read |
| `finish_report` | 9–13 min | Return to Word, type the completion notes, save |
| `verify_and_review` | 13–15 min | Save, close, reopen and verify the report |

Unused phase time becomes reading/review time. If typing or loading runs out of time, the run ends as `cancelled` rather than pretending to finish.

---

## Websites

Sites come from the `web` list in `config.json`:

```json
"web": [
  "https://www.coursera.org",
  "https://www.apple.com",
  "https://apnews.com"
]
```

- At the start of each browsing phase the agent picks **one URL at random** from this list (seeded by `seed`, so the same seed picks the same sites) and types it into the address bar.
- While browsing it mostly scrolls. About 20% of steps it clicks a random visible link (`main`, `article`, `nav` links), moving the real cursor to it. Links are forced to open in the same tab.
- Requests to domains outside the list are **logged** (`network_request_external`) but not blocked, so pages load normally.
- New tabs/popup windows are closed and focus returns to the main window. Downloads are denied.

---

## Cookie banners, popups and stop conditions

### Handled automatically

**Cookie/consent banners.** The agent detects OneTrust, Cookiebot, Didomi, Usercentrics (including shadow-DOM), TrustArc, CookieYes and generic fixed cookie bars, and clicks the matching button with the normal cursor path. Set `COOKIE_CONSENT_CHOICE` at the top of `web_agent.py`:

| Value | Clicks |
|---|---|
| `'reject'` (default) | "Reject all", "Decline", "Necessary only", "Continue without agreeing" …; if there is no reject button: "Got it"/"Close"; last resort: "Save my choices" |
| `'accept'` | "Accept all", "Allow all", "I agree", "OK" … |
| `'stop'` | Stops the run instead |

**Other popups** (location prompts like Amazon's "Deliver to Singapore", newsletters, promos) are closed with their Close / Dismiss / No thanks button, or Escape if there is none.

**Language/region selectors** ("You're visiting Samsung US. Go to Samsung Singapore?") are answered with "Stay on …" so the agent remains on the configured site.

**Small non-modal popovers** (hover menus, toasts) are ignored.

**Fallback click.** If a banner or popup is still there after the physical click, the agent retries once with Playwright's `page.mouse.click()`. That helps when the OS click missed (focus or coordinate issues). It does **not** get past an invisible element covering the button, because it hits the same spot.

**Browser permission prompts** (notifications, location, camera …) are suppressed with `--disable-notifications` and `--deny-permission-prompts`.

**JavaScript dialogs.** "Leave site?" is accepted. Alerts and prompts are dismissed.

Each banner or popup gets at most 3 attempts per page.

### Stops the run (`status: blocked`, exit code 3)

| Audit reason | Cause |
|---|---|
| `visible_captcha_or_challenge` | reCAPTCHA / hCaptcha / Cloudflare challenge frame |
| `access_verification_or_restriction` | Text such as "access denied", "verify you are human", "unusual traffic", "page not found", "not available in your region" |
| `http_status_403`, `http_status_429`, … | Main page returned HTTP 400+ |
| `page_dialog_requires_attention` | Sign-in dialog, or a popup that survived 3 attempts |
| `cookie_consent_requires_attention` | Banner with no recognised button, or one that survived 3 clicks |
| `unexpected_download` | The page tried to download a file |
| `navigation_failed_to_load: …` | Browser error page (DNS failure, offline …) |

When a run is blocked, look in `audit.jsonl` for `cookie_consent_not_answered` or `page_dialog_not_dismissed`. They record the banner or popup text and the page URL.

---

## How the browser launches

1. Create a run-specific browser profile and a `Launch training browser.lnk` shortcut in the run folder.
2. Open the run folder in File Explorer, select the shortcut, and press a physical **Enter**.
3. Attach Playwright over the local DevTools port for observation and verification.
4. Confirm the expected profile, `--enable-automation` and a single browser process, then target only that window.

The profile is isolated from your normal browser and stays in the run folder. File Explorer is left open.

---

## Input, stopping and cleanup

- Word text and URLs are typed as individual PyAutoGUI keystrokes. Typos are corrected with Backspace. Cursor movement uses Bézier curves and scrolling uses small wheel-click counts.
- Before each input action the agent checks that the right window is in the foreground. For Word it also checks that the expected document has body focus.
- Word COM is used only for document setup, saving and readback, not for inserting text.
- **To stop:** hold **F8**, or push the mouse into a screen corner. Ctrl+C works when the terminal has focus. Office and browser calls can block briefly, so the stop is not instant.
- Cleanup closes only the Word document and browser this run created. Explorer and the browser profile are left in place.

### Exit codes

| Code | Status |
|---|---|
| `0` | Completed live run, or simulation |
| `1` | Execution failure |
| `2` | Setup / configuration / output error |
| `3` | Blocked by a website restriction |
| `130` | Cancelled (F8, corner, Ctrl+C) or out of time |

---

## Configuration

`config.json`

| Key | Meaning |
|---|---|
| `duration_seconds` | Session length (default 900) |
| `seed` | Random seed for site choice, timing and typos |
| `typo_probability` | Chance of a typo per character (0–1) |
| `phases` | The five phases above, in this order, with shares summing to 1 |
| `web` | List of site URLs to browse |

`scenario.json` holds the text typed into Word (`draft`, `completion`) plus `title`, `brief` and `reference`. Only printable ASCII and newlines are allowed, up to 6000 characters each.

Command-line options: `--mode simulation|live`, `--check`, `--config`, `--scenario`, `--output-dir`, `--duration`, `--seed`. A shorter `--duration` does not speed up typing. Too little time ends the run as `cancelled`.

---

## Outputs

Each run creates `runs\run-<id>\` containing:

- `audit.jsonl`: every action and decision with UTC timestamps and the observed Explorer, browser and Word PIDs
- `summary.json`: final status, error, durations and verified file evidence (SHA-256 of the saved report)
- The saved Word report (live) or `intended-report.txt` (simulation)
- The shortcut and browser profile (live). These may contain site cookies and cache, so don't share them.

Analysis helpers:

```powershell
.\.venv\Scripts\python.exe metrics.py .\runs\run-ACTUAL_ID\audit.jsonl
.\export_telemetry.ps1 -RunDirectory .\runs\run-ACTUAL_ID     # exports existing Sysmon events for the run window
```

---

## Simulation and tests

```powershell
python main.py --mode simulation
python -m unittest discover -s . -p "test_*.py" -v
```

Simulation runs the 900-second plan on a virtual clock in a fraction of a second, with no desktop actions. Its output is labelled as simulated and must not be presented as a real run.

Test status (Python 3.13): **73 tests, 67 pass.** The 6 failures in `test_adapters.py` and `test_public_web.py` are older tests that call functions which no longer exist in `web_agent.py` (`click_reference_link`, `_route_request`). They need updating or removing. `TEST_RESULTS.txt` describes an earlier version.

---

## Files

| File | Purpose |
|---|---|
| `main.py` | Command-line entry point and prerequisite check |
| `exe_entry.py` | Entry point for the packaged exe (double-click = live run) |
| `build_exe.bat` | Builds the exe with PyInstaller on Windows |
| `RUN_LIVE.bat` | Check + live run from the source `.venv` |
| `session.py` | Five-phase session runner, summary and exit codes |
| `web_agent.py` | Browsing, clicking, scrolling, cookie banners, popups, stop checks |
| `web_policy.py` | Restriction phrases and `AccessRestricted` |
| `explorer_launcher.py` | Explorer-shortcut browser launch and Chromium flags |
| `office_agent.py` | Word document typing, saving and verification |
| `desktop.py` | Window ownership, focus guard, F8/corner stop |
| `mouse_behavior.py`, `stealth_mouse.py` | Bézier cursor paths and wheel scrolling |
| `typing_behavior.py` | Typing rhythm and typo/correction model |
| `runtime.py`, `audit.py`, `metrics.py` | Run control, audit log, timing metrics |
| `settings.py` | `config.json` / `scenario.json` validation |
| `export_telemetry.ps1` | Sysmon event export for a run |
| `WINDOWS_ACCEPTANCE.md` | Manual Windows acceptance checklist |
| `CHANGELOG.md`, `SUBMISSION.md` | History and submission notes |

### Changes in this version

- `web_agent.py`: popups are dismissed instead of stopping the run; language/region selector handling; wider cookie-banner detection (more button wordings, shadow DOM, generic fixed bars, covered buttons); `page.mouse.click()` fallback; header links near the top of the page are no longer skipped; new audit events (`page_dialog_*`, `cookie_consent_not_answered`, `physical_click_intercepted`).
- `explorer_launcher.py`: `--disable-notifications` and `--deny-permission-prompts`.
- `exe_entry.py`, `build_exe.bat`: new, for building and running as an exe.
- `test_cookie_consent.py`: tests for popup dismissal, sign-in blocking and the fallback click.
