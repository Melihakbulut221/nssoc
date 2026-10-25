# Cloud-only continuation, 22 October 2026

The local nnsoc workspace is empty. The separately preserved legacy run-log directory is absent. Source changes are committed directly through GitHub APIs without a local checkout, and all tests, simulations and physical-design execution use GitHub-hosted runners. Native evidence stays in immutable release assets; this change does not remove any cloud evidence.

CDR follower v31: leaf and full parent physical validation passed; fresh extraction and MIM capture passed. Source d63e597c03d297a6f566907ecc6514c1103c0903 launches run 39721805172 for the unchanged raw conservation/MIM identity and exactly-once composition gates. Its results must be checked before full original loaded waveforms.

TX normal run 39711301866 completed all 34 ns with 77,695 rows and 14,182 columns. It is rejected: 85 of 604 HBTs fail unchanged safety gates, zero of 5,376 MOS devices fail, and the original output oracle observes 14 wrong-sign and 51 below-100 mV samples across the three original sampling phases. The worst minimum post-startup VCE is 0.216836 V. Interface checks also fail in CMOS, final, level-4 and level-8 groups. These are measured failures, not runner exhaustion. The paired negative-control run 39711311480 must be interpreted separately. Preserve both complete raw results.

Mainchip continuation 39710297457 still requires an actual terminal report before route quality or final timing can be claimed. The latest accepted checkpoint remains the saved process from 39696184554. PLL remains saved at 892.691 ns from 39674830790: sparse native continuation and the original 5,106-column prefix reader are qualified, but production logical archive integration and complete 1 us acquisition remain open.

The machine-readable companion records observed run states and next steps. Full serial PHY, mainchip integration and final timing are not accepted. No clocks, waveform lengths, vector sets, physical rules, fault controls or electrical thresholds were relaxed.
