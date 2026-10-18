# Current cloud-only continuation — 2026-10-18

All work is CLOUD ONLY under the latest user instruction. Local task workspace is empty. Do not clone, download native archives/waves, write source locally, run local CAD/tests or start a self-hosted runner. Use GitHub Git Data API for source edits and GitHub-hosted Actions for execution. Preserve healthy jobs and all original failure evidence. Do not mark the active goal complete: full serial Gen3x4 PHY, integrated mainchip routing and final setup/hold are still OPEN.

## Exact live mainchip/TX jobs

- Mainchip native50-buffer route39121691046 at3b415c02d11ac763fd081412b34234103772d347, native job117658413515. Verified in_progress. It reroutes the exactly proven candidate, checks native antenna/DRC/disconnected pins and original145088cell geometry/topology, then freshly extracts nominalRC and three cell corners. Preserve original20/4/8/8ns clocks and5%derate. Source recipe scripts/cloud_onehot_load_route.py and hw/soc/pnr/onehot_load_route_flow.py. No measured timing improvement yet.
- TX compact-column full-wire39112087217 at65d48a27773e891f289c6a9a534290a16623fd56. Verified in_progress. Preserve native jobs117631094041(swap_leaf_select)/117631094117(nominal), full256bits/34ns, all actual116611R77471C and device/data gates. No restart on polling timeout.

## Mainchip authoritative baseline

Round4 physical39115222502 passed0antenna/0DRTDRC/0criticaldisconnected with145038cells. Fresh routed nominalRC+three cell corners39117700521 FAILS real timing: slow/typ/fast setup9687/7650/3698; hold4/13/51; setupWNS-20.619253/-10.225716/-4.959596ns. Slew/cap/fanout also fail. Receipts replay-onehot-antenna-round4-result-20261018.json and replay-onehot-round4-routed-sta-result-20261018.json. Native path diagnosis39118996064 pins slow Ibex checkedRF cone, fast PCIe replay tail weak/high-cap gates and pcie_rx_valid_i hold path; receipt onehot-round4-path-diagnosis-20261018.json.

Native50 prepare39120628517 failed missingYosys AFTER exact geometry insertion; saved candidate unchanged. Logic continuation39121253733 passed native geometry/equation controls and actual buffer inversion rejection. Receipt onehot-load-logic-pass-20261018.json pins candidateODB ef4a2cd71dcb448a104b2abacaf6a44848e3342b1ac0b23461ad926070a116ae and NL547eee3ac9cf503723f78b985f87841c2bde5277808f8716d0b6459bac55a62a. Route39121691046 consumes it. Keep baseline failures; route success alone is not timing/LVS/signoff.

## Full physical PD420 remains electrically rejected

The actual PD420 physical/model chain passed: parent39116999945(560DRC/deep-flat420LVS), planes39117334854, wireinputs39117796759, binding39118454522, freshRC39118996010, MIMcapture39119282623, rawaudit39119562797, composition39119795848. Exact native100HBT22MOS102R11MIM185contacts;2530wireR3270wireC with11MIM emitted once. All receipts stay in docs/evidence.

Loaded whole-parent39119999874 FAILED original early/late sampling and early phase direction; nominal device limits passed, actual faults detected. Receipt cdr-hybrid-v2-full-wire-rejection-20261018.json. Read-only39121253725 confirms retimed input attenuation and actual large wire capacitance; receipt cdr-hybrid-v2-native-path-review-20261018.json. Standalone sampler success will NOT supersede this full-parent rejection.

## Current native sampler repair

Design rationale and all intermediate outcomes: docs/pcie-cdr-sampler-load-drive-design-20261018.md.

