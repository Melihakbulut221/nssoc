<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# 93 — Rechecking SRAM with updated IHP verification rules

2026-09-20. The unchanged installed SRAM GDS files pass the **main KLayout
rules** from upstream IHP commit `5e6d592e4002946a4616f798c357f0f3c06cf3b6`.
The previous pinned-deck failures remain recorded. This is a new measurement
with a different verification deck, not a retroactive PASS or full-chip signoff.

## Controlled comparison

Both arms use KLayout 0.30.9, the same input GDS bytes, `run_mode=deep`, main
rules, and `no_recommended=True`. Neither arm excludes cells or selected rules.
The installed PDK stays at `c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c`.
Only the upstream arm's unmodified rule files and matching process constants
change. The [record](evidence/ihp-upstream-drc-20260920.json) includes all
eight exact commands, input/report hashes, marker categories and return codes.

| SRAM macro | Pinned-deck markers | Upstream-deck markers |
|---|---:|---:|
| `RM_IHPSG13_1P_2048x64_c2_bm_bist` | 3,538 | 0 |
| `RM_IHPSG13_1P_1024x32_c2_bm_bist` | 2,672 | 0 |
| `RM_IHPSG13_1P_512x16_c2_bm_bist` | 2,316 | 0 |
| `RM_IHPSG13_2P_256x16_c2_bm_bist` | 4,320 | 0 |

The updated [contact rules](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/5e6d592e4002946a4616f798c357f0f3c06cf3b6/ihp-sg13g2/libs.tech/klayout/tech/drc/rule_decks/feol/5_14_cont.drc)
distinguish SRAM regions, and the updated deck changes device recognition and
several other checks. The measured reduction is attributable to the complete
deck/constant change in this controlled experiment; it is not an assertion
that one particular rule edit accounts for every old marker. Earlier GDS
comparison found only a boundary-layer change in the upstream macros
([record](evidence/ihp-macro-update-check-20260919.json)); replacing the macro
geometry was neither necessary nor performed in this experiment.

## Reproduce without changing the installed PDK

[prepare_ihp_drc.py](../hw/soc/flow/prepare_ihp_drc.py) prepares the upstream
deck under the ignored project tool directory. The [lock](../hw/soc/pnr/ihp-drc.lock.json)
pins all 45 runtime/constant/licence files by immutable source revision, size
and SHA-256. Changed cached bytes and wrong downloaded bytes fail rather than
being silently accepted or replaced. Nine preparation tests cover cache reuse,
corruption, path escape, symlinks and immutable-source/licence requirements.

```bash
python3 hw/soc/flow/prepare_ihp_drc.py
.venv/bin/python -m pytest -q sw/tests/test_ihp_drc_preparation.py

# Example: repeat the unchanged 1024x32 macro's upstream arm.
mkdir -p hw/soc/out/drc-replay-1024x32
klayout -b -zz \
  -r hw/soc/tools/ihp-drc-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/drc/ihp-sg13g2.drc \
  -rd input="$HOME/.ciel/ihp-sg13g2/libs.ref/sg13g2_sram/gds/RM_IHPSG13_1P_1024x32_c2_bm_bist.gds" \
  -rd topcell=RM_IHPSG13_1P_1024x32_c2_bm_bist \
  -rd report="$PWD/hw/soc/out/drc-replay-1024x32/drc.lyrdb" \
  -rd run_mode=deep -rd no_recommended=True -rd thr=2
```

A zero process exit alone is insufficient: inspect the completed report's
marker count. The old deck exits zero while reporting the nonzero counts above.
Use the same pinned input hashes and KLayout version to reproduce this table.

### Report-based acceptance command

