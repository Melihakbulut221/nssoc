# Native master/slave diagnosis: original CDR rejection retained
Both39326235115 cases completed diagnostic replay, reproducing all116original HBT checks and4original sampler checks. The original fullwave remains rejected. The100mV internal-node marker is diagnostic, not a new input acceptance requirement.

C/D master inputs remain below the internal100mV marker at all8examined phases, both cases. At0.9UI the late case still has30C and98D wrong output signs (early30/105). A/B outputs settle later and are valid by0.6UI at the examined points; this does not satisfy the original0.3UI/37.5ps output gate. No shifted sampling window is accepted.

The measured positive track-minus-hold collector currents never overlap at the saved sample points in either case. This observation alone does not rule out races or prove clock correctness. Native master outputs and slave inputs can differ because physical nodes on a shared logical net are connected through extracted wires.

The exact parent hierarchy is scripts/cdr_retimed_localbus_v12_parent_plan.py: all four samplers use rx_sampler_input_drive_v13. C/D receive A/B through actual ac/bd rc_retime macros (4um-wide5.4/12.6um resistors and7.2um MIM feedforward capacitors); the sampler input adds its native bias network. Next trace these actual input-chain resistor/MIM and intrinsic terminal waveforms, separating amplitude, common-mode and settling loss before changing real devices/geometry. A new repair still requires native DRC/LVS, fresh complete RC and the unchanged fullwave/device gates.
