# TX wire24 native composition

The 28-route width candidate passed native physical checks and fresh metal RC
extraction. Its original workflow failed only at release publication; recovery
39341750762 restored the exact source bytes without rerunning native CAD.
The complete original report is pinned in
[evidence](evidence/tx-fast-wire24-extraction-recovered-pass-20261020.json).

This stage restores that candidate's archive (SHA-256
bcf58ad5044105b25379f39c3de24b7b5b92f4937ca047034e8914f73a1bfce9),
never the older wide-signal RC. Source checks require exact extraction report
equality, fresh physical summary equality, original immutable ancestry,
unchanged placements/topology and the explicit 28-route geometry delta.

The original 1674-device model binding, 116611 resistor / 77538 capacitor
composition, six malformed-composition controls, resistor-component topology
recovery and 124 physical input-leg / 372 base-terminal probes remain.
The interface binder uses the unchanged original topology but probes the new
GDS and native LVS database. Both actual endpoint fault controls remain.

All native work runs in GitHub Actions. A successful composition is a model
integrity result only. Loaded waveforms, native device screens, qualified PEX,
four lanes, recovered-clock behavior and main-chip timing remain required.
The next step is binding the clock network and running the original waveform
conditions against this exact candidate, preserving every failed result.
