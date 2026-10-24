# Measured drive/load trial: do not promote to layout

Run40017175142 successfully re-read both original full34.25ns v47 captures,
reproducing all120 HBT and all four sampler checks. Exact source/parts hashes
and compact observations are in the accompanying receipt. The native candidate
remains electrically rejected; successful diagnosis does not accept the circuit.

The original early C/D sampler outputs still each have64 samples below100mV.
C has three wrong-sign samples. Its worst clock-to-valid time is48.90625ps;
D reaches45.78125ps. Original output limits and sample positions remain fixed.
All native device bounds passed, but phase/VI limits did not.

Against the original v44l39 early record, C's minimum signed native input
resistor source differential at the capture aperture fell64.572->56.161mV,
and its HBT base differential fell30.602->27.644mV. At +0.1UI those base values
fell34.283->29.849mV. At +0.3UI C master output minimum fell158.824->121.683mV
while the external sampler minimum became negative. These are observed values
at identical original apertures, not a causal attribution to a single device.

At the aperture C's sampled minimum master VCE was410.182mV versus418.971mV
previously. This narrow observed headroom discourages an unqualified further
current increase or simple common-mode shift. Input resistor endpoints, base
wire drops, upstream loading and selector operation must be considered together.
The32 tail width and32 resistor-length changes were a combined hypothesis;
they cannot isolate which term caused the degradation.

Do not create accepted candidateGDS from v47. The next circuit hypothesis
should address the measured upstream/input-transfer limitation and device
headroom together, retaining fixed clocks, source bits, loads, full capture,
all original sample/phase/VI/device gates and freshRC qualification afterward.
Internal100mV markers in diagnostic tables are not additional acceptance gates.
