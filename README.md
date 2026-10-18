# Synthetic Human Agent — Explorer launch and public Coursera browsing

This update launches the training browser through **Windows File Explorer** and browses **public Coursera pages**, replacing the self-created local website. It preserves visible typing, corrected typos, curved mouse movement, scrolling, reading pauses, application switching, verified Word saves and audit logs.

**Windows acceptance is still pending.** Automated tests exercise logic and mocked interfaces; they do not certify real Explorer, Word or Coursera behavior. Extract this ZIP into a fresh folder and use this project as the new working version. Earlier packages remain backups.

## Public pages

The default `config.json` selects:

- [Coursera computer science catalogue](https://www.coursera.org/browse/computer-science)
- [Learning How to Learn](https://www.coursera.org/learn/learning-how-to-learn)

Both URLs were accessible through the research browsing tool on 17 October 2026. That does not guarantee access from the automated Windows browser, your network or future dates. No self-hosted page/server is used. A blank browser tab appears briefly during setup before the first public URL is typed.

Only the two configured HTTPS Coursera course/catalogue paths are allowed as top-level destinations. Normal page assets may load from third-party sites; the allowlist is not a system network firewall. The demo does not sign in, enroll, purchase, submit forms or download course files.

## How the browser launches

1. Create a new run-specific browser profile and a clearly named `Launch training browser.lnk` shortcut.
2. Open the run folder in real Windows File Explorer and select that shortcut.
3. Verify the Explorer window and selection, then send a physical **Enter** keypress.
4. Connect Playwright to that browser's local automation endpoint for page observation and verification.
5. Confirm the expected profile, automation flag and browser process; target only that browser window.

This is ordinary Explorer shortcut activation, not process-parent spoofing. The actual parent chain is whatever Windows creates. The browser retains `--enable-automation`, and the code requires `navigator.webdriver` to remain true. It does not conceal Python control or suppress automation indicators.

The profile is isolated from your normal browser account. It and the shortcut remain in the run directory. File Explorer is deliberately left open because its window can be reused by Windows. If browser startup/attachment fails before ownership is proven, the code does not guess which process to kill; the audit requests manual inspection of the run-owned window.

## Session plan

| Scheduled time | Activity |
|---|---|
| 0–2 min | Launch via File Explorer; type the first public URL; browse and read |
| 2–6 min | Switch to a new Word document; type the prewritten research-session draft; save and read |
| 6–9 min | Return to the browser; open the second configured page; browse and read |
| 9–13 min | Return to Word; type the completion notes; save and read |
| 13–15 min | Save, close, reopen and verify the report; review it |

If a visible link points to the second configured page, the agent moves the native cursor to it, verifies the target under the pointer and clicks. If that link is absent or off-screen, it records the fallback and types the configured URL into the address bar. It never clicks an arbitrary course/enrollment button just to force a click.

The Word notes are explicitly prewritten demonstration text, not a generated course review. Actual visited URLs and page titles are recorded separately. The historical `brief`, `reference`, and `workshop-report.docx` names remain internal configuration/output names; the scenario now concerns public-course research.

The activity window is 900 seconds; unused phase time becomes reading/review time. Setup is inside the first phase; cleanup can extend total runtime. Slow loading or insufficient typing time causes a non-success result rather than an invented completed session.

## Stop on challenges and restrictions

The agent stops when it detects:

- Visible CAPTCHA/challenge frames or common verification/access-denial messages.
- Main-page HTTP errors, including 403 or 429.
- Redirects/navigation outside the configured public pages, including login routes.
- Visible modal dialogs, JavaScript dialogs, unexpected popups or downloads.

A website restriction yields `status: blocked`, exit code `3`, and an audit reason. It does not retry a challenge, solve a CAPTCHA, rotate identities/proxies, suppress indicators, or continue typing into Word as if browsing succeeded. Cookie/consent banners are answered instead of stopping the run: by default the agent moves the cursor to the banner's "Reject all" / "Decline" / "Necessary only" button (or a plain "Got it"/"Close" when no choice is offered) and clicks it, logging `cookie_consent_detected` and `cookie_consent_answered`. Set `COOKIE_CONSENT_CHOICE` at the top of `web_agent.py` to `'accept'` to accept instead, or `'stop'` for the old stop-the-run behaviour. If no matching button is found, or the banner survives three clicks, the run stops with `cookie_consent_requires_attention`. Other popups (location prompts such as Amazon's "Deliver to Singapore", newsletters, promos) are closed with their Close/Dismiss/No thanks button, or Escape if there is none, logging `page_dialog_detected` and `page_dialog_dismissed`. Small non-modal popovers (hover menus, toasts) are ignored. Sign-in dialogs, and popups that survive three attempts on a page, still stop the run with `page_dialog_requires_attention`; the audit's `page_dialog_not_dismissed` event records the popup's text.

Detection is best-effort and based on observed page state. Public websites can change, show unsupported widgets or refuse automation entirely. Some blocked states may surface as ordinary navigation failures. Do not describe the detector as a guarantee that every restriction is recognized.

## Windows setup

Use a dedicated interactive Windows desktop with Word installed/activated, initial dialogs dismissed, US English keyboard layout, and primary monitor at **100% display scaling**. Browser zoom must be 100%. Do not interact with the run windows while the agent is active.

From this folder in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe main.py --mode live --check
.\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py" -v
.\.venv\Scripts\python.exe main.py --mode live
```

After setup, `RUN_LIVE.bat` also checks prerequisites and starts the session. `--check` checks platform, package availability, Word registration and Chromium installation; it does not prove Explorer shortcut activation, Office focus, site access or DPI mapping.

Python 3.10+ is intended; development tests used Python 3.14.2 on macOS. Dependency ranges are supplied. After Windows acceptance, record exact tested versions with `python -m pip freeze > windows-tested-requirements.txt`.

## Simulation and configuration

```sh
python main.py
python main.py --mode simulation --seed 42
python -m unittest discover -s . -p "test_*.py" -v
```

Simulation runs the 900-second plan on a virtual clock. It does not open Explorer, contact Coursera, move the mouse or create a real Word file. It produces `intended-report.txt`, explicitly simulated audit records and a simulated summary. It must not be presented as a real 15-minute Windows run.

Edit the two URLs under `web` in `config.json`, preserving supported public Coursera paths:

```json
"web": {
  "brief_url": "https://www.coursera.org/browse/computer-science",
  "reference_url": "https://www.coursera.org/learn/learning-how-to-learn"
}
```

Other options: `--config`, `--scenario`, `--output-dir`, `--duration`, `--seed`, and `--check`. Reducing `--duration` does not accelerate physical typing; too little time causes cancellation. Scenario text supports printable ASCII/newlines. All five phases stay in dependency order.

## Input, stopping and cleanup

Word content and browser address entry use individual PyAutoGUI OS keystrokes. Typo recovery uses Backspace. Browser cursor movement follows the original Bézier model; wheel scrolling uses small click counts. Before each input action, foreground ownership is checked; Word additionally requires body focus and the expected active document.

Office COM performs document setup, insertion-point selection, saving and readback, not content insertion. Playwright/CDP observes the browser, enforces top-level destinations and verifies navigation. All support operations are declared in the audit.

Hold **F8** briefly or move to a screen corner to stop. Ctrl+C works when the terminal receives it. Cancellation is checked between calls and during pauses. Office/browser calls can block, so a hard real-time stop is not guaranteed. Focus checks also cannot make OS input atomic with a focus change.

Cleanup closes only owned Word documents and the browser whose profile was verified. Other documents/processes are not killed. Explorer and the run-specific profile remain. Inspect any `manual_inspection_needed` or cleanup error before rerunning.

Exit codes: `0` completed live run or simulation; `1` execution failure; `2` setup/configuration/output error; `3` website restriction; `130` cancellation/deadline. The summary distinguishes simulation from live work.

## Outputs and evidence

Each unique run directory contains `audit.jsonl`, `summary.json`, and any saved Word document. Live runs additionally create the shortcut and browser profile. Simulation creates `intended-report.txt` instead of a DOCX.

Audit events record actual agent PID/PPID, observed Explorer/browser/Word PIDs, UTC timestamps, timing, actions, restrictions, saves, verification and cleanup. `summary.json` includes activity/cleanup durations and final verified file evidence. Files are saved to a known path, reopened and compared against intended text; the final artifact receives a SHA-256 hash.

Logs/profile data may include public-site cookies/cache, page URLs and local paths. Logs are not tamper-proof or power-failure durable. Do not package the live browser profile with your submission; attach only reviewed audit/evidence files.

```powershell
.\.venv\Scripts\python.exe metrics.py .\runs\run-ACTUAL_ID\audit.jsonl
.\export_telemetry.ps1 -RunDirectory .\runs\run-ACTUAL_ID
```

The Sysmon helper reads existing event XML without changing monitoring. It exports matching events for the time window, including unrelated activity. Correlate observed PIDs with timestamps and images, then ProcessGuid; never assume every event belongs to this run. Metrics describe sampled/observed timing, not proven human indistinguishability.

## Changed files

- `explorer_launcher.py`: real Explorer selection/Enter launch and isolated declared-automation profile.
- `web_agent.py`, `web_policy.py`: public browsing, allowlisted destinations, native input and stop-on-restriction behavior.
- `config.json`, `scenario.json`, `settings.py`, `session.py`: public URLs, coherent demo notes and blocked status.
- `desktop.py`: owned browser window lookup by observed PID.
- Tests, README and Windows acceptance instructions updated; the local fixture/server module was removed.

## Validation

See `TEST_RESULTS.txt` and `WINDOWS_ACCEPTANCE.md`. Tests use mocks for Explorer, browser and Word and include launch selection, retained automation indicators, policy restrictions, native input, save corruption, cancellation and cleanup. Real Windows Explorer launch, Coursera's response to this browser, Office body focus, screen coordinates, live timing and Sysmon export have not been validated here.

Technical references: [Playwright browser connection](https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp), [Chromium debugging protocol](https://chromedevtools.github.io/devtools-protocol/), [Microsoft Sysmon](https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon).
