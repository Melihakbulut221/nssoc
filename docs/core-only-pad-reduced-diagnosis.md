# Reduced pad diagnostic circuits

These are explicitly changed test circuits, not replacements for the chip pad and not signoff candidates. The original pad runner and pinned PDK subcircuits remain unchanged. Three reductions at the same PVT, KLU/Gear2/itl4=100,1ps maximum step,50ns duration and unchanged error tolerances:

- clamps: native NMOS and PMOS clamp subcircuits plus native DCN/DCP protection diodes. Replace gate decoder with ideal gate voltage sources matching the on/off levels;0-to3V or3-to0V transitions last120ps. Remove input receiver. This deliberately changes gate loading/drive, so its timing is not full-pad timing.
- decoder: native GateDecode and its level-shifter hierarchy alone with unloaded ngate/pgate outputs. Remove output clamps, protection diodes and input receiver. Pad clamp current is irrelevant here; do not impose an active drive current check on an unconnected pad.
- decode_clamps: retain native GateDecode, both output clamps and DCN/DCP diodes. Remove only the input LevelDown receiver. Its input loading is therefore changed and it remains diagnostic only.

All six data-state/control cases execute even after a failure. Gate voltages and clamp currents are captured; full duration, finite/increasing samples, maximum step, native configuration and numerical diagnostics remain checked. Synthetic tests cover every reduction plus incorrect solver readback, preserving aggregate failure. No production acceptance is possible for a reduced fixture, even if all captures complete.

Full pad remains numerically incomplete on0-turnoff across5/2.5/1ps and both Sparse/KLU; latest evidence at cloud-pad-step-evidence-20261118. Core detailed route44337630426 is independent and must remain running.
