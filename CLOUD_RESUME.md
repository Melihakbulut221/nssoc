# Cloud continuation — checkpoint v257

Updated: 2026-11-01T17:55:42.077839+00:00

Latest instruction: **her şeyi bulutta yap, lokalde bir şey bırakma temizle.**
It overrides the earlier local-execution wording in the active goal. All CAD, simulation, native archive/layout/waveform acquisition and numerical/geometric analysis run on GitHub. Local coordination uses source/API-derived text in RAM only. Never acquire native ODB/DEF/GDS/SPICE/raw archives locally, including RAM. The local workspace and project temp entries were verified empty, with no local CAD processes. Unrelated user files remain untouched.

## Latest result: six real physical divider shortcuts generated on cloud

Actual native run41333497715/source2f7f6e673e0bac5052d82e7ffd7073b9685f962f succeeded after31 controls (19 unchanged wire/coordinate plus12 geometry tests). It authenticated all3091 original RC capsule members, loaded actual GDS42ed5bcd567518786b718248947771172e9f5cc419d0aaa8fc8c49d8cfa4e876 and wire L2N57abb9fe69e4fcc57a18ee8a61fbcfa04475ad3331581062fde41f2d6aa6fe3b, matched complete M1/Via1/M2/Via2 layer unions, and generated all six A_p,A_n,C_p,C_n,D_p,D_n shortcuts. No target remains unrouted within this six-net candidate.

Actual new native file: native/nssoc_cdr_pd500_wire_shortcuts.gds in archive root wire-shortcuts;999700bytes;SHA256244992e91350d3bcac15fd58c48cc5249ee615ffc21f30f539a0cbb6b42fc347.
Permanent release430752170/tag cloud-results-41333497715-1-cdr-wire-shortcuts:
- complete-output-index.json asset699061027,1894bytes,SHA256f0258c68ee4bf6608e5b926f420cdd259a8119f7f5ef0e78a111be7dd903f3f3.
- native-candidate.tar.gz asset699061028,348712bytes,SHA2560dec57eeac173fc9c9ec0ca76d1a6cd218e265605c8e143188d69bac71ba7e17.
The native archive was never acquired locally. Derived artifact13094222549,164182bytes,SHA256a5ae083a4e41009d348b7fddc440efd4e57cc2c72b870e44912404d09e598de9.

Only0.6um-wide Metal2 shortcuts were added. Each endpoint reused its actual original four-Via1 landing, after proving same-net M1/M2 ownership and50nm lower/upper enclosure of each190nm square cut. Existing Via2 cuts and all original vias remain. There are zero new Via1 shapes. All original device/M1 geometry remains unchanged. The serialized GDS contains exactly the declared layer-union additions; deleting inserted shapes restores all original layer material. Foreign-M2 clearance605nm, foreign-via avoidance, same-net ownership, continuous route and existing die boundary checks all passed. These static guards are NOT the full PDK DRC/LVS or electrical acceptance.

All six selected routes use the first Manhattan path:
A_p [1024100,2059690]->[1084100,2059690]->[1084100,2055530];
A_n [1204100,2059690]->[1264100,2059690]->[1264100,2055530];
C_p [1024100,2835580]->[1084100,2835580]->[1084100,2831420];
C_n [1204100,2835580]->[1264100,2835580]->[1264100,2831420];
D_p [1024100,2587350]->[1084100,2587350]->[1084100,2580790];
D_n [1204100,2587350]->[1264100,2587350]->[1264100,2580790].
Coordinates are original1nm GDS DBU. New M2 area38344150DBU2 per A/C route and39784150DBU2 per D route; via added area0.

Preserved actual unsuccessful predecessors:
41332615153/source7374d2201b6541f67c23e6f56dda8b0b78325eb1/release430746317 passed27 controls but selected a nonexistent mim/precise/wire/native05/wires.l2n path; no generation. Correct canonical input is binding/inputs/wire/native05/wires.l2n (and matching wires.gds). New source checks selected paths against pinned complete inventory before acquisition.
41332859047/source9fb67f1332fbc2e17e51d182461a176b40669e6e/release430747892 passed27 controls and native layer-union checks but found no new via sites in a small search; no candidate.
41333160166/source60464d2610e69ffbd040c35ee4d5abef7778487f/release430750188 passed29 controls and preserved every10um bounded access refusal. It revealed that existing four-via stacks already occupy the1.730um x0.300um M1 /1.730um x0.290um M2 terminals. The final source reuses these existing qualified same-net landings rather than duplicating cuts. No clearance or electrical threshold was relaxed.
All four complete source/log/result proofs are imported under docs/evidence/wire-shortcuts-terminal-RUN. Initial failures remain genuine failures; only the final generation succeeded.

