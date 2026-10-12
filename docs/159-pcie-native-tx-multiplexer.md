# 159 — Native final-stage TX multiplexer
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

The [supported-device replacement](160-pcie-supported-tx-multiplexer.md)
passes three schematic points and new 54-device layout verification. Its
post-layout electrical test fails; the replacement is also not PHY signoff.

## Model-domain rejection — 12 October, 09:27 TRT

**The `Nx=12` circuit below is rejected as electrical evidence.** Inspection
of the pinned foundry `sg13g2_hbt_mod.lib` header gives valid `npn13G2`
multiplicities **1–10**, matching the PCell parameter range. The numerical
results below were obtained outside that declared domain. DRC and LVS alone
do not validate model applicability. The published circuit, geometry and
captures are retained as rejected development history, not an accepted part.

The out-of-domain 81-point matrix was explicitly stopped with its complete
and partial captures retained. The first passive alternative also used
`Nx=16/48`; at 48 the model's substrate-capacitance expression becomes
negative, so its startup failures cannot characterize a supported circuit.
Fresh candidates split oversized devices into separate native `Nx=6` or
`Nx=8` instances. They require new simulation and physical verification;
parallel splitting is not assumed electrically equivalent. The
[domain audit](evidence/pcie-tx-mux2-domain-20261012.json) records the pinned
model/PCell hashes and supersedes any nominal acceptance interpretation below.

## Historical out-of-domain development results

A new **2:1 HBT multiplexer and emitter-follower output** drives the existing
native SG13G2 TX output pair in simulation. Its separate layout passes native
DRC and transistor LVS. This supplies a missing serializer building block;
**the full 32:1 serializer, four-lane serial PHY and main-chip connection are
still incomplete**. The separate PLL, routed-chip and setup/hold work continues.

## Circuit and measured boundary

The [circuit](../hw/soc/analog/pcie/tx_mux2_hbt_n12_v1.spice) has ten HBTs and
six native, self-heating `rppd` resistors. Four data transistors use `Nx=12`.
The positive differential select chooses input A; the negative select chooses
B. Emitter followers connect directly to the existing
[TX circuit](../hw/soc/analog/pcie/tx_cml_rsil.spice), without an ideal gain
element between the two circuits. The combined simulation has fourteen HBTs.

The fixture supplies two externally synchronized 4 Gb/s differential inputs,
a 4 GHz differential select, 25 Ω source resistance per input, 2.5 V mux and
1.8 V TX supplies, and ideal 0.5/1.5 mA references. The load is an ideal 100 Ω
differential termination with 100 fF on each output. These are development
conditions, not a pad/package/channel model or an implemented upstream
serializer. Input data common mode is 1.9 V with ±0.15 V levels; select common
mode is 1.29 V with ±0.30 V levels.

An independent reader derives the selected value from the captured external
A/B/select voltages and checks **all 256 output bits at three positions per
125 ps interval: 768 samples**. It also reconstructs all fourteen HBT terminal
bindings from the actual source and checks their recorded extrema.

| Nominal result | Measurement |
| --- | ---: |
| Minimum signed output margin, initial `Nx=2` | 295.264 mV |
| Initial minimum selector VCE | 362.867 mV — fails 400 mV screen |
| Repaired minimum selector VCE, `Nx=12`, 1 ps run | 440.672 mV |
| Repaired minimum signed margin, 0.5 ps run | 295.306 mV |
| 0.5/0.25 ps largest terminal-voltage difference | 0.373 mV |
| Largest output-edge displacement between those runs | 0.007395 ps |
| Relative supply-power difference | 0.005592% |

Both fine-step runs pass the original 100 mV signal margin and fourteen-device
electrical screens. Post-settling VCE is constrained to 0.4–1.6 V, absolute
VBE to 1 V and collector current to 3 mA per emitter. The independent review
also checks upper bounds over the entire power ramp. These are engineering
screens; no foundry SOA or lifetime qualification follows from them.

