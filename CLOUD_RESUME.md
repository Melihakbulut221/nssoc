## Full-sized original core visible geometry verified

Run44331431907 atd054faaf0b2767062321cdeca8ab6cdf5177bf37 PASSED. Artifact14439487122 SHA25643d02965456088408dfcba23b9e51d416d3622c6f76e8fb7d66d46607acce1a7; all four outputs and protected repository sources independently verified. Native visible geometry reports zero disconnected signal nets, zero missing terminal shapes, zero unwired multi-terminal nets and zero inter-net contacts. An actual SpaceWire-memory net loses connectivity when its17route shapes are removed in the negative control. The indexed checker also passed1,624 reference comparisons and11native decoder fixtures.
Elapsed wall90.001s; observed child maximumRSS1,686,652KiB. This qualifies practical core-scale execution on the cloud runner. The checked input is the ORIGINAL pre-ECO routed core ODBeb3ed6dc3921b8b8584e455856615c5e64372650b638f9edfa2cf4e674b391c4. It does NOT cover the latest ECO, internal macro/stdcell transistor connectivity, hidden GDS or foundry/manufacturer approval. Evidence:docs/evidence/core-only-original-core-visible-geometry-20261118.json.
Use the same qualified scripts and hashes after the next final detailed route: audit_native_signal_geometry_indexed.py3baed05b7cbad6c03991d783fc7ad772e3b68e1534031ad07735750d7e79dabd and native_geometry_contact_index.py0423bd8ec0941d761f7594100f2e3be84f6cc6b2c67a2d55c951d69b86b7a26f.
Main candidate44331913767 (four slew driver resizes +two cap buffers) remains pending native admission; inspect its current result before further routing.

## Latest measured timing and remaining electrical ECO

Run44328874040 at733cb000518b8bd6d95470fde5e6e3c3e32bafa6 completed: artifact14438862280 SHA256 e47da3fe91a279ad2102ee2d84420b226afddd73646b26dceb5ab42c37e05fa8, all106 output hashes and protected repository source files independently verified. Three corners have0setup/hold/fanout violations. Slow setup margin0.0661107ns; fast hold margin0.0426459ns. SRAM output capacitance no longer violates. Remaining cap violation nssoc_sta_i_78908/Q:0.304662/0.306369/0.308337pF versus0.300pF.
Slow slew count increased5->11 after global rerouting. Four drivers account for those endpoints: nssoc_sta_i_64237/Y,54306/Y,52754/Y,66325/Y. Preserve reports; this is not electrical closure. New candidate strengthens these measured combinational drivers only after matching actual native master pins and exact Liberty function, and adds two spatially grouped buf4 branches to78908/Q. All clocks, SRAM relocation, prior hold chain and other instance geometry must remain unchanged.
All figures are GLOBAL-ROUTE ESTIMATES, not final extracted timing. Native core geometry baseline runs independently from original routed core; it cannot qualify this ECO. Next: candidate admission, fresh screening, detailed routing with antenna checks, RCX and full-chip verification.

## Full-sized native geometry baseline

Indexed geometry qualification44330297789 passed1,624 exhaustive-reference comparisons and reproduced the authenticated parent result with zero geometry disconnections/missing terminals/inter-net contacts. Artifact14438982327 SHA256 bfa8bd0bb9fa92a3896b91bbd073a14e685b7bd6862a1dfeac9fc181dd619082; all hashes and source files independently verified.
The new baseline runner selects only routing/1-nssoc-coreonlydetailedrouting/soc_top.odb from ORIGINAL core run44263061910 (SHA256 eb3ed6dc3921b8b8584e455856615c5e64372650b638f9edfa2cf4e674b391c4), never a drt-run-N intermediate. This tests core-scale visible geometry and does not cover the latest ECO or hidden macro GDS/transistor LVS. It emits30-second liveness messages, records runtime/RSS, and imposes no subprocess timeout; GitHub job limit355minutes remains.
Main latest timing run44328874040 has completed; its artifact14438862280 is being independently verified. Do not substitute this original-core geometry check for the latest physical candidate.

## Pin-aware candidate admitted for fresh global-route screening

