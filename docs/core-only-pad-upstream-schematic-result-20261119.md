# Updated pad schematic six-case result — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44416611076, attempt 1, commit `416cd79343dbdb59d9e773c99048215329cdbf2c`, artifact `14480201435`, SHA256 `a3e25166120838a541f62eb1ffbd9466e953c08102823a59c4f0e3c55f6741ef`. All 79 output hashes independently verified.

All six 125 C slow-corner cases complete 50 ns without diagnostic warnings/errors or solver aborts, with native KLU/Gear2/ITL4=100 and at most 1 ps steps. Updated official pad schematic: IHP `cc9afba57e0ec1b5ba77e6bbb638ba9dbe5866b8`, schematic SHA256 `1d53ab7df431b717ef5aff43e1117c0224681d5cc84886da37a319280ee958d6`; corrected diode model SHA256 `e6211bd0318122fbeb707498ede893223c332098cbb21c441b28b9d8c365e83d`. Existing MOS/resistor bundle retained, explicitly not a complete PDK migration.

| Data | Enabled current | Post-turnoff current | First below 1% current after enable midpoint |
| --- | ---: | ---: | ---: |
| 0 | -2.13127376 mA | +0.265283538 nA | 1.5465 ns |
| 1 | +2.08507141 mA | +0.265283554 nA | 1.8685 ns |

Static enabled and disabled controls agree with corresponding steady currents. New pad pin order and internal gate-node mapping are explicit in the test source and companion binding document. This qualifies only the six-case schematic compatibility probe. It does not establish transistor/GDS equivalence, extracted timing, full PVT/Liberty characterization, ESD, whole-chip signoff or manufacturing acceptance. Next, inspect native GDS differences and pad connectivity before migrating physical/timing views coherently. The one-percent current timing remains distinct from Liberty voltage-slew metrics.
