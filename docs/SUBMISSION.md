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

## Recording plan

Use [the three-person recording guide](DEMO-THREE-PEOPLE.md). It demonstrates a
circle that cannot be replaced by any compatible two-person swap, then consent,
collection and recipient confirmation across three separate accounts. Aim for
2 minutes 45 seconds. It also includes an optional cancellation-after-pickup take.

## Quick user study, if time permits

Ask two people to create a group, post reciprocal errands and complete a TEST
exchange without coaching. Record where they hesitate and whether they can explain
who collects for whom. Clearly distinguish a simulated exchange from actual goods
being handed over. Obtain permission before showing names or recording people.
Do not describe the result as real-world savings unless separately measured.
