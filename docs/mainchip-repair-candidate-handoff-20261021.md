# Proved postroute repair candidate: fresh-route handoff

Native repair 39669577979 completed with 226 additional positive buffers,
nine equivalent cell-size changes in the logic proof, and 336 instance records
changed including connectivity. All 152762 original instances were retained.
The native geometry, power/ground/NDR/ports, twenty SRAM and clock-pin geometry,
fixed PCIe clock wire, equation proof and actual inverted-buffer rejection passed.
The new candidate has 152988 instances. This is not routed timing closure.

The handoff job restores this exact proved ODB/netlist and all original
PDK/SRAM/SDC/tool inputs through the previously validated native preflight.
It rejects changed candidate hashes, missing inversion proof, changed clock wires
and changed SRAM geometry. Only stale data wires are removed; all non-wire DEF
and every unrelated net record must remain exact. Three real DEF corruption
controls and a separate native fixed-clock comparison remain mandatory.

State files discard stale DEF/SPEF/PNL/SDF and timing metrics. Original 20/4/8/8ns
clocks, 5 percent derate, uncertainty and raw config remain unchanged.
After this preparation, generate new global guides from current pins and use
resumable native detailed routing. Fresh extraction and original-clock three-corner
STA, antenna/disconnect/DRC/LVS and serial-PHY work remain outstanding.

No local CAD or archive is used; all evidence is published by hosted Actions.
