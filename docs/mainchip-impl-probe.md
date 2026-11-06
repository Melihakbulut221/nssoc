# Main-chip placement-to-global-route timing probe from RTL

Branch `analysis/impl-probe`, `scripts/impl_probe.py` and `.github/workflows/cloud-evidence-summary.yml`. Each variant runs the following in one hosted job:

- The firmware build and native Yosys synthesis use the same environment as the boot candidate (`check_soc_corrpre_pcie_mbist_native_boot.sh`): packet-async PCIe, system and Ethernet MBIST, logic boot ROM, CORRPRE register file, `abc -D 20`.
- `prepare_pcie_mainchip_pnr.prepare` builds the unchanged packet-SoC LibreLane configuration. Only the listed overrides are applied.
- LibreLane 3.0.5 runs `PacketInterfaces` from `Yosys.JsonHeader` up to, but excluding, detailed routing. That covers floorplan, the 20 fixed SRAM placements, PDN, placement, CTS, the capped post-CTS repair, global route, antenna repair and the capped post-GRT repair.
- An OpenROAD STA reads the final database with all three corners, the physical SDC, propagated clocks and the PDK's `LAYERS_RC`. It runs a fresh global route and `estimate_parasitics -global_routing`, then `report_checks -corner` for each corner.

These are global-route estimates, not extracted timing, and nothing here is a candidate. LibreLane's own mid-PnR STA steps report only one corner (`nom_fast_1p32V_m40C`), which is why the per-corner step exists.

## Per-corner worst slack after global route (run42097143810)

Setup worst slack per clock group, in ns:

| Variant | Corner | clk_i | pcie_clk_i | asynchronous | eth_rx_clk_i | eth_tx_clk_i |
|---|---|---:|---:|---:|---:|---:|
| baseline RTL, density 40% | slow | -12.98 | -16.44 | -6.45 | -3.60 | -4.22 |
| | typical | -0.83 | -9.58 | -2.81 | 0.56 | 0.01 |
| | fast | 6.16 | -5.62 | -0.69 | 2.89 | 2.50 |
| baseline RTL, density 60% | slow | -12.12 | -9.73 | -7.56 | -2.98 | -3.26 |
| | typical | -0.17 | -5.09 | -3.54 | 1.04 | 0.86 |
| | fast | 6.68 | -2.60 | -1.15 | 2.73 | 3.08 |
| register-slice RTL, density 60% | slow | **-9.69** | **-9.32** | -7.53 | -2.29 | -2.47 |
| | typical | **1.41** | -4.45 | -3.40 | 1.52 | 1.46 |
| | fast | 7.82 | -1.61 | -1.04 | 3.59 | 3.69 |

Hold worst slack is within -0.91 ns everywhere. The worst hold is fast-corner `clk_i` with the register slices; slow and typical hold are within -0.26 ns.