1. Invalid load-drivev2 run39122483815 failed native startup. Exact archived model review39123356324 confirms npn13G2 Nx1..10; Nx16 clock devices were invalid and made Csub negative. Original failure and aborted175row trajectory retained. Receipt cdr-sampler-load-drive-model-domain-rejection-20261018.json. Native model SHAae9288f885dd30fab24b07ed1e7e02e69eac9154022a0a6da576985183b0bd79. Decode archived model text Latin1, never change its bytes.
2. Split-drivev3 run39123587911 replaces each invalidNx16 with two actual separateNx8 devices:16HBT(allNx8,total128),3MOS,12rppd. Native startup fixed; all three corners768samples pass at1pF/output, zero diagnostics. Device VCE limits stillfailed. Both actual faults detected. Receipt cdr-sampler-split-drive-data-pass-device-rejection-20261018.json. Native domain controls reject sourceNx0/11/16 before simulator.
3. Headroomv4 run39123948513 changes only inputAVDDpullups length3.6→2.4um. Nominal/cold and both faults now pass all retained gates; hot_low data passes(min110.576mV,max35.469ps) but four slave HBT minima0.38608/0.38658/0.36935/0.36971V fail0.4V. Receipt cdr-sampler-headroom-hot-device-rejection-20261018.json.
4. Read-only native review39124255052 at725542c6105962c4e5f4d9b4360544720934d9db reproduces all four hot extrema and nearby original terminal/current samples. Receipt cdr-sampler-headroom-native-extrema-20261018.json. Worsthold is low-current interval just after clock edge: emitter1.780662V, collector2.150008V, VBE0.594174V,IC88.676uA. No relaxation for inactive HBTs.
5. This commit launches cdr-sampler-bleed-cloud.yml for v5. Only slave SE/HE rppd bleeder lengths38.4→9.6um, width1um; master unchanged through explicit separate native slave subcircuit. Source hw/soc/analog/pcie/rx_sampler_bleed_v5.spice and controller scripts/cloud_cdr_sampler_bleed.py. All original5cases/256bits/34.25ns/0.3125ps/1pF/100mV/37.5ps/transistor/startup/domain/source gates unchanged. Inspect actual results before physical integration. No acceptance yet.

## Mandatory next work

Inspect v5 exact run/terminal evidence, preserve any rejection and fix actual circuit before adoption. If all component gates pass, build actual new sampler geometry with separate clock devices and a real folded/parallel128um tail implementation. Old generator assumes cell height<70um and one local tap perMOS; do not blindly reuse it for128um devices or claim its old38device LVS. Require native560DRC, unsimplified deep/flatLVS, actual fault controls, LEF and fresh parasitic extraction, then regenerate full parent and replay the ORIGINAL loaded early/late, faults, PVT/constants and closed-loop gates. No standalone1pF screen replaces actual distributed wire/model validation.

Full PLL/CDR acquisition, SERDES/PCS/LTSSM/replay integration, all four serial lanes, analog pads/ESD and full-chip links remain required. Existing original audit scope and manufacturing/RCminmax/SRAM/LVS requirements remain open unless individually proven. Healthy remote jobs survive local shutdown; checkpoints and evidence live in GitHub. Read the historical continuation document for prior attempts, not stale live-status paragraphs.

## Latest actual v5 result and v6 run to inspect

V5 cdr-sampler-bleed39124621809 at2dc72303010a7aa87641693fca162f5f5c21e01d completed. Nominal/hot and faults pass; cold onlyslaveDPVBE1.000106822V>1V fails. Every normal data test passes. Exactreceipt cdr-sampler-bleed-cold-vbe-rejection-20261018.json. V6 cdr-sampler-balanced-cloud launches from this commit: ONLYslaveDATA emitter bleederL9.6→12.8um, HOLDstays9.6um, allboundaries/gates/native models unchanged. Inspect its real outcome next. Physicalwork remains mandatory after electricalscreen; do not adopt v5 or claimfullPHY/timeclosure.

## Latest authoritative v6 milestone — supersedes pending v6 status

