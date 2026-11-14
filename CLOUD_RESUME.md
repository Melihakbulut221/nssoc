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
