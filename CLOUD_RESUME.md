## 2026-11-14 — fresh postCTS repair running; new physical gate-mesh extraction dispatched

**PostCTS:** first43624906428/sourcea425eb5b862feeda83ed86f455b621d2f140fb4f failed before CAD because scripts/restore_predecode_chip_boot.py was absent from integration base. Added exact tested helper from placementa3a79275..., verified all4original mapped-source input hashes against candidate branch before dispatch. Current source63a2a8fbed52f0765a46cd5f5cbacff5cf773623/run43625119515: exact mapped-source restoration and pinned runtime preparation passed; native three-corner before/after STA plus electrical/setup/hold repair confirmed in_progress. Continue this handle, not43624906428. Original clocks/derating unchanged, boot/equivalence/routedRCX remain separate.

**Fresh paired650 gate mesh:** branchcodex/cdr650-paired-gate-mesh/sourcebc78aa9667a0915c7dc31b244b714a1d2166a362. Adapted original qualified mesh producer41721107217/source6fc562599fdc527bf95c0ef92332e87a4efd26e6. Numerical characterize() body byte-identical except both exact GDS pins changed to new285760.../1627742bytes. Acquires new actual candidateGDS native14124521775, terminal geometry safe14124672969, native identity safe14125295448; binds producer IDs, heads, success and archiveSHA. Every actual polygon/contact and200MOS dimensions/ownership reread. Original four pitches600/300/150/75nm, analytic70ohm checks, full200gate current-return conservation retained. Frozen nominal7ohm/square and15ohm/contact are still only nominal published material values, NOT calibrated signoff corners or temperature. Intrinsic model/runtime unchanged. Must not claim polyC/material/fullPEX/loadedPHY qualification from this resistance-network diagnostic.

First mesh43625347253/source0ba45c... failed pip because version parser truncated0.30.4.post1 to0.30.4.; corrected exact original version and workflow pin, no numerical acceptance change. Current snapshot below. Expected safe paired650-gate-mesh-derived-RUN and native paired650-gate-mesh-native-RUN. All native content stays hosted. Next after gate mesh: original noise-preserving port reduction producer41725473326/source8d7874d8c9740725ed1e4cd8c3631ec1c81bc2e6, then full composition factory41733225660/source9bba58288772dd2bee9dab142e391d0616737973 using NEW metalRC43623877135 and NEW gate mesh/IDs. These original factories are reference only; never import old native geometry/RC or rejectednx1 whatif. Original frozen waveform/retimedD/SOA gates remain.

[{"id": 43625119515, "head_sha": "63a2a8fbed52f0765a46cd5f5cbacff5cf773623", "status": "in_progress", "conclusion": null}, {"id": 43625413974, "head_sha": "bc78aa9667a0915c7dc31b244b714a1d2166a362", "status": "in_progress", "conclusion": null}]

Full chip manufacturing goal remains incomplete. Original oldRTL route43614100441/43610680141 and boot43620739672 were live this turn, not restarted. Experimental cloud-evidence-summary.yml workflows must not merge into timing/combined.

## 2026-11-14 — correction: inherited metrics were NOT post-CTS timing; fresh repair dispatched

Authenticated stage diagnosis run43624756918/source078cba2d9f1e0476c3a62bb0e96c934855a2ba68 PASSED. Safe artifact14125851871 SHAbd8bea1955083690d7d32561049a24bb05018103008e11f0771505244432831f contains original-hash-checked metrics plus independently hashed first240-line report excerpts. The prior CTS snapshot mixed stale inherited metrics: slow -207199132.342ns and typical -127533037.097ns originated in step04 STAPrePNR, fast -71.779ns in step23 STAMidPNR BEFORE repair24 and CTS27. Step27 or_metrics_out.json contains NO timing metrics. Do not cite any of those as measured post-CTS timing. PrePNR worst path goes from rst_sys_n (5327loads,24.787149pF,153.759842ns slew) through row_bm to SRAM A_BM; report shows213590672ns terminal slew and -207199008ns library setup. These are diagnostic pre-placement/model extrapolation symptoms, not validated current chip timing; fresh per-corner measurement is required.

Fresh postCTS driver scripts/cloud_predecode_postcts.py is on branchcodex/predecode-postcts-repair/sourcea425eb5b862feeda83ed86f455b621d2f140fb4f. Exact source native14124619734/safe14125635095, all file hashes and CTS ODBfc440027... verified on hosted runner. Restores original mapped source separately, discards inherited metrics, separately measures three corners before/after guarded electrical and setup/hold repair using existing CorrpreBankedPostCTS. Original 20/4/8/8ns clocks and5percent derating retained. functional_boot_accepted=false, accepted=false, finaltiming=false remain explicit; no historical boot proof reused. Experimental workflow MUST NOT merge into integration. This is candidate repair, not routed timing, equivalence, serial PHY, or production approval.

{"id": 43624906428, "head_sha": "a425eb5b862feeda83ed86f455b621d2f140fb4f", "status": "in_progress", "conclusion": null}

Native files remain cloud only; no local source/native downloads. Follow current repair handle; also original boot43620739672 and original routes43614100441/43610680141 still in_progress at inspection. PHY next remains fresh gate-poly RC/composition on actual paired650 geometry, then unchanged loaded electrical gates. Full goal incomplete.

## 2026-11-14 — actual paired650 metal/MIM RC PASSED both native orders

Run43623877135/sourceca7922a41bb122ec714a23cd2ca5b7ea63d197ba completed successfully. New actual GDS285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514 yielded28634resistors,18488capacitors and7separate intrinsic MIM devices. Both native extraction orders produce identical complete R/C/device records; original13raw wire +9MIM identity fault cases rejected in EACH order. Actual650devices,2046terminals,1428anchors,200gatecontacts remained bound. No oldRC reused/scaled. Numerical methods, qualified Magic binary, raw conservation checks unchanged; MIM masks/access points derived from actual new GDS/native identities.

Safe14125052605 SHA26bccc7db4231b610aa780e128fea159424bafdf5b3cc32da3a3a4474f0d506c. Native14125201998 SHA1443428cee3752ae7c9b14aa65d01e614520ca5547e79abf8e406ff3c56617fb (386133458bytes), CLOUD ONLY. Native archive includes mos650-metal-rc/native/mim-precise/wire/rc03/{wires.spice,pump_wires.ext,pump_wires.res.ext} and precise_reversed, plus complete restored paired-terminal-anchors. Receipt docs/evidence/cdr650-paired-metal-mim-rc-20261114.json retains original full result and both complete variant reports.

**Next PHY work:** fresh gate-poly access RC on new geometry/anchors, proper MIM/metal/poly/full650 intrinsic composition, then unchanged loaded electrical checks. Do not call this full RF PEX or full PHY/electrical acceptance: gate_poly_RC_extracted=false,full_loaded_composition_executed=false,substrate_r_modeled=false,full_pex_qualified=false remain explicit. Use actual native650 device parameters and new native IDs; do NOT carry forward rejected nx1 transistor what-if or old RC. Keep frozen retimed-D selector semantics/windows and original transistor SOA gates.

**Newchip CTS diagnosis:** dispatched branchcodex/predecode-cts-path-diagnostics/source3c21f988de3987aec473c2f2ee74a620a688eab0 to select source-hash-checked run/27-openroad-cts text reports from native14124619734, without downloading native files locally. Current run snapshot below. Read worstpaths/clock/slew reports and repair the exact newcandidate; huge placement/CTS delay values are NOT timing acceptance. Actual GDS/ODB assets remain hosted.

[{"id": 43624148622, "head_sha": "3c21f988de3987aec473c2f2ee74a620a688eab0", "status": "completed", "conclusion": "success"}]

## 2026-11-14 — new full-chip predecode CTS completed, timing NOT accepted

Run43622573415/sourcea3a79275ea42940b3c319c7c15cab2ae75f15109 completed placement/CTS in537.19s, returncode0, all protected inputs unchanged. Actual20SRAMs and141520instances, CTS ODB SHAfc4400278ce81212ca7b30bf2d02aa7356f23e512336020e201e98839cd9beab, state run/27-openroad-cts/state_out.json. This means physical stage completion only. functional_boot_accepted=false, accepted=false, final_timing_complete=false remain explicit.

**Timing is severe and requires diagnosis/repair:** fast setup WNS-71.779ns,12777hold violations WNS-0.601382ns,14250setup violations; slow setup WNS approximately-207199132ns andtypical-127533037ns (extreme extrapolated/delay values, cause NOT established). Clockskew metrics around310-320ns;11479maxslew violations/338maxcap worst counts. These are placement-estimate CTS reports, NOT extracted routed timing. Do not compare them as an apples-to-apples regression against the heavily repaired/routed oldRTL baseline. Do not route or adopt this candidate blindly, and do not hide enormous values. Next chip action: read actual per-corner CTS worstpaths/clock reports from saved native archive on hosted runner, identify extreme load/slew/cell/table/constraint cause, then coherent postCTS electrical and timing repair with original constraints. Existing scripts/cloud_replay_crc_postcts.py shows the native repair sequence but its oldboot-proven handoff pins cannot be reused for this pendingboot candidate.

Safe14125635095 SHA27634a4fc273d1dfa52c6bb72cbfde2b50e8f7c3bf15fb5ff73cf31dbad72ace. Native14124619734 SHA244a660873d74ae73e2913c1cd96546817d6a3e0474045a662ea566246adaac5 (301323113bytes), cloud only. Full receipt docs/evidence/predecode-chip-cts-20261114.json preserves metrics, protected inputs, commands and all output hashes. Native archive holds prepared/config.json,physical.sdc,run/... including CTS reports andODB. Never download native archive locally. Use slim derived text report job if needed. Exact newnetlist4b17ff9e... is restored separately from mappedsource43618915765; original60hash binding still valid.

Fresh PHY metal/MIM RC43623877135/sourceca7922a41bb122ec714a23cd2ca5b7ea63d197ba remains live; native newanchors43623472892 alreadypassed. Icarus boot43620739672 andoriginal oldRTLroutes43614100441/43610680141 remain separate pending qualifications. Fullproductiongoal active/incomplete.

## 2026-11-14 — fresh RC current handle after exact geometry pin correction

Follow **43623877135**, sourceca7922a41bb122ec714a23cd2ca5b7ea63d197ba, branchcodex/cdr650-paired-fresh-metal-rc; confirmed in_progress. Previous43623675068/source81c9464b91d9d5b618b604104e97c06212adb3b6 is terminal failure, NOT live. All current source acquisition/anchor hashes/native integer MIM dimensions passed, then support.generate() correctly rejected a stale hardcoded baseline GDS SHA c3351820... before actual native R/C. Replaced that sole source-identity constant with exact newly DRC/LVS-qualified candidate285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514 and rebound source manifest. No geometry, numerical method, circuit assumption, threshold or acceptance check was relaxed. New explicit dispatch uses approved_source=ca7922a41bb122ec714a23cd2ca5b7ea63d197ba. Do not restart a live run.

First failed safe14124782932/7408ea38f69ed1d24d56d716ed0598f17d6004f609bd55064843d2b06442717a; native14125425563/7b4c90bc5b25c23527834e49d32f323ca5f1f96bb3a854f2c442ba1cd2a75efe cloud only. New expected safe paired650-metal-rc-derived-43623877135/native paired650-metal-rc-native-43623877135. Two native orders and13wire+9MIM faults each remain required, followed by new gate-poly/MIM composition and unchanged electrical tests; no new R/C result yet.

Previous actual paired650 DRC/LVS and terminal-anchor successes remain valid for their exact hashes. Fullproductiongoal active, no local files.

## 2026-11-14 — paired650 all terminal anchors PASSED; fresh MIM-aware RC live

Run43623472892/source54a4766e9256d2cd0a3f93f5441ca5d1c238c7ce PASSED actual current650 device-location, terminal anchor, gate-poly-group, contact and dedup workers. 2046terminals,1428distinct physical anchors,200actual gate contacts across50groups, separate intrinsic MOS gates preserved. All source material reread from actual serialized new GDS and L2N; current native-owner probes passed. Ten original actual binding corruptions rejected (lost terminal, parameter, duplicate instance, wrong native owner, missing anchor/group/contact, duplicate contact, gate ideal collapse, wrong group association).

Physical macro relocation proved explicitly: original40 topinstances ->16macros with24topvias flattened into conserved parent geometry; exact declared transforms, full child material and local annotations checked. Wrong translation and missing macro controls rejected. Full old hierarchy equality is correctly FALSE; per-primitive pin identity and explicit relocation proof replace that obsolete invariant. Old qualified primitive local pin drawings hash-bound and checked against unchanged intrinsic geometry, never old global coordinates/native IDs. Firstrun43623331177/sourcee4c109726edb2da17e4b436c21a128072edca351 failed after successful relocation checks due missing FLAGS import; fixed one import and reboundsourcehash before newrun. No geometry or acceptance gate change.

Safe14124672969 SHAa3e3b980b8d03f8ef38d854b414649a40496711d532f4824957184fc9082c199. Native14124873759 SHA0bf3857c86266eb8628545faea5b3a2794b80abaa6f06a09d7c8d1f9c785f422, cloud only. Receipt docs/evidence/cdr650-paired-terminal-anchors-20261114.json. Native archive root contains selected/ and view/; all actual new anchor files under view/wire/. Corresponding fresh flat identity remains graph-safe14125295448/d8376d4009da54acbe52569fd119add9f07f4f13d8120ebc65bd5fa193c899ac; its LVSDB digest must match restored selected/physical/lvs_flat/result.lvsdb.

