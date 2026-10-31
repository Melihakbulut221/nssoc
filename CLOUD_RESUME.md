# Cloud continuation — checkpoint v183

Updated: 2026-10-31T17:35:12.237876+00:00

The latest user instruction is cloud-only execution. All RTL tests, simulation, CAD and numerical/native processing run on GitHub. Never acquire native archives, models, ODB/GDS, raw waves or native-frame gzip locally, including RAM. Source authoring and API derived JSON/text coordination use RAM only. Local workspace and project temporary prefixes are empty; no local CAD process runs.

## Live work to preserve

- Mainchip routing [41211382427](https://github.com/Melihakbulut221/nssoc/actions/runs/41211382427), source ddc1cbddf68096c5e976bf9acda5c5fb0168c5b9; release429993235. Do not restart for quiet logs. This is packet-interface SoC routing, not full serial PHY integration.
- Loaded ten-case CDR matrix [41218657461](https://github.com/Melihakbulut221/nssoc/actions/runs/41218657461), source84b8b591e10be32716947c8d6b079fd7a21ce18d. All eleven releases already reserved; no recreation/retry.
- Third shared-front actual RTL run [41223635170](https://github.com/Melihakbulut221/nssoc/actions/runs/41223635170), source17033684f3dfd0c760ac7cf64d2e1dc1a4b2fdb0; release430074402. Read its actual result before test-count claims.

Exact observations are in docs/evidence/cloud-collector-recipes-20261029/actual-wave-replay-and-cloud-only-v183.json; snapshots are not completion claims.

## Actual CDR diagnosis completed, electrical rejection remains

Existing nominal capture readback [41223527977](https://github.com/Melihakbulut221/nssoc/actions/runs/41223527977) completed successfully for both cases. All2991 original archive members were authenticated; original electrical REJECTED verdicts replayed exactly. Each case includes4590 interpolation queries and1530 native settling windows. Native row/gzip files remain exclusively in cloud releases/artifacts. No new analog simulation was performed by readback.

Complete116-file44,179,088-byte proof imported from514863b3debfe8b76116e91e778cad272157cf3a under docs/evidence/cdr-current-eight-drain-wave-readback-terminal-41223527977/. Receipt SHA614198507a27592652ecaba65202e21dc9f3d88e31631f0ab2cc1cf492382b09. Compact same-row witness JSONs and original complete logs are preserved.

Both nominal original captures completed113475rows/1152columns with ngspice0 and no diagnostics, but failed four selector HBT minVCE gates plus sampler/XOR delay/margin and phase/current gates. Hot cases additionally fail A/B slave hold HBT headroom. Original rejects remain rejects.

Do not blindly raise gain output common-mode: actual gain HBT max-VCE margin is only25.470mV, while selector61 needs about58.75mV recovery. Actual native gain pulldowns are w4/l5um, whereas checked-in v57 text says l7.4um; trace the applied physical source transformation before selecting a candidate. Investigate real selector C/E access geometry from same-row evidence; voltage differences alone are not causal/KCL proof. No new sizing or physical candidate accepted yet.

## Digital integration

Previous actual run41222222369 passed37positive tests and two synthesized production hierarchies. Remaining13positives and two mutants did not run because the Verilator miter requires --timing. Its complete failure proof is retained; source17033684 adds only that harness timing option and proof. Third actual run above is authoritative.

The actual receiver chain is events_v3 -> owned_rx_v2 -> recovered_x4_v5 -> shared front_x4_v1. A separate source branch codex/pcie-training-epoch-ingress-v1 is implementing stable four-phase command ownership, safe modulo epoch reuse, same-epoch/encoding PMA acknowledgments, coordinated transport reset and actual Gen12/shared-Gen3 ingress. Physical composition has eight FIFOs, four active for the selected encoding. Its tests have not yet run. Normative TS/EQ/training owner, actual PLL/CDR closed loop and soc_top serial integration remain open.

## Mainchip and final timing

Routed-view source56df4c3ba965c949f5b47d3503fd64dd0dcf8a43 passed26 source tests. Native export remains disabled until the actual terminal final-measured.odb and engine/LEF/Liberty lineage are bound. Preserve153129original instances plus1351diodes,154480total and143820nets. Old candidate Verilog is not a substitute.

Current native router has17commands; old host expects16. Only if physical gates truly pass and the host fails solely on that discrepancy, apply qualified read-only adapterc6132e91884c796bfdb5c38f9b4c1bb015ccc74d after authenticating the full capsule. Never reroute merely for the count discrepancy or relabel physical failure.

Fresh original RC/STA must retain20/4/8/8ns clocks,5percent uncertainty, threePVT and zero setup/hold/slew/cap/fanout violations. Nominal RC is not RC-min/max qualification.

Eight-hour monitor: 465 handles, inventoryv183, automatic_native_dispatch=false. PriorHTTP502 monitor issue is not claimed fixed. All future commits include [skip ci]; use nonforce CAS. Whole-root recursive tree truncates: descend nonrecursive paths and use scoped subtrees.

Detailed state: docs/evidence/cloud-active-checkpoint-20261024.json

Full serial PHY, routed-chip final setup/hold, RC-min/max qualification and production approval are not complete.
