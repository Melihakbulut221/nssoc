# Fresh cleaned-v26 wire and MIM validation

Physical clean-parent39531419538, all four extraction stages39532277767 and
MIM capture39532836299 passed their native gates. The actual new RC count is
17674R and12694C, with all seven intrinsic MIMs and938 physical reference points.

The next cloud audit independently checks every raw resistor/capacitor and each
source/replacement/export MIM identity, including13 raw-RC and9 intrinsic faults.
Composition preserves all476 native devices and every raw RC token, includes
each intrinsic MIM once, and retains19 composition faults. Model:
nssoc_cdr_pd476_retime_mim_wire_v26.

These are model-construction gates, not loaded-waveform or full-PHY acceptance.
Run the original complete early/late/fault cases only after both stages pass.
The latest PLL initial report exposed an immediate disk-budget checkpoint at
94.76GB raw capture and11.94GB free; current continuation39502073954 remains live.
Do not fork it or weaken the original1us/all1694-terminal capture.
