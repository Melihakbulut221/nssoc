## Full native boot advanced to 1.90M cycles; next checkpoint continuation live

Parent43573697024/source `27c496c5649c284e5cc1494792ef103c7fd427c7` completed CHECKPOINT infrastructure successfully, **not boot acceptance**. Lastcycle1900000, UART450 bytes, flash6frames; firmware entered, tests1..5 print ok. completed_boot=false,passed=false, checkpoint_saved=true. Safe14110894168 SHA256 `93d10bd767f486fdc5718cec80d4de1cdd2c1fd453c805bda68e31874bdaf79d`. Native14111635745 SHA256 `4118593a84fc58be234b22d1fe177626dba8a2a6f973ff10e5effca36b9472a9`; tgzSHA `06e96554e91fd1b956b3c948419a02f7de81c8ba43f75df69e5d6014453d5875`, images-43573697024, logprefix16449bytes SHA `6fc8354e52debce6a7854615f17ef0cce200158d95a819638f58fa6535e85793`.

Live continuation [43588310054](https://github.com/Melihakbulut221/nssoc/actions/runs/43588310054), source `1c0d103c64f040543106b2a3e9265fe580f4d289`, branch `codex/full-native-boot-continuation-three`. Exact 1.90M checkpoint/runtime/parent/input guards retained, original3M bound and28 final checks unchanged. Do not replay older1.26Mcheckpoint. All native work stays cloud.

DP bounded mismatch diagnosis43587894664 failed on unavailable Net.id; corrected43588102578 hit native Python malloc abort (not an LVS result). Current instrumented diagnosis43588371410/source `4c3e36b2409301d094fd1ff57f2e776f22735405` reads saved DB only, with faulthandler/stage logging to locate binding abort; no new LVS extraction. Full bounded comparison result remains25Match/1topNoMatch. Other live PHY43584735530, antenna43579643337, SP43566292104.

## Bounded DP comparison completed in 87.68s: 25 Match, 1 top NoMatch

Run43587554414/source `d4a4f4f4468e56f354b87ce20748ca9945b2f1c9` completed DIAGNOSIS successfully, **LVS FAILED**. Native10/10 default/bounded identity and mutation controls passed. Exact70110 devices per side preserved; extraction diagnostics0. 25 child circuitsMatch, topNoMatch. Strict audit remainsFAIL. Safe14111580210 SHA256 `cc9d018c2ee7e6c3d4fff20edf534c8eaa2640a945f06c3eef1976cbcffcc9f0`. Native14111500413 SHA256 `31142082483dce4751f3abfe3af48cc1e76a48b4ce6f61ce9afbb6f29f5f3ced`; final DB SHA256 `341e7da0e6d9552c99f31d058d0250846321051badf48c099add4e60edebc2aa`. Native files stay cloud. Do not interpret green diagnostic job as LVS pass.

Live mismatch diagnosis43587894664/source `8d7ec27a32169f50002cc2fb253e5007c5ecf2cc`, branch `codex/dp-sram-bounded-mismatch`: read saved DB only in cloud, aggregate top net/device/subcircuit statuses and parameter differences. Safe `dp-sram-top-mismatch-derived-*`. No new extraction or graph edits. Other live jobs: PHY43584735530, antenna43579643337, SP43566292104, MBIST43573697024.

## DP bounded-comparison diagnostic launched

Run [43587554414](https://github.com/Melihakbulut221/nssoc/actions/runs/43587554414), source `d4a4f4f4468e56f354b87ce20748ca9945b2f1c9`, branch `codex/dp-sram-bounded-comparison`. Restores exact timeout archive only in cloud. Validates runtime/deck/reader/reference/input hashes. Only adds `max_branch_complexity(16)` in strict compare branch, leaving depth, device/port/dimension acceptance unchanged. Native default and bounded identity/fault controls run first. Bound exhaustion is failed_match in pinned KLayout source, not match. Native cap1800s for diagnosis; any unresolved graph remains failure. No full-chip/vendor/production claim. Safe `dp-sram-bounded-derived-*`; native artifacts cloud-only. Do not rerun old 43562021054.

Live alongside PHY sizing43584735530, CRC antenna43579643337, SP LVS43566292104, MBIST43573697024. Previous evidence below.

## DP engineering full-macro LVS timed out in comparison, not a mismatch verdict

Run 43562021054/source `70ebe8dca3b28d91a259f49bfee6b5b57c219f6e` is TERMINAL FAILURE. Native KLayout reached 18000-second timeout. Do not poll or blindly rerun it. Safe derived artifact 14110887368 SHA256 `f242d163ee68b57e2d873ec8b4104be8c9c30dc5ed2749102c964a318ece1195`. Native archive 14110867794 SHA256 `d0109ba41e2d146d25a90f7dcaeba2602b87168cbe9b0d01a175b57b1734658e` stays cloud-only.

Cloud log diagnosis 43587113786/source `1c2c0c3837f1c302a681a461ca1febed4ac80dc8` succeeded; safe artifact 14111100106 SHA256 `08511c7c8597c2a20a76df20a0b3048a90fade1858e6ead6334e0e746f1f48c5`. Last deck line: 05:48:26 UTC Starting SG13G2 LVS Comparison with flag_missing_ports, following derivation/extraction/alignment at 05:48:17..26. No final lvs.lvsdb/extracted.cir. Next inspect comparator matching behavior and strict negative controls; not geometry extraction or blind timeout extension. Existing six-cell flatten/count proof and engineered resistor candidate remain unqualified; no vendor/full-chip LVS pass. Full evidence in `docs/evidence/dp-sram-engineering-comparison-timeout-20261114.json`.

Still live: PHY sizing 43584735530 (two variants), CRC antenna 43579643337, SP LVS 43566292104, MBIST 43573697024. Earlier records below.

## C sampler phase diagnosis completed; two isolated circuit candidates live

New screen [43584735530](https://github.com/Melihakbulut221/nssoc/actions/runs/43584735530), source `842ab2012fae1904251fd1503024e5670de6ad8f`, branch `codex/cdr-c-slave-sizing`. Relative to `bd10_lowz8_xor2`, `cdata3` changes ONLY XD0255/XD0257 nx=4 to 3; `cslave3` additionally changes XD0253/XD0254. No bench, solver, acceptance, wiring-RC or layout changes. Candidate binding uses actual nx for current-density gates. Isolated-edit proof includes three negative controls. Do not integrate these circuit changes without results. Safe artifacts `cdr-c-sampler-result-only-*`; mixed NPZ and native artifacts stay cloud-only.

Phase diagnostic 43584493730 passed unchanged-gate reproduction. Verified artifact 14110140623 SHA256 `87e4c31c3a91c3df65895773196fde014965e0ec93ed9e25e80f0a2fde019298`; full report in `docs/evidence/cdr-c-sampler-phase-result-20261114.json`. For history 010, median C output at phase .5UI is 203.2mV, falling to 88.25mV at .875UI (all 32 bits below 100mV there). History 011 retains 147.97mV at .875UI. Early transition acquisition also fails. Simultaneous differential samples and physical clock-bank currents support acquisition/retention investigation; no closed-loop PHY claim. Frozen original gates are unmodified.

Other live work: CRC antenna 43579643337; SP LVS 43566292104; DP LVS 43562021054; MBIST 43573697024. Poll actual jobs, never restart on observation timeout. Prior records below.

## C sampler transistor diagnosis completed, PHY still rejected

Run 43584141378: both jobs passed diagnosis, reproduced original failing gates. Ten physically connected HBTs traced from C output, including feedback. Safe results and original full reports in `docs/evidence/cdr-c-sampler-path-result-20261114.json`. Load12/load16 both show history 010 minimum about 51.92mV and median about 93.3mV at frozen samples, below 100mV requirement; load change does not fix sampler. Script now retained; experiment workflow not merged. Next: analyze phase-resolved C master/slave acquisition and feedback currents before a circuit candidate; pooled node percentiles do not prove instantaneous differential gain. No new simulation/layout/PHY pass. Four previous long jobs remain separate; check their actual terminal results.

## C sampler original-bias path diagnosis launched

Run [43584141378](https://github.com/Melihakbulut221/nssoc/actions/runs/43584141378), source `413bd9793862cfd88281883d82ae8355f3ba811b`, branch `codex/cdr-c-sampler-original-bias-path`. Uses both rejected original-bias load12/load16 native captures on cloud runners only, replays original gates, then reports physical transistor voltages/currents by bit history. No acceptance or circuit changes. Inspect safe `cdr-sampler-c-path-derived-*` JSON on completion; do not download native archives locally. Do not merge experiment workflow.

Four existing jobs were still in progress without artifacts: CRC antenna resume 43579643337, SP LVS 43566292104, DP LVS 43562021054, MBIST 43573697024. Do not restart them. Prior checkpoint below remains applicable.

# CRC continuation handoff archive-name error fixed

43579396178 failed BEFORE native CAD: base archive SHA passed, but tar expected routed.tgz whereas actual freshCRCbase14100640319 contains handoff.tgz. Verified original parent workflowb1626c18095a9a9c7a06b3cb1bd508a4a0ba7f19 uses handoff.tgz. No repair result or changed design. Stop polling thisfailedrun.

Replacement43579643337 source288a68db7bd32fd3218eec5486165a2b4adeb48e, samebranchcodex/crc-jumper-checkpoint-resume, queued at latest dispatch check. Changed only base archive member name and failure archive preservation of recovered-route (so NL/PNL/input checkpoint references survive). ExactSHA/ODB/SDC/565antenna check, jumper-only method,5iterations, freshfinalCheckAntennas and dependent3cornerSTA unchanged. Await actual checkpoint restoration and native repair result. Native archive/content remainscloudonly. Other live43566292104,43562021054,43573697024. Fullgoalopen.

---

# Exact CRC DRT checkpoint recovered; jumper-only repair continuation active

Inventory43579197875 completed/success; safe14106639162 SHA2d74ec95899508f1e5ce5580c13e6c4c18570d9cc556552260675e1be608b651. Savedroute/3-openroad-detailedrouting/drt-run-0/soc_top.odb218660715bytes SHA9adefc224ed62b8e661cdf4c2ae009f4e9910e5e2c5b848156464eb0fdfca40c; SDCroute/1-openroad-detailedplacement/soc_top.sdc SHA1fab1c6a3d4777bca6c00e4008ea6546ef403b100a3bc480683172a0ba682511. State_in NL/PNL fromdetailedplacement. This is completed initialroute before failed diodeinsertion; no newroute pass claimed.

Continuation43579396178 source94b5fab106b45e94460f9ab382cd6b80b2e5ed23, branchcodex/crc-jumper-checkpoint-resume, verified in_progress. Restores freshCRCbase14100640319 SHAf724a289dc08812190d1aac64bfd1b4fafceeaca71c734ed578ca41d96a62f7c then failednative14107653261 SHAa401c73f139405396cf8afdb0e24e718c1334c09d8c49c3e4774d78e3440f64c. Moves oldroute to recovered-route before new force-run-dir, keeps NL/PNL refs valid. Exact ODB/SDC guards, stale metrics cleared, requires fresh565antenna nets before skipping initialDRT. Config changes only DRT_ANTENNA_REPAIR_JUMPER_ONLY=True/DRT_ANTENNA_REPAIR_DIODE_ONLY=False; original5repairiterations,DRT16,ratio10/clocks preserved. Uses supported pinnedupstreamdrt script guardd389d9e6...; no relaxed thresholds. Adds OpenROAD.CheckAntennas afterrepair to prevent stale finalcounts, thenRemoveRoutingObstructions. Dependent extractedSTA retains strict3cornerzero gates. Route355min/19200s,STA355min/19800s. Actual repair result pending.

Safe route-crc_jumper_resume-43579396178; native routed-db-crc_jumper_resume-43579396178 cloudonly; safeSTA routed-sta-crc_jumper_resume-43579396178. Failednative antenna-resume-incomplete-native-43579396178 cloudonly. Failure recovery may require original archive too, because recovered-route references are outside new route archive. Receipt docs/evidence/crc-jumper-recovery-launch-20261114.json. Source experiment only until tested. Stop pollinginventory43579197875 aslive.

Otherlive43566292104(SP),43562021054(DP),43573697024(MBIST). PHYnext: actual Csampler gain/data path after load-only screens failed. Fullgoalopen.

---

# Fresh CRC route failed diode legalization, checkpoint inventory launched; CDR settling diagnosis complete

43561900502 sourceb1626c18095a9a9c7a06b3cb1bd508a4a0ba7f19 terminal/failure, ROUTE_RC2 NOT timeout. Job132347238762 log: initial detailedrouting3h18m08s finishes DRC0; antenna565nets656pins; first repair_antennas fails DPL-0036 on ANTENNA_482,ANTENNA_1342,ANTENNA_457,ANTENNA_458. DependentSTA skipped. Native14107653261 SHAa401c73f139405396cf8afdb0e24e718c1334c09d8c49c3e4774d78e3440f64c stayscloud. Routeartifact14107820079 SHAd88db968c580a65be20a6f92f28f7f4511a23dfffb481103f8a6cf9f3c097a5a includesDRCgeometry, do notdownloadlocally.

New inventory43579197875 sourcedbadad3fb7fbbc40565e65496a6121f9de38d312, branchcodex/crc-route-recovery-inventory, queued at dispatch check. Same prior tested inventory adapted to route-incomplete.tgz; collects only paths/hash/size/state references/metrics, no native bytes locally. Safecrc-route-recovery-inventory-43579197875. Find exact saved drt-run-0 ODB, config/state refs; then diagnose diode legal placement or jumper repair using checkpoint. Do not repeat initial full route. Receipt docs/evidence/crc-route-diode-placement-failure-20261114.json. Stop polling43561900502 aslive.

CDRdiagnosis43579024949 sourceb562486df6d8c15994b355b877bfc80a648d77ac success; safe14107443996 SHA4d9a5206ab7aa3a5d05a7769241058bf3520d308ee87acd5986b2a105b97a895. Exact252interiorbits UI/16grid: neverstable>=100mV by117.1875ps A0/C64 in baseline,load12,load16 all; bufferA67→63/63,bufferC96→96/96. No acceptance threshold/window changes. Csampler history-sensitive margin remains; loads do not fix it. Testedscript integrated, result docs/evidence/cdr-acload-settling-result-20261114.json. Next PHYwork should inspect actual Cmaster/slave gain/data path instead of more load/current sweep. No fullPHY/layoutclaim.

Stilllive43566292104(SP),43562021054(DP),43573697024(MBIST), plusnewinventory43579197875. Fullgoalopen.

---

# Both original-bias collector-load CDR screens fail data; saved-sample diagnosis live

acload16 result from43571075470 verified: simulatorRC0/devicePASS/phasePASS/dataFAIL. X381wrong717below100mV, Y2wrong596below,765samples each. A/C/D lowmargin65/139/96 exactly same counts as acload12;Bpass. Lower collector resistance alone does not fix the data path. No new layout or closed-loop proof. Safe14107393490 SHAd335866dcf7c30ea6e7100f2ba2041b71d64692ee36bc3b3d197a5fa4896ae2e. Native14107159021 SHA5dbfa37bb7560c8b363f6edf179e098c4e2469281b797aba3d0486ebcc389dcc; mixed14106994265 SHAf8b37b573de8ec7608b800a71089896805462a387bd2c3f97cc371f1953ab17e, bothcloudonly. Raw8fb118e2e91346887be64ba06ebd3c9d31bd1b992fbb5adb2d8f8ec97d1a654a,113490points. Receipt docs/evidence/cdr-acload16-rejected-20261114.json.

Next43579024949 sourceb562486df6d8c15994b355b877bfc80a648d77ac, branchcodex/cdr-acload-settling, verified live. Same tested exactUI/16 conditional settling diagnostic adapted to baseline+xor2acload12/acload16 pinned mixed archives. No waveform realignment, threshold edits, new simulation/layout. Script scripts/diagnose_cdr_acload_settling.py onexperiment, safeartifactcdr-acload-settling-43579024949. Goal: distinguish unchanged sampler-margin from buffer-settling effects before another circuit candidate. Native/mixed archives staycloud. Await result before integrating script.

Other live43566292104(SP),43562021054(DP),43561900502(freshCRCroute),43573697024(MBIST). Fullgoalopen; RX6finalantenna0/0 independentlyproven but extractedSTA rejected as recorded below.

---

# RX6 final antenna independently0/0; routed timing rejected; CDR load12 data fails

43577454990 source7e10978a522ae51d0ccc3d251e1f04e7c089884a completed/success. Fresh read-only native antenna check0nets/0pins,0warnings/errors. ODBSHA3eaa76b381138c637770590f5e19bdedebedc9e658c854fe9b4bf109d31c03cd,SDCSHA5c65218b6106315c71d45c19eb61af09781607f0f438f2c7f99c4427884d24a4 unchanged. Old1/2was pre-finalrepair: do not repair this now-clean antenna candidate. Safe14107441301 SHA25849f1b1bffc545a7984b6e20aca9ec633dd49ca36023d35a795d616b77590d. Tested source copied to main. Receipt rx6-final-antenna-zero-20261114.json. Future routing must check antennas unconditionally after final repair; no report-only freshness assumption.

43569629324 terminal/failure. SafeSTA14107520603 SHA3e1a511d5f9560af0dae28a9ecf652d32ee3fb647eb0d5bc8e87fd0944148911 verified/read. Slow1327setup(-1.996737943ns),0hold;typ0setup,2hold(-.012410961ns);fast0setup,74hold(-.111859136ns). FastgroupsPCIe70/CPU4; EthRXhold0. SlowsetupPCIe754/CPU529/async41/EthTX3. Cap105/106/111,slew751/249/125,fanout1423each. Timingreject; freshCRC43561900502 remains priority separate netlist. Do not transplant old-instance ECO. RepeatSTAartifactdownload timedout180s before mutation; first successful SHAverified read supplied exact scalarreceipt docs/evidence/rx6-routed-timing-rejected-20261114.json. No simulator rerun needed.

CDR43571075470 acload12 completed/failure: simulatorRC0/devicePASS/phasePASS/dataFAIL; X381wrong717below100mV,Y1wrong588below,765samples each. A/C/Dlowmargin65/139/96,Bpass. Safe14107175734 SHAc7afa62bbf62281ed8aad8aff94c97bc16af769ceaedd21cff1815c422ca7501; fullresult docs/evidence/cdr-acload12-rejected-20261114.json. Native14107240670 SHAa4f8b266f11b0a48d7bda855c8a6d69933d6ea2933be82f2ec200a89925eb3d5 cloudonly, mixed14106494834 SHA7847a708ebe849dbb6219c58982ff24543d9094dd96e1b7872942f9e6ff22f71cloudonly. RawSHA7591486c78ad4f9e50e82c675417f047b04d8f71d781bb11ea1e4f0e5ca64444,113490points. acload16 stillpending atlastpoll.

Livehandles43571075470(partial),43566292104,43562021054,43561900502,43573697024. Stop polling43569629324/43577454990 aslive. Fullgoalopen; router/antenna checks are not foundry signoff or fullPHY.

---

# Antenna audit format-key bug corrected; final-archive-bound check live

43577172823 failed before OpenROAD measurement with KeyError:'SDC': deprecated DesignFormat.name returns lowercase format id, not enum identifier. Replacement uses explicit odb/sdc keys. Removed incorrect pre-route-SDC hash comparison: final views are bound to exact SHA-verified final routed archive14105679819; hash invariance of ODB/SDC before/after native check remains required. No layout/threshold changes; old SDC equality was not evaluated due KeyError, so no claim of measured hash mismatch.

Replacement43577454990 source7e10978a522ae51d0ccc3d251e1f04e7c089884a, branchcodex/rx6-final-antenna-audit, verified in_progress. Safe artifactrx6-final-antenna-derived-43577454990. Require native antenna__violating__nets/pins, no view replacements, input hashes unchanged. Stop polling failed43577172823/43576971725. Actual final antenna status still unknown; recorded1/2 may precede last repair. Other livehandles remain43571075470,43569629324,43566292104,43562021054,43561900502,43573697024. Fullgoalopen.

---

# Final antenna audit run-directory failure fixed; replacement live

43576971725 failed before any native antenna measurement: CLI --force-run-dir requires existing directory final-ant. Exact source/raw checkpoint unaffected. Job132393216711 confirms archive SHA passed; exit2 on missing run directory. Derived error artifact14106581453 SHAea306ba8840a83fef48235c6be98a926aee285e4f9cb7df743327b3cc8c805c7.

Workflow now mkdir -p out "$OUT/final-ant" before CLI. Replacement43577172823 sourcef2a0307ed1b5c51a6d5422e72b8aeed1c4143f59, samebranchcodex/rx6-final-antenna-audit, job132393847343 verified live preparing pinned tools/PDK. No design/limit/helper change. Await derivedrx6-final-antenna-derived-43577172823, require actual fresh native metrics and ODB/SDC hash invariance. Stop polling failed43576971725. Existing main RX6 stored1/2 remains potentially pre-final-repair and not proven final. Fullgoalopen.

---

# RX6 final antenna metric freshness unresolved; independent read-only audit launched

New evidence: pinned LibreLane3.0.5 drt.tcl loop is `while {$i <= $::env(DRT_ANTENNA_REPAIR_ITERS) && [log_cmd check_antennas]}`; it increments i after each repair/reroute, then writes views WITHOUT an unconditional final check. RX6 consumed all3iterations, so saved1net/2pins may describe the pre-final-repair database. Previous receipt accurately preserves stored metrics, but they DO NOT prove final remaining violations. Do not assert final antenna closure or final1/2 until fresh audit.

43576971725 source94ed5de217b4d811cc735db425c74fe49f6abf21, branchcodex/rx6-final-antenna-audit, verified in_progress. Uses exact final native14105679819 SHA623d7be7b8438522b6b0f81fdec45801006997892ec07953b4687ed88b53d85a; all native stays cloud. Clears old metrics, runs original OpenROAD.CheckAntennas only; no route/repair/threshold edits. ODB/SDC before-after hash invariance and no replacement views required, native antenna metrics required. Derived artifactrx6-final-antenna-derived-43576971725 contains reports/JSON/log only. Sourcehw/soc/pnr/final_rx6_antenna_audit_flow.py is on experiment until tested. First local source-validation attempt failed an enum-text formatting assertion before any mutation; final flow uses only verified ODB/SDC enums. No native local work.

RX6 routedSTA43569629324 remains independent/inprogress. FreshCRC43561900502,CDR43571075470,SRAMLVS43566292104/43562021054,MBIST43573697024 still require results. Fullgoalopen.

---

# RX6 hold candidate routed: router DRC0 but antenna1net/2pins remain; STA started

43569629324 source12101bb1da5f82420b08b363ef707d2d08e55933: routejob132370971009 completed/success. Exact final routed-state reports router DRC0, antenna1net/2pins (NOT antenna closure). Initial39 reproduced by NSSOC_RESUMED_PINNED_DRT_ANTENNA_39. 159731instances,20SRAM,1134antenna cells,0padcells. Ten unsupported LEF58_ENCLOSURE/noCUTCLASS warnings remain; router DRC0 is not foundry signoff.

Safe14106655609 SHA30023bc4368caf39a3327cd0097b1feed3dd4862fa1314dea3a3bafe64c56829. Native routedDB14105679819 SHA623d7be7b8438522b6b0f81fdec45801006997892ec07953b4687ed88b53d85a remains cloud-only. Same-run routedSTA132392278204 started; await exact extracted timing, then diagnose remaining antenna from this exact saved database. Do not restart initial route or transplant old ECO. FreshCRC43561900502 separate/still live. Other liveCDR43571075470,LVS43566292104/43562021054,MBIST43573697024. All acceptance gates unchanged; fullgoalopen.

Receipt:docs/evidence/rx6-route-residual-antenna-20261114.json.

---

# Extracted timing rejects older electrical candidate; misleading clock labels fixed separately

43567570194 completed/failure. Exact finalroute DRC0/antenna0/0 but threecornerSTA fails: slow1390setup(-1.989753ns),2hold(-.356828ns);typ0setup,4hold(-.212935ns);fast0setup,98hold(-.251383ns). Cap105/109/113,slew708/272/144,fanout1416each(slow/typ/fast). SafeSTA14106081080SHA`04c1539e64b73d7e9d53f03d4aac401b43545b721d70c85672ede06c67842f0b`. NominalSPEFsha0a343a9739393cfe0b759e96b21a74241a1a4a7c4c6d7ae3ed3ea547d08d266e,capconservationpasses;RCminmaxunqualified. Receipt:docs/evidence/electrical-routed-timing-rejected-20261114.json.

Worstsetup remainsPCIe fold_word27→crc7,CPUinstr→RF,asyncreset,EthTXb_func→bank1. WorstholdEthRXwq_data9→bank0, NOT earlierRX6address-only target. Prioritize freshCRC43561900502 and separateRX6candidate43569629324 results before any old-instanceECO. Do notcall this oldcandidate timingclosed or transfer its metrics to newRTL.

Clock header contradiction resolved in upstream3.0.5corner.tcl: `if is_propagated` erroneously sets `is_virtual` printvariable, so report showedVirtualyes/Propagatedno. Fixed printassignment only in guarded source, no STA clock/SDC/SPEF/delay/limit edits. Cloud43575282471 sourceacb25e2ffa9c7ce0d65fd0e194bb54cc758074cd passed4truthstates+missing/duplicateanchor rejection; originalbug reproduced in2states. Safe14105737685SHAf0e730850a10485954b0d56837eb1f02ed85ca7dda766c8dbd3b928cf2c1f0ab. Integrated source/test; existingruns unaffected. Receipt:docs/evidence/routed-clock-report-label-controls-20261114.json.

Sixlivehandles43571075470,43569629324,43566292104,43562021054,43561900502,43573697024. Stop polling43567570194 aslive. Fullgoalopen.

---

# Electrical candidate routed with zero router DRC/antenna; exact routed STA now running

43567570194 source`0b0afcacd36d6223e0fba6ce1ddbf18312c955e8`: routejob132364639141 completed/success. Pinnedresume reproduced28antenna nets31pins, then2/2, then0/0. Fresh finalmetrics route__drc_errors=0,antenna__violating__nets=0,pins=0,flowerrors=0. Confirmed stale metrics removed/config unchanged. Final159612instances,20SRAMmacros,1018antennacells. Routepass elapsed~1h19m. Safe14105204176SHA`54cad8e84c4e919fc471203c4a43ef1000d52e53d628fc629f6394ba4dd453c8`; native14105074398SHA`7704bd4afb10dab17e6d15b1abc7290d80ca0663b55af6193a0802a4620f123f` stayscloud.

Same-run dependent routed-stajob132384337030 verified in_progress restoring exact routedDB. Await3corner extracted STA: zero setup/hold/cap/slew/fanout gates unchanged,clocks20/4/8/8ns. No timing pass yet. TenDRT-0349warnings: router skips LEF58_ENCLOSURE withoutCUTCLASS on Cont/Via/TopVia layers. RouterDRC0 does not cover those rules or independent foundry/full-chipDRC. No padcells in this core candidate. This is older five-driver electricalcandidate, NOT freshCRC43561900502 orRX6hold43569629324; do not transplant evidence.

Receipt:docs/evidence/electrical-route-zero-antenna-result-20261114.json. Poll43567570194 STA plus43569629324,43561900502,CDR43571075470,LVS43566292104/43562021054,MBIST43573697024. Fullgoalopen.

---

# MBIST second restore PID collision fixed; same1.26M checkpoint retry active

43573337312 failed in CRIU restore; followup43573539211 collected exact native diagnostic: `criu/log.c:430 pidfile: Can't open .../restored.pid: File exists`, followed by Cannot write pidfile/Restoring FAILED. Original dump includes the previous restore PID file. No simulator error or boot completion. Safe14104814119SHA`fb27a96d108a0feff659ce84e77637199a1318b68506429523592786cd2e2b8f`. FullCRIUlog14105725472SHA`a03213b9615963aff1b3c67b25a1d29d3e7513db062230f9e09b6dbd9e75b961`cloudonly. First failure safe14104843822SHA`a3641939cdf17db5eb2d76620ac9ff4aa0efe807a7d87d0a89fb50280ddd2eab` lacks detailedCRIUlog.

Fixed43573697024 source`27c496c5649c284e5cc1494792ef103c7fd427c7`, branchcodex/full-native-boot-continuation-two, in_progress at restore/simulation step. New outputPID`restored-RUN_ID.pid` must not exist; old files retained. CRIU detailed errors now extracted into safe result, full log retained cloudonly. SAME original1.26Mcheckpoint/input/runtime/hash/image identity, original28gates and3Mcyclebound, no restartfromzero. Actual restore progress/boot acceptance still requires result, not inferred from live step. Script on experiment branch; copied to integration only as dedicated source snapshot to avoid replacing older entrypoint.

Receipt:docs/evidence/full-native-restore-pid-fix-20261114.json; snapshot:scripts/resume_full_native_boot_from1260k.py. Poll43573697024 instead of failed43573337312/43573539211. Otherlive43571075470,43569629324,43567570194,43566292104,43562021054,43561900502. Fullgoalopen.

---

# Full native MBIST advanced to1.26M cycles; next exact checkpoint continuation launched

43558722004 completed/success as checkpoint infrastructure ONLY: passed=false,completed_boot=false,checkpoint_saved=true,stage_status=checkpointed_pending_boot.10800.323s segment,last_progress_cycle1260000. Safe14105022987SHA`43f3463da142dde3d0e5e9ca57d0292a8bf67286479b00656d69a39d9fb479de`; native14104748996SHA`875955125fb62aa659076191cf87496b58209fd56059d2bc1f38f24cf3aac6cf`cloudonly. Innernext-checkpoint.tgzSHA`8f480f6170a83b41ed1be10ef15ac5beae08b3f77e635575274e6f1ad6632181`; prefix10534bytesSHA`a2b5e52f0f115f5c17249a7eea6528f2b50814d1be91992f5b7b66714f5223e5`; CRIUimage_directory`images-43558722004`. No boot acceptance; uart/flash still0 during observed MBIST phase.

Next43573337312 source`5f4612b7a1aa09f8fafb3a0ffc3548b8c82f84fa`, branch`codex/full-native-boot-continuation-two`, verified in_progress. Exact parent chain/status/source/cycle/hash guards, restore images-43558722004; runtime/kernel/mappedfiles unchanged required. Input next-checkpoint.tgz renamed parent-checkpoint.tgz after restore/unpack verification so unchanged input cannot be uploaded as a fresh output checkpoint. Original full3Mcyclebound and28bootchecks/system+EthernetMBIST retained. Original boot checker/preparer/lock compared with frozen parent and unchanged. Native restore not yet proven by completed result. Safe prefixfull-native-continuation-result-43573337312, nativefull-native-continuation-checkpoint-43573337312; allnative stayscloud.

Receipt:docs/evidence/full-native-1260k-continuation-20261114.json. PollnewMBIST43573337312 plusCDR43571075470,route43569629324/43567570194/43561900502,LVS43566292104/43562021054. OldMBIST43558722004 terminal, do notpollaslive. Fullgoalopen.

---

# Internal clock topology/measurement completed; no missing clock edges in observed candidate

43572236262 source`e260cf027733c35302e1ac375b0d10a80ec69a24` completed/success. Safe14103694704SHA`b96721f2fa7ef446cbcfde835258d25b10d8c7dde97a112e447b742cba8ca8b9`. Prior43571981658 failed solely because one-to-one pairing assumption rejected real parallel clock devices; corrected by all shared-emitter positive/negative branch combinations, not arbitrary matching. Source and report: scripts/diagnose_cdr_internal_clock.py; docs/evidence/cdr-internal-clock-result-20261114.json.

Native acbuf15 waveform and original failure gates reproduced. Connectivity-only wire-R collapse identifies16cp-driven+16cn-driven HBTs,32branch combinations,8master/slave MOS-tail banks. Actual captured base voltages retain full RC. All branches have258rising/257falling expected edges. C master/slave source-relative crossings roughly14.76..15.36ps, versus receiver port~11ps. This establishes measured internal clock arrival for this rejected candidate, not missing-edge causation, C sampler gain acceptance, jitter/PVT qualification, closed-loop PLL or final PHY. Keep original sample times/limits. C history-dependent amplitude problem remains; inspect data/latch/gain path next rather than assuming clocks absent. Await ongoing acload12/16 isolated load screen43571075470.

Other six handles43569629324,43567570194,43566292104,43562021054,43561900502,43558722004 active at last poll. Fullgoalopen.

---

# Corrected clock-capture diagnosis: physical cp/cn were saved

Clock audit43571554607 source`df70272f91e5819edc20421868e6ef7e0fdd4382` completed/success. Safe14104249669SHA`3030d7a5065d48fea1a0857aa4a081dbce2944a0b8e2118e73aab84b68d49329`. Exact full acbuf15 raw reproduces original failed data/device gates. Both v(cp),v(cn) exist. Prior notes saying clock vectors were absent were incorrect: clk/clock substring search missed cp/cn. Corrected both settling scripts to include contract-bound cp/cn aliases. Full diagnosis source and report preserved in scripts/diagnose_cdr_saved_clock.py and docs/evidence/cdr-saved-clock-port-result-20261114.json.

Receiver port crossings:258/258 rising,257/257 falling; rising source-relative10.987..11.662ps,falling10.889..11.207ps. Differentialrange-0.29949..+0.27762V, commonmode1.28353..1.29335V. These are receiver port voltages, NOT internal latch-clock timing, PLL recovery, jitter qualification or timing acceptance. Original stimulus-referenced sampler thresholds/windows remain unchanged; do not subtract observed delay to obtain a pass. Existing captured internal device-base voltages may permit further stage diagnosis without new simulation once actual topology identified.

New acload12/16screen43571075470 still live at last poll; other six43569629324,43567570194,43566292104,43562021054,43561900502,43558722004 also live. Fullgoalopen.

---

# Exact CDR failure recovered; independent collector-load screen running

Native diagnosis43570807730 completed/success: original sampler/comparison and device gates reproduced exactly from full raw. acbuf15 eight HBT violations are active minimumVce0.2186..0.3017V vs0.4V floor, NOT excessive current. acbuf20 lowers selectorVce to0.0734..0.1273V and adds buffer/tail headroom violations plus three startupVce peaks1.603..1.609V vs1.6V ceiling. Do not relax those bounds. C sampler low-margin samples occur only when bits[k-2]!=bits[k-1] in the diagnosed interior history; not a proven clock-topology explanation. No internal clock measurement inferred.

Safe artifacts14103968849SHA6552ec7b2f30e515ffd107678c5ac5545ec6ca4f2257377eec2743a6f9ca1389,14103859118SHA48a9d9ea9ee5f656dc539a2507b7af58e1f4da3e0a93447d24a10faaaae5bfab. Results and next-run receipt:docs/evidence/cdr-native-failure-result-and-load-screen-20261114.json. Tested diagnosis source preserved scripts/diagnose_cdr_native_failures.py; needs frozen helper source ec52087 for reproduction.

Next screen43571075470 source`7e7b32d746ef5b19e7ed72ac23af2368b8fea624`, branch`codex/cdr-ac-load-original-bias`, observedin_progress. Two variantsacload12/acload16 keep ALL originalbench/bias sources byte-identical and only change four A/C collector widths8u→12u/16u relative to xor2 baseline (bd10_lowz8_xor2). Native topology and fourline-only guards retained. Pure source patch checks passed before dispatch. Original device/data/phase gates unchanged. This separates collector-load reduction from harmful bias increase; lower swing is a risk requiring actual measurement. ExistingRC/externalclock means no newlayout/PHYpass. Safe resultprefix`cdr-ac-load-result-only-VARIANT-43571075470`; mixed/native archives cloudonly. Read result-only first.

Six other live handles43569629324,43567570194,43566292104,43562021054,43561900502,43558722004. Fullgoalopen.

---

# Full saved CDR device/history diagnosis launched

43570807730 source`ec52087e74b97d707236035938df178180f27378`, branch`codex/cdr-native-device-history-diagnosis`, verified in_progress. Two cloud jobs restore original full raw waveforms for rejected acbuf15/acbuf20; no simulator rerun. Exact archive/raw hashes, candidate nx=2 binding, unchanged gates must reproduce saved results. Reports exact failing HBT metric/time/terminal voltages and four-bit history at original sampler phases. Safe artifacts`cdr-native-failure-derived-VARIANT-43570807730`. Native archives remain cloud-only. Implementation on experiment branch; integrate only after successful result. Receipt:docs/evidence/cdr-native-failure-diagnosis-launch-20261114.json.

Six prior routing/LVS/MBIST jobs still live at latest poll. Full production goal remains open.

---

# CDR comparison completed: current-only buffer change is insufficient

Diagnostic43570390846 completed/success; safe14104122995 SHA`f5c99f1b5635a011c56874959815b8d09850b49e518d9c542b7e4ca5d77a40b4`. Result saved in docs/evidence/cdr-ac-buffer-settling-result-20261114.json. Diagnostic success is not a PHY pass.

Exact preserved grid after rising[k],252 interior bits: transition A-buffer failures67/127 baseline,63/127 for BOTH acbuf15/acbuf20 by final117.1875ps grid point; passing transitions still ~101.6..117.2ps. C sampler failures64/252 unchanged, C buffer96/252 baseline and1.5x,89/252 at2x. Original strict sample gates remain authoritative; these conditional grid counts are different windows, not replacements. Stronger buffer modestly improves latency but leaves dominant errors and introduces device-limit failures. Neither candidate accepted.

Next: diagnose C sampler history/clock relationship and XOR selector operating-point violations before another current sweep. Saved captures lack clock vectors: do not infer clock timing from data alone; use actual topology plus a targeted cloud capture if needed. Native archives stay cloud-only. Existing six timing/LVS/MBIST jobs were still active at last poll; retrieve their final evidence before claiming closure. Full goal remains open.

---

# CDR A/C buffer current screens rejected; saved-waveform comparison running

43562981217 completed/failure. Both acbuf15 and acbuf20 simulate successfully and pass phase, but fail data and device limits. X wrong-sign samples383/765 for BOTH; Y below100mV587/588 samples. Failing HBT counts8/14; sampler A/C/D remain failing. No PHY acceptance, no new layout. Do not repeat unchanged current increases.

Safe result-only14103877257SHA`f9e9332b631252c132227b877b48b7593d95af88317ae3ac7b482d4a0c5cd466` and14103871330SHA`b39fb2fa31b2e955c00f7380e9a8b0d429f7b59847bbc63c5be589df5dbfee61` verified. Full results: docs/evidence/cdr-ac-buffer-rejected-result-20261114.json.

Diagnostic43570390846 source`7b6db8cfb6c50edb9d6330aed231cc833976cd8a`, branch`codex/cdr-ac-buffer-settling-comparison`: exact UI/16 saved grid for original xor2 + acbuf15 + acbuf20. No threshold or sample alignment changes. Mixed NPZ archives remain cloud-only. Safe artifact`cdr-ac-buffer-settling-43570390846`. Inspect conditional transition settling before next circuit change; diagnostic success alone is not acceptance.

Other six runs freshly verified in progress: RX6resume43569629324, electricalresume43567570194, SP43566292104, DP43562021054, freshCRCroute43561900502, nativeMBIST43558722004. No numerical timing/LVS improvement inferred from live job status. Full goal remains open.

---

# RX6 hold checkpoint verified and split continuation launched

Inventory43569490025 completed/success. Safe14104151119SHA`0d974e1bec75005424ef7e0ac94b81bd52587b9234245dc5e07c2a989ae965bb`; candidate drt-run-1ODB221904411bytes,SHA`329e6ef42702320243b595ab56554d5fc3fd3c63e93ff452faad0a206df36c82`. SDCsame5c65218b6106315c71d45c19eb61af09781607f0f438f2c7f99c4427884d24a4 but path`rcx/1-nssoc-cut10jrx6holdthree/soc_top.sdc`. Native14103417683SHA`361ca0f3c8fad45e6c8a8a4b49e828804cb48df8835651acb49932222f6e1c31`cloudonly.

Resume43569629324 source`12101bb1da5f82420b08b363ef707d2d08e55933`, branch`codex/resume-rx6-hold-antenna-pass`, dispatched. Same exactruntimeDRTscriptguard/skipinitialfullroute approach as43567570194, but MUST reproduce39antenna nets for this specificholdcandidate. Clears inherited metrics, originalconfig/clockunchanged. Route and RCX/STA split jobs, original strict zero gates. Artifacts`route-cut10j_rx6_ant_resume-RUN`,`routed-db-cut10j_rx6_ant_resume-RUN`,`routed-sta-cut10j_rx6_ant_resume-RUN`; nativefailprefixantenna-resume-incomplete-native-RUN. Neither continuation yet validated as success.

Receipt:`docs/evidence/rx6-hold-checkpoint-resume-launch-20261114.json`. Poll7live handles:43569629324,43567570194,43566292104,43562021054,43561900502,43562981217,43558722004. Old43538031308/43541234973 terminalfailure. Fullgoalopen.

---

# Ethernet RX6 hold candidate also timed out; separate checkpoint inventory running

43541234973 completed/failure, nativeRCX_STA_RC=124 at330min. IntermediateDRC0 after first antenna repair;39nets/41pins remain, secondrepair82diodes cut off during pinaccess. No final timing, so hold benefit not yet verified. Safe14104080998SHA`79cf09302f5cc660a21d05d0ca5dd6c7105395790bfa498856426e4df88dbfb6`; native14103417683SHA`361ca0f3c8fad45e6c8a8a4b49e828804cb48df8835651acb49932222f6e1c31`cloudonly.

Inventory43569490025 source`0aebe4c70dbf6c5273f23f2c2d821ad5c33ea430`, branch`codex/rx6-hold-route-recovery-inventory`, safe prefix`rx6-hold-recovery-inventory-43569490025`. Inspect exact drt-run-1ODB and candidateSDC hashes; never use electrical-only candidate hashes for this variant. Reuse split-resume method only once native readiness/identity established. First electrical-only resume43567570194 still running; do not duplicate it.

Receipt:`docs/evidence/rx6-hold-route-timeout-recovery-20261114.json`. Otherlive SP43566292104,DP43562021054,newCRCroute43561900502,CDR43562981217,MBIST43558722004. Bothold43538031308/43541234973 terminal, no longerpollaslive. Fullgoalopen.

---

# Saved antenna checkpoint continuation launched with separate RCX/STA budget

43567570194 source`0b0afcacd36d6223e0fba6ce1ddbf18312c955e8`, branch`codex/resume-pinned-antenna-pass`, active. Restore original base14068260482 then nativecandidate14102387358. Exact drt-run-1ODB SHA6613e8102b7a4076f1748b75447ece150ccf86818c06dc89b50ca42cb2b92b7e, candidateSDC SHA5c65218b6106315c71d45c19eb61af09781607f0f438f2c7f99c4427884d24a4. Initial state onlyODB/SDC/NL/PNL, all stale metrics removed; config unchanged.

Flow`hw/soc/pnr/resume_pinned_antenna_flow.py`: exact runtimeDRTscript SHA`d389d9e6d75bbb82552321f689d92a2e0392684142c11ffabe59c757ece59461` guard. Omit initial full drt_run ONLY; fresh check_antennas must reproduce28net violations before continuing original3-passrepairloop. Native restore behavior still needs result, no pass claim. Route19200s then routed_handoff; dependent separateRCX/STA19800s,355min each. Strict3cornertiming/electrical+DRC+antenna gates unchanged. Native failure archives retained. Safe route report excludesDRCgeometry files. Artifacts:`route-cut10j_ant_resume-RUN`,`routed-db-cut10j_ant_resume-RUN`,`routed-sta-cut10j_ant_resume-RUN`; failednative`antenna-resume-incomplete-native-RUN`cloudonly.

Receipt:`docs/evidence/antenna-checkpoint-resume-launch-20261114.json`. StillactiveSP43566292104,DP43562021054,freshCRCroute43561900502,CDR43562981217,MBIST43558722004,oldholdroute43541234973. Prior43538031308 terminalfailure, do notpollaslive. Fullgoalopen.

---

# Route recovery checkpoint located; implement resumed antenna pass next

Inventory43567101492 completed/success. Safe14103305888SHA`9e8ece69660c7d0b8cb99aa997cbad3a143766c7843db23e7d8876a0a31da3e1`. Saved checkpoint `hw/soc/out/impl-probe/rcx/4-openroad-detailedrouting/drt-run-1/soc_top.odb`,221619313bytes,SHA`6613e8102b7a4076f1748b75447ece150ccf86818c06dc89b50ca42cb2b92b7e`, after first antenna pass (28nets/31pins remain; intermediateDRC0). Native archive14102387358SHA`3f7e4ca94925a33d730cfe47b1f4487434c05b76e4c6e10e847f04317d3898e6`. Presence/hash verified, native restore still untested.

NEXT: create split cloud recovery flow. Restore original base14068260482SHAcf6a83685c33cdf4083786f0ab136ef1ea2666b44476521228aed5eed73d0855 then candidate archive overlay to sameabsolute workspace. State ODB must bind drt-run-1; SDC at rcx/1-nssoc-cut10jfivedriverresize/soc_top.sdc SHA5c65218b6106315c71d45c19eb61af09781607f0f438f2c7f99c4427884d24a4. Old state has STALE inherited route/antenna metrics; clear/recompute, not acceptance. Upstream LibreLane3.0.5 `librelane/scripts/openroad/drt.tcl` inspected: drt_run writes eachODB, initial `drt_run $i {*}$drt_args` then incr i, whilecheck_antennas/repair_antennas/drt_run. Adapt runtime script with exact anchor guard to omit first full reroute from this checkpoint, then fresh antenna check/repair. Native restart behavior needs validation; no pass claim from files. Separate route handoff and RCX/STA (avoid330min combined budget). Existing freshCRCroute unaffected; do not use old instance ECOs there.

Receipt:`docs/evidence/five-driver-route-checkpoint-result-20261114.json`. Stilllive SP43566292104,DP43562021054,newroute43561900502,CDR43562981217,MBIST43558722004,oldholdroute43541234973. Full goal open.

---

# Old five-driver route timed out; cloud recovery inventory running

43538031308 completed/failure, nativeRCX_STA_RC=124 after19800s. Initial detailedroute4h06m;244antenna nets/261pins. First repair424diodes and intermediateDRC0, then28nets/31pins. Second repair44diodes started, cut off during pin access. NO final route or extracted STA. Derived14102821860 SHA256`30ce5dfb1e35baa00e3da190ccfb5f83b346e2f4b9d53f7c2d9b7e7d87d24585`; native14102387358 SHA256`3f7e4ca94925a33d730cfe47b1f4487434c05b76e4c6e10e847f04317d3898e6`192.8MB, cloud-only.

Recovery inventory43567101492 source`a3907ddf599b5533187995ea8de00b35c60ec7c7`, branch`codex/five-driver-route-recovery-inventory`: inspect archive filenames/hashes and state view paths in cloud. Safe artifact`five-driver-recovery-inventory-43567101492`. Do NOT assume intermediate routedODB exists merely because logs show completedDRT; inspect saved states first. Next recovery must split/checkpoint stage budget; do not repeat unchanged330min run. Do not transplant this oldcandidateECO into freshCRCnetlist.

Receipt:`docs/evidence/five-driver-route-timeout-recovery-20261114.json`. Other live runs:SP43566292104,DP43562021054,newCRCroute43561900502,CDR43562981217,MBIST43558722004,oldholdroute43541234973. Full product remains unqualified.

---

# SP fullmacro mismatch localized; six-boundary comparison running

43564996899 completed/failure, extractionRC0/auditRC1:24Match,6NoMatch,1Skipped top;0extraction diagnostics. Both sides1211120recursiveprimitives (817450MOS+393670R), unchanged original/candidate CDL inventory. Tested reader hash87a75b402b35d7306153a66089c0f0105b4e50c4816c7c553d97219af6c41519 bound to actual candidate. Safe14102840450 SHA256`8aba5c22b51a18a6f7942427d2cdba5e48a65a8981c9806d917d2fed89f68e29`; native14101844940SHA`48f06a811262a9ae15a99ce5fd53c9e31503f450e3f90eae69e3135fffd1f120` stays cloud-only. No LVS pass.

43566292104 source`c226118b038f4180ce97452b9e469e873b37fd83`, branch`codex/sp-sram-engineering-six-boundaries`: sameSPreference, flatten exactly observedCBUFX8,CINVX2,CINVX8,FILLCAP4,FILLCAP8,WLDRVX8 on both sides. Count must remain1211120 before/after EACH side. No geometry/CDL/net/body/port edits. This tests hierarchy representation, not an acceptance waiver. Native18000s/workflow350min. Derived prefix`sp-sram-engineering-reference-normalized-derived-sp-deep-43566292104`; native counterpart cloud-only. Receipt:`docs/evidence/sp-sram-fullmacro-boundaries-20261114.json`.

Other six runs remain active:DP43562021054,newroute43561900502,CDR43562981217,MBIST43558722004,oldroutes43541234973/43538031308. Full product goal remains active.

---

# Independent SP engineering reference fullmacro comparison running

43564996899 source`867aa31021be8d6fec40ebb5afe2d7bcdc85a354`, branch`codex/sp-sram-engineering-reference-v1`. Five explicitly reversible R statement edits only: bitcellR0/R1metal2,R2metal3 W0.2/L0.6; standaloneMET2RES/MET3RES eachW0.26 unchanged, only layer-model identity explicit. Original GDS/CDL immutable, terminal tokens unchanged. Strict reader, metal1 controls, ports/bodies unchanged. Full recursive original/candidate CDL inventory must agree before native run. Original SP hierarchy retained, NO DP six-cell flatten or70110 count assumption. Native18000s/workflow350min.

Safe result prefix`sp-sram-engineering-reference-v1-derived-sp-deep-43564996899`; native counterpart remains cloud-only. Bind actual candidate reader to tested87a75b402b35d7306153a66089c0f0105b4e50c4816c7c553d97219af6c41519 when result arrives. Successful engineering comparison is not vendor qualification or full-chip acceptance. Receipt:`docs/evidence/sp-sram-engineering-reference-launch-20261114.json`.

Continue DP43562021054, route43561900502, CDR43562981217, MBIST43558722004, oldroutes43541234973/43538031308. Goal active; full production not achieved.

---

# SP direct-pin recovery passed; original SRAM LVS remains failed

43564703460 completed/success source`daf24ca240958f2ed85099b48f72bb0b44904487`; safe14101134348 SHA256`9ef327edaad1aaa5c6d605e127c36c8fb658d464a9da3836cf6f47b5503314e2`. Native saved DB reused, no extraction rerun. One duplicate expanded net name confirmed in original layout; direct Net.each_pin avoids merging conductors by label. All three R have unique two-external-endpoint correspondence: R0/R1 -> res_metal2, R2 -> res_metal3; each W0.2/L0.6um versus original genericW0.26. Isolated body ports still absent in layout vs NW/PW reference; NEVER alias those. Tested script now on integration.

Next: use this independent SP map for a separately versioned engineering reference, preserving original GDS/CDL and strict fullmacro comparison. SP standalone MET3RES width is0.26 (NOT DP0.24); no SP fullmacro correction/acceptance yet. Determine exact SP primitive counts/hierarchy, do not transplant DP70110 assumption. Current DP engineering comparison43562021054 remains running. Receipt:`docs/evidence/sp-sram-direct-pin-result-20261114.json`.

Keep live route43561900502, CDR43562981217, MBIST43558722004 and oldroutes43541234973/43538031308. Full product remains unqualified.

---

# SP original bitcell LVS failed; saved-database endpoint recovery running

Run43563445727 completed/failure. Independent audit: one NoMatch,9primitives both sides,0extraction diagnostics. Three original generic R W0.26 vs extracted twoM2/oneM3 W0.2 (L0.6). Endpoint diagnosis stopped with AssertionError; expanded-name uniqueness assumption suspected. Duplicate VSS port labels observed; NEVER merge nets by those labels or alias body ports.

Recovery43564703460 source`daf24ca240958f2ed85099b48f72bb0b44904487`, branch`codex/sp-sram-direct-pin-diagnosis`, reads saved native14101208963 only in cloud. Uses actual netlist Net.each_pin/NetPinRef.pin directly, preserving duplicate names; no repeated extraction or reference edit. Await derived `sp-bitcell-endpoint-diagnosis-43564703460`; require native process exit0 and inspect mapping before using it. Original failure receipt:`docs/evidence/sp-sram-bitcell-failure-recovery-20261114.json`.

Other six live runs unchanged:43562021054,43561900502,43562981217,43558722004,43541234973,43538031308. Full PHY/timing/current full-chip production gates remain open.

---

# SP SRAM owner diagnosis passed; separate SP bitcell comparison running

**43563284302 completed/success**, source`b7adb2000f01d80a24532e8dc91ea2057d07fd4e`, safe14100549566 SHA256`f63436b55538ad4ac67d374ea10d12cc9c355bf3ba05c96441f0cebcf890d6a6`. Original SP reference393670genericLVSRES:393216in131072bitcells(3each),64MET2RES,384MET3RES,6metal1dummy. All original W0.26/L0.6um. Physical marker leaves show bitcell-typeM2/M3W0.2 and standaloneM2/M3W0.26. **SP standalone metal3 is0.26, not DP0.24**; independent SP mapping required. No whole-macro polygon expansion/topology/LVS acceptance. Receipt:`docs/evidence/sp-sram-resistor-owners-result-20261114.json`.

**43563445727**, source`60dd2a564467738d1fc55ef628bf751443896e2e`, branch`codex/sp-sram-original-bitcell`: original physicalRM_IHPSG13_1P_BITKIT_CELL vs originalCDLRM_IHPSG13_2048x64_c2_1P_BITKIT_CELL, explicit top-name translation only. ThreeR+sixMOS expected. Strict widths/classes/ports and no-merge correction; native1200s bound. Actual netlist endpoint mapping integrated (not xref display circuits), no body aliases. Do not call successful diagnosis LVS acceptance; inspect audit and mapping. Native artifacts cloud-only, derivedprefix`original-sp-sram-bitcell-derived-`.

Long runs remain active as before: newroute43561900502, DPcandidate43562021054, MBIST43558722004, oldroutes43541234973/43538031308, A/Cbuffer43562981217. Keep full serial PHY, qualified RC/Liberty, current full-chip verification and external manufacturing approval open.

---

# Current SP SRAM independently inventoried next; DP evidence is not transferable

**43563284302**, source`b7adb2000f01d80a24532e8dc91ea2057d07fd4e`, branch`codex/sp-sram-original-resistor-owners`: original **RM_IHPSG13_1P_2048x64_c2_bm_bist** GDS/CDL pins restored from package663146895 only in cloud. Script`scripts/diagnose_sp_sram_resistor_owners.py` enumerates original hierarchical generic resistor owners and physical marker-leaf dimensions. Full top polygon expansion intentionally omitted; no LVS/connection/production claim or source edits. Require no unresolved CDL child models. Receipt:`docs/evidence/sp-sram-resistor-owners-launch-20261114.json`.

Do not extend DP bitcell mapping or candidate43562021054 to the four SP macros without independent evidence. Continue the live freshroute43561900502, DPcandidate43562021054, MBIST43558722004, oldroutes43541234973/43538031308 and A/Cbuffers43562981217. No same-input reruns; no local native files. Full product goal remains active and unproven.

---

# Exact reader controls passed; targeted A/C buffer circuit screens running

**43562548073 completed/success**: all10actual-CDL CustomReader positive/layer/W/L/open controls passed, nativeRC0. Safe14100384146 SHA256`2d34f811c1557b044eaaec0436035555bf8466c21cfc6c2880436e01357ac62c`. Candidate reader SHA256`87a75b402b35d7306153a66089c0f0105b4e50c4816c7c553d97219af6c41519` must match actual engineering macro43562021054 result before binding. Receipt:`docs/evidence/sram-reference-reader-controls-result-20261114.json`.

**43562679420 completed/success**, source`10eba9d8c228d5146df70ba37e78b2fc5ccda8dd`, safe14100379062 SHA256`86c5edf695e8a93a773bb441c6d238ab897e70ef2dad1e6e113a7b98facca056`. Exact-grid A sampler stable100mV at39..47ps on transitions; bufferA67/127(xor2),73/127(xor3) transitions still not stable by117.1875ps, those stable reach109..117ps. No clock vectors saved; selector clock remains unmeasured here. Some C sampler late margins also fail. Sampled settling is not continuous/native acceptance. Receipt:`docs/evidence/cdr-buffer-settling-result-20261114.json`.

**43562981217**, source`27a6dc7c4ae918c7d8a3888701e5b2ae26e254f3`, branch`codex/cdr-ac-buffer-current-resistance`: two isolated screens on failedxor2 baseline. Only four A/C collector resistor widths8->12/16um and two ibda/ibdc reference bias1->1.5/2mA change. All other topology, actual multiplicity binding,3mA/emitter and original sampler/data/phase/device gates remain. NominalI*R preservation is a hypothesis. ExistingRC/externalclock retained forscreen only; no newlayout or closedloopclaim. Safe result-only artifact prefix`cdr-ac-buffer-result-only-`; mixed NPZ/native archives remain cloud-only. Receipt:`docs/evidence/cdr-ac-buffer-screen-launch-20261114.json`.

Scripts for successful reader/settling diagnoses are now on integration. Continue live routes43561900502/43541234973/43538031308, fullmacro43562021054, MBIST43558722004. Full production objective remains open.

---

# Reader qualification and CDR settling diagnostics launched

**43562548073**, source`5ce444217f111bad822c9cf44a17e0645b7cc1c9`, branch`codex/sram-reference-reader-controls`: actual CDL through exact candidate CustomReader, then native independent graph comparison. Ten positive/layer/W/L/open controls. When finished, bind reader_candidate_sha256 to engineering macro reader hash; do not treat isolated policy tests as whole-macro signoff. At observation native runtime install stage live.

**43562679420**, source`10eba9d8c228d5146df70ba37e78b2fc5ccda8dd`, branch`codex/cdr-buffer-settling-diagnosis`: frozen failed XOR2/3 native samples remain cloud-only; exactUI/16 phase grid quantifies A/C sampler-to-buffer settling by bit transition. No new simulation/layout/polarity/gate changes. Metric is stable signed100mV through last sampled phase, not continuous-time/PHY acceptance. Use to select concrete next circuit experiment; do not repeat blind XOR size sweeps.

Receipt:`docs/evidence/reader-cdr-settling-launch-20261114.json`. Five long runs43561900502,43562021054,43558722004,43541234973,43538031308 verified live this turn; continue exact polling. Full production objective remains open.

---

# Strict native resistor negative controls passed

**43562168662 completed/success**, source`425b317cbd0dc7c5e82fd31a3806febdcaaf087a`, safe14100796355 SHA256`4fa2c9ca950e00f7c564f7d27ca7c92884c1b03a2e370fa5c8927259440f41aa`. All10native verdicts checked: both metal2/metal3 positive graphs match; wrong layer/W/L/open each rejected. Native returncode0, exact fixed RES2 class SHA256`1f9d1328eb1af5a534ff68a5cbc263513e305ece27bb87b75ef4b9454f45236f`. Scope is comparator policy only, not full deck-reader/candidate-macro/signoff qualification. Script now on integration; receipt:`docs/evidence/sram-reference-resistor-controls-result-20261114.json`.

Fresh route43561900502 and engineering-reference macro43562021054 remain the active next tasks below; poll exact handles. Do not rerun comparator controls unchanged or infer full LVS closure.

---

# Fresh routed candidate and SRAM engineering reference now running

**43561900502**, source`b1626c18095a9a9c7a06b3cb1bd508a4a0ba7f19`, branch`codex/crc-order-fresh-antenna-route`: exact fresh CRC handoff14100640319 pinned, now native route stage. Legalize/global/detailed route with antenna repair5/5 and unchanged ratios, DRT16; dependent nominal extracted RC and standalone three-corner STA; strict zero timing/electrical/DRC/antenna gate. No old instance ECOs. Native data retained cloud-only.

**43562021054**, source`70ebe8dca3b28d91a259f49bfee6b5b57c219f6e`, branch`codex/sram-engineering-reference-v1`: strict full-DP-macro engineering-reference comparison. Script`scripts/run_sram_engineering_reference_v1.py`; eight R statements across three cells change only proven layer/W tokens, original CDL/GDS unchanged. Exact reversibility and unchanged terminal assertions; no body aliases, no ports/tolerance waiver. Candidate result explicitly separate from original vendor/current-chip acceptance. Original70110primitives preserved.

**43562168662**, source`425b317cbd0dc7c5e82fd31a3806febdcaaf087a`, branch`codex/sram-reference-resistor-controls`: exact Ruby RES2 strict layer/width/length/open native rejection controls. Inspect all10verdicts, not just green workflow; not full macro/deck-reader/signoff proof.

Receipt:`docs/evidence/fresh-route-sram-reference-launch-20261114.json`. New experimental workflows stay on experiment branches. Long MBIST43558722004 and old route candidates43541234973/43538031308 were verified live this turn. Poll exact handles; do not relaunch based on observation delays. Full serial PHY, current-chip LVS, final qualified timing/RC and manufacturing remain open.

---

# Fresh CRC deep repair completed: route the new pinned handoff next

**43550440744 completed/success**, exact source`ecbcf43200413fc63844bbd20a7532f87af54216`. Both deep setup and hold repair completed; native handoff **14100640319**, SHA256`f724a289dc08812190d1aac64bfd1b4fafceeaca71c734ed578ca41d96a62f7c`, retained7days, cloud-only. Derived report14100400861 SHA256`d4b77f873736fe69c70c665478c465e32a645bb80cc57d3a9ca8cd62b7a893c9` inspected; contains logs/reports/TCL/config/flop map, not native DB/netlist.

Same-candidate estimated PCIe worst setup improved **-1.123 -> -0.264ns**. Remaining reported slow CPU setup~-0.15ns, fast Ethernet RX hold~-0.02ns. These are **post-global-route estimated parasitics, not routed/extracted acceptance**, group table values rounded and not full violation counts. Receipt:`docs/evidence/crc-order-deep-repair-result-20261114.json`.

**Next physical action:** launch fresh antenna-aware detailed routing and extracted RC/all-corner STA from this exact handoff. Do not transplant old cut10j instance ECOs. Preserve antenna ratios; old3iterationsleft1violation, so evaluate additionaliterations. No downstream route has been launched for this handoff yet.

Latest SRAM endpoint diagnostic succeeded as documented below; original full LVS still fails, corrected engineering reference candidate not yet launched. MBIST43558722004 and old route candidates43541234973/43538031308 remain live. Full serial PHY and manufacturing objective remain open.

---

# SRAM bitcell endpoint correspondence proven; original LVS still fails

**43561481053 completed/success**, source`31c39226b470f7fd07d14f2788b0fbe74c2e4ec0`, safe14100646223 SHA256`5b740aa78dda74bad16c0ca0478f7d471c8e42a3ac1953af6967be6e60643cfb`. Read-only original DB: each of six resistor endpoints has two named external anchors, uniquely paired. **R0/R1/R3/R4 -> res_metal2; R2/R5 -> res_metal3; all L0.6 W0.2**, versus original generic LVSRES W0.26. Original schematic MOS bulk pins anchor PW/NW; isolated layout body nets lack external pin labels. Do not invent body aliases. Working script`scripts/diagnose_sram_bitcell_endpoints.py` now on integration; uses actual db.netlist/reference circuits, not xref display circuits.

Failed harness runs43561017033/43561129891/43561263620/43561370062 are terminal and rejected, including two cleanup aborts despite JSON output. Receipt:`docs/evidence/sram-bitcell-endpoint-mapping-20261114.json` contains sources/reasons. No need to rerun this diagnosis unchanged.

Next: versioned engineering reference candidate using proven layer/width mapping plus previously established standalone MET2RES/MET3RES ownership, strict full-macro comparison in well/tap context, wrong-width/layer/open controls. No geometry changes, no body aliases, no tolerance waiver; candidate correction is not vendor approval. **No corrected candidate has yet been launched or accepted.**

Continue exact live handles MBIST43558722004, CRC deep repair43550440744, old routes43541234973/43538031308. Native data stays cloud-only. Full PHY, final timing, current-chip LVS and manufacturing remain open.

---

# Original SRAM bitcell: strict mismatch localized; endpoint mapping launched

43559617022 completed/success as a diagnostic, **LVS audit FAIL/NoMatch**. Fourteen primitives on both sides. Six reference LVSRES L0.6 W0.26 versus extracted four metal2 and two metal3 L0.6 W0.2. Reference additionally has NW/PW ports absent as separate extracted ports. Eight MOS pairs are marked mismatch; dimensions alone must not be taken as topology proof. No extraction diagnostics. Safe14099104530 SHA256`76d38343e3a35e5d5ada715372d3e1c987fc7a6b7a9ae8bff1e72d313d6145ad`; native14099039829 SHA256`b99ccd77e73bcf774597d9a67c030a1a89f18ae0a154e97f512805c354c6a563` remains cloud-only.

Next read-only cloud diagnosis **43561017033**, source`6650b1c1b558b319be5fb4d7904ed1d48dcf19cd`, branch`codex/sram-bitcell-endpoint-diagnosis`: exact original DB SHA256`c367b0565c64b00eedd2510d465d9c0d9cba64a7c2f79e4c04b5a9389bd49598`, mapping by identical named external resistor terminals where unambiguous and MOS body-port inspection. No class/width/geometry/port edits. Inspect result before versioned candidate reference correction; do not guess R0..R5 layers or waive NW/PW. Evidence:`docs/evidence/sram-original-bitcell-result-20261114.json`.

Live MBIST43558722004, fresh CRC deep repair43550440744, older routes43541234973/43538031308. Final timing, full current-chip LVS and serial PHY remain unaccepted.

---

# Fresh CRC candidate: preliminary timing available; deep repair running

Run43550440744 source`ecbcf43200413fc63844bbd20a7532f87af54216` reached deep setup repair. Safe artifact14099407422 SHA256`479b5d7f13488c2ba6a271058f8732cc391a9b5076b5da00a580445d01fbdc3f` contains post-global-route estimated STA, not final routed acceptance. Worst traced PCIe path is packet_accepted_o -> receive_ownership.head_last[2], slack -1.123ns. Do not infer a final improvement against older extracted-route measurements. Evidence:`docs/evidence/crc-order-preliminary-timing-20261114.json`. Wait for exact fresh deep-repaired handoff before antenna-aware routing/RC/STA; old instance ECOs must not be transplanted.

Bitcell43559617022, MBIST43558722004 and older physical candidates43541234973/43538031308 remain live at observation. Full PHY, current SRAM/chip LVS and final timing remain open. Native artifacts remain cloud-only.

---

# Latest archived SRAM RC audit — conservation and independent MOS topology passed

**43560070099 completed/success**, source`526c35599625cbcb093f0617d4aed09976f2d807`, safe artifact14099668660 SHA256`8e6818c2766f129b50d07f56b03427bcfd93e2c3187ebd55a9f3960fcd1f3c46`. Archived alternative DP8TSRAMDP256x16:37076MOS,237334R,1215822C. After resistance-component projection,155342capacitance pairs:0missing,0extra,0changed within1e-23F+1e-5relative tolerance. Independent schematic topology proof:37076devices,10272nets,88ports, exact net bijection/MOS edge multiset without body aliases. Positive resistor count explicitly checked. Evidence:`docs/evidence/archived-sram-rc-independent-result-20261114.json`.

This closes the **scoped connectivity/conservation audit only**, not physical value/corner calibration, junction geometry, Liberty, current vendor SRAM/chip binding or manufacturing approval. Native RC netlist SHA256`57f426ae891d1551d3d8d752d1dec75dacb3887b403509699b8f8d1785e930ad` remains in native artifact14099637041 cloud-only. Do not rerun extraction unchanged; reuse pinned native result for subsequent calibrated simulation work. The large extractor report was never downloaded locally.

Original bitcell43559617022 and full native MBIST43558722004 remain the active targeted tasks. Other physical runs43550440744,43541234973,43538031308 need continued exact polling. No current-chip LVS/timing/PHY closure claimed.

---

# Latest RC result — archived alternative extraction completed; independent audit running

**43534692191 completed/success**, source`2b9714c3c9c9ffb6e47313c7b96d09f74435dd98`, after extra32GiB cloud swap. It extracted the **archived alternative DP8TSRAMDP256x16**, not a current-chip vendor SRAM. Do not poll it as live or transfer its result to current-chip signoff. Native14099637041 SHA256`d937d7733a8fb8ffebed9ee61b6923c5d66c75284ed33e549a3493e8eb2e3404` stays cloud-only; large report14099432476 has not been downloaded locally.

Independent audit **43560070099**, source`526c35599625cbcb093f0617d4aed09976f2d807`, branch`codex/sram-full-rc-independent-audit`, observed completed. Hash-pinned native RC, prior CC artifact14082854262 and independent schematic14069436539. Tests37076MOS identities/parameters/ordered terminals, no resistor shorts or split reference nets, anchored passive networks and pair capacitance conservation; then reruns independent CC MOS topology proof, no body aliases. Original GDS identity required on both. Native payloads stay cloud-only; output JSON only. Inspect actual resistor count is positive as well as conservation result before accepting any RC-network claim. Even a pass does not qualify values/corners, junction/metal calibration, Liberty, present-chip binding or manufacturing. Evidence:`docs/evidence/archived-sram-rc-extraction-audit-launch-20261114.json`.

Original bitcell43559617022 remains live; MBIST43558722004 live. Other physical runs43550440744,43541234973,43538031308 still require fresh polling. Old flat43529228292 and strict fullmacro43553707234 are terminal failures, not pending.

---

# Latest native task — bounded original bitcell comparison running; old flat job timed out

**43559617022**, source`b75511764c3b131039325a05a142b98b9271e971`, branch`codex/sram-original-bitcell-lvs`, job132340149751, is live in native comparison. Script`scripts/diagnose_original_sram_bitcell.py` restores pinned original package and KLayout, applies the independently tested resistor no-merge switch correction, enables strict reference LVSRES L/W comparison, and isolates original CDL bitcell with only its subcircuit top name translated to GDS RM_IHPSG13_2P_BITKIT_CELL. It asserts6resistors+8MOS reference primitives, preserves dimensions/connections and runs native extraction with port audit. No layer guesses, width edits or class collapse. Result emits device pairing class/parameter metadata and port names, no netlist. Successful workflow means diagnosis complete, not LVS acceptance. Native artifacts stay cloud-only.

**43529228292 is now terminal/failure in both children.** Flat child132242493732 timed out at18000s, with no completed LVS DB/verdict. Do not poll/restart it as live or call it a pass. Safe derived14099936774 SHA256`5d0d13bd234c2b42ab4db0a2c0cde7fb2a35d65fa656581580199095d2a60678`; native14100130986 remains cloud-only. Evidence:`docs/evidence/sram-original-flat-timeout-20261114.json`.

Live long MBIST43558722004. Other live CAD:43550440744,43541234973,43538031308,43534692191. Re-poll exact handles before interpreting. Full manufacturing-ready objective remains open.

---

# Latest physical ownership — GDS cell names located; isolate bit cell next

**43559302585 succeeded**, source`85e28d9a82d1b3d7933a82847a24261417448d6c`, safe artifact14099392016 SHA256`d172c8821e7f34cf0972a34571991e3601a25f165b39f15f2bba6bec18c024c3`. Physical resistor owner leaves: lvsres_db_0x0283509a=M2 .6x.2; lvsres_db_0x02834b9a=M3 .6x.2; lvsres_db_0x0400b71a=M2 .6x.26; lvsres_db_0x263f099a=M3 .6x.24; lvsres_db_0x04007e9a=M1 .6x.26. GDS bit-cell names include **RM_IHPSG13_2P_BITKIT_CELL** and **RM_IHPSG13_2P_BITKIT_CELL_SUB**, whereas CDL uses **RM_IHPSG13_256x16_c2_2P_BITKIT_CELL**. Evidence:`docs/evidence/sram-resistor-physical-owners-20261114.json`.

Next concrete task: bounded native extraction/comparison of the original bit cell with explicit top-name handling and strict ports/primitive inventory, to establish the six resistor instances' physical layer correspondence before a versioned reference correction. Do not guess which R0..R5 maps to metal2/metal3 from aggregate counts. Do not collapse all resistor classes, relax widths, or adopt a layout-derived reference as independent signoff. Original GDS/CDL stay frozen; diagnostic controls remain distinct from acceptance. Existing native artifact14099740595 supplies exact original inputs and runtime. No new native job launched for this bit-cell task yet.

Full MBIST43558722004 remains live, five CAD handles as below. All native data stays cloud-only.

---

# Latest resistor ownership — three reference cells explain the remaining inventory

**43559140090 succeeded**, source`b0748dea6d3932fe7673d28c135b9ac43254f5ca`, safe artifact14099766973 SHA256`d02d8725ea0f3681d302f31fac420fd7a9b9c426ff92655ca88472f28d6c8d1f`. Original CDL recursive24822resistors and every child model resolve. Owners: RM_IHPSG13_256x16_c2_2P_BITKIT_CELL has6 direct resistors R0..R5,24576total; RSC_IHPSG13_MET2RES has1,16total; RSC_IHPSG13_MET3RES has1,192total. All useW2.6e-7,L6e-7. Matching metal1 RSC_IHPSG13_CDLYX1_DUMMY has1,38total and exact original geometry. **The other three CDL cell names have no exact GDS cell match**, so aggregate counts must not be used to invent instance/layer correspondences. No source correction or LVS acceptance yet.

Expanded cloud ownership diagnostic **43559302585**, source`85e28d9a82d1b3d7933a82847a24261417448d6c`, same branch`codex/sram-resistor-reference-owners`, queued at latest check. Exports original GDS cell-name and direct resistor-marker ownership counts plus recursive dimension summaries, no coordinates or connectivity. Inspect this before choosing a strict source correction or bounded local topology experiment. Evidence:`docs/evidence/sram-resistor-reference-owners-20261114.json`.

Full native MBIST43558722004 and physical CAD runs retain their exact handles below; re-poll before interpreting. Do not mark the chip or SRAM LVS accepted from these diagnostic successes.

---

# Latest SRAM diagnosis — original marker dimensions now match extraction one-to-one

**43558886103 diagnostic succeeded**, source`ea631c8c991a6f0538bb21f71f05e686886df462`, safe artifact14099676514 SHA256`63ebc8a05e3c7c1cb233c3147e2310d635389970e47098a8f8d0c1ae7e1e0e7a`. With strict unmerged resistors, original geometry exactly matches extracted dimension/count inventories: metal2=16384(.6x.2)+16(.6x.26); metal3=8192(.6x.2)+192(.6x.24). Reference has24784 generic LVSRES(.6x.26) instead.38 metal1 LVSRES(.6x.26) and all MOS dimension/count distributions agree. **This is not topology or full LVS proof**; no reference/GDS edits made. Evidence:`docs/evidence/sram-unmerged-dimension-diagnosis-20261114.json`.

Next cloud diagnosis **43559140090**, source`b0748dea6d3932fe7673d28c135b9ac43254f5ca`, branch`codex/sram-resistor-reference-owners`, observed completed. Reads original pinned CDL/GDS from native artifact only in cloud, counts original resistor ownership recursively, and reports cell names/instance parameter metadata plus per-cell original geometry dimensions. Exports no connectivity/netlist/geometry coordinates. Require original hierarchical resistor count24822 and no unresolved child models; use ownership evidence before proposing any reference/geometry correction. No class collapse or dimension tolerance waiver.

Long full MBIST **43558722004** and five CAD jobs remain the live handles from prior section; refresh before acting.

---

# Latest SRAM result — merge fix preserves70110 devices; top LVS still fails

**43553707234 is terminal/failure**, source`c077726eb378897ef2bf2b2e10bb8c6333195111`; do not poll it as live or rerun unchanged. Strict switch correction produced the expected **70110 recursive devices on both sides**, unchanged by selective flatten. Final audit:25Match,1NoMatch(top), no extraction diagnostics. Counts alone do not prove connectivity. No tolerances/ports/geometry/reference were waived. Evidence:`docs/evidence/sram-strict-merge-result-20261114.json`.

Diagnostic **43558886103**, source`ea631c8c991a6f0538bb21f71f05e686886df462`, branch`codex/sram-strict-merge-top-diagnosis`, observed in_progress. Reads only the exact new native database in cloud (artifact14099740595 SHA256`815d7babfb54232f89de61f45a6b1b2bc181cfe2c7d2158d5e521c1eb62cf4c7`, DB`dc81844b99e5b7b73898e6e8acebc71677d2d3934707b07c272d550696e22f0d`), exports bounded mismatch and hierarchy inventories, compares original metal2/metal3 marker polygon dimensions one-to-one now that resistors are unmerged. A diagnostic pass is not LVS acceptance. Inspect remaining class/width/topology causes; do not collapse metal classes or waive widths.

Full native MBIST continuation **43558722004** remains the live long run from the preceding section. Other live CAD:43550440744,43541234973,43538031308,43529228292(flat child),43534692191. All native data remains cloud-only.

---

# Latest continuation — full native MBIST continuation is running

**43558722004**, source`7d118a79f0bdfab6aa60b5bccb1cdb9dd836e2b8`, branch`codex/full-native-boot-continuation`, observed **in_progress**. Script`scripts/resume_full_native_boot.py` restores the real full-chip process from pinned native artifact14099590587 (SHA256`e6bebcf73c67bed72610b3d903ca91bd4037e665564659d926b059cfefd1c393`) and result14099221726 (SHA256`d6286a1a89a173c7aa8ca2818d6e9043cea026a3c4b6d6a52afa6c6c5901dcec`). Original netlist, firmware, PDK models, 3million-cycle bound and all MBIST/28-check gates remain. This is not a start-from-scratch run or memory preload.

Prerequisites passed:43557919707 matches the **3 original log lines through20000cycles** after separate-runner restore; this is bounded output agreement, not exhaustive state equivalence or full MBIST. Corrected43558336660 normal native exit0+completion+trace passed, while SIGTERM exit0 and SIGKILL exit-9 were correctly rejected as incomplete. Complete derived evidence:`docs/evidence/full-native-checkpoint-qualified-continuation-20261114.json`.

Long segment runs for up to10800s of simulation. On actual process exit, require original boot_checks with actual waitpid exit code, all MBIST/PCIe/28-check banners, no fatal/error and unchanged sources. On segment time budget, save the entire process and emit **checkpointed_pending_boot**, `completed_boot=false`, `passed=false`, `checkpoint_saved=true`; a green workflow in this state is NOT boot completion. Derived artifact`full-native-continuation-result-43558722004` contains result and log; native artifact`full-native-continuation-checkpoint-43558722004` remains cloud-only.

If checkpointed: pin exact next artifact IDs/hashes and resume its image_directory (images-RUNID) with exact runtime/file identity. The next harness must accept the validated checkpoint_saved state instead of requiring passed=true, bind the new parent source/run, and use the new image_directory, preserving all final gates. Do not mistakenly restart from the old10000cycle checkpoint. Current native script is first-segment-specific and must be adapted with those pins for the next segment. If completed_boot=true, independently inspect final report/log and provenance before calling this scoped functional boot closed; no SDF, serial PHY, memory fault qualification or manufacturing acceptance follows.

Six physical CAD handles remain as in the re-polled snapshot. Continue exact live jobs; original43558139164 is terminal/failure (normal child passed, obsolete SIGTERM -15 expectation failed). Native data stays cloud-only.

---

# Latest correction — SIGTERM may return zero; completion evidence required

Exit-control run43558139164 SIGTERM child **failed** its assumed -15 expectation: the real restored VVP returned **0** after SIGTERM. Subreaper/waitpid worked; this is why exit0 alone is insufficient. The control failed closed, not a chip pass. Evidence: `docs/evidence/native-vvp-sigterm-zero-exit-20261114.json`, safe artifact14099185767 SHA256`6985e162d1562918fbeb5da4db5bc29d57f876287f188c9fe67e3a8ce499a26d`.

Corrected controls **43558336660**, source`292a3313f7c0fca20c3fa65cc5de910003083162`, branch`codex/native-checkpoint-exit-status`, dispatched/queued at observation: normal requires native exit0, completion marker AND identical full trace; SIGTERM/SIGKILL require missing completion and rejected simulation; SIGKILL additionally requires native -9. Do not replace this with an exit-code-only gate. Original full-chip boot_checks already requires MBIST/PCIe/28-check banners and no fatal messages; preserve those checks unchanged in long continuation.

**43557919707 full-chip prefix is still live** in dump stage. Require its successful restore/equality plus corrected exit controls before long native MBIST continuation. Previous normal exit-control child132335564397 was still live; do not cancel or mislabel it. All native payloads remain cloud-only; no manufacturing signoff.

---

# Latest continuation — native exit-status controls running

Full-chip prefix qualification **43557919707** is still live in dump stage; do not restart. A second prerequisite **43558139164**, source `241ecd5640abc2a2f4e83f139faf76924ff858f9`, branch `codex/native-checkpoint-exit-status`, tests actual restored native process exit collection. Python becomes a child subreaper, checks parent identity, and uses waitpid: normal native execution must exit0 with exact trace; forced SIGTERM must be observed as -15 and rejected as successful simulation. Both jobs remain pending at this observation. See `docs/evidence/native-checkpoint-exit-controls-launch-20261114.json`.

Next: inspect both exact run results. Only after the full-chip prefix and exit-status controls pass, start long continuation from the pinned real full-chip checkpoint, with strict runtime/CPU/mapped-file/source identity, full memory tests and original28-check firmware gates. Use actual native exit0 plus original boot_checks; a text PASS or successfully saved chunk alone is insufficient. Retain process images only in cloud. All six CAD handles in the previous snapshot were also confirmed live this turn.

---

# Latest checkpoint — pinned native IHP restore passed; full-chip prefix running

**43557409470 completed/success**, source `85aeb1e224eca0cf2d1f5008da9e8ed59e4d199d`. Pinned original OSS CAD suite ARM package and untouched native IHP flip-flop were used in the 50-million-cycle four-state/delayed-event comparison. All502 lines byte-identical, trace SHA256`c82f1f1fa067c864f09fbec3f5f30b61bdf42d2e74b7a003e95f3de84f85b6a3`. Strict CPU/runtime and mapped-file checks preserved. This is not full-chip MBIST or silicon acceptance. See `docs/evidence/native-ihp-checkpoint-result-20261114.json`.

**43557919707**, source `104cfcfbe16b589bf3ee5df1b51d0374c1d19eb2`, branch`codex/full-native-checkpoint-prefix`, observed **in_progress**. Script`scripts/check_full_native_checkpoint.py` downloads pinned original recovery artifact14097721346 only in cloud, reconstructs exact original testbench/firmware/netlist/models with input hashes and flags, recompiles using pinned ARM suite, and runs the unchanged full-chip workload. It compares first20000cycles uninterrupted against a process saved after10000cycles and restored on a separate runner. No preload/shortened MBIST/RTL mutation. This test deliberately stops after prefix comparison; do not mistake it for full MBIST/boot pass. If passed, qualify/use the preserved process checkpoint for multi-job continuation through the original final MBIST and28-check firmware gates, maintaining exact runtime/file identity. Process images/netlist/GDS/waveforms stay cloud-only.

Six CAD handles were re-polled in the evidence snapshot. Continue exact live handles, no blind reruns. Full serial PHY, final timing, current SRAM/chip LVS, qualified characterization/RC and manufacturing acceptance remain open.

---

# Latest continuation — native model controls pass on both architectures

Run **43557240046** at `8a4f8605f4e6ac501f111df5ccbb0ea868bdd514` passed x86 and ARM native flip-flop and mapped SCRUB positive/negative controls using pinned OSS CAD suite 2026-08-04. Untouched locked PDK sources verified. This is not SRAM or full MBIST completion. See `docs/evidence/native-ihp-architecture-controls-20261114.json` for complete derived results, artifact identities and fresh CAD status snapshot.

Next **43557409470** at `85aeb1e224eca0cf2d1f5008da9e8ed59e4d199d`, branch `codex/native-ihp-arm-checkpoint-proof`, observed in_progress: native IHP flip-flop added to the 50-million-cycle X/Z and delayed-event cross-runner checkpoint control, using the pinned original OSS suite ARM package. Checks every file mapped by the native VVP process before restore, exact kernel/runtime identity and strict CPU compatibility; requires full byte-identical output. No full-chip result yet. If passed, qualify real SRAM/full mapped workload before resumable MBIST deployment. Native artifacts stay cloud-only.

Six ongoing CAD handles were re-polled; read exact snapshot and refresh. No duplicated CAD jobs or waived signoff gates.

---

# Latest checkpoint — ARM restore equivalence passed; native model qualification launched

Run **43556397817** passed both dump and separate-runner restore with strict CPU/runtime checks. All 502 output lines of the 50-million-cycle four-state/delayed-event control match the uninterrupted baseline, SHA256 `972d25b21a2ed9247967e9597a35e0a48f04dfe4e7203a7c02fcae5ea39ad160`. This uses apt Icarus and does **not** establish native IHP/full MBIST acceptance. Evidence: `docs/evidence/native-vvp-arm-checkpoint-result-20261114.json`. Process images remain cloud-only.

Next workflow dispatched on `codex/native-arm-model-qualification`, source `8a4f8605f4e6ac501f111df5ccbb0ea868bdd514`: pinned original OSS CAD suite 2026-08-04 on ARM and x86, untouched model-lock preparation, native flip-flop compatibility plus mapped SCRUB positive and historical failing negative controls. Resolve exact run handle by branch/source, inspect both results, then qualify checkpoint equivalence on the real native workload before full MBIST. No simulator version relaxation or MBIST bypass.

Six CAD runs rechecked live:43553707234,43550440744,43541234973,43538031308,43529228292(flat child),43534692191. Their results remain pending.

---

# Latest checkpoint result — dump works, x86 cross-runner restore rejected

Run **43556082535** at source `0463c149ea3a7e50c1024d31532a064bc815ce1f` completed/failure. Native VVP dump and kernel preflight succeeded. Separate-runner restore failed the preserved strict CPU check: **unsupported xfeatures0xe0** on AMD EPYC7763. Exact runtime libraries and kernel matched. No output equivalence, full MBIST completion or chip acceptance. Do not use `--cpu-cap=none` or otherwise suppress this failure.

New capability probe **43556397817**, source `3f2c7fa6209ea5b4be64c2d6a969f8ee433455ee`, branch `codex/native-vvp-arm-checkpoint-proof`, observed **in_progress**. Only runner labels changed to supported `ubuntu-24.04-arm`; four-state delayed-event test and strict dump/restore validation remain. A success would still require original native model/simulator qualification before a real MBIST run; no architecture substitution has been accepted.

Evidence and earlier harness/build failures: `docs/evidence/native-vvp-x86-checkpoint-result-20261114.json`. Safe derived artifacts14098840762/14098940303 are authenticated there; process images remain cloud-only. Six physical CAD handles below still need exact polling.

---

# Latest experiment — native simulator process checkpoint across cloud jobs

Capability run **43555672343**, source `78e99d71c98793c35eeaabf0e764beaf786aa065`, branch `codex/native-vvp-cloud-checkpoint-proof`, observed **in_progress**. It builds official CRIU v4.3.1 at `3ce556b7e8291c1bfdca974962f6282d7802b69f` on the cloud runner. Initial43555513918 failed at apt because criu had no installation candidate; no capability test ran there.

Purpose: determine whether a complete VVP process, including pending events and four-state state, can be moved between GitHub jobs to overcome the20000s native MBIST timeout. A synthetic trace with X/Z, nonblocking updates and delayed events must be byte-identical to an uninterrupted run. Both dump and separate-runner restore must pass, with exact runtime/kernel identity and `--cpu-cap=all`. No weakened CPU checks, RAM-only preload, MBIST shortcut or chip acceptance. Even a successful small test still requires qualification on the exact native PDK workload.

Evidence/next steps: `docs/evidence/native-vvp-checkpoint-capability-launch-20261114.json`. Native checkpoint payloads remain in cloud. Do not download them locally. The six CAD handles below were re-polled; use the JSON snapshot then refresh before acting.

---

# Latest continuation — MBIST timeout and CDR transition-margin diagnosis

Observed 2026-11-14T04:08:40.137899+00:00. **MBIST/boot43516903518 is terminal/failure**, not live. Native vvp exited124 at20000.064s, with progress through1,530,000cycles; UART startup at~1,460,000 and six flash frames by~1,480,000. No native PASS. The RTL-preparation exit0/28checks belongs to a different run phase and does not close MBIST. Filtered cloud diagnosis43554935242 succeeded; see `docs/evidence/full-mbist-native-timeout-20261114.json`. Native recovery artifact14097721346 is pinned there and must remain cloud-only. Do not repeat the same timeout blindly; investigate runtime/MBIST startup and preserve full native model semantics and coverage in any acceleration.

**CDR conditional diagnosis43554632921 succeeded** (source39887bdeaa187c80e5340b5bb5bb23772784d19c), not electrical acceptance. In each XOR-load candidate, transition-group A sampler has0/381 below100mV at diagnostic phases, but buffer A has347/381(nx2) or349/381(nx3) below100mV; X has381/381. This prioritizes sampler-to-buffer level shifting/settling and actual selector timing over another XOR-area sweep. Corrected B expected bit accounts for the next falling edge; initial diagnosis43554431443 is superseded. Full original acceptance gates remain untouched. See `docs/evidence/cdr-xor-conditional-signals-20261114.json`. Next audit actual selector topology before inferring a polarity or test expectation fix.

Six native handles last observed live: strict SRAM merge fix43553707234, fresh CRC physical43550440744, five-driver hold/antenna43541234973, five-driver antenna43538031308, original DP flat43529228292, alternative SRAM RC43534692191. Re-poll exact handles. No manufacturing-ready claim.

---

# Latest correction — resistor merge switches verified; full macro running

Native controls **43553545114 passed all 16 cases**. Original Ruby RES2 merges serial and parallel pairs even with both requested switches off; the two-line correction honors all four switch combinations. Controls instantiate the actual Ruby class in native resistor graphs with boundary pins; no unsupported getter or Python imitation. Original harness failures 43553195656/43553342992 are terminal and superseded.

Full frozen DP SRAM candidate **43553707234**, source `c077726eb378897ef2bf2b2e10bb8c6333195111`, branch `codex/sram-strict-resistor-merge-fix`, is **in_progress** at this observation. It pins successful control artifact14096828657 SHA256 `b58b9142d77cb2f5b429ea23df5854b5e65f5bb19158561d635f9be9872214da`, verifies the original custom_devices source, and adds only the tested two-line switch correction. Existing strict W/L, ports and extraction checks remain unchanged. The new expected 70110 recursive-device guard is derived from 62046+8064 formerly merged pairs and must be verified by the run; it is not yet a measured macro result. Other vendor width/model/hierarchy issues remain open.

Result and provenance: `docs/evidence/sram-resistor-merge-switch-controls-20261114.json`. Reproducible control source is now `scripts/check_sram_resistor_merge_switches.py` on integration. Experimental workflow remains on its own branch. No native files or local checkout created.

Continue the six older live runs: fresh CRC physical43550440744, five-driver hold/antenna43541234973, five-driver antenna43538031308, original DP flat43529228292, alternative SRAM RC43534692191, MBIST/boot43516903518. Four-driver43528773096 is terminal/rejected, not live. Poll before acting.

---

# Latest terminal result — four-driver antenna candidate rejected

Run **43528773096** completed/failure: **DRC=0, antenna nets/pins=1/1**, slow setup **1367** (WNS -2.070215 ns, TNS -478.996881 ns), slow hold3, typical hold11, fast hold**82** (WNS -0.319650 ns). Electrical/fanout gates also fail. Evidence `docs/evidence/cut10j-four-driver-antenna-result-20261114.json`. Do not adopt this candidate or call it timing closure.

SRAM isolated Ruby control run **43553195656** failed before testing flags; captured subprocess stderr had been hidden by the harness. Diagnostic retry **43553342992**, source `1b412c55021425ec17be2601548e81bcb5c1f1d7`, branch `codex/sram-resistor-merge-switch-controls`, preserves native stdout/stderr in a derived JSON and was live at the latest check. Diagnose that failure before applying the proposed merge-switch correction. No pass yet.

---

# Latest investigation — original resistor geometry and ignored merge switches

Observed 2026-11-14T03:45:29.353822+00:00. Cloud geometry check **43552896584** independently confirms metal2/metal3 width differences in the frozen original SRAM GDS. Metal3 polygon count/dimensions match extraction; metal2 polygon count does not (16400 versus 8336 normalized devices), while width-binned total lengths agree. Failed direct-count test **43552738032** is preserved; aggregate agreement is not connectivity proof.

The exact frozen `RES2` class does **not** bind `supports_serial_combination`/`supports_parallel_combination` to requested switches. Thus prior `no_series_res=true` should not be interpreted as proof of no merge during `combine_devices`. Upstream PR1121 (still open, head `3df647ebe53439ae41d56a1e9c2b38003ba2124d`) contains a two-line fix and requires explicit metal-layer identity for LVSRES.

Isolated cloud controls **43553195656**, source `63876fda9e588ae2a7261f1ce85ee89b189c16ca`, branch `codex/sram-resistor-merge-switch-controls`, observed **completed**. These execute the original/fixed Ruby class for all four switch combinations, then native two-resistor serial/parallel controls (16 cases). If passed, integrate only the tested switch correction into an experimental macro flow, recompute unmerged primitive counts, and retain strict dimension/topology/port checks. The frozen GDS/CDL discrepancy remains separate. No class collapse, dimension waiver or physical acceptance.

Evidence: `docs/evidence/sram-original-geometry-and-merge-switches-20261114.json`. Existing native job statuses are pinned there; all seven other runs were re-polled in this continuation. Native files remain cloud-only.

---

# Latest result — hierarchy-expanded SRAM inventory

Cloud diagnostic [43552140757](https://github.com/Melihakbulut221/nssoc/actions/runs/43552140757) completed successfully at source `39512ef05cd88123d0e1d46554ce8067f3dd4414`. This supersedes the pending diagnostic below; it is **not** LVS acceptance.

Both full hierarchies contain **62,046** primitive devices. All MOS class/L/W/count distributions match exactly at 12-digit rounding. Inventory differences are restricted to metal resistor classes and widths: extracted metal2/metal3 include W=0.20/0.24 um while reference LVSRES uses W=0.26 um. Equal MOS inventory does not establish topology or supply connectivity. No GDS/CDL dimensions, tolerances, net aliases or acceptance gates were changed.

Evidence: `docs/evidence/sram-hierarchy-dimension-inventory-20261114.json` (artifact 14095939669, SHA256 `3a8436cfdfb54c22567d523850ff21a0574f8fd4e6225c64ed7a15bcedc147c4`). Next isolate model-reader identity and actual marker/reference mismatch before any source correction; require strict full LVS, negative controls and DRC for a candidate. Continue monitoring the exact active physical/MBIST/flat-LVS/RC handles below. No native data was downloaded to disk.

---

# Latest continuation — SRAM dimension diagnosis and rejected CDR screens

Observed 2026-11-14T03:32:49.878654+00:00. This section supersedes older live-status claims below.

- Current DP SRAM selective flatten run **43543201489 failed**: 25 Match, one top NoMatch; no Skipped, no extraction diagnostics. Hierarchy changes did not close LVS.
- Bounded top diagnosis **43551681909 succeeded** as a diagnostic, not LVS acceptance. Paired resistor samples show metal3 width **0.24 um versus reference 0.26 um**. Direct top inventories have different child boundaries and are not evidence of missing transistors. See `docs/evidence/sram-top-dimension-diagnosis-20261114.json`.
- Cloud hierarchy-expanded inventory diagnostic **43552140757**, source `39512ef05cd88123d0e1d46554ce8067f3dd4414`, branch `codex/sram-selective-flatten-top-diagnosis`, is completed at this observation. It reads the exact pinned selective-flatten database; no new extraction, net aliases, tolerance relaxation, or device omission. Inspect the resulting derived JSON before choosing a correction.
- CDR XOR nx=2 and nx=3 run **43542889935 failed electrical acceptance**. Both native simulations exited zero, device limits and phase passed, but X comparison has 386/392 wrong-sign samples and sampler A/C/D margins fail. No layout accepted. See `docs/evidence/cdr-xor-load-reduction-result-20261114.json`. Next diagnose data-path polarity/settling and sampler margins rather than repeat this load sweep.
- Fresh CRC physical **43550440744**, old-layout route candidates **43541234973 / 43538031308 / 43528773096**, DP flat LVS **43529228292**, alternative SRAM RC **43534692191**, full MBIST/boot **43516903518** were still in progress on this continuation. Poll exact handles; do not restart live jobs. Fresh CRC run remains probe-only and needs its own downstream detailed route/RC/STA after successful handoff.

All native artifacts remain in cloud. Full PHY, final timing, full current SRAM/chip LVS and manufacturing acceptance remain open.

---

# Latest continuation update — CRC proof and fresh physical candidate

This update supersedes the PCIe proof/live-run entries below. Other native jobs must still be re-polled by their exact handles. The full manufacturing-ready objective remains open; all native work stays in cloud.

- **CRC proof passed:** [43549353231](https://github.com/Melihakbulut221/nssoc/actions/runs/43549353231), source `0e86c8c8ec9db5838ae371821e6c047a6825d554`. Capacity 8: 551/551 points; capacity 32: 1351/1351, both directions. Proof-only semantic wire `fold_ordered_word=transmit_order(fold_word,fold_msb_first)` in the baseline provided 32 additional obligations, all proven. No assumed relation or output mask. Scope is Yosys async2sync/undef induction plus previously completed packet/reset simulations, not whole-chip or physical signoff. See `docs/evidence/pcie-crc-order-state-relation-result-20261114.json`.
- **Fault controls passed:** [43549920774](https://github.com/Melihakbulut221/nssoc/actions/runs/43549920774), source `81f6fec51e315d0bfa2b3188576715716dc9e857`. CRC bit and output bit corruption rejected in both directions (capacity 8); rc=1 and final unproven-equivalence assertion, no timeout acceptance. See `docs/evidence/pcie-crc-state-relation-negative-result-20261114.json`.
- **Fresh physical run LIVE:** [43550440744](https://github.com/Melihakbulut221/nssoc/actions/runs/43550440744), source `ecbcf43200413fc63844bbd20a7532f87af54216`, branch `codex/crc-order-fresh-physical`, job `132311448151`. Last observed CAD runtime setup. Uses exactly candidate RTL SHA256 `51aff3ebbbf80d251b4a3ebaa3c8da744d1c0e67fb3189f2cb947af1d15219ce`, all original cut10j knobs, fresh RTL simulation and synthesis through placement/CTS/global route and setup/hold repair. Emits a native `route-handoff-r_cut10j_td_d68-43550440744` artifact if successful. **This workflow contains only the probe job.** After completion, bind its exact handoff artifact/hash and run antenna-aware detailed routing, fresh RC extraction and all-corner STA. Never reuse old cut10j layout as evidence for new RTL. Existing fixed instance-name ECOs are from the old netlist and must not be blindly applied to this new synthesis.
- Candidate RTL remains **unmerged** in `timing/combined`; require fresh physical evaluation before adoption. Original failed proof runs 43543271489 (structural) and 43546370331 (deeper bitwise) are terminal timeouts, no longer live; their reports remain preserved.
- Initial physical dispatch at source `870322cd742c2ff872f39905eeaa5fb014aa30ac` was rejected HTTP422 because a header split matched the `pcie_jobs` input. No CAD job started. Corrected top-level split produced the live source above.

Still-live native handles at this update: SRAM selective flatten 43543201489; CDR actual-multiplicity XOR load screens 43542889935; old-layout hold/antenna candidate 43541234973; five-driver antenna 43538031308; four-driver antenna 43528773096; current DP flat LVS 43529228292 (deep child already failed); archived alternative SRAM RC 43534692191; native full MBIST/boot 43516903518. Re-poll before acting. No result here closes full PHY, current-chip LVS, final timing, qualified RC/Liberty, integrated pad/DFT, or production review.

---

# Cloud continuation — 2026-11-14

Observed at **2026-11-14T01:58:10.696260+00:00** on integration branch **`timing/combined`**.
Repository: https://github.com/Melihakbulut221/nssoc
This is a resume checkpoint, not a chip signoff. The manufacturing-ready goal remains open.
All source edits and native computations are in GitHub. Do not recreate a local CAD checkout or download native geometry, SPICE, netlists or waveforms. Read source and vetted derived summaries through API in RAM; filter mixed artifacts in cloud first.

## Resume these exact jobs

| Run | Scope | Observed status | Source |
|---|---|---|---|
| [43543201489](https://github.com/Melihakbulut221/nssoc/actions/runs/43543201489) | Current DP SRAM: six-cell symmetric hierarchy flattening | in_progress / pending | `220c52b2872ad4350d1308adf2b2d99b3802d9cc` |
| [43543271489](https://github.com/Melihakbulut221/nssoc/actions/runs/43543271489) | PCIe CRC retiming: forward structural plus sequential proof | in_progress / pending | `be7609b53929c286ee31537a333c226934b2d727` |
| [43542889935](https://github.com/Melihakbulut221/nssoc/actions/runs/43542889935) | CDR XOR input area nx=2/nx=3 with corrected current-density binding | in_progress / pending | `225363749ed24b5b9e452ab39af757376f21db00` |
| [43541234973](https://github.com/Melihakbulut221/nssoc/actions/runs/43541234973) | Five-driver plus isolated Ethernet RX bank6 A_ADDR6 hold ECO | in_progress / pending | `f83a2f29afc00626688942b2ce663a4b844eeb3c` |
| [43538031308](https://github.com/Melihakbulut221/nssoc/actions/runs/43538031308) | Five-driver plus antenna repair | in_progress / pending | `6c5d8de09c0fd88b0daa57e669b3b6fc2bf67bbb` |
| [43528773096](https://github.com/Melihakbulut221/nssoc/actions/runs/43528773096) | Four-driver plus antenna repair | in_progress / pending | `e8d24c8d92dbec192db84115d8c8110f82a1812c` |
| [43529228292](https://github.com/Melihakbulut221/nssoc/actions/runs/43529228292) | Current DP SRAM normalized deep/flat comparison; deep failed, flat pending | in_progress / pending | `13d88396f2be3a7823981be6ffe5e67df7b9ed32` |
| [43534692191](https://github.com/Melihakbulut221/nssoc/actions/runs/43534692191) | Archived alternative DP SRAM RC extraction with 32GiB swap | in_progress / pending | `2b9714c3c9c9ffb6e47313c7b96d09f74435dd98` |
| [43516903518](https://github.com/Melihakbulut221/nssoc/actions/runs/43516903518) | Full native system/Ethernet MBIST and firmware boot | in_progress / pending | `3fd0fded2d874efa0109d8558a213380de1f36a7` |

Poll exact handles again before acting; these observations will age. Do not restart a live run on observation timeout. Inspect failed steps and derived reports before retrying. No pending result in this table is a pass.

## Latest findings and next decisions

- **SRAM:** run 43541320172 passed the scoped metal1 model/width/length/A-Z-open controls, then failed the full current DP macro: 25 Match, 6 NoMatch, 1 Skipped; both sides 62,046 primitive devices. The isolated leaf still lacks physical VDD/VSS ports and is not full-LVS accepted. The next hierarchy test preserves all primitives and the strict final port/extraction audit. See [controlled result](docs/evidence/sram-metal1-controlled-macro-result-20261114.json) and [open-control diagnosis](docs/evidence/sram-metal1-open-control-diagnosis-20261114.json). Do not waive dimensions, supply opens, unmatched ports or extraction warnings to obtain a pass. The older full flat job is still a separate pending comparison.
- **Ethernet hold:** full reports from rejected four-driver run 43505737740 show RX bank6 `A_ADDR[6]` setup +5.231030 ns in slow corner and hold -0.427385 ns in fast corner. The new candidate inserts three noninverting delay cells only on that endpoint branch, with Liberty identity, power and contracted-connectivity checks, then fresh routing/RC/STA. The source name had to be resolved from escaped ODB hierarchy; prior parser/name failures are preserved. These old path margins do not predict acceptance of the new layout. See [budget](docs/evidence/ethernet-rx-hold-budget-investigation-20261114.json) and [candidate](docs/evidence/cut10j-rx6-hold3-antenna-launch-20261114.json).
- **PCIe CRC RTL:** candidate byte-order retiming remains **unmerged**. Packet simulations and mutation tests passed, but both full mutual proof attempts timed out at 1,800 s. The cleaned proof left 402/1,178 unproven cells at capacities 8/32 before induction; no completed counterexample or proof. The new structural method still requires every remaining equivalence cell proven. See [proof record](docs/evidence/pcie-crc-order-cleaned-proof-timeout-20261114.json). Require successful mutual proof, negative controls and fresh physical timing before accepting the RTL candidate.
- **CDR:** sampled diagnostics found late/weak A/C-buffer transitions and six `nx=4` XOR base loads on each `nx=2` buffer collector. Two circuit-screen variants reduce only 24 XOR device `nx` parameters. Initial run 43542698325 was cancelled because the legacy checker used original emitter multiplicity for current density. Replacement 43542889935 uses the actual candidate binding and unchanged 3 mA/emitter limit. Existing interconnect RC is retained only for screening; a good waveform would still require new layout/extraction, numerical agreement and full operating-condition checks. See [response](docs/evidence/cdr-lowz8-buffer-response-20261114.json) and [corrected screen](docs/evidence/cdr-lowz8-xor-load-reduction-launch-20261114.json).
- **RC:** the swap-extended extraction is for an **archived alternative** DP8TSRAMDP256x16, not either vendor SRAM in the current chip. Apply independent topology/RC audit if it completes; never transfer its result to the current macro or claim qualified min/max RC.
- **Native MBIST:** the current full run includes system and Ethernet memories plus firmware handover; PCIe is idle and there is no SDF. Do not call it serial PHY or routed-timing proof.

## Completion remains unproven

Keep the full scope in [product acceptance](docs/92-product-acceptance.md), [second audit](docs/96-second-audit-closure.md) and the README. Outstanding work includes final setup/hold/electrical closure on the same routed chip, full current SRAM and chip LVS, qualified SRAM characterization/Liberty and min/max RC, full serial Gen3 x4 PHY/control/clock integration, integrated padframe/DFT and physical verification, manufacturing review, and the required silicon/radiation qualification. Historical pilot/core passes and scoped diagnostics do not close these requirements.

The previous checkpoint is retained below as history; its live-run statements and dates are not current.

---

# Claude handoff — terminal status update, 2026-11-04

Read [CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md) first for the detailed Turkish handover, exact sources, failures, measurements and next steps. Machine-readable selected evidence: [CLAUDE_HANDOFF_EVIDENCE.json](CLAUDE_HANDOFF_EVIDENCE.json).

At 2026-11-04 02:07 UTC, runs 41699812301, 41733225660, 41734419971 and corrected handoff 41739641054 were all completed/failure. No queued/in-progress runs were returned by the API. The old v360 live-status text below is historical.

- Route: supervisor memory-sample bounded-window failure; last successful RSS below limit. Route did not finish.
- Actual650 N1/N2: native transients exited zero; data/device/phase electrical gates failed.
- Handoff: original1691 scope correction passed its former failure point; DEF single-wire-clause parser now fails in prepare. Logical diode supplies passed; physical continuity unverified.
- Full serial PHY, completed mainchip routing, final timing and production acceptance remain open.

Documentation handoff only, not a new native experiment or v361 monitor rebuild. Native assets remain cloud-only. No CAD/simulation job dispatched for this handoff.

---

## Historical v360 checkpoint (preserved verbatim below)

# Cloud continuation — checkpoint v360

Updated: 2026-11-03T23:21:08.981491+00:00

## Native route-class restoration and diode-inclusive netlist handoff

New source50f1ebf8d1c940abff985f971aeae670eeb4a9ec on codex/mainchip-postroute-handoff implements actual original full-chip class restoration, diode logical-supply audit, physical netlist export, fresh-library read/link and complete instance/pin/boundary incidence comparison. The old zero-diode route12 adapter and original timing gates remain unchanged. Source controls41738123187 passed, including six rejection cases; their1190-byte artifact13280920159 was authenticated in RAM.

Native job41738314531/release433325391 is the first real execution. Its initial input is the existing completed route41440285882, which still has known physical violations. It is a qualification of the handoff implementation, not the new full64 result and not signoff. It invokes no new routing. The complete real netlist comparison must pass, then native diode/port mutations must be rejected. Native failure must be diagnosed without silently omitting diodes/physical cells.

Current full64 route41699812301 and actual650 N1/N2 runs41733225660/41734419971 retain their exact handles. If the handoff implementation passes, acquire the completed full64 output with exact source/asset/member pins and apply it there before fresh RC/original-clock timing. Do not use the old zero-diode netlist. Original global class restoration and actual physical diode PG connectivity are distinct; the new logical supply check does not establish metal continuity or LVS.

The restored PLL terminal map and distinction between failed RHI120 and olderPLL845 captures remain documented in docs/pcie-cdr-pll-connection-audit-20261104.md. Current650 benches still use an external clock and do not prove a recovered-clock loop.


Observed 2026-11-03T23:21:08.981491+00:00:
- 41699812301: in_progress/None
- 41733225660: in_progress/None
- 41734419971: in_progress/None
- 41738123187: completed/success
- 41738314531: in_progress/None


## History and execution
Previous actual route and failure handoff:
https://github.com/Melihakbulut221/nssoc/blob/1725fa8d43b6befeb966504d5aa5af8f1e9c69b0/CLOUD_RESUME.md
All earlier sources, complete reports and failed runs remain preserved.
All native CAD/geometry/runtime/electrical payloads stay cloud-only. The local
workspace is empty; source and derived-text API coordination uses RAM.
The8-hour monitor remains read-only with automatic_native_dispatch=false.
Poll existing exact handles; do not restart on observation timeouts.
Full serialPHY, completed mainchip routing and final setup/hold must all
pass real complete verification before the overall goal is complete.
