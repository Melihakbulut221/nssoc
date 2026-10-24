# Real-device independent preset and first-fall release candidate — 2026-10-24

This supplies actual transistor schematic source for the functions required by the proved 31-clock mapping. It has not passed physical or electrical qualification. The source is `hw/soc/analog/pcie/clock_div2_async_preset_firstfall_v2.spice`; `scripts/build_tx_phase_async_preset_source.py` records reproducible derivations from the unchanged original latch, tail and high-input networks.

## Independent preset while either clock phase is active

The original seven-HBT latch current stack and load/bleeder geometries remain. Four transistor base connections change: the data pair receives a real CML selector output, and the regenerative pair receives a second real CML selector output. In normal mode those selectors pass the original data and actual positive feedback respectively. In preset mode both paths select the same real resistor-derived polarity.

Thus the preset can drive the chosen output sign whether the clock selects the data pair, the hold pair, or overlaps them during a transition. The design does not depend on a running clock to clear a held slave, and it does not insert an additional series transistor into the original current stack. It does add real devices, capacitance, bias current and feedback delay; preserving the stack is not a proof of timing or safety.

Two latch variants force positive or negative differential polarity. Positive and negative refer to the sign of QP−QN, never an assumed voltage or simulator initial condition. The selector uses native npn13G2 and rppd devices. Its DC seed consists of four explicit resistors, with geometry inherited from the earlier unqualified source hypothesis. Actual loaded seed voltage and polarity still require measurement. No ideal internal voltage/current source, behavioral switch, .ic or UIC is present.

The real high-input limiter and two-MIM feed-forward network are copied exactly from the existing phase55 source. They handle the external clock, global ARM control and released control domains. Their original physical qualification does not qualify these newly added loads or interconnects.

## Real first-parent-fall release topology

A separate falling-edge master/slave CML flip-flop uses the new independently preset-negative latches. A real four-resistor seed drives its constant-positive data input. Global ARM passes through the actual level network and holds both internal signs negative while reset is asserted.

After ARM is enabled, its master tracks during parent-clock high and its slave tracks during parent-clock low. At the first eligible parent falling edge, the slave receives the positive seed. Its real output passes through another real level network and enables normal operation in both divider latches.

If ARM is enabled while the parent is low, the release master remains negative until the next high phase, then captures positive before the following fall. If enabled while the parent is high, it can capture positive before that phase ends. In both cases the source-level event relation is the required first-fall release, **provided physical setup, removal/recovery and settling constraints are met**. Enabling ARM close to an edge is not proven safe; metastability and a possible extra-cycle latency remain native validation obligations.

The positive-parent variant presets divider master/slave positive/positive. The negative-parent variant presets master/slave negative/positive. The unchanged 31-clock mapping selects four positive-parent and eleven negative-parent instances. The eleven master output wire swaps remain exactly as proved; no waveform-dependent phase or polarity fitting is introduced.

ARM_P/ARM_N are explicit external differential control pins, not ideal internal clocks or reset assignments. The final product still needs a qualified global reset driver, voltage-domain conversion and distribution. The PLL has not been connected.

## Source census and controls

The proposed hierarchical expansion is 106 HBTs, 127 resistors and eight MIMs per parent variant: 241 compact primitives and 821 compact terminals. HBT emitter multiplicities are thirteen Nx1, 54 Nx2 and 39 Nx4. These are schematic counts; physical body contacts, extracted topology and layout census are not invented.

The source checks preserve every original latch card except its four intentionally selected base nodes, retain the original tail reference and unequal seed MIM geometry, retain the exact level-network device cards and public port order, bind every hierarchical instance and expand both variants independently. Connection faults exercise bypassed data/hold selectors, reversed feedback, altered tail stack, symmetric seed, wrong preset, wrong release edge, release bypass, output shorts, original-device changes and ideal-source insertion.

The control's Boolean truth checks are conditional topology checks. They assume valid loaded differential signs and represent no analog simulation, metastability proof or physical reset implementation.

## Required native work before use

1. Review the source topology and its full device/connection checks.
2. Establish real ARM and clock input common mode/swing from verified source interfaces; no default measurement is substituted.
3. Build fresh native layout, body contacts, all-device LVS and full DRC. The old 55-device GDS/RC cannot be reused for this changed topology.
4. Extract fresh two-order RC with every new terminal/anchor and all intrinsic MIMs. Implement actual parent power/reset/clock routes.
5. Screen every HBT at the original limits: post-start VCE≥0.4 V, whole-trajectory |VCE|≤1.6 V, |VBE|≤1 V and |IC|/emitter≤3 mA. No limit is relaxed for the extra selectors or release flop.
6. Run startup from the real powered operating point with no initial-state forcing; assert/deassert global ARM in both clock phases, characterize recovery/removal and near-edge behavior, and prove all original fixed phase/load/bit gates at 4 GHz and required corners.
7. Qualify selector-level clock buffers, global reset distribution and the actual routed 31-node parent with the real PLL.

The added selectors lengthen the regenerative and data paths and the release circuitry increases clock loading. A failed electrical result requires a genuine design change, not a fitted initial condition, extra ideal driver, delayed oracle or relaxed threshold. No native simulation or physical job is registered by this source-only workflow.
