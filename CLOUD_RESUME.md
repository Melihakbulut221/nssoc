# Current cloud-only continuation

Read [the authoritative continuation](docs/cloud-phy-timing-continuation-20261018.md). All CAD, simulations, source and artifacts stay on GitHub. Local task workspace is empty; no local CAD processes.

Mainchip round4 run39115222502 passed 0 antenna / 0 DRT DRC / 0 critical disconnected. Exact-source RCX and routed STA run39117700521 completed; actual timing DID NOT CLOSE. Slow/typ/fast setup counts9687/7650/3698 and hold4/13/51; setup WNS-20.619253/-10.225716/-4.959596ns, hold-0.540326/-0.443744/-0.374138ns. Slew/cap/fanout remain open. Source378b1fd258c51ed1eaa8200e6f746cd409b0a29a and pinned receipt `docs/evidence/replay-onehot-round4-routed-sta-result-20261018.json`. Next restore detailed timing/path reports in a GitHub-hosted diagnosis job; preserve exact constraints and repair actual path causes. Nominal RC only; no RCmin/max qualification or post-route LVS acceptance.

CDR420 physical39116999945, planes39117334854, wholewire inputs39117796759 and native model binding39118454522 PASSED. Binding source94789e90690b45b4a2ed643af3ea262bd2d5d041, receipt `docs/evidence/cdr-retimed-hybrid-v2-binding-pass-20261018.json`: all420 devices/1186 terminals and12 corruption controls, including actual64um MOS. Next fresh MIM-aware RC capture/audit/composition and original loaded waveform gates. Actual802 anchors/111 physical conductors; never reuse406 device IDs or old RC counts. Model conversion is not waveform acceptance.

TX fullwire run39112087217 remains in progress; preserve nominal and swapped-select trajectories. Full serial PHY, retimed sampler attenuation, closed loop, qualified RC and final setup/hold remain OPEN.

This commit launches `onehot-round4-path-diagnosis-cloud.yml` (restore exact native path reports only) and `cdr-retimed-hybrid-v2-rc-cloud.yml` (fresh420 wire RC and all13 raw corruption controls). Inspect exact handles and results before next ECO/MIM composition. All execution cloud-only.

Fresh wire RC39118996010 passed2507R/3259C/111conductors/802points and all13 corruption controls. Pinned v2 RC receipt committed; this commit launches cdr-hybrid-v2-mim-parent-rc-cloud.yml to capture actual11 MIM masks and exact bottom access points, followed by raw22controls and composition19controls. No loaded-wave acceptance yet.

Exact routed path diagnosis39118996064 completed: slow worst mainclock path starts Ibex checked register file through a long combinational cone; fast worst PCIe replay tail path has multiple heavily capacitive weak gates/buffers; worst hold starts pcie_rx_valid_i. Original20/4/8/8ns constraints unchanged. Detailed source reports pinned in onehot-round4-path-diagnosis-20261018.json. Next actual routed repair must address electrical loading/logic depth and hold branches, preserve equation proof and re-extract RC after routing.

MIM-aware capture39119282623 passed2530R/3270C and exact11native MIM identities/5corruptions. This commit launches cdr-hybrid-v2-mim-parent-audit-cloud.yml with unchanged13wire+9intrinsic raw fault controls. New binding helper uses only420 native IDs. Next exact-once intrinsic composition and original loaded waves; no electrical acceptance yet.

Native MIM-aware raw audit39119562797 passed all22corruptions and exact2530R3270C conservation. This commit launches cdr-hybrid-v2-mim-composition-cloud.yml for one intrinsic model per native capacitor and all19composition controls. After pass, adapt original loaded-wave bench with new420/100HBT22MOS identities, 64umMOS support, two remaining HBT buffer tails and14MOS tails includingselect/XOR; preserve all timing/phase/safety gates and native physical collector references.

Composition39119795848 passed420devices/2530R3270C/all19controls, with11MIM emitted exactly once. This commit launches cdr-hybrid-v2-mim-loaded-cloud.yml: nominal early/late plus stopped-clock/VI-bias-off, original256bits/34ns/step/phases/loads/safety gates unchanged. New actual100HBT22MOS/14MOS tails/2HBT buffer tails. Follow live native jobs; preserve them. All10cases remain required after this initial regression screen; no fullCDR/PHY acceptance from composition.
