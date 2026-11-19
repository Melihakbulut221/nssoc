# Two load-isolation buffers admitted for routing

Run 44426268856, head 09fdcf87424f1988ad38892da05cafad2db24653, artifact 14483548127, SHA256 d2ecceec90e6aeac6dde4c6eab5e057eb38eb555f7bda0fffda618a79e086980. All 13 output hashes verified. Candidate ODB SHA256 6a93288d78e6594edeee7ea3ed2928950ccc7f3bd96da59fb2fd49f03da7fc8f.

Two buffers legalized: nssoc_loadiso_0 (buf_4, separating two distant NAND3 sinks) and nssoc_loadiso_1 (buf_8, driving eight remote NOR3 sinks). 106619 instances. Every original instance geometry is preserved. Verified identity-buffer collapse restores all original functional terminal connections exactly. Existing diode connections, special supply geometry and ports are preserved. All four added power terminals have positive-area same-supply contacts; no failures reported. These limited checks do not prove full transistor LVS or final physical signoff.

Next job authenticates this artifact and its protected sources, exports fresh netlist/DEF, restores unchanged 20 ns / 5 percent constraints and globally routes the candidate for three-corner estimates. Actual detailed routing, antenna repair and freshly extracted RC/STA remain required regardless of estimate results. Source lineage remains the first antenna repair (15 residual nets); second antenna-repair branch is independent.
