# v37 C/D divider impedance candidate

The completed cloud input-bias diagnosis39856218758 reproduces all120 HBT and all4 sampler gates on both original load16 early/late captures. At the original expected C/D capture edge, the worst signed HBT input differential is only27.3/32.9mV for C and16.4/19.2mV for D. These internal values are diagnostic, not a new acceptance limit.

More importantly, C master-track minimum VCE is0.42030/0.42123V across the full active interval, leaving about20–21mV above the unchanged0.400V limit. Reducing only the input resistor may lower base common mode and consume that headroom. Actual resistor endpoint and HBT-base means also differ by about41mV; a simple ideal divider calculation cannot substitute for the real wire/loading network.

v37 retains the separately running v36 slave_drive15_load12 experiment and changes only the eight actual C/D input/bias resistor widths together:4um to6um (cdbias15) or8um (cdbias20). Lengths stay1.2um and0.9um. This retains the nominal geometry ratio while lowering intrinsic resistance; actual transfer gain, common mode, follower loading and selector headroom may still change and must pass the original full native simulation.

The parent v36 result is pending, not accepted. It carries32 slave HBT area edits,16 MOS width/diffusion hypotheses and16 slave resistor edits; v37 adds8 master input/bias resistor edits,72 total. All other native primitive cards and every17918R/12850C wire card remain byte-equivalent to the baseline. Reversing all72 parameter edits must recover the exact original composition.

All original8GHz clocks, biases,256 bits,34.25ns/1104 columns,150fF sampler/50fF XOR loads,37.5ps/100mV output gate and device/phase/current gates remain intact. Both early/late cases run for both variants after source and geometry corruption controls. Every failure is retained. These frozen-wire intrinsic experiments are not GDS/DRC/LVS/fresh RC/PVT/loop or PCIe PHY acceptance; a useful circuit needs that full physical flow afterward.
