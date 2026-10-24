# Original loaded full-wave tests on the v30 physical RC model

The cloud matrix waits for exact native audit/composition run [39708600220](https://github.com/Melihakbulut221/nssoc/actions/runs/39708600220), source e20a8aa2da383cfeffaf8662c173923e87d12366. Both jobs must pass and all immutable summaries and archives must match before any native electrical simulation starts.

The circuit includes the actual 476 devices and freshly measured 17918 resistors / 12850 capacitors. The exact change map preserves every original dependency hash, test equation and threshold. Only provenance namespaces, native measured R/C census and model identity change from v29.

All four cases remain: nominal early, nominal late, stopped clock and disabled VI bias. Preserve the original 34.25 ns duration, 256 bits, 1104 capture columns, externally driven 8 GHz clock, 150 fF sampler loads, 50 fF XOR loads, 37.5 ps sample deadline, 100 mV sample margin, 30 mV phase threshold, 50 uA VI current and all transistor operating limits. Fault cases passing means detecting their faults; it is not nominal acceptance.

Full raw waveforms, logs, failure reports and source manifests are retained in immutable cloud result releases. No local simulation, decimation, dropped vectors, shortened duration or relaxed electrical limits.

Nominal electrical acceptance is not yet established. Even a passing externally clocked phase-detector model does not prove a complete closed-loop serial Gen3 x4 PHY, qualified RF/ESD/PEX or final mainchip setup/hold closure.