V6 native balanced sampler39125008269 at13e670e3b356924603e18e7cc4fd4e16d0ae4d7b is terminalSUCCESS with actual allfive reports verified, not merely green workflow. All3normalconditions768correctsamples/1pF/100mV/37.5ps and all16HBT/3MOSdevicegates pass. Both actualfaultsdetected and devicesafe under retainedscreen. No diagnostics,16nativeOFFreadbacks, zeroOP, sourceimmutability, sourceNx0/11/16mutationrejections pass. Receipt docs/evidence/cdr-sampler-balanced-native-pass-20261018.json contains all5full reports and archive pins. Candidate source hw/soc/analog/pcie/rx_sampler_balanced_v6.spice, controller scripts/cloud_cdr_sampler_balanced.py.

NEXT ACTUAL WORK: physical implementation of this repaired sampler, including viable128um tail realization and actual body contacts. Existing generator needs geometry changes; possible separate4x32um NMOS or foldednativePCell changes require their own electrical revalidation before use. Exact v6 topology16HBT/3MOS/12rppd, allHBTNx8(total128), reference8um/tails128um,L.3um, collectorW32L2.12, inputpullupsW1L2.4; onlyslavebleedsDATAW1L12.8/HOLDW1L9.6; masterbleedsW1L38.4. Use actualgeometry560DRC/deepflatLVS/faults/LEF/freshRC, rebuild parent with new IDs/RC, and replay originalwholeloaded andlooptests. Do not substitute thisscreen for fullPD420 previouslyfailed loadedwaves. Native model is nominalHBT with three temperature/supplyconditions, not completeprocessqualification.

Live jobs revalidated at this receipt commit:
[
  {
    "run": 39121691046,
    "status": "in_progress",
    "conclusion": null,
    "head": "3b415c02d11ac763fd081412b34234103772d347"
  },
  {
    "run": 39112087217,
    "status": "in_progress",
    "conclusion": null,
    "head": "65d48a27773e891f289c6a9a534290a16623fd56"
  }
]
Full goal remains OPEN; all work/cloud artifacts only.

## New physical-tail candidate v7 to inspect

This commit launches cdr-sampler-parallel-cloud.yml: each128um tail becomes four actual32um/L.3/ng1 native NMOS with identical D/G/S/B, retaining totalwidth128um perstage and reference8um. Counts16HBT/9MOS/12rppd; all HBT/resistor/reference maps exactly compared against passedv6. No electrical equivalence assumption. Original stagecurrentgate uses actual sum of four native currents and all individualMOSvoltagechecks remain. Allfiveoriginal1pF/fullwindow/data/device/fault/source/modeldomain gates rerun. Candidate rx_sampler_parallel_v7.spice and cloud_cdr_sampler_parallel.py. After actualpass, implementreal54devicegeometry incl17taps with fullnativeDRC/LVS/LEF/faults and newparentRC; oldgeometrynotvalid. Mainchip39121691046 and TX39112087217 verifiedin_progress before this change, preserve.

V7 parallel32 run39125446778 is terminal: all device gates pass, hotdelay37.65625ps fails37.5ps; preserve receipt cdr-sampler-parallel-hot-delay-rejection-20261018.json. This commit launches cdr-sampler-parallel-drive-cloud for v8: eighttailMOS widths32→36um(total144um/stage), unchangedallotherdevices/1pF/step/window/gates. Inspect actual fivecase results. Only afterpass build54devicephysicalgeometry (16HBT/9MOS/12R/17taps) with nativeDRC/LVS/LEF/faults; width36um/bodycontacts must actuallypassLU. No physicalintegrationaccepted.

V8 parallel36 run39125857951 at3c5d2dcde9235c499ed0238e057fd2c3e6cb9605 PASSED all five actual screens, with all normal768samples/device gates and bothfaults; source16HBT/9MOS/12R, actualtail4x36=144um/stage. Receipt cdr-sampler-parallel-drive-native-pass-20261018.json. This commit launches cdr-sampler-parallel-physical-cloud: generate actual54devicegeometry(16HBT9MOS12R17taps), native560DRC/deep-flatunsimplifiedLVS/LEF and14faults(original12+missingparallelMOS+missingclockHBT). Exactgenerator/checker/controllerdelta and allfiveelectricalreceipt bindings enforced. Inspect actualnativephysicalresult; do not claim v8geometryaccepted untilallgatespass. Then newparentgeometry/terminals/RC/modelbinding and ORIGINALloadedwaves mandatory.