[check_ihp_drc.py](../hw/soc/flow/check_ihp_drc.py) runs those same locked
main rules and writes `inputs.json`, `run.log`, `drc.lyrdb` and `result.json`
under a new `hw/soc/out/<tag>` directory. It refuses to reuse an existing
directory. PASS requires a successful process **and zero markers** in a
complete report naming the requested top cell; even visited or waived markers
are counted. Missing/malformed reports, interrupted processes and input bytes
changed during the run produce ERROR. GDS, deck, process constants and lock
hashes accompany the exact command. The installed PDK remains unchanged.

```bash
python3 hw/soc/flow/check_ihp_drc.py path/to/soc_top.gds \
  --top soc_top --tag my-new-drc-run --klayout klayout
.venv/bin/python -m pytest -q \
  sw/tests/test_ihp_drc_preparation.py sw/tests/test_ihp_drc_result.py
```

The gate exits 0 for PASS, 1 for a completed report with violations, and 2
for an execution/evidence error. The regression above recorded **21 passing
tests** on 2026-09-20, including a zero-exit process with two waived/visited
markers that must fail. It does not make this newer deck a foundry signoff
qualification or replace the independent Magic/LVS/timing checks.

The actual wrapper run on the unchanged 1024x32 macro completed with exit 0
and **zero report markers**; [execution record](evidence/ihp-drc-gate-20260920.json).
The same parser reproduced every count in the eight existing reports above.
Combined preparation, result, evidence and document checks passed 181 tests;
the record pins the command and log. This verifies the acceptance command on
real tool output, in addition to its negative-control tests.

## Remaining physical gates

The complete original 24-macro SoC GDS is running separately with the updated
deck in `hw/soc/out/external-review-20260919/full-upstream-drc-20260920`.
No full-design verdict is available in this entry. Native Magic and pinned
KLayout checks also remain independent measurements. The original layout's
[passing scoped LVS](evidence/ethernet-lvs-20260920.json) and its
[failing extracted timing](evidence/ethernet-extracted-layout-20260920.json)
remain unchanged. A timing ECO needs its own final extraction, streams and
decks. This experiment does not qualify pads, packaging, analog PHYs, memory
transistor LVS, radiation behaviour or silicon manufacturing.

## Full original SoC result, 2026-09-20

The complete `interfaces-eth256-resume-20260919-184950` GDS now passes the same
unchanged upstream **main KLayout rules with zero markers**, exit zero, in
5,013.69 seconds. FEOL, BEOL, offgrid, angle, pin, forbidden and connectivity
checks are enabled; optional recommended checks remain off. The
[full-chip record](evidence/ihp-full-chip-drc-20260920.json) pins the GDS,
report, log, command and runtime rule files. This is the original 24-SRAM
geometry, not a later timing ECO. Magic and setup/hold remain independent
requirements; the installed PDK has not been migrated or modified.

**Thread-control correction, 2026-09-20:** the earlier commands passed
`-rd thr=2`, but this upstream revision reads `$threads`. Its run log shows
**20 tiling threads**, not two. The resource-control argument was ineffective;
the selected rules and measured markers are unchanged. The wrapper now sends
`-rd threads=2`. Earlier command records remain exact historical records.

## Magic comparison: remaining contact rules

The unchanged 512x16 SRAM, imported using upstream's `read_sram_gds.tcl`
helper, still produces **57 Magic error boxes** under the same upstream
revision's full DRC style: 21 general `Cnt.c` and 36 SRAM `Cnt.c` boxes.
The measured command, GDS hash and categories are in the
[Magic follow-up](evidence/ihp-magic-sram-followup-20260920.json). This
completed arm took 2,173.59 seconds; the other controlled arms are pending.

The same upstream revision's
[Magic rules](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/5e6d592e4002946a4616f798c357f0f3c06cf3b6/ihp-sg13g2/libs.tech/magic/ihp-sg13g2-drc.tech)
use a 0.02 µm SRAM contact enclosure, while its
[KLayout defaults](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/5e6d592e4002946a4616f798c357f0f3c06cf3b6/ihp-sg13g2/libs.tech/klayout/tech/drc/rule_decks/sg13g2_tech_default.json)
set 0.006 µm in SRAM and 0.05 µm in DigiBnd. The matching official layout-rule
PDF still marks section 8.3 as work in progress. This discrepancy is being
investigated geometrically; it does not by itself prove all Magic boxes false.
No local threshold change or blanket waiver is adopted.

