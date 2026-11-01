# Cloud continuation — checkpoint v246

Updated: 2026-11-01T13:48:26.209792+00:00

Latest instruction: **her şeyi bulutta yap, lokalde bir şey bırakma temizle.**
It overrides the earlier local-execution wording in the active goal. All CAD, simulation, native archive/layout/waveform acquisition and numerical/geometric analysis run on GitHub. Local coordination uses source/API-derived text in RAM only. Never acquire native ODB/DEF/GDS/SPICE/raw archives locally, including RAM. The local workspace and project temp entries were verified empty, with no local CAD processes. Unrelated user files remain untouched.

## Current mainchip result and next repair

Restoration41308526628/source05d336a1b1b681c9d96b71d464c5ea430835e438, release430583367, is a terminal failure. The master representation correction passed for58masters/1666rectangle tuples; serialized before/after SHA25623119c37fd7402fc26de7f2fc59cb6f7db0859a4a82dec7ca62eb205dcf193fa. All1691 original clock/fixed-net records and attached geometry passed unchanged. The next original wire-only connectivity gate rejected the candidate. Power-contact, final DRC/antenna, RC and timing have not completed.

CandidateODB:214409779bytes,SHA256d526feec659883b65dc737853d4d6a192d529384e2676d8a2d17e9b5e7d6de7e.
Native archive:469346574bytes,SHA25665f84c98d2207f238194a97f27728405d3c44f278a85db2837d3b89a04985385, release430583367.
The full1726-member derived artifact and native release contain828 original connectivity graphs and828 restored-owner reports. All1656 large per-net records remain in the native cloud archive; they are authenticated and indexed, not falsely claimed copied into Git. The other95 proof files are already imported under docs/evidence/scoped-restoration-native-terminal-41308526628.

Diagnosis41311644194/source8f8f13a42d0edf2a3d11ef0931351c2974ba9c29 PASSED13controls and exact replay of every failed original graph. Of828owners,142fail the original wire-only predicate:113antenna owners and29counterpart owners. Full22-file proof390b08ec7dbbaeb0009aaf64ecaed3c3d71c0f37 is imported under docs/evidence/restored-connectivity-diagnosis-41311644194. This is diagnosis, not repair.

Pin-metal diagnosis41312549409/sourcea8588f493cc2816fa4e5c601209a4fd89f670dc8 PASSED all23controls (13original+10new) and actual authenticated readout. Adding only the observed ODB/LEF pin-metal rectangles in a separate diagnostic graph connects all142nets, under BOTH positive-area and closed-boundary overlap. Original pin access is missing on0nets;57nets have a single actual pin rectangle that directly bridges original wire components. No joining by logical pin name, inferred via, or unobserved filled gap is allowed. Original wire-only gate and original failures remain unchanged. Full24-file proof1f8da68823e1451c7b04a3a831d57d6b2e6060ce is imported under docs/evidence/restored-pin-metal-diagnosis-41312549409.

**Next:** Verify the observed pin rectangles against the actual frozen standard-cell GDS/LEF and placement transforms on GitHub. Do not call all142 true opens, blindly reroute them, or silently turn the diagnostic augmentation into acceptance. If actual pin metal explains connectivity, qualify an explicit physical-conductor model correction with preserved original reports and controls for disjoint pin shapes, layer separation, missing vias, positive-area contact, all828owners and all1351diode pins. Then run the remaining native PG, final DRC/antenna and matching-netlist/RC/STA gates. No original physical criterion is waived.

No new native routing was run during these diagnoses. The saved8-pass router reported397last-router violations; this is not final DRC acceptance. Preserve608diode ownership separately from828routing ownership,1691protected nets,1351diodes and2702required PG contacts.

## Current PHY results

Width2 native41306148937/source2a62d651d415fba8db3c5b758d1b66c05cde3a38, release430565351: actual engine returned0 in863.844793s, no diagnostics. Device/VI gates pass; phase37.0801368476mV passes the unchanged30mV limit. All six data gates fail. Full111-file proof was imported earlier.

