# Cloud continuation — checkpoint v182

Updated: 2026-10-31T17:09:01.877873+00:00

The user's latest instruction is cloud-only execution. All RTL tests, simulation, CAD and numeric/native processing run on GitHub. Never download native archives, models, ODB/GDS or waveforms locally, including RAM. Source authoring and API coordination use memory only. The local workspace and project temporary paths are empty; no local CAD process is running.

## Preserve existing running work

- Mainchip routing: [41211382427](https://github.com/Melihakbulut221/nssoc/actions/runs/41211382427), source ddc1cbddf68096c5e976bf9acda5c5fb0168c5b9; branch codex/mainchip-net459-diode-prune, release 429993235. Do not restart because redirected logs are quiet. This is the packet-interface SoC, not full serial PHY integration.
- Loaded CDR matrix: [41218657461](https://github.com/Melihakbulut221/nssoc/actions/runs/41218657461), source 84b8b591e10be32716947c8d6b079fd7a21ce18d. All eleven case/preparation releases are already reserved; do not recreate them. Ten original cases, two-job concurrency and original electrical limits remain unchanged.
- Shared serial receiver RTL: [41222222369](https://github.com/Melihakbulut221/nssoc/actions/runs/41222222369), exact source 64d31863ad2f5cd59483251dbe1dad8e7069c44e; reserved release 430065437. Read the actual terminal result before claiming any RTL test total.

See the immutable snapshot for exact live job status at this checkpoint; it is not a completion claim.

## Genuine CDR electrical failures

Nominal early and late completed with ngspice exit 0, no numerical diagnostics, and complete 113475-row / 1152-column captures. Both failed original electrical acceptance. HBT selectors 61/62/115/116 have minimum active VCE below 0.4 V; sampler/XOR margins and delays, phase output and VI current also fail. Native waveforms stay in cloud releases. Both complete JSON/log proof subtrees are imported with exact receipts; original rejection is preserved.

Fresh RC remains the verified 500-device / R24356 / C15566 composition from run 41213815773. Do not substitute older reduced node IDs or captures.

The readback adapter branch is codex/cdr-current-eight-drain-wave-readback. Initial source run 41222200293 passed its numerical/provenance controls, including six native-row witness test methods, but failed the log-preservation job; readback was skipped. The workflow repair and its new source run are recorded in docs/evidence/cloud-collector-recipes-20261029/nominal-rejections-and-cloud-only-v182.json. Actual native capture replay has not been accepted. Readback authority remains disabled until independent review, complete hosted source controls and empty exact-source destination releases.

## Mainchip connectivity and timing

Routed-view source 56df4c3ba965c949f5b47d3503fd64dd0dcf8a43 passed all 26 synthetic controls in run 41221893021. Full proof is 7ea43fda5824e2460d4cec2e4db3f5f106027f62; the earlier fixture failure is also retained. This verifies source functions, not actual routed-chip export or timing.

Native export is unconditionally disabled until an independently authenticated terminal candidate is bound. Keep the original 153129 instances plus 1351 diodes, totaling 154480, and 143820 nets. Old candidate Verilog lacks inserted diodes. Only admitted work/bulk-postdrt-antenna/final-measured.odb may feed fresh connectivity export and RC/STA.

The current native route sequence has 17 commands while the old host expects 16. If actual physical gates pass and only this host expectation fails, apply the separately qualified read-only admission c6132e91884c796bfdb5c38f9b4c1bb015ccc74d after full capsule authentication. Do not reroute just for this bookkeeping mismatch; do not reinterpret a physical failure.

Keep 20/4/8/8 ns clocks, 5% uncertainty, three PVT corners and original zero-violation setup/hold/slew/cap/fanout gates. Nominal RC is not RC-min/max qualification.

## Digital integration scope

The new actual consumer chain is events_v3 -> owned_rx_v2 -> x4_v5 -> front_x4_v1, sharing four complete recovered-record CDC paths. First RTL run 41221205033 stopped on a Yosys escaped-name checker defect after elaboration, before cocotb. Its full failure proof is retained. The corrected source and current run are above. Planned test counts are not passing results. Training ownership, closed-loop analog operation, full serial PHY and mainchip serial integration remain open.

Five accidental generic push runs were canceled and retained in the monitor inventory; all future source commits must include [skip ci]. The original router and CDR matrix were not canceled.

Eight-hour monitor: 461 handles, inventory v182, automatic_native_dispatch=false. The earlier HTTP 502 monitor issue is not claimed fixed.

Detailed state: docs/evidence/cloud-active-checkpoint-20261024.json
Immutable snapshot: docs/evidence/cloud-collector-recipes-20261029/nominal-rejections-and-cloud-only-v182.json

Full serial PHY, final routed-chip setup/hold, RC-min/max qualification and production approval are not complete.
