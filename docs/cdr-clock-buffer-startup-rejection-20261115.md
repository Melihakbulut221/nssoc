# Clock buffer startup rejection and next candidate

Run 43713326015 at 9d2c5d9d360d9ac3d79aa321eeea985ebcb040ec failed. Authenticated derived artifact 14162305555, SHA256 34559d8fa8c5830869cb3a1032c1d173fd2561f2c153b9d939c22136db063b7d, reports temperature-limiter NaN and timestep too small at 68.2974 ps on q.xtn.qnpn13g2. Only 234 transient rows were emitted for buffer-100ff. Native exit zero was correctly rejected by diagnostic and waveform gates. Native artifact 14162230681 is retained in GitHub.

The three direct capacitive-load controls completed; buffered cases did not qualify. This is not a passing PHY result.

The next candidate replaces the externally forced 0.5 mA reference ramp with a supply-referenced ideal 3.2 kohm sizing resistor into the diode-connected reference transistor. This removes an ideal source that can force bias beyond a low rising supply; it is a hypothesis, not an established root cause. Device sizes, clock waveforms, supply ramp, load sweep, native model, solver tolerances, maximum timestep and failure gates are unchanged. Native results must determine convergence, actual bias, swing, delay and device voltages. No thermal model is disabled.

This remains a pre-layout topology screen with ideal passives. Full loaded 650 circuit, physical resistor implementation, PVT, extracted layout and main-chip integration remain open.
