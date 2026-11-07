# PLL c5r3k: from the extracted-deck what-if to layout

Status: all four child macros pass native main DRC, deep and flat LVS and
their fault controls. Parent integration, RC extraction and acquisition have
not started. Nothing here is accepted.

## Origin

The c5_r3k what-if on branch `analysis/pll-divider-currents`
(`scripts/pll_divider_currents.py`, `docs/pll-first-divider-currents.md`)
edits the extracted RHI120/C8 PLL deck (release asset 668392118,
`cloud-pll-rhi120-c8-preparation/composition/pll845-mim-wire.spice`). The
frozen acquisition gate (`independent_analysis` in
`scripts/review_pcie_pll_acquisition_v1.py`, unchanged) returns `passed: true`
for it, and also for c5_r6k. The what-if changes are:

1. XD0375 W 6.4 -> 8 um (L 2 um).
2. XD0497, XD0498 W 4 -> 16 um (L 3.6 um).
3. XD0480-XD0482 and XD0490-XD0492 L 4.4 -> 4.93 um (W 8 um).
4. A new ideal 3 kOhm resistor in series with 5 pF from `vctrl` to `avss`.
   With 6 kOhm (c5_r6k) the gate also passes. XD0567/XD0568 are unchanged.

## Mapping from extracted instances to sources

The deck numbers devices in extraction order and loses the hierarchy. Each
device was traced back by its native nets in
`composition/binding/binding.json` (asset 668392118), using its neighbours,
its supply net and the ring HBT topology.

| Extracted (deck line) | Native nets | Source instance | Source file:line | Layout macro and generator |
|---|---|---|---|---|
| XD0375 (377) | S=div_avdd, G=$1634 (gate of the diode XD0374 = XPREF), D=$1635 (source of XD0376 = XPENABLE) | pump `xloop.xdet.xcp.xpsource` | `hw/soc/analog/pcie/pll_pfd_charge_pump_hv_v1.spice:69` (XPSOURCE), instantiated by `pll_pump_filter_hv_rhi120_c8_v1.spice:10` (XDET) | parent instance `pump` = `nssoc_pump_filter13_rhi120_c8_v1`. Built by `hw/soc/flow/make_pcie_pump_filter13_v1.py` (rows placed at `x = 30 + i*40`, line 271), driven by `scripts/cloud_pll_rhi120_c8_layout.py:16,45` |
| XD0480 (482) | vco_avdd -> $53 (MIM XD0576 11.2x11 = CP0, collector of ring HBT XD0379) | VCO `XRP0` | `hw/soc/analog/pcie/clock_vco_hbt_v6.spice:32` | parent instance `vco` = `nssoc_clock_vco_hbt_v6_local_v1_layout`. Built by `hw/soc/flow/make_pcie_clock_vco_v6_local_v1.py` (CIRCUIT line 15, RP/RN placement lines 53-54) |
| XD0481 (483) | vco_avdd -> $54 (base input of XD0381, i.e. p1) | VCO `XRP1` | `clock_vco_hbt_v6.spice:34` | same |
| XD0482 (484) | vco_avdd -> $69 (p2) | VCO `XRP2` | `clock_vco_hbt_v6.spice:36` | same |
| XD0490 (492) | vco_avdd -> $161 (n0) | VCO `XRN0` | `clock_vco_hbt_v6.spice:33` | same |
| XD0491 (493) | vco_avdd -> $162 (n1) | VCO `XRN1` | `clock_vco_hbt_v6.spice:35` | same |
| XD0492 (494) | vco_avdd -> $143 (n2) | VCO `XRN2` | `clock_vco_hbt_v6.spice:37` | same |
| XD0497 (499) | clkn -> $169 (= ckn; pull-up XD0488) | div1 `DIV__XFIRST__XSN` | `hw/soc/analog/pcie/clock_div2_conditioned_hbt_v3.spice:6`, via `clock_div4_hbt_v10.spice:16` (XFIRST) | parent instance `div1` = `nssoc_clock_div4_load3p2_v2_layout`. Built by `hw/soc/flow/make_pcie_clock_div4_load3p2_v2.py` (SOURCES line 21, root walk line 142, resistor placement line 457) |
| XD0498 (500) | clkp -> $170 (= ckp; pull-up XD0489) | div1 `DIV__XFIRST__XSP` | `clock_div2_conditioned_hbt_v3.spice:5` | same |
| XD0567 / XD0568 (569/570) | vco_avdd-vctrl / vctrl-avss | pump `xloop.xrhi` / `xloop.xrlo` | `pll_pump_filter_hv_rhi120_c8_v1.spice:11-12` | unchanged |

