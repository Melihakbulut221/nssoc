# Cloud continuation — checkpoint v186

Updated: 2026-10-31T18:18:20.851518+00:00

Latest user policy is cloud-only. All tests, simulation, CAD and numerical/native processing run on GitHub. Source/API derived JSON/text coordination uses RAM only. Never acquire native archives, models, ODB/GDS, raw waves or native-frame gzip locally, including RAM. Workspace and project temporary prefixes are empty, no local CAD process. Unrelated user files and original review attachments are preserved.

## Current work

- Original mainchip routing: [41211382427](https://github.com/Melihakbulut221/nssoc/actions/runs/41211382427), source ddc1cbddf68096c5e976bf9acda5c5fb0168c5b9, release429993235. Keep same run; quiet redirected logs do not justify restart. Packet-interface SoC only. Read current snapshot before reporting status.
- Actual training ingress RTL: [41227114547](https://github.com/Melihakbulut221/nssoc/actions/runs/41227114547), source f2e452405f87aa079f79f604604294138fcfe261, release430096033. Planned110positive/6compiledmutants/4hierarchies are not passed results. Same-run sourcecontrols/tool setup passed; actual terminal result must be preserved. Root37existingdependencies match,7newfiles await actualqualification.
- Four-network CDR RC readback: [41227192284](https://github.com/Melihakbulut221/nssoc/actions/runs/41227192284) SUCCESS, source bf95941c21a19221136c707843e7983648c3ae1b, release430096504. Full70file9,941,711byte proof imported from80194a3639666bb46664c6a57693ba5af6df0cfa. Original electricalREJECTED unchanged; no new analogsimulation or layout change.
- Original ten-case loaded CDR: [41218657461](https://github.com/Melihakbulut221/nssoc/actions/runs/41218657461) terminalfailure. Preserve every case, including successful expected clock-stop fault detection and pre-native vi_bias_off storage failure. Complete per-case proof pins are in the detailed checkpoint and recipe below.

## Actual CDR finding and next physical action

Readonly RC authenticated2991members, conserved24356R/15566C and7separateMIM, selected582R/454uniqueincidentC acrosscomponents17/19/61/63 (native28/38/135/136), and performed76pure-wire mathematical1A DC solves. EffectiveR selectorE-to-MOSD26.1988–26.6318Ohm; upperE-to-selectorC14.2838–14.9629Ohm. These are not actual operatingcurrent, EM/RF/timing or causalproof.

DominantDtailendpoint R2997 T003_D--T065_E.n53 is14.7788Ohm; C counterpartsR12299/R12289/R12279/R12300. Current overlay already covers the entire36umprimitive drainrail and35.6umM2. Repeating it has no established benefit. Rawrnode layerunknown and units require authentic currentGDS/L2N/PCell/anchor binding.

fresh_rc_next_audit prepares a narrow cloud-only realgeometry ownership/clearance collector before selecting any bypass. No geometrymutation authorized by this checkpoint; no resistance or waveform acceptance limits relaxed. Raising gaincommonmode blindly is also inadmissible: actual minimummaxVCE margin25.470mV is below selector recovery58.75mV.

## Original matrix classifications and cloud storage fix

Constant_one is a positiveconstant-input screen, not one of the two expectednegative controls. Its VIoffset−3.821488868mV fails unchanged2mV; current−0.996229uA passes5uA, with data/device/phase/bias gates passing. Preserve genuine electrical rejection.

Clock_stopped returned native0 and actual_fault_detected=true: expected fault detection passes within the loadedscreen scope. FullCDR/PEX/PHY acceptance remains false.

vi_bias_off failed initial16GiB storage preflight before simulation. The subsequent missingprotectedresult error is secondary. Original freebyte count was not logged; do not invent it. loaded_admission_review owns codex/cdr-eight-drain-storage-preflight-v1. Candidate investigates exact1961protected/sourceclosure sparsecheckout and disk observations before refusal. Pinned actions/checkout11bd719 automaticallysetsblob:none when sparseCheckout is provided without explicitfilter. Fullcheckout as actual failurecause is a hypothesis until measured. Keep16GiB and all electrical gates; no blindmatrixretry or deletion of required evidence.

## Completed integration and remaining boundary

Rootv184 integrated shared-front source qualified by41223635170:50named positiveRTL tests,0positive skips,2compiled semanticmutants detected,2productionhierarchies each1front/4aligners/4CDC/4FIFO. All17protected dependencies matched. Candidateworkflow not copied, rootruntimequalification not implied.

Training command/ingress uses four-phase acknowledged epoch mailboxes, both encodings,8physicalFIFOs/4active, async abort/front flush and same-edge reset fix. NormativeTS/EQ/LTSSM ownership, seed/lane/statehandoff, physicalCDC and soc_top serialconnection remainopen.

For final mainchip routing authenticate17actualcommands and final-measured.odb. Qualified stale-wire adapter only fixes oldhost16-vs17 accounting after realphysicalsuccess. Candidate retains153129original+1351diodes=154480instances/143820nets. Routed-view26sourcecontrols passed; native export remains disabled until actual candidate/engine/LEF/Liberty lineage is bound. FreshRC/STA preserve20/4/8/8ns,5percentuncertainty,3PVT, zero setup/hold/slew/cap/fanout. Oldnetlist/SPEF inadmissible; nominalRC is not RCmin/maxqualification.

Monitor inventoryv186: 472handles, every8hours, automatic_native_dispatch=false. EarlierHTTP502 issue not claimedfixed. Allcommits [skip ci], nonforceCAS; use scopedtrees because whole-rootrecursive truncates.

Detailed state: docs/evidence/cloud-active-checkpoint-20261024.json
Immutable receipt: docs/evidence/cloud-collector-recipes-20261029/actual-rc-and-terminal-loaded-matrix-v186.json

Full serial PHY, serialmainchip hookup, final routedchip setup/hold, RCmin/max qualification and production approval remainopen.
