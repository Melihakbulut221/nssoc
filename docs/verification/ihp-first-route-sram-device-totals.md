# Recursive SRAM MOS instance counts

The [leaf investigation](ihp-first-route-sram-leaf-differences.md) identified missing device records at individual cell boundaries. Recursively expanding each SRAM root changes the interpretation of those local differences.

| Root | Extracted NMOS | Reference NMOS | Extracted PMOS | Reference PMOS |
|---|---:|---:|---:|---:|
| RM_IHPSG13_1P_2048x64_c2_bm_bist | 541301 | 541301 | 276149 | 276149 |
| RM_IHPSG13_2P_256x16_c2_bm_bist | 30820 | 30820 | 14468 | 14468 |

Inputs were extended.cir (SHA-256 5bb47e790d2bf96beca39e29151c8b6697ce5e28cf2202a7ce27f465f44995ce) and reference.cdl (SHA-256 c1cbfcd2b317e0838b09fa1e1bd871a693a21bc8067ed5609c4a2e5b13a7736c). The census joined SPICE continuation lines, indexed each subcircuit case-insensitively, counted M records by model and added the recursively expanded model counts of every X instance with its occurrence count. Both roots resolved fully. Counts represent M statements per instantiated hierarchy and do not compare terminal connectivity, width, finger parameters or electrical equivalence.

The unchanged-deck run logs for both standalone SRAMs also report a mismatch. Matching aggregate transistor counts together with the full-layout leaf discrepancies make the hierarchy boundary and net correspondence the next comparison to resolve. Adding devices based on the leaf count alone has no demonstrated justification.