Full-wave diagnosis41309130293/sourced516afbe5391c42d1f1e378102116cc593a23680 passed34controls and reproduced every original measurement. At0.6UI all255 A-source values are valid and divider signs correct, but111A-buffer signs are wrong. C/D dividers have64/100 source-valid wrong-sign samples. A bit128 buffer remains old polarity at1.0UI. Full24-file prooff5623ecd4f4b400c63548f01966be8fae753fcbd is imported.

The4um and8um trials independently start from the golden1um parent and change only12rppd widths. All lengths,HBT Nx,200MOS units,ports and electrical gates remain unchanged. Retained wireRC is screening only: no regenerated layout or freshPEX is claimed.

- **4um41310177288/source d86d44b42ab1dca1af333efa65098c872649bb74**, release430594411: source controls passed75new+75inherited refusals and original binding. Native was stopped at the original1200-second engine budget (observed return-15). **No measurement result exists; electrical acceptance/rejection is unknown.** Full110-file proofc8fa7776e54f75ebc84317908b89a681abc524c4 is imported. ModelSHA256ed9291cabadfbad104fe8ed168114d2c000133011491c073e7aa660ba0d6b9a6.
- **8um41310192873/source66fb47bb12eff45c83b3d2819d281f99960ac4cc**, release430594515: actual engine returned0 in934.837169s, no diagnostics. All six data gates, device gate and phase gate fail. Phase25.8611110771mV is below30mV. A/B have64/29below100mV samples; C/D have92/28wrong-sign samples; X/Y have412/60wrong-sign samples. Full111-file proof9bb52e88a8b91196606b747cfa02263f61ad6bef is imported. ModelSHA256a8d8fa39039fe91a3ccca1ba724daef23b7a19c6fa28d551cda346ade90d4175.

Next PHY work must use these actual measured paths and device records to select a circuit repair. Wider dividers alone have not solved the loaded path. If4um completion is still needed, treat any larger execution allowance as an explicit new host experiment with identical model/stimulus/electrical gates, independent controls and exact-source release reservation. Do not present the timeout as a measured circuit failure. Preserve all rejected attempts.

## Timing and full-chip scope

docs/mainchip-restored-route-timing-handoff.md and docs/evidence/restored-route-timing-handoff-v241.json remain source-audit handoff, not executed RC/STA.
Old route12 requires153130instances/zero added diodes and netlistSHA2563c053c4cda51a001b926cce347b97de5c825cbff2082de550eeb9e31ff7fe5cd. Current layout has154480instances. Export and verify a matching diode-inclusive netlist from the current actualODB; old netlist/SPEF cannot be reused.
After physical connectivity and PG validation, generate fresh nominalSPEF, then the unchanged slow1.08V125C/typ1.20V25C/fast1.32V-40C corners,20/4/8/8ns clocks and5%derate. Require nonnegative setup/hold and zero setup/hold/slew/cap/fanout violations with propagated clocks. NominalRC is not foundry RCmin/max qualification.

Full serialPLL/CDR/SERDES, training/LTSSM, replay/credits, lane mapping/descrambling/TX, serial soc_top ownership, complete DRC/LVS/ESD and production approval remain open. Packet-interface SoC routing is not full serialPHY integration. No fullPHY, final timing or production acceptance is claimed.

## Cloud resumption and monitor

Authoritative branch:codex/complete-open-work. This checkpoint imports267files from the four new proofs (22+110+111+24). Existing sources and full artifacts stay on GitHub. Read each exact run before dispatch; do not duplicate jobs after observation timeouts. Current run/job snapshots and source bindings are in docs/evidence/cloud-active-checkpoint-20261024.json. Earlier failure receipts and sources remain intact there.

Eight-hour monitor configuration stays read-only,automatic_native_dispatch:false. Its last saved live observation had an HTTP502 error; do not claim monitor health without a new successful full observation. Two old checks.yml runs41292160619 and41293340525 were still active at the prior snapshot; consult the current API snapshot.

The current pin-metal collector recipe is docs/evidence/cloud-collector-recipes-20261029/cloud-pin-metal-v246.json. It has already run successfully; do not rerun its branch-creation mutations. All numerical/physical continuation remains cloud-only.