NEXT REQUIRED PHYSICAL ACTION: authenticate the new candidate archive on GitHub; run original full560-category DRC, deep and flat500-device transistor LVS and13 actual fault controls on this exact new GDS. Preserve original schematic/ports and bind fresh candidate metadata/output hashes; do not relabel the previous GDS result.json as a new generation. Existing validated physical pipeline is scripts/cloud_cdr_via2_m3_physical_recheck.py at9bf12d1e496f7d9192582175ab2fa714e3e8d41b: derive_physical uses cloud_cdr500_resistor_v59_physical.physical_source(original,'cd_shunt') with four exact substitutions; checker SHA3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66. Original source hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py checks actual layout result inputs/outputs, immutable PDK revision5e6d592e4002946a4616f798c357f0f3c06cf3b6, all560categories, deep/flat primitive counts124HBT/50MOS/98R/7MIM/221ptap and13 fault controls. AppImage3.0.5 SHA d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466, pinned frozen runtime and scoped AppArmor launcher must be restored on cloud using actual current-source admission, not old producer authority.
Then create canonical native view/new wire extraction and fresh RC for the exact new GDS, run unchanged loaded-wave/device/phase/V-I gates. The new RC/electrical improvement is NOT yet measured. Width2/Nx8 device-geometry trials are still not regenerated accepted layouts. Supply-path repair and complete closed-loop/serialPHY remain open.

Mainchip full64 run41323446729/sourceff1c0e6163e0ba1537a075d50e940fafc9332c64 remains active; do not restart or duplicate. After terminal publication qualify actual pins/classes/native connectivity, DRC/antenna and new diode-inclusive154480-instance netlist/RC/STA.

All CAD/native acquisition/analysis remains on GitHub; local source/API-derived coordination RAM only. Workspace and project temp remain empty. Eight-hour monitor inventory now697, read-only automatic_native_dispatch:false. Prior live monitor HTTP502 remains recorded. Full serial PHY, mainchip physical closure and final setup/hold remain unachieved.

## Previous checkpoint v256: original extracted wire bottlenecks and native coordinates mapped

Actual cloud run41331408334/source352b68e4d6a0f6fabbb18b850fff264e24fa0121 passed14 controls and mapped eleven physical-anchor pairs on the original RC graph. Its first coordinate reader handled EXT node records but omitted rnode records; most internal coordinate references were empty. Preserve this limitation and do not treat that first pass as complete geometry mapping. Proof0a1833238c5884607e6e2a703db8d0322b005886 at docs/evidence/wire-path-map-terminal-41331408334 contains all17 files (receipt3234ec6216d594cd6d2a5cf7605991c020df158516b141da3588da119a855e62).

Successor run41331683449/sourcef09bea650a2180b14efa651f3d648f9fdc3ba77e passed19 controls, including five additional coordinate parsing/refusal checks, and authenticated all3091 original native capsule members on GitHub. All24360 wire resistor cards match the original composed model through its exact node map. Every ranked edge endpoint now has actual rnode coordinates. Rnode numeric type is deliberately not interpreted as a metal. All original numerical calculations, original physical anchors and original source archive remain unchanged. Proof9676c2b87b2fcfc32a6e5981e78827883827506f at docs/evidence/wire-path-map-terminal-41331683449 contains17 files (receipt1d63cbd22390592f5be549d1c97012e88bb24cd76357f0f6c6fc28d77b01964e).

Measured effective resistance on original passive wire network:
- A series output T227_rppd_2 to shunt top T228_rppd_1:54.24519999999601ohm.
- A series output to buffer base T123_B:67.84909999998533ohm.
- A shunt top to buffer base:72.99409999998234ohm.
- C series output to shunt top:54.24519999999601ohm.
- D series output to shunt top:54.06919999999009ohm.
- AVDD to T124_C:42.62048764263007ohm.
- AVSS to T126_E/T129_E:21.13319100251308/21.18774570249786ohm.
- AVSS to shunt228/235/239:22.131607769626264/22.31409945376873/22.186162469739923ohm.

Important original edge identities:
A path R13592=24.5501ohm T273_mim_btm.n1--T227_rppd_2;
R13591=25.5151ohm T273_mim_btm.n2--T228_rppd_1;
R13590=4.18ohm between those internal nodes;
R13589=43.299ohm T123_B--T273_mim_btm.n1.
AVDD R18797=33.4312ohm P_avdd.n1103--T124_C and R18796=8.46587ohm P_avdd.n1102--P_avdd.n1103.
Ground126 R21114=13.5088ohm P_avss.n1959--T126_E and R21110=6.16703ohm P_avss.n1956--P_avss.n1960.
These are electrical network sensitivities to one-ampere DC test injections, not operating-current estimates, AC transfer, physical resistor footprints, proven sole causation or PEX signoff. Kirchhoff residual and energy conservation passed. Original limits/acceptance remain unchanged.

Native coordinates are supplied with scale1000/1/0.5; coordinate values are in centimicrons after applying lscale. GDS uses0.001um DBU. Actual terminal coordinates match for A series/shunt/base and supply124; ground126 retains native -2nm y offset, not silently normalized. For A, original physical anchors T227_rppd_2=[1024100,2059690],T228_rppd_1=[1084100,2055530],T123_B=[1084525,2305300]DBU, native cluster139/component66. Native rnodes T273_mim_btm.n1=[204120,439962] and n2=[215520,439962] in EXT coordinates. Full eleven-pair report retains all endpoint coordinate records and unit-injection energy contributions.

