# Candidate PCell geometry inventory

The v36/v37/v38 intrinsic trials share a54um native MOS width and several changed HBT emitter counts/resistor dimensions. Their wire RC remains the original reference and their MOS diffusion fields are an explicit hypothesis. A passing intrinsic trial must still become a new physical design.

The exact existing PDK/runtime creates17 actual isolated PCells: MOS widths36/54um; HBT Nx2/3/4/5/6; input/bias resistors width4/6/8um at lengths0.9/1.2um; collector resistors width32um at lengths1.0/1.2/1.6/2.6um. Requested dimensions are compared against native PCell parameter readback, and the resulting bounding boxes and GDS drawings are retained.

The old sampler placement generator checks every raw cell top below50um at each fixed row position. This inventory reports that necessary dimension test from real geometry, without assuming that a parameter change fits. It does not check the complete placements or routes, does not prove AS/AD/PS/PD, and does not run whole-macro DRC/LVS. Those remain explicit false/unproven fields in the report. No accepted layout or circuit is replaced.

All generation and controls execute on GitHub-hosted runners. Raw failures and source/runtime hashes are preserved.
