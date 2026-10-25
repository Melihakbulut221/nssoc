# Source-bound physical handoff for registered replay selection

All execution is in GitHub. Four exact source jobs at5c4137e553a0eb647873bc0c41592259e0b111e0 are prerequisites: native mainchip boot39059432529, protocol39059432338, bank proofs39059432637 and registered-cursor proofs39059432485. The successor observes these handles and never cancels/restarts them because of an observation deadline. A terminal unsuccessful source blocks physical execution.

After all four succeed, the controller retrieves the three new bank summaries and three registered-cursor summaries from exact first-attempt release groups. It checks hashes, source identity, read-cut counterexamples, full sequential counts and baseline/candidate/stuck-cursor packet results. The three unchanged LCRC bank proofs retain their original receipt hashes. The source validator requires each changed module to match its own proof revisions and the actual protocol/boot/current sources, and every RTL file to match protocol/boot/current trees.

The original43-file native boot artifact is retained intact and the28boot checks, actual PCIe idle monitoring, system and both Ethernet MBIST handover, native scrub negative control and mapped-netlist hash are independently rechecked. The unchanged physical preparation then routes this exact native netlist through floorplanning, placement and CTS, retaining all20SRAMs, packet-async PCIe, full Ethernet and20/4/8/8ns constraints.

This handoff does not accept previous ODB/timing results for the new RTL. Post-CTS repair, exact logic comparison, routing, real parasitic extraction and all-corner setup/hold/physical signoff are subsequent requirements. The old regional route remains a separate candidate.

Initial successor39059649989 failed before physical execution because the protocol handle39059439328 was the PR event, automatically cancelled by a later PR synchronization. Its source-ready log is preserved in evidence/replay-onehot-handoff-pr-binding-error-20261017.json. The corrected source is the existing live branch-push run39059432338 at the same RTL revision; no source computation was restarted. The handoff now explicitly rejects any non-push source event.
