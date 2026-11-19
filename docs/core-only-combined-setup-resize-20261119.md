# Combined candidate common setup driver ECO — 2026-11-19

PCIe and Ethernet remain excluded. Clock period remains 20 ns (50 MHz), derating 5%; no timing exceptions relaxed.

Source route: run 44446105491, head a537abf3e2f06e598cc785c2364e68b6c7df90f4. Extracted timing run 44448236669 has slow setup 19 violations, worst slack -0.19486635079340425 ns; hold zero across slow/typical/fast. Fast hold margin is only +0.037160608975109796 ns. This is not production signoff.

Native inventory run 44450381253 confirms matching physical pins and available nor2_2 and buf_4 masters. All 19 setup paths traverse nssoc_sta_i_2496 and fanout2484. Candidate resizes nor2_1 to nor2_2 and buf_1 to buf_4 respectively; Liberty functions must match. All other cells are frozen, all clock routes preserved. Exactly five connected data nets are invalidated. Placement legality, unchanged connectivity, unchanged unselected DEF records and positive-area supply contacts are mandatory.

Next: selected routing with native encoded FIXED guard, independent geometric short/connectivity checks, antenna checks, fresh netlist/DEF/RC extraction and all-corner timing. Preparation alone is not a timing result. Reject regressions; retain the previous combined candidate.

## External interface decision

The user confirmed that package, PCB, QSPI memory model and connected devices have not been selected. External I/O timing is unresolved; no board delay, device timing, package parasitic, interface speed or production approval is inferred. Continue internal timing independently. Before external signoff, select these components and derive traceable min/max input/output constraints for SpaceWire/SPI/QSPI and other retained interfaces.
