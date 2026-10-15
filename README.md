Synthetic Human Agent

A transparent synthetic office-workflow agent for controlled Windows demonstrations and cyber-range telemetry experiments.

The connected workflow reads a local project brief in Chromium, calculates a budget in Excel, and writes a Word summary using the verified budget. It saves, closes, reopens and checks the Office artifacts before reporting success. Simulation is the default and never launches desktop apps.

**Live Windows integration is implemented but has not been exercised on a real Windows/Office machine in this delivery.** The automated tests use fake Office/browser interfaces. Run the Windows acceptance checklist below before presenting this as a validated live demo.

## Quick start: simulation

Requires Python 3.10 or newer; no external packages are needed for simulation or tests. Development tests were run on Python 3.14.2 on macOS.

From the extracted project folder:

```sh
python main.py
python main.py --seed 42 --duration 60 --output-dir runs
python -m unittest discover -s . -p "test_*.py" -v
```

The bundled scenario totals **USD 559.00**. Simulation validates the scenario and records the planned steps and total. It creates `audit.jsonl` and `summary.json`, but does not create fake Word/Excel files or claim desktop verification.

## Windows live setup

Use a dedicated Windows test desktop with licensed desktop Word and Excel installed, initial activation/setup dialogs completed, and an interactive signed-in user session. Office automation uses separate COM activation requests and only closes document objects created/opened by this run. Avoid interacting with those instances during a run.

In PowerShell, from the project directory:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe main.py --mode live --check
.\.venv\Scripts\python.exe main.py --mode live --duration 900 --seed 42
```

`--check` checks platform, package availability, Office registration and the Chromium executable. It does not launch Office or prove that Office activation, add-ins, dialogs or automation will work. Fix any reported missing prerequisites before the live run. Dependency version ranges are included; they are not a Windows-validated lock file.

The browser displays a locally fulfilled fixture at `https://synthetic.invalid/brief`; no server is required and that hostname is not contacted for the fixture. The Playwright context blocks other page requests and service workers, and does not accept downloads. This is a page-routing policy, not a machine-wide network firewall: Office, browser background services and other installed software may still generate their own network activity.

## Connected workflow

1. Validate the scenario before opening any app. Currency is explicit, monetary arithmetic uses decimal values, and input sizes are bounded.
2. Open the controlled browser brief, verify its title and row count, scroll with sampled pauses, and follow its instructions link. Close the owned browser.
3. Create a new Excel workbook. Fill items and quantities, calculate row formulas and a SUM total, save to `budget.xlsx`, close and reopen it read-only. Verify item data, row formulas/values and total.
4. Create a new Word document containing the verified budget summary and run ID. Save to `report.docx`, close and reopen it read-only, and compare the full text.
5. Record artifact sizes and SHA-256 hashes, cleanup outcomes, and final run status.

Failures prevent dependent steps. For example, a failed budget verification prevents report creation. A partial run may leave useful files in its unique run directory; their presence alone does not mean the workflow succeeded.

Office operations use **COM document APIs**, not physical keystrokes. Browser actions use **Playwright**, not global mouse control. These backend names appear in the audit. The implementation preserves actual process ancestry and never claims these methods are indistinguishable from human input. Randomized pauses are experimental pacing, not a calibrated human behavior model.

## Options

| Option | Default | Purpose |
|---|---|---|
| `--mode` | `simulation` | `simulation` or explicit `live` desktop execution |
| `--scenario` | bundled `scenario.json` | Local scenario file |
| `--output-dir` | `runs` | Parent of a new unique directory for each run |
| `--duration` | `900` | Maximum work budget in seconds; work can finish earlier |
| `--pace` | `1` | Positive multiplier for sampled pauses |
| `--seed` | `42` | Reproducible random samples under the same action order |
| `--headless` | off | Hide Chromium; Office remains visible |
| `--check` | off | Report prerequisites without running the workflow |

A 900-second budget does not force a 15-minute run. Increase `--pace` or expand the scenario to spend longer doing work; do not claim an exact session duration. Real timing and outcomes depend on application responsiveness even with the same seed.

Ctrl+C and termination signals request cooperative cancellation. Exit codes: `0` = completed live run or completed simulation; `1` = workflow failure; `2` = setup/configuration/output I/O failure; `130` = cancellation or deadline reached. Check `summary.json` to distinguish live completion from simulation.

## Customize the scenario

```json
{
  "title": "Synthetic team workshop",
  "currency": "USD",
  "items": [
    {"name": "Room hire", "quantity": 1, "unit_price": "250.00"},
    {"name": "Lunch", "quantity": 12, "unit_price": "18.50"},
    {"name": "Materials", "quantity": 12, "unit_price": "7.25"}
  ]
}
```

