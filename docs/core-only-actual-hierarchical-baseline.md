# Actual hierarchical baseline integration diagnostic

This job qualifies connecting actual routed parent and core netlists with ordered
parent-first, child-second SPEF loading. It deliberately uses the authenticated
original routed core (44308129454) and the 56-buffer parent (44350414168 and
44349370248). It is **not** current post-ECO core signoff. Main core routing
44337630426 and native boot 44342916945 remain independent, preserved jobs.

The purpose is to expose real integration, library linking, hierarchical clock
propagation and annotation issues before the current core extraction is ready.
A real soc_top u_core hierarchy is used, not a core timing black box. Nominal
RC, typical 25 C libraries and unchanged 20 ns / 5 percent parent constraints
are used. Four native SRAM macro clock pins and representative standard-cell
pins must resolve in the actual linked core. Standalone core I/O constraints
are not read a second time.

The job authenticates complete source artifact output manifests and original
repository sources. It records the SRAM PDK commit, Git blob identity and SHA256.
The SRAM model remains unqualified for production. Fast SRAM -55 C vs stdcell
-40 C mismatch is not hidden by treating this typical-only diagnostic as
three-corner signoff.

Successful execution still requires annotation/coverage review and migration to
the final core and parent artifacts. External I/O budgets, CDC reliability,
qualified RC min/max, physical integration, foundry DRC/LVS and manufacturing
approval remain open.

## Native tool correction

The first attempt (44353327958, head e2b49a162ebd0d75ebce0a814df480ec18b24b43)
failed before timing: OpenROAD link_design required technology data (ORD-2010).
Artifact 14448983055, SHA256
19608ebc8baed36a0f824b70168909ca26062956af42b3869de1dfdc23af4f14,
and its 10 output hashes were verified. This is not a design timing result.

The corrected runner invokes the same standalone sta entry point already used
by qualify_core_only_hierarchical_spef.py in the pinned AppImage. Verilog escaped
identifier delimiters are removed when constructing STA pin queries. Actual
sequential CLK pins replace antenna-pin representatives, and the max-path report
must contain real u_core paths clocked by shell_main. Native errors fail the
runner; warnings are retained for explicit review. Constraints, source netlists,
libraries and SPEF ordering are unchanged.

The standalone-STA attempt 44354458971 failed before executing STA because
GitHub returned HTTP 503 while reading route artifact 14448476079.
Its failure artifact 14451095047, SHA256
8ebf7ee0b0ef5da37fd8189f3a8bb20780f2fa71e983b42fe86901d034923ed1,
and all six outputs were verified. No new design timing result was produced.
Source authentication now permits at most three attempts for failed read-only
GitHub commands, with 5 and 10 second backoffs. The exact run/head/artifact and
all hash checks remain mandatory on every attempt. Content/design assertions
are not retried or suppressed; routing, simulation and STA are not restarted
by this read retry.