The 0.5/0.25 ps comparison uses limits recorded before the finer run: 1 mV
for every terminal-voltage difference and signal-margin difference, 0.2%
power difference and 2 ps edge displacement. No phase fitting or edge
discarding is used. The earlier 1/0.5 ps observation reaches 1.088 mV at one
terminal and is retained rather than presented as passing the tighter test.

## Startup and actual fault controls

The initial circuit passes data samples but fails selector headroom and emits
thermal/initialization warnings. Native BJT `OFF` initialization with all
external sources initially zero removes the warnings but **does not repair
the headroom failure**. Increasing the four data-transistor multiplicities
then fixes that nominal failure. Both prior outcomes are retained.

`OFF` is a DC initialization option, as described in the
[ngspice BJT documentation](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf).
The run records all fourteen native flag readbacks, solves and checks the
zero-source operating point, and then ramps real sources without `UIC`, a
forced signal node or a modified foundry model. All positive final runs are
free of the recorded numerical diagnostics. Swapping the actual mux select
wiring and removing its reference current each produces wrong output samples;
tool failure is not counted as detecting either circuit fault.

## Physical implementation and next gates

The [generator](../hw/soc/flow/make_pcie_tx_mux2_hbt_n12_v1.py) produces a
**646 × 161.63 µm** standalone macro with twelve ports, sixteen core devices
and sixteen explicit substrate contacts. Native validation passes all
**560 DRC categories**, hierarchical and flat **32-device LVS**, and five
actual wrong-size, missing-device, open, short and off-grid controls. The
[checker](../hw/soc/flow/check_pcie_tx_mux2_hbt_n12_v1.py) retains those checks.
Canonical regeneration matches the verified layout by per-layer polygon XOR,
text labels, exact LEF and exact transistor reference. This does not establish
post-layout electrical behavior: the transient uses schematic parasitics,
and the existing TX driver has not been placed into this new macro.

An 81-point matrix was started over three HBT corners, three resistor corners,
three temperatures and three common supply scales. All 81 generated decks
are checked against the proven nominal fixture, allowing only the declared
corner fields and an additional supply-voltage probe. Inputs, select levels,
references and load stay fixed; independent supply variation, mismatch,
jitter and channel effects are outside this matrix. The completed typical-HBT,
typical-resistor points already **reject this candidate**: at −40 °C and 95%
supply, TX tail VCE reaches **372.378 mV**; at 125 °C and nominal supply, a
TX data-pair VCE reaches **278.461 mV**, both below the unchanged 400 mV
limit. Data samples still pass, which does not override the electrical failures.
No matrix pass or production adoption is claimed. A passive common-mode
alternative is being investigated separately; its first two startup attempts
abort numerically and provide no acceptance evidence.

The retained failures also include an initial review requesting an unsaved
TX-supply vector, an incorrect tap-count metadata field, and a PVT runner's
literal-enum error before its first simulation. Fresh corrected methods
preserve each original. The corrected power review uses the exact pinned
ideal 1.8 V source and the captured current, rather than inventing a voltage
sample. Corrected physical metadata and native LVS both count sixteen taps.

The [evidence record](evidence/pcie-tx-mux2-20261012.json) binds the completed
captures, physical reports, failures, controls and prospective PVT methods.
The [235-member public archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/nssoc-tx-mux2-native-physical-20261012.tar.gz)
is 141,007,133 bytes, SHA-256
`1a5f780935f35c4e355bc06c009680ea9e87d896d1b5fde8d0e2c740d03e1cfc`,
and passes complete anonymous byte/hash readback. Running PVT data and the
subsequent passive-divider attempts are excluded from that nominal archive;
the evidence record identifies the completed PVT failures separately.
Extracted interconnect, coupled TX placement, the complete serializer tree,
actual clock/bias drivers and full serial main-chip integration remain open.
