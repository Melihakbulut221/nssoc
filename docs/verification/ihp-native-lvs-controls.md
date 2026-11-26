# SG13G2 transistor-level LVS diagnostics

KLayout 0.30.7, IHP PDK c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c. The unchanged sg13g2.lvs deck SHA-256 is 5de8c4b60398f95d5a596b265dc4f723f2a208c908b71284770180dbe62bd234. The existing detailed-route powered netlist SHA-256 is 241000a2bae24a0548c7eda14b5bbe436dfd8555a5714c021f9b48617df52a28. It references 2705 sg13g2_inv_1, 16 dual-port 256x16 SRAM and four single-port 2048x64 SRAM instances.

Run in a writable scratch directory with PDK pointing to the pinned ihp-sg13g2 directory.

```sh
deck="$PDK/libs.tech/klayout/tech/lvs/sg13g2.lvs"
std="$PDK/libs.ref/sg13g2_stdcell"
sram="$PDK/libs.ref/sg13g2_sram"
check() {
  klayout -b -r "$deck" -rd input="$1" -rd schematic="$2" -rd topcell="$3" -rd run_mode=deep -rd report="$PWD/$4.lvsdb" -rd target_netlist="$PWD/$4.cir" > "$4.log" 2>&1 || return 1
  make check-native-lvs LVS_DB="$PWD/$4.lvsdb" LVS_TOP="$3"
}
sed -n '/^.SUBCKT sg13g2_inv_1 /,/^.ENDS/p' "$std/cdl/sg13g2_stdcell.cdl" > inv.cdl
sed 's/MX1 Y A VSS/MX1 Y VDD VSS/' inv.cdl > invfault.cdl
for c in inv invfault; do check "$std/gds/sg13g2_stdcell.gds" "$PWD/$c.cdl" sg13g2_inv_1 "$c"; done
n=RM_IHPSG13_2P_256x16_c2_bm_bist
check "$sram/gds/$n.gds" "$sram/cdl/$n.cdl" "$n" sram256
```

Read the native comparison verdict and the LVS database. The inverter extracted two MOS devices and matched. Reconnecting only the NMOS gate to VDD produced a mismatch. The independent PDK unit example sg13_lv_nmos extracted 28 MOS devices and mismatched its 28-device reference under these invocation settings. Its cause remains unresolved.

The unchanged SRAM GDS (420b5223d14e2f873a2464849e3decbbec2b5b16b3c6a0f8cd2bb21b0d52365b) and CDL (1b307d5bd84ba57087717c1d1e631959352c6d20a27167b3ed08f637e3d312a8) produced a 53 MiB LVS database and a mismatch. KLayout LayoutVsSchematic.xref.each_circuit_pair reported 24 Match, three NoMatch, four Mismatch, one Skipped. The skipped pair is the SRAM top. The NoMatch pairs are RSC_IHPSG13_CDLYX1_DUMMY, RSC_IHPSG13_DFPQD_MSAFFX2P and RSC_IHPSG13_WLDRVX8. The four schematic-only entries were CINVX2, CINVX8, FILLCAP4 and FILLCAP8 under the RSC_IHPSG13_ prefix. Root cause remains open. The remaining single-port macro and full layout still require native LVS. These controls used no rule waivers or macro black boxes.

## Native report acceptance

Run from the repository root with fresh per-run output paths. The gate reads the KLayout comparison database, verifies the expected root on both sides, requires exactly one matching top pair and rejects any circuit status other than Match. Record the deck, layout, reference and report identities separately. The existing Magic/Netgen snapshot metric uses another report format.

Run the pinned inverter regressions with `python3 scripts/test_native_lvs_gate.py`. Add `--sram-dir DIR` for the two archived SRAM databases named in that script. The checksum pins refer to the measured artifacts. Independently regenerated databases can be checked directly with the make target. A rejected negative control is expected. EdgeSeal integration remains conditional on the actual die and pad floorplan.
