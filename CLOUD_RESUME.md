<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# NSSOC cloud continuation — 13 October 2026

## Controlling request and scope

The user requires **cloud-only execution**. The local workspace is empty.
Do not clone the repository locally, restore local CAD, run local tests, or
retain local artifacts. Use GitHub API metadata/source edits in memory and
GitHub-hosted runners for all native work. Repository: `Melihakbulut221/nssoc`,
branch `codex/complete-open-work`. Never force-push or blind-retry a mutation.
On uncertain publication, inspect the remote ref before proceeding.

**Full serial PCIe Gen3 x4 PHY, assembled main-chip PCIe/Ethernet route and
final setup/hold remain OPEN.** Compact/4:1 component gates do not prove a
32:1/x4 PHY, actual PLL/CDR clocking, ESD, qualified RF/substrate PEX, or chip
production acceptance. Main-chip packet-interface work is a separate scope.

The previous long continuation log is preserved unchanged at
https://github.com/Melihakbulut221/nssoc/blob/a45de762a05b9625fe9308aac90805544988c81d/CLOUD_RESUME.md
and all immutable results/failures remain in Git history and release assets.
This concise checkpoint supersedes stale running/pending statements there.

## Active physical candidates: inspect these runs before dispatch

| Work | Exact source / runs | Verified boundary and next action |
| --- | --- | --- |
| Short selector buses on unchanged v8 | Physical38452058065, extraction38453131275, composition38453569616 | All native physical/RC/composition gates passed. Loaded nominal38454523127 andhot/cold38454526301 completed ona45de762a05b9625fe9308aac90805544988c81d. Fiveof six engineering screens pass; hotwire fails128early samples, minimum20.841388mV. Allsix retained inpcie-final-v8-low-selects-loaded-tree-20261013.json. Native paired diagnosis is next; no adoption. |
| Nx3 data-bank v10, original low-critical buses | Nominal38452808927, hot/cold38452812892 on7f95123097589d5edb304e9c0cdde52720a8ac2b | 6captures retained; complete=true; failed cases=[('hot_low', 'physical_wire')]. Check exact receipt before adopting anything. |
| Main-chip alternative net ordering | 38448901835 on c19fc8b4c72e4db8ad20d6132ad73153f1ef856b | Latest live readback: in_progress/None. Seed13, capacity perturbation0, exact135-overflow buffer placement. Preserve native result; detailed routing/extraction/final STA still required. |
| Bounded-save32:1 nominal | 38441895491 on26e3692a27cb4aea7faa877b8df3388ddc06024d | Latest readback: in_progress/None. Compact passed; extracted-wire companion must complete. Do not restart a live job after observation timeout. |

Source/model/geometry/original-bit/license checks38454282998 PASSED before
launching the short-selector loaded runs. Earlier v10 binding checks
38452484468 and receipt checks38453573552 also PASSED.

## Exact analog evidence and unchanged limits

Both current4:1 candidates use `cascade158_kelvin_supply_direct` prestage,
`stiff65` native clock common-mode reference/feed and matched compact/wire.
Original256source bits,768samples at0.3/0.5/0.7UI, output100mV, interfaces150mV
and1.8..2.05V common-mode remain fixed. All native HBT/MOS limits, zero-start
OFF flags and simulator diagnostics remain gating. No phase-fitting or RC
scaling. Differential clocks/intermacro connections still have ideal parts.

- **v8 low-selects** changes only actual sp/sn TM2 buses to y32/40um. Native
  physical passed560DRC categories/zero markers, strict54-device hierarchical
  andflat LVS andfive actual physical/reference fault controls. FreshRC passed
  all13corruption controls. Composition has54devices/4043R/2661C.
  `docs/evidence/pcie-final-v8-kelvin-low-selects-composition-20261013.json`
  binds archive6675045bytes/SHAf591bc98448db872b00d8d0b7c2c2f7aa27625908e265f7431a98008dc10a3b6
  andsummaryasset638003525/SHA91b3d4ce252c81e4c28b06b081d8ba10e05a3f91106ec3211a7d9ffdb9e84d14.
  Do not substitute old low-criticalRC. Profile: `v8_kelvin_low_selects`.
