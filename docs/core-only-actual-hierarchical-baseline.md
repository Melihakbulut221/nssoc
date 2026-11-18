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
