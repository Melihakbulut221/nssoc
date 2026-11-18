# I/O library revision compatibility review — 2026-11-19

The remaining pad slew cannot be assessed solely by replacing a maximum-transition value. Read-only upstream review found a newer official I/O library with materially changed tables and physical/circuit views. No production view was replaced.

Pinned existing PDK: `c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c`.
Current upstream dev snapshot read: `cc9afba57e0ec1b5ba77e6bbb638ba9dbe5866b8`.

| View | Existing | Upstream |
| --- | --- | --- |
| slow 1.08/3.0 V 125 C Liberty SHA256 | a23776c264fc0d177b4a5612eb3e1595c0eddc98d5b28b5ef7925e40b743b6ae | fefb19df14f6a440ce8bb7f396531638b6ea00bab6747d8a604d9cbb7ff3c8e7 |
| LEF SHA256 | 8b3dc3960960c08e07a1cde3dd9cd0484f5b12df07c4628726fff551bb775c0c | 1100f050cd477b0db6072e1b2b53ee1e13d7e5473e7b5d20f27534cc27806320 |
| GDS Git blob ID | 6b9cf6fd110e9c78040a433ecce704171e275bfe | f12b92abbb474add36ca5447ab4a54c9dce56f89 |
| GDS bytes | 71,399,424 | 71,426,048 |
| schematic SPICE SHA256 | c2cfa122268050f770e91eeb0c70682775f9610cf4d5b066805b2d57c5980ce2 | 1d53ab7df431b717ef5aff43e1117c0224681d5cc84886da37a319280ee958d6 |

SPICE filename changes from `sg13g2_io.spi` to `sg13g2_io.spice`. GDS identities above are Git blob identifiers from GitHub tree metadata, not independently computed SHA256 or geometry equivalence proofs. A direct binary contents request failed; no geometry validation is inferred.

The complete LEF text diff contains seven pad direction changes (INOUT to INPUT or OUTPUT), without coordinate changes. This does not prove GDS connectivity equivalence. The newer Liberty has 3.5 ns default maximum transition versus 1.2 ns previously, changed load-grid points (1,3,6,9,14,20 versus 1,3,7,9,12,15 pF), and substantial cell/table changes. The newest Liberty-file commit inspected is `16713c2b92e9d9dcabb33072718a0e1cdee5044c`; use the full dev snapshot above for cross-view comparisons, not an unrelated last-file commit.

Next gate: compare relevant cell transistor connectivity and actual GDS geometry for a coherent revision migration before accepting timing under newer models. Re-run pad behavior and parent/whole-chip timing with authenticated compatible views. Do not waive slew or substitute the new limit into the old Liberty. The six-case official-diode-model schematic current result remains valid only for the pinned pad schematic and documented diode revision, not every newer pad view.
