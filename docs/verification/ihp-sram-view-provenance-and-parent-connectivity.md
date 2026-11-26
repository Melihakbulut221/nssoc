# SRAM provenance and parent-device connectivity

Compared git hash-object on each local input with the blob entry in the [IHP commit tree](https://github.com/IHP-GmbH/IHP-Open-PDK/tree/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_sram). The [earlier input receipt](ihp-complete-sram-original-pin-text.md) records SHA-256 and macro dimensions.

| View | Upstream and local Git blob | Bytes |
|---|---|---:|
| Single-port GDS | 7b0c7dadf8e881780643e85b769765bd9c7227dc | 602558 |
| Single-port CDL | f6fc8e8e89d04ec5530f93f1c63f9e5200ceace8 | 1296737 |
| Dual-port GDS | 306f28a413ec067096b5b0b9d19a26901b81a850 | 632832 |
| Dual-port CDL | eb4e99f1efa5238ae4080ece63f5d6bd4463cbaa | 415685 |

Both dual-port views last changed in IHP commit 6d9d0a9971cfbefe83e579915e8efeec82a8feee. The last single-port GDS change was b6cbdfb1f524fbe5ae8dcf87a7fd00b735e3e6fc (layout layer fix), and the last CDL change was 3b47c37498acd9e293b77c86ef0079a92780b34b (MOS model names). These establish a common distributed PDK snapshot. No mismatched distribution or distinct SRAM compiler release was established.

## Connectivity experiments

* DEC04. Select RM_IHPSG13_2P_DEC04 from the dual-port GDS and use the original CDL block RM_IHPSG13_256x16_c2_2P_DEC04 with all nine reachable child definitions byte-preserved. The original names prevent native top alignment. In a diagnostic GDS copy only, renaming the selected cell to the reference name allows the unmodified flat deck to reach comparison. The extracted clock inverter from ECLK_H_BOT to ECLK_L_BOT has one 0.705 µm NMOS and one 1.62 µm PMOS. From ECLK_L_BOT to internal net $25, the second stage has **two parallel NMOS and two parallel PMOS** on the same input, output and respective bulk rails, each with those same widths and 0.13 µm length. The summed widths equal the schematic CINVX4 (1.41 and 3.24 µm); $25 also feeds the word-line output stages. This resolves the local drive-width discrepancy. The whole DEC04 still has NoMatch and zero matched top pairs; the native report names ECLK_H_TOP, ECLK_L_TOP, ECLK_H_BOT and ECLK_L_BOT. Extracted branches between BOT and TOP are res_metal2, R=2.30769230769, L=0.6 µm, W=0.26 µm. The unmodified CDL's MET2RES definition uses lvsres with the same drawn dimensions. No device alias was applied.
* Single-port WLDRVX8. In the native hierarchical extracted circuit, each WLDRVX8 call exposes VDD!, output, intermediate node and input. For every one of the 1024 instances, the **parent** has exactly one NMOS between the intermediate net and VSS!, gated by input (1.8 µm), and one between output and VSS!, gated by the intermediate net (1.41 µm). Both bulk terminals are VSS! and both lengths are 0.13 µm. Interchanging input and output in this terminal query produces zero matching pairs for all 1024. This accounts for the two devices missing from the leaf listing without inserting any transistor.
* The six single-port CDLYX1_DUMMY instances expose VDD! and VSS! in the first two extracted positions. Five have successive A/Z chain connections. Its extracted A–Z branch is res_metal1, 0.6 × 0.26 µm, whereas the original CDL specifies lvsres. Electrical acceptance of the model correspondence and macro connectivity remain open.

## Bounded native reader

Through make check-native-lvs the large first-detail soc_top database now rejects the explicit skipped top in 3.51 s with 495832 KiB maximum child RSS; the compressed single-port report rejects in 4.53 s at 495772 KiB. The streaming precheck can only reject. All potential successes still require the complete KLayout comparison/port checks. The healthy inverter passed in both raw and gzip forms. The faulty inverter and crossed-port control failed for their expected reasons.

## 4118-byte PCIe scope activity

With the same compiled VVP images, original selected reseed case and seed 4118, load the [read-only VPI module](../../hw/soc/tb/pcie_scope_activity_vpi.c) alongside cocotb. Build with gcc -shared -fPIC -O2 and the pinned Icarus include/iverilog directory, then add -M<module-directory> -mscope_activity to the [cached replay](ihp-leaf-labels-and-pcie-event-profile.md). The positive passed at 1052 ns. Value-change callbacks: candidate framer 31961, reference framer 31937, candidate and reference ingress 3040 each, other 7469. The deliberately corrupted image still raised PCIE_CYCLE_MITER_OUTPUT_MISMATCH at 576001 ps. These counts cover exposed nets/registers; they exclude memory words and do not assign CPU time or include every internal VVP event. Full 18-case coverage remains outstanding.
