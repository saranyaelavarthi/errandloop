# Submission verification — 20 September 2026

## What was tested

Automated checks created fresh Alice, Bob and Cara accounts in an isolated
SQLite database and exercised the rendered DOM against the real local HTTP API.
These are simulated participant checks, not independent human usability research.

- Create an empty group; join through a prefilled invitation link.
- Post through the UI and see the post from a different account.
- Reject a return time equal to departure; retain the note and focus the error.
- Review a two-person match; accept, collect and confirm as the appropriate accounts.
- Complete a three-person-only circle with no compatible pair swap.
- Cancel after collection, preserve custody and finish the outstanding handovers.
- Show completion feedback and accurate reported confirmation counts.
- Sign in with an incorrect password, retain the username, then retry successfully.
- Recover the same completed records after signing in from a fresh session.
- Present an actionable error when initial app loading fails.

Result: **57 Python tests passed**, the HTTP/DOM integration scenario passed,
and JavaScript syntax and whitespace checks passed.

## Limits

The cloud browser could not access the local preview. Desktop/mobile screenshot
review is therefore not complete. DOM tests do not verify rendered layout,
touch usability or screen-reader announcements. No independent user feedback,
real delivery impact, public AWS deployment or award outcome is claimed.

## Fast submission preparation

1. Update with `git pull --ff-only`.
2. Run `python scripts/run_local.py --rehearsal`.
3. The app opens as Asha. Use the banner to switch to Ravi and Meena in the same window.
4. Follow `docs/DEMO-THREE-PEOPLE.md` for the demonstration. Keep it under three
   minutes if required by the submission form. Label the pickups as simulated.
5. Show the matching explanation, each person's consent, collection and receipt,
   and the completed exchange. Briefly show the Cedar policy and its enforcement
   tests to substantiate the AWS open-source component.
6. Use `docs/SUBMISSION.md` for the write-up; include the actual video URL and
   public repository URL. Check the submission form's deadline and eligibility.

Best UI is considered across the two tracks according to the supplied event
brief. The local Cedar-based project targets Build It and Best UI; do not claim
Ship It or provide a localhost address as a public deployment.
