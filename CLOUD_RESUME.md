# Current checkpoint: core output isolation candidate (2026-11-18)

Scope remains PCIe/Ethernet excluded; 50 MHz / 20 ns and 5 percent derating unchanged.
All physical execution is cloud-only.

## Preserve these core jobs

- Detailed core route 44337630426, execution head 19924a826cfca054f30f19cdde091fbe6c744960.
- Selected ECO native boot/system MBIST 44342916945, head 96acee7ce6afcf8c8692f58ceffa47afb905e6ab.
Both last confirmed running. Poll exact handles; do not restart because observation expires.
After independent route artifact admission, dispatch the staged core RCX workflow on
codex/core-only-posteco-extraction at b75792d10e647522ecb6c554a35906708d718c57
with verified route_artifact_id and route_artifact_digest. No core RCX result yet.

## Latest verified parent

56 perimeter buffers plus 14 residual-crossing buffers cleared all five targeted
native buffer paths. Parent route 44353658604 / b9f958703287713d4cff8adf98fd820bd63be945
has 2045 instances, 2019 routed nets, zero native route DRC and zero visible geometry
errors, with strict pre/post route identity. Artifact 14449707674 SHA256
c393deff70e3d24a33c4efea0362f9a3335e380f8d77f185de9ee2ea85708055; 27 outputs verified.
Actual nominal three-corner timing 44355961230 / 07fb3635e7e2fc98691d5a8056707a2cf153a81d:
artifact 14452736425 SHA256 85672c97a9d40da712b4fa0bc750f3e80d2d41f470d8099c239c1df2f58058d0,
30 outputs and protected sources verified. All remaining slew pins are pads:
51 slow / 39 typical / 27 fast. All 70 inserted buffers and ten original repair
endpoint buffers are clear. Parent timing is scoped, nominal RC and core blackbox.

## Actual hierarchical integration diagnostic

44355637027 / 5469259854713f227beab053940e28fe2f8f6b09 successfully linked the original
pre-ECO routed core and the 56-buffer parent using standalone STA, parent SPEF first
and child SPEF second. Artifact 14453721269 SHA256
e6eedd2bb5763bafbe6b6a6e1f3bf102b48bf5bffec51be2c4c1de5d903682ac; 13 outputs/protected
inputs verified. Typical worst max/min slack +6.709909439/+0.183034375 ns is NOT
current ECO closure. 1540 unannotated drivers split into 1403 core, 76 boundary
ports, 61 pad-cell /pad outputs; zero partial annotations. This split is not yet
a complete native cross-boundary coverage qualification. Missing input/output
delays: 73 each; unconstrained endpoints: 103. Four missing timing cell definitions
are Corner/Filler10000/Filler4000/Filler200; latest native master inventory confirms
only POWER/GROUND terminals, not signal pins. Preserve these as physical-only cells,
do not pretend they have transistor/ESD signoff.

## Next candidate on this branch

Inventory 44357611874 / 4b2996acaeee744fc8b31544a10448ad42a05c4c:
artifact 14453627328 SHA256 9ffea7f1cb2fae40bc9f85d141a19ab1f78c81ee6c00bb01d2f6829f8344635f,
12 outputs/protected sources verified. 79 core outputs directly feed pads; longest
actual routes approximately 5.8 mm. Real hierarchical analysis confirms the
resulting load also violates core output driver slew.

cloud_core_only_parent_corepad_repair.py now creates an isolation buffer near each
core output and at most 300 um planned segments along a rectangle outside the core.
All 2045 original instances must remain unchanged; buffer contraction must preserve
original connectivity and power. New cells must stay outside the core, within
100 um of planned placement; first buffer actual A pin must be within 80 um of
the core driver pin. Native execution and subsequent route/RCX remain required.
Find the dispatched run on codex/core-only-parent-corepad-repair; do not duplicate it.

GitHub HTTP 503 caused prior read-only source-download failures, not design failures.
New source readers have bounded retries; hashes, identities and constraints remain
strict. See docs/evidence/core-only-parent-and-hierarchical-measurements-20261118.json.
Qualified min/max RC, SRAM Liberty/internal LVS, external I/O/CDC, final actual
core-parent timing/physical integration and manufacturing approval remain open.

---
# Routed parent CDC path measurement

Read-only measurement against authenticated parent timing44314493056 and original shell mapping44268658068. It binds156 snapshot flops/162 flop-backed positions to actual routed parent terminals, preserving the30 zero-constant positions and the mapped-bit distinctions from the mapping; actual zero constants remain excluded from source-flop queries. Reports162 bundled-data max paths and max/min on four synchronizer chains at each of three native library corners using the exact nominal parent SPEF.

