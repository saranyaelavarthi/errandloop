# Three people. No pair swap. One working circle.

This is a scripted demonstration, not evidence of real deliveries or user research.
Use the current real-account application, not the identity-switching sample mode.

## Prepare the recording

Run the local app. Create one test group with Print shop, Library and Grocery as
pickup locations and Reception as the handover point. Use three separate browser
profiles or different browsers. Two incognito windows in the same browser usually
share cookies, so they are not separate accounts. All three must use the same
server URL. Create one account, then join the same group from the other two.

Use names you have permission to show, or clearly fictional names Asha, Ravi and
Meena. Choose your own demo passwords; never display passwords or deployment
secrets in a recording. Do not use personal order numbers or addresses.

| Person | Already going to | Needs collected from | Example prepared item |
|---|---|---|---|
| Asha | Print shop | Library | Reserved book |
| Ravi | Library | Grocery | Prepaid grocery bag |
| Meena | Grocery | Print shop | Assignment envelope |

For every trip, choose departure 30 minutes from now, return 60 minutes from now,
and capacity one. For each request, choose ready now, needed 120 minutes from now,
and one item space. If recording later, create fresh future times.

Expected circle: Asha collects Meena's printout, Meena collects Ravi's groceries,
and Ravi collects Asha's book. No pair can meet both people's requests. A three-way
exchange can. Do not describe this as a first-ever invention.

## Record under three minutes

**0:00–0:20 — Problem.**
“Three neighbours are already going out. Each needs something from a different
stop. A simple favour swap cannot help any pair. ErrandLoop closes the circle.”
Show the three posts and requests. Label the group as a demonstration.

**0:20–0:55 — The distinctive moment.**
Open Review this circle and show all three assignments. Scroll to Why this circle
fits. Show the pair-swap explanation, posted ready times, carrying space and
return-to-deadline margin. Explain: “We match existing pickup stops; we don't
verify traffic, routes or real-world savings.”

**0:55–1:25 — Consent.**
Propose as Asha, then accept from Ravi's and Meena's separate accounts. Before the
last consent, point out that there is no collection action. After it, show the
personal next-step message. Refresh the board if another account's update has not
yet appeared; normal polling is every 15 seconds.

**1:25–1:55 — A promise becomes a handover.**
Mark collection as each giver. From each recipient's account, confirm only their
own received item. Reload: three receiver-confirmed handovers, one completed
circle. These are test confirmations, not measured community impact.

**1:55–2:20 — Why AWS matters.**
Show app/policies.cedar and app/auth.py. Explain: “The AWS open-source Cedar engine
checks who can accept, collect and confirm receipt. Identity comes from the signed
session, not an identity chosen by the client.” Show a passing authorization test
and the integration test result. Disclose that this is the local Build It version.

**2:20–2:45 — Limits and validation.**
“Cancellation before collection releases available posts. After collection we
preserve the handover and do not silently reassign someone's item. The prototype
supports small trusted groups. We still need actual user trials and don't claim
verified delivery or savings.” Disclose ChatGPT/Codex assistance in the writeup.

## Optional second take: plans change

Use a fresh circle. After the first pickup, have a participant choose I can't
make this trip and confirm. Show Handover needs attention, the preserved collected
item and the absence of a replacement match. Finish outstanding handovers only if
the participants can still do so. The app does not provide substitute collectors,
dispute resolution, or proof of physical delivery.

## Before upload

- Watch the entire recording; keep it below three minutes.
- Hide group invitation codes if you reuse the group after recording.
- Check that every capability claimed is visibly demonstrated or explicitly a limit.
- Upload public/unlisted to YouTube and verify the video link signed out.
- Check actual project start time against the event's build-window rules. Never
  alter history to make an earlier project appear eligible.
