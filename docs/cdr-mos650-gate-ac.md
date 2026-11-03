# Native gate impedance characterization before physical gate-network composition

Use the same complete pinned Ngspice engine and PSP/PSPNQS model library as the original loaded simulation. Enumerate every unique W/L/AS/AD/PS/PD tuple from all200 actual MOS units and retain current native device IDs. Compare rfmode=0 and rfmode=1 at explicitly declared0.8 V gate and0.6 V drain bias,1 MHz through10 GHz. Use pre_layout=0 with actual extracted areas/perimeters. This comparison does not replace the complete circuit test or certify the RF model's applicability to the physical gate layout.

Keep every native model readback, complex input impedance, numerical diagnostic and failure. Require finite complete frequency measurements and unchanged source/model files. Extract the bound technology's full resistance/contact variant statements as well. The older500 layout and provisional unit expansion are not substituted for the actual650 geometry.

Interpret the results before building a distributed physical poly/contact network; do not assume rfmode=1 matches a single-contact chained gate topology, or add an external gate network on top of an overlapping compact gate model. Full intrinsic MIM composition, complete loaded electrical gates, full PHY and final timing remain open.
