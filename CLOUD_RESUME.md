# Cloud continuation — checkpoint v235

Updated: 2026-11-01T10:31:28.804048+00:00

All CAD,simulation and native payloads stay on GitHub. Local project directory and project-prefixed temporary entries are empty; no CAD processes are running locally. Source/API text coordination is in RAM only. User unrelated files remain untouched.

PD650 twelve-divider trial41295928971 completed and was rejected by original electrical gates. The simulator exited0 without diagnostics and device gates passed; all six sampler/comparison gates failed. Phase improved to29.329mV but remains below30mV. Full terminal proof: 19d07ce5f55be3d0c09014f56df9e76a51c9aa1a at docs/evidence/divider-drive-native-terminal-41295928971. Do not present this as full PHY closure or automatically repeat the same trial.

Mainchip routing41292673925 must be observed at its existing handle. Preserve the v234 restart caveat: an ODB is not proof of persisted optimizer state; inspect actual restored output and residual violations before another repair. Full serial PHY,routing and final setup/hold are still open.

Eight-hour monitor stays read-only with automatic_native_dispatch:false.

## Previous continuation records

# Cloud continuation — checkpoint v234

Updated: 2026-11-01T10:22:04.726263+00:00

Important continuation correction: an exported ODB is not proven to persist TritonRoute optimizer/iteration state. Do not implement repeated8-bound calls as equivalent continuation. See docs/mainchip-routing-restart-review.md and exact-source review evidence. Authenticate restored candidate and source/fallback flags first,then derive actual residual-owner repair or separately qualify the restart. Four raw route files precede class restoration; never infer preserved clocks merely from their existence.

Existing cloud jobs remain41295928971(PD650 trial) and41292673925(mainchip route). Observe those handles; no duplicate dispatch. Full serial PHY,routing and final timing remain open. Local native execution remains prohibited by latest user instruction.

## Prior continuation record

# Cloud continuation — checkpoint v233

Updated: 2026-11-01T10:08:14.357865+00:00

All numerical tests,CAD,simulation and outputs remain on GitHub; local workspace and project temporary outputs are empty. This overrides the old local-work goal wording.

PD65012-divider trial implemented on branch codex/cdr-divider-drive,source 3a6f1f9e3b30f97ffae87f43cf0f7f00e2d2ab43. Original gates and200MOS are retained. Source-controls41295792666 passed all inherited checks plus75 divider corruptions and6 independent ratio checks; complete proof 29ca141af33df09b69c320ccdceb92ae1bbc3c63 at docs/evidence/divider-drive-controls-41295792666.

Native simulation41295928971 was dispatched against the same source. Independently reserved and read-back exact-source release430496244,tag cloud-results-41295928971-1-cdr-sampler-load. Observe this existing handle; never redispatch merely because it is still running. Actual electrical result is not yet accepted. See docs/cdr-divider-drive.md.

Mainchip stage1 run41292673925 remains the routing handle; terminal status and actual checkpoint content must be authenticated before follow-on continuation. No final routing,timing or serial PHY acceptance is implied.

Monitor inventory645 runs;8-hour monitor stays read-only and automatic_native_dispatch:false.

## Prior checkpoint retained for remaining full-scope work

# Cloud continuation — checkpoint v232

Updated: 2026-11-01T09:54:59.949118+00:00
All tests, CAD, simulations and numerical/geometry analysis execute on GitHub. This explicit instruction overrides the older local-work goal wording. Local project and project temporary outputs stay empty. Source/API-derived text coordination uses RAM only; no native archives/models/SPICE/ODB/GDS/raw waves are acquired locally.

Latest diagnostic progress:
- Complete-wave reproduction41293861314/source46319d4691e2b06a193ebf47984b40256800fa41 passed29 controls and reproduced all6 original failures and phase19.616mV. Full22proof198ac19f2ffb0a2d853936ee31f7951c06d673b5.
- Native-node buffer diagnosis41294574040/sourceabd8ec54a53e615dd9384a287f6690fd9130440f also passed29 controls; full23proof5d32ba3ace05084b64cc1c1766c8ff19fa84908d. At0.9UI, A/C/D sources are already>=100mV but their downstream buffers still have77/43/89wrong-sign samples. X active positive peak75.144mV never reaches100mV. The selector already usesretimedD viaR234-237, so no speculativeB-toDrewire.
- See docs/pd650-buffer-lag-diagnosis.md. Next explicit hypothesis: halve both legs of A/CdividersR227-230/R238-241 from1.8/10.8to0.9/5.4um and DdividerR234-237 from6/8.6to3/4.3um,w1um. Exact12IDs in v232 proposal. NOT YET GENERATED/SIMULATED. Preserve original gates,200MOS and all other model/RCbytes; after actual electrical result update geometry/freshRC separately.
- Initial cancelledreader41293342915 and list-type failure41293436380 are preserved in13/17-file proofs71e233ec0651b3062bcd0aaf69a1c5b870f1fc48/1777bacdebf3e371acd5a8ac0b485267f2b4cce3. No simulator rerun in these analyses.
- Three duplicate proof-ref CI attempts cancelled with originals retained; cancellations are not test passes. Future proof publisher must build its final [skip ci] commit FIRST, then create the branch directly at that commit. Never create an intermediate ref at the tested source, which triggers redundant generalCI.