Next PHY action: on GitHub acquire the exact original GDS and wire L2N from original RC archive41251732540/release430243359 using scripts/cdr-wire-path-map-inputs.json atf09bea650a2180b14efa651f3d648f9fdc3ba77e. The native members include binding/inputs/parent/layout/nssoc_cdr_pd500_resistor_v59.gds and mim/precise/wire/native05/wires.l2n (plus matching wires.gds). Map actual owned conductor shapes, identify legal direct or wider signal/supply access and generate a reversible physical candidate with foreign-metal/via clearance checks. Frozen scripts/cdr_current_via2_m3_access_candidate.py at9bf12d1e496f7d9192582175ab2fa714e3e8d41b demonstrates authentic LayoutToNetlist layer/owned-net/GDS-union checks; its old eight-drain targets and authority cannot be reused as new geometry. Then full DRC/LVS, fresh RC and loaded-wave validation. Width2/Nx8 electrical device-geometry trials are not regenerated accepted layouts; do not pretend this wire-only diagnosis closes that gap. No arbitrary R scaling or gate weakening.

Mainchip full64 run41323446729/sourceff1c0e6163e0ba1537a075d50e940fafc9332c64 is still active; use existing handle, no duplicate dispatch. Its terminal results require actual-pin/class restoration/connectivity qualification, DRC/antenna, matching154480-instance netlist, fresh RC and unchanged final STA.

All work remains cloud-only. Local workspace/task temp empty; no local CAD or native payload acquisition. Eight-hour monitor read-only inventory now693; prior HTTP502 live monitor failure remains recorded. Full serial PHY, physical routing closure and final setup/hold remain open.

## Previous checkpoint v255: three native physical path and supply diagnoses completed

Cloud run41329721970/source11960a3bf126617857f2afda3686410664ff5764 passed71 controls (62 original and9 sign-settling controls) and all three isolated case analyses: width2, width8, buffer_drive. Each authenticated its original native archive on GitHub (129/129/124 members) and independently reproduced all six original data, phase, device and V/I metrics before reporting physical node voltages. All three original data gates remain false. Width2 remains device-safe; width8 and buffer_drive remain rejected. This is diagnosis, not a new simulation or accepted circuit/layout.

Complete60-file proof c084b7f31a004473bb62c7c478aba86b6ac8d6e1 is imported under docs/evidence/physical-path-diagnostics-terminal-41329721970; receipt SHA256 be10edf4e74e940f8a526fb2ddf84580f4805d537103cd3239177c33ff7e7553. Initial run41329263955 failed source parsing before native acquisition because of missing whitespace in fn.__code__ is value.__code__. Its source/run/jobs/log/receipt are preserved. Successor fixed only that syntax and passed all71 controls.

Actual width2 sampled measurement-window common-mode means along A: sampler2.100638V, series input2.034841V, series output1.723213V, shunt top1.613528V, buffer base1.673503V, buffer collector1.836408V, first downstream receiver base1.870649V. Same-net physical terminal identity is verified. Actual supply terminal xpd.w_t124_c has mean avdd drop0.351546V; tail126/129 ground rises0.113409/0.116035V. Shunt228/235/239 ground rises0.112550/0.106404/0.112662V. These are sampled waveform voltage measurements, not inferred DC currents or power signoff.

Width8 shunt228/235/239 ground rises increase to0.220667/0.199536/0.210432V. Nx8 buffer drive retains A series-output/shunt-top means1.722627/1.613000V and supply124 drop0.352617V. At0.6UI all255 A source samples are valid in width2, while buffer/receiver wrong-sign counts are111/129; Nx8 buffer drive worsens buffer wrong signs to125. Full path reports preserve A/C/D_X/D_Y, all receiver identities,138 supply terminals per case, unchanged sample windows and gates. Sign-settling is an additional diagnostic, never a substitute for100mV acceptance.

Next PHY work: locate the actual original500-device layout builder, GDS and fresh-RC producer41251732540 via scripts/cdr-via2-m3-loaded-producer-inputs.json at2a62d651d415fba8db3c5b758d1b66c05cde3a38 (not present at root105fe). Map measured high-current signal and supply terminal drops to authentic interconnect geometry; repair legal conductors/PDN and regenerate fresh physical extraction on cloud before evaluating. Large same-net and supply drops motivate this direction but do not prove a single root cause. Do not blindly repeat tail sizing, arbitrarily scale extracted R, widen divider devices, weaken limits or relabel diagnostic success as PHY acceptance.

Existing full64 native route41323446729/sourceff1c0e6163e0ba1537a075d50e940fafc9332c64/release430685443 remains the only active route. Observe it without duplicate dispatch; after terminal preservation qualify actual new pins/connectivity/original route classes, DRC/antenna, matching154480-instance diode-inclusive netlist, fresh RC and unchanged three-corner setup/hold.

All CAD, simulation, native acquisition and numerical/geometric analysis remain on GitHub; local coordination uses source/API-derived text in RAM only. Workspace and task temp verified empty. Monitor remains every8hours, read-only, automatic_native_dispatch:false, now inventories691 runs; prior live monitor HTTP502 remains unresolved evidence, not healthy qualification. Full serial PHY, physical routing closure and final timing remain open.