Post-CTS-repair attribution from run42066000930 (LibreLane's one-corner report; `pcie_clk_i` worst setup): baseline at 40% -1.79 ns, register slices at 40% -0.95 ns, register slices at 60% -0.41 ns. Both changes help independently. The register-slice variant at 40% failed global routing with congestion (GRT-0116) in that run; its rerun is in run42097143810.

## What this says about closure

- The register slices and 60% placement density close `clk_i` at the typical corner and bring the slow corner from -12.98 to -9.69 ns.
- The slow corner (1.08 V, 125 C) still needs about 30 ns for the Ibex paths against the 20 ns period. `pcie_clk_i` at 4 ns is still about 9 ns short in its internal logic. The asynchronous (reset recovery/removal) group is -7.5 ns.
- Synthesis already maps with the most aggressive delay target (`abc -D 20` is read as 20 ps; see the comment in `syn_soc_top.sh`). The remaining levers are therefore architectural:
  - an Ibex pipeline with the writeback stage and request register (`SOC_CORE_WB_STAGE`, `SOC_CORE_REQ_REG`, already supported by `syn_soc_top.sh`);
  - deeper pipelining of the PCIe link layer, or a lower PCIe logic clock;
  - reset-tree work for the asynchronous group.
- Run42120851358 probes the first lever at 60% density: `SOC_CORE_WB_STAGE=1`, with and without `SOC_CORE_REQ_REG=1`. A pipeline change alters the core's cycle behaviour, so any adoption needs the native boot gate-level run as well.

## Core pipeline and carry mapping (runs42120851358 and42140031564)

Every variant below uses the register-slice RTL. Slow-corner setup worst slack after global route, in ns:

| Variant | Density | clk_i | pcie_clk_i | asynchronous | typical clk_i |
|---|---:|---:|---:|---:|---:|
| reference | 60% | -9.69 | -9.32 | -7.53 | 1.41 |
| `SOC_CORE_WB_STAGE=1` | 60% | -12.40 | -9.37 | -7.11 | -0.42 |
| `SOC_CORE_WB_STAGE=1`, `SOC_CORE_REQ_REG=1` | 60% | -12.41 | -12.21 | -8.23 | -0.30 |
| `SOC_SYNTH_PREFIX_ADDER=1` (Kogge-Stone `$lcu`) | 60% | -9.89 | -9.07 | -8.35 | 1.12 |
| `SOC_SYNTH_PREFIX_ADDER=1` | 70% | **-8.57** | **-8.34** | -7.39 | **2.07** |

- Neither core pipeline selector helps. `SOC_SYNTH_PREFIX_ADDER` is a new opt-in knob in `syn_soc_top.sh`; at 0 the script is unchanged. Kogge-Stone carry mapping alone is neutral, presumably because ABC already restructures the carry logic. Density 70% gives the best slow corner so far.
- Run-to-run spread from placement looks like about 1-2 ns. The critical path itself is the Ibex execute path from the register file read (see `docs/mainchip-sta-measurement.md` on `analysis/mainchip-sta`). It remains about 8.5 ns over the 20 ns budget at the slow corner.

## Register file without inline SECDED (run42257277688)

This is a measurement for the architecture decision, not a design change. `IBEX_REGFILE=upstream` drops the register file's SECDED codec; `ibex_fault_port.py` ties the fault port to zero, and `CORRPRE` is off. Everything else matches the Kogge-Stone reference rows above: register-slice RTL and `SOC_SYNTH_PREFIX_ADDER=1`. The synthesised `soc_top` area is 1483614 um^2.

Setup worst slack after global route, in ns:

| Variant | Corner | clk_i | pcie_clk_i | asynchronous | eth_rx_clk_i | eth_tx_clk_i |
|---|---|---:|---:|---:|---:|---:|
| upstream register file, density 60% | slow | -7.74 | -8.65 | -6.01 | -2.76 | -2.10 |
| | typical | 2.62 | -4.00 | -2.39 | 1.00 | 1.66 |
| | fast | 8.70 | -1.43 | -0.21 | 3.14 | 3.79 |
| upstream register file, density 70% | slow | **-6.55** | -8.74 | -7.71 | -1.42 | -1.30 |
| | typical | 3.48 | -4.11 | -3.44 | 1.71 | 2.16 |
| | fast | 8.77 | -1.46 | -0.97 | 2.86 | 4.10 |

Compared with the SECDED register file, slow-corner `clk_i` moves as follows:

- At 70%: -8.57 to -6.55 ns.
- At 60%: -9.89 to -7.74 ns.

Removing the codec is worth about 2 ns, so it does not close the slow corner by itself.

The worst slow-corner `clk_i` path at 70% still arrives at 28.3 ns against 21.8 ns required, through about 50 cells. Most of the delay sits on single-drive cells driving 6-8 loads:

- `buf_1` fanout trees take 0.6-0.7 ns per stage.
- A `nand2_1` takes 1.16 ns, an `xnor2_1` 1.15 ns, an `inv_1` 1.37 ns, a `nor4_1` 2.02 ns and a `nand4_1` 1.34 ns.

The capped post-GRT repair leaves these cells unsized. Two levers apply to either register file:

- Uncapped setup repair, which `docs/mainchip-sta-measurement.md` measured at about 3-6 ns.
- A shorter execute path.

`pcie_clk_i` (4 ns) and the asynchronous group are unchanged by the register file.
