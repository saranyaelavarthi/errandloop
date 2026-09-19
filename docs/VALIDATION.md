# Current live-group validation

- **50 Python tests pass**, including independent-account exchanges, actor-header
  spoofing denial, group isolation, salted password storage, login lockout,
  group-code validation, real pickup locations, restart persistence, cloud revision
  conflicts, and Lambda session identity.
- A DOM + live HTTP integration test creates two accounts through the actual
  onboarding forms, checks an empty initial board, posts a real trip through the
  app, observes it from the second account, and adds a pickup location as owner.
  It uses jsdom; this is not a visual browser/layout review.
- JavaScript syntax and both AWS infrastructure templates validate successfully.
- AWS deployment remains unexecuted without authenticated account access. No public
  URL, cloud user-flow result, or real-world impact is claimed.

Reproduce DOM integration with Node 24.15+ and `jsdom@30.1.0` installed in a
separate test environment, then `node scripts/live-dom-test.cjs`. CI runs it with
Python dependencies installed. Browser screenshots below depict the older demo,
which is retained only with `--demo`.

## Earlier demonstration-mode checks

# Validation record

Validated on 17 September 2026 in a Linux workspace with Python 3.12 and a Chromium browser.

## Automated domain and adapter tests

`python -m pytest -q`: **31 tests passed**.

- Feasibility: deadlines, readiness, capacity, departure, and no self-exchanges.
- Cycles: 2–4-person cycles, stable ordering, and non-overlapping recommendations.
- Exact objective: randomized small boards compared with an independent brute-force packing oracle.
- Explanations: recommended participants are never also reported as unmatched.
- Cedar: outsider acceptance/cancellation, wrong-recipient handover, deleting another person's post, and unspecified actions denied.
- Lifecycle: unanimous acceptance, separate collection/receipt, expiry, cancellation before/after collection, and completion.
- Persistence: rollback, stale-version rejection, idempotent retries, and two concurrent reservations yielding one winner.
- AWS adapter: consistent DynamoDB reads, guarded writes, conditional-write conflicts, and unsigned Lambda rejection, using SDK stubs rather than an AWS account.

## Browser checks

`scripts/browser-test.cjs` completed successfully in headless Chromium 153 via Playwright:

- Proposed a three-person circle through the interface.
- Accepted individually as Asha and Ravi after Sana's proposal.
- Collected and confirmed all three handovers as their assigned people.
- Verified completion persisted after a reload.
- Created a new trip and request for Kabir and obtained a real matching suggestion.
- Used destination filtering and downloaded the activity export.
- Checked no horizontal page overflow at 1440px, 390px, 768px, and with 200% root text size at 1280px.
- Opened/dismissed a mobile dialog with the keyboard.
- Confirmed no JavaScript page errors or console errors.

Desktop, mobile, and active-circle screenshots are included and were visually inspected. The stock Playwright browser download was unavailable in the build environment, so an npm-distributed Chromium binary was used. That browser package is test infrastructure, not an app dependency.

## Infrastructure and syntax

- `node --check app/static/app.js`: passed.
- `cfn-lint template.yaml` using cfn-lint 1.56.3: passed with no diagnostics.
- AWS deployment was **not** performed. AWS account permissions, regional resource availability, deployment packaging, and live service behaviour remain unverified.
- The Windows launcher is supplied but was not run on a Windows machine. The equivalent Python startup and dependency installation were exercised on Linux.

## Bounded performance observation

A synthetic all-compatible board with 16 participants produced 12,160 candidate cycles and matched all 16 in approximately 3.7 seconds in this workspace. This is one local observation, not a service-level guarantee or a Lambda benchmark. The shipped seven-seat demo is much smaller.

## Defects found and fixed during validation

- Candidate reordering initially made a summary count refer to old list positions. Totals now come from the solver result, and unmatched explanations use the final recommendation flags.
- Switching participants initially produced two people labelled “You.” The first demo person now has a stable name, Sana; only the current seat is rendered as “You.” A browser assertion covers this case.

## Reproduce browser checks

Install Node.js and Playwright separately:

```bash
npm install --no-save playwright
npx playwright install chromium
```

Run the app in one terminal and the browser test in another:

```bash
python -m app.server
node scripts/browser-test.cjs
```

The browser test resets the fictional board and modifies its demo data. Run it only against a disposable local demo. It resets the board again when it finishes successfully.


## Hosted deployment preparation

The additional HTTP API v2 entry point serves the browser UI and enforces a
generated demo access code with signed, expiring secure cookies. Total Python
tests: **40 passed**. Hosted tests cover unauthenticated denial, invalid codes,
cookie tampering, expiry, code rotation, cross-origin writes, a complete
three-person exchange, shared reset, logout, and invalid request bodies.

`cfn-lint template.yaml infra/hosted.json` passed. JavaScript syntax checks passed
for both app and login scripts. A 4.8 MB deployment ZIP was built with the native
Linux CPython 3.12 Cedar wheel; its extracted hosted entry point and Cedar imports
loaded successfully. The package excludes repository history and deployment
credentials.

No AWS deployment, hosted browser session, or live cloud smoke test has been
performed. `scripts/deploy_aws.py` performs those live HTTP checks only when run
inside an authenticated AWS environment. AWS console navigation was unavailable
from the authoring session. See DEPLOY-AWS.md for the exact continuation.
