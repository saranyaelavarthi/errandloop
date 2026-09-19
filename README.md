# ErrandLoop

**Going anyway? Turn your next trip into a circle of small favours.**

ErrandLoop helps a small group exchange pickups on trips they already plan to
make. Each person helps once and receives help once. The default app now starts
with **your own account and an empty group** — no fictional people, seeded posts,
or impersonation switcher.

## Run locally on Windows

Python 3.12 is required. In Git Bash:

```bash
cd ~/errandloop
git pull --ff-only
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe -m app.server --open
```

Stop an already running server with Ctrl+C before restarting it. If environment
creation was interrupted, recreate only its disposable packages using
`python -m venv --clear .venv`. Let setup finish before starting the server.
Windows users can also double-click `start.bat`. macOS/Linux: `bash start.sh`.
Open http://127.0.0.1:8000 and keep the terminal running.

## Use your own data

1. **Create a group:** name your building/group, specify a shared handover point,
   and enter at least two actual shops or pickup locations.
2. Create your username and password. The board starts empty with only you.
3. Open **Your group**, copy its group code, and share it privately with people
   you know. They use **Join a group** and make their own accounts.
4. Post where you are going and what you need collected. Group owners can add
   more pickup locations from **Your group**.
5. When at least two people have compatible trips and requests, a circle appears.
   Everyone must accept from their own account. Each collector marks collection;
   each recipient confirms their own receipt.

For example, if you are going to Shop A and need an item from Shop B, a neighbour
already going to Shop B who needs something from Shop A can form a two-person
exchange. Both people must post a trip and a request with compatible times and
capacity. No artificial matches are inserted.

Locally, all accounts must use the same running server. To test two independent
accounts on one computer, use a normal browser window and an incognito window.
A group code cannot connect separate local servers. A public deployment supplies
one HTTPS URL that everyone's device can reach.

## Public AWS deployment

[Deployment instructions](docs/DEPLOY-AWS.md) use API Gateway HTTP API, Lambda,
DynamoDB, and a private S3 deployment-artifact bucket. The interface and API share
one URL. The Lambda handler is `app.live_handler.handler`.

In your authenticated **AWS CloudShell**, not Windows Git Bash:

```bash
git clone https://github.com/saranyaelavarthi/errandloop.git
cd errandloop
python3 scripts/deploy_aws.py --region ap-south-1
```

For an existing clone, run `git pull --ff-only` instead of cloning again. The
script prints the URL only after deployment and live HTTP checks. No AWS account
was authenticated in the authoring environment, so no deployment or URL is
claimed. AWS charges may apply; expired credits do not prevent charges.

## Authentication and isolation

- Accounts use salted scrypt password hashes; plaintext passwords are not stored.
- Signed sessions identify the real member and group. Demo actor headers are
  ignored. Hosted cookies are Secure, HttpOnly, SameSite=Strict, and expire after
  12 hours. Local HTTP cookies omit Secure so localhost works.
- Group invitations use random 128-bit codes. A code grants permission to join;
  share it only with intended neighbours. Keep it for later sign-in.
- Five incorrect password attempts lock that account for 15 minutes.
- AWS Cedar enforces group, post ownership, circle participation, and the assigned
  collector/recipient. The AWS-originated engine runs through the independently
  maintained `cedarpy` binding.
- SQLite transactions or DynamoDB conditional writes prevent conflicting updates.
  Each group is stored separately. Credentials never appear in board responses.

This is a first working small-group release: at most 16 members and 20 locations
per group. Password recovery, invitation rotation, member removal, moderation,
and email verification are not implemented. Names are self-reported, not verified
identities. Sign-out clears this browser's cookie; stolen cookies remain valid
until expiry or server-key rotation. Use people you know and arrange legitimate,
prepared, paid-for pickups. There are no payments or live-location tracking.

## Matching and durability

The exact solver enumerates directed cycles of 2–4 members and selects disjoint
circles maximizing matched requests, then minimizing scheduled return times.
It checks exact shared destinations, ready times, deadlines, and bag capacity.
It is not a map-based routing service. Potential trips avoided are estimates,
not measured impact.

Each proposal reserves its posts and expires if participants do not all accept.
Cancellation before collection releases the other available posts. Cancellation
after collection preserves assigned handovers and prevents duplicate pickups.
The application persists after restarts and rejects stale updates.

Local groups and session keys live in `errandloop-groups.sqlite3` (excluded from
Git). The older fictional sample board is isolated in `errandloop.sqlite3` and is
available only with `python -m app.server --demo --open`. It cannot be used to
impersonate users of the live-group app. The older IAM API and protected demo
handler remain reference/test modes; the hosted deployment uses the live handler.

## Tests and originality

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests cover the exact matcher, group isolation, account creation/login, actor
spoofing, cookie tampering, consent, collection, handovers, cancellation,
persistence, and concurrent reservations. See [validation](docs/VALIDATION.md).

Source and visual design were authored for this project with AI assistance.
Errand sharing and cycle matching are established ideas; no first-ever novelty,
real-user research, or measured impact is claimed. Follow hackathon disclosure
rules. Original code is MIT-licensed; dependencies retain their own licenses.

References: [Cedar](https://github.com/cedar-policy/cedar),
[cedarpy](https://pypi.org/project/cedarpy/),
[Python scrypt](https://docs.python.org/3.12/library/hashlib.html#hashlib.scrypt).

## Submission and demonstration

See [the submission writeup and 2:45 recording plan](docs/SUBMISSION.md).
Circle reviews explain each pickup’s readiness, capacity and deadline margin.
The board separates receiver-confirmed handovers from estimated opportunities.