## Previous checkpoint v254: buffer drive experiment rejected; full raw diagnosis completed

Actual native run41325168813/source43fd3f71a289fef004aeb41cd2d0972d81f76f41 finished with electrical rejection, not timeout. Engine return0,1088.429415022s, no diagnostics. All six original data checks failed; device limits failed. Phase40.0143933667mV passes30mV and loaded V/I passes. Native archive and failures are durably published in release430697288/tag cloud-results-41325168813-1-cdr-sampler-load. Complete71-file derived/native-publication proof990d448dd8f502691046b7b6dbb4ae2621e87375 is imported under docs/evidence/buffer-drive-native-terminal-41325168813 (receipt a3295ba5cfabd0a1791f7d77789e4ad9ec7f97426b7217502b89eae6dab41ff5). No native archive was acquired locally.

Cloud full-wave run41327211667/source9c5843a973b5a0175d137af0780ae1b5aca46968 on codex/cdr-buffer-wave-analysis PASSED62 reader controls, authenticated all124 native archive members and independently reproduced every original six-data/phase/device/V-I measurement. It is a successful diagnosis of a failed circuit. Complete25-file proof fc2d712203a350ba8a68d7c650290c771a597a29 is imported under docs/evidence/buffer-drive-wave-terminal-41327211667 (receipt76751db63c22a55ec771dae301222f5de480be5e76b245b40cdb12874752e70f).

Nine actual HBT minimum-active-VCE failures against unchanged0.4V:
129=0.39647300049766077V;
137=0.29473418798359907V;
139=0.2964981295741759V;
142=0.27748090769744127V;
143=0.27614763950230437V;
155=0.34184134412719663V;
157=0.3445799462464897V;
160=0.33242284308074294V;
161=0.32964571373351964V.
These are C-buffer tail129 and all eight XOR selectors. The prior width2 parent passed device limits. Increasing tail Nx4 to8 and halving collector load length therefore cannot be adopted as a fix.

Compared with width2 parent41306148937, A/B below100mV sample counts stay97/25; C wrong signs30 to31 and D stays33. X wrong signs418 to383, Y6 to12. All six data gates remain false. At0.6UI with all255 A source samples valid, A-divider wrong signs remain0 while A-buffer wrong signs worsen111 to125. New A/C mean tail currents are3.582214/3.566502mA, compared with2.529654/2.513732mA for width2. A/C tail minimum-active-VCE becomes0.483172/0.396473V. Do not infer current doubles merely because Nx doubles; measured common-mode/headroom/loading must govern the next design.

Next PHY work: use the actual physical driver/consumer snapshots and sampler worst-bit windows to address the upstream A/B margin/settling failures, C/D bit errors, and divider/buffer/XOR common-mode and headroom. Preserve the width2 device-safe baseline and failed Nx8 trial. Do not just repeat stronger drive or relax thresholds. Any new geometry remains exploratory until regenerated legal layout, fresh extracted RC, corners and full closed-loop/link proof. Existing current evidence is NOT a full serial PHY or chip timing result.

The reader now accepts a passing device flag only if its recomputed decision agrees, rather than hardcoding failure. Data_passed is independently enforced as ALL six data checks AND the original phase gate. It additionally reproduces loaded V/I against the original frozen producer statements;62 controls include exact original VI comparison on four fixtures and invalid combined-data flags. All original electrical limits and accepted=false/full-PHY scope are retained.

Mainchip full64 native run41323446729/sourceff1c0e6163e0ba1537a075d50e940fafc9332c64 remains active; observe existing job/release430685443, never duplicate it. After terminal publication authenticate outputs on cloud, restore original route classes on actual new pins, requalify native connectivity/GDS, measure DRC/antenna, export matching diode-inclusive netlist and extract fresh RC for unchanged three-corner setup/hold. Old candidate/142-net pin proof and old netlist/SPEF are not new-route evidence.

All CAD/native acquisition/analysis stays on GitHub. Local workspace/task temp remain empty, source/API-derived text coordination uses RAM only. Eight-hour monitor remains read-only and inventories689 runs. Full serial PHY, physical routing closure and final timing remain open.

## Previous checkpoint v253: A/C buffer drive candidate qualified and native screening dispatched

Width2 diagnosis showed source-valid A divider samples arriving before the buffered output, with A/C tail minimum active VCE of0.573442/0.486867V against0.4V. Width2 native41306148937 passed device/VI and37.080mV phase but failed all six data gates. The new source43fd3f71a289fef004aeb41cd2d0972d81f76f41 on codex/cdr-buffer-drive changes exactly two tail HBTs126/129 from Nx4 to8 and four collector loads232/233/243/244 from length1.8um to0.9um, retaining width8um. All12 width2 dividers,200MOS units, physical terminals, remaining geometry and original measurement/current/data/phase predicates are retained. Reversing all six edits restores exact parent bytes and descriptors. Both the500-device binder and650-device native model receive identical edits and actual binding exposes Nx8 for both tails. This is a native electrical experiment, not layout acceptance.

