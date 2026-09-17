# ErrandLoop: a three-minute demonstration

## 0:00–0:25 — Start with a familiar inconvenience

“I need a printout. My friend needs a prepared grocery order. We each make an extra trip because we do not know who is already going where. In a hostel, a small favour is often one message away, but those messages get buried.”

Do not claim this story came from an interview unless you actually conducted one.

## 0:25–1:00 — Show the circle

“Here I am going to the shop. Asha is going to Print Point. Ravi is going to the library. ErrandLoop finds a complete exchange: I pick up Ravi's order, Ravi collects Asha's reserved book, and Asha collects my printout. It checks all three deadlines and carrying limits.”

Open the circle. Point to each concrete handover. There are no invented distances, prices, or emission figures.

## 1:00–1:45 — Demonstrate consent, not just matching

Propose the circle as Sana (shown as “You”). Switch the clearly labelled demo seat to Asha, then Ravi, and accept separately.

“A match is only a suggestion. Every person controls their own commitment. The source of that rule is an executable Cedar policy, not just a hidden button.”

Mark an item collected. Switch to its receiver and confirm receipt.

## 1:45–2:20 — Let the judges break a promise

Cancel after one collection. Show `Handover needs attention`.

“The app does not forget that someone is already holding an item. It keeps those handovers visible and avoids sending another neighbour to collect the same thing.”

Reset and show a cancellation before collection. The other requests reopen.

## 2:20–3:00 — Explain the engineering and the next validation

“The matcher builds a directed graph, finds circles of two to four people, and selects non-overlapping circles to serve the most requests. It is deterministic and tested against a brute-force oracle. Cedar enforces who can take each action. SQLite makes the local demo persistent, and the AWS template uses Lambda and conditional DynamoDB writes.”

“The next step is a consent-based pilot with a small hostel group: measure successful handovers, cancellations, and trips participants say they actually avoided. Today's numbers are simulated, not evidence of community impact.”

## Answers to likely questions

**Why not a group chat?** Chat already enables favours. This prototype adds constraint-aware multi-person matching and an explicit record of acceptance and handover. A pilot must establish whether those benefits outweigh the effort of posting.

**Why not simply help without expecting something back?** Mutual circles are this experiment's scope, not a rule for community kindness. One-way help can be added later without weakening voluntary consent.

**Why AWS?** Cedar's explicit policy model is a real runtime dependency. The same state machine can use Lambda and DynamoDB. No unnecessary LLM calls are used to solve an exact graph problem.

**What is novel?** This particular combination and user experience. We do not claim to invent neighbour favours or graph algorithms.

**What is not finished?** Public multi-user authentication, real group onboarding, messaging, collection permissions, and a real-world pilot. The current demo is intentionally local and fictional.
