# Synthetic Human Agent — consolidated submission candidate

This version returns to the original hackathon approach: visible keyboard typing with pauses and corrected typos, curved mouse movement, scrolling, application switching, and a connected Word/browser workflow. It preserves accurate telemetry and does not spoof process parents or hide automation.

**Status:** code and simulation tested; real Windows/Word/browser acceptance is pending. This is the single consolidated project to test and submit, replacing neither your original backup nor its history. Do not merge it file-by-file into v2. Extract this ZIP into a fresh folder and use it as the working submission candidate.

## What it demonstrates

A fictional worker reads a workshop brief, drafts an update in Word, checks a budget reference, finishes the report, and verifies the saved file.

| Session time | Activity |
|---|---|
| 0–2 minutes | Open the controlled browser brief; move the cursor, scroll and read |
| 2–6 minutes | Open a new Word document; type the draft with variable pauses and occasional corrected typos; save; read |
| 6–9 minutes | Switch back to the browser; physically click the reference link; scroll and read |
| 9–13 minutes | Switch to Word; type the budget and recommendation; save; read |
| 13–15 minutes | Save, close, reopen and verify the report; review it |

The scheduled activity window is 900 seconds. Setup occurs inside the first phase, and cleanup occurs after the activity window. Reading pauses occupy spare phase time, so a successful live run does not exit as soon as typing finishes. Slow applications or insufficient typing time produce cancellation/failure rather than a false success. Cleanup may extend the total wall-clock runtime.

## What is preserved from the original

- Adjacent-key, swapped-letter and doubled-letter typos, followed by Backspace correction.
- Gaussian character/word/sentence pauses and a bounded fatigue multiplier.
- Cubic Bézier cursor paths with varying movement speed.
- Small randomized wheel movements, occasional upward scrolling and reading pauses.
- Word and browser desktop activity, now coordinated through one session runner.

The mathematical models have been refactored to accept a seeded RNG, cancellation controls and guarded input. They are illustrative distributions, not a validated model of biological human behavior.

## What changed

- One CLI and a five-phase scheduler connect the original behaviors.
- Before each OS input call, the agent checks the owned foreground window and PID. Word input additionally requires document-body focus and the expected active document.
- Browser link clicks verify that the observed native pointer is over the intended link before clicking. Unsupported scaling or mismatched coordinates stop the action.
- F8, PyAutoGUI's corner fail-safe, Ctrl+C and termination signals request a stop.
- Unique run directories, checkpoint saves, readback verification, final reopen verification and SHA-256 evidence replace blind save/close keystrokes.
- Cleanup targets the created browser and owned Word documents. It does not close arbitrary user documents or kill processes.
- Structured audit events distinguish OS input, COM support operations, Playwright setup/observation, simulation and errors.
- The process-parent spoofing launcher is gone. The retained optional launcher uses normal process creation.

## Actual keyboard input versus support APIs

| Operation | Mechanism |
|---|---|
| Word report text and typo correction | Individual PyAutoGUI OS keystrokes; no paste or COM text insertion |
| Browser address entry | PyAutoGUI keyboard input |
| Browser link selection, cursor motion and scrolling | PyAutoGUI click, Bézier movement and wheel input |
| Create a Word document, position its insertion point | Word COM setup |
| Save, read back, reopen and close the owned document | Word COM support operations |
| Launch owned Chromium, inspect DOM and observe pointer position | Playwright |
| Generate local pages | Python HTTP server bound to loopback only |

These support operations are explicitly recorded, not disguised as user input. Process ancestry is whatever Windows and the applications actually produce. A requirement for Explorer ancestry or complete human indistinguishability is **not claimed as satisfied**.

## Quick start: simulation

Python 3.10+ is the intended minimum; this package was tested with Python 3.14.2 on macOS. Simulation and tests need only the standard library.

```sh
python main.py
python -m unittest discover -s . -p "test_*.py" -v
```

Simulation uses a virtual clock: it exercises the entire 900-second plan and typing/typo model quickly, creates `intended-report.txt`, and records `status: simulated`. It does not launch apps, move the mouse, create a DOCX, or claim Windows validation. Virtual elapsed time must not be presented as a real 15-minute demonstration.

## Windows setup

Use a dedicated interactive Windows test desktop with:

- Desktop Microsoft Word installed, activated, and initial dialogs dismissed.
- A US English keyboard layout.
- The primary monitor at **100% Windows display scaling**, and browser zoom at 100%.
- No concurrent user interaction with the run's windows. Focus-loss checks reduce risk but cannot make global input atomic with foreground-window changes.

