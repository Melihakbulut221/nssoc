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

## Route after the foundry-antenna relayer (run42247427878)

The routed database is artifact 13518226848. Two nets (`u_ram.g_ram_2048x64_ecc.mbist_aborted`, `net37210`) had their TopMetal guides moved down and were rerouted for the foundry `Ant.e_TopMetal2` rule. Results:

- **Foundry antenna deck:** PASS, 0 markers.
- **LVS with the vendor SRAMs blanked:** "Congratulations! Netlists match." The audit gives PASS within comparison scope.

This candidate therefore has OpenROAD `check_drc` 0, LEF antenna 0, foundry antenna 0, no unrouted multi-terminal nets, and LVS matching outside the SRAM interiors. The foundry main deck (run42242071796, with swap) is still open.

## Foundry main deck: every marker is NW.b (runs42242071796 and42255827123)

The main deck was run through `check_ihp_drc_partitioned.py` with recommended rules, a 32 GB swap and one thread, on two GDS files:

- artifact 13499508759, in 13199 s;
- artifact 13518226848, in 13672 s.

Both give the same result: **9499 markers, all `NW.b`** (N-well spacing). The other partition passes with 0.

The cause is that the routed database has no filler cells; `decap_swap.py` found no `fill` or `decap` instance at all. Empty row sites therefore break the N-well between standard cells, and every short gap becomes an `NW.b` violation.

## Density deck and metal fill (run42263877748)

The unmodified IHP `density.drc` (5e6d592, `density_sanity=True`) runs on the GDS of artifact 13518226848. All 37 rules execute, and `check_ihp_density_coverage.validate_density_coverage` accepts both runs.

- **Without fill:** 158 markers.
- **With fill:** 14 markers. Fill is the pinned gdsfill bundle (release asset 597158300, chip config) through `fill_chip_windows.py`: 35 tiles of 500 um, layout extent as the boundary, geometry preservation PASS, 1822 s.

The 14 remaining markers are all in the standard-cell core:

| Rule | Measured | Limit |
|---|---:|---:|
| `AFil.g` global Activ | 29.90% | 35% min |
| `AFil.g2` Activ, 6 windows of 800 um | 20.8-24.6% | 25% min |
| `M1.j` global Metal1 | 31.27% | 35% min |
| `M1Fil.h` Metal1, 5 windows of 800 um | 21.2-24.2% | 25% min |
| `M2.j` global Metal2 | 33.41% | 35% min |

GatPoly, Metal3-5 and TopMetal1/2 meet their limits. The empty row sites hold no Activ, GatPoly or Metal1, and gdsfill keeps out of the rows. That is the same missing-filler cause as `NW.b`.

## Decap and filler insertion (run42326849862)

On artifact 13518226848, the routing engine (OpenROAD dcf36133) runs `filler_placement {sg13g2_decap_8 sg13g2_decap_4 sg13g2_fill_2 sg13g2_fill_1}` on the empty sites only. Signal routing starts at Metal2, so no wire changes.

It places 142909 `decap_8`, 30412 `decap_4`, 38203 `fill_2` and 41007 `fill_1`. A `check_drc` pass then finds one `decap_8` whose internal Metal1 touches a router Metal1 patch of `$abc$1804206$new_n41321` at (100.5, 505.6) um. That decap is replaced by `fill_4 + fill_2 + fill_1` in its own footprint.

The result is artifact 13557301203, with 407063 instances:

- `check_placement` passes;
- full `check_drc` is **0**;
- `check_antennas` is **0**.

Run42330567274 measures LVS with the SRAMs blanked, fill plus the density deck, and the foundry main deck on it.

### Results on the filler database (runs42330567274 and42335832230)

- **LVS, vendor SRAMs blanked:** "Congratulations! Netlists match." All 407063 instances are in the comparison, including the 173320 decaps; 0 PG terminals are unbound. The audit gives PASS within comparison scope. The deck takes 7093 s at a 4.98 GB peak.
- **Fill plus density deck:** 35 of 35 tiles are generated and geometry preservation passes. All 37 rules execute and the coverage check accepts the run. Only **1 marker** remains, `M2.j`.

| Layer | Global density | Limit |
|---|---:|---:|
| Activ | 38.69% | 35-55% |
| GatPoly | 25.01% | >= 15% |
| Metal1 | 38.36% | 35-60% |
| **Metal2** | **33.41%** | 35-60% |
| Metal3 | 38.26% | 35-60% |
| Metal4 / Metal5 | 45.77% / 45.81% | 35-60% |
| TopMetal1 / TopMetal2 | 38.36% / 38.50% | 25-70% |

The fill generator is not what limits Metal2. Raising only the Metal2 target from 50 +/- 10 to 58 +/- 2 percent (`fill_density_m2`) moves the global value only from 33.41% to 33.74%. The vendor SRAMs carry 39.1% (2048x64) and 39.5% (256x16) Metal2 of their own.

