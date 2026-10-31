# Cloud continuation — checkpoint v181

Updated: 2026-10-31T16:34:13.624020+00:00

All engineering, RTL tests, simulation and CAD run on GitHub. Do not download native archives, models, ODB/GDS or waveforms locally, including RAM. Local source authoring and API coordination use memory only. The workspace and project temporary paths are empty; no local CAD process is running.

## Active cloud jobs

- Mainchip routing: [41211382427](https://github.com/Melihakbulut221/nssoc/actions/runs/41211382427), source ddc1cbddf68096c5e976bf9acda5c5fb0168c5b9, branch codex/mainchip-net459-diode-prune, release 429993235. Keep this run. It clears 608 owned stale wires and routes under the original physical gates. Do not restart merely because its redirected log is quiet.
- Loaded CDR matrix: [41218657461](https://github.com/Melihakbulut221/nssoc/actions/runs/41218657461), source 84b8b591e10be32716947c8d6b079fd7a21ce18d, branch codex/cdr-drain-m1-loaded-electrical. Same-run source controls and preparation passed. Two nominal cases are running; eight wait under the original two-job concurrency limit. All eleven releases are already reserved against this exact source; do not create them again.

The matrix preserves the original ten cases and analog limits. Preparation passed input binding and vector checks but did not execute OFF operating point or transient simulation. It is not electrical or PHY acceptance.

## Durable preparation evidence

Imported proof 41a8c4d6ca9ed4a1d97f80a8066200f3eea53fd5: 51 files, 9,706,031 bytes, receipt SHA256 84760ccb2e176b133f6e046895706ee70cb19a1696743d12cbedcf533bbdbb81. Path: docs/evidence/cdr-current-eight-drain-loaded-preparation-41218657461/

It preserves three prerequisite/preparation logs, emitted JSON and the actual publication receipt. Native archives remain in GitHub releases. This readback authenticates derived JSON/logs; it does not independently stream-verify the native archive.

Fresh RC run 41213815773 and collector 41217092264 passed. Loaded input has 2,874 native files and a fresh 500-device composition. Current drains map to component 17/cluster 28/$131 or component 61/cluster 135/$699. Do not substitute old reduced node IDs or old captures.

## Mainchip admission and timing

The running router is the packet-interface SoC; it does not yet integrate the full serial PHY. Externally supplied link/training status is not a completed serial link.

The new native sequence has 17 commands while the original host expects 16. If all native physical gates pass, authenticate the full original capsule and apply separately qualified read-only admission c6132e91884c796bfdb5c38f9b4c1bb015ccc74d. Run 41217482957 passed 373 controls; complete proof ae4e05018e4f88943b45e56b76daf620ca1b9497 is already imported. A host expectation mismatch alone is not grounds to reroute; a physical failure cannot be relabeled.

Only an admitted work/bulk-postdrt-antenna/final-measured.odb can feed the next stage. Actual starting design has 153,129 instances plus 1,351 inserted diodes, totaling 154,480. Old candidate Verilog lacks those diodes. Export and verify current connectivity, DEF and Verilog before fresh RC/STA. Keep 20/4/8/8 ns clocks, 5% uncertainty, three PVT corners and original violation gates.

## Source work

- codex/pcie-shared-serial-front-v1: shared recovered-record front with actual v5/owned/events consumers and independent hosted RTL tests; not yet qualified.
- codex/mainchip-routed-view-admission: routed view export, diode load and parasitic annotation checks. Source controls only until the original router finishes and its candidate is authenticated.

Full serial PHY, closed-loop analog operation, mainchip serial integration, final setup/hold, RC-min/max qualification and production approval remain open.

Eight-hour monitor: 446 handles, inventory v181, automatic_native_dispatch=false. Earlier HTTP 502 issue is not claimed fixed.

Detailed state: docs/evidence/cloud-active-checkpoint-20261024.json
Immutable snapshot: docs/evidence/cloud-collector-recipes-20261029/preparation-and-cloud-only-v181.json
