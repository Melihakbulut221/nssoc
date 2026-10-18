# Cloud-only continuation state

All execution, CAD outputs, native waves and source changes remain on GitHub. The local workspace is empty. Do not clone or restore artifacts locally. The goal remains complete serial PCIe Gen3 x4, routed PCIe/Ethernet mainchip and final setup/hold. None is closed by this checkpoint.

## Current native jobs and latest terminal results

- Mainchip detailed routing39084569446 (source92c6161af3fbb040ce6433ccae32ee614e6db1ab, nativejob117548333285) remains live at this checkpoint. Never restart while live. Exact zero-overflow GRT39082708488, original20/4/8/8ns clocks,5percent derate,20SRAM and NDR are retained. Route/antenna/disconnected-pin gates, independent route geometry/LVS and extracted all-corner timing still remain.
- TX return64 actual physical39086629991 passed all560DRC categories, deep/flat1674device LVS, five physical faults and exact six-rectangle drawing delta. Fresh extraction39086995085 passed377conductors/3262probes/4774terminals and13corruption controls with116611R77471C. Composition39087377122 passed six malformed-model controls, full native-net recovery and124leg/372base binding with two endpoint controls. Full source-bound receipts are retained.
- TX loaded run39087664998 (sourcec68680dcf8d645534d9c5f9bfd1673bdf0206cb0) is live. Builder/adapter byte-equivalence preflight passed. Native full-wire nominal117557594345 and swapped-leaf fault117557594283 run the complete original34ns/256bits, actual1674device116611R77471C core and eleven clock reference/feed macros. The nominal workflow explicitly fails any original electrical gate. No nominal result or improvement is assumed.
- CDR loaded run39086822540 completed FAILURE: both nominal cases rejected, simulator exit0/no diagnostics/sources unchanged; two actual fault controls detected faults. V3 has14failed-HBT VCE gates per nominal case, versus7in v2; supply-only repair did not close the defect. See cdr-v3-full-wire-rejection-20261018.md and its receipt. Do not rerun the same transient unchanged.
- CDR v3 original-wave path diagnosis39087834710 (source85ba0c49007edc11517c00f3e9dec31f8040c519) is live. It restores full original captures only on GitHub, reproduces sampler margins/counts and all122HBT VCE minima, then records rail/terminal voltages and actual resistor paths. No new transient or weakened gate.

## Completed CDR v3 chain

Physical39084708980:23 actual TopMetal2 supply shunts,569via stacks; all560DRC categories pass; deep/flat394device LVS and five deliberate faults pass. Full flattened drawing delta is controlled. Native planes39085138687:158planes51nets1134terminals19faults. Whole-wire inputs39085392184 and native binding39085569056 pin actual v3 native IDs and dimensions.

Wire-only RC39085569087 is diagnostic only. MIM-aware capture39085974150 contains9979R7761C,11native MIMs,111components776points, five capture fault controls. Strict raw audit39086426677 passes native resistor identity/value, per-point C attachments, collapsed C conservation and22controls. Complete composition39086629993 passes15controls, preserves every wire token and binds each native MIM once. Full receipts under docs/evidence pin summaries/manifests and original output hashes. The subsequent original loaded v3 tests failed as recorded above. This is not RF/body PEX qualification, recovered-clock CDR or loaded-wave acceptance. Do not reuse old v2RC or native IDs.

## Mainchip completed and still unclosed

Targeted39080594759 retains97622logic cells. Slow setup8037/WS-5.54096ns; fast setup663/WS-0.901378ns; fast hold24/WS-0.391465ns including3r2r violations. These are placement estimates only. GRT39082708488 routes141375nets with zero final overflow and preserved NDR. Detailed routing and actual extracted final all-corner setup/hold are still pending.

## Preserved electrical failures

- CDRv2 loaded39081843889 failed both nominal cases: early sampler wrong100/277/345/365, late133/84/347/349 of765samples each; seven HBT active-VCE failures per case. Original fault detection passed. Full-wave review39083732157 reproduced every metric and found select-tail return rise about0.229/0.234V and already weak selector inputs. V3 supply reinforcement is an actual experiment, not an assumed complete cure.
- TX full-wire39067769686 failed227/768wrong-sign samples, level4/final interfaces and eight HBT VCE gates. Full-wave review39084981409 reproduced original results. Physical paths39085786545 maps six failures to final f and two to p8_7; final tail emitter return rise about0.172V with shortest raw return paths16.18605/16.22470ohm. Shortest path sums are not effective resistance. Do not reuse old high3/tight return64 models.
- PLL full1us39078674197 failed original800-900ns100ppm acquisition gate at135.380ppm; later900-1000ns89.850ppm cannot replace it. No native process/capsule remains. Local MIM-window capture is not complete clock RC.

## Required next work

1. Inspect terminal DRT once available; preserve failures and original zero DRC/antenna/disconnected-pin gates. Verify route logic, geometry/LVS, complete RC and extracted all-corner timing before acceptance.
2. Inspect completed v3 original-wave diagnosis39087834710. Select the next actual physical/bias repair from terminal data; retain the fourteen-device VCE rejection and all failed sampler gates. Original PVT/convergence and recovered-clock loop integration remain.
3. Inspect TX full-wire nominal/fault39087664998 when terminal. Compare all original gates with baseline39067769686 and use original raw terminal waves for any next repair. No compact model or same-R/C-count shortcut replaces these actual new values.
4. Extend full PLL/clock MIM-aware RC and correct original acquisition failure. Full serial PHY requires actual clock distribution, recovered-clock CDR, all x4 lanes, analog pads/ESD and real mainchip links. External-clock PD tests or digital route alone do not prove this.

No goal completion, qualified PEX, final timing or manufacturing approval is claimed. Green workflow status alone is insufficient.
