# Antenna-clean resized core: fresh extraction admission

Run 44427090834, head 8a27e631912305e5a184c0268279374283705dc9 completed with zero router DRC, zero violating antenna nets and zero violating antenna pins. Artifact 14486835187 SHA256 d32941fd839e1f0a505d1f0a57de09ea83f12ca5f3958bb7510b83a452bf5993 and all 18 outputs were verified. Final ODB SHA256 234841fdb17170a7973e3315d2e493e9220c13808a881fa43e262e63a3b02d76 has 106647 instances. Round three added nine diodes; all 18 local power terminals passed. Instance, connectivity, special-wire and visible signal-geometry checks passed.

This closes native antenna and router DRC checks for this particular six-resize core candidate, not full foundry DRC, transistor LVS or production readiness. It does not contain the separate two load-isolation buffers. Prior actual RC showed setup failures; none are presumed fixed by antenna repair.

The new extraction wrapper authenticates all three additional antenna rounds and exports all 1396 post-baseline diodes. It retains 20 ns, 5% derating and all three corners. Extracted RC is nominal only. SRAM characterization, qualified min/max RC, external I/O, full-chip integration and manufacturing approval remain separate gates.