Run 44327965276 at 0fbac4d6617c72f3d00a0b759cfc4677bae1b732 PASSED native legalization/audit. Artifact 14438605718 SHA256 36fcd030bd23666169d392b84668f5bf0cd727d1b4b5f351d75c8a20fd876bb1; all 12 output hashes and protected repository source hashes independently verified.
SRAM output-to-buffer pin Manhattan distance improved from 646.635 um to 22.725 um. Four cell resizes and six new non-inverting buffers passed exact contracted terminal connectivity, original net types, PG/pin geometry, all original antenna cells and unchanged clock geometry/connectivity audits. Output candidate ODB SHA256 5d800a165a0fa1a0600c6f5e076b1af0ff8b37edff802f2f62c72f0fb0f4483d.
Fresh screening runner: scripts/cloud_core_only_pin_aware_electrical_globalroute.py. Keep 20 ns and 5% derate. A shorter pin distance is NOT capacitance closure; evaluate fresh corner metrics, then detailed routing/antenna/RCX and actual final timing. Production approval remains open.

## Current pin-aware repair candidate

Candidate [44327965276](https://github.com/Melihakbulut221/nssoc/actions/runs/44327965276) at 0fbac4d6617c72f3d00a0b759cfc4677bae1b732 is running. It consumes the authenticated zero-setup/hold/fanout global-route estimate 44323428899; it is not yet a routed or timing-qualified result.

Read-only native inventory 44326794780 verified actual transformed pin geometry (artifact 14436573246, SHA256 55dce0851fbd1341b5cd7224a0fac8d037bebfbc1d17115651cdcd4c8f72bf6f). SRAM bank1 output pin center is near (955.39,687.05) um; the existing isolation buffer input is near (933.645,62.16) um, about 646.635 um Manhattan distance. The candidate moves this buffer above the macro output and requires final distance <=75 um and <one quarter of baseline. No original macro moves.

The candidate strengthens nssoc_sta_i_8470 a21oi_1 to a21oi_2 for residual slew; three measured setup-path buf_1 cells (fanout4263, nssoc_sta_i_27642, fanout478) become buf_4. Two spatial sink groups on each of nssoc_sta_i_10894/X and nssoc_sta_i_78691/Q get four buf_4 total. Two buf_1 delay only the measured fast minimum-slack endpoint nssoc_sta_i_77169/D from nssoc_sta_i_45238/Y. All other original cells, clock connections, PG and antenna cells must remain unchanged. Cell function and pin types are checked; final extracted timing remains required.

Native residual audit qualification 44327223071 PASSED: one positive and seven deliberately corrupted fixtures, all hashes and protected repository sources independently verified (artifact 14438655216 SHA256 f6ded972c607f19ee3aba5a4e91c4aceb19a6d8d91cbf9f6002f0b3afbf2bfcb). Prior failed attempts are harness-development evidence, not successful controls. The final test temporarily unlocks only a copied FIRM fixture to inject orientation corruption, then restores its status. See the two new evidence JSON files.

Next: validate the pin-aware candidate's native audit, then fresh global-route three-corner timing. Keep 20 ns / 5% derate. Do not skip detailed route, antenna/native DRC, actual RCX, full-chip timing/LVS and manufacturer qualification.

## Latest measured result: setup, hold and fanout zero in global-route estimates

Run [44323428899](https://github.com/Melihakbulut221/nssoc/actions/runs/44323428899), source 3d8c75c1f63dfa753f58617e391e28850aa603ef, completed. Artifact 14437435877 SHA256 a335010597079f4fcc72495c622f759630788f2a1f1f453f24a4ba1f8dbe2291; all 106 output hashes and protected repository sources independently verified. See `docs/evidence/core-only-residual-electrical-globalroute-20261118.json`.
All three corners report zero setup, hold and fanout violations at 20 ns / 5% derate. Slow setup margin is only 0.00781064 ns; fast hold margin only 0.00942668 ns. This is GLOBAL-ROUTE ESTIMATED RC, not final extracted timing.
Remaining: slow slew on nssoc_sta_i_8470/Y and wire2419..2422/A; capacitance in all corners on SRAM bank1 A_DOUT[0], nssoc_sta_i_10894/X, nssoc_sta_i_78691/Q. SRAM load increased to 0.114655 pF vs 0.064 pF maximum; inspect actual macro output pin and nssoc_residualbuf_2_0 location before moving its isolation buffer. Its prior placement used the macro instance origin, not the output pin. Do not claim the SRAM capacitance fix succeeded.
Next: inspect native terminal geometry/load groups, repair these electrical residuals and improve very small timing margins, then fresh detailed route with the documented jumper-only antenna trial, native connectivity/antenna/DRC, RCX and final corner timing. Full-chip/qualified PDK/production approval remain open.
Native audit controls run 44325758272 at 885bae9185fcb1add9ca396d744bdb07a6f61625 is the current attempt. Attempt 44325061422 rejected the positive fixture because preserving the resized cell's original orientation was overly restrictive; legalizer can legally flip/reorient resized cells. The revised check allows R0/R180/MX/MY and tests invalid R90. Existing untouched instance geometry and all original net signal types remain exact requirements. Preserve failed evidence; do not count these harness failures as successful negative controls.

## Verified routed-core boot result and current work

Run [44303624006](https://github.com/Melihakbulut221/nssoc/actions/runs/44303624006) completed successfully: 28 firmware checks, zero fail mask, 2,263,211 cycles; system MBIST passed (1,310,690 busy cycles). All 15 artifact output hashes, protected repository source hashes, nested simulation result and actual compiled netlist hash were independently checked. See `docs/evidence/core-only-routed-boot-20261118.json`.
This is the original detailed-route netlist from 44263061910, before subsequent ECOs. It uses FUNCTIONAL native models without SDF; Icarus reports unsupported edge-sensitive ifnone paths. It is not timing, equivalence or production signoff.

Active follow-ups: residual electrical global-route timing run 44323428899; strengthened native audit controls run 44325061422. The first controls run 44324480776 failed before testing because NSSOC_CONTROL_BUFFER_OUT was unset; commit 1efeae09e3e226d55330bdf91bab230cbc9049c4 supplies the required environment. Do not interpret that failed attempt as a circuit failure or successful negative test. No physical run was restarted.

## Active continuation: residual electrical global-route screening

PCIe and Ethernet remain excluded. Preserve the 20 ns period and 5% derate.
Candidate run 44322374175 at b386cdf9512ce5fe57ed670e4a0ddbae3ed01a19 succeeded. Artifact 14434813194 SHA256 12cc118f39137f015b74391973efdd0b912f6876959bfb43640544fc13c28669 and all 11 output hashes were verified independently. Protected repository source hashes match the producer commit.
Two logic cells were strengthened; six buffers were added, including three clock branches. Native audit preserves all other instance geometry, terminal connectivity classes, power/pin geometry and existing antenna cells. Candidate ODB SHA256 06ff0bf05d7f1587a9e3d362f5ff5213567c42aca80bcf1778e50278eda5967b.
Next: cloud_core_only_residual_electrical_globalroute.py measures fresh global-route estimates in slow/typical/fast corners. This is not extracted final timing. Check setup, hold, slew, fanout, capacitance and clock skew before detailed routing. Retain original SRAM hold chain. Then detailed routing, antenna checks, extracted RC timing and full-chip verification remain necessary. Production approval remains open.

# Cloud continuation: canonical core timing verified

User scope remains core-only: no PCIe/Ethernet; retain CPU, four system SRAMs/MBIST, SpaceWire/CAN/I2C/SPI/UART/GPIO/QSPI/NPU/protection. Core50MHz20ns and5%derate unchanged. All work cloud-only.

Canonical extraction44308129454 at78432b99eb354dcb2a7a2d3266ecbb445a31c9cc passed. Both artifact digests, matching result bytes,131 output hashes and protected repository sources verified. Evidence: docs/evidence/core-only-canonical-timing-20261118.json.81,091 instances and77,298 nets renamed through reversible map;104,885 instance geometry,538,831 terminals and all ordinary wire opcode/data bytes plus special geometry unchanged, including binary readback. Exact helper passed seven native fault controls44309322608.

All three corners now have zero partial drivers, zero loaded unannotated drivers and zero missing-load names.1403 unannotated remain:1288 disconnected outputs +115 connected no-sink drivers. They are recorded, not functionally waived.102601 SPEF nets resolved. No missing-name warnings in independently inspected slow/fast logs.

Slow118setup/-1.471500297ns, hold0/+0.429305492ns. Typical setup0/+6.459904794ns, hold0/+0.174315678ns. Fast setup0/+10.337638593ns, hold1/-0.024185321ns. Electrical slow477slew/171fanout/41cap; typical5/171/41; fast1/171/44. NominalRC only.

This branch selects only the actual worst violated setup data path, not the whole max report. It upsizes measured buf1 outputs >=.45ns delay tobuf4 and inserts sixbuf1 on wire30226->SRAMbank2 A_MEN. It consumes canonical ODB and keeps the reversible name map. Original endpoint slice71785->72130 is verified through that map. The previous44306730950 candidate selected too many buffers and failed before changing anything. This new candidate must pass legalization and topology/geometry audit; then needs fresh global/detailed routing, RCX and all corners. Never reuse old SPEF on resized/moved geometry as final timing.

Parent pad repair timing44306169864:1939-net coverage, cap slow18->1,typical6->0,fast1->0. Remaining GPIO13cap and pad/internal slew recorded in docs/evidence/core-only-pad-repaired-timing-20261118.json. Core still blackbox in that scoped parent analysis. Routed boot44303624006 remains live; preserve. Full-chip IO/CDC, SRAMLiberty/LVS, qualifiedRC, foundryDRC, DFT/package/ESD and manufacturing approval remain open.

## Targeted ECO admitted for fresh route

Run44310594615 at a543203ea5e43d8a6993911933f91335d6ff4e9d succeeded. Artifact14429279260 SHA256 eb56e7b226a8209083b2d64fc6b0aa57a45c36609dbe1199b6efeef70767aac4 and all14 output hashes independently verified. Exactly9 buf1->buf4,6 hold buffers. Original other cell geometry, PG/pins and contracted logical connectivity preserved; maximum selected displacement6.66um. Candidate ODB9cc447b33b477b27fe89e1ad3acdd99627209f6cb11211456376bd880862efaa. All102601 stale routes removed.

Next runner scripts/cloud_core_only_targeted_globalroute.py restores authenticated dependencies, verifies producer sources, exports fresh candidate views and runs guarded global routing plus slow/typical/fast STA. These are route ESTIMATES; do not promote to final extracted timing. Detailed routing and fresh extraction are still required. Routed boot44303624006 remains live.

## Residual GPIO pad candidate

Core targeted global routing44311633615 at52ebe8043d3ea6a7d456ebd6d667efa254ae7fa0 is active; preserve. This branch independently addresses only GPIO12/13 pad p2c nets measured in44306169864. Slow slew1.307124019/1.446408153ns against1.200000048ns; GPIO13cap.526872516pF against.511631012pF. Native artifact14427703059 digest and all30 output hashes independently verified. New runner checks summary equality and protected producer sources too. Exact two-net selection; same full original geometry/connectivity and buffer-source checks. Candidate only: fresh route and RCX needed, no fullchip IO/CDC signoff claim.

GPIO candidate44312347548 passed:10 buf2/buf4 added only to n_1513/n_1514; original1965 cell geometry, terminals and PG preserved. All17 output hashes and protected repo sources independently verified. Admission docs/evidence/core-only-gpio-pad-repair-admission.json pins artifact14430423180 and exact unreouted ODB. Fresh GPIO parent route expects1949 routed nets+76exact pad contacts and1975instances. New runner reuses unchanged full route identity and native geometric connectivity checks. It must pass before fresh RCX. Core globalroute44311633615 and routed boot44303624006 preserved.

## Second setup path candidate

Global route44311633615 succeeded; both artifact digests and matching result bytes and106 output hashes verified. Slow8setup/-0.510523ns,typical0/+5.95171ns,fast0/+8.91644ns;hold0all corners with fast+0.0426468ns. These are globalroute ESTIMATES, not comparable as a controlled before/after to earlier extracted metrics.171fanout and slow32slew remain. New worst path nssoc_sta_i_77897->75239. Six measured buf1 delays>=.45ns targeted:fanout5676,fanout676,nssoc_sta_i_15048,fanout656,nssoc_sta_i_15049,fanout643. Second candidate preserves previous six hold buffers and all other104891-instance geometry/topology. Needs new GRT/DRT/RCX; not signoff. GPIO physical route44312962654 and native boot44303624006 remain active.

Second setup candidate44313432783 succeeded. All12 outputs and protected producer sources verified;6buf1->buf4,maximum displacement3.78um,previousholdchain unchanged. Pin artifact14431422748 SHA94f4547d41cbad0d23d46598efab1a14175fca869bf86a48c5d215edecfb9ec4. Follow-on scripts/cloud_core_only_second_setup_globalroute.py reroutes and measures three corners with50MHz/5% unchanged. Still estimate-only until DRT/RCX.

GPIO repaired route44312962654 succeeded:1975instances,1949routed nets+76exact coincident pad contacts,nativeDRC0,visiblegeometry0disconnections/0missingterminals/0inter-netcontacts. Both archive digests and identical summary bytes,25outputs and protectedrepo sources verified. Evidence docs/evidence/core-only-gpio-repaired-route-20261118.json. Fresh extraction/timing runner scripts/cloud_core_only_chip_gpio_repaired_timing.py pins this route and1949SPEFnets; nominalRC and provisional parentclock/coreblackbox limitations unchanged. Second core GRT44314190563 and nativeboot44303624006 remain active.

## GPIO extracted result verified

Run44314493056 succeeded.30output hashes,both digests,identicalsummary and protectedrepo sources verified.1949SPEFnet/terminal/graph coverage. GPIO12/13p2c violations no longer reported. Parent electrical reports:cap0/fanout0all corners;slew53slow/43typ/30fast remains. Scoped parent slack slowsetup+15.526295662ns/hold+.290302843ns;typ+17.210100174/+.181521356;fast+18.183654785/+.118415229. Still nominalRC,coreblackbox,unqualifiedexternalIO/CDC;notfullchipclosure. Evidence docs/evidence/core-only-gpio-repaired-timing-20261118.json.

First coreGRT electrical report171fanout includes clkbuf_6_31_0_clk_npu/X17loads(limit8),fanout5325/X22loads;antenna diodes appear in slewviolations. Before fanout buffering,inventory actual receiver master types and clockmembership;do notwaive cap/slew or count all sinks as ordinarylogic. SecondGRT44314190563 remainsactive.

Load inventory44315708144 failed safely in reportparser:61of171nativefanoutrows have blank printed slack forlimit8/fanout9. No violations waived. Strict parser now requires every markedrowparse,unique pins,fanout>limit,and exact arithmetic for printedslack;blank printedslack retained separately andcomputedlimit-fanout.2positive+6negativecontrols run in cloud before nativeinventory. SecondGRT44314190563 succeeded:summary reports6slowsetup/-0.0978702ns,hold0allcorners;nativeartifact verification still pending.

SecondGRT44314190563 native+summary digests,identicalresultbytes and106output hashes verified.6remaining setup endpoints:75298->77885(-.097870),78403(-.056090),78563(-.056051),78243(-.039078),78755(-.013793);77912->78381(-.007404). Third candidate selects4 buf1 outputs>=.45ns on actual worstpath:fanout4819(.470314),fanout359(.865434),nssoc_sta_i_48118(.676931),fanout311(.911674). Native geometry/topologyaudit remains exact. Sixth independentpath and171fanout/36slowslew remain open;do notdeclareclosure.

Third setup candidate44316794375 passed:4buf1->buf4,maxdisplacement4.8um,all originalterminals/othergeometry/PG unchanged,previousholdchain preserved.12outputs and protectedsources verified. Artifact14432817763 SHA b741e44790b18ef8943e9fc80afbb424131587613956e578120176ea4fbb486d. New GRT runner scripts/cloud_core_only_third_setup_globalroute.py pins candidateODB31ce8138c79ae6a20ba2f24dcf5a91433a29b2c539ae864571dc221f968fc29f.

Load inventory44316553449 succeeded at42b08594e0a6b8b41477ca96eb51c0407480a407. Artifact14433760218 SHA67fb7f0ccf8e6ff015b5e9d54a16217f123c59bff202fcb5175531991b483393. Outputhashes verified;2positive6negative parsercontrols. All171reportedfanouts equalnativeinputterminalcounts. All171include CORE_ANTENNACELL(sg13g2_antennanp);1260ordinaryCORE terminals+671antenna terminals across171nets. Every nonantenna count<=8. OneCLOCK net clknet_6_31_0_clk_npu:6CORE+11antenna. This explains postDRT fanout increase but does NOT waive cap/slew/rawfanout or authorize deleting protection. Electrical repair must preserve/recheck antenna protection.

## Signal electrical candidate

New scripts/cloud_core_only_signal_electrical_eco.py consumes third setup candidate44316794375 and verified loadinventory44316553449. It checks every sink identity against actual source ODB, then inserts spatial buf4/buf8 trees only on170overloaded SIGNAL nets;CLOCK clknet_6_31_0_clk_npu remainsunchanged andopen. Every original antenna cell/placement/master retained;no protectionwaiver. Groups include actualantenna loads and atmost8receivers. Exact originalconnectionclasses,originalPG/pins/geometry,bufferpower/driveracyclicity checked afterlegalization. Alteredbranches require freshroute+antennaanalysis+RCX+allcorners;donotpromotecandidate toproduction. ThirdGRT44317490808 andboot44303624006 preserved.

Electricalcandidate44318129858 passed:348buf4 on170signalnets,104891originalinstancesgeometry/pins/PG preserved,alloriginalconnectionclasses preserved,allantenna cells retained,clocknet unchanged.13outputs and protectedreposources independently verified. Pin artifact14434365399 SHA f3d02a45163b6a6474606bd845e49fd5ecd80b90242db6953fedfa4476f0fa9b;ODB626fe2ad42df30765a2864f1c1b08d59a5847aa6259b230389c896e71ee2839c. FreshGRT scripts/cloud_core_only_signal_electrical_globalroute.py now measures impact; MUST later redo detailedroute,antenna,RCX/allcorners.
ThirdsetupGRT44317490808 completed;verifiedsummary reports4slowsetup/-0.0349978ns,allhold0(fast+.0390485ns),slow32slew/171fanout/1cap. Nativeartifact14433199134SHA b34146f7535b163ce4eeaea373bc36c2eefd1dde9bff627d9c23b3e7056ded00;summary14433468683SHA a72c12acbadef55859dd181959c26ff47d5800429c3207a4cf8d547d2c3b56ce. Fullnativeoutput audit pending;notfinaltiming.

Detailed-route source research recorded in docs/core-only-antenna-load-route-decision.md. PinnedOpenROAD supports-jumper_only;LibreLane3.0.5 forwardsDRT_ANTENNA_REPAIR_JUMPER_ONLY andreroutes afterrepair. NextDRTtrial shouldpreserveall existingdiodes and tryjumper-only toavoidnewfanoutloads,withstrictantenna/DRC/RCX/allcornerchecks andno marginrelaxation. CurrentGRT44319155353 untouched.

## Electrical GRT verified; fourth setup candidate

Run44319155353 passed. Both archive digests,identicalsummary and106output hashes verified. Fanout171->1allcorners(theCLOCKnet);slowslew32->7;slow/typcap0,fastcap2. Hold0allcorners(fast+.0246021ns). Setup regressed to8slowviolations/-0.220242ns,allfrom nssoc_sta_i_77912. This remains an unaccepted estimated candidate. Native14435046015SHA040832e1f21d2a45a3b1cbe23c285dcdb4167d52ae5982f478144a95d5b37b6b;summary14435096024SHA3a11b5149ee6d127104d366d14c02d247d7043db322744f8c918439c14dd4e1d.
Fourthsetupcandidate selects8measured buf1outputs>=.45ns onactualworst77912->78377path. Baseline105239instances includes348electricalbuffers;allpriorrepairs preserved. Slowslew remaining roots nssoc_sta_i_66156/Y and8532/Y;fastcap78595/Q(.301756vs.300pF),SRAMbank1A_DOUT[0](.064254vs.064pF). Clocknetfanout andtheseelectricalresiduals stillopen. Needclock-awareloadrepair,thenDRTjumper-only/antenna/RCX/allcorners.

Fourthsetupcandidate44321041305 passed;12outputs independentlyverified,ODB4154f31a6b96a6e746bf9e373848c010e24dcb22a4581784379a92193e2641d6. Next residualelectricalcandidate consumesit:resize66156nor4_1->2and8532a21oi_1->2 with exactpinnedLibertyfunction/pincheck;split78595Qintotwobuf4branches;isolateSRAMbank1A_DOUT[0]withonebuf4;splitCLOCKclknet_6_31_0_clk_npu into3buf8branches,eachwithactualclockreceiverandpreservedantenna cells.6newbuffers2logicresizes;originalgeometry/topologyclasses,PG,pins,andnewclocktypesstrictlyaudited. Clockskew/setup/hold/antenna needfreshmeasurement. No closure claim.