- **v10** changes only twelve data HBTs toNx3; four selectorsNx6, two tailsNx8
  andreferenceNx1 remain. Physical38450309882/extraction38450839520/composition
  38451600151 passed native gates with54devices/4041R/2659C. Profile:
  `v10_kelvin_low_critical`; distinct composition receipt and
  `docs/evidence/pcie-final-v10-loaded-tree-20261013.json` preserve all completed
  captures. Threecompact andnominal/cold wire gates passed; consult hot result.
- **v9 rejected:** Nx2data improved hotwire minimum17.694to41.723mV but still
  failed110early samples. Coldcompact also failed12HBT VBE/current limits
  (maximum1.021886V/3.676749mA). Allsix captures remain in
  `docs/evidence/pcie-final-v9-loaded-tree-20261013.json`; no selective adoption.
- **Native delay diagnosis38451366659 passed:** summaryasset637967168 SHA
  024328b471f0d1ee06476f080849621df84af4d17bd1c1a593f620d9393058c6. All128changing
  bit events unambiguous. Compact/wire clock-toMUX-zero median8.606881/19.656687ps;
  MUX-toTX-zero5.956289/6.178540ps. Source-to100mV median26.362079/39.053899ps,
  wiremax41.441851ps versusfirstsample37.5ps. This motivated selector routing;
  it does not already prove the new geometry works. Hot pair receipt:
  `docs/evidence/pcie-final-v9-hot-loaded-tree-20261013.json`.

If short selectors pass, expand unchanged independent HBT/resistor/MOS corners,
quarter-step numerical agreement and actual physical faults, then full32:1
andphysical clock/tree integration. If they fail, preserve/read exact events
before selecting another geometry. Do not combine sizing/geometry changes
without measuring their separate effects and then retesting the combination.

## Main-chip route and timing evidence

The seed13 trial must reproduce placement SHA
660692b3e59756186bb017a62823999db593fa9d77b6e4181be9625fa7bfb707.
Pre-route asset637931919/SHA8db957ba8f6b07fd0cc12e31df23d0f6925306f3b7c96310ab9ff646676f7a7e
reproduces that exact placement and prior timing. Estimated slow setup is
still negative (PCIe -1.275681ns, system -0.589711ns); fast hold also negative
(PCIe -0.065767ns, system -0.054434ns). These are pre-route estimates, not
signoff. Same cells, SDC, PDK RC/capacity adjustment andzero-overflow gate.

Previous priority30 run38420407838 is terminal GRT-0116 failure, not live:
153layer overflow (M3=21,M4=16,M5=107,TM1=7,TM2=2). It was native max-overflow
attempt termination, not elapsed timeout. Failure receipt:
`docs/evidence/cloud-critical30-buffers-route-failure-20261013.json`.
Diagnosis38443872244 has113markers/155summed marker overflow/933nets; marker
andlayer totals are different native reports. Asset637840399. Prior same
buffer placement had135overflow; broad endpoint move produced420 andwas
rejected. Do not repeat unchanged rejected candidates or waive physical gates.

## 32:1 capture, publication and local retirement

Original32run38440472079 failed wire allocation (42.522GB reported). Oversized
save-command risk was fixed with bounded128-vector commands; its contribution
to that original failure still needs actualnative-log verification. Do not
assert causality from the memory warning alone. Corrected32run38441895491
compact has604native OFF flags,69541wave rows, complete original engineering
gates andzero diagnostics. Exact summaryasset637874261/SHA
 e9423a26a42909dfeb088124e76e072f7701fcc6f37c617dd9c8eadd381739d8 is bound by
`docs/evidence/pcie-bounded-save32-compact-20261013.json`. Wire remains separate.

All native artifacts are retained in immutable GitHub releases, including
failed cases; never label workflow success as electrical acceptance. Migration
finished with `COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE`; do not
redo retirement or restore local CAD. The8hour cloud-only automation remains
the continuation mechanism. No full goal completion or production approval.


## Latest cloud-only follow-up

