## Current continuation: collector Via2 canonical PASS, fresh RC live; saved mainchip iteration19 recovery

Previous checkpoint v304 fcee42478c0e7c8795ec65ca77aea76bc7441cdd has790inventory rows. Native CAD/GDS/ODB/SPICE/waves remain exclusively GitHub. Local workspace empty. Full serialGen3x4 PHY, mainchip routing and finalsetup/hold remain OPEN.

CORRECTION TO v304: mainchip41415994457/sourcef808321a is TERMINAL FAILURE, not live. Route elapsed5737.308s; supervisor maximum_group_rss, returncode-15. RSS11605680KiB exceeds11534336KiB(11GiB); available3664296KiB remains above2097152KiB floor.12GiBcgroup/swap0; no OOM kill. Iteration19 completed with92internal markers (28MetalSpacing+64Short); iteration20 guides tiles stopped near90percent. This is not finalDRC and no finalrouted checkpoint returned. Complete native release431237039 has100members,3archiveparts and snapshots0..19. Do not repeat same failing route unchanged.

SOURCE RESEARCH: exact engine OpenROADdcf36133a369abc8f3c5e5738cd4d82e4903c0e0, src/drt/src/dr/FlexDRFlow.cpp and FlexDR.cpp. Below100markers state machine can selectGUIDES. guideTilesFlow unions original guideboxes, creates explicit-sized workers and processes whole independent batches before clearing. The normal args.size optimization tiles do not bound these explicit guideboxes; reducing threads alone may retain completed workers in a batch. A safe bounded-batch/box repair needs new runtime qualification, not altered DRC acceptance. Snapshot support was ALREADY enabled in originalroute47 source. Actual19ODB214392179bytes SHAa93e921ccd7abb164dbe2ff3f6a1a1c26777d707399cea7580d7c5d08ea11017 is preserved. Reuse must first pass original complete scope/class/DRC audits; serializedODB is not internal router-search-state resume.

MAINCHIP RECOVERY41440285882/source0990e2971dee0333598a59a033dfe4f1f1f4215b/branchcodex/mainchip-route47-snapshot19-audit/release431403455. Independent same-source controls41440092152 PASS, oldsource-controls41439875813 and41439959911 FAILED only because new negative archive test expectedAssertionError instead of existingvalidatorValueError. Test corrected; actualvalidator/native gates unchanged. Native helper also explicitly inserts /work/tail-source/scripts before embedded imports. Both failures preserved.
Authenticate whole failedproducer capsule, all100members/all3parts, select7exact baseline/protection/scope/failure/snapshot records. Recompute original47selectednets against actual baseline and1691protected clocks. Restore original routeclasses, run unchanged complete native wire/opcode/DEF/scope/clockaudit, fullDRC/antenna and readonlymeasurement. No newroute call, no failure reclassified success.11GiBRSS/12GiBcgroup/2GiBhostreserve unchanged. Current candidate originalclass/PG/fullLVS/threecornerSTA and broader original828netscope restoration remain required after this diagnostic. Follow same live job; do not restart on observation timeout.

COLLECTOR GENERATOR41434944363/sourcef878816a SUCCESS. Actual c0d420cdbc31863bf21086e88c12f494779961225031c261d6b05fe07e7585a7 GDS1078900bytes: four HBT54/56/106/108 emitter accesses on two collector nets44/598,12newVia2 each,48total. OnlyVia2/M3 added1732800/12048600nm2; originalM2/devices unchanged. Fullwave diagnosis41433864856 of rejectedparent41430498959 showed30..94mV collector pathlosses, motivating this repair.

ACTUAL PHYSICAL41435641296/source262ac9b4d9142be6235c68d279c67aac9b92e3a8/release431371522 PASS.560DRC categories zero markers, deep andflat500primitive LVS match, all13intentionalfaults rejected. Derived13136427750=354889bytes SHA62f6d57cb094be6e1a1905762e5e58fdcd44a3045f6f1fc89a0480d868a4df48.

ACTUAL CANONICAL41438707959/source6ecc4bac9ac806babd879413cd6d7230e70b826d/release431392541 PASS.123controls=96unchangedprevious+27collectoridentity/offset/grid/guard/cut/spacing/enclosure mutations. All113partitions×13layers=1469comparisons. Exactlypartitions3/51 changedVia2/M3,24cutsperpartition,areas866400/6024300nm2each. All500devices1446terminals238native114electricalnets978anchors25ports and78canonicalfiles preserved. Native port order actualpositions15/16 reverted fromxn,xp toxp,xn; always bind actualneworder rather than assumingIDs unchanged. Derived13138450060=1449973bytes SHA137114c9609b4312005c8f518a2eed84330736f9f4597b757275fd0ecd6ff34b.

FRESH RC41439516945/source710869eb13082f3c3dc488159bf167d937294454/branchcodex/cdr-collector-via2-fresh-rc/release431398178. Host byte-for-byte reversible toa53fb2f3 after exactproducer/candidate/schema/status/branch/measuredport substitutions. Original13commandplan/658runtimefiles/11numericalreceipts/bothMIMorders and resource limits unchanged. Sourcecontrols PASS; native extraction live at dispatch observation. Require actual terminal qualification, measuredR/Ccounts and model/composition hashes; then same fullloadedgates. Loaded negative selector-order fixture must change to parentxn,xp because currentactualxp,xn. No waveform shortening/gates relaxed.

Parent drainM23loaded41430498959 remainsREJECTED: phase14.3184mV<30mV,VI43.0307uA<50uA,Vce.337433/.334166/.358205/.356719V<.4V,samplermaxdelays45.78125/41.71875/51.09375/54.53125ps>37.5ps,wrongsign0/0/2/34. All1045823299rawbytes SHA bf5572baba3665b925385cf257686b7fb8dbcb24371e9de65bef5196a53fddb3 preserved in original release. Physical/canonical/RC success is not electrical, EM/PVT, closedloopCDR/PLL/SERDES, fullPHY or finalmainchip timing acceptance.

Next: follow actual recovery and freshRC handles. On successfulRC, consume actualcensus/portorder in full unchangedloadedwave stage; use passive comparison only as diagnosis. On recovery completion, inspect realcompleteDRC and scopedelta before choosing memory-bounded reroute. No new mainchip reroute until recoverability is proven.8hourreadonlymonitor remains automatic_native_dispatch=false.

Observed at 2026-11-02T11:57:08.403779+00:00:
- 41415994457: completed/failure
- 41435641296: completed/success
- 41438707959: completed/success
- 41439516945: completed/success
- 41439875813: completed/failure
- 41439959911: completed/failure
- 41440092152: completed/success
- 41440285882: in_progress/None
