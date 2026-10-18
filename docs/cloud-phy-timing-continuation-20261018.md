# Cloud-only continuation state

All work stays in GitHub-hosted jobs and releases. The local workspace remains empty. Do not restore a local checkout, waveform or CAD outputs. The active goal remains complete serial PCIe Gen3 x4, routed PCIe/Ethernet mainchip and final setup/hold; none is closed by this checkpoint.

## Active computations at this checkpoint

- Mainchip detailed routing: run 39084569446, source 92c6161af3fbb040ce6433ccae32ee614e6db1ab, native job 117548333285. This starts from exact zero-overflow GRT 39082708488 and revalidates original source/boot/protocol/logic proofs. Do not restart while live. Earlier 39084143703 stopped before the router at a missing optional configuration key; its failure is retained, and the corrected controller uses the same native false default as GRT.
- CDR v3 native interface binding: run 39085138687, source 175ff17206813a27926c1a5ebe90780c3bc82714. New physical source 39084708980 passed; this binds new native IDs before fresh RC. Do not reuse v2 native IDs or extracted wire model for the changed geometry.
- TX v5 full-wire path review: run 39084981409, source 36f659124c17dfbb818b089c064d0f53604a5d2b. It reads the original failed capture, reproduces every original gate, then localizes the 32:1 stage and eight HBT failures. No new transient is running for this review.

## Completed physical progress

- Mainchip targeted repair 39080594759 retained all 97622 original logic cells. Slow setup8037/WS-5.54096ns; fast setup663/WS-0.901378ns; fast hold24/WS-0.391465ns (three r2r hold failures). These are placement estimates, not final timing.
- Mainchip GRT39082708488 completed: 141375 routed nets, zero final overflow, original native NDR preserved, 20 SRAM macros. Source 1eed365029e07ccc65680e5e30a2adb3e46c116d. See `replay-onehot-global-route-result-20261018.md` and its pinned full receipt. DRT, extracted STA and physical signoff are still required.
- CDR v3 physical39084708980 completed: all560 DRC categories pass; deep/flat LVS each match394 devices without extraction diagnostics; five intentional faults rejected. Source735f37517a12c8e651312d1bff0f7216ef000bc7. The actual candidate adds23 TopMetal2 supply shunts and569 native via stacks. Region-union checks preserve every old drawing and all device layers. It is not an electrical pass. See `cdr-v3-supply-overlay-20261018.md` and `evidence/cdr-retimed-parent-v3-physical-pass-20261018.json`.

## Terminal electrical failures and diagnosis

- CDR v2 whole MIM-aware loaded39081843889 FAILED both nominal cases. Early sampler wrong counts100/277/345/365; late133/84/347/349, each765 samples per sampler. Seven HBT active-VCE failures per case. Fault controls passed detection, not nominal acceptance. Full failure receipt is `evidence/cdr-v2-full-wire-rejection-20261018.json`.
- CDR v2 path review39083732157 completed both cases and reproduced original counts/margins and every HBT minimumVCE from full captures. Native select-tail emitters on AVSS rise to approximately0.229/0.234V above external return; select inputs already have weak swing. This motivates v3 real supply reinforcement but is not proof that all defects will be fixed. See `evidence/cdr-v2-path-review-pass-20261018.json`.
- TX full-wire39067769686 completed and FAILED:227/768 wrong-sign samples; level_4 and final interfaces fail; eight HBT VCE failures. Compact PVT passes cannot replace this physical-wire failure. See `tx-v5-full-wire-rejection-20261018.md`.
- PLL refined full1us capture39078674197 completed and FAILED the fixed800–900ns100ppm gate (135.380ppm; later900–1000ns89.850ppm). No native process/checkpoint remains to resume. Do not cold-rerun unchanged parameters or substitute overlapping windows. See `pll-c8-half-full-capture-20261018.md`.

## Required next work

1. Inspect native DRT39084569446 only when terminal. Preserve all native failure reports, zero routing-DRC/antenna/disconnected-pin gates and exact source linkage. Then perform actual route connectivity/geometry/LVS and extracted all-corner timing; no inherited placement metric is final evidence.
2. After v3 planes pass, regenerate whole wire inputs from v3 native geometry and reference planes. Bind all394 intrinsic devices, capture full MIM-aware RC with actual new counts, audit native values/identities/matrix conservation, compose once per intrinsic MIM and re-run unchanged loaded nominal gates. Successful v3 DRC/LVS does not permit reusing v2 RC or declaring electrical success. Then PVT/convergence and native full-loop integration remain.
3. Inspect TX path-review terminal output; use the actual failed level_4/final paths and HBT terminal voltages to select physical repairs. Preserve raw capture and all original acceptance thresholds.
4. Extend PLL MIM semantics from local windows to complete clock RC before adopting loop changes. Full serial PHY includes recovered-clock CDR/PLL, all x4 lanes and real mainchip/analog-pad links; none is implied by the external-clock phase detector or digital mainchip route.

The full serial PHY, physical mainchip integration, final extracted setup/hold and manufacturing qualification remain open. Never use green workflow completion alone as acceptance.
