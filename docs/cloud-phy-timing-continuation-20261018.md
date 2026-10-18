# Cloud-only continuation state

All work stays in GitHub-hosted jobs and releases. Do not restore a local checkout or native outputs. The active goal remains complete serial PCIe Gen3 x4, routed PCIe/Ethernet mainchip and final setup/hold; none is closed by this checkpoint.

## Current computations and terminal outcomes

- Mainchip targeted repair 39080594759 completed with retained-equation proof. Slow setup8037/WS-5.54096ns; fast setup663/WS-0.901378ns; fast hold24/WS-0.391465ns (three r2r hold failures). See `replay-onehot-targeted-result-20261018.md`. Run 39082708488 (source 1eed365029e07ccc65680e5e30a2adb3e46c116d) of `replay-onehot-global-route-cloud` now routes its exact ODB, with source proofs, native NDR and zero-overflow gates. It does not reuse old regional coordinates or claim final timing.
- CDR v2 real full-wire loaded screen 39081843889 has completed and FAILED both nominal cases. Early sampler wrong-sign counts are 100/277/345/365; late counts are 133/84/347/349 (765 samples per sampler). Both have seven HBT active-VCE failures. Fault-control jobs passed detection, which is not nominal acceptance. See `cdr-v2-full-wire-rejection-20261018.md` and its pinned receipt; do not rerun unchanged or relax thresholds.
- TX full-wire nominal run 39067769686/job 117498996909 has now completed and FAILED its electrical gates: 227/768 wrong-sign samples; level_4 and final interface checks fail, with native HBT VCE failures. It is no longer a live process. See `tx-v5-full-wire-rejection-20261018.md`; do not rerun unchanged or substitute compact PVT passes.

## Newly completed evidence

- CDR v2 layout 39079610383: 560-category zero-marker DRC, deep/flat 394-device LVS and five geometry/reference faults.
- Native interfaces 39080139959: 158 planes, 51 nets, 19 faults; whole wire inputs 39080362471: 1134 terminals, 111 conductors, 776 points.
- Native model binding 39080782016; wire-only baseline 39080782022 (diagnostic only).
- MIM-aware capture 39080982948; strict raw audit 39081441241 (13 wire + 9 intrinsic faults); composition 39081620727 (15 faults). The earlier stale-helper rejection 39081203572 is preserved and corrected only by binding the helper to v2 evidence.
- PLL full refined-step capture 39078674197 has finished; it is no longer live and is not a checkpoint to resume. Actual 1 us capture still fails the 800–900 ns 100 ppm gate. See `pll-c8-half-full-capture-20261018.md` and its full receipt. Do not call the green workflow an acquisition pass or cold-rerun unchanged parameters.

## Required next work

Review the actual TX level_4/final distributed paths and failed HBT headroom before the next physical change; preserve the complete raw capture. CDR v2 nominal failures are now established: map the weak select0/select1 interfaces and seven low-VCE native devices back to their actual routes and source circuit before another geometry/circuit change. Repeat full native loaded nominal validation after repair, then PVT, convergence and native full-loop integration without relaxing gates. Extend the PLL's MIM mask semantics from local windows to complete native clock RC, then evaluate actual loop changes. Continue mainchip repair/routing only from the exact new evidence; retain original failures and all source/native boot/protocol bindings. Full serial PHY, physical mainchip integration and final extracted timing remain open.
