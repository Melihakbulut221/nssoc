# Measure the remaining retime wire load after v21 collector shortening

The new passive-network review reads the exact full v21 transistor/wire
composition from rejected late capture39444824145, cross-bound to capture39443205735.
It preserves the previous native-node reconstruction, independent resistor graph
solution and controls. Every R/C value comes from the new extraction.

The purpose is to measure actual collector/filter-input/filter-output wire
capacitance and effective metal resistance after removing7761.4um of parent
horizontal routing. Compare against retained v20 measurements; the reduction in
wrong samples does not by itself reveal which load now limits data transfer.
No intrinsic resistor, model, topology, phase or sampling gate is edited here.
This diagnosis runs alongside the exact-wave latch review, not a new simulation.
Qualified RF/substrate PEX and full PHY acceptance remain unproved.
