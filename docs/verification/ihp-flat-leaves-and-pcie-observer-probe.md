# Flat SRAM leaf comparison

The experiment used the same native SG13G2 deck and source GDS/CDL at PDK c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c. The existing [complete first-route comparison](ihp-sequential-sta-and-first-route-lvs.md) remains the full-layout baseline. For each leaf use the original containing SRAM GDS, extract the single matching .SUBCKT through .ENDS from that SRAM's original CDL, and run the original deck with topcell set to the leaf. Set run_mode=flat and retain the deck defaults, including flag_missing_ports.

| Containing SRAM and selected leaf | Extracted MOS | Comparison |
|---|---|---|
| Single-port 2048x64, RSC_IHPSG13_WLDRVX8 | 2 NMOS, widths 1.41 and 1.8 µm, and 2 PMOS, widths 0.9 and 6.48 µm | Deck reported mismatch |
| Dual-port 256x16, RSC_IHPSG13_CINVX2 | 1 NMOS, width 0.705 µm, and 1 PMOS, width 1.62 µm | Deck reported mismatch |

The selected roots reproduce the reference MOS populations, including the NMOS absent at the wordline-driver boundary in the full hierarchical report. Neither isolated extracted root exported the four reference pins. The native inverter database, for example, reports four port mismatches and four pin pairs missing the layout side despite a circuit-pair status of Match. Debugging parent-to-child connectivity still requires the full hierarchy. The separately bounded flat run on the entire dual-port macro produced no comparison database before termination. Full-chip equivalence remains open.

The repaired gate checks the presence, status and case-insensitive name correspondence of each expected top pin pair. Through make check-native-lvs, the native standard-cell inverter control passed, the faulty inverter failed, and both flat SRAM leaf databases failed on unmatched top ports. The previous gate had incorrectly accepted those two databases.

# PCIe miter observer experiment

The full original node can emit elapsed-wall-time case events from the repository root using `python scripts/profile_pcie_v23_miter.py <fresh-directory>`. It calls make test with the exact 4118-byte node and polls the existing nested simulation log. It forwards the subprocess exit code.

Diagnostic only: select start_without_abort_reseeds_and_discards_prior_epoch with the standard 4118-byte miter and cocotb runner. In a scratch generated wrapper only, compare the original ring observer loop against one with the additional loop guard `ring_offset < reference.framer.occupied`. Keep both original guarded assertions, address expression, time delays, stimulus, complete RTL pair, fault observer and Icarus model. The proposed guard stops iterating through inactive ring entries. Repeat both variants with the original miter's public_data_inversion fault. All four trials ran via make test.

Both unmutated runs passed at 1052 ns. Cocotb case wall times were 48.13 and 46.52 seconds respectively (one sample per mode). Both deliberate faults produced PCIE_CYCLE_MITER_OUTPUT_MISMATCH at simulator time 576001 ps. The observed time difference does not establish a meaningful 18-case speedup. The original observer remains active. Full regression coverage has not been credited for these trials.
