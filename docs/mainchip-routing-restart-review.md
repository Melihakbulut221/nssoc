# Routing checkpoint use and residual repair

Source review:1November2026. This is an execution-plan correction,not a native routing or timing pass. Producer41292673925/source7a0776718ec37a106b7dfde0cbd477c6a2a5522f is terminal failure with retained raw routed checkpoints and397 last-router DRC. Actual diagnosis41302468053 isolated220 counterpart class-restoration failures; scoped native restoration41305082558 is a separate pending attempt. Neither route admission nor final timing is established by this review.

## What the current stage saves

The four route-partial/routed-fixed DEF/ODB outputs are written before class restoration. The actual restoration selects routed-fixed.odb,then route-partial.odb,then fixed.odb. Its class-restoration-plan.json records the exact source pin and whether it fell back to the pre-route state. candidate.odb is the restored output; final-measured.odb exists only after later checks. A file's presence alone proves neither routing progress nor original-clock preservation.

Successful restored-audit produces restored-snapshot.json,route-delta.json,original-clock-gate.json and connectivity-summary.json. Failure cleanup has separate failure-restored-snapshot/clock-gate evidence and cannot stand in for all successful audits. Reject pre-route fallback as a claim of saved optimized routing. A failed-but-returned route may be useful for further repair,only after an explicit independent audit; its original failure remains a failure.

## Restart is not a persisted optimizer checkpoint

The build contract pins OpenROAD upstream dcf36133a369abc8f3c5e5738cd4d82e4903c0e0 and permits changes only in TritonRoute.cpp and FlexDR_init.cpp. The former contains the internal observer; the latter the FIXED guard. Inspect the actual build/source records when admitting an execution.

At this revision,[TritonRoute::dr/stepDR/endFR](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/drt/src/TritonRoute.cpp#L645-L695) distinguish a live router object from exported OpenDB state. [FlexDR::main](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/drt/src/dr/FlexDR.cpp#L1884-L1948) initializes a search strategy and exports geometry for diagnostic snapshots. This source review does not prove that a reloaded ODB preserves optimization history or resumes at the next strategy position. Repeating end-iteration8 calls must not be presented as equivalent to continuing the original64-bound search. Read the actual loop indices and pass count from terminal logs.

The [nine-argument step_dr interface](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/drt/src/TritonRoute.tcl#L440-L448) operates on a live initialized router. It is not a persisted-resume command. The [historical maintainer response](https://github.com/The-OpenROAD-Project/OpenROAD/issues/6330#issuecomment-2544315053) also cautions against repeated detailed_route calls as pause/resume; that historical response is not a qualification of our patched executable.

## Next actual repair

Authenticate the producer's complete native archive on GitHub,restoration source,returned output pins,all protected1691 records and actual residual DRC owner/shape evidence. Before adopting a restart,qualify it on the exact executable and admitted database and record actual changed owners and violation counts. If needed,derive a scoped residual-net repair from those measured violations while retaining other routes; do not erase all828 owners again by default. Any expanded ownership or new snapshot/single-step strategy needs explicit source qualification and actual physical comparison.

Preserve all1351 diodes,PG contact,connectivity,antenna and original final timing predicates. A route repair candidate still requires complete final DRC/LVS,extracted RC and all-corner setup/hold/electrical closure.

The RTL review also confirms soc_top.v still exposes packet inputs; recovered-front and epoch transport modules explicitly leave training and PMA ownership outside their scope. No RTL change or full serial PHY integration is claimed by this review.