From the extracted project folder in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe main.py --mode live --check
.\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py" -v
.\.venv\Scripts\python.exe main.py --mode live
```

Alternatively, after setup, double-click `RUN_LIVE.bat`. It checks prerequisites before starting the visible desktop session. Keep the pointer away from screen corners unless you intend to stop.

`--check` checks the OS, packages, Word registration and Chromium installation. It does not prove Word activation, body focus, DPI behavior or live input compatibility. `WINDOWS_ACCEPTANCE.md` is the final validation gate.

Dependency ranges are supplied, not a fabricated Windows-tested lock. After successful acceptance on the demo machine, record its exact versions:

```powershell
.\.venv\Scripts\python.exe -m pip freeze > windows-tested-requirements.txt
```

## Run options

```sh
python main.py --mode simulation --seed 42
python main.py --mode live --config config.json --scenario scenario.json --output-dir runs
```

| Option | Purpose |
|---|---|
| `--mode simulation` | Default; fast virtual-clock execution with no desktop input |
| `--mode live` | Real Windows input and 15-minute wall-clock activity |
| `--config` | Session duration, seed, typo probability and ordered phase shares |
| `--scenario` | Local title, brief, reference, draft and completion text |
| `--duration` | Override total phase duration; reducing it may leave insufficient typing time |
| `--seed` | Reproduce random samples under the same action sequence |
| `--output-dir` | Parent folder for unique run directories |
| `--check` | Prerequisite report without launching desktop apps |

Do not use a tiny `--duration` as a successful live demo. Input speed is deliberately not compressed to fit; the deadline should cancel insufficient runs. Edit the scenario to shorter text if you want a shorter functional test.

Scenario text supports printable ASCII and newlines, up to 6,000 characters per field. All five phases must remain in dependency order. The default title and text are fictional. The demonstration focuses on Word and browser tasks; Excel is not included in this consolidated version.

## Stopping and recovering

Press and briefly hold **F8**, or move the pointer to a screen corner to stop input. Ctrl+C works when the terminal receives it. The agent checks cancellation during delays and between actions, then attempts cleanup. Earlier checkpoints remain in the run folder. Unsaved partial text is not falsely reported as verified.

Office COM calls and some browser calls can block until the application/API returns. Consequently, this does not promise a hard real-time stop or forcibly kill Office. If Word hangs, review and close the run-owned application manually. Do not disable the fail-safe to make a failing run continue.

Exit codes: `0` = completed simulation or completed live session; `1` = failure; `2` = configuration/setup/output error; `130` = cancellation/deadline. The summary distinguishes simulation from live completion.

## Outputs and telemetry

Each run creates `runs/run-<unique-id>/`:

- `audit.jsonl`: UTC timestamps, monotonic audit elapsed time, run ID, sequence, actual agent PID/PPID, phase transitions, typed-key counts, sampled pauses, typo corrections, native mouse actions, save/verification and cleanup events.
- `summary.json`: status, error, cleanup results, time basis and final verified artifact evidence.
- `workshop-report.docx`: live checkpoint/final document, when successfully saved.
- `intended-report.txt`: simulation-only expected text.

The audit includes the synthetic scenario and local output paths. It is flushed record-by-record but is not tamper-proof or guaranteed durable after a power failure. An incomplete log is not success. The final artifact hash corresponds to the verified file; later edits change that hash.

Describe a run's timing and counts:

```powershell
.\.venv\Scripts\python.exe metrics.py .\runs\run-ACTUAL_ID\audit.jsonl
```

The metrics separate sampled pauses from observed live key-event intervals. Long observed intervals can include phase changes and breaks. No “human indistinguishability” score is fabricated.

If Sysmon is already configured and its Operational log is readable, export **existing** events after a live run:

```powershell
.\export_telemetry.ps1 -RunDirectory .\runs\run-ACTUAL_ID
```

The helper copies process creation, network, termination and file creation event XML during the run window to `sysmon-events.xml`. It does not install/reconfigure Sysmon, clear logs or overwrite an existing export. It exports all matching machine events in that interval, not just agent activity. Empty results can reflect disabled event categories.

Correlate observed Word/browser PIDs with image paths and UTC timestamps, then use Sysmon `ProcessGuid` to distinguish reused PIDs. The locally served pages generate loopback activity; this demo does not generate public-site browsing traffic. Browser/Office background traffic is outside the page-level routing policy.

References: [PyAutoGUI input and fail-safes](https://pyautogui.readthedocs.io/en/latest/), [Microsoft Sysmon](https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon), [Playwright networking](https://playwright.dev/python/docs/network).

## Files

| File | Role |
|---|---|
| `main.py`, `settings.py` | CLI, preflight, config/scenario validation |
| `session.py`, `runtime.py` | Ordered phases, virtual/live timing, cancellation, results |
| `typing_behavior.py` | Preserved typo and typing-pause models |
| `mouse_behavior.py`, `stealth_mouse.py` | Guarded original-style curves and wheel movements; pure geometry |
| `desktop.py` | Windows foreground/PID/body-focus checks and OS input |
| `office_agent.py` | Word lifecycle, physical typing, checkpoints and reopen verification |
| `web_agent.py`, `fixtures.py` | Owned browser, native interaction and local pages |
| `audit.py`, `metrics.py`, `export_telemetry.ps1` | Ground truth, descriptive metrics and read-only OS-event export |
| `process_prep.py` | Optional normal launcher; live session uses COM/Playwright setup |

The large duplicate website-specific scripts have been consolidated. The demo uses two predictable, preselected local pages to avoid public website drift, cookie dialogs and account actions. Extending it to external sites is future work, not a hidden feature.

## Validation and limitations

See `TEST_RESULTS.txt`, `WINDOWS_ACCEPTANCE.md` and `SUBMISSION.md`.

Tests cover typo recovery, deterministic sampling, focus-loss rejection, guarded cursor paths, exact virtual session timing, cancellation, corrupted reopened content, save failure, native-click checks and ownership-aware cleanup. Browser and Word unit tests use test doubles; they do not validate real Office UI behavior or real DOCX serialization.

The development environment cannot run Windows Office and blocks loopback server binding, so neither real GUI execution nor the local HTTP integration was verified here. DPI/coordinate mapping, Word's `_WwG` body-focus class, keyboard layout, AutoCorrect, live phase timing and PowerShell export must pass on your Windows demo machine. If those fail, preserve the failed audit and fix the cause before submitting a successful-demo claim.
