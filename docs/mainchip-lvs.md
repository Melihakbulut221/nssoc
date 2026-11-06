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

## Result with the vendor SRAMs blanked (run42207147048, audit run42211661510)

The deck reports **"Congratulations! Netlists match."** The run took 1873 s at a 4.43 GB peak.

The independent audit gives **PASS within comparison scope**: 59 of 59 circuits Match, no reasons, no extraction diagnostics. This covers:

- all std-cell types;
- `soc_top`;
- both SRAM macros as blanked circuits (0 devices on each side).

So the full-chip layout of the DRC-clean route is transistor-level equivalent to its powered netlist. That includes all std-cell devices, the 154524 instances and every net into the SRAM macro pins.

What this does not cover:

- the SRAM macro interiors, because the vendor CDL does not match its own GDS;
- physical supply continuity beyond extracted connectivity;
- foundry signoff.

The logical PG binding of the 44 new diodes is part of the exported netlist.

## Final route (antenna 0, DRC 0): run42214541985

The routed database is artifact 13499508759. It has 154530 instances, full OpenROAD `check_drc` 0 and `check_antennas` 0, with no unrouted multi-terminal nets (run42214527471). All diode PG terminals are bound in the database, so the export binds 0 terminals.

The vendor SRAMs are blanked. The deck reports **"Congratulations! Netlists match."** in 1569 s at a 4.43 GB peak. The audit gives **PASS within comparison scope**.

Foundry-deck KLayout DRC on the same GDS runs as run42218554075:

- the main rule tables, with recommended rules, through `check_ihp_drc_partitioned.py`;
- the antenna deck, through `check_ihp_drc.py`.

Density is a separate deck and needs metal fill first.
