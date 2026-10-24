# CDR follower-current and clock-steering limits — 2026-10-23

Hosted run39876477694 completed all four existing-record analyses. Each exactly reproduced all120 HBT bounds and all four full sampler checks from the original rejected34.25ns capture. No new SPICE simulation was run. The source-bound diagnostic is complete; CDR acceptance remains false.

For early-data v39, shortening follower pull-down length from1.8 to1.5um raised AC positive mean native collector current from1.110704 to1.575410mA; BD positive mean current rose from1.188381 to1.657743mA. Minimum currents remained positive. AC output common mode fell from1.349648 to1.332931V, while differential extrema increased from−205.854/+185.147mV to−226.575/+200.424mV.

That improvement consumes C master-selector headroom: its minimum active VCE fell from0.412677 to0.400970V, only0.970mV above the original0.4V lower limit. D minimum is0.424391V. Do not extrapolate another pull-down reduction as safe, and do not treat this nominal margin as PVT closure.

C's minimum master output at37.5ps rose only from98.016 to100.764mV; its slave input is98.332mV and slave output still has33 wrong signs at that diagnostic phase. The internal100mV markers are observations, not new acceptance conditions. The original output gate still fails. C master-off/slave-on median edge observations remain about14.63/14.87ps and D about14.21/14.44ps; follower bias did not materially change them.

Actual differential clock zero crossings at physical selector bases arrive much earlier: early l15 C pairs show roughly4.05–4.22ps, D3.65–3.83ps, A3.72–3.90ps and B2.24–2.49ps relative to matching external clock edges. These are nearest-edge descriptive medians, not a causal per-bit delay decomposition. They do show that the14–15ps current-steering marker cannot simply be described as external clock arrival delay. Changing external phase or acceptance windows is not a repair.

Next bounded design hypothesis: test selector emitter-area changes at unchanged tail current to examine switching/current-density versus added junction loading. The1.8um follower parent has more measured C headroom than1.5um. Compare slave-only Nx3→4 against masterNx2→3 plus slaveNx3→4, retaining data/hold devices, tail MOS, external stimuli, loads and every original gate. This hypothesis is not yet simulated or accepted; increased area can itself reduce VCE margin and increase clock capacitance. It requires exact native graph binding, actual whole-record simulation, and later real candidate layout/freshRC. A remains outside its original output margin/delay limits and must not be omitted.

The complete immutable summary/parts hashes, full compact observations and all physical clock-pair metadata are retained in the accompanying evidence JSON. The old54um MOS row-height obstruction and all full-loop/PVT/layout/PHY obligations remain open.
