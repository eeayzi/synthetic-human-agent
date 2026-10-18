# Windows acceptance — public browsing update

Complete on the actual demo machine; nothing below is pre-marked passed.

- [ ] Record Windows, Python, Word and installed package versions.
- [ ] Use primary-monitor 100% scaling, browser 100% zoom and US English keyboard layout.
- [ ] Run preflight and the automated test suite.
- [ ] Start live mode. Confirm Explorer opens the run directory and activates `Launch training browser.lnk` with Enter.
- [ ] Confirm a separate Chromium window/profile opens. Automation is declared; existing personal browser sessions remain separate.
- [ ] Confirm the first URL is typed and public Coursera content loads. No custom local website should open.
- [ ] Confirm native curved cursor motion, scrolling and pauses.
- [ ] Confirm the second configured public URL opens by a verified visible link or logged address-bar fallback.
- [ ] Confirm no sign-in, enrollment, purchase, arbitrary button clicking or download occurs.
- [ ] If access is restricted, expect status `blocked`/exit 3, or a navigation failure if the condition is not recognized. Do not bypass the site to make the test pass.
- [ ] Test the restriction logic in unit tests; do not deliberately trigger rate limits on the public service.
- [ ] Confirm Word receives visible typing, typo corrections and application switching.
- [ ] Confirm the final document contains the configured draft/completion text, and its hash matches final evidence.
- [ ] Confirm a successful activity window is approximately 900 seconds; record cleanup time separately.
- [ ] Test F8, corner fail-safe and foreground focus loss. Confirm input stops.
- [ ] Confirm unrelated documents remain open. The run-folder Explorer window is intentionally left open.
- [ ] Inspect failed startup/attachment for `manual_inspection_needed`; close only the run-owned window manually if necessary.
- [ ] Record successful run ID, summary, reviewed audit log, report and demo recording.
- [ ] Export genuine Sysmon events if available and correlate actual observed process ancestry.
- [ ] Exclude `browser-profile` and unreviewed site data from your submission.

No claim is made that the site cannot detect automation or that Explorer will always be the browser's immediate recorded parent. This version uses normal Windows launch behavior with accurate telemetry.