The original two20ns propagated-clock SDC is unchanged. This is measured evidence under those provisional phases, not asynchronous timing closure, metastability qualification, external IO qualification or complete-chip signoff. No false paths or relaxed budgets are introduced. Native execution still required.

Active core detailed route44337630426 and selected ECO boot44342916945 remain unchanged. Extraction runner stays staged atb75792d10e647522ecb6c554a35906708d718c57 on codex/core-only-posteco-extraction until detailed-route artifact admission.

---
# Packed diagnostic counter adaptation

Current next boot uses the exact authenticated canonical map SHA256a19e410fab8a15fb0337b4d0ccfd50704f08eba76828d5d5b59c5c28826c5187. The old u_scrub.cnt[0] and[2] observers are16-bit buses. OpenDB map stores separately escaped array-index names with bit suffixes; direct aggregate lookup was incorrect. Run44341250145 failed before simulation with KeyError(u_scrub.cnt[0]); artifact14444955350 SHA25690da2cfd1f5d55b9ca67f1bcfe640c9a9d37126267adbc1ea03c6ff18e71128c and both outputs verified.

New adapter requires exactly one mapping for each bit0..15, checks all32 scalar declarations, concatenates15 down to0 and proves inverse replacement exactly restores the qualified harness. Only the two progress-display expressions change. Earlier runs44340407734 and44341120096 failed Python syntax; final0661ebb syntax passed before this semantic lookup failure. Do not label any of these failed attempts a DUT failure or a passing simulation.

Detailed route44337630426 at19924a826cfca054f30f19cdde091fbe6c744960 continues unchanged. RCX runner is staged on codex/core-only-posteco-extraction atb75792d10e647522ecb6c554a35906708d718c57, not dispatched. Keep50MHz/20ns/5percent; PCIe/Ethernet excluded.

---
# ECO boot observer adaptation

Boot44339388679 failed at compile/elaboration (exit2), with no simulation executed. Source netlist b7323e4872a3c76b57c4bd88d64574e09619b22540a74006eb6ff2f767dfb834 is intact. Only errors: two old u_scrub.cnt[0]/[2] names in progress display no longer bind after canonical naming. Evidence is docs/evidence/core-only-selected-eco-boot-observer-failure-20261118.json.

Runner now authenticates the original canonical-name-map from44308129454 and translates exactly these two read-only debug references in the copied harness. It proves inverse replacement recovers the exact qualified harness bytes and verifies both mapped nets are declared in the selected netlist. No pass/fail conditions or DUT netlist modifications. New compile and complete native boot/MBIST simulation are required. Detailed route44337630426 remains untouched; extraction staging remains b75792d10e647522ecb6c554a35906708d718c57 on its separate branch.

---
# Selected ECO native boot running alongside detailed route

This branch boots the authenticated pin-aware ECO/global-route netlist from44328874040/head733cb000518b8bd6d95470fde5e6e3c3e32bafa6, using the previously qualified native core boot/system MBIST harness. It does not claim the later detailed-route netlist was simulated, does not applySDF, and does not prove formal equivalence. Detailed route44337630426 at19924a826cfca054f30f19cdde091fbe6c744960 continues unchanged. Exact pre/post route identity must pass to relate the selected ECO's functional result to the routed candidate.

Prepared extraction remains on codex/core-only-posteco-extraction atb75792d10e647522ecb6c554a35906708d718c57, not dispatched. Wait for and independently verify the detailed-route artifact, then supply its ID/digest to that branch's workflow. Do not dispatch the extraction workflow from this boot branch.

---
# Post-ECO extraction staged, not dispatched

Active physical job:44337630426 at19924a826cfca054f30f19cdde091fbe6c744960. Do not restart it. This branch stages `cloud_core_only_posteco_extraction.py` and its manual workflow. Wait for the exact routing job, independently verify its artifact SHA256, every output/source, DRC/antenna, identity and indexed geometry before dispatch. Supply route_artifact_id and route_artifact_digest (sha256: prefix) to cloud-evidence-summary.yml on this branch. No artifact pins exist yet because the job is running; no RCX result is claimed.

The runner restores pinned mapping/CTS/clock refinement, pin-aware ECO, global routing and the new detailed route. It validates exact105251-cell identity and physical geometry reports, admits canonical identifiers read-only, preserves20ns/5percent, runs nominalRCX and standalone three-corner nativeSPEF STA, classifies all unannotated drivers. No re-canonicalization and no inherited metrics. The new runner and name guard still require cloud execution. Qualified min/maxRC, full-chip timing and manufacturing approval remain open.

