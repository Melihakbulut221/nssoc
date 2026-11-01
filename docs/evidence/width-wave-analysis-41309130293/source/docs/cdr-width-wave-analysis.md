# Width-trial data-path diagnosis

The 12-resistor width trial 41306148937 passed the unchanged 30 mV phase gate (37.0801368476 mV) but failed every original sampler/comparison data gate. This cloud-only readout reuses the qualified full-row reader and original measurement functions from eb9b2602db8d971e405310142ab88d3fc652d308. It authenticates every archive member, reproduces all six original numerical measurements and the phase integral, then reports source-conditioned divider/buffer errors and connected transistor voltages/currents. There is no simulator, candidate edit, new layout, new RC extraction or acceptance.

The diagnostic reader's prior assumption that phase must fail is replaced with equality to the producer's phase decision. The 30 mV threshold and all six original data gates remain unchanged. The width trial remains rejected. A new control covers a valid measured phase above threshold. All 33 existing reader/measurement controls remain.

Native archives and waveforms stay on GitHub runners. Derived text is published as Actions artifacts. The original model, complete output index and release assets are immutable inputs; these numerical observations do not certify full serial PHY or final chip timing.
