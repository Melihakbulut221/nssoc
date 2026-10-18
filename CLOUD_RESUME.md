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


Native54marker review39128067557 reproduced allTM1.b errors. ActualsamplerM_T3/S_T0/S_RP supplyspans run0.085/0.965/1.17um from fixedQP/QN M6via patches; nativeTM1.b requires1.64um. This commit shifts onlythose12spans(+2um, fourcopies) and addsactualM6 endpointbridges tooriginalnativevias. Existingchilddrawing/terminalnets retained. Same-net redundantshunt omission radius4→5um prevents endpointnotches; everyomission stillbindstoactualsame-net retainedriser, originaltwoXOR omissions preserved. Fullparent physical rerun starts; noacceptanceuntilnativeDRC/deepflatLVS/faults pass. Receipt cdr-parallel484-native-tm1-diagnosis-20261018.json.

Parent39128392958 generation guard correctly stopped beforephysicalchecks: global5um shunt radius changed an unintendednon-sampler leaf. Newfix limits5um radius tosampler; allotherleaves retain4um exactly. Recorded cdr-parallel484-shunt-scope-rejection-20261018.json. Native2um span reroute andallgates unchanged. Inspectnew cdr-retimed-parallel-v3-parent-cloud run.

Parent39128692386 at646ef87aa354f31551a4772f73716f7cf9021325 now passes560-ruleDRC withZEROmarkers; unsimplifiedLVS failsNoMatch despiteexact484vs484devices and noextractiondiagnostics. Receipt cdr-parallel484-drc-pass-lvs-rejection-20261018.json pinsactualresult. Thiscommit launches cdr-parallel-v3-lvs-review: probe158public/childplanes and nativeclusters fromactualfailedLVSdb, preserve extracted/schematicnetlists, identifyshorts/opens. DoNOTacceptparent/reuseoldRC. Earlier39128654621 was superseded wrongscopevariable candidate and failed; nohealthyjobwasrestarted. Mainchip39121691046 and TX39112087217 lastverifiedlive.


NativeLVS review39129071316 at85d8a92da366a663321dc6a8541d567c63a60b91 proved onecluster joins aqp/aqn/bqp/bqn/cqp/cqn/dqp/dqn/avdd/avss; noopenedpublic/childnet. Exact484device census preserved. DRC0 alone was insufficient: overlappingM6 conductors merged asshorts. Fullreceipt cdr-parallel484-native-lvs-short-diagnosis-20261018.json. Newrepair checksEVERY sampler supplyspan plus endpointbridges against actualbaselineM6 and already-added overlayM6 with1.645um clearance. Deterministic nearest5nm-grid offset within10um; originalM4/M5 endpoints preserved; allnon-sampler spans unchanged; fixedthree-path patch replaced. Native560DRC/unsimplifieddeepflatLVS/faults remain mandatory. Inspectnewparentrun beforeanyfreshRC acceptance.


Latest native-job checkpoint after actualM6 obstacle routing:
[
  {
    "run": 39129347291,
    "status": "in_progress",
    "conclusion": null,
    "source_head": "8136ace492152f1f91e4e355a7c164bd24059e08"
  },
  {
    "run": 39121691046,
    "status": "in_progress",
    "conclusion": null,
    "source_head": "3b415c02d11ac763fd081412b34234103772d347"
  },
  {
    "run": 39112087217,
    "status": "completed",
    "conclusion": "failure",
    "source_head": "65d48a27773e891f289c6a9a534290a16623fd56"
  }
]
Read parent39129347291 at8136ace492152f1f91e4e355a7c164bd24059e08 next. TX actualswap_leaf_select job117631094041 finished: full34ns/256bit capture detects fault,24HBTfaildevicegates; doNOTinfer nominal acceptance. Complete rawwaves remaincloud release parts (about1.6GB), never downloadedlocally. Receipt tx-v5-columns-actual-fault-observation-20261018.json. NominalTX117631094117/mainchip117658413515 remainindependent; preservehealthyjobs. FullgoalOPEN.


## Authoritative parent484 physical pass; fresh extraction begins

Run39129347291 at8136ace492152f1f91e4e355a7c164bd24059e08 passed560-ruleDRC ZEROmarkers, unsimplifieddeep/flat484deviceLVS andfiveactualfaults. Nativecensus116HBT/46MOS/102R/11MIM/209taps. GDSfc5597ca57d9c6ff97bb230ba4db0334e454fbb5b214d85552c578ebe48e4de1. Receipt cdr-parallel484-parent-physical-pass-20261018.json. SevenactualsamplerM6tracks shiftedpercopy by0.475,-1.795,0.68,1.7,2.72,3.74,1.56um; allactualM6obstacles avoided, originalendpointsandchildshapesretained. FullPHY NOT accepted.

