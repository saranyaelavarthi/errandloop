# ErrandLoop — your trip, someone's day made

## Short submission writeup

People in a hostel, campus or apartment building often make separate trips to the
same few places. A message asking for help does not tell you whose timing fits,
who has space, or whether the favour can be reciprocated.

ErrandLoop finds circles of two to four people using trips they already planned.
Each person picks up for one neighbour and receives help from another. Unlike a
simple pair swap, a three-person circle can work even when no pair can exchange
favours directly. An exact matcher checks shared pickup locations, readiness,
return deadlines and carrying space, then selects non-overlapping circles that
serve the most members. The interface explains the constraints behind each match.

People create their own accounts and private groups with actual pickup locations.
Every participant must accept before collection. Only the collector can record a
pickup and only its recipient can confirm receipt. If someone cancels after a
pickup, the existing handover stays visible instead of being matched twice.

AWS's open-source Cedar policy engine enforces authorization through the cedarpy
Python binding. The runnable local version uses Python and SQLite. AWS deployment
code for Lambda, API Gateway and DynamoDB is included, but this submission must
not claim a public deployment unless it has actually succeeded.

Validation includes automated domain and authorization tests and a two-account
DOM/HTTP workflow. Confirmed handovers are member reports, not independently
verified impact. Suggested trip savings are estimates, not measured results.
The initial version supports small trusted groups of at most 16 members and has
no password recovery, member removal or identity verification.

AI assistance: ChatGPT/Codex assisted with design, implementation, tests and
writing. Dependencies and their licences remain attributed in the repository.

## Before submitting

- Check that actual development began after the event opened. Preserve original
  timestamps and history; a later commit does not make pre-event work eligible.
- Register/check in and resolve student verification as the event requires.
- Add your real personal motivation in your own words. Do not claim interviews,
  users, trips saved or a campus pilot that did not happen.
- Record the workflow below and upload a video under three minutes to YouTube
  (public or unlisted). Check its link signed out.
- Submit repository, video and writeup through the event form before its deadline.
- Record a local Build It entry if AWS deployment is unavailable.

## Recording plan: aim for 2 minutes 45 seconds

Prepare two accounts in separate browser profiles in the SAME local server.
Use a test group, clearly described as a demonstration. Create two places: Print
shop and Library. A goes to Print shop and needs a library pickup. B goes to
Library and needs a print pickup. Leave 30 minutes from now, return after 60,
and set requests ready now and needed after 120. One item space each.

0:00–0:20 — Show the problem and the two planned trips.
Say: “We already make these trips. Can we help each other without making another
pickup journey? ErrandLoop finds reciprocal circles inside a trusted group.”

0:20–0:55 — Show the two signed-in accounts and their posted requests. Open the
suggested circle and its explanation: actual stop, ready time, space and deadline
margin. Say that handover travel and delays are not verified.

0:55–1:25 — Propose as A. Show that collection is unavailable until B accepts.
Switch browser windows and accept as B. Explain that the two accounts are separate.

1:25–1:55 — Mark both pickups collected from their respective accounts. Show
that each person can confirm only the item they receive. Complete both handovers.
Reload and show two confirmations and one completed circle.

1:55–2:20 — Show app/policies.cedar
and app/auth.py, then the passing authorization test output. Explain: “Cedar
checks ownership and group membership on the server, not just hidden buttons.”

2:20–2:45 — State limits and next validation: “This is a tested prototype for
small trusted groups. The next step is observing real collections with willing
users. We count member-confirmed handovers, not invented carbon savings.”

## Quick user study, if time permits

Ask two people to create a group, post reciprocal errands and complete a TEST
exchange without coaching. Record where they hesitate and whether they can explain
who collects for whom. Clearly distinguish a simulated exchange from actual goods
being handed over. Obtain permission before showing names or recording people.
Do not describe the result as real-world savings unless separately measured.
