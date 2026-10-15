# Consolidation from the original uploaded repository

Base archive: `synthetic-human-agent-main.zip`, archived Git revision `21d47288499f510a044a31902d1ce6c3f78ac44a`.

- `office_agent.py`: retained the original physical-typing approach; moved its timing/typo models into `typing_behavior.py`; added owned-document setup, focus checks, checkpoints, verification and cleanup.
- `web_agent.py`: retained physical address typing, mouse curves, wheel movements and link clicks; consolidated duplicate implementations around two controlled pages, bounded actions and verified click targeting.
- `stealth_mouse.py`: preserved the pure Bézier geometry with validation and lazy GUI import. The filename is historical; it implements ordinary movement and no monitoring evasion.
- `process_prep.py`: replaced process-parent spoofing with normal process creation. The main live workflow uses declared COM/Playwright setup.
- `main.py`/`config.json`: replaced a logging-only random scheduler with a connected, explicitly ordered five-phase session; simulation is still the safe default.
- Added audit/metrics, cancellation controls, unique output directories, standard-library tests, full setup instructions and a Windows acceptance checklist.

This package is the consolidated submission candidate. Earlier v2 used COM for report content insertion; this package does not. Original input ZIP and earlier deliverables remain separate backups.