This commit launches cdr-retimed-parallel-v3-planes-cloud: original158planes/51nets/19faults, newly derived1394terminals. Nextfresh wire-inputs/native binding/RC/MIM audit/composition and ORIGINAL full-loadedearly/late/fault gates. Expectedmetalterminal921/body473/anchors946 (derivefromactualcensus; verifyactualnativegeometry); originaltopology111wirecomponents must be independentlyconfirmed, never assume oldRC stillvalid. No reuseold420RC.

TX39112087217 nowTERMINALFAILURE: nativefull34ns/256bits completed in14960s,181/768wrongsign and220below100mV;24HBTfailminVCE;0MOSfail; nodiagnostics. CMOS,level8,level16 interfaces pass;level4 andfinal fail. Receipt tx-v5-columns-native-full-wire-rejection-20261018.json. NextTXwork: bind24failingHBT IDs to physicalstages and inspect nativelevel4/final timing/amplitude/clockheadroom before another expensive simulation. Source65d48a27773e891f289c6a9a534290a16623fd56, fullarchivescloudonly. Mainchip39121691046 stilllastverifiedlive; preserve. FullgoalOPEN.


Nativeplanes39129717120 at0a4b2de04f7fc6ffeb880df2cb96ee2c6d45e97e PASSED: all158physicalplanes,51distinctnets,1394native device terminals,19corruptionsrejected. Receipt cdr-retimed-parallel-v3-planes-pass-20261018.json. Thiscommit launches cdr-retimed-parallel-v3-wire-inputs-cloud using actual484GDS/LVSdb and exactlyidenticalprimitiveannotations; expected921metal/473body references plus25public=946anchors. Frozenoldnativeextractionmethods preserved; onlypath/top/censusbindings changed, sourceguard checks exactdelta. Inspectactualnativegraph/anchors before binding/RC; never reuseold420wireRC. TXnormalfailure remains todiagnose (181wrong samples,24HBTminVCE failures). Mainchip39121691046 lastverifiedin_progress.

TX nextaction running: tx-v5-columns-stage-review-cloud maps the24actualfailed HBT IDs to physicalmacro bboxes and actualinput-base bindings, using verified34MB compositionarchive only. No4-hourSPICE rerun orlocalwave download; originalnormalfailure/delta/gates preserved. Inspectactualmapping beforecircuit/clock/route repair. CDR newwire-inputs job proceeds independently.


Whole nativewire-inputs39130017671 at e1fe561870696bccffaec7e4d0cc2c45eeb6ef07 PASSED:484devices/1394terminals,111wirecomponents,946exactanchors(921metal+25public),473intrinsicbodyreferences. Noquantizationmerge/nogeometryedit. Receipt cdr-retimed-parallel-v3-wire-inputs-pass-20261018.json pinsfullsummary/archive/outputs. Thiscommit launches BOTH cdr-retimed-parallel-v3-binding-cloud (484nativePDKdevices,12corruptions) and cdr-retimed-parallel-v3-rc-cloud (actualfreshnativeRC, original13rawcorruptions). Sourceguards preserveoriginalmodels/limits/topology/valuechecks. Afterbothpass still MIMcapture/audit/composition and originalloadedearly/late/faultwaves required. TXstage-review39130259920 rejected ambiguous same-basename childlayout paths; exactparentarchivepath fixed andnewreviewlaunched, allhashchecksretained. Mainchip39121691046 remainslastverifiedlive.


Fresh484wireRC39130617868 at438160cab31372aae54597e7d083dc26c499ebb2 PASSED:3515R/4027C,111components/946anchors, exactnativeRvalues and allground/mutualcapattachments preserved, original13actualcorruptions rejected. Receipt cdr-retimed-parallel-v3-rc-pass-20261018.json. NotqualifiedRF/substratePEX; MIMcapture/audit/composition stillrequired. Binding39130617923 stopped at oldMOSconverter whitelist8/32/64um. Newbuild_cdr_parallel_v3_native_models.py adds exact36um tails; bindingenforces nativewidthcensus8x8um/2x32um/32x36um/4x64um. AllPDKmodels, extractedjunctiongeometry, portorders and12controls unchanged. Freshbindingrunlaunches; no needrepeat already-passedwireRC.

TXstage review39130617772 PASSED actualmapping: failed24HBTs group f6,p8_1=4,p8_3=4,p8_7=4,p8_6=2,p8_5=4. All are clockselector HBTs except finaltwo tailHBTs; none matchdata-inputbase references. FinalID109-112 clocks Nx6 and114-115 tailsNx8; p8 selectorsNx1. Nativecoordinates/modelbindings preserved in tx-v5-columns-native-stage-diagnosis-20261018.json. Nextinspect fullnative Vc/Vb/Ve at worstVCE and sourceclock/commonmode/bias/RCdrops; retainoriginal100mV/0.3,0.5,0.7UI and devicegates. Do not launchanother4hfullsim withoutsupportedrepair.


