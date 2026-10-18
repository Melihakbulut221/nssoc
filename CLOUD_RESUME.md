# Current cloud-only continuation

Latest user instruction is CLOUD ONLY; do not clone, download archives/waves, run CAD/tests or write source locally. The task workspace is empty. All edits use GitHub Git Data API; all execution uses GitHub-hosted Actions. Read the continuation document and pinned receipts; no production/PHY/timing closure claim.

## Live native jobs — preserve healthy trajectories

- CDR420 loaded-wave run39119999874, source9983399ba530ee13708be851b94dd8bd91d4d3b9. Source-delta controls passed; actual native jobs117653550444(clock_stopped),117653550461(vi_bias_off),117653550502(nominal_early),117653551229(nominal_late) verified running. Inspect exact terminal outcomes and every native safety/data/phase/VI gate. Do not restart on observation timeout.
- TX compact-column full32 wire run39112087217, source65d48a27773e891f289c6a9a534290a16623fd56. Actual native jobs117631094041(swap_leaf_select) and117631094117(nominal) verified running. Preserve original256bits and device/phase gates.

## Newly proven PD420 model chain

Physical39116999945:560DRC0/deep-flat420LVS/5faults. Planes39117334854:158planes/51logicalnets/19faults. Wire geometry39117796759:420devices/1186terminals/802anchors/111physicalconductors. Model binding39118454522:100HBT22MOS102R11MIM185finitecontacts/12controls, actual64umMOS geometry. Fresh wireRC39118996010:2507R3259C/13rawcontrols. MIM-aware capture39119282623:2530R3270C plus11nativeMIM identities/5controls. Raw audit39119562797:13wire+9intrinsic controls passed, all raw point/value/ownership and collapsed capacitance conserved. Composition39119795848:420devices+2530R3270C, exactly11MIM emitted once,19controls passed. New receipts and source-delta checks committed; old406 identities/RC must never be reused.

Loaded bench uses original256bits/time/step/loads/phase windows and transistor limits. Native14MOS tails now include sampler/select/XOR; two HBT buffer tails remain. Initialfour cases are not all10cases or full-loop/RF/body qualification. After actual nominal pass, remaining hot/cold/constants and timestep/closed-loop gates remain. If rejected, diagnose exact preserved native wave/model; never adjust acceptance gates to pass. Original retimed-sampler attenuation still unproven fixed.

## Mainchip actual routing and timing

Round4 run39115222502:0antenna/0DRTDRC/0criticaldisconnected. FreshRCX/STA39117700521 completed with REAL VIOLATIONS: slow/typ/fast setup9687/7650/3698, hold4/13/51; setupWNS-20.619253/-10.225716/-4.959596ns, holdWNS-0.540326/-0.443744/-0.374138ns. Slew/cap/fanout remain. NominalRC, original20/4/8/8ns clocks and5%derate; no fullRCminmax/LVS/signoff.

Saved native path diagnosis39118996064 completed at784d451a74dc3568bd2e665198f9b97a48697efc. Receipt `docs/evidence/onehot-round4-path-diagnosis-20261018.json`; fullsummary asset653188146 SHA d07dbf5096fb065bf39f7a19cab8576dbb9cb7117079d5ca055dc9767c4dad3c includes firstpaths and groupcounts, archive has all reports. Worst slow clk_i path starts Ibex checked register file and a long combinational cone. Worst fast PCIe path starts replay tail[0], includes weak high-cap gates1813410/Y(nor2b_1,.367385pF,1.319135ns) and1857249/Y(nor3_1,.343576pF,2.043263ns); full instance prefix $abc$1804206$auto$blifparse.cc:397:parse_blif$. Worst hold starts pcie_rx_valid_i to slice1192852. Original waveform/path evidence retained.

Next mainchip action: select actual data-path loads from all saved native reports and prepare a source-bound positive-buffer/drive repair with native geometry/logic controls, actual reroute, fresh RC and all-corner timing. Existing `prepare_cloud_critical_load_eco.py`/`run_cloud_critical_load_eco.py` demonstrate protected placement, exact net/master/fanout checks, positive-buffer equation proof, selected guide merge and reroute; they bind an OLD113791cell candidate and MUST NOT be run unchanged. Current route has141654original+3384antenna instances. CurrentRCX controller restores the authoritative full new source chain. Keep original constraints and evaluate hold regressions too.

Full serial Gen3x4 PHY, full routed PHY/mainchip integration and final setup/hold remain OPEN.

This commit launches onehot-load-prepare-cloud.yml: top50 measured weak data outputs in exact round4 slow native report, positive buf16 isolation, original145038cell geometry fixed, native legalization/equation proof and actual inversion control. This is preparation only; route/RC/allcorner setup+hold still required. Original source chain is revalidated before mutation.

Actual PD420 loaded39119999874 completed: nominal early/late device gates nowPASS(all100HBT/22MOS), but sampling failed and earlyphase wrong. Both actual fault controls detected. Pinned `cdr-hybrid-v2-full-wire-rejection-20261018.json`. This commit launches cdr-hybrid-v2-path-review-cloud.yml to reproduce failures and quantify original distributed inputs/loads without resimulation.

50buffer preparation39120628517 actually placed and legalized50buf16, preserved145038original cell geometry and native pin/NDR/PG topology; stopped because Yosys was absent for logic controls. Failed evidence preserved; no timing or logic acceptance. This commit launches onehot-load-logic-cloud.yml to restore the SAME candidate (no regeneration), install original pinned OSS CAD suite2026-08-04, prove native controls+actual netlist and inversion. Next route only after proof.

Saved50buffer logic continuation39121253733 PASSED: retained101006nonbuffer cells,34298→34348positive buffers, original macro/state equations, allnative controls and actual buffer inversion rejection. CandidateODB ef4a2cd71dcb448a104b2abacaf6a44848e3342b1ac0b23461ad926070a116ae; NL547eee3ac9cf503723f78b985f87841c2bde5277808f8716d0b6459bac55a62a. This commit launches onehot-load-route-cloud.yml for actual global+detail reroute, antenna/pin checks, freshRC and3cornerSTA, plus all145088candidatecells/topology/geometry preservation. No timing improvement claimed yet.
