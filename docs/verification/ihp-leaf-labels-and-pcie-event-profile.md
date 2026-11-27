# SRAM leaf GDS labels and extracted power nets

At PDK c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c both original SRAM leaves contain four text objects on GDS 8/2 (Metal1 pin). The native deck reads polygons on 8/2, text on 8/25, and connects metal1_con to metal1_text. At the original macro roots, pin polygons and text already occur on distinct datatypes: 352 texts on 10/25 and 200 on 50/25 in the single-port macro, and 212 and 64 respectively in the dual-port macro. Macro-root labels include a separate VDDARRAY! rail.

Original leaf-local label positions in 0.001 µm units:

| Leaf | A | Z | VDD! | VSS! |
|---|---|---|---|---|
| RSC_IHPSG13_WLDRVX8 | 510,1695 | 2806,1995 | 840,4200 | 1155,5 |
| RSC_IHPSG13_CINVX2 | 410,1625 | 825,2015 | 565,4155 | 540,-45 |

For a diagnostic copy, project the four original leaf texts at their original coordinates onto the deck's Metal1 text layer. Use the original leaf CDL supply names VDD and VSS. This naming convention is local to the extracted test cell. No macro-root rail alias was applied. For the negative control exchange only A and Z in the projected texts. Original streams, original CDL and deck are preserved. A recursive XOR of boxes, paths and polygons was empty on every layer for each of the four copies (eight populated geometry layers per leaf).

```sh
klayout -b -r hw/soc/flow/diagnose_sram_leaf_labels.rb -rd gds="$MACRO_GDS" -rd leaf="$LEAF" -rd mode="$MODE" -rd out="$COPY"
klayout -b -r "$DECK" -rd input="$COPY" -rd schematic="$ORIGINAL_LEAF_CDL" -rd topcell="$LEAF" -rd run_mode=flat -rd report="$DB" -rd target_netlist="$CIR"
make check-native-lvs LVS_DB="$DB" LVS_TOP="$LEAF"
```

Use mode original or crossed and a fresh copy path per run. Both correctly projected cells passed both the unchanged deck comparison and the strict repository port gate. Both crossed cells failed both checks. In the inverter extracted netlist A drives both gates, Z is the shared output, and the PMOS and NMOS bulk connections are VDD and VSS respectively. In WLDRVX8 the two stages share an internal net; their corresponding bulks also resolve to VDD and VSS. Passing diagnostic database hashes (SHA-256) were 1259b228631ff331c60c19f8e12c239867ea51f8f861b090e8ed518fe10ea25b for CINVX2 and b9184db56107b21e3b220d4e604bcec024379c8a6c57236c3f0306814fd054a5 for WLDRVX8. Integration of these cells into their original parents, global supply correspondence and whole-chip connectivity remain open.

# PCIe event and CPU profile

Replayed the previous original and public_data_inversion VVP images with the repository's cocotb Makefile and prepared Icarus runtime, the same 4118-byte configuration and selected deterministic reseed case. Set PCIE_WIDE_MAX_BYTES=4118, COCOTB_RANDOM_SEED=4118, COCOTB_ENABLE_PROFILING=1, and pass SIM_ARGS=-v. Use the exact existing SIM_BUILD and matching original VERILOG_SOURCES, a fresh COCOTB_RESULTS_FILE and COCOTB_TEST_FILTER selecting start_without_abort_reseeds_and_discards_prior_epoch. Both images retained their SHA-256 before and after replay (positive e875e0cea971a30dfa5a91479d902dc76ad538fca2ea1de13dd7e8ac7b22cdcd, negative 82ad8667d4bddead4d4579c90cf904fc42cd8778ddfb62840390e8f1682db28f).

The positive ran 64.04 s wall and 62.34 s user CPU. VVP reported 59.01 s in the execution phase, 1,316 time steps, 5,128,897 thread scheduling events and 1,180,082 assignment events. The cocotb profile attributed 0.320 s to its measured Python callbacks. The largest measured phase is simulator execution. These counters do not attribute CPU time to a specific RTL process.

Reusing the compiled image avoided recompilation. The positive reached 1052 ns and the negative raised PCIE_CYCLE_MITER_OUTPUT_MISMATCH at 576001 ps as in the clean builds. Cached negative wall time was 48.78 s. This single-case bounded replay compared with prior clean times of 89.11 s and 77.10 s, respectively, on separate runs. The full suite already shares a compilation across its 18 cases; these figures cannot be multiplied by 18. No default mode change or passing full regression is recorded.