Binding39131028585 at3c8cb98bc8d7a42e40dbea8709009f62736d78ee PASSED actual484nativePDKdevice binding, exact1394terminals and12faultcontrols. Receipt cdr-retimed-parallel-v3-binding-pass-20261018.json pins fullreport/archives andactualMOSwidthcensus8x8/2x32/32x36/4x64um. Thiscommit launches cdr-parallel-v3-mim-parent-rc-cloud: actual11MIM masks/vias,946physicalpoints,111nativewirecomponents, exactintrinsicgeometry/plateownership with fivefaults. Originalcapturemethod/model/tech checks retained through source-delta guard; no old420RCreuse. Aftercapture still rawRCaudit/composition and ORIGINALfull-loadedearly/late/faultwaves mandatory. Mainchip39121691046 revalidatedin_progress; preserve. TXfullnormalrejection stillopen; nextnativeextremareview. Cloudonly, localworkspaceempty; fullgoalOPEN.


Thiscommit launches tx-v5-columns-extrema-review-cloud: restore original failed nominalrun39112087217 nativefull34ns/77618row/3004vector wave ONLY onGitHubhost; verifyimmutablearchive/rawSHA and reproduceall604originalHBTmetrics exactly. Map24minVCE extrema toactualnativeC/B/E/S,clockcommonmode,bias/supplynodes andneighboringsamples. Diagnostic only; noSPICErerun/gatemodification. Runnerrestoredrawcopy removed onlyaftervalidation; originalcloudreleaseparts preserved. Useactualextrema fornextcircuit/clock repair, notanotherblind4hsimulation.


NativeMIMcapture39131886057 at121e1ac810782f6b174080dfa258cfbd353b8a09 PASSED:3538R/4038C,11actualintrinsicMIM,111components/946points,exactnativeplategeometry andallfivecapturefaults. Receipt cdr-parallel-v3-mim-parent-capture-pass-20261018.json pinsfullreport/archive. Thiscommit launches cdr-parallel-v3-mim-parent-audit-cloud with actualnewcounts, original13rawwire+9intrinsiccorruptions, newbindinghelper andexactsourceguard. Rawvalue/topology/capattachment conservation must actuallypass; capturealoneisnotacceptance. Nextcomposition andoriginalloadedwaves.


MIMrawaudit39132239771 PASSED exact3538R4038C nativevalues/topology/attachment,11intrinsicMIMidentities and13wire+9intrinsicfaults. Receipt cdr-parallel-v3-mim-parent-audit-pass-20261018.json. Thiscommit launches cdr-parallel-v3-mim-composition-cloud preserving everywiretoken,484nativePDKdevices,1394terminals,946anchors/473bodyrefs and19controls includingdouble-countedMIM rejection. Nextfull-loadedoriginalgates, with actualfour36um tails perstage collectivelychecked againstoriginalstagecurrentfloor; everyindividualMOSvoltage/currentbound retained.

TXextremareview39132058371 at17b58aa321b3393c3902e2d4876d047134f97414 reproducesall604originalHBTmetrics exactlyfromfull77618native rows. Receipt tx-v5-columns-native-extrema-20261018.json. Finalselector minima C~0.948/E~0.582V; finaltail minimum C~0.457/E~0.093V (publicnativeE isavss, actualterminalhas93mVreturnrise). p8selector minimum C~1.014/E~0.634V. Publicclock-toactualbase drop onlymicrovolts; clockCM1.35-1.41V andinterstagecollectorheadroom needjointanalysis. Original24failures/dataerrors retained; noacceptance/clock-shift fix claimed. Fullrawremainsimmutablecloudrelease; diagnosticrunnercopyremovedafterverification.


PD484composition39132443095 at36a735880cb24251800c1bf0355dd43efcf346af PASSED exact484devices/3538R4038C and19actualcorruptions,11MIMemittedonce. Receipt cdr-parallel-v3-mim-composition-pass-20261018.json. Thiscommit launches cdr-parallel-v3-mim-loaded-cloud originalnominalearly/late+clockstopped/VIbiasoff cases with actual116HBT46MOS/wholefreshdistributedRC andoriginal256bits/150fFcollectorloads/50fFcomparatorloads/phases/margins/delays/devicebounds. New32samplertailMOS areboundas8actualparallelgroups; all38MOS tails form14physicalstages. Sum instantaneouscurrentsof eachactualdrain/gate/sourcegroup forunchanged0.5mAperstagefloor; everyindividualMOSvoltageandnonnegativecurrent retained. ExactnativeMOSwidthcensus enforced. No testwave/dataphase/window/thresholdrelaxation. Allhot/cold/constants andclosedloop/RFqualification stillrequired afterthisscreen. Sourceguardsretainoriginalfailuremethods.
