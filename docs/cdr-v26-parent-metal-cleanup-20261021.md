# V26 parent metal cleanup candidate

Native diagnosis39529481164 reproduced the unmodified wire-graph rejection
against the passing476-device physical candidate39525872386. It located eight
terminal-free M3/M5 components at the former C/D sampler input pad positions:
23.18 square micrometres on M3 and9.54 on M5. No port or device terminal belongs
to these components. This diagnosis is not an electrical acceptance.

The new cloud-only generator recomputes each component from the immutable native
LVS database, requires exact cluster/area/bounds identity, and requires every
removed polygon to lie entirely in direct parent metal and outside all child
drawings. Four corrupted diagnosis identities must fail. The serialized GDS must
equal the original on every layer except these exact removed regions; all16
instances, child geometry, text, schematic and LEF remain unchanged.

The independent full560-rule native DRC, deep and unsimplified flat476-device
LVS, original fault controls, all16 placements/eight native leaf drawings, and
original strict wire-component graph all run again. The graph adaptation changes
only input paths, preserving its terminal ownership and no-label-union gates.
A pass requires111 connected components and1382 terminals.

Historical parent source pins remain archived in the immutable baseline metadata;
new generation inputs bind the actual restored files by SHA256. This is a physical
candidate. Fresh wire/MIM extraction and original full-waveform electrical gates
are still required. Full serial PHY and final mainchip timing remain open.
