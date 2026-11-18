# Isolated inverter LVS: independently reproduced mismatch

Run 44420487897, head be0b2f5ca26b2a3ba5c7a070bb65e31d8e18b8ba, artifact 14481213667, SHA256 97a083eaf3abe5cbe1597d04c986351a9750e9fba456dfa706a83bd5955c2832. All 56 manifest output hashes verified. Both deep and flat official-deck comparison fail with three devices on each side.

The isolated layout extraction joins i and vdd into one net; the native cross-reference explicitly identifies a potential short between reference I and VDD. Extracted tap: A=0.624p, P=4.76u; reference: A=624.1f, P=3.16. Thus adding a missing unit alone would not establish equality. Context differs from the parent-pad extraction; do not call this a proven physical short without investigating geometry and label connectivity.

Next diagnostic reads original, hash-authenticated old and current GDS with KLayout 0.30.9; compares inverter, tie, decode and pad geometries; exports unmodified recursive primitive polygons and labels for inverter and tie. It changes no geometry, reference netlist or LVS rules. Source files and outputs are hashed. Use the resulting coordinates to locate the i/vdd merge and compare standalone and parent context before proposing a physical repair.
