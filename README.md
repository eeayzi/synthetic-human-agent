# Synthetic Human Agent

A Windows desktop agent that carries out a connected 15-minute office session using real operating-system input. It launches a browser through File Explorer, types website addresses and browses public pages with curved mouse movement and wheel scrolling, switches to Microsoft Word to type a report with natural pauses and corrected typos, then saves, reopens and verifies the document. Every action and decision is recorded in an audit log.

The agent is transparent by design. The browser keeps its automation markers (`--enable-automation`, `navigator.webdriver === true`), process ancestry is not faked, CAPTCHAs are never solved, and the run stops when a website restricts access.

---

## Contents

1. [Features](#features)
2. [How it works](#how-it-works)
3. [Requirements](#requirements)
4. [Installation and running](#installation-and-running)
5. [Configuration](#configuration)
6. [Website handling](#website-handling)
7. [Safety and transparency](#safety-and-transparency)
8. [Outputs and evidence](#outputs-and-evidence)
9. [Testing and validation](#testing-and-validation)
10. [Limitations](#limitations)
11. [Project structure](#project-structure)

---

## Features

- **Real OS input:** every keystroke, mouse movement, click and scroll is sent through PyAutoGUI, the same way a person's input reaches Windows.
- **Human-like typing:** variable inter-key timing, typos on neighbouring keys, delayed discovery of mistakes and Backspace corrections.
- **Natural mouse movement:** Bézier-curve cursor paths, short hesitation before clicks, and scrolling in small wheel steps with reading pauses.
- **Application switching:** alternates between the browser and Word across five timed phases.
- **Browser launched by Explorer:** the browser starts from a shortcut selected in real File Explorer and activated with a physical Enter keypress.
- **Website handling:** answers cookie-consent banners, closes ordinary popups, chooses "stay on this site" in region selectors, and stops on CAPTCHAs, access denials and HTTP errors.
- **Verified output:** the Word report is saved, closed, reopened and compared with the intended text, and its SHA-256 hash is recorded.
- **Full audit trail:** a JSON-lines log of every action with UTC timestamps and the observed process IDs.
- **Safe defaults:** simulation mode runs by default. Hold F8 or push the mouse into a screen corner to stop at any time.
- **Packaged executable:** can be built into a Windows `.exe` so the run machine needs no Python.

---

## How it works

### Session plan

| Phase | Time (of 900 s) | Activity |
|---|---|---|
| `read_brief` | 0–2 min | Launch the browser via File Explorer, type a website address, browse and read |
| `draft_report` | 2–6 min | Open a new Word document, type the draft, save |
| `check_reference` | 6–9 min | Return to the browser, type another address, browse and read |
| `finish_report` | 9–13 min | Return to Word, type the completion notes, save |
| `verify_and_review` | 13–15 min | Save, close, reopen and verify the report |

Time left over in a phase becomes reading or review time. If typing or page loading can't fit in the remaining time, the run ends as `cancelled` instead of claiming a completed session.

### Browser launch

1. Create a run-specific browser profile and a `Launch training browser.lnk` shortcut in the run folder.
2. Open that folder in File Explorer, select the shortcut and press a physical **Enter**.
3. Attach Playwright over the local DevTools port. It only observes the page and verifies navigation; all input still comes from the OS.
4. Confirm the expected profile, the `--enable-automation` flag and a single browser process before any input is sent.

### Browsing behaviour

At the start of each browsing phase the agent picks one website at random from the `web` list in `config.json`, using the configured seed so runs can be reproduced. It types the address into the address bar, then alternates between scrolling with reading pauses and, about one step in five, moving the cursor to a visible link and clicking it. Links open in the same tab, new popup windows are closed, and downloads are denied.

### Word

Word's COM interface is used only to create, save, close and reopen the document. The report text itself is typed keystroke by keystroke. Before each input action the agent confirms that Word is in the foreground and that the expected document has focus.

---

## Requirements

- Windows 10 or 11 with an interactive, visible desktop
- Microsoft Word, installed and activated, with first-run dialogs dismissed
- US English keyboard layout
- Primary monitor at **100% display scaling** and browser zoom at 100% (the agent checks this and refuses to start otherwise)
- No one using the mouse or keyboard while a session runs
- To run from source: Python 3.10+ and the packages in `requirements.txt` (PyAutoGUI, Playwright, pywin32)

**Running in a virtual machine (e.g. Proxmox):** keep the desktop visible through the VM console, or keep an RDP window open and not minimised. A disconnected RDP session locks the desktop and OS input stops working. Also check that RDP hasn't changed display scaling away from 100%.

---

## Installation and running

### Option A: Windows executable

On a Windows machine with Python installed, double-click **`build_exe.bat`**. It installs the dependencies and PyInstaller and produces:

- `dist\SyntheticHumanAgent\SyntheticHumanAgent.exe`
- `dist\SyntheticHumanAgent.zip`, the same folder zipped for copying to other machines

On the run machine, extract the folder and double-click `SyntheticHumanAgent.exe`. The first launch downloads Playwright's Chromium once (needs internet). It then checks prerequisites, runs the live session, and waits for Enter before closing. `config.json` and `scenario.json` sit next to the exe and can be edited without rebuilding.

```powershell
SyntheticHumanAgent.exe                        # prerequisite check, then the live session
SyntheticHumanAgent.exe --mode live --check    # prerequisite check only
SyntheticHumanAgent.exe --mode simulation      # dry run on a virtual clock
SyntheticHumanAgent.exe install-browser        # download Playwright's Chromium again
```

### Option B: from source

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe main.py --mode live --check
.\.venv\Scripts\python.exe main.py --mode live
```

After setup, `RUN_LIVE.bat` runs the check and the live session in one step.

### Simulation (any OS)

```powershell
python main.py --mode simulation
```

Runs the full 900-second plan on a virtual clock in under a second, with no desktop actions. The output is labelled as simulated.

### Stopping a run

Hold **F8**, or push the mouse into any screen corner. Ctrl+C also works when the terminal has focus.

---

## Configuration

**`config.json`**

| Key | Meaning |
|---|---|
| `duration_seconds` | Session length (default 900) |
| `seed` | Random seed for website choice, timing and typos |
| `typo_probability` | Probability of a typo per character (0–1, default 0.12) |
| `phases` | The five phases, in order, with time shares summing to 1 |
| `web` | List of website URLs to browse |

**`scenario.json`** holds the prewritten text typed into Word (`draft` and `completion`) plus `title`, `brief` and `reference`. Only printable ASCII and newlines are allowed, up to 6000 characters per field.

**Command-line options:** `--mode simulation|live`, `--check`, `--config`, `--scenario`, `--output-dir`, `--duration`, `--seed`.

**Cookie choice:** `COOKIE_CONSENT_CHOICE` at the top of `web_agent.py` can be `'reject'` (default), `'accept'` or `'stop'`.

---

## Website handling

### Handled automatically

| Situation | Response |
|---|---|
| Cookie/consent banner (OneTrust, Cookiebot, Didomi, Usercentrics, TrustArc, CookieYes, generic cookie bars, including shadow DOM) | Clicks the reject option by default ("Reject all", "Necessary only", "Continue without agreeing" …). If there is no reject option it uses "Got it"/"Close", and as a last resort "Save my choices". |
| Ordinary popup (location prompt, newsletter, promotion) | Clicks Close / Dismiss / No thanks, or presses Escape |
| Language or region selector | Clicks "Stay on …" so the agent remains on the configured site |
| Small hover menus and toasts | Ignored |
| Browser permission prompts (notifications, location, camera) | Suppressed with `--disable-notifications` and `--deny-permission-prompts` |
| "Leave site?" dialog / other JavaScript alerts | Accepted / dismissed |
| Click had no effect | Retries once with Playwright's `page.mouse.click()` |

Each banner or popup gets at most three attempts per page.

### Stop conditions

When any of these is detected the run ends with `status: blocked` and exit code 3, and the reason is recorded.

| Audit reason | Cause |
|---|---|
| `visible_captcha_or_challenge` | reCAPTCHA, hCaptcha or Cloudflare challenge |
| `access_verification_or_restriction` | Text such as "access denied", "verify you are human", "unusual traffic", "page not found" |
| `http_status_<code>` | The main page returned HTTP 400 or above (e.g. 403, 429) |
| `page_dialog_requires_attention` | A sign-in dialog, or a popup that could not be closed |
| `cookie_consent_requires_attention` | A consent banner with no recognisable button, or one that stayed open |
| `unexpected_download` | The page tried to download a file |
| `navigation_failed_to_load` | Browser error page (DNS failure, offline) |

---

## Safety and transparency

- **Automation is declared:** `--enable-automation` stays on, and the run aborts if `navigator.webdriver` is not `true`.
- **No evasion:** no CAPTCHA solving, no retrying around blocks, no proxy or identity rotation, no fingerprint masking.
- **No account actions:** the agent never signs in, buys, enrols, submits forms or downloads files.
- **Honest process records:** the browser is launched normally through Explorer, and the parent process is whatever Windows creates. Nothing is spoofed.
- **Isolated profile:** a fresh browser profile is created for each run, separate from personal browser data.
- **Scoped cleanup:** only the Word document and browser created by the run are closed. Nothing else is killed.
- **Operator control:** F8, the screen-corner fail-safe and Ctrl+C stop input. Focus is checked before every action.
- **Honest outcomes:** a blocked or cancelled run is reported as such and is never presented as a completed session.

---

## Outputs and evidence

Each run creates `runs\run-<id>\` containing:

| File | Contents |
|---|---|
| `audit.jsonl` | Every action, decision and restriction with UTC timestamps and the observed Explorer, browser and Word process IDs |
| `summary.json` | Final status, error, activity and cleanup durations, and verified file evidence (SHA-256) |
| Word report | The saved document (live mode) |
| `intended-report.txt` | The text that would have been typed (simulation mode) |
| Shortcut and browser profile | Created in live mode. The profile may contain site cookies and cache, so leave it out of anything you share. |

**Exit codes:** `0` completed or simulated · `1` execution failure · `2` setup or configuration error · `3` blocked by a website · `130` cancelled or out of time.

**Analysis tools:**

```powershell
.\.venv\Scripts\python.exe metrics.py .\runs\run-<id>\audit.jsonl     # timing statistics
.\export_telemetry.ps1 -RunDirectory .\runs\run-<id>                 # export Sysmon events for the run window
python plot_path.py                                                  # visualise the Bézier cursor model (needs: pip install matplotlib)
```

---

## Testing and validation

```powershell
python -m unittest discover -s . -p "test_*.py" -v
```

The test suite uses mocks for Explorer, the browser, Word and OS input. It covers Bézier geometry, typing and typo correction, cookie-banner and popup handling, CAPTCHA and HTTP stop conditions, navigation races, focus recovery, cancellation, Word save verification, cleanup and the command-line interface.

Current result (Python 3.13): **73 tests, 67 pass.** The 6 failing tests in `test_adapters.py` and `test_public_web.py` call two functions that are not part of the current `web_agent.py` (`click_reference_link`, `_route_request`). They do not indicate a fault in the current code.

Live Windows behaviour (Explorer launch, Word focus, screen-coordinate mapping, real website responses and 15-minute timing) can only be confirmed on a real machine. `WINDOWS_ACCEPTANCE.md` is the manual checklist for this.

---

## Limitations

- Live mode requires Windows and Microsoft Word. Other platforms can run simulation mode only.
- Detection of banners, popups and restrictions is best-effort and based on what the page shows. Websites change, and some may refuse automated browsers entirely. That is recorded as a valid `blocked` outcome.
- `page.mouse.click()` cannot click through an invisible element covering a button, because it targets the same screen point.
- A stop request is checked between actions and during pauses. A Word or browser call that is already in progress can delay it briefly.
- The Word text is prewritten demonstration content, not generated from the pages visited.
- Timing metrics describe the agent's own behaviour. They are not a claim that the agent cannot be told apart from a human.

---

## Project structure

| File | Purpose |
|---|---|
| `main.py` | Command-line entry point and prerequisite check |
| `exe_entry.py` | Entry point for the packaged executable |
| `build_exe.bat` | Builds the Windows executable with PyInstaller |
| `RUN_LIVE.bat` | Prerequisite check and live run from source |
| `session.py` | Five-phase session runner, summary and exit codes |
| `web_agent.py` | Browsing, clicking, scrolling, banner and popup handling, stop checks |
| `web_policy.py` | Restriction detection and the `AccessRestricted` signal |
| `explorer_launcher.py` | Explorer-shortcut browser launch and Chromium flags |
| `office_agent.py` | Word document typing, saving and verification |
| `desktop.py` | Window ownership, focus guard, F8 and corner fail-safe |
| `mouse_behavior.py` | Cursor movement and wheel scrolling |
| `stealth_mouse.py` | Bézier path geometry (historical file name; it does no monitoring evasion) |
| `typing_behavior.py` | Typing rhythm and typo/correction model |
| `runtime.py` | Run control, deadlines, cancellation and file evidence |
| `audit.py` | JSON-lines audit log |
| `metrics.py` | Timing statistics from an audit log |
| `settings.py` | Validation of `config.json` and `scenario.json` |
| `process_prep.py` | Normal process creation helper |
| `plot_path.py` | Visualisation of the cursor path model |
| `export_telemetry.ps1` | Sysmon event export for a run |
| `config.json`, `scenario.json` | Session configuration and report text |
| `test_*.py` | Unit tests |
| `WINDOWS_ACCEPTANCE.md` | Manual live-run checklist |
| `SUBMISSION.md`, `CHANGELOG.md`, `TEST_RESULTS.txt` | Supporting documentation |

### Technical references

- [Playwright: connect over CDP](https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp)
- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
- [PyAutoGUI](https://pyautogui.readthedocs.io/)
- [Microsoft Sysmon](https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon)
