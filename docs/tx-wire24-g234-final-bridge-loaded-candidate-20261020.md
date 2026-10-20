# Full32 TX: physical final clock bridge with fixed group2/3/4 bias

Composition run39375939797 passed native2 + actual3R8C with all12 composition corruptions rejected. Model SHA256:ad89ed29fe7507aad77844e2bdc4eec1e1aef224403ac34a3f321df5a53e61ff. Its five device terminal identities, finite contact and all native wire elements are preserved.

This new candidate adds exactly one XFINALBRIDGE across final sp/sn in the fixed g234 experiment. Original differential PWL sources,25ohm source resistors, common-mode reference, data, phases, full34ns duration,604HBT/512MOS limits,116611R77538C core and original acceptance gates stay unchanged. The source-delta check permits only the new adapter call, result directory/scope and additional protected model files. Removing the bridge/include and added probes must recover the entire original deck byte-for-byte.

The actual native bridge archive and original PDK resistor model are hash-verified before use. All four internal bridge nodes and both public signal voltages are captured. Six actual deck/probe faults must reject before SPICE. Normal and real leaf-selector-fault runs execute independently. The previous g234-only run remains live as the comparison; it is not cancelled or treated as passed.

This is a loaded engineering experiment, not acceptance. Original clock modulation, supply/substrate/wire-reference boundary assumptions and intermacro ideal connections remain explicit. Assembled bridge layout/mainchip wiring, qualified PEX/substrate, resistor reliability, PVT and full PHY remain open.