Prices are nonnegative strings with at most two decimal places; quantities are integers from 1 to 10,000. Use 1–100 items and labels of at most 120 characters. Formula-like label prefixes and control characters are rejected. HTML labels are escaped, and Excel item labels are written as text. Only locally supplied scenario data is used; there is no public website browsing or document ingestion in this version.

## Outputs and audit

Each invocation creates `runs/run-<unique-id>/`:

```text
summary.json       status, run ID, mode, results and any error
audit.jsonl       timestamped application ground truth
brief.html        live browser fixture
budget.xlsx       live Excel artifact, if saved
report.docx       live Word artifact, if saved
```

The audit uses UTC timestamps, monotonic elapsed time, per-run sequence numbers, actual Python PID/PPID, backend labels, explicit simulation actions, artifact verification and lifecycle events. Office window PIDs are observed through Windows APIs and recorded without assuming their parentage. Browser subprocess PIDs should be identified from the actual OS event stream; the app does not invent them.

Logs are flushed after each record. They are not tamper-proof or guaranteed durable after a power failure. A force-kill or I/O failure can leave incomplete output or no final event; do not treat that as success. Input fixtures are synthetic, but logs contain scenario values and local paths.

## Sysmon export and correlation

The application does not install, disable, reconfigure or clear monitoring. If Sysmon is already enabled and you have permission to read its Operational channel, export existing events after a live run:

```powershell
.\export_telemetry.ps1 -RunDirectory .\runs\run-REPLACE_WITH_ACTUAL_ID
```

This read-only helper copies existing process creation, network connection, process termination and file creation events in the run's time window to `sysmon-events.xml`. It refuses to overwrite an existing export. Empty results are possible if event categories are disabled. The XML is a copy of event XML, not an EVTX backup.

The export includes other machine activity during that time. Correlate observed PIDs with UTC timestamps and image paths, then use Sysmon `ProcessGuid` to avoid confusing reused PIDs. Office may reuse internal services; preserve the actual observed ancestry. Process existence alone does not prove a file was saved correctly. Review artifact verification events alongside OS telemetry.

References: [Microsoft Sysmon](https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon), [Get-WinEvent](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent), [Playwright networking](https://playwright.dev/python/docs/network).

## Architecture

| File | Responsibility |
|---|---|
| `main.py` | CLI, prerequisite checks, signal handling |
| `workflow.py` | Dependency-ordered scheduling, run workspace, result/error lifecycle |
| `runtime.py` | Per-run cancellation, deadlines, pacing, artifact hashes |
| `scenario.py` | Validation, exact budget arithmetic, fixture/report content |
| `web_agent.py` | Single browser implementation using a controlled fixture |
| `office_agent.py` | Owned Excel/Word documents, reopen verification, cleanup |
| `audit.py` | Append-only application JSONL records |
| `export_telemetry.ps1` | Read-only export of existing Sysmon event XML |
| `simulation_scheduler.py` | Original weighted scheduler retained as a standalone simulation tool |
| `process_prep.py` | Optional normal process launcher; not needed by the COM workflow |
| `stealth_mouse.py` | Legacy geometry helper; not used by the connected workflow |

The old weighted scheduler remains available with `python simulation_scheduler.py --duration 15 --seed 42`. Its `config.json` configures only that simulator. The new connected workflow is dependency ordered, so it cannot randomly write a report before verifying its budget. The duplicate extensionless browser agent and unsafe global-input Office entry point are not included in this version.

## Tests and Windows acceptance

The standard-library test suite covers dependency order, failed-save handling, corrupted reopened content, cancellation, input validation, simulated/live separation, workspace isolation, browser request routing/cleanup, and Office ownership-aware cleanup, plus the original scheduler and geometry regressions. Office and browser adapters use test doubles; test artifacts are placeholders, not real DOCX/XLSX validation. See `TEST_RESULTS.txt` for execution results.

Before a live demonstration:

- Run preflight, then the live workflow on the Windows test machine.
- Confirm the final status is `completed`, and open both artifacts manually. The bundled total must be USD 559.00.
- Confirm existing unrelated Office documents remain open and unchanged.
- Test Ctrl+C during browser work, spreadsheet entry and report creation. Inspect cancellation and cleanup records.
- Test a short deadline, unavailable Office, missing browser, and an unwritable output directory. Verify failure status rather than false success.
- Export existing Sysmon events and compare the real process/file events with the audit timeline.

**Known limits:** Office COM calls and cleanup can block if Office hangs or displays a modal dialog; cancellation/deadline checks occur between calls. Some browser operations also wait until their API timeout. This version does not kill Office processes, guarantee a hard wall-clock deadline, resume interrupted runs, model human keystrokes/typos, or calibrate behavior against a human baseline. Windows Office, real-browser execution and the PowerShell export were not tested in the macOS development environment. These are explicit validation and capability limits, not completed features.