A 400 um map of the filled GDS shows where the deficit is. The standard-cell core holds 26-31% Metal2: about 18% routed wire and 8-13% fill. A further 12% of the core is free space at least 0.3 um wide, but narrower than the 1.0 um minimum filler width. The deck itself checks only `MFil.a2` and `MFil.c`, but the generator keeps the rule book's minimum filler width, and so does this flow. Narrower floating shapes would be fill under another name, so they are not used.

Closing `M2.j` therefore needs more drawn Metal2 in the core, for example Metal2 power straps over the rows or a denser placement. That is an implementation change and is left open.

### Foundry main deck on the filler database (run42342082873)

The two main-deck partitions run as parallel jobs on artifact 13557301203. They use the same command, tables and catalog check as `check_ihp_drc_partitioned.py`, with recommended rules on. In the earlier single-job run (run42330567274) the filler database's first partition exceeded the 9000 s per-partition limit. That run reported ERROR and carries no measurement.

| Partition | Markers | Elapsed |
|---|---:|---:|
| feol_and_geometry | **0** (was 9499 `NW.b` before filler insertion) | 10836 s |
| beol | **0** | 12285 s |

All 9499 `NW.b` markers came from the empty row sites, and filler insertion clears them. The main deck therefore passes on this candidate with no cell or region excluded.

The foundry antenna deck also passes on this database: 0 markers in 2105 s (run42356845718).

## Metal2 power straps close the density deck (run42387899733)

Raising the fill target alone cannot close `M2.j`. Instead, `scripts/m2_pg_straps.py` (KLayout) adds Metal2 power straps after the fill. Each strap sits on one standard-cell Metal1 row rail and has a single Via1 at its centre inside that rail. It touches no other conductor, so it carries the rail's own net and cannot short anything.

The straps fill every free interval along each rail. They are 0.28-5.0 um wide and 3.4 um tall, with these clearances:

- 0.25 um to drawn Metal2 and between straps (Mn.b 0.21, Mn.e 0.24);
- 0.42 um to Metal2 fill (MFil.c);
- 0.22 um to other Via1 (V1.b);
- 0.05 um Metal1 enclosure of the Via1;
- 2 um from the vendor SRAMs.

Obstacles are expanded with rectangular corners. The script checks its own result: no two straps touch, they are at least 0.25 um apart, their width is in range, and no strap overlaps the clearance of existing Metal2 or fill.

On the filled GDS of artifact 13557301203 the run places 93621 straps. They add 258924 um^2 of Metal2, which is 3.14% of the die. The density deck then gives **PASS, 0 markers**, with all 37 rules executed and the coverage check accepting the run.

The resulting GDS (fill plus straps, artifact 13581294638) is the one checked next. Run42391759014 runs on it:

- the foundry main deck, both partitions;
- the foundry antenna deck;
- LVS with the SRAMs blanked.

The straps exist only in the GDS, like the fill. The OpenROAD database and the timing netlist do not contain them.

### Grid fix and the complete foundry check set on the final GDS (runs42404887162 and42410792687)

The first strap GDS failed the feol partition with 109836 `via1_drw_Offgrid`, all on the new Via1. A centre computed as `(left + right) // 2` was not on the 5 nm grid. The strap script now snaps every strap edge and Via1 centre to the 5 nm grid, keeps each Via1 centre inside its feasible interval, and asserts that no shape is off grid. The strap count and area are unchanged: 93621 straps, 258924 um^2.

On the earlier strap GDS the beol partition was already PASS with 0 markers (run42391759014). That partition covers Metal2 spacing, Via1 and Metal2 filler rules. LVS on that GDS also matched.

The final GDS is artifact 13588974063, SHA-256 433d319f...: the filler database 13557301203 streamed out, tiled metal fill, then the grid-snapped Metal2 power straps. Every check runs on this one file.

| Check | Result | Run |
|---|---|---|
| Density deck, all 37 rules executed, coverage accepted | **PASS, 0 markers** | 42404887162 |
| Foundry main deck, feol_and_geometry, recommended on, no exclusions | **PASS, 0** (10249 s) | 42410792687 |
| Foundry main deck, beol | **PASS, 0** (8672 s) | 42410792687 |
| Foundry antenna deck | **PASS, 0** (1940 s) | 42410792687 |
| LVS, vendor SRAMs blanked | **Netlists match**, audit PASS within comparison scope (8681 s) | 42410792687 |

The database behind the GDS has OpenROAD `check_drc` 0, `check_antennas` 0 and no unrouted multi-terminal nets. Physical signoff of the main chip is therefore complete within these limits:

- LVS excludes the vendor SRAM interiors, whose CDL does not match their own GDS (IHP issue #239).
- Timing is not closed (see `docs/mainchip-sta-measurement.md` on `analysis/mainchip-sta`).
- The chip has no padframe or ESD.
- This is not a manufacturing release.