Only the first divider changes. Both parent divider instances (`div1` at
(1100,100) um and `div2` at (1100,800) um) use the same cell,
`nssoc_clock_div4_load3p2_v2_layout`. It was swapped into both by
`scripts/cloud_pll_divider_v2_layout.py:21,29`. Each div4 macro contains one
conditioned div2 (XFIRST). The second macro's conditioner is XD0540/XD0541
(rppd W4 L3.6, driven from $859/$858, the gain stage outputs), and the
what-if leaves it unchanged. The first divider therefore gets its own macro,
and div2 keeps the v2 macro.

The parent geometry comes from the summary of run 39914855175 (release
`cloud-results-39914855175-1-pll-rhi120-c8-parent`):

- `pump` sits at (200,1550)-(744,1756.63).
- `vctrl` is a TopMetal1 bus at y 1764.18-1765.82 from x 123 to 2519, with
  TopMetal2 drops at x 126-128 and 2514-2516.
- `avss` has a TopMetal2 strap at x 940-1020 (y 148-1870) and a TopMetal1
  plate at y 1790-1870.
- `div_avdd` and `sub` have TopMetal2 straps at x 854-934 and 808-848.
- No parent route or macro lies inside (1022,1495)-(2162,1760) um.

## Changes on this branch

None of the frozen files are edited. Each change is a new, separately named
source and macro that reuses the frozen generator code.

| Change | New source | Generator | Macro |
|---|---|---|---|
| 1 | `hw/soc/analog/pcie/pll_pump_filter_hv_c5r3k_v1.spice`: copy of the charge pump named `nssoc_pll_charge_pump_hv_c5r3k_v1`, with XPSOURCE `w=8u`. The slice and filter keep their names, so the paths `xloop.xdet.xcp.*` are unchanged. | `hw/soc/flow/make_pcie_pump_filter13_c5r3k_v1.py` checks that the only core delta against the RHI120/C8 rows is `xloop.xdet.xcp.xpsource` W 6.4 -> 8, then calls `make_pcie_pump_filter13_v1.build` | `nssoc_pump_filter13_c5r3k_v1` |
| 3 | `hw/soc/analog/pcie/clock_vco_hbt_v6_c5r3k_v1.spice`: XRP0-2/XRN0-2 `l=4.93u`, everything else identical to v6 | `hw/soc/flow/make_pcie_clock_vco_v6_c5r3k_v1.py` checks that the delta is exactly the six loads, then runs the v6 local generator | `nssoc_clock_vco_hbt_v6_c5r3k_v1_layout` |
| 2 | `hw/soc/analog/pcie/clock_div2_conditioned_hbt_c5r3k_v1.spice`: XSP/XSN `w=16u`. It keeps the subcircuit name, so the flattened names `DIV__XFIRST__XSP/XSN` are unchanged. | `hw/soc/flow/make_pcie_clock_div4_load3p2_c5r3k_v1.py` swaps only this source in the v2 generator and checks that the delta is exactly the two resistors | `nssoc_clock_div4_load3p2_c5r3k_v1_layout` (div1 only) |
| 4 | `hw/soc/analog/pcie/pll_vctrl_integrator_c5r3k_v1.spice`: `XRINT vctrl mid sub rppd w=2u l=23u` and `XCINT mid avss cap_cmim w=57.7u l=57.7u` | `hw/soc/flow/make_pcie_pll_integrator_c5r3k_v1.py` (new) | `nssoc_pll_vctrl_integrator_c5r3k_v1` |

In the divider, the 16 um resistors stay at their v2 origins (x 832 and 856,
row 0). The 24 um pitch still leaves the neighbouring escape lanes clear. The
VCO loads grow by 0.53 um in y, below the ring buses at y 30 and 60.

### New device sizes (PDK typical, `resistors_mod.lib`, `capacitors_mod.lib`, `cornerRES.lib`, `cornerCAP.lib`)

