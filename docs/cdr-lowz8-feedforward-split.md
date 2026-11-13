# CDR isolated feedforward screens

Reference: rejected bd10_slave_parallel2_lowz8, run 43497945915.
Authenticated topology: run 43514448538, source 3a8b12502002364554957ba6027b0610be00335d. All six MIMs bridge the upper divider resistor; 50 gate subcircuits are excluded from top-level wire collapse.

Two independent variants: acff4 doubles A/C MIM side lengths 7.2 to 14.4 um (4x geometric area); selectff4 doubles only selector MIM side lengths 9.6 to 19.2 um. Each retains lowz8, BD10 and slave multiplicity 2. Compare each to the same reference, never treat these as sequential changes.

Hypothesis: stronger transient feedforward may reduce observed downstream delay. Risks: sampler loading, overshoot, hold-margin loss and device stress. No guarantee of improvement. Frozen timing, sign, amplitude, phase, device and simulator-success checks must all pass. No relaxed thresholds or bypasses.

Existing interconnect parasitics are reused for screening only. Changed capacitor dimensions require a fresh physical implementation, extraction, DRC and LVS before any layout acceptance. External 8 GHz clock remains; this is not closed-loop CDR, a complete PHY or main-chip integration. Only result-only artifacts are safe for local derived-data inspection; other archives contain native circuit/wave data and remain cloud-only.
