# Native antenna insertion admission — 2026-11-18

## Verified result

Re-audit run [44382891924](https://github.com/Melihakbulut221/nssoc/actions/runs/44382891924), source `508bb46d0366363d7e79a001ab8a68b230f4fd96`, attempt 1 completed successfully. Artifact `14464567635`, SHA-256 `d5864cb7b9575155444b2ca063010f889c9203ab7bf1a8867b86dba19254c4b3`; archive and every declared native output hash were verified.

Candidate ODB SHA-256: `2147b6df67feac28691ca76defdd7d3cafd4df1c00a74c0043fcd55f47767750`.

800 native sg13g2_antennanp diodes were added: 798 attached to SIGNAL nets, 2 to CLOCK nets. Total instances 106051. All original 105251 instances retain their geometry, masters and placement status; all original terminal connections and net types are unchanged. Special power wires, ports and die are unchanged. All new diode terminals have logical net connections, with POWER/GROUND terminal types checked against net types. This does not establish physical power connectivity or routed signal connectivity to the new cells.

The first insertion run 44381946807 at 14f4ff51de6541638ed75d13152bb5f6b5113611 returned native success but the wrapper failed because its audit allowed only SIGNAL nets. The repair did not fail: re-audit explicitly admits CLOCK nets while still rejecting supply/other net types. The existing insertion output was reused; no second insertion occurred. First artifact 14464217419 SHA-256 4131561c5d0c9a0062c755f58daf386e9863cbfe05c57815452a2b70003bbded.

Nineteen fault-control tests passed, including clock-net acceptance, changed old geometry/status/connections rejection, and floating or wrongly supplied diode rejection. Their scope is the additive identity contract, not physical continuity or timing.

## Active continuation

Detailed reroute dispatched as [44383558280](https://github.com/Melihakbulut221/nssoc/actions/runs/44383558280), immutable source `b42104b780290a762ecf705e0741af846db8d43b`, tag `cloud-core-antenna-reroute-v2-20261118`. At checkpoint creation the run is queued, not completed. Runner scripts/cloud_core_only_antenna_reroute.py authenticates the successful re-audit, exact artifact digest and all output hashes before using the ODB. It checks native routing DRC/antenna counts, exact post-insertion identity and visible wire/via/LEF geometry after routing. Source inputs remain protected. Native routing is physical only; it does not perform timing closure.

Next: inspect that exact run and artifact. If successful, bind fresh RC extraction and setup/hold checks to its new database and netlist; do not reuse the old 105251-instance timing admission. If unsuccessful, diagnose preserved outputs before changing or restarting. Previous stage 6e590b8889719eb164e650f64ca8887f55d031af targets the failed insertion job and is superseded; do not dispatch it.

## Still open

Antenna closure after routing, extracted timing and electrical limits, hierarchical main-chip integration/signoff, full transistor LVS, qualified SRAM/RC data and production approvals are not established. External package/PCB/devices remain unspecified. Retain the approved 50 MHz / 20 ns clock and 5% derate; PCIe/Ethernet are excluded from the reduced scope. Native diode-model convergence research and 22 slow-corner pad slew violations remain separate open work.