- rppd: R = rsh * L / (W + 0.006 um) + 2 * rzspec / W, with rsh = 260 ohm/sq
  and rzspec = 35 ohm*um. For W 2 um and L 23 um: 2981 + 35 = **3016 ohm**.
  The rsh corners 234 and 286 ohm/sq give 2.72 and 3.32 kOhm. The gate passes
  at both 3 and 6 kOhm, so the slow corner keeps margin.
- cmim: C = 1.5 fF/um^2 * A + 0.04 fF/um * P. For 57.7 x 57.7 um:
  4993.9 + 9.2 = **5003 fF**. The PDK limit is 75 x 75 um.
- The MIM bottom plate (Metal5, MINUS) is on avss, and the top plate is the
  internal node.

### Integrator macro and its proposed parent placement

The macro follows the pump generator conventions:

- one ptap per core device on the `sub` port;
- M1 -> M3 escapes to private M4 lanes;
- one M5 bus per net from y = 110 um;
- Metal5 ports `avss`, `sub` and `vctrl` on the left edge.

The cmim lanes are placed 9 um right of the bottom plate rather than at
x+17, because the plate is wider than the 40 um pump pitch. The generated macro measures 164.3 x 118.63 um. Its ports sit at y 100.03
(avss), 106.03 (sub) and 112.03 (vctrl).

Proposed parent origin: (1100, 1550) um, inside the free area. The macro
would then occupy up to (1264.3, 1668.63). The parent
step would add these routes, using the same pattern as the existing pump
port connections (M5 stub, TopVia1, TopMetal1 to a lane, TopVia2):

- `avss`: TopMetal1 from the port to lane x 980 on the existing avss
  TopMetal2 strap.
- `sub`: TopMetal1 to lane x 828. It crosses the `div_avdd` and `avss`
  TopMetal2 straps only on TopMetal1.
- `vctrl`: TopMetal1 to a new lane at x 1060, then a 2 um TopMetal2 riser to
  y 1766, then TopVia2 onto the existing TopMetal1 `vctrl` bus.

The parent device count becomes 845 + 4 = 849: rppd, cmim and two ptaps.

## First cloud step: child DRC/LVS

`scripts/cloud_pll_c5r3k_children.py --macro {pump,vco,div1,integrator}`
does the following for each macro:

1. Restores the pinned input bundle and runtime, the same ones the
   RHI120/C8 layout step uses.
2. Records the exact source delta.
3. Generates the macro with native PCells.
4. Runs the frozen checker of the base macro, with the macro name and source
   pointed at the c5r3k files:
   - pump: `check_pcie_pump_filter13_v1` and `_lef`. The width fault is
     replaced by a reference with XPSOURCE at 6.4 um.
   - vco: `check_pcie_clock_vco_v6_local_v1`. Its `wrong_load` fault now
     reverts RP0 from 4.93 to 4.4 um.
   - div1: `check_pcie_clock_div4_load3p2_v2`, with one added fault,
     `conditioner_series_reverted` (XSP from 16 to 4 um).
   - integrator: the new `check_pcie_pll_integrator_c5r3k_v1`, which uses the
     same decks and verdict rules. It checks main DRC (560 categories), deep
     and flat LVS (4 devices), wrong R and C references, vctrl open,
     avss/sub short and off-grid.

The thresholds and verdict rules are those of the frozen checkers. The
branch reuses the dispatchable `cloud-evidence-summary.yml` (matrix over the
four macros) as its entry point, and results go to workflow artifacts
`pll-c5r3k-<macro>-<run>-<attempt>`.

### Results

Run 42397336387, on commit df528e34:

- pump, vco and div1 pass.
- The integrator passes DRC, LVS and four of its faults. Its off-grid
  mutation could not run, because it needs a top-level Metal1 box and this
  macro has none.

Commit 9d955f1c moves that mutation to a top-level Metal3 escape. Run
42397775128 then passes for all four macros:

