# Cloud continuation — checkpoint v185

Updated: 2026-10-31T18:02:50.720281+00:00

The user requires cloud-only work. All tests, simulation, CAD and numerical/native processing run on GitHub. Never acquire native archives, models, ODB/GDS, raw waves or native-frame gzip locally, including RAM. Source/API derived JSON/text coordination uses RAM only. Local workspace and project temporary prefixes are empty; no local CAD process runs.

## Preserve four original/authorized runs

1. Mainchip router [41211382427](https://github.com/Melihakbulut221/nssoc/actions/runs/41211382427), source ddc1cbddf68096c5e976bf9acda5c5fb0168c5b9, release429993235. Preserve original job; redirected quiet logs do not justify restart. Packet-interface SoC only.
2. Original ten-case loaded CDR [41218657461](https://github.com/Melihakbulut221/nssoc/actions/runs/41218657461), source84b8b591e10be32716947c8d6b079fd7a21ce18d. All11case/preparation releases already reserved. Preserve every terminal case and any stillrunning case.
3. Actual training transport RTL [41227114547](https://github.com/Melihakbulut221/nssoc/actions/runs/41227114547), sourcef2e452405f87aa079f79f604604294138fcfe261. Separate empty exactsource release430096033, tag cloud-results-41227114547-1-pcie-training-epoch-ingress-v1. One dispatch, no retry. Planned110positive tests/6compiled mutants/4hierarchies are NOT yet passed results.
4. Readonly current CDR RC collector [41227192284](https://github.com/Melihakbulut221/nssoc/actions/runs/41227192284), sourcebf95941c21a19221136c707843e7983648c3ae1b. Separate empty exactsource release430096504, tag cloud-results-41227192284-1-cdr-current-access-rc-readback-nominal_late. One dispatch, existing original nominal_late archive only. No new analog simulation or layout edit.

Exact job observations are in docs/evidence/cloud-collector-recipes-20261029/actual-training-and-access-rc-dispatch-v185.json; snapshots are not completion claims. Do not recreate reservations, modify original acceptance limits or discard failures.

## Genuine shared-front RTL result integrated

Run41223635170/source17033684f3dfd0c760ac7cf64d2e1dc1a4b2fdb0 passed50named positive RTL tests,0positive skips; two compiled semantic mutants detected by exact independent assertions; two production top hierarchies each1sharedfront/4aligners/4CDC/4FIFO. Full proof1006eae3d1198e12ed1d3f22e3eaf800be13a788 remains imported.

Rootv184 commit19fd799e4afa60f50b9ae6b05d522ddfe9c574cb integrated12qualified source/docs files, with all17existing protected dependencies matching. Candidate-specific workflow was not copied: runner stays on its dedicated execution branch; root runtime acceptance is not inferred. Chain: events_v3 -> owned_rx_v2 -> recovered_x4_v5 -> sharedfront_x4_v1. soc_top serial hookup remains open.

## Training command and ingress

Root+peer reviewed the actual four-phase command mailboxes and Gen12/sharedGen3 ingress. Safe modulo epoch reuse requires all acknowledgments low. Epoch abort flushes old records. Same-edge STARTUP completion/reset false-success was fixed; exact edge and WAIT_LOW stopped-clock tests added. Physical composition8FIFOs,4active for the selected encoding.

Original corrected source2a69d010 passed16source controls. Activationf2e45240 passed21source controls plus17release/4waiter refusals in41226756847; full proof0f4b9c5fee9ea11ac68a69504a3aac4f48ade5a5 imported. RTL and both oracles remain byte-identical to reviewed2a69d010. Actual dispatch above requires exact approved_source, dedicated job, successful sourcecontrols and separateemptyrelease. No normative TS/EQ/LTSSM or fake link-up implemented; physical CDC and full training handoff remain open.

## CDR current evidence and physical next step

Actual existing nominal readback41223527977 authenticated2991archive members and replayed original electrical REJECTED verdicts exactly, including4590queries and1530native settling windows percase. Full116file44,179,088byte proof retained. Native frames remain cloud-only.

Actual gainpulldown l5um is the deliberate v59 cd_shunt nativePCell/reference transform of oldl7.4um; source audit55db15f41be2779ec2e9e9e0b83d95f970f74f0c retained. GainmaxVCE margin25.470mV is below failedselector recovery need58.75mV. Do not blindlyraise gaincommonmode.

Four actual access nets are components17/19/61/63, native28/38/135/136. Current eightdrain straps only alter boundedMOSdrainM1/M2 access. The new readonly collector preserves all current R/C and boundarycaps, exact device/anchor/geometry identities and rawnative nodecoordinates. Its76pairwise1A mathematicalDC evaluations are not real device currents, RF/timing, EM or causality proof. Missing/unknown coordinates remain explicit.

First collector sourcefca2396 failed sourcecontrols41226430440 because numpy was imported beforedependencyinstall. No numerical/native input was acquired. Full failure proof imported. Explicit lazyloader402ecb3a preserves exact solverbody5346f0aef7ee3ab8ad6b0d77a0a79ee8e54e7b5ec9585edf09e487d062008993. Corrected controls41226700901 and finalactivated controls41226950039 passed12RCmethods,6samplermethods, inherited10groups/86refusals/4lifecycle and publication7positive/33refusals/4lifecycle. Full proofs81c7cefd... and214af4d9... imported. No algorithm/limit drift during authority activation.

Use the actual collector output to select real geometry changes, then regenerate physical verification and original loaded cases. No new physical correction has yet been accepted. Remaining eight original nonnominal case proofs are being preserved separately by loaded_admission_review on codex/cdr-eight-drain-matrix-terminal-preservation. Missingnative-result/solvererror/expected negativecontrols must be classified from full evidence, not assumedPASS.

## Final routed-chip timing

After actual router terminal authenticate all17commands/full capsule and final-measured.odb. Qualified stale-wire adapterc6132e91884c796bfdb5c38f9b4c1bb015ccc74d only addresses oldhost16-vs17 bookkeeping after genuine physicalsuccess. Never relabel physical failure or reroute just for the count discrepancy.

Routed-view26source controls passed but actualexport remains disabled until candidate/engine/LEF/Liberty lineage is bound. Keep153129original+1351diodes=154480instances and143820nets. Fresh RC/STA must retain20/4/8/8ns clocks,5percent uncertainty, threePVT and zero setup/hold/slew/cap/fanout. Oldnetlist/SPEF is inadmissible; nominalRC is not RCmin/max qualification.

Monitor: 472handles, inventoryv185, every8hours, automatic_native_dispatch=false. EarlierHTTP502 issue not claimedfixed. Allcommits [skip ci], nonforceCAS. Use scoped subtrees; whole-rootrecursive tree truncates.

Detailed state: docs/evidence/cloud-active-checkpoint-20261024.json
Immutable receipt: docs/evidence/cloud-collector-recipes-20261029/actual-training-and-access-rc-dispatch-v185.json

Full serial PHY, mainchipserial hookup, final routed-chip setup/hold, RCmin/max qualification and production approval remain open.
