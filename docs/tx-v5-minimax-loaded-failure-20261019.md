# Minimax TX loaded waveform: rejection retained

Native run39268446646 nominal job118115200444 completed the unchanged34ns/256bit simulation in12507.22seconds, exit0 with zero numerical diagnostics. All1674devices,116611wire resistors and77516capacitors were retained. The1.865GB raw capture has77616rows and3004columns; its1.61GB preserved archive stays in cloud release storage.

The electrical gate rejected the circuit:
-123wrong-sign samples and146below100mV out of768 at the unchanged0.3/0.5/0.7UI phases. Per-phase wrong signs:60/37/26.
-24HBT devices fail minimum post-start VCE0.4V; worst0.362661847V at xtree.xd0109. No MOS device failed.
-CMOS, level16 and level8 input groups passed. Level4 has144wrong signs; final input group822wrong signs across the original6912samples per group.
-No phase fitting, bit-oracle substitution or threshold changes are allowed.

The new cloud path review restores the exact immutable waveform, contract and geometry-bound model. It must reproduce the entire original review byte-for-byte as JSON before diagnosing native terminal voltage minima, each physical input group and all31native clock paths. Matching an edge is diagnostic only; original electrical gates remain failed. This does not establish complete Gen3x4 PHY or mainchip timing acceptance.