Actualphysical39126125731 terminalFAILED nativeDRC193markers(560rules):Cnt.b60/Cnt.g1=12/CntB.a48/CntB.a1=24/CntB.h1=48/M4.b1. RealGDS946.125x191.03um generated; LVSnotreached. Receipt cdr-sampler-parallel-first-drc-rejection-20261018.json pins summary653410357SHAff01ce724eaa8d03ed268d5bc971532c0bf07cc1cf681fb4422914e3bf44dffe andparts653410405. This commit launches read-only cdr-sampler-parallel-drc-review to expose193actualnative markercoordinates/cells, reproducecounts and retainoriginalgeometry/reference. Next usemarkers forcontact/M4geometryrepair, preserveallgates/sourcecircuit; noparentadoptionuntilnativeDRC/LVS/14faults/LEF pass.


## Native tap overlap repair, pending fresh physical validation

Read-only run39126723857 at5604b9caf2fda8ebda5d56851149deb1d78594c1 reproduced all193markers. The192contact errors locate six local taps shifted onto their own MOS strips; source32/36um electrical topology was not the cause. One same-SUB M4 pair has only0.14um edge separation. The generator now reserves18um between primitive bboxes, rejects localtap overlap with every actualprimitive bbox (1um clearance), and spaces all M4 columns including same-net SUB. Electricalv8 source,54device census,560native rules, unsimplifieddeep/flatLVS and14faults unchanged. This commit triggers fresh cdr-sampler-parallel-physical-cloud; inspect actual result, not workflow submission. No samplerphysical/parent/fullPHY acceptance yet. Mainchip39121691046 and TX39112087217 still in_progress, preserve. All modifications through GitHub API in RAM; localworkspace remains empty.


## Authoritative sampler physical pass and new parent484

Run39127236215 at0d73c02a6311a7abf3d99a774a510d2857917829 passed actual560-rule DRC with zero markers, unsimplified deep/flat54-deviceLVS, nativeLEF and all14actualfaults. GDS a361748f617e202e509cb78489c0593d4596200a0c6621f096c01485b2dc7341; bbox1134.69x191.03um. Fullreceipt cdr-sampler-parallel-physical-native-pass-20261018.json. Prior193marker rejection remains archived.

This commit launches cdr-retimed-parallel-v3-parent-cloud: replace exactlyfourold38device sampler leaves with verified54device v8 leaves. Exact sourceplan41cards/16macros, expected484devices =116HBT+46NMOS+102rppd+11MIM+209taps. Allotherleafreceipt hashes and native560rules/deep-flatLVS/fivephysicalfaults remain; add explicit extractedprimitive-kind census. Actualleafshapes must be conserved. Supplyoverlay retains the two verified XOR redundant-via omissions and independently binds any new sampler omissions to actualsame-net retainedrisers within4um. Original420source/failedloadedwave evidence unchanged. No newparent electrical acceptance until actualfreshgeometry/RC/modelbinding and ORIGINALfull loadedearly/late/fault gates pass.

Mainchip39121691046 and TX39112087217 remain in_progress at this checkpoint. Cloud-only; localworkspace empty. Full serialPHY/mainchip/finaltiming remain OPEN.


Parent484 run39127789321 at36e1c530d71671261e2380e5ba7b57a213208b7b generated actual484device layout2128.29x4505.08um, but native560rule DRC rejects54TM1.b markers; LVS not reached. Sampler54child remains independentlypassed. Receipt cdr-parallel484-first-drc-rejection-20261018.json preserves fullrejection. This commit launches cdr-parallel-v3-drc-review to expose all54actual native markercoordinates and parent supplyoverlay metadata. Nextfix actualTopMetal1 geometry, retain childconservation/strictDRC/LVS/faults; nofreshRC orparentacceptance yet.