Independent controls41325031300 PASSED:67 new refusal controls,75 inherited width controls and all earlier suites. Complete45-file proof8725ab4120e5999dba12b776a5d3fc2115fe296c is imported under docs/evidence/buffer-drive-controls-terminal-41325031300. Receipt SHA2562f3d959bd7331ade5dea063c56557dfe437699f09e4880a7cc5d0a156972cb3a.

Actual native run41325168813 was dispatched exactly once on that same source with independent controls41325031300. Empty exact-source release430697288 / cloud-results-41325168813-1-cdr-sampler-load was reserved and read back. Its own source controls passed; native job124903702846 is active. Observe the existing job; do not repeat dispatch/reservation mutations. Original ngspice/model/runtime and1200-second engine supervision are retained. The shared host publishes native archive parts, complete-output-index and parts.json into the release even for electrical failures; fallback artifacts preserve failed publication. Retained distributed RC is screening only. Any useful result requires regenerated layout/fresh PEX and full corners/closed-loop/link proof before PHY acceptance.

Actual full64 mainchip route41323446729/sourceff1c0e6163e0ba1537a075d50e940fafc9332c64 remains live at its Execute and preserve actual full64 route step. No internal route iteration is inferred from that API observation. Preserve its existing exact-source release430685443. After terminal publication, authenticate results in the cloud, restore original classes using actual new route pins, requalify actual new connectivity/GDS correspondence and run original-class DRC/antenna. Old d526... candidate/142-net pin proof must not be relabeled. Then export matching diode-inclusive netlist, extract fresh RC and enforce unchanged multi-corner setup/hold. Last measured old candidate still has399DRC and19antenna nets/23rows.

All CAD/native acquisition/analysis remain on GitHub; local source/API-derived text coordination is RAM-only. Local workspace/project temp empty with no local CAD processes. Native payloads must not be downloaded locally even into RAM. The8-hour monitor inventories both new runs and never automatically duplicates native dispatch. Full serial PHY, mainchip physical closure and final timing remain unachieved.

## Previous checkpoint v252: actual full64 native route dispatched and running

Source ff1c0e6163e0ba1537a075d50e940fafc9332c64 on codex/mainchip-full64-native integrates the actual original64-pass router with authenticated saved-diode acquisition, original prep/guide/PG/fixed-overlay/828-net clear, owned native engine/runtime/container and permanent checkpoint publication. Independent controls41323333392 passed all11 full64 lifecycle plus12 preservation/dispatch controls,0 failures/errors/skips, and authenticated2361 original source files. Complete20-file proof063318bb2cb55c5b394a4c091dc8d8fa6ebaf20e is imported under docs/evidence/full64-native-controls-terminal-41323333392.

**Actual native run41323446729 has been dispatched exactly once.** Permanent empty exact-source release430685443/tag cloud-results-41323446729-1-mainchip-bulk-postdrt-antenna was reserved and verified. The native run repeated all source controls successfully. Latest live observation: job124898487629/native-routing in progress at Execute and preserve actual full64 route. This step includes cloud acquisition and CAD; do not infer the current internal route iteration from the Actions step alone. Poll this existing run, not a replacement.

The native phase order is bootstrap,guide-overlay,guide-reload-audit,power-contact-audit,make-overlay,fixed-import,fixed-audit,clear,route. The source executes the exact original64-pass Tcl; it is a fresh same-seed trial, not a resumed internal iteration. Native report is bulk-postdrt-full64-inner-result.json; successful route status is COMPLETE_FULL64_NATIVE_ROUTE_CHECKPOINT. Route output pins are in bulk-postdrt-antenna/full-route-stage.json and work/bulk-postdrt-antenna/routed-fixed.odb/.def plus route-partial.odb/.def. Output preservation always runs. Host output is full64-native-evidence; fallback artifact contains the run-owned out directory. Do not download native archives locally.

The checkpoint intentionally retains temporary fixed classes. It is NOT a restored candidate, physical/timing/full-PHY acceptance. The next stage must restore classes using the actual new routed-fixed pins and the scoped restoration algorithm, then measure fresh native graphs and requalify relevant GDS pin correspondence. Old core.CANDIDATE d526... and exact142 failed-net/1300-pin/77-master-pin qualification are bound to the old8-pass candidate and MUST NOT be relabeled as new-route proof. Core.audit accepts an explicit expected tuple, but production values must come from authenticated new readout, not from making tests pass. No broad acceptance is granted by route completion.

Host preservation is now implemented and tested in mainchip_full64_output_preservation.py: exact four Tcl programs require capsule pins and64KiB cap; the two clock-gate DEF files are native-only and require matching capsule pins; host-progress is a regular JSON object capped16MiB and exact-copy verified. The original three host failures were reproduced before confirming the correction. All unexpected-file/symlink/unpublished-large/output-overwrite/hash-drift refusals remain. This correction is integrated into this full64 host.

All source and evidence are in GitHub, local workspace/task temp empty and no local CAD processes. The monitor tracks this run every8 hours and never automatically duplicates native dispatch. New source and reservation/dispatch recipes are already executed; never replay creation mutations. Last accepted physical evidence remains399 DRC/19 antenna nets/23 rows, qualified connectivity828/PG2702/protected1691 from the old candidate. Full serial PHY and final matching-netlist RC/STA remain open.
## Previous checkpoint v251: classification and source-only full64 qualification

