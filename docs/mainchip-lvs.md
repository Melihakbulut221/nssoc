# Full-chip KLayout LVS of the DRC-clean main-chip route

Branch `analysis/mainchip-lvs`, `.github/workflows/cloud-evidence-summary.yml`.

## Input and steps

The layout is the routed database of run42189463974 (artifact 13493489102): full OpenROAD `check_drc` 0, 154524 instances.

1. The routing engine (OpenROAD dcf36133) exports DEF and `write_verilog -include_pwr_gnd`. Before the export, the 88 PG terminals of the 44 antenna diodes added by the antenna repair are bound logically to VPWR/VGND with `global_connect`. The row rails already supply them physically.
2. GDS stream-out uses LibreLane 3.0.5 `scripts/klayout/stream_out.py`. The cell views are std cells and the two vendor SRAMs from IHP-Open-PDK `c4b8b4e5`. The script reports "All LEF cells have matching GDS cells".
3. `hw/soc/flow/transistor_schematic.py` builds the transistor schematic from the powered netlist and the vendor std-cell and SRAM CDL.
4. LVS uses the repository-pinned IHP deck (`hw/soc/pnr/ihp-lvs.lock.json`, commit 5e6d592) in deep mode and strict port mode.
5. `hw/soc/flow/audit_klayout_lvs.py` judges the lvsdb, because the KLayout exit code is not a verdict. The audit needs the `klayout` Python module, so it runs inside the AppImage.

## Result with the vendor SRAM CDL (run42204287008, audit run42210207602)

**FAIL.** The deck reports "Netlists don't match". The audit status is FAIL, with 79 Match, 5 Mismatch, 2 NoMatch and 3 Skipped circuits. The run took 2153 s at a 5.37 GB peak.

- The five Mismatch circuits are all SRAM-internal cells: `RSC_IHPSG13_CBUFX8`, `CINVX2`, `CINVX8`, `FILLCAP4` and `FILLCAP8`. They appear in the vendor CDL but have no layout circuit of their own.
- Both SRAM macros are Skipped: 1080304 devices on each side for 1P_2048x64; 62012 layout against 62046 schematic devices for 2P_256x16.
- Because the macros are skipped, `soc_top` is skipped too, so there is no top-level verdict.

This is the same picture as the 2026-09-23 full-chip run (`docs/evidence/full-chip-transistor-lvs-20260923.json`). The vendor SRAM CDL does not match its own GDS (IHP-Open-PDK issue #239). The fix belongs to the SRAM views, not to this layout.

Run42207147048 adds `blank_circuit("RM_IHPSG13_*")` before the deck's alignment step. It blanks both macros on both sides, so `soc_top` connectivity into the macro pins gets its own verdict.
