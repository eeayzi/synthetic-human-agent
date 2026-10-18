# Synthetic Human Agent — public-site edition

This project demonstrates a connected 15-minute office session: launch an instrumented browser through real Windows File Explorer, browse two public Coursera pages with visible OS input, draft a Word report with variable pauses and corrected typos, return to the browser, finish the report, and save/reopen it for verification.

The original typing/typo and Bézier cursor models are retained. Application setup and observation use declared COM/Playwright support APIs. Browser automation indicators remain enabled. Process parentage and OS logs are not fabricated.

The agent stops on detected challenges, access restrictions, unexpected dialogs and navigation outside its configured public pages. It does not sign in, enroll, purchase, solve CAPTCHA challenges or retry around blocks. If no safe visible link leads to the second configured page, it types that URL instead. Public sites may refuse automation, and that refusal is a valid recorded outcome rather than a completed browsing demonstration.

The Word content is prewritten demonstration notes, not a scraped course assessment. Public URLs/titles actually observed are recorded in the audit. The implementation uses Word and Chromium; it does not include Excel or claim validated human indistinguishability.

Validation status: automated logic/simulation tests completed; actual Windows Explorer, Word and public-site execution remains pending. Complete WINDOWS_ACCEPTANCE.md before claiming a successful live demo. Record environment, run ID, activity/cleanup time, final document hash and supporting telemetry. Exclude the run's browser profile from submission artifacts.
