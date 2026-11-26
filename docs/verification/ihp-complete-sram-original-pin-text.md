# Original pin texts in complete SRAM hierarchy

Used the full original GDS and full unchanged CDL of each macro at c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c. Each diagnostic copy adds four 8/25 text elements in one cell definition. Deleting those four reproduces the source GDS byte for byte, including geometry, hierarchy, original text, and stream padding. Supply spelling retains the exclamation marks. Coordinates below are integer GDS units of 1 nm.

| Macro / selected cell | A | Z | VDD! | VSS! | Original populated cells / elements |
|---|---|---|---|---|---|
| 1P 2048x64 / WLDRVX8 | 510,1695 | 2806,1995 | 840,4200 | 1155,5 | 134 / 8852 |
| 2P 256x16 / CINVX2 | 410,1625 | 825,2015 | 565,4155 | 540,-45 | 165 / 9458 |

Reproduce each run with the full master names (use the RSC_IHPSG13_ prefix for the leaf). Add --crossed to the projection command for the deliberate A/Z control.

```bash
python scripts/diagnose_sram_macro_pin_text.py "$SOURCE_GDS" "$LEAF" "$NEW_GDS"
klayout -b -r "$DECK" -rd input="$NEW_GDS" -rd schematic="$ORIGINAL_MACRO_CDL" -rd topcell="$MACRO" -rd run_mode=deep -rd report="$DB"
make check-native-lvs LVS_DB="$DB" LVS_TOP="$MACRO"
```

* Dual port: the deck logged a mismatch. The gate returned make code 2, reporting 24 Match, 4 Mismatch, 3 NoMatch, 1 Skipped and zero matched top pairs. An additional reference root was RSC_IHPSG13_DFPQD_MSAFFX2P. CINVX2 remained unpaired on the layout side of the comparison database despite 138 reachable occurrences in the source GDS. In the original reference hierarchy the count is 122. Eight physical DEC04 blocks each have three CINVX2 instances. The corresponding CDL definition has one CINVX2 and one CINVX4. This localizes a difference in partition and drive-cell representation; equivalence would require proving the actual parallel connections and device parameters.
* Single port: both source hierarchies contain 1024 WLDRVX8 instances. The deck logged a mismatch. The complete saved database specifically skips the top, naming layout-side CDLYX1_DUMMY and WLDRVX8 among the failed child comparisons. The separate make gate returned 2 after its KLayout reader was killed (137). Streaming the completed database gives direct negative evidence independent of that reader.
* Negative control: the crossed dual-port macro also failed. The whole-macro pair counts alone cannot distinguish the deliberate error from the pre-existing mismatch. Selecting the CINVX2 leaf from each of those very same complete streams with the original leaf CDL and the unchanged deck in flat mode distinguishes them. Both report VDD! versus VDD and VSS! versus VSS. Only the crossed copy additionally reports A versus Z and Z versus A. The port gate rejected both. The [previous diagnostic](ihp-leaf-labels-and-pcie-event-profile.md) used the reference's supply spelling in its isolated positive control.
* CDL SHA-256 before and after: 1P 734647f8383209c7e08fc8e66a2914a3acaa33e1848b9ff33b6a4a2ed3c2ec61, 2P 1b307d5bd84ba57087717c1d1e631959352c6d20a27167b3ed08f637e3d312a8. Deck SHA-256 5de8c4b60398f95d5a596b265dc4f723f2a208c908b71284770180dbe62bd234. Compressed comparison database SHA-256: 1P e3eecbe33e6add6e67a1eedc9cf58b6eeca17e7b7e2dddb2c80fa707d9a76283, 2P 9d8340dc40d590d026986aa923a69bf219e6c2e348f42310eb132063e2378531, 2P crossed be9ff4e47fb0f3c83c6423fe2d02c6cefb9f47499f03c6b178602907a0489a06.

Neither full macro achieved a complete match. The prior soc_top connectivity verdict stays open.
