# Via-rich CDR: fresh native RC and loaded-wave handoff — 2026-10-18

All computation and evidence storage is cloud-only. Local project directory remains empty.

## Actual physical and electrical model provenance

| Stage | GitHub Actions run | Result |
|---|---:|---|
| Native full parent geometry | 39163291382 | 484 devices, 560 DRC categories with zero markers, unsimplified deep and flat LVS MATCH; original physical fault controls rejected |
| Actual interface planes | 39163773591 | 158 planes, 1394 terminals, 51 nets, 19 faults |
| Wire geometry and terminal anchors | 39163941646 | 111 independent conductors, 946 actual physical/logical anchors |
| Native PDK binding | 39164390482 | All 484 devices and 1394 terminals bound; 12 model faults rejected |
| Fresh wire-only native RC | 39164390476 | 13163 R, 10116 C; 13 original raw corruption checks passed |
| Actual MIM-aware native capture | 39164761407 | 13186 R, 10127 C, 11 actual MIM identities; five capture faults rejected |
| Strict raw RC and intrinsic audit | 39165053573 | Same actual values, points, topology and per-conductor capacitance retained; 13 wire and nine intrinsic faults rejected |
| Model composition | 39165288792 | All 484 devices, 13186 R, 10127 C; exactly one compact model per each of 11 native MIMs; 19 faults rejected |

Every stage has an immutable summary/parts SHA256 receipt in `docs/evidence/`, with the matching `cdr-retimed-via-rich-v7-*` or `cdr-via-rich-v7-*` prefix. Failed older geometry and electrical results remain retained. Increased RC element counts reflect fresh extraction of the changed actual geometry, not a reduction in electrical requirements.

## Loaded simulation being started

`cdr-via-rich-v7-mim-loaded-cloud.yml` executes nominal early/late data and actual clock-stopped/VI-bias-off negative cases. The script differs from the previous strapped candidate only in provenance/model identities and exact measured RC census. It retains original 256 bits, 125 ps UI, stimulus, timestep, solver, sample phases, 100 mV sample margin, clock-to-valid and all device operating limits. Loads remain 150 fF at each actual sampler data-pair collector and 50 fF at comparator ports. Dependency hashes and all original source-delta checks remain enforced.

This is an externally clocked loaded phase-detector screen. It does not prove recovered-clock loop lock, four-lane serial PHY interoperability, qualified RF/body PEX, mainchip timing or production readiness. Prior strapped electrical rejection remains authoritative until fresh actual waveforms establish a result. A native physical or model-conservation pass alone is not electrical acceptance.

## Measured conductor change and rejected full capture (2026-10-19)

Cloud comparison39165970043 passed exact physical-location/parameter correspondence for all484 devices and bijective native net topology. It reproduced all64 old two-terminal calculations before evaluating the new geometry. Analytic series/parallel, reciprocity, disconnected-net, increased-resistor and missing/swapped physical-identity controls passed.

| Wire-only effective DC resistance | Old range | New range | Reduction across matched paths |
|---|---:|---:|---:|
| Supply to load access | 28.437860–31.667977 ohm | 14.387278–17.332300 ohm | 45.27–49.41% |
| Load to collector access | 37.764021–40.798657 ohm | 19.509282–21.960785 ohm | 46.17–48.34% |

These unit-current linear calculations leave other terminals floating; they are not the multi-terminal operating point, actual current, transient delay, EM or RF qualification. Full receipt: cdr-via-rich-wire-comparison-pass-20261019.json.

All four original full loaded cases39165464508 terminated with native max-data warnings and were rejected before electrical waveform acceptance. Native process exit0 does not override these diagnostics. The complete four-case reports/archives are pinned in cdr-via-rich-v7-loaded-memory-matrix-rejection-20261019.json. The separate cloud stream-transport control39166618949 is running. It must verify every saved native sample before full-window streamed reruns. No tolerance, load, timestep, bit count or voltage acceptance reduction is authorized by this transport repair.
