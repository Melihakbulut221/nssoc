# Native minimax model identity and original full-wave screen

Read-only comparison39267792841 passed all1674 devices:589HBT,248rppd,
837taps,162 fixed public net names and exact device parameters. Macro-local
primitive geometry determines identity independently of circuit topology.
174 internal node names changed with native enumeration; a bijection recovers
the same topology. Formal public port order also changed. The original builder
reads the actual subcircuit formal list and maps each public net by name;
it does not assume the prior ordering. No pin-order workaround was added.
Missing-device, changed-size, wrong-terminal and physical-identity-swap faults
all failed as expected. Full comparison receipt is retained.

This push starts nominal and actual swapped-leaf-select fault simulations
against the exact new full wire model. Only the two accepted model SHA values
change in the original builder, and only its import changes in the clock adapter.
Source-delta and native identity guards preserve all stimuli, clocks, solver,
34ns/256 original bits, sampling phases, voltage/current and interface gates.
All116611R/77516C and11 physical clock-reference macros are retained, with
604HBT/512MOS screened and124legs/372data-base probes.

This remains a component electrical experiment, not full serialGen3x4:
external clock modulation, frontend/bias/output physical integration, recovered
clock/jitter/BER, PVT/substrate/RF qualification and mainchip closure remain.
No result is accepted before the complete original waveform checks finish.
All execution and full captures remain on GitHub.
