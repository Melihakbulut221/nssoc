# Cloud-only continuation state

All work stays in GitHub-hosted jobs and releases. Do not restore a local checkout or native outputs. The active goal remains complete serial PCIe Gen3 x4, routed PCIe/Ethernet mainchip and final setup/hold; none is closed by this checkpoint.

## Current computations and terminal outcomes

- Mainchip exact onehot critical-branch repair: run 39080594759, source ca47b86ea376a8404c4d8ed95baff292748c3ba6, native job 117536552310. Nine observed internal data buffers only; original periods, 5% derate, all-corner baseline, source proofs and equation proof retained. Review new counts/slacks and logic before adoption. Do not restart a live job.
- CDR v2 real full-wire loaded screen: run 39081843889, source 34cc19546680b2662983355e0241a324cc66adb4. Jobs 117540291525 (nominal early), 117540291526 (nominal late), 117540291431 (stopped clock), 117540291517 (VI bias off). Model SHA256 96ddeb52f12e3efc40046b228cb5b3d45cb4af3e7776e5f338eaa65421fc3f2d. All 394 devices, 8956 R and 7079 C are physical, unscaled. Read actual pass/fail gates after captures; successful fault detection does not imply positive-case acceptance.
- TX full-wire nominal run 39067769686/job 117498996909 has now completed and FAILED its electrical gates: 227/768 wrong-sign samples; level_4 and final interface checks fail, with native HBT VCE failures. It is no longer a live process. See `tx-v5-full-wire-rejection-20261018.md`; do not rerun unchanged or substitute compact PVT passes.

## Newly completed evidence

- CDR v2 layout 39079610383: 560-category zero-marker DRC, deep/flat 394-device LVS and five geometry/reference faults.
- Native interfaces 39080139959: 158 planes, 51 nets, 19 faults; whole wire inputs 39080362471: 1134 terminals, 111 conductors, 776 points.
- Native model binding 39080782016; wire-only baseline 39080782022 (diagnostic only).
- MIM-aware capture 39080982948; strict raw audit 39081441241 (13 wire + 9 intrinsic faults); composition 39081620727 (15 faults). The earlier stale-helper rejection 39081203572 is preserved and corrected only by binding the helper to v2 evidence.
- PLL full refined-step capture 39078674197 has finished; it is no longer live and is not a checkpoint to resume. Actual 1 us capture still fails the 800–900 ns 100 ppm gate. See `pll-c8-half-full-capture-20261018.md` and its full receipt. Do not call the green workflow an acquisition pass or cold-rerun unchanged parameters.

## Required next work

Review the actual TX level_4/final distributed paths and failed HBT headroom before the next physical change; preserve the complete raw capture. Review CDR v2 loaded results; repair actual geometry/circuit if data/device gates fail. If nominal cases pass, complete PVT, convergence and native full-loop integration without relaxing gates. Extend the PLL's MIM mask semantics from local windows to complete native clock RC, then evaluate actual loop changes. Continue mainchip repair/routing only from the exact new evidence; retain original failures and all source/native boot/protocol bindings. Full serial PHY, physical mainchip integration and final extracted timing remain open.