1. New mainchip source **7a0776718ec37a106b7dfde0cbd477c6a2a5522f**, branch codex/mainchip-net459-diode-prune, shared workflow cloud-evidence-summary.yml. All inherited files including old workflow remain byte-identical. Original 64-iteration environment contract is retained; the actual router argument explicitly uses8 iterations for intermediate stage1 only. Existing828-owner/1351diode/1691protected-record and final DRC/antenna/connectivity/timing predicates remain. No checkpoint or final physical result is inferred from source controls.

2. Controls **41292181207** succeeded:12 new source/lifecycle tests plus all inherited controls including165 saved-diode audits. Full controls proof 6c2918b9134a61734e315f6291302655c9ddb9db, prefix docs/evidence/bounded-route-controls-41292181207. Native job **41292673925**, exact-source independently reserved release **430474717**, tag cloud-results-41292673925-1-mainchip-bulk-postdrt-antenna. Observe that same run; do not duplicate it. Supplemental source manifest has2361 exact files. See docs/mainchip-bounded-route-stage.md.

3. The new stage writes actual pre/post route Tcl and hashes all four returned route-partial/routed-fixed DEF/ODB files. Failures and available partial output remain failures. Validate the actual terminal native report, complete streams, protected records and publication. Follow-on stage2 must authenticate and resume the resulting checkpoint without repeating the initial stale-wire clear. Stage2 is NOT implemented yet; no internal TritonRoute optimizer-state resumption is claimed.

4. Original run41270471645 is TERMINAL TIMEOUT:14400.811145697s/-15/elapsed_limit. Full23proof de4e92bc723d6885c3c800aa5c9676f7495f9a4a; full native route readout41290408993/full19proof e19b8a246accee5125c14291b6effd46b94249ad. Last complete iteration26 had129 intermediate router violations;27cut at40%. No optimized ODB saved.1691 original clock/fixed records restored exactly. Do not repeat the old64iteration lost-progress run.

5. PD650 transient41288195752/source d638e0e3cd15a0ee930212c27ab1f238b5085237 is TERMINAL ELECTRICAL REJECTION. Actual engine0,1037.382s,zero diagnostics; all device gates and VI pass but six A/B/C/D/X/Y data stages and phase fail. Full115proof6fdf10cd1683b920950104e7edb6206865eab78e/native release430445706. Original1301vector capture and all raw rows remain cloud-only. Use waveform-led valid-domain drive/load repair; do not revert42MOS to unsupported wide model instances. See docs/cdr-mos-parallel-loaded-simulation.md.

6. Actual four physical MOS unit widths8/9/8.890/8.885um,L.3um,ng1 are qualified in41290670037/sourcee3839b66d23c4cd678e4cf917c3b458495f4ac96. All20native stages passed: four560-category zero-DRC results, eight deep/flat2device unsimplified LVS matches, exact W/L/AS/AD/PS/PD and all8negative controls rejected. Full119proof6e9362d5c95e1c2b2fca62d9c71aec8ac4e099e4/release430461761. Do not rerun this qualification. Prior hostPython/inspector failures remain preserved in v230. Integrate200qualifiedMOS units/50origins while preserving450nonMOS devices and original221tap design; do not blindly add200newtap wrappers. FullPD650 layout/freshRC still open. See docs/cdr-four-mos-unit-physical.md.

7. Gates unchanged: UI125ps, samplers100mV/37.5ps, XOR100mV/75ps; HBTminVCE.4/maxabsVCE1.6/maxabsVBE1/strictIc-emitter<3mA; MOS<=1.32V/activeVDS>=0/nonnegativeunitcurrents/16instantaneousstage-sums>=.5mA; sevenMIM<=1.6V; phase30mV; PLL62.5ps. FinalSTA20/4/8/8ns+5%,3PVT,zero setup/hold/transition/cap.

8. Mainchip remains packet-interface SoC, not full serial PHY ownership. Actual PLL/CDR/SERDES, fulltraining/LTSSM, lane mapping, descrambler/TX and serialsoc_top integration remain open. Authorized spec access request already pending; do not repeat it.

9. Local project and project-named temporary directories were rechecked empty; no CAD process. User files/shared apps preserved. All changes and evidence live on GitHub. Inventory 643 runs. Eight-hour monitor stays read-only automatic_native_dispatch:false. Full serial PHY, routed serial-integrated chip, final setup/hold and production acceptance remain OPEN.
