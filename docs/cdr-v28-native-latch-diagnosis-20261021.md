# Actual v28 transfer delay diagnosis

Both cases of39570507312 reproduced the complete original native waveforms, all120 HBT bounds and all4 sampler checks. Every sample at0.6 and0.9UI passed100mV; the original0.3UI samples account for all margin and polarity failures. This does not waive37.5ps clock-to-valid. All observed wrong C/D samples are on changed expected bits.

At the expected edge, C master input is below the diagnostic100mV marker for222/255 early and197/255 late bits (minimum42.88/48.10mV). D is below for193/255 in both, with64 wrong signs at that edge. The physical clock-selector banks do steer: nearest-edge median slave track-on offsets are approximately12.6–14.3ps. These medians are observations, not a causal delay proof. The two original VCE failures belong to C sampler Nx2 clock selectors.

Before changing current or resistor geometry, the transfer follow-up reads both real ac/bd emitter followers' bases, emitters and collector currents, using native-cluster identity to match the actual parent pins. It retains and reruns every original diagnosis check and adds only measurements. This separates measured loading/current cutoff from speculation; no ideal drive, shifted oracle or weaker gate is introduced.
