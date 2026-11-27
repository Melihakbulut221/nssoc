# Dummy-cell supplies in the original SRAM hierarchy

Trace the .cir written by each original, unmodified-deck GDS comparison and the separately supplied PDK CDL. The script unfolds instances reachable from the named macro top, checks port arity and propagates positional bindings. Run python trace_sram_supply.py FILE MACRO_TOP on each input. The preceding ihp-sram-lvs-differential.md identifies the GDS/CDL sources. No edited diagnostic CDL enters this trace.

| Macro | Extracted CDLYX1_DUMMY pin order | Top rails of the anonymous pair | Reachable instances in extraction / original CDL |
|---|---|---|---|
| RM_IHPSG13_2P_256x16_c2_bm_bist | $2, $3, Z, A | VDD!, VSS! | 38 / 38 |
| RM_IHPSG13_1P_2048x64_c2_bm_bist | $1, $3, A, Z | VDD!, VSS! | 6 / 6 |

Both original CDL definitions use A, Z, VDD, VSS. Every reachable instance binds the last two formals to VDD! and VSS! respectively. Example layout instances X$201 (dual-port) and X$20032 (single-port) can be inspected in the extracted netlists. Example CDL paths are XB_DLYH/XIDM<9> and XA_DLYH/XIDM<5>. These examples are witnesses for their own representations; the count is exhaustive without requiring signal-instance name alignment.

Extracted CIR SHA-256: dual-port 5d0c2ba1daac3710a54735f5eb5b0c64ebf86f81d72e76bf47b0849b8ee04676; single-port 259f356c31c15f9af6731f071d0f579056fe114ff86ebf72febf4b1a2e577376. CIR headers include a generation timestamp.

In the detailed-route powered Verilog (SHA-256 241000a2bae24a0548c7eda14b5bbe436dfd8555a5714c021f9b48617df52a28), all 16 dual-port and four single-port instances bind VDD! and VDDARRAY! to VPWR and VSS! to VGND. This last observation is a netlist port-binding check. Physical top-level rail continuity still requires full-layout extraction. The original transistor-level LVS mismatch remains open for both macros.
