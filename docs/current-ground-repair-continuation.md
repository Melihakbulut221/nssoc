## Current continuation: compiler ID collision corrected; first bias trial rejected; balanced divider trial dispatched

All native CAD, SPICE, waveforms, GDS/ODB and native archives remain GitHub only. Local workspace empty. Full serial Gen3 x4 PHY, routed mainchip and final setup/hold remain OPEN.

MAINCHIP actual full build41453866417 FAILED after2063.7seconds at87%: upstream message scanner found DRT9999 twice (new FlexDR guard and existing TritonRoute.cpp). Compiler exit2, no OOM, cgroup peak3717890048bytes under12GiB limit. Original release431499827 preserved; no binary was qualified. The passing lifetime fixture did not cover cross-file message IDs.

Cloud diagnostic41460346322/sourceb36fa4700d78c2b8a5145db94603126887d13052 succeeded, authenticated entire failed archive and retained complete logs. Derived13147914267=77579bytes SHA56f4602691b66d161598bd4dd8962e8cb6392a755c6172813683edf9a2645c17. Its full selected text is stored here.

CORRECTION source851db8f517c03cffd0afeb6527e281bd9353f5d2: only new guard ID9999->10000, next free reported by actual scanner; worker accounting guard9998 unchanged. FlexDR derivedSHA892a9771d911cf8ed350ffe4d42683b16561f3989f1e7c8302a02f8016328d9e,78757bytes. Bounded two live workers, guides, geometry, cost and original full64 schedule unchanged. Source controls41492927619 SUCCESS: all old engine7positive/45refusal/25lifecycle and observer4positive/29refusal,9compiled lifetime cases retained. Exact pinned upstream find_messages.py now scans both actual derived C++files plus observer header; corrected version passes and prior duplicate-ID version is rejected. Whole actual DRT directory preflight is also required before compiler-container creation; original upstream build check remains enabled. Source-check three-file scope is not whole-engine qualification.

NEW COMPLETE ENGINE BUILD41493369685, same source851db8f5, branchcodex/mainchip-guide-batch-engine, release431773741/tagcloud-results-41493369685-1-mainchip-guide-batch-engine-build. Follow this exact handle; do not restart on observation timeout. After successful build/interfaces, qualify new binary on actual recovered chip and all protected clock/wire scopes before full64 routing. Current chip evidence remains92DRT (64short28spacing),21antenna nets,1691protected clocks unchanged. No new route/STA improvement has been measured.

PHY first provisional pull-up-only experiment41458294059/source4bc8aa4117cb603155e4d03bcd00c69c7d6ee943 is terminal REJECTED_WHOLE_MIM_PD500_LOADED. Native transient return0, sourcesunchanged=true, complete34.25ns/113475rows/1152columns raw1,045,823,299bytes SHA1370699f6fbd8523743afd942fceee845a82f4f014e08de075f199a71b1a971d. Full native release431531665 retains four parts and complete index. Derived13148519767=1409362bytes SHA1aaf64b5b67ca623db80c4a33f18271790ae0904b662c38b38575d7ae58dbf93; complete measurement and provenance copied here.

Compared with unchanged physical parent41441047354, four critical Vce values rose from(.342697,.339778,.370967,.369198)V to(.396086,.393141,.416315,.413390)V. C now passes0.4V for its two critical devices; D still fails. Phase14.18547mV<30mV and VI42.66045uA<50uA remain failures. Sampler A/B/C/D maximum clock-to-valid45.78125/41.71875/118.90625/54.21875ps, limit37.5ps; C previously51.09375ps worsened. Wrong signs0/0/0/33, below100mV129/128/128/128of765. Do not promote pull-up-only trial to physical layout or acceptance.

NEXT BALANCED TRIAL41494299114/source df723c791fec2621585c80fb56409d65b5811b44, branchcodex/cdr-sampler-balanced-bias-trial, release431779366/tagcloud-results-41494299114-1-cdr-sampler-balanced-bias-trial. Independent controls41493968467 SUCCESS, artifact13165312239=1338bytes SHAd383b888f1d9753f34c3ebb13aa3112ad7c4ccb9512e24a59a4e0de67840c640. Original29numerical definitions/5blocks/9files/13admission refusals plus6card refusals and both parameter shapes retained; actual13binding and2equivalent-unit controls still required.

This experiment starts from unchanged authenticated collector Via2 freshRC41439516945, not previous trial. Actual mapped pull-ups182/183/220/221 change L1.8->1.75um,W8 unchanged; pull-downs184/185/222/223 change L5->6um,W4 unchanged. First-order sheet-only normalized parallel resistance0.190677966->0.190909091 (+0.1212%); supply-divider fraction0.847457627->0.872727273. Hypothesis: raise common-mode while retaining differential load/gain, unlike previous14.49% normalized resistance drop. This estimate ignores contact/bias/capacitance effects and is not measured PDK resistance or expected success.

Both trials explicitly use fixed parent interconnect RC with modified primitive dimensions; matching_layout_verified=false and fresh_RC_for_modified_devices=false. New trial preserves other492devices, all interconnectRC, all original externalclock/stimuli/loads/gates/fullwaves and requires exact model/contract reversal. No new analog geometry generated. Even numerical success needs actual schematic/GDS regeneration, DRC/LVS, canonical matching, freshRC and original loaded verification; full-loop/PVT/ESD/EM/PCIe integration remain open.

Readonly8hour monitor keeps automatic_native_dispatch=false. Next: collect both current native results, diagnose actual failure/success, maintain same handles until terminal; never equate fixture/build or provisional circuit improvement with fullPHY/production/timing acceptance.

Observed at 2026-11-02T17:49:05.888877+00:00:
- 41453866417: completed/failure
- 41460346322: completed/success
- 41458294059: completed/failure
- 41492927619: completed/success
- 41493369685: in_progress/None
- 41493968467: completed/success
- 41494299114: in_progress/None
