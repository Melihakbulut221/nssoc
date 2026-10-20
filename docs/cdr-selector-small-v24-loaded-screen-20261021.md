# Original loaded electrical gates on the actual v24 CDR

The v24 sampler clock selectors use native Nx2 geometry; the other sampler devices, currents, loads and parent routing remain unchanged. Fresh parent DRC/LVS, reference-plane binding, intrinsic model conversion, wire RC and MIM capture have passed. The electrical workflow waits for the exact raw audit/composition run39495976408 and verifies its original13wire,9MIM and19composition faults before using the model.

All electrical stimuli and acceptance checks are unchanged from the v23 rejection:256source bits,external8GHz clock,original early/late phase offsets,.3125ps timestep,150fF at each actual sampler data collector and50fF at XOR outputs. All120HBT/46MOS native terminal/current probes are retained. Reducing selector multiplicity must pass the same per-emitter current limits; it is not an exception.

Initial cases are nominal early/late and the original stopped-clock/disabled-VI negative controls. Remaining PVT, constant-data, full recovered-clock loop and full PHY/system qualification are still required. A nominal pass alone will not close those requirements. Failed waveforms and all original samples are published.
