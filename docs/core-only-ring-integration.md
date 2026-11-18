# Core/pad-ring integration geometry

The authenticated clock-refine artifact (run 44259265143, artifact 14408985519) contains a DEF header with 1000 DBU/um and DIEAREA `(0 0) (3326400 2475900)`. The core is therefore 3326.4 x 2475.9 um. The current native pad-ring generator uses a 4000 x 3200 um die and 180 um-deep pad rows, leaving a 3640 x 2840 um inner rectangle.

A mathematically centered core would have translation (336.8, 362.05) um and gaps of 156.8 um on each side and 182.05 um above/below. This is **bounding-box feasibility only**. No translation has been applied; site/manufacturing-grid alignment, macro pin access, supply connection, shell placement, clock routing and signal/CDC timing remain unverified. Recheck actual completed DRT views before any physical assembly. The mapped shell's standard-cell area is not a routability proof.

For a hierarchical physical boundary, OpenROAD's documented `write_abstract_lef` exports external pins and metal obstructions from an existing database: https://openroad.readthedocs.io/en/latest/main/src/README.html#abstract-lef-support . The pinned runtime must be checked, and exported power pins must agree with the powered netlist and shell supply wiring. This has not yet been executed on the final routed core. A LEF boundary is not a GDS/LVS/timing model or production approval.
