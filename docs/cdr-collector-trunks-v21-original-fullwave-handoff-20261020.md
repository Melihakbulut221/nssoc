# CDR v21 original loaded full-wave handoff

The new full-wave workflow is bound exclusively to validation run 39444363134
at e6f07163c4011a1acb5fb3c29366709bd232b02e. Each native case waits for successful
raw audit and composition, verifies both published archives and their source
receipts, and refuses to replace a receipt or restart a live prerequisite.

The source-delta guard proves that the original full-wave stimuli, sample
phases, loads, transistor limits, simulation horizon and tool/model SHA-256
literals remain unchanged. Candidate identity and the measured capacitor census
are the only adaptations. The current model has 484 native devices, 17,674 R and
12,704 C. Fresh plane and binding evidence supplies every internal terminal.

Four independent cases remain: nominal_early, nominal_late, clock_stopped and
vi_bias_off. The nominal cases still require all original sampling and device
gates. The two faults must be detected. The external 8 GHz clock, 256 bits,
34.25 ns horizon, 150 fF sampler and 50 fF XOR loads are retained. Passing these
tests would be a standalone loaded CDR result, not a closed-loop serial PHY,
PVT/RF qualification or final mainchip timing closure.

Evidence and execution remain on GitHub runners and releases; nothing is
downloaded or executed as CAD in the local workspace.
