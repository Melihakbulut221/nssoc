# C/D actual input-divider and headroom diagnosis

The v35 full-transfer reports show all255 C/D bit inputs below the diagnostic100mV marker at master steering, while original output data/timing acceptance still fails. The input marker is not itself an acceptance gate or proof of root cause.

In the load16/nominal_late record, actual AC follower output common mode spans1.3386–1.3985V and BD1.3561–1.4204V; their differential extrema reach about0.19–0.23V. The physical sampler includes4um-wide input resistors of1.2um length and bias resistors of0.9um. A static ideal divider estimate cannot establish the loaded transient behavior or selector headroom.

This cloud diagnostic binds each C/D master base to its actual native input and AVDD resistor terminals and observes source/base differential, common mode, resistor/wire voltage drops, and master data/track/hold VCE. It retains all original active samples for statistics and observes all255 original bits at eight fixed aperture offsets. It neither infers resistor currents nor fits gain. A future smaller input resistance must still preserve all original full transistor and sampler checks and receive actual candidate layout/RC verification.

Both original load16 early/late complete captures are restored by immutable hashes; all120 HBT checks and all4 sampler results must reproduce exactly. Native simulation is not restarted. Eight binding/interpolation fault controls reject missing, ambiguous, wrong-net/model and duplicate terminals and extrapolation. No existing source, candidate, load, clock, threshold or accepted physical status changes.
