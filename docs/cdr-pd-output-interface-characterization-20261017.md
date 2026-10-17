# Actual phase-detector output interface before V/I integration

The next missing physical connection is the retimed detector output into a real V/I converter and loop filter. Its input common mode and voltage extrema must come from the actual extracted-XOR/sampler circuit, not an assumed logic-level output.

The cloud-only output analysis restores all six nominal/hot/cold early/late waveforms from native run39056756395, matches their exact saved summary and waveform hashes, reads the four output legs, and recomputes the original average phase signal as a parser cross-check. It reports all-time/active leg extrema and common-mode/differential ranges. Only the disposable cloud restoration is removed; original captures remain in source releases, with exact receipts retained. No local files or native reruns are needed.

This is design-input characterization, not a new electrical pass. The original50fF external loads and ideal bias references are still present. The next circuit must connect real converter device terminals to these exact outputs, retain all original sampler/XOR gates under the added load, check converter device bounds and signed phase-to-current transfer at both early/late polarities, then drive the actual filter/VCO in a closed loop. HBTprocess corners, mismatch, interblock RC, four lanes and mainchip remain additional requirements.
