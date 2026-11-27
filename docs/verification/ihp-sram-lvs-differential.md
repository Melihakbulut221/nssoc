# Single-port SRAM and dummy-cell LVS

Using the unchanged deck, command and versions in [the native controls](ihp-native-lvs-controls.md), set `n=RM_IHPSG13_1P_2048x64_c2_bm_bist` and run `check "$sram/gds/$n.gds" "$sram/cdl/$n.cdl" "$n" sram2048`. GDS SHA-256 48be5102bf97e56daee4cda1f63eaf6e7bb3450a68d48a2825060b1172011d00. CDL SHA-256 734647f8383209c7e08fc8e66a2914a3acaa33e1848b9ff33b6a4a2ed3c2ec61. An initial 200 s wall-clock cap interrupted database serialization. A fresh run completed, returned exit code zero and explicitly reported a mismatch. The completed database SHA-256 is c8a61ed8e7619399aeb4c36265a16ad20cb0d2ec997b89ede5180af335a80e40. Its circuit-pair section records 23 matches, five schematic-only circuits, two NoMatch pairs (RSC_IHPSG13_CDLYX1_DUMMY and RSC_IHPSG13_WLDRVX8) and a skipped top. Both supplied SRAM layout/reference pairs therefore remain open.

## RSC_IHPSG13_CDLYX1_DUMMY

Use the dual-port GDS as input with this exact subcell as top. Copy its single .SUBCKT through .ENDS block from the corresponding PDK CDL. In the standalone LVS database, the layout has named pins Z and A. The CDL exposes A, Z, VDD and VSS. Inside the complete dual-port hierarchy the extracted pair has two additional anonymous terminals. Their connectivity to parent supply nets still needs independent verification. NMOS and PMOS drawn lengths/widths matched at 0.30/2.49 and 0.64/3.24 micrometres respectively. The A–Z resistor is 0.60 by 0.26 micrometres on both sides. Extraction identifies res_metal1, R=2.30769230769, while the schematic reader reports LVSRES, R=0.

Each row below changes only a disposable schematic. All runs use the same original GDS and deck.

| Change to original standalone CDL | Native verdict |
|---|---|
| None | Mismatch |
| Rename lvsres to res_metal1 | Mismatch |
| Remove VDD and VSS only from the .SUBCKT pin list | Mismatch |
| Rename the resistor and add r=2.30769230769, retaining all pins | Mismatch |
| Rename the resistor and remove the two power pins from the header | Match |
| Also specify the extracted resistance | Match |
| Additionally rewire the NMOS gate from vdd_r to A | Mismatch |

The experiments isolate a difference in resistor-class and pin representation for this standalone comparison. They do not resolve supply connectivity in the parent or qualify an altered reference. No PDK, product CDL, hierarchy mapping or rule settings were changed.
