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