The completed pinned-deck full-chip control reports **22,280 markers** on
the identical GDS: 2,768 `Cnt.c.digibnd`, 9,756 `Sdiod.d` and 9,756 `Sdiod.e`.
Its exact cell attribution and report hash are retained in the full-chip
record above. The isolated native DRC step exits zero despite markers; the
report verdict is **FAIL**. The updated deck's zero is a separate measurement.

The corrected thread argument was also exercised end to end on the unchanged
512x16 SRAM: the log explicitly reports **two threads**, and the full main
deck finishes with zero markers in 46.48 seconds;
[record](evidence/ihp-drc-gate-20260920.json).
The official PDF discussed above is pinned at
[the same IHP revision](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/5e6d592e4002946a4616f798c357f0f3c06cf3b6/ihp-sg13g2/libs.doc/doc/SG13G2_os_layout_rules.pdf).

### Contact geometry and pinned Magic control, 2026-09-20

The read-only geometry follow-up now maps all 57 upstream Magic boxes to
exactly one original GDS contact each. Of these, 21 are inside DigiBnd and
outside SRAM, with 60 nm orthogonal active enclosure; 36 are inside both
masks, with 10 nm enclosure. The command checks complete contact polygons
against nearby active geometry in 1 nm growth increments. A separate Magic
query measures its internal grid as approximately 0.005 µm, validating the
coordinate conversion. Commands, coordinates and source/log hashes are in
the [follow-up record](evidence/ihp-magic-sram-followup-20260920.json).

These enclosures are below Magic's respective 70/20 nm limits and above
KLayout's corresponding 50/6 nm limits. This explains the disagreement for
these contacts, but does not authorize changing SRAM geometry or waiving a
deck. The pinned Magic control, using the same macro and upstream reader
helper, also completed: **499,098 boxes**, FAIL, in 1,961.42 seconds. Its
five rule categories are retained alongside the upstream arm. Raw-reader
comparisons remain pending; neither arm is a full-chip result.

### Raw-reader control, 2026-09-20

The upstream deck's raw hierarchical GDS-reader arm has now completed in
**4,100.375 s** with **57,916 error boxes**, so it also fails. The dated
[SRAM follow-up](evidence/ihp-magic-sram-followup-20260920.json) retains all
seven categories: 30,720 Metal2 minimum-area, 25,944 layer-overlap, 594 tie
extension, 376 subcell-abutment, 225 SRAM well-spacing, and the same 21 + 36
contact-enclosure boxes. The helper-reader arm's 57 boxes and this raw-reader
result use the same unchanged macro GDS. Their different handling of hierarchy
is consequential; neither result provides a passing Magic verdict or a waiver.
The pinned-deck raw-reader comparison is still running.

**Dated update, 2026-09-20:** the pinned raw-reader arm has also completed:
**557,149 boxes**, FAIL, in **1,931.615 s**. All four arms are now finished.
The [follow-up record](evidence/ihp-magic-sram-followup-20260920.json) retains
its ten categories and exact commands/source hashes. Completion of this
comparison does not close Magic DRC; none of the four combinations passes.

### Completed full-chip abstract Magic check, 2026-09-20

The original 24-SRAM baseline's full Magic check has now completed in
**4 h 34 min 16.429 s**: **642 boxes**, FAIL. Its actual input is the DEF
with LEF macro abstracts (`MAGIC_DRC_USE_GDS=false`), so this is distinct
from the real SRAM-GDS reader experiments above. The
[full-chip record](evidence/ihp-magic-full-chip-20260920.json) includes the
complete native report, every marker coordinate, source hashes and commands.

