# Final Windows acceptance gate

These checks are intentionally **not marked passed**. Complete them on the actual demo machine. Development unit tests are not a substitute.

## Record the environment

- [ ] Windows version/build:
- [ ] Python version:
- [ ] Word version/build and activation status:
- [ ] Installed package versions saved to `windows-tested-requirements.txt`.
- [ ] Primary monitor at 100% scaling, browser zoom at 100%, US English keyboard layout.
- [ ] Sysmon version/configuration recorded if used.

## First functional run

- [ ] `python main.py --mode live --check` reports ready.
- [ ] All unit tests pass.
- [ ] Run `python main.py --mode live` without touching the desktop.
- [ ] Browser loads both local pages; the cursor visibly moves, wheels scroll, and the reference link is physically clicked.
- [ ] Word receives visible character-by-character typing, occasional typos and Backspace correction.
- [ ] Browser/Word switches occur in phase order.
- [ ] Five phase-completion records are present. The activity window is approximately 900 seconds; report cleanup time separately.
- [ ] Summary status is `completed`, mode `live`, and `desktop_actions_verified` is true.
- [ ] Manually open `workshop-report.docx`. It includes both draft and completion, including USD 559.00.
- [ ] Hash matches the final `artifact_verified` evidence before any manual modification.
- [ ] Run-created windows close after review, and unrelated documents remain unchanged.

## Failure handling

Use a fresh run for each check; cancellation is an expected nonzero exit.

- [ ] Press F8 during typing: input stops and the summary is cancelled.
- [ ] Move to a screen corner during a pause: the fail-safe is noticed.
- [ ] Switch to an unrelated app during typing: the agent stops; no continued typing in the unrelated app.
- [ ] Switch Word focus to the ribbon: typing stops rather than entering commands there.
- [ ] Run with `--duration 1`: it does not falsely report live completion.
- [ ] An unwritable output directory produces a clear nonzero error.
- [ ] If an Office modal/add-in blocks execution, record it and resolve it before the demo. Never remove focus guards or bypass the fail-safe just to continue.

## Evidence to attach

- [ ] Successful run's `summary.json`, `audit.jsonl`, and final DOCX.
- [ ] Metrics output labeled as descriptive measurements, not proof of human equivalence.
- [ ] Read-only Sysmon XML export if available; correlate actual processes and artifacts.
- [ ] Screen recording showing the real interactions and terminal result.
- [ ] Completed environment notes and this checklist.

If the competition strictly requires Explorer-parent process ancestry, ask the organizers whether normal transparent automation ancestry is acceptable. This implementation deliberately does not spoof it. Do not state full compliance with that requirement without clarification.