Cloud run41321744519/source4090f5c3ce1d7655de4144299f69df278a2d7a16 passed16 controls and authenticated all1749 native members from release430648315. Every actual DRC/antenna record is retained. Counts:329 shorts +70 metal-spacing markers =399;19 antenna nets/23 rows. Among320 named owners:92 original diode owners,36 previous counterpart owners,186 outside-scope signal owners,4 protected nets and2 power nets. 369 markers involve an outside-scope signal;6 involve protected nets;13 involve power. All antenna rows lie inside the existing828-net scope. Source reports and42-file proof9663c2bcc94ceae21d7739bc6279740522e53524 are imported under docs/evidence/postrestore-classification-terminal-41321744519.

The actual routing effort was explicitly limited to8 passes by mainchip_bounded_route_stage.py at7a0776718ec37a106b7dfde0cbd477c6a2a5522f, despite the original environment requiring64. Complete the intended effort on the same seed/scope first, so a scope expansion is not conflated with additional router optimization. Existing final399/19/23 rejection remains authoritative until a new native candidate is measured.

New mainchip_full_route_stage.py/source0502f3cbb7e74286d6cb024504d593be04bd778a executes the byte-identical original64-pass Tcl (SHA2564769e146e1bf59e08fb4c08c436d1f0f285de4086f8c72974825305db6fa9a7b). Cloud run41322259020 passed all11 lifecycle controls,0 failures/errors/skips. It preserves partial failures and rejects8-pass programs, stale/symlink outputs, repeated calls, wrong commands/budgets, missing outputs, source drift and false acceptance. Source proof fcde4e2991da08c38e0521c8dd4e2756da787287 is imported under docs/evidence/full64-controls-terminal-41322259020. **No native64-pass run has been launched or accepted.** This will be a new trial from the same saved-diode seed, not a claim of internal router-iteration resume.

Next concrete work: integrate full64 execute_stage after the original828-net clear and before current qualified restoration/connectivity/PG/final audits; fix exact host preservation cases before dispatch. The original cloud_mainchip_saved_diode_routing.perform acquires CURRENT, failed donor41172959321/release429743993 and saved reconstruction41190910993/release429853533 before tail.restore_prefix; do not omit either seed acquisition. The existing scoped-restoration host only replays a saved8-pass route and cannot itself run64. Preserve original frozen source projection, owned container, native runtime and source pins. Adapt new routed-fixed/candidate pins from measured results rather than keeping old hardcoded pins. Keep all1351 diode attachments/1691 protected nets and all original physical gates. Independently qualify combined source, reserve exact-source cloud release, then dispatch exactly once. If using staged routing followed by restoration, preserve original failures and distinguish route completion from full physical acceptance.

No native data is stored locally. Full serial PHY still fails width8 device/data/phase gates; final RC/STA needs the actual current diode-inclusive matching netlist. Goal remains active and unachieved.

## Previous checkpoint v250: completed native audits and rejected candidate

All project CAD, simulation, native data acquisition and analysis run on GitHub. The local workspace and project temporary locations were verified empty; no local CAD processes were present. Source/API-derived text coordination uses RAM only. Do not download native ODB/DEF/GDS/SPICE/raw archives locally.

Actual run 41317927121/source 340fb4f217e920c1bc4d5fa552e4b11eb81d0a4b completed all six native phases: qualified connectivity for 828 nets in both modes, 2702 direct diode power contacts, and unchanged 1691 protected clock/fixed nets passed. The physical candidate is still rejected: 399 DRC markers, 19 antenna nets and 23 violation rows remain. No final timing or full serial PHY acceptance.

The host job is red with three preservation errors: original-clock-gate/before.def and after.def are already authenticated in the native capsule but refused by the derived suffix filter; oversized host-progress.json is outside the native publication prefixes. Preserve these failures and fix the exact output cases with refusal controls in a successor; do not rerun CAD merely to recolor CI. The permanent native release is 430648315, archive SHA256 c9cf1d646a8116c5ddc77dcb0d36838677c9d6243f4db08df9ac17369d65f95f. No candidate data needs a local copy.

Width8 full-wave diagnosis 41319989811/source 7866608fd58ceb372fa927b408ba7087c54d9610 passed 48 controls and reproduced the six original measurements and all device tables. Its proof is imported below docs/evidence/divider-width8-wave-terminal-41319989811. It confirms failure, not PHY acceptance: phase 25.861 mV is below 30 mV; eight HBT limit violations and one aggregate stage-tail current violation remain. Full raw waves stay in release 430594515.

Readout 41320700483 failed because the final*.json selector included the 27 MB all-net antenna table. Corrected source 23a41f2b4c6d057babbffad3dfd3b768f1809e49 uses an explicit bounded-report allowlist and four selection controls while still hashing EVERY archive member. Run 41321233030 is the single dispatched successor; inspect its actual terminal result before relying on its readout.

