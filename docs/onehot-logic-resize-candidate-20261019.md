# Source-measured combinational sizing candidate

The latest saved routed design still fails setup/hold. Native slow-path evidence shows heavily loaded logic gates after the first buffer resizing: O21AI cell 1824202 contributes 3.357555ns, NOR4 cell 1824216 contributes 3.880652ns; the fast PCIe path includes NAND4 1830785 at 0.752665ns and NOR4 1830796 at 1.360980ns. These are measured stage delays, not predicted improvement.

fanout7880 and fanout8443 are instance names, not fanout counts. Their report fanouts are respectively 8 and 13. Preserve this distinction when discussing the native paths.

The candidate restores the exact completed route ODB (SHA256 4acbb9969285c715969619795ec7a45305de1bd4a3f6ac97a91139cf0024b723), including its 1,130 additional antenna diodes, for 147,858 total instances. The original negative slow-data-path selector remains unchanged (capacitance >=0.1pF, stage delay >=1ns). It now permits up to 32 stronger native combinational cells, including NAND/NOR and complex gates as well as buffers. Only masters actually present in the restored database with identical pin names/directions/types may be selected; unavailable alternatives are recorded.

All untargeted cells remain fixed through legalization. Complete net membership, pin equations, PG routing, NDRs, ports and native row alignment must remain verified; native Liberty equation comparison and an actual inverted-buffer negative control are required. Original 20/4/8/8ns clocks, 5% timing derate and all-corner setup/hold checks remain unchanged. Existing signal routes are discarded because pin positions change.

Preparation is not timing closure. It must be followed by fresh routing, RC, all-corner STA, unchanged-candidate topology validation and final antenna/DRC checks. Hold regression must be assessed on the resulting routed candidate, not assumed absent. Final PHY and chip signoff remain OPEN.
