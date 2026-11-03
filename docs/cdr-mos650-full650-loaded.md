# Actual650 whole nonlinear loaded circuit

This source assembles the actual650 native identities with all28634 current metal resistors,18476 wire capacitors, seven intrinsic MIM models at their original exported nodes, and all50 physical gate-port macros. Each native MOS is represented by N same-dimension intrinsic models with multiplicity1/N; N=1,2,4,8,16 models are built. All200 contacts,2046 device terminals and finite body contact models remain explicit.

The selected partition/case executes the original256-bit loaded waveform: external8GHz clock,2ns start,34.25ns stop,0.3125ps maximum step,150fF sampler loads and50fF XOR output loads. Original sampling, phase, device-voltage and current thresholds remain unchanged. All124 HBT and200*N MOS currents/terminal voltages are captured;192*N tail currents aggregate into the original16 physical stage groups derived from42 source families.

All computation and native acquisition run on GitHub-hosted infrastructure. A native invocation has a five-hour bound within the hosted six-hour job limit, leaving publication time; this is not a guarantee of convergence. Every result, deck, waveform, protected input and native log is preserved on success or failure. Numerical convergence, startup warnings, electrical rejection and incomplete execution remain failures.

This is the next whole-circuit experiment, not a claim of a passing circuit. A selected passing case does not close partition refinement, full PVT/fault cases, extrinsic gate capacitance, substrate spreading, material corner qualification, recovered-clock operation, complete serialGen3x4, mainchip routing or final setup/hold.

## First complete assembly and startup rejection

Run41732402949/sourceb3768d5f3201cf661b15bc85f431ba46be3eee48 produced all five whole-circuit partitions with all native bindings, then failed the full N1 nominal_late simulation. Native ngspice returned zero but its diagnostics reported temperature NaN, singular matrices and a timestep collapse at3.125fs; the waveform had only two rows. The result is a failure. Native outputs remain in release433293515 and the derived receipt records all warnings.

This successor restores the original bench-local spinit and SPICE_SCRIPTS startup environment that the first adapter omitted. It also selects the existing Sparse1.3 backend, with verified native option readback, to test whether the KLU startup breakdown is backend dependent. This is a hypothesis, not a proven cause or repair. Original physical models, sources, loads, waveform length, time-step bound and all electrical/diagnostic acceptance limits stay unchanged. Both numerical and electrical failure remain fatal. The two changes are recorded separately; a subsequent controlled comparison is required before attributing improvement to either.

The existing repository backend harness supports both solvers. Official ngspice documentation: https://ngspice.sourceforge.io/docs.html .
Derived diagnostics are now uploaded before the large native archive, so an error can be examined while immutable native publication continues.