Next: collect that existing readout, classify the 399 DRC markers and 19 antenna owners on the actual current candidate, then qualify the next physical repair. Export and prove a matching diode-inclusive netlist and fresh RC before unchanged multi-corner setup/hold gates; old route12 netlist/RC is stale. PHY work must address the measured internal divider/buffer/device failures, not declare width-only screening complete. All work continues in the cloud.

## Previous checkpoint v249: qualified native adapter and dispatch

The private adapter is implemented at source 340fb4f217e920c1bc4d5fa552e4b11eb81d0a4b on codex/mainchip-qualified-restoration. It binds the unchanged qualified core to the original native connectivity reader, preserving all original wire-only reports. Candidate ODB bytes and both GDS qualification records are hash-bound. The original source, predicate and graph functions are not mutated. Native source additions are authenticated in the existing source capsule.

Independent control run 41317771048 completed successfully: all 49 restoration controls, 67 inherited graph/GDS/model controls and 12 boundary controls passed. The actual original native reader function body reproduced all 1656 graphs across the authenticated 828-net dataset with simulated ODB accessors. Graph, predicate and scope source files were byte-identical to frozen native dependencies. This is boundary qualification, not actual ODB execution. Complete 48-file proof 26ef125546aa247ab72707f20c04a30c0040ee33 is imported under docs/evidence/qualified-native-binding-controls-41317771048.

**Actual native run 41317927121 is dispatched on that exact source**, with the independent control run supplied. Empty exact-source release 430648315 / cloud-results-41317927121-1-mainchip-bulk-postdrt-antenna was reserved and verified before native admission. The native run's repeated source controls also passed. Poll that existing run and its release; do not restart it merely because observation expires.

The sequence is original class restoration, full restored snapshot / 1691 protected-net audit, qualified physical connectivity, 2702 direct power contacts, final DRC/antenna checks and final unchanged-snapshot comparison. No routing, reconstruction or physical geometry edits were added. The result explicitly names qualified physical audits and retains original_wire_only_acceptance=false. A successfully completed invocation does not establish a zero-violation result; inspect the actual census and bounded_cycle_qualified.

Next: collect and authenticate the terminal native capsule, preserve failed and successful phases, and repair whichever actual physical gate fails. If physical checks pass, export a matching diode-inclusive netlist from the actual current database and extract fresh RC before the unchanged multi-corner timing gates. Full serial Gen3 x4 PHY remains unaccepted. No final timing or production acceptance is claimed.

All CAD, native acquisition and analysis remain on GitHub. No local project files or native payloads are needed. Completed collection, dispatch and reservation recipes are saved in docs/evidence/cloud-collector-recipes-20261029/cloud-qualified-native-v249.json and must not be rerun as creation mutations.

## Previous result: complete 828-net qualified connectivity model passed

Cloud run 41316154727 at source 77247c06db249537a643fb2e6e9a256bdbcfe557 (codex/mainchip-qualified-pin-connectivity) completed successfully. All 67 controls passed: 52 inherited and 15 qualified-model controls. The complete authenticated 828-net dataset passed both overlap modes after replaying all 1656 original graphs. All 142 original wire-only failures and 686 original passes remain preserved. Only the actual 1300 pin observations / 77 master pins independently verified against frozen GDS, LEF and placement transforms were admitted as physical conductors. All 1351 diode attachment requirements remain enforced. No logical-name bridging, inferred vias or geometry edits are allowed.

The pure core is scripts/mainchip_qualified_pin_connectivity.py at that source, with the wrapper scripts/cloud_mainchip_qualified_pin_connectivity.py and 19-file manifest scripts/mainchip-qualified-pin-pins.json. Complete 34-file proof 90231e2a46b2bccd0169c304cddae2b7aa8cade7 is imported under docs/evidence/qualified-pin-connectivity-terminal-41316154727. The successful result is explicitly NOT execution of the native adapter and is not chip acceptance.

**Completed in v249:** the private native adapter is implemented and independently qualified; actual native run 41317927121 is now the authoritative next step, as described above.

Then execute the remaining 2702 power-contact checks and final DRC/antenna checks. Fresh matching-netlist RC/STA and full serial PHY remain open. No native adapter, new physical route, full chip LVS/DRC, fresh RC, final timing, or full PHY acceptance is claimed by this result.

All CAD and analysis stay on GitHub. Local workspace/task temp entries are empty; source/API-derived text coordination uses RAM only. Completed collector recipes are preserved and must not be rerun as creation mutations.

## Previous result: actual GDS pin correspondence passed

Cloud run41314829887/sourceb0cc820906e9cc75c3a7d55fce11297a8e4f1da1,branch codex/mainchip-pin-gds COMPLETED SUCCESSFULLY. All52controls passed (23inherited graph+29geometry/parser/grid controls). Against the authenticated current restored snapshot, all1300pin observations across the142original wire-only failing nets matched77unique master/pin definitions. Native-to-LEF region equality, GDS drawing-metal coverage including polygon holes, and all placed orientation/origin transforms passed. Missing/mismatched pins:0. Both actual SRAM masters RM_IHPSG13_1P_2048x64_c2_bm_bist and RM_IHPSG13_2P_256x16_c2_bm_bist were included. Actual required GDS reference libraries use0.001um DBU,matching the1000DBU/um native database.