**LIVE actual fresh metal/MIM RC:** [43623675068](https://github.com/Melihakbulut221/nssoc/actions/runs/43623675068), source81c9464b91d9d5b618b604104e97c06212adb3b6, branchcodex/cdr650-paired-fresh-metal-rc. Source-controls passed, native-metal-rc running. Adapted original1b40bf2db3844d6281c467022b248a2871ced6df factory, unchanged frozen numerical methods, original qualified Magic runtime, explicit seven MIM devices, two native capacitance enumeration orders,13raw wire faults +9MIM identity faults EACH. Only acquisition/source path/producer binding changed to new paired650 archive. Restores original absolute paired-terminal-anchors paths so anchor input hashes remain checked. New cfg paired_view replaces obsolete view producer spec; all materialized source files rehashed before/after. MIM geometry helper now explicitly targets paired-terminal-anchors/native/view. No old R/C used or scaled. No relaxed electrical gates.

Safe expected paired650-metal-rc-derived-43623675068; native paired650-metal-rc-native-43623675068, all native stays cloud. Status still requires full composition, gate-poly RC, and unchanged loaded electrical tests even if metal stage passes. Do not call this qualified full RF PEX. Preserve original component113/net114/650device/2046terminal/1428anchor/200contact counts.

Newchip placement43622573415, Icarus boot43620739672, exactjumper route43614100441 andbuf4route43610680141 remain their original live handles. No duplicates or local files. Manufacturing objective remains active/incomplete.

## 2026-11-14 — new paired650 native identities and fresh conductor graph PASSED

Run43622884786/sourcee0a87989915cb7d65a20176de33649859f013393 completed successfully. New GDS285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514 independently binds650 devices,2046 terminals,25 ports against original schematic identities;15 actual identity corruptions rejected for EACH deep/flat readback. Fresh complete metal/via graph has113 conductor components and114 native electrical nets; every component's material belongs wholly to one native LVS net, no native metal-net split or union-by-label shortcut. This is NOT extracted R/C yet.

Safe14125295448/d8376d4009da54acbe52569fd119add9f07f4f13d8120ebc65bd5fa193c899ac. Native14125325353/b29785a0ad74a923e6c250f564a3f57da8d876e58992d57b5800e18ab4176b47 (215800722bytes), cloud only; contains selected exact new layout/LVS databases and native/view/wire/native05/wires.gds,wires.l2n,result.json. Original physical archive also preserved inside. Full graph/control receipt docs/evidence/cdr650-paired-wire-graph-20261114.json.

Next actual extraction work: qualify primitive pin provenance after declared macro translation and top-via flattening, run locate01.py/current650 gate anchors/dedup, validate all1428 physical anchors including200 gate contacts with current native xrefs. Oldsource_pins() full hierarchy/annotation equality cannot be reused unchanged because actualmacro transforms/public pins moved and24top via instances were flattened into conserved overlay geometry. Preserve per-primitive material/pin identity; verify explicit baseline->candidate transformations and use current native IDs/coordinates. Then run fresh metalRC/poly/MIM composition and unchanged electrical gates. No oldRC or oldanchors accepted as newextraction.

Newmainchipplacement43622573415/sourcea3a79275ea42940b3c319c7c15cab2ae75f15109 remains live at native floorplan/placement/CTS. Boot43620739672 and originalroutes43614100441/43610680141 remain separate pending qualifications. Fullproductiongoal active/incomplete.

## 2026-11-14 — new paired650 layout PASSED native DRC/LVS; fresh graph and new chip placement live

**Completed physical qualification:** [43622190993](https://github.com/Melihakbulut221/nssoc/actions/runs/43622190993), source8274b540b6223e6a9bd2c7aa7b3d2c5046b09a7f. Actual candidate GDS285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514 (1627742bytes) passed560-category DRC with0markers, deep+flat LVS with650devices each (124HBT,200MOS,98rppd,7MIM,221tap), and all13 actual fault cases rejected. Frozen checker SHA30c4586b... unchanged. Complete physical report SHA7fec2657806b39de1cf96815f469787aa66934e7b7f004755cbbbb071ac654bf. NewLEF SHA02f6b1ad6a9f3b4f52281e5330f9f22d95fe71c524d90d3da4973316e5a55741; independent reference21d730545b983930eacf733ba77a7593df52e253987991724de9594fe136bbfb unchanged. Actual25 pin boxes regenerated; footprint2316.6x4715.48um. Native lifecycle clean, no surviving child processes.

Safe14125115411 SHA0d9b23019c89ab327ef3a296437a1bd61c180491954d09274c225814a69dc674. Native14124657803 SHA bf981a5887f0fd69167f41e1ce6b8065662202d1fe9f8b2de201df210eb408ec (217602539bytes) contains full new physical outputs/caches at hw/soc/out/cloud-cdr-wire-shortcuts-physical/...; cloud only. DeepLVSDB a660b051307cf53822a5d84be53c3d73bce70448d6fafbf8e5b4f3ad8b4abbca; flat ec58d3df5a7a815b1b992d1c4f8fe7f2e99dc3436b138a18e99ed76f1f0f0a16. Full receipt docs/evidence/cdr650-paired-native-physical-20261114.json. This is the CDR block's exact physical pass, NOT serialPHY completion, newRC/electrical acceptance or main-chip signoff.

**LIVE fresh topology extraction:** [43622884786](https://github.com/Melihakbulut221/nssoc/actions/runs/43622884786), sourcee0a87989915cb7d65a20176de33649859f013393, branchcodex/cdr650-paired-wire-graph. Authenticates new physical run/native archive and every selected layout/LVSDB/decklog input; executes original independent650-device/2046-terminal/25-port native identity comparisons and fault controls. Then runs original exact geometric metal/via graph extraction with only declared650 census adaptation. Requires every component wholly owned by one actual native net, no split metal networks, complete terminal coverage. No old geometry/RC reused. Safe paired650-wire-derived-RUN, native paired650-wire-native-RUN. This extracts fresh wire graph only; source pin/terminal anchors and actual R/C still follow. Original wire pipeline source f3aece4ae3b048df220cb51277d74fcd026940ed in scripts/cdr_mos650_wires.py requires hierarchy/annotations identity with old pin geometry, which must be adapted explicitly to relocated bands and flattened top-level vias, not simply bypassed. Use native xref identities for new device/terminal ownership; do not carry old native IDs or old coordinates blindly.

**LIVE full-chip new predecode placement/CTS:** [43622573415](https://github.com/Melihakbulut221/nssoc/actions/runs/43622573415), sourcea3a79275ea42940b3c319c7c15cab2ae75f15109, branchcodex/predecode-chip-placement. Exact60-file mappedbuild43618915765 restored through tested source-binding helper; netlist4b17ff9e9dac2452c60fc3a1e1860e775cdce2015589bb020b7530ab83314997 andmappedJSON532a165624564dcc0f1b1bd7904e697b244afcdadde7d289b2bd9fb07e01d59a. New script cloud_predecode_chip_placement.py uses existing20SRAM/four-clock floorplan and original constraint/CTS flow. This is explicitly NON-ADOPTED physical candidate work while boot43620739672 remains pending, not the old boot-proven handoff and not inherited acceptance. Requires separate successful newboot before adoption. Safe predecode-chip-placement-derived-RUN; native predecode-chip-placement-native-RUN. Latest poll has entered actual native floorplan/placement/CTS, runtime preparation and source restoration passed. Future need newroute/RCX/LVS, no oldODB reuse.

Original boot43620739672 and route43614100441/43610680141 remain their original handles. Manufacturing objective remains active/incomplete. No local native/source files.

## 2026-11-14 — paired650 full native physical qualification LIVE

Run [43622190993](https://github.com/Melihakbulut221/nssoc/actions/runs/43622190993), source `8274b540b6223e6a9bd2c7aa7b3d2c5046b09a7f`, branch `codex/cdr650-paired-native-physical`. Source-controls job132530121821 PASSED; native-physical132530193052 started. Follow this exact handle. No native physical verdict yet.

The experiment adapts the earlier physical factory from b3d9d1d284b1e8464d5359e7e21991aef21a787c without changing the frozen native checker SHA30c4586b86167ad775af14b5568152820a802037150bdfd282e7ba0843a1555f,560 DRC categories, deep+flat650-device LVS,13 fault controls, qualified launcher/supervisor/resource limits. All source closure hashes rebound. The original baseline_candidate() still authenticates the complete old650 generation archive and independently rebuilds the original reference; new candidate() additionally authenticates run43621748603/source0d90e18e09678eb1733123d97f41942dace720b3 and both native/proof artifact digests. source.gds must byte-match the independently restored650 baseline. Candidate hash285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514. Original650 schematic copied unchanged and hash-checked.

prepare_layout() now reads actual25 TopMetal2 pin boxes/labels from the serialized new GDS, checks all names and proof coordinates, regenerates LEF pins AND obstructions with original use/direction, and supplies moved coordinates to frozen checker metadata/fault generation. Original old LEF is not used as candidate coordinates. Candidate admission and final native record are bound to scripts/cdr650-paired-physical-input.json. No previous physical verdict transferred. Experiment workflow is NOT merged to timing/combined; only promote tested controller when appropriate.

Outputs: paired650-physical-derived-43622190993 contains safe derived reports; paired650-physical-native-43622190993 contains all native output/caches, cloud only. Earlier controls artifact includes schematic sources; do not download it locally. The new workflow uses artifacts rather than old release-reservation/publish steps; source/runtime controls, native verdicts, diagnostic preservation remain intact. It does not perform new RC or electrical transient verification; these follow only on exact physical pass.

Verified live at dispatch followup: boot43620739672 Icarus (approximately16min), route43614100441 exact jumpers (89min), route43610680141 buf4 (127min). Original handles unchanged. Supplemental Verilator incompatibility is already diagnosed and not waived. Full-chip timing, full serial PHY and manufacturing readiness remain open. All native work stays on hosted runners; no local source/CAD files.

## 2026-11-14 — actual paired CDR layout generated; native qualification is next

**New physical candidate:** run [43621748603](https://github.com/Melihakbulut221/nssoc/actions/runs/43621748603), source `0d90e18e09678eb1733123d97f41942dace720b3`, branch `codex/cdr650-paired-band-layout`. Generation and serialized geometry checks passed. Candidate GDS SHA256 `285760f3930a1cc142b45a3c43866202f1ea4694f468fb1603f286cb546cd514`; source `c335182048dc1696821ab875fb34447e5b5a9ba0f1a24d5d16d572680906c16c`. Preserves 16 primitive macro hierarchies and all later local overlays, including gate contacts; rebuilds 37 actual global TM1 trunks. Every old/new via incidence checked; no new same-metal contacts or overlapping distinct trunks permitted. Removing a real trunk or native contacts is rejected by serialized-geometry controls. Public pins move with bands. This is **NOT native LVS/DRC, fresh RC, electrical acceptance, full PHY or chip integration**.

Safe artifact14124466665 SHA726986be12be609ba674d4622b6011b30d3392a2ff70e6e69578a552984705ce. Native14124521775 SHA84bbb918af34605e7c6f14598fc68e7d5bb811a3d32d6c22bb294c0a51623ac6 contains candidate.gds/source.gds, cloud only. Generator promoted byte-identically as scripts/generate_cdr650_paired_bands.py (tested experiment path scripts/audit_cdr_native_cap_records.py); inputs metal.tgz releaseasset707281704/09c2185efebbdb7e60c0457d62c175d98d7bffca35e60bfe7c3f179f62ebbfb6 and geometry.tgz asset706980601/d8bd9f7463e7941e4f0319c5d01c47f217366cd213d83c68b9f6fdc6d256bc36. No experimental workflow merged. Receipt docs/evidence/cdr650-paired-layout-20261114.json. Total trunk length39385.2->39493.2um; targeted shortening is not a total capacitance/timing claim.

Preceding intersection audit43621581186/sourcefd516803e5e742ca87a4e6a51fd08ddeec1c61f7 safe14124267180/78ed5dc774b2a09bda0b65dbf8af673b5f09c510ecea5b018e043d457d64ed9b identified all37trunks with actual TopVia2 contacts and zero remaining band-crossing polygons. The prior four crossings were late shortcuts atx953..961.2um, outside overly conservative earlier953.6um filter but inside realmacro boundary993.6um. No crossings were sliced or waived.

**Next physical work:** validate this exact GDS against independent unchanged650 reference using frozen full560-category DRC/deep+flat LVS/13 fault controls, then new RC and unchanged electrical gates. Existing factory source `b3d9d1d284b1e8464d5359e7e21991aef21a787c`, scripts/cloud_cdr_wire_shortcuts_physical.py, derives exactchecker SHA30c4586b86167ad775af14b5568152820a802037150bdfd282e7ba0843a1555f via checker_text(). Original factory is branch/source/asset pinned and CANNOT simply run unchanged on newcandidate. Prepare new explicit source binding and regenerate LEF/metadata from actual25moved pin geometries; do not keep old pin coordinates. Source physical reference schematic SHA21d730545b983930eacf733ba77a7593df52e253987991724de9594fe136bbfb in original650 geometry lineage; verify actual archive bytes before use. Factory uses pinned AppImage d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466 and unchanged native checks. Do not transfer previous physical pass.

**Native cell diagnosis:** run43621515746/source9a80c7aad2f033f3b8b3a25527c08f7d334f1f21 completed diagnostic collection. Safe14123229761/64e69eb08a195f3782e573f84623554383e3ac239304257c29b2b7dac8e56f1f. Untouched IHP model passes Icarus; Verilator seed1 fails asynchronous reset reassertion at66ns, seed29 positive-edge capture at55ns; compiler reports unsupported specify constructs. Diagnostic success is NOT Verilator compatibility. Strict compatibility gate retained, no altered models or bypass. Actual chip Icarus boot43620739672 continues; native-cell diagnostic script and receipt retained. Existing routes43614100441/43610680141 also continue. Joint traffic43617762343 already passed and promoted in dcba4e028997c7ba7426bb071b3a2cc9998690d6. All native work stays cloud; manufacturing goal active/incomplete.

## 2026-11-14 — joint predecode traffic PASSED; native boot and routes remain live

Verified run43617762343/source df8c47d62027a3b5fd378f459ef8cb7208b9b712: inferred and vendor FIFO variants each PASS,2 tests/0failed/0skipped, actual SRAM instances0/16, asynchronous PCIe, source/runtime hashes unchanged. Actual Ibex + PCIe packets + GMII traffic and FIFO POR MBIST; NOT serial PHY, full mapped chip boot, layout or timing. Safe14122964087 SHA43e94a25337983a1b542e329a840a681afab3fcc33125f77e42af39570b2b868. Only tested checker define whitelist promoted; no experiment workflow. Complete reports docs/evidence/predecode-joint-traffic-20261114.json.

Boot43620739672 Icarus remains live. Supplemental Verilator FAILED native-cell compatibility before whole-chip compile (both seeds1/29 failed, untouched IHP library SHA28343754a828972d614c15b7db27892e92a8c16e49fc06ed69d858a659942ed4). Safe14123713097/ab629997a3df10119605ed18a08aefadd1fdd90f6e637314df10aac56f56f419. Do not waive compatibility or call this a chip functional failure/pass. Existing diagnostic collection omitted nested cell logs; next focused cloud probe must preserve these. Icarus continues unchanged. Routes43614100441/43610680141 remain live; no duplicates.

Band feasibility43620938275/source6f4e11caa345f0d4e064c68ae0f2dfb0d8b298e9 completed. Safe14123109182/1085d139c5ec3aa0f472059bb6820614085bad42bc96e6ebc54d978963c47346. After 33 conservatively identified TM1 trunks, four remaining TM1 crossings at x953..961.2um block a naive whole-band move. These are left of macro boundary993.6um, but geometry alone does not establish electrical ownership; inspect their actual via/metal intersections before rebuilding. Full receipt docs/evidence/cdr-current-band-feasibility-20261114.json. No new geometry or timing acceptance; full manufacturing goal remains incomplete.

## 2026-11-14 — fresh predecode main-chip synthesis PASSED; mapped boot live

Run43618915765/sourceb900da8cc1d57b8b2ce80416b6742c36239afd63 PASSED fresh firmware RTL preparation, strict native preparation tests, synthesis, and actual mapped-select audit. 114952cells,26 realclocked selection bits(10write_group+16write_low),20SRAMmacros(16Ethernet256x16 +4system2048x64). Candidate SHA4b17ff9e9dac2452c60fc3a1e1860e775cdce2015589bb020b7530ab83314997; mappedJSON532a165624564dcc0f1b1bd7904e697b244afcdadde7d289b2bd9fb07e01d59a; firmwareab7440619ca719358e6598b0cf291a268c8ccf13357b50ef3a89cbe583e71801. Safe14123429089/f11becfb6e2ab79646a58d29285409fc1dc1c6d30acf1501836e5a424dc3f695; native14123718652/c6848d124c65c6aae6af7ee70deb7b516d0a06e91886a0d4945ea12ce4645615 (build.tgz,60hash-bound files). Native stayscloud. Tested syn_soc_top.sh/sim_soc.sh opt-in define forwarding plus prepare_predecode_mainchip.sh and check_predecode_mainchip_mapping.py integrated byte-identically; experimentalworkflow excluded. Defaultoff behaviorunchanged. Receipt docs/evidence/predecode-mainchip-mapping-20261114.json.

LIVE gateboot43620739672/source98281a5792ac15ed28f5ecd001b0cff462e95f99, codex/predecode-chip-native-boot. Restores exact60sourcefiles/hash, samepinnedPDK and OSS2026-08-04. Two separate jobs: nativeIcarus4state and supplementalVerilator2randomseeds. Full20SRAM POR MBIST plus28firmwarechecks, asyncpacketidle profile,2Mcycles,19000s simulatorbound/355minhostedjob. Fourstate may hit known hostedlimit; don't waive gates or callVerilator a4state substitute. No remapping or bootprooftransfer. Safes predecode-chip-boot-iverilog-43620739672 and predecode-chip-boot-verilator-43620739672; inspect terminal verdicts and sourceunchanged before claimingboot. Fulljointtraffic43617762343 still pending separately. Oldroutes43614100441/43610680141 stilloriginaloldRTL.

CDR completegraph planning43620299436/dbed4fa2675efea02e15f17d732822e29a8e049b passed after first43620183298 failed ONLYrailidentitylookup (fixed to explicitdetail.public_port, not guessedlabels). Safe14123208037/2c40ce1637f98cd27103d6bae831299ab79ac4b0e91188053bfb4eec4f1ae782. Unconstrainedweightedplan REJECTED for adoption: shortensdata1050.52um butlengthensCdivider->buffer inputs1355.15um. NoGDSmodified.

Pairedplan43620553452/source0e2361ad89a4afd8593dd608387efde21a11624a PASSED40320exhaustive backendunitpermutations. Safe14122963884/7b6b52f81bf4b08aea51d4b5b6658a07df3afc52987af252432c7c6ae8a171e4. All1428anchorsassigned:1403to16currentmacros,25explicitpublicports; exact3supplycomponents. Fixesfirst6frontendtransforms, externalpins; preservesdivider/bufferpairs(6,7),(9,10), protectednets66/67/75/76 HPWLnotincreased. Candidateorder[3,0,1,2,4,5,8,6,7,12,11,9,10,13,14,15]. DataHPWL2044.62->994.10um and1804.62->754.10um; selectors+35.6um; otherupstream/outputnets stillincrease(up to799.89um). Weightedproxy118064.513->113320.583. NOTtiming/routeacceptance; fullnetdeltas retained docs/evidence/cdr-paired-placement-plan-20261114.json.

LIVE physicalband feasibility 43620938275 branchcodex/cdr-current-band-feasibility. Uses exactcurrent650GDS; subtracts immutablechildgeometry and classifies known-width TM1 rectanglesleftofmacros as candidateverticaltrunks; reports everyremainingband-crossingconductor before movinganything. This decideswhether old scripts/generate_cdr_retime_band_reorder.py strategy canpreservelateroverlays. Thatoldhelper is for484devices and mustNOTrun unchanged; it rebuildstrunksandmovespublicpins, unlike currentplanning'sfixedpins. Current650 includes150top-levelcontacts andmanylocalmetal/viaoverlays; allmustbeconserved. Sourcegenerationtrace nextusecomplete scripts git subtree, not truncatedrootrecursive/contents1000listing. FullgoalACTIVE; no native/localassets.

## 2026-11-14 — current650 macro boundaries recovered for actual floorplan repair

Macro audit43619786675/sourceae37a42977e99dc57ef648736b89f1893207c0c0 PASSED; safe14123722696 SHAa570289fa65af522ad286ce4e11f03a415f4ef076ee61c3944a70c0d1b8d202c. Exact GDS top has40directinstances:16functional macros plus24via stacks (not40functionalblocks). All first16 macros X=993.6um in a single long vertical stack. A data buffer ordinal7 Y2286.41um, Cdata ordinal10 Y3062.30um, selector0ordinal11 Y3336.93um, XOR0ordinal12 Y3611.56um, selector1ordinal13 Y3916.19um, XOR1ordinal14 Y4190.82um. Data macro406x194.63um, selector466x194.63um, XOR826x224.63um. Macros themselves untouched; source devices remain actual650. Top route shapes and24via stacks include later physical changes; merely changing instance transforms would break connections and is NOT an implementation. Native pin labels on direct children absent, so use actual terminal anchors/net ownership to rebuild interconnect, not guessed friendly labels. Receipt docs/evidence/cdr-current-macro-boundaries-20261114.json.

Current650 generation source from physical-candidate manifest: run41709759119/source087721d42112ed108543d2da053ee6d0e2f20a9c, release433163953, tagcloud-results-41709759119-1-cdr-mos650-gate-metallization. Verification41710162510/sourceb3d9d1d284b1e8464d5359e7e21991aef21a787c. This geometry has200MOS/124HBT/98rppd/7MIM/221tap, later gate-metal straps and source/drain via relocations. Old394/484 generators cannot replace it wholesale. Next actual design work: derive complete macro terminal/net graph from source anchors/L2N, compact data/select/XOR placement while accounting for upstream sampler paths, rebuild top routing, then exact unchanged circuit LVS/DRC/newRC/electrical gates. Currentmillimeterdistance evidence changes direction away from blind transistor sizing sweeps. No new PHY native job currently live after these completed audits.

Other original live handles unchanged at latest verifiedpoll:43618915765 firmware RTLboot/full20SRAMsynthesis,43617762343 actualjointtraffic/MBIST,43614100441 exactjumperDRT,43610680141buf4DRT. No localfiles or duplicatejobs. Productiongoalactive/incomplete.

## 2026-11-14 — actual CDR placement spans measured; compact macro audit live

Physical-span audit43619538391/source693c1d9c878ba3b9bce355c30e6e04c01f11169c PASSED. Safe14123666468 SHA6d822df59c2da0152245a473f9ec10af16701057682466a33b57d5ac5c54a0d9. Exact current650 GDS c3351820... read with pinnedKLayout0.30.4.post1: DBU0.001um, top2316.6x4715.48um. Data driver->six XOR base Manhattan LOWER BOUNDS adp1474.62–1804.62um/adn1594.62–2044.62um; commonverticalspan1322.77um. Selector driver->two bases605.95–725.95um. No physical change yet; not routed length or proven timing causality. Receipt docs/evidence/cdr-buffer-physical-spans-20261114.json. This justifies compact macro placement/rerouting investigation; adding parallel wires alone leaves oldcapacitance. Preserve upstream sampler/divider loading and all device/net identities, then fullnativeDRC/LVS and regeneratedRC/frozen electrical gates.

LIVE macro-boundary audit 43619786675/sourceae37a42977e99dc57ef648736b89f1893207c0c0 branchcodex/cdr-compact-macro-boundaries. Same exactnativeGDS/anchors; adds topinstance transforms/bboxes/pinlabels, no geometrychanges. Safe cdr-native-cap-records-43619786675. Follow originalhandle, do not rerun prior span audit. Source generator reconnaissance: main scripts/cdr_retimed_*_parent_plan.py describe OLD394/484device hierarchical sources; do NOT treat as current650. Currentphysicalrun41710162510/sourceb3d9d1d284b1e8464d5359e7e21991aef21a787c/codex/cdr-mos650-gate-metal-physical has exact650 reference and physicalchecker, scripts/cdr-wire-physical-candidate.json identifies its generator. To rebuild, use currentGDS hierarchy and that current650 generation provenance; oldprimitivegenerators alone would discardlaterchanges. RecursiveGit tree maytruncate (huge docs); use contents directory endpoints for focusedsource discovery.

Verified live now: newmainchipsource43618915765 (firmware RTL boot/full synthesis), joint43617762343 (traffic/POR MBIST), exactjumpers43614100441 andbuf4route43610680141. Nochanges/restarts to ongoingjobs. Fullproductiongoalactive; nothing native written locally.

## 2026-11-14 — native capacitor provenance confirmed; source build progressing

Native capacitor record audit43619048065/source5e5ae228678377ff602befb779077c6a52946ee4 PASSED. Safe14123805673 SHA75d60093cff9cf9f5e0f8dc64f34441eb31db8af1336eb9a36419b6e076622ac. Exact metalRC archive707281704/09c2185e... read only on runner. Original Magic pump_wires.res.ext contains T382_rppd_2.n0 cap131020.2109375aF and T383_rppd_2.n0 cap146790.359375aF, matching composed C8237/C8243; not newly introduced by nx1 trial. Original .ext identifies T382 resistor terminal, Q275 collector and six XOR bases on same conductor; T383 similarly Q273 plus six bases. Res.ext preserves distributed branches (e.g T382.n0->Q275_C27.453ohm; T382.n1->n053.3457ohm; T382.n0->T38240.4117ohm). This supports investigating actual routed topology/load, but is NOT qualified high-frequency PEX or proof the physical capacitance model is correct. Do not scale C or alter valid frozen checks. New receipt docs/evidence/cdr-native-cap-records-20261114.json retains bounded actual native records and four terminal anchors. Next trace full same-conductor geometry/driver-to-load distances and consider a compact physical buffer/XOR arrangement with fresh RC, unchanged LVS/DRC gates.

Fresh predecode main-chip build43618915765 has passed source/tool preparation and is running Fresh firmware RTL boot and complete chip synthesis with twenty SRAMs. Joint43617762343 still actual concurrent traffic/FIFO POR MBIST. Source modifications remain experiment-only until native checks pass. Existing exactjumper and buf4 DRTs still run at their original handles. Snapshot: {"43618915765": {"status": "in_progress", "conclusion": null, "head_sha": "b900da8cc1d57b8b2ce80416b6742c36239afd63"}, "43617762343": {"status": "in_progress", "conclusion": null, "head_sha": "df8c47d62027a3b5fd378f459ef8cb7208b9b712"}, "43614100441": {"status": "in_progress", "conclusion": null, "head_sha": "b83bc3a3f204bf9a2833c89fd632ae9308a58b56"}, "43610680141": {"status": "in_progress", "conclusion": null, "head_sha": "d42836ac2566de769473973bb15625e27f788f8d"}}. No duplicate runs or local native files. Full goal remains active/incomplete.

## 2026-11-14 — measured predecode write-path improvement; fresh main-chip synthesis live

Integration ff1e70cc1faf92b4c77837d71be814139b55104a records exact tested placement/path helpers and receipts. Placement43616617171/source df75847d635b3c53b895ea3b1c62c3f20d83f091 plus saved-ODB write-path readback43617173813/source8ca0209c777e4e84405b3b7be172b8c3b7755f9e: same constraints/placement-estimate RC, slow targeted write setup after electrical repair improves -0.883149ns -> +0.131997ns; targeted fast hold +0.269111 -> +0.182012ns. ALL-path slow setup remains -2.344590ns and fast hold -0.059318ns. Isolated block, no CTS/route/signoff. Never claim full-chip timing closure. Safe placement14121799888/0c05fde1f4ec73ff467ba17781565fe950d3163f826f246a697a2d7b6ef6c16c; native14122337899/d55d22b5617fb2d693985c1cf2dec9616dbbb1f50a0f555ee9d640844eca1611 cloud only; safe readback14122254324/ef8d0590ee9ea3a3b3ac6fcb7b3ae49ede5e56c13bed793b046be827a6c78611. See docs/evidence/replay-write-predecode-placement-20261114.json.

LIVE joint CPU/PCIe/GMII test43617762343/source df8c47d62027a3b5fd378f459ef8cb7208b9b712, branch codex/replay-write-predecode-joint: inferred then vendor16FIFO SRAMs, asynchronous PCIe, all C10 peripheral defines plus WRITE_PREDECODE. Require each two tests/no skip/errors and exact 0/16 actual SRAM instances. Pending; do not merge whitelist change before results. Safe replay-predecode-joint-43617762343; native input archive stays cloud.

LIVE fresh full-chip source build43618915765/source b900da8cc1d57b8b2ce80416b6742c36239afd63, branch codex/predecode-mainchip-source. Missing WRITE_PREDECODE forwarding in syn_soc_top.sh/sim_soc.sh patched ONLY on experiment branch; one addition to existing strict0/1 define loops, default unchanged. New prepare_predecode_mainchip.sh preserves existing MBIST boot preparation through firmware RTL boot and synthesis, deliberately stops before lengthy mapped boot; check_predecode_mainchip_mapping.py requires actual26 registered select bits(10group+16low),20SRAMs incl16Ethernet and exact RTL SHA374722073fc503a85970748d79daad12fd360fb1edeb58b76250ddf3b967eb35. C10 peripheral flags, execute/PMP stage, RF CHKDEFER/PREDECODE, MEM_RDREG2, prefixadder, full interface. This is a NEW netlist, not old boot/physical evidence. Next requires actual native gate boot/proofs then coherent placement/CTS/route/RCX/LVS. Original full4state MEM_RDREG2 MBIST boot may exceed hosted6h; do not omit MBIST or claim a2state substitute proves4state. Keep preparation native artifact predecode-mainchip-source-native-43618915765; safe mapping summary predecode-mainchip-mapping-43618915765. Do NOT merge experimental workflow replacement.

PHY correction, superseding earlier window question: direct passive-divider-only input binding43617454925/source a7d15d20d2606b605146daf69d54a9e3d3efdc22 proves BOTH s0/s1 XOR selectors derive from RETIMED D, not raw B. D retains expected previous-bit sign at .6/.75/.9UI. No basis to change frozen checker windows/expected bits. Safe14121769540/8bc073a79e1a3dc0e8c18345bb2c0573c19af682a55fe02ec19716282de8c06f. Clock/load audit43616487827/source9935e4a991472d2bdcfcd87eb84a7f7fa795760f traced32physical clock bases, expanded50 passive subcircuits:18476C/28984wireR. Incident explicitC adp0.566521pF/adn0.595331pF/s0p0.234530pF, includes coupling; NOT grounded effective load/qualified RFPEX. Dominant C8237=131.0202fF to wire_cref, C8243=146.7904fF to wire_cref, differential C238=107.741fF. See docs/evidence/cdr-buffer-loading-and-retimed-selector-20261114.json. Nx1 trial still REJECTED unchanged.

Read-only geometry provenance43618600239/source b49e1d61d2901e513026f8036c3ca0bb670f6c18 PASSED; safe14123580366/4f7cfe1084a89aadbf769ced05d75dceb40c0f524c8430d4c7a5e125452dc97f. Exact GDS is c335182048dc1696821ab875fb34447e5b5a9ba0f1a24d5d16d572680906c16c (legacy filename nssoc_cdr_pd500_resistor_v59.gds, actual650 devices). Source metalRC producer41728568165/1b40bf2db3844d6281c467022b248a2871ced6df, asset707281704 SHA09c2185efebbdb7e60c0457d62c175d98d7bffca35e60bfe7c3f179f62ebbfb6. Native wires.spice637a79590e87a3e11866ec822afb6096c3dc7d626d23acd0235389af8bfd0e3c. LIVE native capacitor record audit 43619048065/source5e5ae228678377ff602befb779077c6a52946ee4 branch codex/cdr-native-cap-records; restores metal archive only on hosted runner, traces T382/T383/T397/T398 resistor terminals into Magic .ext/anchors. Safe cdr-native-cap-records-43619048065. Next determine actual geometry/model behind dominant caps, then physical layout/driver change and regeneratedRC. Parameter-only previous what-ifs did not regenerate layout; do not arbitrarily scale C.

Existing original route handles unchanged and live: exact-jumper DRT43614100441/sourceb83bc3a3f204bf9a2833c89fd632ae9308a58b56; buf4reroute43610680141/sourced42836ac2566de769473973bb15625e27f788f8d. No duplicate/restart. Both oldRTL, neither tests newpredecode. Follow final antenna/DRC then fresh3cornerSTA; older LVS cannot transfer. All native work/cloud artifacts remain on GitHub; local workspace untouched. Full production goal ACTIVE and incomplete.

## 2026-11-14 — tested predecode integrated; nx1 PHY rejected and diagnosed

Integration313e85443f23d48b85d24b2bf10f3afccaf32efb contains byte-identical tested predecode RTL, co-simulation script/bench, source/SAT guards, actual full-RTL proof helper (physical read/reset options), and mapping helper. SOC_PCIE_REPLAY_WRITE_PREDECODE is DEFAULT OFF. Experimental workflow NOT merged. No source/native files written locally.

Stronger test43614166666/source5634da5c513f0ef0ed76df2d68155e8f6d760132 PASSED:12x300000cycles with every actual byte enable AND every stored byte compared,6 actual compiled wrong-select faults detected,19 independent tests no skips/errors/failures. Safe14121404592 SHA25dc8ac9590fe4bd175fc7eae9021ca6232c51e691ebd28c717e1a24d4f340b6. Default fullRTL proof43613750120 and physical-option fullRTL proof43614451027 both passed2x22/4x38; physicalsafe14120689834 SHA848b82d0db03127c7c18d7337afa9462d6d64251533753ccf8c34bc4e68437f8. Mapping43615106119/source141207b93d0ba17d402a427a64ca0543db6d8a96 PASSED, safe14121384406 SHAee910e980e9760ddec1d19f5b56b79f0edabb87a35d11176c737a6b6b339ca12. Isolatedcellcounts5900->5898,flops1605->1622; this says NOTHING conclusive about routed delay/hold. Firstmapping43614858489 onlyreporterfailed on two zero-port $scopeinfo records; strict empty-connectivity metadata classification fixed, unknown hardware stillrejected. See docs/replay-write-predecode-20261114.md and receipts. Next: actual physical candidate with newdefine; current running native routes still OLD RTL and cannot measure this newcandidate. Do not blindly apply old route/LVS pass tochangednetlist.

PHY43603972722 now TERMINAL FAILURE: simexit0/7004.41s, X385wrong/717below100mV of765 unchanged versusnx2; Y1wrong/588below, samplerA65/C148/D96below, Bpass. Devicesfailed XD0292/XD0293. This nx1 variant is rejected; don't restart same sweep. Safe14121124635 SHAd497b09e264004bba0c90f78ddb26c5853206a3d4855445549518344691e53dc. Native14121577984 SHAd5e62c25486ba447781a5e4cdc12c00b303e890fb3cb51de1c8cdf77f32d1615 stayscloudonly. divider-whatif artifact containsNPZ, do NOTdownloadlocally.

Read-onlydiagnosis43615016719/source059c7cde174f8b8496909493294ab1156c66f9cd PASSED exactfrozengatereproduction. Safe14122285145 SHAd961cd8d420b0b7c091b1c44b380340f3db7521de3512b02c91a6d792023b557. XD0292/293 unchangednx6 failACTIVEminimumVCE .380924/.379038V vs .4V gate at5.833/5.830ns, NOTcurrentdensity orstartuppeak: alltimeabsVCE .741/.746V,VBE .831/.833V,current/emitter .335/.353mA withinlimits. A sampler sign correct at.75UI transitiongroups, downstreamA interface stilllate/wrong: 01 median+.0561V vs sampler-.2357V;10 median-.0148V vs sampler+.2168V. SmallerXORload didnotrepairthe upstreambuffer. Fullreceipt docs/evidence/cdr-xor1-rejected-20261114.json. Do not relaxfrozengates. Before anotherbias/widthsweep, investigate actual sampler/buffer settling and clock/observation-window alignment; clock generator flips again .5UI after rising, whereas XORchecks use .6/.75/.9UI afterrising. This is a contract-audit QUESTION, not a demonstrated checker bug or permission tochange thresholds/expectedbits. Actualphysicalclock/retiming topology mustresolve it.

Native routing continues at original handles: exactjumper-guides43614100441 (699jumpers/473guide nets, noGRTregeneration; thenfreshRCX/3cornerSTA) and buf4trial43610680141. Snapshot: {"43614100441": {"status": "in_progress", "conclusion": null, "head_sha": "b83bc3a3f204bf9a2833c89fd632ae9308a58b56"}, "43610680141": {"status": "in_progress", "conclusion": null, "head_sha": "d42836ac2566de769473973bb15625e27f788f8d"}}. NeithernewRTLcandidate norfullserialPHY is integrated into those old-RTL physicalruns. Full product goal remainsopen.

## 2026-11-14 — predecode functional qualification passed; exact-jumper DRT live

Full actual replay RTL equivalence PASSED run43613750120/source1d665b21afbe869f46d4befa832c6b76197e5610 using pinned OSS CAD Suite2026-08-04, configurations2x22 and4x38. Earlier43613576934 failed only old Ubuntu Yosys parser on existing sized-cast syntax. Safe14121491806 authenticated, both complete native proof logs/hash/verdicts checked. Simrun43613400964/sourcef95fe2d305c3a64f234376218ccaeaebebe1b284 PASSED:12 all-output co-simulation cases,3.6millioncycles,zero mismatches, plus19 independent cocotb tests across4suites,zero skips/errors/failures. Receipt docs/evidence/replay-write-predecode-functional-20261114.json. RTL remains experiment-only and default-off. This is NOT measured timing closure.

Stronger validation43614166666/source5634da5c513f0ef0ed76df2d68155e8f6d760132 (codex/replay-write-predecode) now additionally compares every actual memory write strobe and every stored byte, including malformed frames; restores baseline source SHAfff6a0d3abb6b3f3a468baef8312b357efb7b591d3733cd92f3dda3345c34c63 by reversing only opt-in changes; compiles actual wrong-low-select mutation and requires specific strobe mismatch in all6seeds. Same candidate RTL SHA374722073fc503a85970748d79daad12fd360fb1edeb58b76250ddf3b967eb35. Do not merge experiment workflow. Preserve source/helper/tests only after controls pass.

PreDRTscreen43612029407 PASSED,699reportedjumpers across iterations,473 changedguide nets outof158097,159934cells/354ports and allinstancegeometry/connectivity unchanged. Safe14120604011/native14120788686 pinned in docs/evidence/pre-drt-jumper-screen-20261114.json. Not finalantennaacceptance.

Continue exactguides via live43614100441/sourceb83bc3a3f204bf9a2833c89fd632ae9308a58b56, branchcodex/exact-jumper-guides-drt. Restore authenticated guides.tgz (SHA69172352eb82e92a998843405c2db5ade521c96654e85fd9ff1fe1785e93b510), renameoldroute tojumper-source, explicitlytake after-jumpers.odb and read_guides after-jumpers.guide in pinnednativeDRT; NO GRTpass. BindexactODB/guide/SDC/netlistSHAs in jumper-input-proof.json. Original16DRTiters/0postDRTrepairloops, no constraint/gate relaxation. DRTthenCheckAntennas and freshRCX/3cornerSTA withallzeroacceptance. Safe route-pre_drt_jumpers-43614100441/routed-sta-pre_drt_jumpers-43614100441; native routed-db-pre_drt_jumpers-43614100441 and pre-drt-jumpers-rcx-native-43614100441 cloudonly.

Other live original jobs: buf4reroute43610680141, PHY43603972722; no restart. Fullgoalstillopen.

## 2026-11-14 — registered replay write predecode candidate in cloud qualification

Existing source/checkpoint e259ba0bb7b255d238aba602fcb405fc10e4bae7 recovered after continuation. No native assets or source checkout written locally. Current diode baseline receipt/six worst paths were successfully committed; do not rerun it.

New candidate run [43613400964](https://github.com/Melihakbulut221/nssoc/actions/runs/43613400964), branch codex/replay-write-predecode, source f95fe2d305c3a64f234376218ccaeaebebe1b284. Only experiment branch changes RTL: default-off SOC_PCIE_REPLAY_WRITE_PREDECODE registers 16 low address choices and ceil(DEPTH*MAX_BYTES/16) qualified high groups. Each of the original five write_valid assignments has its corresponding group assignment immediately following under the define; no duplicated acceptance predicate, no extra pipeline cycle. Same write_data flop; memory update uses high[group] && low[offset]. Reset/link-clear group assignments mirror original write_valid clears. Default build retains original code. Do not assume timing benefit before synthesis/placement/route/RCX/STA.

Qualification includes six-size Boolean factorization SAT with six deliberate wrong-low-address counterexamples; those are NOT full sequential equivalence. It also runs the original six-seed 300000-cycle all-output replay co-simulation twice (predecode alone and with read-ahead/in-bank/reset copies), and four independent cocotb suites (replay/reliable/flow/buffered-flow), rejecting failed/skipped/missing tests. Safe artifact replay-write-predecode-43613400964. First SAT step succeeded; actual co-simulation currently running, all results pending.

Separate full actual-RTL sequential proof [43613576934](https://github.com/Melihakbulut221/nssoc/actions/runs/43613576934), branch codex/replay-write-predecode-formal, source 8a7190db46a6ae0a5e413f293cbc64ac7dd73980. Real default/candidate builds, flattened modules, memory_map, async2sync, equiv_make/simple/induct(seq4), equiv_status -assert, configurations DEPTH2/MAX22 and DEPTH4/MAX38. No blackboxed memory or manually recreated state machine. Each native proof bounded1200s to diagnose non-convergence; timeout is not acceptance. Safe artifact replay-write-predecode-equivalence-43613576934. Formal not yet proven. Preserve exact default source binding and inspect failures before promoting RTL; no experiment workflow merge.

Existing independent jobs unchanged: pre-DRT jumper screen43612029407, buf4 reroute43610680141, PHY43603972722 all still in progress at latest poll. Follow original handles; active job status alone does not prove internal progress. Full goal remains open, including coherent new-route LVS, actual all-corner timing/electrical/antenna closure and full serial PHY integration.

## 2026-11-14 — baseline RCX/STA completed; distributed write-enable bottleneck persists

Run43591198141 nowcompletedFAILURE due actualacceptanceviolations, NOTtoolcrash. NativeRCX+3cornerSTA5m53s successful. SafeSTA14120119428 SHA65a0b3c26fc315e23ee1396d3fda00d3748c1d14d824b8dba5723e0eee8f5b8e (29.4MB). Cloudslice43612497640/source8940e666340465899db4bf9ddd2d1fa5cf641aac PASSED; smallsafe14120707100 containsfullsummary and6completeworstpaths; preferthis overrepeatedlargearchivedownloads. Receipt docs/evidence/diode-legalized-routed-sta-20261114.json.

Slow:539setup,WNS-1.074318442ns,0hold; setupgroupsPCIe510/CPU26/async2/EthTX1. Typ0setup,8hold,WNS-0.033812398ns(PCIe). Fast0setup,115hold,WNS-0.110754686ns (PCIe111/CPU2/EthRX2). Capviolationsslow101/typ104/fast111; slew567/241/126; fanout1477allcorners. RouterDRC0,antenna377nets424pins. Original4nsPCIeclockunchanged; nominalRCnotqualifiedRCcorners.

Latestslowworst write_valid->$auto$ff.cc:337:slice$570168(retry.bytes[25][5]): sourceQ0.638662ns,place35302buf1 .376415, NAND3_1 $abc$720139$auto$blifparse.cc:397:parse_blif$810545 delay1.356738ns at.117590pF/1.594826nsslew, place31537buf1 delay.977058ns at.164274pF/.849530nsslew, NOR2 .295619, place28884buf2 .420569, mux .364190; arrival6.017402ns. No holdpads. Criticalbranchchangedfrompreviousplace31551. Currentbuf4reroute43610680141 testsolderbranchonly; letfinish but doNOTassume onebufferclosesdistributedwrite-enabletree.

PotentialnextRTLhypothesis afterreviewingpriorvariants: predecode capture_address into registered16-waylowselect and registeredqualifiedhigh-addressgroups (ceil(storebytes/16),10for152bytes). Samewrite-data register andsameone-cyclecapture->storewrite; eachbyteenablegroup_q[index/16]&low_q[index%16] ratherthan globalwrite_valid+binarydecodeafterflop. Needexactcapture-validpredicate matching bothoriginalwrite_valid<=1 branches, sameasyncreset/linkclear, and formalper-byte strobeequivalence plusexistingreplay/fullpacketregressions BEFOREanynativecandidate. This is NOTimplemented orvalidated; do notclaimlatency/functional/timingpass. Inspectcurrentrtl pcie/soc_pcie_replay_tx.v and docs/combined-timing.md priorwritepaths. Avoidblindlyaddinglatency.

Otherjobs: preDRTjumpers43612029407, buf4reroute43610680141, PHY43603972722 remainliveatlatestpoll. Nojobsrestarted. Fullgoalopen.

## 2026-11-14 — pre-DRT jumper screen live, not a final antenna result

Follow43612029407/source408d751279f3ec57f9ee3a2b6601fd059aaa7b99 oncodex/pre-drt-jumper-screen. Basedbaseline2bb475... withunchangeddiodelegalizedODB/SDC/config. RunsONLYGlobalRouting, then native repair_antennas sg13g2_antennanp -jumper_only -iterations3 withoriginalratio_margin/congestionpolicy BEFORE detailedrouting. Explicitgrt::have_routestrue/have_detailed_routesfalse guards. Nativecheck_placement, before/afterODB+guides, independentwholechipinstance/master/location/orientation/status/pin/net/topport equality and canonicalper-netguidegeometry comparison. Requires actualGRT-0302 InsertedN jumpers (N>0) and changedguidenets; no-effectcasefails ratherthan launchinglongDRT. Noaddeddiodesallowed. 2400sflow/65minjob; noRCX/STA/detailedroute inthisscreen.

OfficialexactOpenROADdcf36133 GlobalRouter.cpp repairAntennas only invokesjumperInsertion when !haveDetailedRoutes(nets_to_repair). LibreLane3.0.5 common/grt.tcl onlyglobal_route/write_guide (noantenna repair), so priorbaseline didnotapplythispreDRTstep. OldpostDRT-jumpercall wasno-op and isnotrepeated. This is a hypothesis to reduceactual377remainingnets, notguaranteedclosure.

Artifacts: route-pre_drt_jumpers-43612029407 safelogs/JSON/proofs; guides-db-pre_drt_jumpers-43612029407 nativecloudonly, innerguides.tgz includes exactstate andentireGRTstep withbefore/afterODB/guides. Ifpassescontinue DRTfromthese EXACTmodifiedguides (doNOTregenerateGRTandlosejumpers), thencheckrealantenna/DRC andfreshRC/STA. FullchipLVS remainsownnewgeometryrequirement. Noexperimentworkflowmerged.

Otherlive snapshot: {"43591198141": {"status": "in_progress", "conclusion": null}, "43610680141": {"status": "in_progress", "conclusion": null}, "43603972722": {"status": "in_progress", "conclusion": null}}. Baseline43591198141 nowRCX/STAafterDRC0but377antenna-netfailedroute; buf4trial43610680141 independentlyrouting; PHY43603972722 simulating.

## 2026-11-14 — baseline routed, antenna improved but FAILED; RCX/STA live

Run43591198141 routejob132436088101 COMPLETEDSUCCESS. Routing3h56m26s, finalrouterDRC0 atiteration5, wirelength11001517. Strict antenna result377violatingnets/424pins (route__antenna_violation__count303); previousroute565nets/656pins. Improvement is NOTzeroacceptance. StandardunsupportedLEF58warnings remain; routerDRC0notfoundryDRC. Parentworkflowoverallnotterminal: RCX/STAjob132497306850 started. Follow samehandlefor3cornerresults; do notrerunrouting.

Safe14119918415 SHAd5d20e5af32453218931ada6aec41e14d4551fe3d14d3907f831be01b1031114 containsroute.log,stateouts,routed-state.json,proofs. Native14119848983 SHA3c9346bd008313c5f50f85e6f4798935bb01c487131fa0d802502c37707e3e60, innerrouted.tgz stayscloudonly. Receipt docs/evidence/diode-legalized-route-20261114.json withexactviews/metrics. No full-chipGDS/LVS pass transferred tothisroute.

Next antennarepair must targetthis completedroute/currentGRTguides and exact377-netreport. EarlierpostDRTjumper-onlyrepair wasno-op: OpenROADjumpers belong beforeDRT. Inspectexistingantennaflowhelper beforetryingpreDRTjumper/diode strategy; avoidrepeatingfailedpostroutecall or silentlyaccepting remainingviolations. Existingbuf4trial43610680141 continuesindependently, PHY43603972722 stilllive. Fullscope remainsopen.

## 2026-11-14 — exact three-corner buffer Boolean equivalence PASSED

Run43611046213/source19ac096b9594e6854399ff2c2554e97b59224715 PASSED all3positiveSATproofs and3actualinversioncounterexamples. Models hash-match frozenimplementationpackage822dab... inputcontract: fast547c5fb3ef0eabe0362de7fb361ff736f6791987996b4b1af39b70deb569a72e; slowed1cff6e4d66d89d200e94c2213b8926a71c451218ca2df9b1157c98460e4b1d; typ968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4. RealYosysread_liberty/flatten/check/SAT, no-libblackboxes. Safe14119783596 SHA260c7f413529e9acc3eb84dedcaedae3eef2f788689b9d4cf555df00278395d9. Allsixloghashes/verdictsrechecked. Tested scripts/qualify_retry_buffer_liberty.py retainedbyteidentically, experimentworkflowexcluded. Receipt docs/evidence/retry-buffer-liberty-equivalence-20261114.json.

Together with nativeplacement/connectivityproof43610473965, selectedbuf1->buf4candidate preserves Boolean behavior and existingconnections. It is NOT a timingpass: livebuf4reroute43610680141 must regeneratewireRC and measureallcorners/hold/electrical/antenna. Originalbaseline43591198141 and PHY43603972722 stillinprogress atlatestpoll. Noadditionalcandidate launched; followcurrenthandles.

## 2026-11-14 — exact buffer Liberty SAT qualification live

Follow43611046213/source19ac096b9594e6854399ff2c2554e97b59224715 oncodex/retry-buffer-liberty-equivalence. scripts/qualify_retry_buffer_liberty.py verifies originalimplementationpackage822dab.../releaseasset663146895, readsinputcontractwithoutrestoringnativefileslocally, fetchespublicIHPc4b8...Gitblobs forstandardfast/slow/typLiberty and requires eachSHA256 equal everymatchingfrozenpackageinput. Typical additionally968b0cfd... . RuntimeAppImaged6a349.../ubuntu22samepinned.

ActualYosys read_liberty (NOT-libblackboxes), flattenedtwo-cellcombinationalmiter and SAT provebuf1==buf4 for eachcorner. Separate inverterreplacement must produceactualSATproof failure, not genericparsererror. 3positive+3negativecases. Safeartifactretry-buffer-equivalence-43611046213 containsresultJSONandnativeYosyslogs; models/miter/nativework remaincloudonly. This is functionequivalence, not timing/physicalapproval. If frozenpublichash differs inspect ratherthan acceptingunboundmodel. No helpersmergeduntilpassed.

Livejob snapshot: retrybuf4reroute43610680141/job132494855003 in Rebuildroutingfromverifiedretrydriversizing; baseline43591198141/job132436088101 in Rebuildroutingfromverifiedfourdiodelegalization; PHY43603972722/job132474510071 in frozengatesimulation. Nojobsrestarted. Existingbuf4placement/connectivitypassed aspreviouscheckpoint; fullgoalstillopen.

## 2026-11-14 — buf4 placement/connectivity PASSED; coherent reroute live

Qualification43610473965/sourced0c1713733ef76d7ad8d601eac41d2a5e656227f PASSED on unchanged savedcandidate from43609939062. Nativecheck_placementrepeatedsuccess; all159933nontargetinstances and ALLnetconnections/354ports identical. Onlyplace31551 masterbuf1->buf4, X2617440->2615520DBU,Y1704780unchanged,R180->MX selectedrowreflection; statusPLACEDandA/X/VDD/VSSnets unchanged. Originalverifier was too strict about selectedorientation; diagnostic43610218581 provedexactdelta beforeexplicitqualification. No othergeometryallowed. Safe14120510154 SHA7118d141ef31cca85c805e615c7768d5a183f89da8da78316acbf11fa8854a52; native14120090635/d67191c...; candidateODB972d9676... . Receipt docs/evidence/retry-driver-buf4-placement-20261114.json. PlacementONLY, no timing/routingacceptance.

Follow newreroute43610680141/sourced42836ac2566de769473973bb15625e27f788f8d, branchcodex/retry-buf4-reroute (based frozenbaseline2bb475...). Originalroute43591198141 and PHY43603972722 remainliveuntouched. Newprepare_antenna_resume binds exactcandidateODB+nativearchive and makes exactlyone reversiblebuf1->buf4declaration change forplace31551 in BOTHindependentnl/pnl; allotherreferencecharactersretained and before/afterhashesrecorded. GRTvalidatesbuf4reference and expectedODB/SDC; allsignalroutesrebuilt,powerspecialpreserved. Same19200sroutinglimit355minjob, then19800sRCX/threecornerSTA, zeroalltiming/electrical/antenna/DRCgatesunchanged. No RTL/clocks/constraints edits. Addedcloud-onlyRCXnativearchive for coherentfollowup aftermeasurement.

Artifacts: route-retry_buf4-43610680141 safe, routed-db-retry_buf4-43610680141 nativecloudonly; routed-sta-retry_buf4-43610680141 safe; retry-buf4-rcx-native-43610680141 nativecloudonly. Ifinputregex/sourceguardfails inspect ratherthan weakeningchecks. Once measured compare againstbaseline; upsize can worsenupload/hold and is notguaranteedimprovement. Need pinnedLibertypositive-buffer equivalence alongside physicalsourceproof beforefinalacceptance. Testedplacementhelpers remainonexperimentbranch; experimentalrouteworkflow notmerged. FullserialPHY/newlayoutLVS/finaltiming/production stillopen.

## 2026-11-14 — buf4 native placement passed; selected-instance delta diagnosis pending

Run43609939062/sourcef8b704e002e5ccff680059459fba0ec4cf21c429: standaloneOpenDBswap passed; detailedplacement passed and159933othercells fixed, selecteddriver displacement1.9um, check_placementpassed. Finalverifier rejected selectedplace31551 attribute mismatch (currently permits onlymaster/location change; orientation/status stillstrict). All-net connectivity and alltopports comparisons alreadypassed before thatassert. Do not assume whichfielddiffers untildiagnostic.

Native14120090635 SHAd67191c33b2015eb39b097946904044e564990b12fddcd0c6d88f643d9ada340, innerretry-buf4-native.tgz. SourceODB c9deaebb...; candidate native/buf4-legalized-unrouted.odb SHA972d9676e2f3af51fda24b2411048b60383e9dfffdb92cd8550a9caf9c53e0b9. Safe14120075645 SHA2ca7cb3965d7dc1562c2928908b63f0b559dd06462250a6ba95902a34f2b4930. Candidate NOTaccepted and NOtimingclaim.

Follow diagnostic43610218581/sourcec35979b8f0efd150ea6f0ff4ed551088f1478121, samebranchcodex/retry-driver-buf4-placement. Restores ONLYoriginal+candidateODB from pinnednativearchive in cloud; does not rerun/editplacement. Updatedverifier writes derived/native-delta.json before originalstrictassert. Inspect actualselectedchange; preserve allnonselectedgeometry, everypin/net/topport and placementstatus. If selectedorientationchanged, determine legitimate legalizedroworientation and explicitlydocument permittedselectedtransform rather than suppressing unexpecteddiffs. No nativefiles local.

Also checked officialLibreLane3.0.5 source: GlobalRouting.outputs=[ODB,DEF], so it does NOT update nl/pnl. Futurecandidate needs matchingbuf4in independentlogical/poweredreference. WriteViews can emit freshviews, or exactsingle-master replacement in originalnl/pnl with inversehash guard and nativeconnectivityproof; do not pair oldbuf1reference withbuf4layout. Primarysource librelane/steps/openroad.py classGlobalRouting and scripts/openroad/common/io.tcl write_views. Originalbaseline43591198141/PHY43603972722 remainlive at priorpoll.

## 2026-11-14 — native sizing callback fix; next integration must regenerate netlists

Retry43609730238 reachedOpenROAD but swapMaster on STA-attachedODB withoutLiberty crashed (signal11 sta::ConcreteCell::portCount/equivCellsArcs/dbStaCbk). Derived14119308393 proves nativefailure; no successfulplacement. The chosen geometry mutation has not yet been validated.

Follow43609939062/sourcef8b704e002e5ccff680059459fba0ec4cf21c429 oncodex/retry-driver-buf4-placement. New scripts/prepare_retry_driver_buf4.py creates independent odb.dbDatabase, validates exacttarget/net/pin schema and allinstance signatures, swaps onlymaster1->4 and writesbuf4-unplaced.odb. Then pinnedOpenROAD Tcl reads thatcandidate, locksother159933cells, legalizesselectedtarget, restoresstatuses, check_placement. FinalindependentPython compares allinstances/allnets/ports to originalsource. This avoids STAcallbacks for geometry-only step; it does NOT substitute for actual Liberty timing.

If successful, next route adaptation must preserve coherent nl/pnl/ODB: existing prepare_antenna_resume.py takes pre-sizing recoveredroute nl/pnl, which cannot silently accompany changedmasterODB. Generate fresh logical+poweredVerilog from resizedODB (or require nativeGRT returns matchingupdatedviews) and verify targetmaster/net connectivity before reusing full-reference generation. The known routeflow resets signals only and retains powerspecialwires; bind itsODBhash to actualnewartifact, regenerate routing+RC, preserve originalSDC1fab1c6a... andallcorners. Do not reuse oldtransistorreference or claim frozenRC timingacceptance. Baseline43591198141 and PHY43603972722 stilllive; unchanged.

## 2026-11-14 — retry driver screen infrastructure fix

Firstplacement43609541720 failed BEFORE nativeCAD: Ubuntu24 AppRun cannotwriteuid_map(Operationnotpermitted), returncode127. SourceODBhash verified unchanged; no placement/electrical outcome. Safe14119618668; native14119434428cloudonly. Do not interpret as designfailure.

Follow replacement43609730238/sourceb1bfdc7664b8b6ba02e5ca77c31bda68e9955948 oncodex/retry-driver-buf4-placement. Uses provenubuntu22AppImageenvironment; hostsha helper now explicit chunkedSHA256 forPython3.10 (samehash checks). ExactsameODB,buf1->buf4target,nativeTcl/independentconnectivityverifier,placementlimits and acceptance boundaries. Previousjobterminal; originalroute43591198141 and PHY43603972722 not restarted. Native outputs onlycloud.

## 2026-11-14 — exact overloaded replay driver placement experiment live

Follow43609541720/sourcea3487a2f42e87c3425db2573856838f7f77434af oncodex/retry-driver-buf4-placement. Targets ONLYplace31551 sg13g2_buf_1->sg13g2_buf_4 on verified159934-instance legalizedODB. Other159933instances LOCKED during detailed_placement, then exactoriginalstatusesrestored. max_displacement1000/1000, no legality waiver. Originaldriver/netnet31551, unique internal SIGNAL output, protection flags and pin-schema checked before swap. Native independent Python inventory compares ALL instance pinconnections, allnetmemberships, ports, nonselectedmaster/location/orientation/status and selectedorientation/status. Source/hash/runtime pinned. No simulationclock/SDC/RTL modifications.

Safe artifact retry-buf4-placement-derived-43609541720 containsresult/native-proofJSON. Native retry-buf4-placement-native-43609541720 stayscloudonly, innerretry-buf4-native.tgz. If pass, resultingout/native/buf4-legalized-unrouted.odb is NOT a routed or timing-accepted candidate; regenerate GRT/DRT and allcornerRC/STA before assessing benefit/hold regressions. Existingroute43591198141 remains untouched as independentbaseline. No testedhelpermerge until nativeexecutionpassed. If requestedmasterabsent/placementfails inspectactualreport, do not weaken invariants.

Source helpers: scripts/run_retry_driver_buf4_placement.py, scripts/retry_driver_buf4_placement.tcl, scripts/verify_retry_driver_buf4.py. Experimentalworkflow only. Parent evidence and rationale in immediatelypreceding checkpoint. Mainroute43591198141 and PHY43603972722 still IN_PROGRESS at dispatchsnapshot. Fullgoal notachieved.

## 2026-11-14 — concrete retry-store setup driver diagnosis

While live route43591198141 and PHY43603972722 continue, inspected actual prior routed STA safe artifact14111793410/run43579643337 (29,027,528-byte ZIP, derived reports only, RAM only). `nom_slow_1p08V_125C/max.head.rpt` worst path write_valid ($auto$ff.cc:337:slice$309577) to $auto$ff.cc:337:slice$569476 has slack-0.799543ns, arrival5.755142ns, required4.955600ns, original4ns PCIe clock.

Concrete data-path cells: sourceQ0.707018ns/0.095786pF; place35302 buf_1 delay0.407540; nand4_1 delay0.224774; place31551 buf_1 drives0.299358pF with1.540707ns slew and1.204865ns delay; next nor2_1 delay0.992989/slew0.747776; place29583 buf_8 delay0.361816; mux2_1 delay0.286367. NO dlygate hold pads on this path. Prior failure here is load/slew dominated, so do not blindly add RTL latency. Replay RTL already stages write_address/data/valid, and historical docs/combined-timing.md records prior write_valid sensitivity to placement.

Next actionable independent candidate: inspect same drivers in exact legalized sourceODB and evaluate targeted positive-buffer upsize/legalization (e.g. place31551) before another full physical run. Preserve all topology/clocks/constraints; measure allcorner hold as well as setup, and regenerate routes/RC after size/pin-geometry changes. Frozen-wire sizing is ONLY a hypothesis screen, never physical acceptance. Existing old helper scripts/cloud_route234_sizing_screen.py and prepare_route234_sizing_screen.py illustrate guarded native master replacement but bind a DIFFERENT old114025-instance design; do not run them unchanged. Current159934-instance legalizedODB is native14112212387/hashbe3f5242a66dbbc81708b43f83d707c58ccc07d944bc8fe8fc3c11a745013228, membernative/four-diode-legalized.odb hashc9deaebb26a07bf0909c249547156b1a1cb96401c8ccfa3748acff818131d959. Proven local legalization helper sourcef0c5230da39e88f6b8a30994015b7e09c911a8d3, scripts/diagnose_four_diode_legalization.py and .tcl. Inspect/adapt carefully; lock others and restore placement-status provenance. No sizing candidate launched yet.

Original route/PHY runs remain live; do not restart them. Latest documentation commit8d67402061277f4adac460b22ca96bbd682163ff adds current scoped LVS pass to README and marks CLAUDE_HANDOFF historical. Fullchip fault suite remains passed. Full serial integration/finaltiming/production unresolved.

## 2026-11-14 — full chip native fault suite PASSED

Suite43607561776/source0af445ae8447e48a7fbd1252f1693df19acc3bfb PASSED allfour controls in one identity-gated cloud job. Identity108Match+strictportstrue; signal_open107Match/1NoMatch; SRAMMOSwidth107Match/1NoMatch; port_name108Match but strictportsfalse. Alloriginal DB hashes unchanged. Safe14118697093 SHA3ae02f4c345b809785f8a03bef78e0fc299ea13a477855e216ec0a7d9edb6917. See docs/evidence/full-chip-native-fault-controls-20261114.json and docs/full-chip-native-fault-controls-20261114.md. Tested helper copied byte-identically to integration; experiment workflow NOT merged.

Signal fault disconnects NSCELL_0 SG13G2_NOR2_1.A fromNSNET_356. SRAM fault changes CELL<31>.N5 width0.30->0.45 in shared DPbitkit definition. Port fault changes CAN_RX_I netname only; topology stillmatches and portgate correctlyrejects. Stored SPICE case semantics restored per originalreader; no blackboxing/deviceexclusion/netequivalence/portwaiver.

Next: follow route43591198141 and PHY43603972722. Route success must feed its OWN coherent GDS, poweredVerilog/fulltransistorreference and LVS; do not transplant old GDS pass. Existing prepare_namespaced_chip_streamout.py and run_full_chip_transistor_lvs.py pin prior artifact/hashes and must be rebound explicitly after newroute artifacts exist. Native outputs stay cloud-only. Full serial PHY, finaltiming/qualifiedRC and manufacturing approval remain open.

Latest snapshot: {"43591198141": {"status": "in_progress", "conclusion": null, "head_sha": "2bb475a2d0a9c51cfa985a50d0239799deaddc45"}, "43603972722": {"status": "in_progress", "conclusion": null, "head_sha": "389d8b4f2e5782521d5bd779807dce3bb5029a10"}}

## 2026-11-14 — stored full-chip identity replay PASSED; full fault suite live

Identity43607296971/source1c3f8363705a03c0e9d254a44b47d85ef5f4bcc7 PASSED:108Match, native comparetrue, flag_missing_portstrue, original DB SHAunchanged,97.73s comparison. Restoring original SPICE reference.case_sensitive=False also makes original saved-xref port check pass (beforefalse/aftertrue), confirming serialization-semantics cause. Safe14119285571 SHAdb1e0fdcaaf6c86fae0ef605d0e5e4fbe4d7d60b0cf94f362dd233c38266de9c. Receipt docs/evidence/full-chip-stored-identity-20261114.json. No port waiver or source/netlist edits.

Follow complete fault suite43607561776/source0af445ae8447e48a7fbd1252f1693df19acc3bfb, branchcodex/full-chip-native-fault-controls. Single cloud job reruns identity FIRST, then signal_open, sram_mos_width, port_name sequentially. Each restores same original DB independently. Identity requires108Match and strict ports; signal/MOS require native comparefalse; port-name mutation requires comparetrue but strict portsfalse. Aggregate requires allfour exact cases and sameoriginalhash; no generic command failure counts. Safe artifact full-chip-native-fault-suite-43607561776 contains aggregate.json plus per-case result/port-inventory JSON. Native DB remainsrunneronly. Tested suite helper not yet merged; do not merge experimentalworkflow.

Once suite passes retain helper/evidence and move to new-route results. Route43591198141 and PHY43603972722 still live at snapshot. Full serial PHY/newroute allcorner timing/coherent newroute LVS/production approval remain open.

Snapshot: {"43591198141": {"status": "in_progress", "conclusion": null, "head_sha": "2bb475a2d0a9c51cfa985a50d0239799deaddc45"}, "43603972722": {"status": "in_progress", "conclusion": null, "head_sha": "389d8b4f2e5782521d5bd779807dce3bb5029a10"}, "43607561776": {"status": "in_progress", "conclusion": null, "head_sha": "0af445ae8447e48a7fbd1252f1693df19acc3bfb"}}

## 2026-11-14 — saved LVS replay loses SPICE case semantics; restoration under test

Diagnosis43606966719/sourceb90cfd743752d1cf92cfe74a296dc4a105e59970 completed: graph compare TRUE/108Match; port check FALSE even on original saved cross-reference before replay. Safe14119210172 port-inventory.json proves both deserialized netlists case_sensitive=True; 354pins each, only2exact-case matches (supplies) but all354match case-folded with no collisions. Layout ports lower-case, SPICE reference uppercase. This is not evidence of electrical mismatch in original accepted extraction.

Official KLayout v0.30.13 src/db/db/dbNetlistSpiceReader.cc line1325 explicitly netlist.set_case_sensitive(false) because SPICE is case-insensitive. New experiment restores reference.case_sensitive=False, retains layout sensitivity, unchanged port/net names, collision/count guards, strict flag_missing_ports, full device graphs and original DB SHA. No pin/net equivalences or missing-port waiver.

Follow identity-only43607296971/source1c3f8363705a03c0e9d254a44b47d85ef5f4bcc7 oncodex/full-chip-native-fault-controls. If identity passes run actual signal_open, sram_mos_width controls and add a port-name mutation to demonstrate port rejection remains effective. Aggregate acceptance must require identity pass and all negatives rejected. Experimental helpers not yet integrated. Native files stay cloud-only.

Route43591198141 and PHY43603972722 still IN_PROGRESS at latest API check. Goal remains active: full serial PHY, final coherent route/LVS/timing and production approval are not complete.

## 2026-11-14 — native graph identity matches; port replay still unresolved

Identity replay43606609559/sourcecceb261dfd98ace5aa3e741df1d3d83d4d05005a completed native compare TRUE with108Match in79.95s after clearing stale xref and explicit model correspondence. However flag_missing_ports returnedfalse: control remains FAILED, no negative-controls acceptance. Safe artifact14118413876 containsresult.json. Original DB hashunchanged.

Follow port-inventory diagnosis43606966719/sourceb90cfd743752d1cf92cfe74a296dc4a105e59970 oncodex/full-chip-native-fault-controls. It records original flag_missing_ports before recompilation, both netlists is_case_sensitive, and top pin/net names; then repeats same identity. Use derived port-inventory.json to diagnose serialization/case or actual port correspondence. Do not weaken port gate or claim full controls passed. Original native extraction engineering LVS acceptance is separate and unchanged. Routing43591198141 and PHY43603972722 were still active at latest check. All CAD/native work remains cloud-only.

## 2026-11-14 — full-chip fault-control replay diagnosis; identity retry live

Original engineering chip LVS pass remains scoped to its exact old GDS/reference. Additional full-chip stored-graph fault controls are NOT accepted yet: first replay43605811862 failed identity and reported duplicate circuit pairs; its negative-width rejection is not independent detection evidence. Signal-open selector also used Pin.name as a field; corrected callable accessors.

Structure inventory43606135790/source69394957314082bcecab05fc1d9e13afe214dc3e PASSED, safe artifact14118323405. Both tops158681subcircuits,0directdevices; layout model names lower-case and reference upper-case. Official KLayout0.30.13 source confirms LayoutVsSchematic.compare appends to existing cross-reference, and xref.clear is exposed. New helper clears only old comparison results and explicitly maps each reference model to its unique same-name case-insensitive layout class after exact Python class/parameter schema checks. No model exclusions, net/pin equivalences, or threshold changes.

Follow identity-only run43606609559/sourcecceb261dfd98ace5aa3e741df1d3d83d4d05005a, branchcodex/full-chip-native-fault-controls. Do not accept negative controls until unchanged identity succeeds. Original DB/artifact hashes remain frozen; native stays cloud only. Experimental helper/workflow NOT merged into integration. After identity success run signal_open and sram_mos_width, require aggregate identity plus both genuine rejections, then retain tested helper and evidence without experiment workflow.

Route43591198141 remains IN_PROGRESS in rebuild-routing step; PHY43603972722 remains IN_PROGRESS in frozen-gate simulation step. Preserve live handles, do not restart. Full PHY, new routed-chip LVS/timing and production approval remain open.

## 2026-11-14 — full chip engineering transistor LVS PASSED

Original run43602758557 completed native compare &&flag_missing_ports TRUE:108Match,zero extraction diagnostics,354topports,7456816recursive primitives on both sides. Both SRAM interiors included (DP70110/SP1211120). Original strict auditor rejected only our changed success wording ("INFO : Netlists match." instead of "INFO : Congratulations! Netlists match."). No electrical mismatch was reported.

Reaudit43605359900/source1999119e9a22d6e771be3583f09debf8be3106b8 PASSED after exact alternate-success recognition.40positive/negative verdict controls passed, preserving mismatch/warning/must-connect/empty/missing-verdict rejection. Native DB and original log hashes unchanged; no extraction rerun or log editing. Safe14117612941 SHA99a62ccc4f2d4ae190fc25883e9a81ae06fd2a3ccc93a7395614075c52bd4a34. Native14117582646 SHAfd250afa9a2c55ef266149c583d76256dd8dcdd9d5f043cfd892a7043e15979b,innerfull-chip-lvs-native.tgz: native/full-chip.lvsdb SHA3ddd851b8f0d80050bc97aabb6576836eb1d20ef41d0184c239f7840b479ca22. Native stayscloudonly.

Accepted scope is exact old packet-interface chip GDS c6c7df7f... with engineering SRAM CDL and independent reference523438b6... . This does NOT accept the live new diode-legalized route, serial PHY, padframe, final timing or foundry approval. No manufacturing claim. Fullchip LVS helpers and auditor fix retained in integration; experiment workflows not merged. See docs/evidence/full-chip-engineering-lvs-passed-20261114.json and docs/full-chip-engineering-lvs-20261114.md.

Next: follow route43591198141 (fresh route+RCX+allcornerSTA) and PHY43603972722. When new route finishes repeat coherent GDS/fullreference/LVS on its own logical+physical inputs; do not transfer this pass across route hashes. Also consider fullchip native connectivity fault controls using completed DB without re-extraction, retaining proven macro controls and strict no-blackbox boundary.

Live job snapshot: {"43603972722": {"status": "in_progress", "conclusion": null}, "43591198141": {"status": "in_progress", "conclusion": null}}

## 2026-11-14 — isolated XOR loading candidate launched

Run43603972722/job132474510071 (source389d8b4f2e5782521d5bd779807dce3bb5029a10, branchcodex/cdr-isolated-xor-load1) dispatched and restoring frozen native input. Variantbd10_lowz8_xor1_cdata3_sel15. Compared to completed43596398222, ONLY24XOR_DATA HBT nx2->1. Same C-pairnx3,selectbias1.5mA, all bench sources/solver, original extracted wires/RC unchanged. This is a nominal externally clocked circuit hypothesis, NOT new layout/RC or full PHY.

Exact reversible24-record source delta plus3negative controls run before simulation. C-pair and selectbias intermediate guards retained using constructed xor1 baselines; receipts explicitly label these baselines unsimulated. Actual candidate current-density binding includes24nx1 HBTs+2Cnx3 HBTs; original3mA/emitter and all data/device/phase thresholds unchanged. No integration helper merge until executed/validated.

Follow the same run to completion (17000s simulator timeout,330minjob). Safe result artifact cdr-xor-load1-result-only-bd10_lowz8_xor1_cdata3_sel15-43603972722 includes result,isolated-xor-load-change,candidate-current-density-binding and intermediate proofJSON. Native xor-load1-native-* stayscloudonly. Mixeddivider-whatif-* containswaveformNPZ: do notdownload locally. Priorphysicaldiag43603543533 has frozen gates reproduced and supports testing reduced input loading; it does not predict acceptance.

Full chip LVS43602758557 and diode-legalized routing43591198141 still live; preserve handles. Goal remains production-ready fullscope, not achieved.

Job snapshot: {"43603972722": {"status": "in_progress", "conclusion": null}, "43602758557": {"status": "in_progress", "conclusion": null}, "43591198141": {"status": "in_progress", "conclusion": null}}

## 2026-11-14 — PHY post-bias physical diagnosis passed

Diagnosis43603543533/source09ff87119d427d932731ccb8a78b706c358ebccd PASSED, actual gates exactly reproduced. Safe14116909437 SHA035d187ec392926c4d111594b96b2e5d7c84b0072b621ca8ae2702fbac25163b. Original43603401088 failed only absent import dependencies; exact proven cdr_mos650_full650_loaded.py and cdr_n1_divider_whatif.py were restored from d22e49cab14ddc4ed70a46492c9ea83d0509ac55 on experiment branch, without gate changes.

At0.75UI X transition groups01/10 have zero samples with both inputs>=100mV. Their A-buffer median output+59mV/-17mV is still wrong sign although A-sampler medians-236mV/+217mV are correct. A-buffer HBT273/275 median collector currents already switch (.602mA/1.977mA for01,1.973mA/.649mA for10) while collectors lag. X has zero wrong-sign relative to simultaneous XOR for strong-input samples but many below100mV; do not mistake this for full data success. Selector-current-only increase did not solve loading/settling.

Next justified candidate to consider: isolated XOR input HBT nx2->1 relative completed cdata3_sel15, all24 XOR_DATA devices only, no source/bias/load/solver/gate changes. This is a hypothesis from observed collector settling, not an accepted circuit. Check prior experiments before launch (known variant list includesxor2/xor3, notxor1). Current/emitter binding must reflectnx1, preserve3mA limit. Existing c_devices and selectbias isolation guards assume xor2 and must be updated with exact reversible24-record differences, not removed. Native waveform/RC stays cloud-only. Existing acbuf15/acbuf20 and collectorwidth12/16 variants already tried; do not blindly repeat.

Full chip LVS43602758557 and route43591198141 still live at latest poll; continue following actual handles. Full PHY/final timing/production unresolved.

## 2026-11-14 — isolated PHY select-bias trial rejected; physical diagnosis live

PHY43596398222 completed FAILURE of frozen data gates, simulatorRC0,4671.69s. Variantbd10_lowz8_xor2_cdata3_sel15: only ibs0/ibs1 bias1mA->1.5mA relativecdata3, model unchanged. Device/phase/VI gates pass but data fails. X385wrong-sign/717below100mV of765samples; Y0wrong-sign/580below100mV. SamplerA65,C148,D96 below100mV,Bpasses. No layout or PHY acceptance. Safe14116609449 SHA f02366f817e8128ef272a93accd09f6c1bc7968f538373969ffd2de8a32a3677. Native14116918270 SHA2f2dd3cffcadde6e7111065c3e5c79580ec245f5bffa14a54116cb66c6587868 (cloud only). Mixeddivider-whatif artifact containswaveform: do not download locally.

Follow diagnosisrun43603401088 (source85e8478623537af67a0642c7ed7cc109c37b86ac, codex/cdr-select-bias-physical-trace). Uses existing frozen-phase physical-path observer on completed native waveform, reproduces all original gates first, now also saves interface_truth_rows. It does not rerun/modify circuit or loosen gates. Inspect input-sign disagreements and strong-input XOR violations to select a justified next circuit change. Do not blindly increase bias or accept partial Y improvement. Full-chip LVS43602758557 and route43591198141 remain active at last poll.

## 2026-11-14 — every native reference pin connection verified

Run43603138368 PASSED (source b278e7a3281e2c6eb4031af5f51ab8aeb0d92a02). Actual frozen KLayout reader graph compared against independent powered-Verilog JSON and qualified CDL pin mapping: all158681native instances and816244pin connections match, zero mismatches. Wrong-signal-net and missing-pin controls rejected. Previous354top-pins/7456816primitive/DP70110/SP1211120counts also pass. No physical-layout LVS acceptance implied. Artifact14116878522 SHA cf4412a58b54b5693149db8f1519bc837796cb66e4e10d14924111f4c44248c1. Receipt docs/evidence/chip-native-reference-connectivity-20261114.json. Updated tested native reader helpers retained.

Next priority: follow live fullchip LVS43602758557, route43591198141 and PHY43596398222; do not restart live jobs. Inspect actual native/audit failures if they finish. Fullchip LVS extraction/comparison still active at latest poll. No new native archives downloaded locally; expected connectivity JSON generated and consumed only in cloud.

Job snapshot: {"43591198141": {"status": "in_progress", "conclusion": null}, "43596398222": {"status": "completed", "conclusion": "failure"}, "43602758557": {"status": "in_progress", "conclusion": null}}

## 2026-11-14 — full transistor chip LVS now live

Run43602758557/job132470857034, branche codex/chip-full-transistor-lvs, source e8f1b7d0782132fcb991182b4fde3c1aa147fa57. Frozen inputs restored and native comparer fault controls PASSED. Full chip extraction/comparison/strict audit step is IN_PROGRESS; do not restart due to observation timeout. Native timeout18000s/job355min. Check terminal result, then derived full-chip-transistor-lvs-derived-43602758557. Native DB/extracted circuit stay cloud only in full-chip-transistor-lvs-native-43602758557.

This uses exact assembled namespaced GDS c6c7df7f... (prior timing-failed route43579643337) and independent full transistor reference523438b6... . Both passing macro deck extraction prefixes are byte-identical; assembled comparison contains all six explicit hierarchy name pairs and nine flatten targets per SRAM namespace, with exact macro device/pin counts and full-side primitive conservation. No blackboxing, nil mapping, net equivalences, or missing-port waiver. max_branch_complexity2048 (same tested SP bound); strict flag_missing_ports and audit retained. Full-chip main primitive totals are measured, not forced equal ahead of native comparison, since physical-only cells require genuine comparison. Still no full serial PHY/final-route/production acceptance.

Reader/source collection run43602421955 PASSED, source67464a2464ffdb9cae864667a2070d073fce659d, derived artifact14116294182 SHAa5738706249770973fe0edb52578c5e04be8240c51c664b244a3f6c3a36eb8f5. Contains actual DP/SP deck source (safe text), native reader result. Main full LVS helpers remain experimental on run branch until execution validated; do not merge workflow.

Latest job snapshot: {"43591198141": {"status": "in_progress", "conclusion": null}, "43596398222": {"status": "in_progress", "conclusion": null}, "43602758557": {"status": "in_progress", "conclusion": null}}

## 2026-11-14 — native full reference reader passed

Run43602238038 (source017e930b9ffd9edd997a98b70e4a614dea3f3181) PASSED. Actual frozen KLayout0.30.13 and original passing DP macro reader read full independent reference: SOC_TOP 354pins,158681subcircuits,7456816recursive primitives, DP70110/SP1211120. No extraction/comparison was performed. Original full reference hash unchanged. Artifact14116517553 SHA71113a8ea0f126257e94d9c799e54ab621fdcaaab4064f9a5ff8d4186dd330b9. See docs/evidence/chip-native-reference-reader-20261114.json.

Next job 43602421955 source67464a2464ffdb9cae864667a2070d073fce659d on codex/chip-reference-native-reader repeats qualification while exposing ONLY source code of both proven macro decks (dp-lvs-deck-source.txt,sp-lvs-deck-source.txt) as derived artifacts. Native archives remain cloud-only. Read these sources to compose both SRAM transformations into full chip LVS without inherited macro-top-only assertions or losing any flattening/pair mapping. Current native reader helper intentionally exits BEFORE extraction; do not mistake it for full LVS. Full-chip extraction/comparison still needs launch. Route43591198141 and PHY43596398222 were still live at turn start.

## 2026-11-14 — independent full transistor reference emitted

Cloud run 43601779482 PASSED, source a8b0244721df1e6d994b30b094fcb3413b25d799. Full hierarchical CDL emitted from unchanged powered routed Verilog: 158681 instances, 354 top pins, 7456816 recursive primitive devices, 1140 qualified isolated clock-load outputs. All 158661 standard-cell supplies and 20 SRAM VDD/VDDARRAY/VSS supplies resolve exactly to VPWR/VGND. No internal constants or supply mismatch. Both SRAM primitive totals match prior native macro LVS (70110 DP,1211120 SP). Original eight empty corner/edge library definitions are preserved and listed; no logical instance is empty. Full source library records unchanged. Pin-order emission/readback passed, but native KLayout reference parse and physical chip LVS are NOT yet run.

Native artifact 14115684311 SHA256 894aa48ad4ee2c0f6e43724f1a88f20b278128e49d27b3584148759317c5c0b9 contains streamout-native.tgz. Reference path hw/soc/out/namespaced-streamout/pinmap-native/soc_top-full-transistor.cdl SHA256 523438b6014557b86ee7d438f95ddbfaabb76f390265283fcb844c233fcb8aa4. Full native data stays cloud-only. Derived artifact14116063825. Details in docs/evidence/chip-full-transistor-reference-20261114.json.

Next: native KLayout reader qualification, then full hierarchical LVS using exact assembled namespaced GDS artifact14116226453 (run43599532225), exact full reference above, and both verified macro deck transformations. Preserve primitive counts, top ports, strict unmatched-port rules, and no blackboxing. Consider reading/validating reference first to catch syntax/name/port treatment before heavy extraction. Full chip layout is still the prior failed-timing route, not final route; no full serial PHY acceptance. First reference runs43601292901/43601561542 failed only new Python parser assumptions (CDL slash delimiter and original empty corner definitions), corrected without modifying library bytes or circuit topology.

Current job snapshot: {"43591198141": {"status": "in_progress", "conclusion": null}, "43596398222": {"status": "in_progress", "conclusion": null}}

## 2026-11-14 — all 1140 open clock-load outputs qualified

Cloud run 43600938256 passed (source eb33eff08d22a924bec182547086dce9dafb187c). Frozen Liberty confirms all 1140 omitted scalar X/Y pins are outputs on exact clkload-number instances. Missing input/power, bus, width mismatch and unrelated-instance controls reject. Top ports have no constants or aliases. This is interface qualification, NOT full-chip LVS. See docs/evidence/chip-open-output-qualification-20261114.json.

Next: emit independent full transistor CDL from powered logical netlist with exact formal order, explicit isolated nodes only for qualified open outputs, and verified internal constant/supply mapping. Raw config VDD_PIN=VPWR/GND_PIN=VGND, VDD_NETS/GND_NETS null; do not guess supply nets from configuration. Inspect logical connectivity and map to declared top supply ports. Use complete standard-cell CDL plus namespaced SRAM CDL; no macro blackboxing. Native JSON and artifacts stay cloud-only. Main routing 43591198141 and PHY isolated-bias 43596398222 remain in progress at last check; do not restart. Integration streamout uses the previous failed timing route and is not final physical acceptance.

## Assembled SRAM geometry readback passed

Run **43600253157**, source `09ac3feea2471ed393055fdf55d84be9dca5b3f5`, verified all **311 SRAM library cells** in the actual assembled main-chip GDS. No missing or different cells; grid, shapes, labels and internal instance transforms/arrays match. The main-chip top contains exactly **16 DP and4 SP macro instances** as required. Safe artifact14116495410, SHA256 `28d31064048873cd2a8e3bb6676f1ff5938773b01642287ddf07a7e46819752c`.

This closes the namespaced SRAM geometry-transfer check for the prior CRC route, **not full-chip electrical LVS, DRC, timing or manufacturing acceptance**. The GDS direct-top instance count1,388,337 is structural and must not be equated to the powered-Verilog logical count158,681 without classifying helper/via/physical-only cells.

Next substantive task: qualify the1140 omitted clock-load outputs using authoritative cell directions, resolve top-port/constant/bus mapping, then build the independent full transistor schematic and compare it to this frozen GDS. Use the pinmap and streamout artifacts listed immediately below. Keep original gate failures visible and repeat final verification on the newer route once it completes.

Evidence: `docs/evidence/assembled-sram-geometry-passed-20261114.json`. Tested readback helper retained in integration.

## Main-chip GDS produced; independent powered-netlist interface inventory completed

### Verified streamout

Run **43599532225**, source `879fb01d6680375de93b18618705ebd38f58b97d`, completed successfully. The actual main-chip GDS with namespaced SRAM views is **138,694,064 bytes**, SHA256 `c6c7df7f7fe7d23c03847ffa49bb547423ff89b7dc9266a47effa495efea077d`. All LEF cells had corresponding GDS cells; original DEF/ODB/netlist/SDC hashes were unchanged. Safe artifact **14116226438**; native **14116226453**, SHA256 `bb1421b73653582fb56f11abedf90d66153e4d5919ef761a1d8a685b12d08d31`, contains `streamout-native.tgz`. Keep it in cloud.

This is an integration qualification using the prior completed CRC route43579643337, which failed antenna/timing gates. It is NOT final layout acceptance. The separate legalized-diode route43591198141 is still running.

Readback audit **43600253157**, source `09ac3feea2471ed393055fdf55d84be9dca5b3f5`, branch `codex/assembled-sram-geometry`, compares the actual assembled macro cells against all311 cells in the verified library, including shapes/labels/internal instance arrays/transforms and16DP+4SP multiplicities. Inspect the result before claiming lossless assembled geometry. Safe prefix `assembled-sram-geometry-derived-`.

### Independent full-CDL pin inventory

Run **43599635907**, source `c04f30d7696e1a3bb2550c5192ed65f125b351e1`, completed its diagnosis. It parsed the original **powered** logical netlist (`pnl`) into YosysJSON without synthesis/optimization, and checked **158,681 cell instances** against full standard-cell and namespaced SRAM CDL headers. **No unknown cell types** were found.

All reported interface issues are omitted X/Y output connections on clock-load examples: BUF_8=342,INV_2=259,INV_4=128,INV_1=330,INV_8=73,INV_16=7,BUF_4=1 (total1140). The report does NOT accept these automatically. Next verify directions using the pinned cell-library interface definitions, check every affected instance (not just first-five examples), and represent intentionally open outputs with unique isolated nodes only after that proof. Missing inputs/power/width errors must remain failures. Add meaningful negative controls for omitted input/power and wrong width.

Before emitting a full schematic, also verify top-port aliases/constants, source bus direction/index metadata, constant-net mapping and source pin ordering. Do not silently tie missing pins or use empty macro definitions. The old blackbox-only converter remains unsuitable. Native JSON is cloud-only in artifact **14115941190**, SHA256 `588c3deacaf4c5824500ba96da77cf85a486e0d122a770f62a94c6436e6a8fa3`; safe pinmap artifact **14115941182**. The streamout GDS contains physical-only cells as well; distinguish intentional physical cells from omissions when full transistor LVS is assembled.

Tested preparation, guarded streamout flow and diagnostic pinmap scripts are now retained in integration. Evidence: `docs/evidence/mainchip-namespaced-streamout-and-pinmap-20261114.json`. PHY43596398222 remains live; complete PHY, full-chip LVS, final timing and manufacturing approval remain open.

## Current checkpoint: fast exact restore verified; main-chip integration advancing

The previous turn made concrete progress. The archive bottleneck was measured and fixed; the coherent main-chip preparation now succeeds. Full-chip LVS and manufacturing approval remain **unproven**.

### Verified input restoration

Run **43598890723**, source `f1145703b7280773670ded41e46638fdaa906413`, verified all **5,030 files / 1,173,231,506 bytes** against the frozen contract, including disk readback hashes. Header scan took 3.33 s and sequential restore 5.89 s. The former lookup order caused 2,539 backward seeks in gzip. Manifest hash: `fe773024abb77b2c184be52ca26eb1028eba228e0a784cfdd78f4175e92f98d0`.

Only the two jobs still in input restoration, **43598072420 and43598415001**, were deliberately canceled after this proof; no routing or PHY calculation was canceled. Their replacements preserve all input hashes. The actual pinned AppImage replay then restored and verified all files in about11 s.

### Coherent main-chip inputs now prepared

Run **43599303587**, source `1d9748bf0bd6436e1bcaddd8a403f90cce6d71f3`, passed preparation. It binds **16 DP and4 SP SRAM instances** to the verified namespaced GDS files. Every other configuration field is unchanged. Archived logical views are `def,nl,odb,pnl,sdc`, and their hashes are in safe artifact **14115961267**. The prior `pdk_dir::` path failure was fixed by resolving the exact file through the pinned input contract; hash checks were retained.

This run stopped at the CLI because `--force-run-dir` requires an existing directory. The workflow now creates it. Current streamout run: **43599532225**, source `879fb01d6680375de93b18618705ebd38f58b97d`, branch `codex/namespaced-chip-streamout`. Inspect its actual terminal result before claiming GDS completion. Safe artifact prefix: `namespaced-chip-streamout-derived-`; native files stay cloud-only.

### Independent schematic interface inventory

Run **43599316243** successfully parsed the archived **powered Verilog netlist** with Yosys, without synthesis or optimization. Its first inventory stopped on a differing connection signature for `SG13G2_BUF_8` instance `clkload0`. This is not yet classified as an intended open output or a defect.

The observer now records every interface variant, its count/examples, and every missing/extra/width issue rather than stopping on the first difference. No unresolved pin is accepted or filled in. Current run: **43599635907**, source `c04f30d7696e1a3bb2550c5192ed65f125b351e1`, branch `codex/chip-full-cdl-pinmap`. Safe artifact prefix: `chip-full-cdl-pinmap-derived-`. Read `pinmap-inventory.json`; unknown cell types and ambiguous power/bus mappings must be resolved before emitting a full independent transistor schematic. The old `verilog_to_spice.py` remains blackbox-only and must not establish full LVS.

The streamout/pinmap work uses the **prior completed CRC route43579643337**, which failed timing/antenna acceptance, solely to qualify the integration process. Repeat on the final accepted candidate. Current legalized-diode route43591198141 and PHY select-bias simulation43596398222 remain separate running calculations.

Evidence: `docs/evidence/fast-restore-and-coherent-chip-preflight-20261114.json`. The tested sequential-restore helper is retained in integration; in-progress streamout/pinmap helpers remain on their experimental branches.

## Coherent main-chip streamout and independent full-CDL interface preparation live

NamespacedSRAM library itself passed bothmacroLVS+losslessmerge (below). Now streamoutqualification43598072420/source85d29262c1048e00e82621dba61af94a61090400,branchcodex/namespaced-chip-streamout. Usescompleted priorCRCjumperroute43579643337 native14111958544 SHA0c61942e79e1c94aceedd757e5d4cc298af6cbbe90480612c72bfed2fcbf18b0 (timing/antenna FAILED; qualificationonly). DoesNOTreplace/interfere withlive legalizeddiode43591198141. Restores exactPDK/design package663146895 SHA822dab7067d901fa79dabffffff784baf5c9965f0a5091eba67acdc48b9956f4 andnative library14114456981 SHA647008a959be8601aeb762f5ba238c7864ad0bcde0ef807f3e1dcae3324d8d25. ChangesONLY2MACROS.gds fields toproven dp.gds/sp.gds, verifiesoldmacrohashes, allotherconfigfieldsequal, retainsoriginalDEF/ODB/netlist/SDC views withhashes. Native KLayout.StreamOut insidepinnedLibreLane3.0.5AppImage. GuardchecksconfiguredmacroGDS hashes andalloriginalviewshashesbefore/after. Requiresactualoutput; skippedstepfails. Safe namespaced-chip-streamout-derived-*;nativenamespaced-chip-streamout-native-* stayscloud.

First43597457415/source89e0282141e7f471174810801bea2cb13655218c failedbeforedesignload:Ubuntu22Python3.10lackshashlib.file_digest. Fixedrestorecommand to usepinnedAppImagePython, notweakenhashchecks. Do notrepeathostPythonexecution. Currentrestore rehydratesallcontractinputs (notonlytools), then exactroutedarchive; monitor actualterminalresultsbeforeassuming success. Helpers scripts/prepare_namespaced_chip_streamout.py,hw/soc/pnr/namespaced_sram_streamout_flow.py areonexperimentbranch,notyetqualified/merged.

Independent pinmapinventory43598415001/source0d40c767d55ed8698afe0b16c1d31158043abccc,branchcodex/chip-full-cdl-pinmap uses sameexactfrozenrestoration. Yosysread_verilog+write_json ONLY, no synthesis/optimization; preferpnl else nl. ParsefullstandardcellCDL+namespacedSRAMCDLheaders, inventoryeverycelltypenamedportwidth/scalar/busbit/supplysuffix mapping,unknowncelltypes/missing/extraports visible. No empty macro definitions, no inferredmissingsupplies, noSPICEoutputorLVSpass yet. Explicit VDD!/VSS!/VDDARRAY! formalaliasesloggedonlyifnamednon!connectionexists. Nonzero-based/irregularbus interfaces flaggedforreview. Same-typeinstanceinterfacesmustagree. Safe chip-full-cdl-pinmap-derived-*; JSONnetlistandnativearchivescloudonly. Existinglegacyverilog_to_spice.py remainsblackbox-only andmustnotbeusedtojustifyfulltransistorLVS.

Next: inspect preflight/result/streamoutlogs andpinmapinventory; resolve genuineport/power/order issues beforewritingindependentfullschematic. StreamoutarchivecontainsnewGDS/config/state/library; sourcelogicalnetlistviewscanberecoveredfrompinnedpriorroutearchive. Repeat finalintegrationonnewcandidateoncecurrentroutecompletes. PHY43596398222selectbiasstillrunning; fullPHY/finaltiming/productionremainopen. Receipt docs/evidence/chip-streamout-pinmap-launch-20261114.json.

## Collision-free SRAM GDS/CDL library built from two strict native LVS passes

43596487748/source5a68106d6043c9ad3f8f644bb4eff6492b281b1e: DP26Match andSP25Match strictPASS,0extractiondiagnostics,originaltopportcontracts and recursiveprimitivecounts preserved. Namespaced GDS/CDL reversible proofs andGDSroundtripgeometry/instance checks passed. No new device/value/port/net waiver. Tested scripts namespace_sram_macro.py and replay_{dp,sp}_sram_namespaced.py retained in integration.

Bundle43596855175/source9b1da1411db02188f90c21dedcb51f36ca1db849 succeeded. 290uniqueCDLdefinitions,311uniqueGDS cells,allXcalls resolveuniquely within ownmacro library. Fullshape/instance/layout-grid equality before/aftermerge andGDSwrite/read,allreference-record equality. Tops unchanged RM_IHPSG13_2P_256x16_c2_bm_bist andRM_IHPSG13_1P_2048x64_c2_bm_bist. Safe14114083194 SHA79666c446a03f9c82b7a5357895439a71ee15f77642fd5352bbb8972c4e9df2a;native14114456981 SHA647008a959be8601aeb762f5ba238c7864ad0bcde0ef807f3e1dcae3324d8d25. Nativezip containsdp.gds,sp.gds,dp.cdl,sp.cdl,sram-namespaced.gds,sram-engineering.cdl,manifest.json. Keepcloudonly. MergedGDS SHAfb6925729c25f70eba48d6feb15daba92e586befe0bf12827e2cc2cc3f76b86a;mergedCDL SHA6a80a60991554f8f680249556192a24b4c3768bf843449927280c049b45eafd6.

NEXT integrate namespaced macroGDS paths into coherent mainchip streamout config, preserving originalmacroLEF/Liberty/timing/topinterfaces. Sourceconfig must be tied to exact routedcheckpoint; finalroute43591198141stillrunning. Main-chip independent schematic conversion must include FULL standard-cell andnamespaced SRAMCDL with explicit originalpinorders/power/busmapping. Existing hw/soc/pnr/lvs/verilog_to_spice.py is explicitly legacy macro-BLACKBOX and must NOT be reported as full transistor LVS. Need an independently sourced logicalnetlist, not GDS-extractedreference. Both full-chip LVS and finaltiming remainopen; individualmacropasses andlosslessbundle are necessarybutinsufficient.

PHY43596398222 isolatedselectbiasstillrunning; no newlayout/PHYacceptance. Nativebootpassed. Testedhelper build_namespaced_sram_library.py retained. Source-tree exploration: rootrecursiveGit tree isTRUNCATED; use subtreeSHAs for scripts,hw/soc/flow,pnr ratherthan assuming omitted filesabsent. Evidence docs/evidence/sram-namespaced-library-passed-20261114.json.

## SRAM namespace fix in native LVS; isolated PHY select-bias trial launched

Reference reachability43595961882 succeeded: both macro tops reach62CDLdefinitions,0unresolvedXinstances. ConflictingMET3RES is genuinely reachable:12DP and6SP direct definition references, widths.24/.26um. It cannot be discarded as unused.

Namespace candidate branchcodex/sram-namespaced-lvs uses NSDP_/NSSP_ prefixes for every internal GDS cell and CDL subcircuit, preserving actual macro top names/ports. Proves reversible complete CDL record substitution, rejects injected resistor-width change, and checks physical shapes/hierarchical instance transforms/arrays before rename and afterGDSwrite/read roundtrip. Every originalinputhash still checked before mutation. No values,nets,ports,models or acceptance thresholds changed. Both same macro strict LVS runs then compare renamed artifacts with original recursive counts and native port contracts.

Firstrun43596245592/source0fc26be6cd80b8a8a99a32a1ce1feee20d9ecaed: preservation proofs passed onboth, native compare stopped because Ruby %w flatten-cell lists retained old names. NOT LVS pass. Fixed exact %w[]/()/{} list mapping plus quoted operands and regression examples in5a68106d6043c9ad3f8f644bb4eff6492b281b1e. Retry43596487748 running, safe namespaced-{dp,sp}-derived-*; native namespaced-{dp,sp}-native-* cloudonly. Requireactualstrictpassboth before building common library/chip reference. Experimentalhelpers stay onbranchuntilnativeverification.

PHY43596398222/source2520c0d8ef6d0c3537d28e5a989048b39a8edfe6, branchcodex/cdr-select-bias-isolated. Singlevariantbd10_lowz8_xor2_cdata3_sel15. Relativemeasuredcdata3: ONLY ibs0,ibs1 references1mA->1.5mA; allphysicalmodelrecordsbyteidentical, allotherbenchlines(data,clock,load,solver)identical, fullfrozendevice/current/data/phasegates unchanged. Motivation verified B/D-to-select physicalpaths and weakselectswing; thisisacircuitwhat-if, NOTnewlayout/RC/completePHY. Safe cdr-select-bias-result-only-*; rawwave/nativecloudonly. Do notrestartwhilelive.

Legalizeddiodefullroute43591198141stillrunning; nativebootpassed; SP/DPengineeringmacroandfaultcontrols passed before namespace. Productionapproval/fullPHY/finaltiming/fullchipLVSremainopen. Receipt docs/evidence/sram-namespace-and-phy-select-launch-20261114.json.

## Shared SRAM geometry inspected; trace actual reference usage next

Geometry preflight43595848957/source13bfe72c6a5e26d81515d130a02dee3f59f08d05 completed. OriginalGDS hashes verified. Conflicting CDL RSC_IHPSG13_MET3RES hasDP width.24um vsSP.26um,length.6um; this named cell is absent from both originalGDS hierarchies. Many unused CDL library cells also absent; corrected observer after43595752035 failed on unusedAND2X4. Do not treat absent unused library definitions as extraction failure or infer electrical corruption from direct shape hash differences. Thirty shared present cell names have differing raw shape hashes (including labels/instance text); this is NOT an equivalence verdict.

Reachability preflight run43595961882,source196ce7b01d5858dd36dabeaa29d8b69b77bd36e0,branchcodex/sram-reference-library-preflight: resolve original CDL X references from each actual macro top; report whether conflictingMET3RES is reachable, reference counts and any unresolvedXinstances. Inspect before building merged chip library. If reachable, preserve both definitions with deterministic macro-specific namespaces and prove unchanged contents/connections; never silently first/last-definition-wins. If unreachable, prove it before excluding unused definitions. No full-chip LVS has passed yet.

SP andDP engineering comparisons andfullmacro fault controls passed; bootpassed; PHY connectivity mapped but electrical marginsfail; legalized-diode route43591198141stillin_progress. Evidence docs/evidence/sram-library-geometry-and-reachability-launch-20261114.json. All nativefilescloudonly.

## Full-chip integration preflight found a shared SRAM reference name conflict

43595567300/source088ee293f07db0611dbd4c6dac103bd4f63c8f11 completed. Exact passed DP/SP engineering CDL libraries each145subcircuits,42sharednames:41identicalcanonicaldefinitions,1different RSC_IHPSG13_MET3RES. Do NOT concatenate/include both with a first/last-definition-wins merge. Individual macro LVS pass does not prove a merged library is equivalent.

Physical shared-cell investigation run43595752035/source202afdd19f4ec20be6c6d02dcfe8e79b59b7fafa, branchcodex/sram-library-geometry-preflight. Restores both pinned passing native archives only on cloud, verifies originalGDS hashes, inventories direct GDS geometry of42sharedcellnames and exact differing reference records. Safe sram-library-geometry-preflight-*. Direct shape hashes include labels and are not electrical equivalence proof; inspect shape/type/parameter differences before choosing deterministic namespace separation and explicit LVS mappings. Full-chip LVS remains pending.

All SP/DP fullmacro sensitivity controls passed; bootpassed; route43591198141stilllive; fullPHY and finaltiming stillopen. Receipt docs/evidence/sram-library-conflict-preflight-20261114.json. Native files remain cloud-only.

## SP full-macro fault controls all passed; A/B physical paths established

43595161911/source da49561e5f322166feb371f7b5e6ee14d96da9fa completed SUCCESS all4controls. Identity25Match strictPASS. WidthR0.2u->.3u,layerR0metal2->metal3,andfirstMOSgateNT->NSSOC_INJECTED_OPEN_GATE each completed native compare and strictFAIL(24Match1NoMatch),as required. Not infrastructure rejection. Both SP and DP engineering macro comparisons now pass with full-macro fault sensitivity controls; original vendor references and full-chip/production qualification still not passed.

PHY43595197025 sourced22e49cab14ddc4ed70a46492c9ea83d0509ac55 completed. Including physical rppd links established A-sampler toadp/adn andB-sampler tos0p/s0n reachability,29and52traceddevices respectively. No unresolved traversal frontier. This is connectivity evidence only, includes feedback/bias, not proof of forward gain or timing. Fixed-phase native waveforms and gates reproduced unchanged; data/XOR margins still fail. Do not repeat HBT-only/NMOS-only observer attempts. Next candidate requires localized RC/settling evidence and unchanged full electrical/data gates, then actual new layout/parasitics.

Full-chip reference collision preflight run43595567300,source088ee293f07db0611dbd4c6dac103bd4f63c8f11,branchcodex/sram-reference-library-preflight. Checks shared SP/DP subcircuit names/definitions in exact passed reference artifacts before building a common chip reference. Safe sram-reference-library-preflight-* only. No circuit/geometry mutation, no full-chip acceptance. Legalized-diode route43591198141 remains running.

Receipt docs/evidence/sp-full-controls-and-phy-paths-20261114.json. Native evidence remains only in cloud. Do not merge experiment workflows.

## SP full engineering macro LVS passed; full macro fault controls running

Run43594788773 sourcef2caf1977cdea6d514b51e2f7aa99c57839d388e: strict audit PASS within comparison scope,25Match,0other,0extraction diagnostics,nativeRC0,auditRC0,124.616s. Both sides preserve1211120primitives and355nativeports before/after normalization. Evidence-backed INVX2/NAND2X2/CINVX4 flattening on both sides;2048 bounded search, original acceptance rules unchanged. Geometry unchanged. This is engineering reference with5resistor corrections, NOT original vendor reference/full chip/foundry approval.

Full SP identity and width/layer/open-gate controls run43595161911, sourceda49561e5f322166feb371f7b5e6ee14d96da9fa, branchcodex/sp-full-macro-controls. Each uses exact native original inputs before one explicit reference mutation,355pins/1211120primitives and strict audit. Do not accept infrastructure failure as fault rejection. Inspect all4actual control results before claiming sensitivity verified. Helpers and native inputs pinned; live runs must not be restarted.

PHY HBT+NMOS trace43594964200 completed but still reaches only final HBTS;98physical rppd devices were not traversed. Added labeled resistor reachability (without changing RC or measured waveforms) in source d22e49cab14ddc4ed70a46492c9ea83d0509ac55, run43595197025. Supply rails stop traversal. Inspect upstream routes before circuit changes. Frozen gates remain failed; no PHY acceptance.

Legalized-diode full route43591198141 still live, native boot43588310054 complete/pass. DPengineering macro and negative controls pass (below). Next full-chip integration LVS must use a consistent routed design and explicit engineering-reference qualification. Receipt docs/evidence/sp-engineering-macro-pass-controls-launch-20261114.json; all native files cloud-only.

## SP normalization trial launched; PHY observer fixed, upstream trace incomplete

SP inventory43594622132 verified exact direct-device and child differences: top layout has1824 additional NMOS and1824 additional PMOS; reference has768 additional INVX2,512 NAND2X2,32 CINVX4 instances, accounting exactly for the difference. Matrix both sides2048 NMOS+64columns,770pins; search messages require640/1024 above previous512 limit. No electrical equivalence inferred from inventory alone.

Next SP run43594788773, sourcef2caf1977cdea6d514b51e2f7aa99c57839d388e, branchcodex/sp-normalized-bound2048: flatten those3 evidenced cell types on BOTH sides, preserve1211120recursive primitives and355native ports, search2048 with original maxdepth and1800s native timeout. Native fault controls also changed to2048. Strict audit required; green diagnosis execution is not acceptance. Safe artifact sp-sram-hierarchy-bound2048-normalized-derived-*. Do not restart while live.

PHY observer43594550414/source4274eeb93e2a17c519cd189f0e754e01ce17437b succeeded after logical/native alias fix. Original gates reproduced. Paths reach terminal HBTs xd0275/xd0273 foradp/adn andxd0282/xd0281 fors0p/s0n; no sampler port reached in current four-level HBT-only trace. Therefore upstream buffer connectivity is still NOT established; extend traversal to actual device types/port mapping before sizing changes. Output/data margins remain failed, no full PHY acceptance. Tested observer source retained in integration; dependency scripts remain on experiment branch.

Boot43588310054 completed/pass (details below). Legalized-diode route43591198141 remains live. Receipt docs/evidence/sp-inventory-and-phy-observer-20261114.json contains both derived reports. Native CAD/waveforms stay cloud-only.

## 2026-11-14: native MBIST/boot complete; SP mismatch narrowed; PHY observer repaired

Boot run43588310054 completed with native_returncode=0, completed_boot=true, passed=true, sources_unchanged=true. Both system/Ethernet MBIST and packet-async PCIe idle boot profiles passed. Source1c0d103c64f040543106b2a3e9265fe580f4d289; original simulation3fd0fded2d874efa0109d8558a213380de1f36a7. No checkpoint continuation needed. This is not SDF timing, serial PCIe traffic or manufacturing acceptance.

SP run43593832917 completed diagnosis in77s; strict LVS FAILED:26Match and2NoMatch (matrix512x128 and top).1211120 primitive devices conserved on both sides;355 native ports. Do not mistake green diagnostic workflow for LVS pass. Read-only SP matrix/top native inventory run43594622132 source9024017cf28506bb0fd546495a47abf8d595ddb9 is running; its safe artifact is sp-matrix-top-derived-43594622132. Compare hierarchy/direct devices before any additional flattening. Native archive14113282480 SHA2c7f88ea31c2e515c84b4664a1f2d99bf5cf06da2c753077a16154c065430ddb remains cloud only.

PHY observer43593968180 failed at assert selected: connectivity tracing omitted logical-to-native binding aliases. Fixed in4274eeb93e2a17c519cd189f0e754e01ce17437b, retry43594550414 running. Inspect actual result before accepting the fix; frozen waveforms, device gates and sampling phases unchanged. No new circuit/layout acceptance.

Legalized-diode full route43591198141 remains in_progress. Do not restart. Fresh DRC/antenna and three-corner timing must still pass. DP engineering macro pass and fault controls remain recorded below; original vendor/full-chip/manufacturing approval remains open.

Receipt: docs/evidence/boot-complete-sp-mismatch-phy-retry-20261114.json. All CAD/native waveforms/checkpoints remain on GitHub; no local project artifacts created.

## SP full macro hierarchy replay and PHY physical buffer diagnosis live

SP43593832917/sourcec0f792bc59c418edaae2bb5f7dfd4bb082fd589b,branchcodex/sp-sram-hierarchy-bound512. Restores exactSPtimeoutnative14111284849 SHAdd437de8cfc8f81ffe504a5555608eebf3b6f3d401ce9cd4c49d87e362e4e58c. SPspecific32cell/column512/matrix512x128pairs,355nativeportnamesbeforealign,1211120primitiveconservation,ownprevioussixflattenboundaries,512boundedsearch+15controls. NO DP-onlyINVX2/NAND2X2/CINVX4extraflatten. Safe sp-sram-hierarchy-bound512-derived-*;nativecloudonly. Strictauditstillrequired,greenjobdiagnosisonly. Do notrestartwhilelive.

PHY43593968180/sourcec65ecf1b92d3c603caaad71d15b63e47ff99e852,branchcodex/cdr-xor-physical-path. Usesexactcdata3native14112762376,originalfrozenacceptancereproduced. Traceadp/adn/s0p/s0nviaactualnumericwiregraphandC/E-to-baseHBTpaths(upstreamsamplerportsreported). Collectsimultaneousphysicalterminalvoltages/currentsatfixed.6/.75/.9UIphases. No newcircuitvalues/simulationoracceptance. Safe cdr-xor-physical-path-derived-*;nativewaveformsstaycloud. Inspectactualconnectivitybeforeanotherbuffersizingchange.

Otherlive legalizeddiodefullroute43591198141,fullnativeboot43588310054. DPengineeringfullmacroand4fullcontrolsPASSED;originalvendor/SP/fullchip/foundryqualificationremainopen. Launchreceipt docs/evidence/sp-hierarchy-and-phy-path-launch-20261114.json.

## ENGINEERING DP macro identity and all three full-macro faults verified

43593348833/source411cb5d256664ff49086779b671cf347c3f60199 terminalsuccessALL4jobs. Nativeidentity26MatchstrictPASS;R0width.2u->.3u,R0metal2->metal3,MOSgateB_RWL->NSSOC_INJECTED_OPEN_GATEeachcompletednativecompareandstrictFAILwithNoMatch. Eachnegativehas3Skippedparents/1NoMatch/22Match;notinfrastructurefailure. Safeidentity14113615843 SHA423d0c9ee2a95b7b69b77806a436004e8e8c2dc08c56b8d6eed0a5001f58d87c; width14113655801 SHAc48a171cf08c068a8b5e9edfc90f2fb939bde1e30ed9868f34d4877c14392fac; layer14113416930 SHAee018c7011ebfe004347b59b6d9fe0a3c87f97d9670782b62702d22fea9ca68f; gate14113990021 SHA07601c536446e8181f2f4f0bd8c6f2c355f77d7764bb2212ff0418650e2f309f. FullrawnativearchiveIDs/hashesincase receipt. No localCADfiles.

Humanreport docs/sram-engineering-lvs-20261114.md; fullreceipt docs/evidence/dp-full-macro-controls-passed-20261114.json; tested mutationrunner scripts/replay_dp_sram_full_macro_controls.py retained (NSSOC_MUTATION identity/resistor_width/resistor_layer/mos_gate_open). ExperimentworkflowNOTintegrated.

NEXT SRAM: adapt proven nativepre-alignports+explicit32cell/column/matrixpairing+512boundedsearch to SP savedtimeoutinputs14111284849. Inventory43591995572 confirmsphysicalRM_IHPSG13_1P_BITKIT_16x2_SRAM/COLUMN_512/MATRIX_512x128 vsreferenceRM_IHPSG13_2048x64_c2_1P_BITKIT_16x2_SRAM/COLUMN_pcell_0/MATRIX_pcell_1; donotcopyDPperipheralthree-cellflattenwithoutSPevidence. SPtotal1211120primitives;referenceportcountfrominventory. KeepimmutableGDS/referencehashchecks. SPinputdeckbeforehash0bf61b1efb961298ed8cca8da9d214bdbc526310065ecabf2a72a9f66d6145e7, command25ff225b27e169e3b65557c38e640fec11dc3381fdfae2e3faea6ee1937bd8bb, engineeringCDL3ef741993177dccaf1be29e34561c2b6d13d4c20dc75b00d6ab72b0a4a972a7c. Originalvendor/fullchip/foundryqualificationstillopen.

NEXT PHY: frozeninterface43592773443 points to A/Bdata/selectbuffer settling/margins; verify actualphysicalconnectivity before new circuit values. Bothsizingvariantsfailed; no blanketauthorizationtoswapoutputpolarityorrelaxgates. Testedobserverretained.

LIVE: legalizeddiodefullroute43591198141; fullnativeboot43588310054. AllotheraboveDP/PHYdiagnosticrunscompleted. Continuefullgoal,notproductioncomplete.

## ENGINEERING DP FULL MACRO LVS PASSED; full-macro fault controls live

43593043558/sourcecb15ee8f57f1050e8c1b7c6fc2a9e986bf7afa3b terminalsuccess. Native12.999s,strictauditPASS withincomparison scope,26Match0other,0extractiondiagnostics,explicitdecksuccess. Native215ports/namecontract,70110primitiveconservationbothsidesand15nativecontrolsPASS. Onlysearchcapacity16->512changedafterobserved360requirement;acceptanceunchanged. Safe14113665237 SHA1a4bbe0da252e0df4bd7822df56589b8d3b7b14eb8690435fcb9bc24fac446bc;native14113411418 SHAbff8640c1efc79d3877f3ececa08d369d5c80bbc81556c13284e540566aa260e cloudonly. ThisisENGINEERINGcandidate(eightresistortokens changed earlier),NOToriginalvendorCDL/fullchip/foundryacceptance. Testedhelper scripts/replay_dp_sram_ports_bound512.py andscripts/check_lvs_ports_bound512.rb retained.

Full-macro controls currentrun43593348833/source411cb5d256664ff49086779b671cf347c3f60199,branchcodex/dp-sram-full-macro-controls. Fourcasesidentity,R0width.2u->.3u,R0metal2->metal3,firstbitcellMOSgateopen. Mutationsoccurafterimmutableoriginalinputhashchecks,proveonlyonefieldchange,allgatespreserved. Requireactualnativecomparisoncompletion;identitymustPASS,eachmutationmustNoMatch/strictauditFAIL. Infrastructureerrornotacceptednegativecontrol. Safe dp-sram-full-control-derived-CASE-*;nativecloudonly. Do notcallcontrolspasseduntilallfourverified.

Topdegreeobserver43593086693/source50e54f8b52e532eec9b1f56cbeb70db3cac09dc6 succeeded. Layout4648nets333empty/reference4395nets0empty;empty-netcountaloneisnotnet-equivalenceproof. No netswerepurged;successful512comparisondidnotrequiregraphdeletion.

PHYXORinterfaces43592773443/source4377f7749e83f687a03fa361191425b24f087f35 completedbothdiagnoses. Frozenoriginalgatesreproduced. BothvariantsXinputsdisagreeideal414/765;strong-input200sampleshave0wrongXpolaritybut135below100mV. Ystrong304,0wrongpolaritybut187below100mV. Namedinterfacehypothesesnotconnectivityproof;nexttraceA/Bbuffer-to-Xdata/selectphysicalpathsandsettling,no polarity/gatewaiver. Safe cdata14112694295 SHAbc52ce27071d570a6f6fd281085d129ca56d3c6c3b52473957fd9700ddd2f865; cslave14112414765 SHAa6769047b6737646822617c0b52f84380173b1f05b3f1275b88f449b91319947. Tested scripts/diagnose_cdr_xor_interfaces.py retained. Fullreceipt docs/evidence/dp-engineering-full-macro-pass-and-controls-20261114.json includesallfourreports.

Otherlive legalizeddiodefullroute43591198141,MBIST43588310054. PHYsim43584735530terminalFAILboth,SP43566292104terminaltimeout. Keepfullproductiongoalactive.

## DP native215ports and primitive conservation pass, stricttopstillfails; PHYbothsizingvariantsrejected

43592362942/source6fd9507ee7542aad7f6be29f2a0125bdd73bc9e2 terminalsuccessDIAGNOSIS,strictLVSFAIL. Native215ports/nameagreementpassed,before/after70110eachpassed,15controlsPASS. 25Match/1topNoMatch(threepreviouslymatchedstandardcelltypesnowflattenedbothsides,notlostprimitives). Native194.116s. Safe14113400577 SHAc6630e283d72401d4d1644b0772bb052f43176561d1dff08092d53074edcdcd0;native14112394415 SHAd9f0cd937bc43ab7550c22d672835d2092556f2f64aac10f0584d0ca945186bc;DB40bf9721db12569e03a51b411a211b8fb8c51fccad02f554578c127a0a8e346c. Newread-onlytopinventory43592863220/source76228b6fa935deafe61753c16cf87a9e6739166d,branchcodex/dp-normalized-top-inventory,safe dp-normalized-top-derived-*. Inspectremainingcount/searchlimitsbeforefurthercompare.

PHY43584735530 nowterminalFAILbothjobs. cdata3job132416701841:simRC0,device/phasePASS,dataFAIL;C148below100mV,min45.73mV(vscslave3C120,min56.63mV). X386wrongsign717below,Y1wrong581below;A65,D96belowunchanged. Safe14112882059 SHA8aab59e3437f6c4e6e4ec97448679d45a7b652af8f5a623bd5c63c9ec96f2610;native14112762376 SHA29605a3d0eda6de2a348d2619d5f009edb87594d9581883be105d03d1bd6449f cloudonly. Neitherintegrated.

NewPHYsaved-capturediagnostic43592773443/source4377f7749e83f687a03fa361191425b24f087f35,branchcodex/cdr-xor-interface-diagnosis. Bothnativecapturescloudonly,originalgatesreproducedthenfixed-phaseX/Ynameddata/selectinterfacevoltagesgroupedbyexpectedbits. No timingshift/newsimulationoracceptance. Safe cdr-xor-interfaces-derived-*. Strong-inputmaskdiagnosticonly,originalgatesunchanged. Combinedreceipt docs/evidence/dp-native-ports-preserved-and-cdr-sizing-rejected-20261114.json.

Otherlive: legalizeddiodefullroute43591198141,MBIST43588310054. Do notpollterminal43584735530/43592362942asrunning. Allnativeworkcloudonly.

## Native port timing of construction corrected; strict215 guard retained

43592200178/source90270dd18db42c1e2729eab9c8f7435db092ce66 terminalFAIL beforecomparison:primitive70110eachpreserved,butnativeTOP_LVL_PINSafteraligncreated273layoutpinsvs215reference. All215present,58extraarehierarchicallypromotedinternal$instance.signal labels. Guardcorrectlyrejected. Safe14112748023 SHAf1fe484adf71435cee249483707d1d4eff46a57efd50d9035d417778177687af;native14112852727 SHA32cad698b0ffd6f222eb91017a400c71987b13a6ebe9888794d9bbca56c76a5e cloudonly.

Currentrun43592362942/source6fd9507ee7542aad7f6be29f2a0125bdd73bc9e2,samebranchcodex/dp-sram-top-ports-normalized. Movebothnative make_top_level_pins calls BEFOREalign,unchangedalgorithm andenabledswitch. No manualpinremoval/selection,nonequivalentnetsaliased. Keepstrict215namecontract,3arraypairs,3additionalflattenedcells,70110conservationand15controls. Safe dp-sram-port-normalized-derived-*;checknativecompletion/strictauditbeforeclaim. Receipt docs/evidence/dp-sram-native-port-order-correction-20261114.json.

Otherlive legalizeddiodefullroute43591198141,PHYcdata3job132416701841,MBIST43588310054. Earlierrecordsbelow.

## DP missing native port construction and exact peripheral boundary imbalance diagnosed

Savedtopobserver43592070053/source2c9c9cf589dfb90792de8fa581fb02f0836ac645 succeedswithoutdetailedxreftraversal. Safe14112946292 SHAc3913d24e6a91b64022b33ca8eba7c3f3edbd34652e73ce77483b937ea0c6e95. Layout0pins/reference215;all215reference namesexistlayoutnamednets. Pinneddeckmake_top_level_pinsdisabledbyoriginaltop_lvl_pins=false. Threeboundaryimbalancesexactlyexplain1808directMOSdifference:referenceextra384INVX2,256NAND2X2,8CINVX4;layout904extraNMOS+904extraPMOS. No proofyetthattopmatches. Nativeobserverfirst43591834876failedreferencepropertyAPI;fixed43591936491/43592070053successful,noGCcrash.

Newrun43592200178/source90270dd18db42c1e2729eab9c8f7435db092ce66,branchcodex/dp-sram-top-ports-normalized. OriginalGDS/CDLunchanged. Nativeoptiontop_lvl_pins=true;allow_unmatched_ports=falseunchanged. Requireexact215portcount/nameagreement(nativecreatesallnamedports,no selectivecreation). FlattenINVX2,NAND2X2,CINVX4onbothsides;before/afterrecursive70110eachmandatory. Preserve3arraypairsand15controls;strictauditunchanged. Safe dp-sram-port-normalized-derived-* includes top-port-and-extra-flatten.json. Notaccepteduntilnativeverdict+auditpass;notvendor/manufacturingapproval.

SPtimeoutinventory43591995572/sourcecd6f627546800d52adf39f5f0a9e4ae3eb5d53ee succeeded. Safe14112383414 SHA1c400482b0983233974d8c711e7d380941c3275e45724d20809685d522c122f0. Lastdeckphasecomparison06:42:45; nofinalDB/extracted.cir. Physical16x2SRAM,column512,matrix512x128namesdifferreferencebutcountsstructurallycompatible. Do notblindrerun. Fullinventories/ports/logs docs/evidence/sram-native-ports-and-sp-phase-20261114.json;testedobserversretainedscripts.

Otherlive legalizeddiodefullroute43591198141,PHYcdata3in43584735530,MBIST43588310054.

## SRAM block, column and matrix now Match; top remains NoMatch

43591517998/source1acd3c5a4d647495111b274178c29f0440f49a68 terminalsuccessDIAGNOSIS, strictLVSFAIL. 28Match/1topNoMatch. Full448-device32cellblock,1792-devicecolumn,28928-devicematrix eachMatchwithallcontentscompared;top70110eachunchanged. 15nativecontrolspass. Native67.066s vs925.965s block-only; no looseningoflimitsoracceptance. Safe14113030357 SHA1e4a50e936c708c72ac10be5854b762084c12593dddc1e9809e4373c0b6e3bb7; native14113100183 SHA9bac7b5cb401e8b8fc28442197e3dba1cf3c2ce30cba523eae779d315c0c7848 cloudonly. Receipt docs/evidence/dp-sram-matrix-match-top-open-20261114.json.

Nextinspectremainingtopports/peripheralcounts/searchmessagesfromsavedDB; avoidpreviouscrashingfullxrefreader. Additionalcellnamepairs requireinputhierarchyevidenceandstrictcontentschecks; no waiver. Do notpoll43591517998aslive orrerununchanged. OriginalvendorCDLqualificationstillopen.

Live legalizeddiodefullrouting43591198141,PHYcdata3job132416701841 in43584735530(cslave3terminalFAIL),MBIST43588310054. SPtimeout43566292104terminal. Allnativeworkcloudonly.

## PHY cslave3 completed and rejected; cdata3 still live

43584735530/source842ab2012fae1904251fd1503024e5670de6ad8f job132416702005 terminalFAIL at frozen waveform/device acceptance gate. SimulatorRC0,devicesPASS,phasePASS,VIpass;data/waveformFAIL. Cbelow100mV120samples(min56.63mV),A65,D96;Xwrong386/below717,Ywrong1/below585. cslave3notintegrated;noPHYclosure. Safe14112233130 SHAce095c2ced48cd5b78a7f036e538f0737fae994ffa925c51ff89c76a0cb47d5e;native14112317745 SHAe75dfba4fbd10c671f23764bd580bb5225f2fd848357e0914fb316981c5a6ab2 cloudonly; mixed14112686651 includesNPZ,donotdownloadlocally. Receipt docs/evidence/cdr-cslave3-rejected-20261114.json. Same run'scdata3job132416701841 stilllive;waititsownresultbeforecandidatecomparison.

Otherlive: legalizeddiodefullrouting43591198141; DPmatrix/column43591517998; MBIST43588310054. Latest integration continues below.

## Remaining DP graph hits depth500; matrix/column correspondence trial live

Serialization-only43591354767/source8baf59cd680f086eb64e33db9a41f510b1f089e3 successful. Safe14112816221 SHA6a9a9182c84264cf102443c1007eb0e334825e7b357ef338f2a6c29cf16d411d. SavedblockpairedDB contains15231search-limitmessages:11520depth500exhaustions plus3711complexity16exhaustions(needsmax272). Thus topNoMatchnotproofallstructuralfaults. Blockitself448vs448devicesMatch. No acceptance.

Currenttrial43591517998/source1acd3c5a4d647495111b274178c29f0440f49a68,branchcodex/dp-sram-explicit-matrix-pairs. Keep32cellpair; add physicalCOLUMN_64->referenceCOLUMN_pcell_0 andphysicalMATRIX_64x32->referenceMATRIX_pcell_1. Verifiedoriginalinventorybothmatrices2048bitcells,16columns,2matrixinstances. Existenceguards,allprimitives/ports/dimensionscompared,15nativeidentity/faultcontrols,depth500/complexity16unchanged. No electricalequivalenceassumedfromnames. Safe dp-sram-matrix-paired-derived-*;nativecloudonly. Receipt docs/evidence/dp-sram-block-depth-and-matrix-launch-20261114.json.

Otherlive legalizeddiodefullroute43591198141,PHY43584735530,MBIST43588310054. SP43566292104 andDPblock43589897545 terminal;neverpollaslive. Earlierrecordsbelow.

## DP32-cell block matched; top unresolved. SP timed out, both terminal

43589897545/sourceea8eef24283b7af4bd4e627330b104fc395af579 completeddiagnosis925.96s,15nativecontrolspass. StrictauditFAIL:26Match(includesexplicit32-cellblock),1topNoMatch;70110recursiveprimitivesbothsides,0extractiondiagnostics. Safe14111923944 SHA1ad936dd8eb943439fa005211519128543cc1656e0fa82c9e15a1070b69c0199. Native14111429578 SHA95e9cf179b818929781a79cca4e5a089e2e04d51a724a0b01752ead2c057fc05; DB839fc525689e193b0dd1146188c274bb2dfcc58f470fe345a17e9044e0de14c5. Do notretryunchanged. Newserialization-onlydiagnostic43591354767/source8baf59cd680f086eb64e33db9a41f510b1f089e3,branchcodex/dp-sram-block-search-messages; safe dp-sram-block-search-messages-derived-*; noCADobjectloading/replay.

SP43566292104/sourcec226118b038f4180ce97452b9e469e873b37fd83 terminalFAIL:18000snativetimeout,novalidfinalLVSverdict. Safe14111334791 SHA74fa424a9b2b86c866bcd5c49ea833654177fbca545df1a08871105944028b65;native14111284849 SHAdd437de8cfc8f81ffe504a5555608eebf3b6f3d401ce9cd4c49d87e362e4e58c cloudonly. Nextinspectsavedphase/hierarchybeforeanyreplay; don'trestartblindly. Fullreceipt docs/evidence/sram-block-match-and-sp-timeout-20261114.json.

Otherlive: legalizeddiodeGRT/DRT43591198141,PHY43584735530,MBIST43588310054. Earlierrecordsbelow.

## Four failed diodes legalized; full routing continuation live

Run43590951082/sourcef0c5230da39e88f6b8a30994015b7e09c911a8d3 succeeded placement-only screen in29.27s. Fourdiodes ANTENNA_482/1342/457/458 movable;159930otherinstances fixed, allotherposition/orientation invariants passed,total159934unchanged. Originalplacementstatuses restored; native check_placement passed, no warnings/errors. No routing/antenna/timing claim. Safe14112471184 SHA3a29560701a518de1bd209909938697fb6f5989bfa5b4652fb125bd36e304122. Native14112212387 SHAbe3f5242a66dbbc81708b43f83d707c58ccc07d944bc8fe8fc3c11a745013228 cloudonly; verifiedfour-diode-legalized.odb SHAc9deaebb26a07bf0909c249547156b1a1cb96401c8ccfa3748acff818131d959. Testedhelpers now retained in scripts/diagnose_four_diode_legalization.py and.tcl.

Current route43591198141/source2bb475a2d0a9c51cfa985a50d0239799deaddc45,branchcodex/crc-legalized-diode-route. Restores exactverifiedplacement and originalSDC; clears only signaldbWires, retaining supply/specialwires, rebuilds GRT+DRT thenfreshCheckAntennas. DRTautomaticrepairloops0 for first fullrouteof alreadyinserteddiodes; strict finalantenna-zero and3cornertiming/electrical gates unchanged. Nativeinput/version/script hashes pinned. Safe route-crc_diode_legalized-* androuted-sta-crc_diode_legalized-*;nativecloudonly. Do not restartwhilelive. Receipt docs/evidence/crc-four-diode-legalized-route-launch-20261114.json.

Otherlive DPblock43589897545,SP43566292104,PHY43584735530,MBIST43588310054. PriorfailedCRCtimingandantennaevidencebelow remains valid for oldcandidateonly.

## CRC extracted STA rejected; captured diode failure now supports isolated legalization

43579643337 is terminalFAIL at strict acceptance. SafeSTA14111793410 SHA2b25292fffb06b73ac4d3f119c3a7c886edeefcaf7888c4c0ea0c58c4ad3f276. Slow569setup WNS-.799542677ns,1hold-.095417454; typ0setup9hold-.069170227; fast0setup122hold-.135881976. Slowviolations PCIe551,CPU15,async2,EthTX1. Fast holdPCIe115,CPU3,EthRX4. Cap96/103/108,slew550/227/119,fanout1363. Antenna565nets656pins stillopen despiteDRC0. NominalRC only, no production claim.

Diode capture43590389460/source9003dfcb3e85be38688357e0d9b823f46cd4d2f8 terminalFAIL as intentionally preserved. Runtime exactdcf36133... confirmed. DPLfails on ANTENNA_482/1342/457/458; native failed-stateODB and before/after statuses saved. Safe14112725149 SHA2769b547134d9c9b21793b3467bd198a9910031bf95fbaad5cd5cc212477cc7c; native14112241785 SHA5a745c683ff7e1adec765b3ef73ffb13ad21900f6e7567f5d7e9cdc663144176 cloudonly. No repeated originalroute needed.

Currentfour-diode trial43590951082/sourcef0c5230da39e88f6b8a30994015b7e09c911a8d3, branchcodex/crc-four-diode-legalization. Restore exactfailedDB, lock allothercells, only4diodes movable, detailed_placement-max_displacement1000x1000; allotherlocations/orientations mustunchanged, then restoreoriginalstatuses and requirecheck_placement. No subsequentroute yet; passingonlyplacementdoesnotcloseantenna/timing. Safe four-diode-derived-*;nativecloudonly. FullSTA+capture receipt docs/evidence/crc-routed-sta-and-four-diode-trial-20261114.json.

Live DPblock43589897545,SP43566292104,PHY43584735530,MBIST43588310054 remain separate. Do not pollterminalCRC43579643337 ordiode43590389460 as running.

## CRC jumper-only route finished but antenna repair failed; diode failure capture live

Run43579643337 route job132401417086 completed execution; fresh final check still565antenna nets/656pins, unchanged across5iterations. Routing DRC0 is not foundry DRC or antenna closure. Safe14111439322 SHA1e8a33fd24778a4212ad496f8a96a675d8cf28067e698d51ef4a5163997e2d85; native14111958544 SHA0c61942e79e1c94aceedd757e5d4cc298af6cbbe90480612c72bfed2fcbf18b0 cloudonly. DependentSTA job132432238364 is running; retain results for timing diagnosis but antenna gate already fails.

Source diagnosis: LibreLane3.0.5 pins OpenROADdcf36133...; GlobalRouter::repairAntennas calls jumperInsertion only if !haveDetailedRoutes, while jumper_only inhibits diode insertion. Explains ineffective post-DRT jumper-only loop; do not repeat. drt.tcl exact SHA matches runtime proof. Native version still to verify.

New diode diagnostic43590389460/source9003dfcb3e85be38688357e0d9b823f46cd4d2f8, branch codex/crc-diode-placement-diagnostic. Exact original checkpoint, no initial or subsequent detailed route. Capture repair_antennas -diode_only error, native DB and pre/post placement statuses; print runtime version. Intentionally non-accepting failure even on successful insertion; native archivecloudonly, safe route-crc_diode_diagnostic-*. Inspect actual failure before changing placement. Receipt docs/evidence/crc-jumper-ineffective-and-diode-diagnostic-20261114.json.

Still live: DP32cell43589897545,SP43566292104,PHY43584735530,MBIST43588310054. Earlier results below.

## Bitcell pairing rejected; parent 32-cell block test live

43589771694/source ef4dcd378344f01360ae663e53ca5ee2bdd2450e completed diagnosis in16.74s, native15/15 controls pass, strict LVSFAIL:25Match, bitcellNoMatch, topSkipped. Physical leaf6devices vs reference14; top recursive70110each unchanged. Explicit name mapping alone is insufficient. NativeDB14f60640f6a1a6fd60c75e265b2b360722ab294737a60fa45ab1fc0424d7b88b. Safe14111783729 SHA2cca92bd0da453cb30d8ae7639e03364e521ab0a4536f7a9dc837e8440ace385; native14112185339 stayscloud. No acceptance.

Current run43589897545/source ea8eef24283b7af4bd4e627330b104fc395af579, branch codex/dp-sram-explicit-block-pair, pairs only physical RM_IHPSG13_2P_BITKIT_16x2_SRAM to reference RM_IHPSG13_256x16_c2_2P_BITKIT_16x2_SRAM BEFORE align, to test parent boundary. Original GDS/CDL,strict checks,16 complexity bound and15 native controls unchanged. Not also pairing defective leaf. Safe dp-sram-block-paired-derived-*; nativecloudonly. See docs/evidence/dp-sram-bitcell-pair-rejected-20261114.json. Other live PHY43584735530,antenna43579643337,SP43566292104,MBIST43588310054.

## DP bitcell name mismatch verified; strict correspondence experiment live

Original GDS and engineered CDL hierarchy inventory43589227835 succeeded, safe14111637882 SHA320189ddd96027c6a03d6a848036f12410178b5f9cdd82ff4252b6d26769b3a4. Physical RM_IHPSG13_2P_BITKIT_CELL differs from reference RM_IHPSG13_256x16_c2_2P_BITKIT_CELL. Similar names alone do not prove equivalence. Pinned KLayout align flattens unmatched circuit names.

New run43589771694/source ef4dcd378344f01360ae663e53ca5ee2bdd2450e, branch codex/dp-sram-explicit-bitcell-pair, inserts exactly this one explicit cell pair BEFORE align with existence guards. Bounded16 and all original comparison controls retained; five extra native renamed-cell identity/width/open/missing/extra-device controls required. No nil mapping, blackboxes, net aliases, pin equivalence or waived checks. Safe dp-sram-bitcell-paired-derived-*; native archives cloud only. Do not integrate experiment workflow or claim LVS until strict audit succeeds. Full inventory/receipt in docs/evidence/dp-sram-prealign-hierarchy-20261114.json.

Other live runs unchanged: PHY43584735530; CRC antenna43579643337; SP LVS43566292104; MBIST continuation43588310054 from1.90Mcycles.

## SRAM search ambiguity confirmed independently; hierarchy inventory live

Run43588998602/source `ff22dfcd50ea2e51222dba28d98c08e16610138b` succeeded without loading CAD objects. Reads exact serialized DB SHA341e7da... only on cloud. Safe14111003774 SHA `abc6554fb3974ede597897234ff08275820dc7ef6102f3d3132a7ae068437a02`. 5752 exact embedded complexity-limit messages: most need32, some128/256, four need8192. Therefore bounded topNoMatch cannot alone distinguish structural defects from search exhaustion. Do not classify all mismatches as design errors.

Detailed native reader ALSO crashes in Ruby during DeepShapeStore destruction; not Python-only. Latest43588791834/source `dcee94349586376e569598b03de41f158d61bb56` staysFAIL, nativeRC6. Partial report preserved safe14111896618 SHA `52c360b1f7b6db6eb9ba63caded65ef3b85bfca3bfad2783e1b03eab04d2e7b2`; **not trustworthy acceptance evidence**, requires independent validation. Previous observer runs43587894664(API),43588102578/43588371410(Python GC),43588535934(Ruby) terminalfailure; do not poll/relaunch them. Report and failures in `docs/evidence/dp-sram-search-ambiguity-and-reader-failure-20261114.json`.

Live hierarchy inventory43589227835/source `e6682d1a15931a7c79a44423686f8a7f05eb1981`, branch `codex/dp-sram-prealign-hierarchy`. Reads original GDS cell names/instance counts and engineered CDL cell definitions in cloud; no LVS replay or correspondence assumption. Compare unmatched leaf names before considering explicit same_circuits; any mapping must retain full primitive and port checks, not blackbox/exclude cells.

Other live work: full native boot43588310054 from1.90Mcycles; PHY43584735530; CRC antenna43579643337; SP LVS43566292104. Earlier records below.

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
