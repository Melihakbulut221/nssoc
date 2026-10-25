# Native CDR v2 path diagnosis

The full-wire nominal v2 run failed. `cdr-v2-path-review-cloud` restores each original capture in a separate GitHub-hosted job and does not start a new transient. Summary, manifest, archive part and selected-file digests bind the raw data to run 39081843889.

The review reproduces the original sampler wrong-sign counts and voltage margins and every HBT minimum active VCE. It maps failed devices through native terminal identities, reports actual shared-emitter differential-pair input and output swings, and measures collector-to-base voltage differences along the physical conductors. It retains every original acceptance failure.

The static wire report groups all 8956 resistors and 7079 capacitors by their extracted connected component and lists the largest terminal-to-terminal shortest resistor paths. Those path sums are upper bounds on effective resistance, not effective resistance measurements or qualified delays. Incident wire capacitance excludes intrinsic device capacitance. These diagnostics prioritize physical changes; they do not prove closure or authorize replacement of the waveform by a simplified model.

No local checkout, waveform or CAD file is created. The existing waveform remains in its original GitHub release; the new release contains only derived reports and restore receipts.
