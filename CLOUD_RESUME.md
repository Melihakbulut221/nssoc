# Cloud continuation — checkpoint v241

Updated: 2026-11-01T12:29:29.344125+00:00

Latest user instruction: all work in the cloud; leave no local project data. It overrides the older goal's local-work wording. All native acquisition, CAD, geometry analysis and simulations run on GitHub-hosted runners. Local coordination is source/API-derived text in RAM only. Do not acquire native archives, ODB/DEF/GDS, transistor models or waveforms locally, including RAM. Workspace/project temporary entries are empty, with no native CAD processes.

## Concurrent native PHY experiment: inspect the actual result
New divider-width simulation run41306148937, source2a62d651d415fba8db3c5b758d1b66c05cde3a38, branch codex/cdr-divider-width, release430565351, tagcloud-results-41306148937-1-cdr-sampler-load. Native result is PENDING at this checkpoint. Independent controls41305872219 passed75 new mutation refusals, all original75 divider controls and original compiled binding. Complete54file proof42d94ed9d46a7bb1286c8dc7c344acd15e2be662 is imported under docs/evidence/divider-width-controls-41305872219. Native dispatch occurred ONCE after full proof readback and independently reserved/read-back empty exact-source release.

The candidate starts from actual twelve-divider parent modelSHA2560a2ce363d3f8159a290f8642fe3a26c7ac1997ca4d8b934e4530fb4823974ef3. It changes ONLY widths1um->2um of12rppd IDs227,228,229,230,234,235,236,237,238,239,240,241. Every length,physical terminal,HBT Nx,200MOS unit and other model byte remains unchanged. Rejected40-HBT trial is NOT retained. Original device/VI/per-emitter current/data/phase gates and compiled prepare/measure code remain unchanged.

Evidence for this experiment: corrected reader41298781054 reproduced the original native measurements. At0.6UI, all255A-source samples meet100mV but65divider outputs and107buffer outputs still have wrong sign; D has255valid sources but92wrong divider outputs and112wrongX-selector buffers. Lower divider impedance is a targeted hypothesis, not a claimed repair. Model parasitics/loading also change with width; actual full simulation decides. Existing wireRC is exploratory only; regenerated layout and freshRC remain required after electrical acceptance.

After terminal, preserve complete controls/derived output/logs/source and authenticate release index/parts WITHOUT downloading native parts locally. The exact ready collector sources are stored in docs/evidence/cloud-collector-recipes-20261029/cloud-divider-width-v240.json, collectors.mainchip_scoped_restoration and collectors.divider_width_native (the latter has this run/release already substituted). Run only against terminal status; failures are evidence, never acceptance.

## Final timing integration finding from source review
Do NOT feed the new1351-diode candidate into the old route12 controller unchanged. Its geometry admission requires153130 retained instances and added_diode_count==0; the worker pins the pre-diode resized netlist3c053c4c... . After actual scoped restoration succeeds, qualify a new exact candidateODB/DEF and matching diode-inclusive netlist boundary with full original functional connectivity,1691clock proof,all1351diode pins and2702PG contacts. Preserve all original numerical RC/STA code and20/4/8/8ns+5percent/three-corner decisions. The old numerical worker already keeps physical and timing acceptance separate; failed measurements may be retained without normalizing them to a pass. Nominal RC remains insufficient for foundryRCmin/max. See docs/mainchip-restored-route-timing-handoff.md and its exact source-fingerprint receipt. This review did not execute STA or RC.

## First next task: read actual scoped restoration native result
Scoped restoration is IMPLEMENTED on branch codex/mainchip-scoped-restoration, sourcebe65a271b066faeffee86237fa879f5f96b70273. Native run41305082558, release430558340, exact-source tagcloud-results-41305082558-1-mainchip-bulk-postdrt-antenna was dispatched ONCE after independent controls41304921000 and an empty release reservation/readback. Inspect the actual run and preserve terminal evidence; do not redispatch blindly. Native completion is NOT established in this checkpoint.

Controls41304921000 passed34 synthetic full-scope class/geometry/connection/census mutation controls plus all2361 original source pins. Three derived JSON inputs are authenticated and materialized on the cloud runner before the original source gate. Failed full controls41304415754 stopped before native acquisition because these inputs were missing; complete failed logs/source are preserved. Preliminary controls41303653373 passed34. All51 proof files for these three runs are imported.

The scoped core retains all828 current routed-owner records and their connections, validates608antenna/220counterpart/1691protected/1351diode ownership, and restores only other original temporaryFIXED classes with the unchanged original function. It requires complete unchanged selected records outside routing ownership, exact net order, net census and outsideNETS bytes. Actual native143820-net result is pending.

The adapter authenticates all728 archived producer members and materializes only11 required saved inputs. It uses original OpenROAD ELF/runtime/container and source7a0776718ec37a106b7dfde0cbd477c6a2a5522f. Original Tcl import renderer, metadata-only change validator, native snapshot,1691clock gate, expanded828route and two connectivity modes,1351diode checks,2702PG contacts and finalDRC/antenna readers remain required. Sequence: restore-plan,restore-import,restored-audit,power-contact-audit,final-check,final-audit. No current routing, repair, stale-wire clear or diode reconstruction calls.

Observe source/runtime/current/saved-input integrity, cgroup/engine return codes, all original terminal audit outcomes, complete native release publication and fallback artifact. A successful experiment may still report DRC/antenna violations; retain original bounded_cycle_qualified and all acceptance flagsfalse. Do not call an imported/restored candidate final routed/timing/PHY closure. If a phase fails, preserve its source/logs/result and fix only the evidenced cause.

