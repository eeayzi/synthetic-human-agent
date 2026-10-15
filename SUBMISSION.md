# Synthetic Human Agent — submission description

## Project

A transparent synthetic office worker for controlled desktop and cyber-range demonstrations. It executes a connected 15-minute browser-and-Word scenario using physical keyboard/mouse automation while producing application ground truth that can be compared with genuine Windows telemetry.

## Demonstrated behavior

The agent reads a local workshop brief, types a draft with variable timing and corrected typos, returns to the browser to inspect a budget reference, completes the Word report, and saves/reopens it for content verification. It includes reading pauses, curved cursor movement, small scroll bursts, application switches, checkpoint saves and cancellation.

## Architecture and originality

This is a consolidation of the supplied Python prototype. It retains/refactors its typing fatigue, neighboring-key/swap/double-letter typo ideas and Bézier cursor mathematics, then adds a dependency-ordered scheduler, foreground ownership checks, interruptible waits, accurate audit records, verification and cleanup.

Word COM and Playwright are used openly for application setup and observation. Report content is entered through OS keyboard events, and browser scrolling/clicking uses OS mouse events. The supporting API operations are labeled in the audit. Process parentage is not spoofed, monitoring is not disabled, and OS logs are not fabricated.

## Scope and limitations

The submitted demo targets an interactive Windows machine with desktop Word, a US English keyboard layout and primary-monitor 100% scaling. It uses controlled local browser pages and a Word document; Excel and external-site browsing are outside this submission's implemented scope. It provides plausible configurable timing, not validated indistinguishability from biological users. It does not force an Explorer parent.

Cancellation is cooperative. A blocked Office/API call can delay stop/cleanup. Focus checks reduce global-input risk but cannot eliminate every race. Seeded simulation, tests and audit measurements support debugging and repeatability, not a claim of invisibility to security tools.

## Validation statement — fill in after Windows testing

Development tests and a virtual-clock session were run. Real Windows/Word/browser acceptance is pending in this package. Do not submit this paragraph as a passed-live-test claim until the checklist is completed.

- Windows/Word environment tested: **pending**
- Successful real run ID: **pending**
- Real activity duration and cleanup time: **pending**
- Verified report SHA-256: **pending**
- Cancellation/focus-loss checks: **pending**
- Sysmon evidence and screen recording: **pending**

See `README.md` to install/run, and `WINDOWS_ACCEPTANCE.md` for the final acceptance checks.
