# Native CDR parent AVDD feed repair

Both immutable localbus full captures still fail the original sampling and device
limits. Read-only review run 39269746336 reproduces those failures with unchanged
sources. Early/late review summaries are pinned separately under docs/evidence.

The observed sampler load-resistor supply-wire loss averages approximately
220–230 mV; the worst observed AVDD terminal is about 300 mV below the external
rail. HBT129/147 violate the original 0.4 V VCE minimum. These are measured
failures, not signoff exceptions. A shortest resistance path is not effective
resistance and does not predict the transient correction.

The exact passed parent 39249146302 routes AVDD from a 64 µm global TopMetal1
rail through 3.2 µm horizontal TopMetal2 branches approximately 930 µm long.
The new candidate adds one parallel supply feed for every one of the eleven
AVDD-consuming macros: 32 µm TopMetal2 through the preceding intermacro gap,
16 µm TopMetal1 beside the macro, and native 4×4 / 4×1 TopVia2 stacks.
No transistor, resistor, capacitor, signal conductor, child placement, reference
card or public interface is changed. Original narrow branches remain.

Actual native shapes must prove clearance before generation proceeds. An
independent reconstruction requires every drawing layer to equal the frozen
parent plus exactly the specified native metal/vias. Three physical-region
corruptions must be rejected. The immutable passed parent's GDS is hash-verified; the regenerated baseline
must match all its actual drawing layers, reference cards, LEF and physical metadata. The unchanged parent checker still requires all 560
DRC categories, strict deep/flat 484-device LVS and its nine fault controls.

A physical pass is only permission to perform fresh native wire/MIM extraction,
intrinsic composition and the original complete early/late and fault waveforms.
No old RC, ideal rail clamp, phase shift or electrical gate waiver is allowed.
Full serial Gen3 x4 PHY, closed-loop operation, mainchip integration and final
setup/hold are still open. All execution and evidence storage are in GitHub.