The empty local workspace and absence of local CAD processes were rechecked.
Low-selects hot wire has zero wrong-sign samples but128below100mV at0.3UI;
later0.5/0.7UI samples and all HBT/MOS limits pass. Shorter selector buses alone
do not close the amplitude failure. Preserve the compact/wire pair in
pcie-final-v8-low-selects-hot-loaded-tree-20261013.json; diagnosis workflow
study v8_low_selects_hot reads exact original archived waves with unchanged
bit oracle and thresholds.

cloud-migration-checks.yml with timing_readback=true restores the archived complete native STA
log/Tcl from run38371498733, verifying archive size/hash and both member hashes.
It publishes a small full-path log for setup/hold inspection while seed13
routing continues. It does not rerun STA or claim routed timing closure.

The new standalone readback workflow was not registered on the default branch
(dispatch404, no native run started). The readback job now uses the existing
registered cloud-migration-checks.yml workflow with timing_readback=true.
Low-selector native diagnosis38457021311 completed successfully on873a6350ca13c5d98981214033bc5b0af33d0add.


Native short-selector diagnosis38457021311 PASSED. Summaryasset638065261, SHA
acf780035a06b3be15e51beca4f7b9fa4360edf8f0d85a9d3a8926ccc0d64465;
all128 changing-bit events are unambiguous. Exact delay statistics(ps):
{"physical_compact": {"clock_to_mux_zero_ps": {"maximum": 9.581434892876144, "median": 9.491111200654228}, "mux_to_tx_zero_ps": {"maximum": 6.09829029383962, "median": 5.97122009132631}, "source_to_output_100mv_ps": {"maximum": 27.4264716742218, "median": 27.179796408673198}}, "physical_wire": {"clock_to_mux_zero_ps": {"maximum": 22.614831331883618, "median": 21.050944335681756}, "mux_to_tx_zero_ps": {"maximum": 6.513847561199617, "median": 6.17929948213888}, "source_to_output_100mv_ps": {"maximum": 42.797680763914016, "median": 40.40026853520598}}}

Timing readback38457177829 restored and verified both original files, then
failed because the caller selected PHASE markers instead of actual CORNER
markers. Failure retained. Corrected caller uses CORNER and requires allsix
slow/typical/fast min/max phases. Raw fullSTA log remainsasset638067970
SHA80055c3fb2022a1366d03f8a010d0c671fe603c57b3ca6ca64350b5a44668374.
It includes one unconstrained endpoint and SRAM slew violations. PCIe worst
setup contains a long logic chain; PCIe worst hold has justINV+O21AI.
These are placement estimates; no constraint relaxation or closure.


## Verified latest timing readback

Corrected run38457514399 onbad1063138a4233ffca9b64b7c1e0f577558176a PASSED
both source/license/model checks and exact archived timing readback. Optional
archive-migration job was not requested and is skipped. Summaryasset638073464
SHAe759439142daa150c9d12cbd8cc67cda55850f61afb81375b8b30619cdb9566d;
complete original logasset638073598, SHA
80055c3fb2022a1366d03f8a010d0c671fe603c57b3ca6ca64350b5a44668374.
Allsix corners reproduce old placement estimates; slowmax -1.275681ns,
fastmin -0.065767ns. Next inspect the full critical paths and bind synthesized
cell names to actual RTL/netlist before selecting an ECO. PCIe setup includes
six consecutive AND2 stages near its endpoint; hold includes INV+O21AI. The
unconstrained endpoint and SRAM slew violations must also be resolved without
weakening constraints. No new timing/layout acceptance.

Main route38448901835 and32:1wire38441895491 remain in progress at last readback;
do not duplicate them. Authoritative cloud-migration-final-checkout-20261013
retirement-progress.json was reread and digest verified: status
COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE. Local directory remains
empty. The existing8hour automation is ACTIVE and explicitly cloud-only.


Next cloud timing readback also restores the exact placementODB and runs native
OpenDB on the same pinned runtime to bind every reported timing cell to its
actual master, placed bbox, pin nets and full incident-net endpoint census.
The STA report and ODB hashes must remain unchanged. This gives RTL-facing
net names before any ECO choice; no cell, clock or constraint is modified.