Against exact LEF footprints, **436 boxes are inside macros** and **206
outside**, with none straddling. Every outside box lies within 0.5 µm of a
macro footprint. Categories are 356 `M2.d`, 174 `M3.f`, 80 `M4.f`, 29 `M2.f`
and three `M4.e`. The older classifier's optional NWell-overhang model is
reported separately and does not waive any marker. The named 0.6 µm routing
halo would reserve a projected **20,336.064 µm² per affected layer** before
pin-access openings; this is geometry arithmetic, not a reroute result.

After preserving the completed Magic result, the following duplicate pinned
KLayout step was stopped. Its parent invocation exits nonzero and is not
called a passing verification flow. The independent completed KLayout
controls on this same GDS remain in their original evidence record.

### Upstream disposition and routing experiment, 2026-09-20

The live IHP issue [#1024](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/1024)
remains open. It independently reports the 0.006 µm KLayout versus 0.02 µm
Magic contact-enclosure specification. The earlier tracking issue
[#794](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/794) was closed after
reader/rule-exception work, but its discussion explicitly records remaining
contact-enclosure problems and the absence of an authoritative SRAM exception
specification. That closed tracking issue is therefore not a zero-error
qualification of these macros. The dated [follow-up record](evidence/ihp-magic-sram-followup-20260920.json)
pins the read-only issue snapshots and their statuses; no vendor waiver or
modified rule is inferred from either discussion.

The separate [routing-halo experiment](evidence/ihp-routing-halo-20260920.json)
has progressed beyond area projection: new blockages retain pin corridors,
preserve the netlist and placement, and complete global routing with zero
overflow. Native detailed routing is running. A new Magic measurement is
still required, and the inside-footprint failures are not addressed by this
outside-ring experiment.

### Recovered routing and transistor LVS, 2026-09-20

The [halo continuation](evidence/halo-routing-recovery-20260920.json)
has now completed detailed routing and independent antenna/connectivity
checks with zero critical violations. Its own stream was generated, and
the same installed Magic DEF/LEF check is running. The prior baseline's
642 markers cannot be replaced until the new report completes and is
classified against the actual macro footprints.

Separately, [real 256x16 SRAM transistor LVS](evidence/sram-transistor-lvs-20260920.json)
was measured against its vendor CDL. Both installed and pinned updated
decks in deep mode fail: 24 matching, four mismatching, three nonmatching
and one skipped circuit (the top). Two full-flat controls hit a 1,200-second
bound without producing a comparison database; no verdict is assigned.
No macro blackboxing, pin relaxation, geometry change or rule edit was used.

Exact isolated-cell controls reproduce the dummy-cell `LVSRES` versus
`res_metal1` mismatch and the sense-amplifier power-connectivity difference.
The word-line driver extracts all four matching transistors in isolation,
but its unlabeled top ports still fail strict comparison. This distinguishes
context-sensitive extraction from a verified macro. Producer KLayout is
0.30.9; the independent Python database reader is 0.30.10.

`hw/soc/flow/audit_klayout_lvs.py` requires an unambiguous nonempty requested
top, matching circuit pairs and the deck's explicit successful verdict.
Its 17 tests pass, and it rejects all seven completed diagnostic reports.
The real word-line case demonstrates why a database `Match` alone cannot
override the strict port verdict. Raw CLI exit zero likewise does not mean
LVS success. This does not characterize the upstream Python wrapper's exit
handling or validate the adequacy of an extraction deck.

The official [lvsres PR #1121](https://github.com/IHP-GmbH/IHP-Open-PDK/pull/1121)
is still open in the recorded snapshot: its Pycell work is present but the
KLayout LVS mapping is explicitly unfinished. It supplies no completed
mapping fix to adopt. An ad hoc resistor alias or blanket implicit power
connection would conceal precisely the distinctions being investigated,
so no such change is counted as verification.
