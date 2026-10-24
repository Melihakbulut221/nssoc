# 145 — Loaded divider passes a finer-step screen; prefix timing still fails
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured result — 6 October 2026

The Tail115 loaded VCO/divider completes the full 34 ns run at a 1.25 ps
output and maximum solver step. **All 455 electrical screens and every
original functional check pass**, including sixty consecutive divide-by-four
intervals and two complete divide-by-eighty intervals. This closes that one
finite nominal test. It does not close numerical convergence: the VCO
frequency still changes by 1,079.469 ppm from the preceding 2.5 ps run.

Separately, the V24 packet-integrity candidate passes its component and
combined functional checks but worsens the slow-corner setup screen by
443.174 ps. It is rejected and not adopted. V11 remains the stable baseline.

The [delivery inventory](../hw/soc/pcie-evidence/20261006-divider-time-step-and-prefix-timing/delivery-inventory.json)
binds the exact source revisions, independent reviews and complete public
captures. [The preceding transport record](144-pcie-publication-recovery-and-incomplete-pll.md)
retains the recovered upload and the incomplete long PLL run.

## Tail115 geometry and loaded behavior

The [V10 divider reference](../hw/soc/analog/pcie/clock_div4_hbt_v10.spice)
changes the second stage's reference resistor length from 12.7 to 11.5 µm.
The first stage retains 12.7 µm. The two 24 µm MIM capacitors, L8 clock
pull-downs and all other intrinsic devices remain unchanged. This tests the
regenerative-current margin identified in the [preceding Bias8 waveform](143-pcie-divider-and-routed-transmitter.md).

The standalone divider's 21 physical checks and ten geometry fault controls
pass, including main DRC and strict deep/flat transistor LVS. Fresh wire
extraction and terminal binding retain 91 devices and 283 terminals. The
wire model has 382 resistors and 649 capacitors; thirteen RC fault controls
pass. The loaded VCO/divider composition contains 1,271 wire resistors and
1,414 capacitors. These are geometric models, not qualified process RC.

The new circuit maintains usable output amplitude through the full run,
where Bias8 lost it late in the simulation. The numerical studies keep the
same 455 intrinsic devices, initial conditions, supplies, bias, model files,
34 ns duration and 4–34 ns acceptance window. They change only the output
and maximum solver step and the declared capture storage bound.

| Step | VCO frequency | Original full functional verdict | Electrical screens |
| --- | ---: | --- | ---: |
| 5 ps | 8.102491691 GHz | FAIL: one of sixty /4 intervals counts three edges | 455 pass |
| 2.5 ps | 8.137405936 GHz | FAIL: one of sixty /4 intervals counts three edges | 455 pass |
| 1.25 ps | 8.146190014 GHz | PASS: all sixty /4 intervals count four edges | 455 pass |

The first two results remain FAIL. Independent raw readers verify every saved
value, all 64 HBT settled collector-emitter minima, source-to-native terminal
mapping and every reported divider interval. The three captures contain
6,523,869, 13,031,469 and 26,046,669 finite values respectively. This readback
checks the saved measurements; it does not qualify the transistor models.

In the two failed runs, a CML edge and a VCO edge cross the same saved time
bracket. Their interpolated separation changes sign by only a few femtoseconds.
All nearest input-edge ordinal advances remain four, with no observed missing
output pulse. A separate synthetic control demonstrates that a perfectly
divided sequence with a small smooth phase drift can fail the original
half-open edge-count rule. It also exposes the analogous boundary problem
in a simple nearest-edge replacement. Neither diagnostic changes a production
checker or converts either failed run into a pass.

The actual 1.25 ps run passes the unchanged checker. Its maximum unaligned
CML edge-time difference from 2.5 ps is about 35.272 ps, with no fitted phase
offset. Its frequency difference remains above the separately declared
100 ppm convergence target. A smaller time step still needs measurement;
shrinking changes alone do not establish convergence. These open-loop runs
are also distinct from the 1 µs closed-loop PLL acquisition study.

## V24: token prefix context increases the remaining control path

The [prefix generator](../scripts/generate_pcie_integrity_prefix_v24.py)
precomputes token relationships in each accepted block while retaining the
public cycle schedule. Five component tests cover token classification and
carry-column relationships, including 3,796,416 literal relation comparisons.
The product control history contains 44 executions: 43 pass
and one retained host-diagnostic failure. The corrected diagnostic rerun
passes both targeted cases; the combined records cover all 42 current
predicates. Two MAX4118 predicates remain excluded from this candidate.

The evidence includes eighteen direct public profiles, eighteen cycle-miter
profiles, actual block promotion/stall scenarios and meaningful cache/context
mutants. It does not claim a single clean 42-test run or mapped-netlist
functional equivalence. The native implementation has 98,919 cells and
9,490 flip-flops. Independent saved review confirms all 182 native archive
members, imported pin bits, the registered descriptor boundary and 24 raw
STA group values.

| Cell corner, original 4 ns preplacement screen | Setup | Hold |
| --- | ---: | ---: |
| Slow | −3.634856 ns | +0.356499 ns |
| Typical | −0.827638 ns | +0.254520 ns |
| Fast | +0.823255 ns | +0.170948 ns |

Slow setup regresses 443.174 ps against V23. The measured critical path runs
from the remaining-length state to the resident verdict cache and still
contains substantial control logic and buffering. Functional coverage does
not overcome this timing failure. V24 remains an experiment, with no routing,
extracted timing, main-chip integration or full PHY acceptance claimed.

## Scope still open

Standalone divider DRC/LVS and one passing loaded run are not full-chip
signoff. Body/substrate assumptions, qualified parasitics, PVT and long-run
clock behavior remain open. Complete PLL/CDR, SERDES/PCS/LTSSM, serial pads
and main-chip physical integration also remain open. The concurrent chip
setup/hold repair and receiver/transmitter routing are separate runs, excluded
from this finite delivery until their own completed results are verified.
