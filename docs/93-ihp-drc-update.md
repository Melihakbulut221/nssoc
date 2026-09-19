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
