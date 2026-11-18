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
