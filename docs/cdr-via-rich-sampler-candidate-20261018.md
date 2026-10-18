# Native via-rich sampler candidate

The original full native CDR remains electrically rejected. Wire diagnosis39161087313 and raw location39161858974 identify dominant finite access resistors close to the32um load-resistor and HBT terminals. For example R2408 spans raw nodesP_avdd.n66→T210_rppd_1; R163 andR148 terminate atT052_C andT174_rppd_2. The immutable native technology includes9ohm nominal via1–via4 contact entries and finite metal sheet resistance. The RC model is not altered.

This physical candidate changes only local wiring: native32um resistor pin via stacks use16 columns instead of4; those Metal3 escapes become2um instead of0.4um. Other primitive-pin escape widths remain unchanged. Lane Metal3→Metal4 stacks use8 columns instead of2, Metal4→Metal5/TopMetal1 and Metal5→TopMetal2 junctions use8 lower-via columns and2 TopVia1 columns. All via rows and TopVia2 counts remain unchanged. Native via PCells generate actual cuts and enclosure geometry.

Device parameters, all54primitive drawings and positions, reference circuit, external pin boundary cuts and the physical validation gates remain unchanged. The exact source delta is hashed and checked against the prior strapped generator; independent native drawing comparison, all560DRCcategories, unsimplified deep/flatLVS and all14originalfaults must pass. A physical pass alone is not electrical acceptance. The new parent must receive fresh RC extraction and original full native loaded wave tests; no old RC can be reused or scaled.

The raw records and [Magic extraction documentation](https://opencircuitdesign.com/magic/commandref/extresist.html) are retained as provenance. Geometry must pass its real native decks before further integration.

## Native rejection and explicit metal correction

Run39162489704 rejected the first candidate with1220TM1.a markers across the original560categories; all other main categories were clear. Native primitive drawing/placement comparison passed. No LVS or electrical acceptance was inferred. The native via-stack implementation checks minimum landing size using column count, so the two-column/one-row TopVia1 combination can leave a TM1 landing thinner than1.64um. The revised generator adds actual top-level TM1 covering each junction's full native landing bounding box, padded outward on the5nm grid to at least1.64um in each direction. Original vias, cuts, circuits, native primitive drawings and DRC rules remain unchanged. New DRC/LVS must still pass.

Code basis: [pinned IHP via-stack PCell](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/ihp/via_stack_code.py), and [IHP main rules](https://ihp-open-pdk-docs.readthedocs.io/en/latest/verification/drc/02_main_rules.html). The actual native deck remains the acceptance authority.
