# Cloud-only continuation state

All execution, CAD outputs, native waves and source changes remain on GitHub. The local workspace is empty. Do not clone or restore artifacts locally. The goal remains complete serial PCIe Gen3 x4, routed PCIe/Ethernet mainchip and final setup/hold. None is closed by this checkpoint.

## Current native jobs

- Mainchip detailed routing39084569446 (source92c6161af3fbb040ce6433ccae32ee614e6db1ab, nativejob117548333285) is live. Never restart while live. It restores exact zero-overflow GRT39082708488, preserves original20/4/8/8ns clocks,5percent derate,20SRAM and native NDR. Final route/antenna/disconnected-pin gates must pass before independent route geometry/LVS and extracted STA. Earlier39084143703 stopped before routing on an optional config key; rejection is retained.
- TX v5 original-placement return64 physical39086629991 (source671f86f8d41fafc474ecb879ba4438ced28c1ff7) completed successfully: zero DRC markers/all560categories, deep/flat1674device LVS, five physical faults and exact six-rectangle geometry delta with three corruption controls. Fresh full RC extraction39086995085 (source0a8561ab56d5fe2aa3938682457fd0db2e1f4168) is live. See tx-v5-return64-physical-candidate-20261018.md and evidence/tx-v5-return64-physical-pass-20261018.json. Electrical acceptance remains open.
- CDR loaded run39086822540 (sourced88b98d3d0b52680743ac47ea6e9de1c360bc8c3) is live with four native jobs117555099185/117555099198/117555099217/117555099220. The cdr-mim-loaded-v3-cloud workflow runs the original early/late nominal cases plus stopped-clock and VI-off controls against the newly composed actual v3 model. Do not duplicate the live run. Syntax preflight passed; native electrical results are pending. All thresholds and256-bit stimuli are unchanged; every394device9979R7761C element is retained. Nominal failures must remain failures.

## Completed CDR v3 chain

Physical39084708980:23 actual TopMetal2 supply shunts,569via stacks; all560DRC categories pass; deep/flat394device LVS and five deliberate faults pass. Full flattened drawing delta is controlled. Native planes39085138687:158planes51nets1134terminals19faults. Whole-wire inputs39085392184 and native binding39085569056 pin actual v3 native IDs and dimensions.

Wire-only RC39085569087 is diagnostic only. MIM-aware capture39085974150 contains9979R7761C,11native MIMs,111components776points, five capture fault controls. Strict raw audit39086426677 passes native resistor identity/value, per-point C attachments, collapsed C conservation and22controls. Complete composition39086629993 passes15controls, preserves every wire token and binds each native MIM once. Full receipts under docs/evidence pin summaries/manifests and original output hashes. This is not RF/body PEX qualification, recovered-clock CDR or loaded-wave acceptance. Do not reuse old v2RC or native IDs.

## Mainchip completed and still unclosed

Targeted39080594759 retains97622logic cells. Slow setup8037/WS-5.54096ns; fast setup663/WS-0.901378ns; fast hold24/WS-0.391465ns including3r2r violations. These are placement estimates only. GRT39082708488 routes141375nets with zero final overflow and preserved NDR. Detailed routing and actual extracted final all-corner setup/hold are still pending.

## Preserved electrical failures

- CDRv2 loaded39081843889 failed both nominal cases: early sampler wrong100/277/345/365, late133/84/347/349 of765samples each; seven HBT active-VCE failures per case. Original fault detection passed. Full-wave review39083732157 reproduced every metric and found select-tail return rise about0.229/0.234V and already weak selector inputs. V3 supply reinforcement is an actual experiment, not an assumed complete cure.
- TX full-wire39067769686 failed227/768wrong-sign samples, level4/final interfaces and eight HBT VCE gates. Full-wave review39084981409 reproduced original results. Physical paths39085786545 maps six failures to final f and two to p8_7; final tail emitter return rise about0.172V with shortest raw return paths16.18605/16.22470ohm. Shortest path sums are not effective resistance. Do not reuse old high3/tight return64 models.
- PLL full1us39078674197 failed original800-900ns100ppm acquisition gate at135.380ppm; later900-1000ns89.850ppm cannot replace it. No native process/capsule remains. Local MIM-window capture is not complete clock RC.

## Required next work

1. Inspect terminal DRT once available; preserve failures and original zero DRC/antenna/disconnected-pin gates. Verify route logic, geometry/LVS, complete RC and extracted all-corner timing before acceptance.
2. Inspect v3 loaded original nominal/fault results, preserving raw waves. Diagnose remaining failures with native terminal data; then original PVT/convergence and actual recovered-clock loop integration remain.
3. Inspect TX return64 physical result and exact six-rectangle delta. If successful, regenerate native interfaces/device ownership and entire RC/composition before original loaded256-bit test.
4. Extend full PLL/clock MIM-aware RC and correct original acquisition failure. Full serial PHY requires actual clock distribution, recovered-clock CDR, all x4 lanes, analog pads/ESD and real mainchip links. External-clock PD tests or digital route alone do not prove this.

No goal completion, qualified PEX, final timing or manufacturing approval is claimed. Green workflow status alone is insufficient.