---
# Best measured ECO entering detailed route

Slew-margin GRT44335251268/head03a3ef19fa1f1b3af17b11b3760864f39da15641 completed. Artifact14442855156 SHA2563e0357758f81bd8a69c4ab3a9d25a11f9daaf257bc87a478a3bcb61173d81383:106 outputs and protected repository sources independently verified. All three corners retain zero setup/hold/fanout violations. Slow setup+0.0661107ns; fast hold+0.0338873ns. Electrical regression: slow slew16 (previous11), cap4 at all corners (previous1). New slow drivers63510/Y,63650/Y,63527/Y; caps79105/Q,78836/Q,SRAMbank1 A_DOUT12,78875/Q. Do not promote this six-buffer trial as closure.

Decision: detailed-route the better pin-aware candidate44328874040/head733cb000518b8bd6d95470fde5e6e3c3e32bafa6 (slow slew11,cap1,zero setup/hold/fanout), then fix using actual extracted RC rather than repeatedly perturb full global-route estimates. This is an explicitly incomplete measurement trial, not electrical acceptance. Existing antenna cells remain; enable jumper-only repair with all other config/constraints unchanged. Exact pre/post identity and indexed visible geometry audits follow routing. Nominal extracted RC/STA, full-chip integration and manufacturing qualification remain pending.

---
# Native route identity guard qualified

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44336120355 passed.
One positive native control and all six injected faults were verified: power disconnect, clock net type, signal rewiring, instance movement, missing antenna cell, and port type. 14 output hashes and four repository sources independently checked. Source had 105257 instances and 103091 nets. Evidence: `docs/evidence/core-only-route-identity-controls-20261118.json`.

Use `scripts/audit_core_only_route_identity.py` after fresh detailed routing. Qualified SHA256: e3de6a24b6a993082970527da2154933c32b4b39ab50342a435028439bf3ef02. Set NSSOC_CONTROL_BUFFER_OUT, NSSOC_ROUTE_IDENTITY_BEFORE, NSSOC_ROUTE_IDENTITY_AFTER and NSSOC_ROUTE_IDENTITY_OUT. This checks exact instances/status/masters, all terminal connections, net names/types, special wires, boundary pins and die. Signal wire geometry still needs the independently qualified indexed native geometry checker. This is not transistor LVS or manufacturing approval.

Global-route/three-corner job44335251268 at03a3ef19fa1f1b3af17b11b3760864f39da15641 remains active; do not redispatch or restart. Retrieve and verify its artifact before choosing next ECO or detailed route. No new detailed routing has been run for the six-buffer candidate yet. Latest retained general checks44336122484; superseded44335258780 cancelled only after ancestry/live-successor verification. PCIe/Ethernet excluded; 20ns/5% unchanged.

---
# Slew-margin candidate admitted for fresh global routing

Candidate run: https://github.com/Melihakbulut221/nssoc/actions/runs/44332978563
Source: 8412abee439a86f3821d6dae9d6220b78837754c
Artifact: 14440182673; SHA256 f560f6adb551cfb293557aa2fab3e2332c4ce42352d3faacacdcf664cc595849.
Candidate ODB: c1dfc3654fbd0849c494532fd60e80e23fe91611a97d180c7aba92e4e2fa5ab2.

Six buf4 additions; no original cell resizing. Native audit reports original geometry, contracted terminal classes, net signal types, power/pins, antenna cells and clock connectivity preserved. Archive digest and four protected repository source hashes independently checked. The new runner also validates all 13 output hashes and protected inputs before using the candidate.

Next: fresh global route and slow/typical/fast STA. Previous estimate had zero setup/hold/fanout violations but 11 slow slew and one capacitance violation. This candidate has no timing result yet. Preserve 20 ns and 5 percent derating. PCIe/Ethernet remain excluded. Detailed routing, extracted timing, full-chip integration and production qualification remain open.

---
## Slew candidate revised for actual library availability

Attempt44331913767 at3331cf10987fe2a7f1009e24b6cf49a250946cd4 stopped during preparation because sg13g2_o21ai_1 has no larger drive variant in the native library. Artifact14439871602 SHA256b93ee72763f0c67ca4f800e1ad8bd3ce37c54964fb93089ddbb24819889bb7c2 verified; no legalized/routed candidate resulted.
Revised strategy uses only six non-inverting buf4 cells: one isolates each of the four slew drivers; two split78908/Q load. No original logic master, placement, orientation or clock cell changes. Audit requires exact original geometry, terminal connectivity modulo new buffers, original net types, PG/pins and existing antenna cells. Fresh legalization and routing/timing required; do not assume electrical closure.

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