| Macro | Checker verdict | bbox (um) | Note |
|---|---|---|---|
| `nssoc_pump_filter13_c5r3k_v1` | PASS_NATIVE_PUMP_FILTER_DRC_LVS_AND_FAULT_CONTROLS, LEF pass | 544 x 206.63 | bbox and all 7 port boxes identical to the RHI120/C8 child; XPSOURCE bbox (189.38,29.38;193.3,38.62) |
| `nssoc_clock_vco_hbt_v6_c5r3k_v1_layout` | PASS_VCO_MAIN_DRC_STRICT_DEEP_FLAT_LVS_LEF_AND_TWENTY_ONE_NEGATIVE_CONTROLS_ONLY | 560 x 407.03 | same as the parent `vco` instance; VCTRL port centre 234.03 matches the parent lane y 334.03 |
| `nssoc_clock_div4_load3p2_c5r3k_v1_layout` | PASS_DIV4_LOAD3P2_V2_STANDALONE_MAIN_DRC_STRICT_DEEP_FLAT_LVS_LEF_NEGATIVE_CONTROLS_ONLY, plus `conditioner_series_reverted` rejected | 960 x 469.03 | same as the parent `div1` instance |
| `nssoc_pll_vctrl_integrator_c5r3k_v1` | PASS_NATIVE_INTEGRATOR_DRC_LVS_AND_FAULT_CONTROLS | 164.3 x 118.63 | rppd (29.8,29.39;32.2,53.61), cmim (79.4,29.4;138.3,88.3) |

The artifacts are `pll-c5r3k-<macro>-<run>-1`. The integrator has no LEF
check, because the pump LEF checker removes the `up` pin, which this macro
does not have. LEF is not used by the parent GDS integration.

## Remaining chain

Each step follows the existing RHI120/C8 workflows. Template runs on
`codex/complete-open-work` are 39914302787 through 39920519407.

1. **Parent integration and DRC/LVS** (`pll-rhi120-c8-parent-cloud.yml`,
   template run 39914855175). This needs a new script modelled on
   `scripts/integrate_pll_rhi120_c8_parent.py` (pump swap) and
   `scripts/cloud_pll_divider_v2_layout.py` (divider swap). The script must:
   - swap `pump`, `vco` and only `div1`, and assert that each swapped
     instance keeps its bbox, transform and port boxes;
   - place the integrator and add the three routes above as the only new
     parent shapes;
   - replace the only-one-delta proof with the exact list of declared
     changes;
   - pass deep and flat LVS at 849 devices and main DRC, and reject a
     wrong-reference fault and a vctrl-open fault.
2. **Geometry**: `pll-rhi120-c8-geometry-cloud.yml`
   (`scripts/cloud_pll_rhi120_c8_geometry.py`, run 39915412640).
3. **Terminals**: `pll-rhi120-c8-terminals-cloud.yml`
   (`cloud_pll_rhi120_c8_terminals.py`, `pll_rhi120_c8_terminals_native.py`,
   run 39915871064).
4. **Binding and Magic RC**: `pll-rhi120-c8-binding-cloud.yml` and
   `pll-rhi120-c8-rc-cloud.yml` (runs 39916625647 and 39916625651). Then
   `pll-rhi120-c8-rc-review-cloud.yml` (39917135843),
   `pll-rhi120-c8-raw-audit-cloud.yml` (39918288755), and
   `pll-rhi120-c8-body-access/-body-rc/-body-audit-cloud.yml`
   (39918715172, 39919164840, 39919694972).
5. **Composition**: `pll-rhi120-c8-composition-cloud.yml`
   (`compose_pll845_body_rc.py`, run 39920160596).
6. **Preparation**: `pll-rhi120-c8-preparation-cloud.yml` (run 39920519407).
   Its output replaces asset 668392118 as `parent865.spice`.
7. **Acquisition**: the native initial and continuation workflows. Then the
   unchanged `independent_analysis` gate on the full 1 us capture, at the
   deck's own step.
8. PVT, device safety and qualified parasitics. All are still open.

Each script pins the device counts (845), the macro names and the one
expected delta of its own step. Every step therefore needs a c5r3k copy of
its script. The pinned values and declared deltas change, and the acceptance
thresholds stay the same.

## Open points

- The child bboxes and port boxes match the parent instances, so the swaps
  should not move any parent route. The parent step must still assert this
  on the actual GDS.
- In layout, the integrator resistor adds its own parasitics and the cmim
  adds bottom-plate capacitance. The what-if used an ideal R and C, so the
  gate must be re-run on the extracted deck.
- The routing of the integrator in the parent is a proposal from the route
  summary. It must be checked against the actual parent GDS in step 1.
