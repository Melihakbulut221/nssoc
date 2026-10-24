# Sampler drive/load compensation experiment

Completed v46 native-record diagnosis40008988737 reproduces every original
HBT and sampler result while preserving the original postprocessing failure.
Neither reduced hold area nor reduced data+hold area closes the original
37.5ps deadline: early C/D remain about45.5--45.8ps and A about38.6ps.
The original signed30mV phase and50uA VI criteria also fail. At+0.1UI,
some C/D master-to-slave inputs remain below the internal100mV diagnostic
marker; that marker is not a new acceptance gate.

Use the measured v44L3.9 parent, not a promoted v46 candidate. One source-bound
candidate increases all32 actual sampler tail MOS widths by1.25 and reduces
all32 sampler intrinsic collector/track-bleed/hold-bleed resistor lengths by0.8.
This tests greater drive and lower resistive time constants together, with
nominal current/resistance compensation. Actual current scaling, DC swing,
headroom and speed are NOT inferred from the nominal arithmetic.

Master tail widths36->45um; slave54->67.5um. Single-finger diffusion area and
perimeter are recomputed using the existing declared0.34um hypothesis,
not presented as extracted candidate geometry. Collector lengths scale
2.6->2.08um (A/B master),3.9->3.12um (C/D master),1.2->0.96um (all slaves).
Bleed lengths also scale0.8. All lengths stay on the5nm parameter grid;
that statement does not replace actual DRC or PDK layout validation.
All HBT areas, follower/input-divider parameters and other devices stay
unchanged from v44L3.9. Tail banks and loads are selected through actual
native clusters, with missing/changed/ambiguous graph controls.

Both measured parent phases pass original device gates. Nominal1.25x
parent peak current/emitter remains below3mA; the narrow parent VCE margin
requires direct new-wave verification. No bounds are relaxed.
Both original early/late records run in GitHub with all476 devices,
17918wireR12850wireC, full34.25ns/256bits, original8GHz clock/bias sources,
150fF sampler and50fF comparator loads, solver, timestep and every
device/data/phase/VI gate preserved.

This is an exploratory frozen-wire experiment, not a physical candidate.
Only a useful full electrical result can proceed to actual newGDS,
native intrinsic extraction, freshRC, DRC/LVS, PVT/timestep/closed-loop
and serial mainchip integration. Original rejected runs remain evidence.

## Source correction before any native transient

Initial40011066168 stopped before native activation: the strict master
track-bleed parent-length check expected6.4um but the actual model contains
38.4um. The original error and both case manifests remain preserved.
Independent inspection of all eight actual master track AND hold resistors
in the immutable v32 native composition verifies W1um/L38.4um.
The corrected recipe requires exactly38.4um and scales it to30.72um.
Slave track12.8->10.24um and hold9.6->7.68um remain unchanged.
Extra controls reject the incorrect6.4,4.8 and28.8um master assumptions.
No waveform, acceptance threshold or equality check is changed.
