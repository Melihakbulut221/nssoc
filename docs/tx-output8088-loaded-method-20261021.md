# Actual8088 loaded TX preparation

The new parent contains the previous8074-device input/core and the14-device
output, joined by actual routed metal. Its full model contains8088 devices,
139838 resistors and99650 capacitors. The physically verified165 ports plus
the explicit wire capacitance reference form166 model arguments.

The preparation replaces the old whole8074 instance and the separate schematic
output instance together. It removes the obsolete public mp/mn boundary and
maps op/on/tvdd/tr to the independently verified physical output ports. No
ideal alias recreates the removed internal boundary. All native terminal
voltages and HBT currents are observed, including finite body/contact nodes.

The604 HBT observations now comprise593 in the actual parent and11 external
clock macro HBTs; all5376 MOS fingers remain observed. The original256-bit
pattern,34ns transient, maximum time step, three sampling phases, solver
settings, external loads/feeds, device bounds and interface gates are retained.
The ten adaptation controls must reject output polarity or supply/bias swaps,
duplicate output, missing HBT/MOS/observations, wrong reference plane, stale
schematic probes and an added external load. Original source/evidence checks
remain mandatory. Both nominal and actual leaf-select fault decks are prepared.

This is preparation only. A new model needs a fresh source-bound checkpointed
native run; no8074 native trajectory is reused as8088 evidence. Existing8074
runs continue unchanged. Full loaded waveforms, clock modulation/intermacro
connections, bias/supply physical integration, qualified RF/body/device-access
PEX, CDR/PLL, mainchip integration and original-clock timing remain open.