The actual precursor diagnosis41302468053 compared all143820nets: exactly220counterpart normalized geometry/class changes, zero changes outside their scope, zero connection-prefix changes, same order and outsideNETS bytes. Original map143212records:142878FIXED->FIXED,220FIXED->ROUTED,114unwired->unwired. The inherited strict restorer rejected only these220 authorized counterparts because restore-plan lacked the scoped adapter. Full diagnostics remain in docs/evidence/route-class-native-terminal-41302468053;91.8MB per-record catalog remains only on release430540422.

## Saved route to reuse, not reroute blindly
Producer41292673925/source7a0776718ec37a106b7dfde0cbd477c6a2a5522f completed FAILURE. Release430474717/tagcloud-results-41292673925-1-mainchip-bulk-postdrt-antenna contains the complete native archive. The bounded router returned and saved all four raw DEF/ODB checkpoints. Last router count397DRC; restored/final audits never ran.

Raw routed-fixed.odb / route-partial.odb:214409779bytes,SHA256b87a2d43fe33dd8ca99f0faa2bdf38337ae30d6c5b72a337472919ac57f64e63.
Raw routed-fixed.def / route-partial.def:186123105bytes,SHA2560ac5108f828158156a858086a2edaff204020a14e17cb491d0ab173131345511.
Pre-route fixed.def:185488886bytes,SHA2569f28be4140f481886d501b26370ffcd431ceb8a436de1aff0946ee39573456d5.
Full archive751995332bytes,SHA256136e2aaa710f7e51c2ed31ef42054309a7c2c13be7a85e2d849db8cfbeaf436f; all728members authenticated by actual reader.

Actual native class restoration readback and397DRC remain open until the current result is inspected. A saved ODB proves retained geometry, not persisted TritonRoute optimizer history. Qualify further routing against the restored snapshot; do not blindly repeat all828 stale-wire clears. See docs/mainchip-routing-restart-review.md and docs/mainchip-bounded-route-terminal.md.

Initial reader41301914645 stopped before DEF comparison because it incorrectly expected828 entries in the608-owner antenna plan. Failure proof750b7c23d9decb159d3d3290bb101c4765c666b7 is preserved. Initial controls41301583231 failed on an unwired-only synthetic fixture that omitted the original restorer's required wired replacement; corrected22controls41301770098 and later26controls41302309403 passed. All failed evidence is retained, not reclassified as a pass.

## PHY latest attempt is rejected; no native PHY run is currently active
HBT-load native41299745896/source12f3e0f3bf7010289dc0f993ac71dbfa55cc19e4 is TERMINAL REJECTION. Engine0,1059.425s,zero diagnostics; original device and VI gates pass, all six data stages fail, phase20.883396mV fails30mV. The40-HBT Nx reduction made phase worse than the divider parent's29.329406mV and increased X/Y wrong-sign counts to420/34. Do not carry it forward as an accepted electrical or physical candidate. Full113fileproof221c55f256afab55630d4e8cb1903ab4e1b3d942/prefixdocs/evidence/hbt-load-native-terminal-41299745896; native release430521829 remains cloud-only.

The previous12-divider/200MOS parent41295928971 also remains rejected. Golden parent modelSHA0a2ce363d3f8159a290f8642fe3a26c7ac1997ca4d8b934e4530fb4823974ef3. Native proof19d07ce5f55be3d0c09014f56df9e76a51c9aa1a. Next analog work must use actual waveform/current evidence to address sampler and downstream delay; no limit relaxation or unsupported single-wide MOS return. Corrected reader41298781054/sourceeb9b2602db8d971e405310142ab88d3fc652d308 reproduced original measurements with33controls. Its earlier phase-loop-variable bug in41298254630 remains rejected and preserved.

Four actual MOS unit widths8/9/8.890/8.885um passed20native stages in41290670037:four zero-DRC,eight unsimplified deep/flatLVS,exact junction parameters,eight negative controls. Proof6e9362d5c95e1c2b2fca62d9c71aec8ac4e099e4/release430461761. This does not prove the whole650device layout/freshRC. Preserve original221taps; do not blindly add200tap wrappers.

## Unchanged acceptance and full remaining objective
UI125ps; samplers100mV/37.5ps; XOR100mV/75ps. HBTactiveVCE>=0.4V,absVCE<=1.6V,absVBE<=1V,strictIc/emitter<3mA using actualNx. MOSterminal<=1.32V,activeVDS>=0,individualtailcurrents>=0,sixteenstagecurrent-sums>=0.5mA. SevenMIM<=1.6V; phase>=30mV; PLL62.5ps. FinalSTA20/4/8/8ns+5%,threePVT,zero setup/hold/transition/capacitance violations.

Full serial PLL/CDR/SERDES,training/LTSSM,replay/credit,lane mapping/descrambler/TX and serialsoc_top ownership remain open. Packet-interface SoC layout is not full serial PHY integration. No production/silicon/radiation approval. Authorized specification access request is already pending; do not repeat it.

Use separately successful same-source controls and independently created/read-back empty exact-source release before native acquisition/dispatch. Never blindly retry dispatch or publication after timeout. Proof branches start at their final[skip ci]commit. GitHub's whole-repo recursive tree listing now truncates; use bounded subtree traversal and compare imported subtree Git hashes.

Inventory661runs. Eight-hour cloud monitor remains read-only,automatic_native_dispatch:false. Full objective remains ACTIVE and UNFINISHED.