All original native archive members from release430583367 and all five original Ciel PDK archives at revisionc4b8b4e5e7a05f375cca3815d51b3a37721fbf5c were authenticated. Actual comparison used only libs.ref GDS/LEF files and the pinned drawing-layer map. No pin-marker layer was counted as conducting metal. Full33-file proof35f96b34545c1db4fef2b963816958337ec1f499 is imported under docs/evidence/restored-pin-gds-terminal-41314829887. Full native layouts remain cloud-only and unchanged. Peak runner RSS2374316KiB.

Earlier run41314212802/source6a256976d29b2dd5d36b1726245b70ee456dca82 passed45controls and authenticated native/PDK inputs, but its reader stopped at a noninteger GDS-to-ODB scale while scanning all PDK GDS files,including QA/test layouts. This was not a measured chip-connectivity failure. Full29-file proofde9dc9a9d34228bb0c134dd73e59db7eee33bb41 is imported. The successor limits candidate material to actual reference-library paths, records units for every GDS, converts only matching master cells on an exact integer common grid, refuses rounding/overflow, and adds7controls.

**Completed in v248:** the explicit physical-conductor core is implemented and qualified on all 828 nets. See the latest result above for the remaining native adapter binding.

The native integration point is scripts/mainchip_scoped_counterpart_restoration_native.py at source05d336a1b1b681c9d96b71d464c5ea430835e438. Its restored-audit clones targeted.bind_phase(plan,scope); that function currently wraps native.connectivity(path,scope_core.observation_scope(plan,scope),out). Add the qualified adapter privately without mutating frozen source functions. Original validate_connectivity returns changed_nets/both_modes_complete and requires every pin/diode to share a single conductive component in both modes. Keep original wire-only reports separate and explicit. Native host source additions must be included in NEW_NATIVE and their source manifest/projection; require independent same-source controls and exact-source empty release reservation before native execution.

Then run the remaining native2702PG-contact, final DRC/antenna and clock/placement preservation audits. Final full-chip timing and fullserialPHY remain unaccepted. No route/database/pin geometry was edited in these read-only diagnoses; no final chipGDS, fullDRC/LVS, newRC orSTA was executed.

Completed collector recipes: docs/evidence/cloud-collector-recipes-20261029/cloud-pin-gds-v247.json. They have already published both proof branches; do not rerun their creation mutations. The full source and primary OpenDB transform references are preserved in each proof. All work remains on GitHub; workspace/task temp are empty.

## Current mainchip result and next repair

Restoration41308526628/source05d336a1b1b681c9d96b71d464c5ea430835e438, release430583367, is a terminal failure. The master representation correction passed for58masters/1666rectangle tuples; serialized before/after SHA25623119c37fd7402fc26de7f2fc59cb6f7db0859a4a82dec7ca62eb205dcf193fa. All1691 original clock/fixed-net records and attached geometry passed unchanged. The next original wire-only connectivity gate rejected the candidate. Power-contact, final DRC/antenna, RC and timing have not completed.

CandidateODB:214409779bytes,SHA256d526feec659883b65dc737853d4d6a192d529384e2676d8a2d17e9b5e7d6de7e.
Native archive:469346574bytes,SHA25665f84c98d2207f238194a97f27728405d3c44f278a85db2837d3b89a04985385, release430583367.
The full1726-member derived artifact and native release contain828 original connectivity graphs and828 restored-owner reports. All1656 large per-net records remain in the native cloud archive; they are authenticated and indexed, not falsely claimed copied into Git. The other95 proof files are already imported under docs/evidence/scoped-restoration-native-terminal-41308526628.

Diagnosis41311644194/source8f8f13a42d0edf2a3d11ef0931351c2974ba9c29 PASSED13controls and exact replay of every failed original graph. Of828owners,142fail the original wire-only predicate:113antenna owners and29counterpart owners. Full22-file proof390b08ec7dbbaeb0009aaf64ecaed3c3d71c0f37 is imported under docs/evidence/restored-connectivity-diagnosis-41311644194. This is diagnosis, not repair.

Pin-metal diagnosis41312549409/sourcea8588f493cc2816fa4e5c601209a4fd89f670dc8 PASSED all23controls (13original+10new) and actual authenticated readout. Adding only the observed ODB/LEF pin-metal rectangles in a separate diagnostic graph connects all142nets, under BOTH positive-area and closed-boundary overlap. Original pin access is missing on0nets;57nets have a single actual pin rectangle that directly bridges original wire components. No joining by logical pin name, inferred via, or unobserved filled gap is allowed. Original wire-only gate and original failures remain unchanged. Full24-file proof1f8da68823e1451c7b04a3a831d57d6b2e6060ce is imported under docs/evidence/restored-pin-metal-diagnosis-41312549409.

**Completed in v247-v248:** actual GDS/LEF/placement correspondence and full 828-net qualified physical connectivity now pass. Remaining native PG, DRC/antenna and matching-netlist RC/STA work is described above.

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
