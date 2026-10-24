# 131 — Standalone divider layout and routed TX timing repair
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Completed block results after the power-loss recovery — 5 October 2026

The current standalone clock divider now passes its native geometry and
connectivity checks. The completed TX02 route also removes the previously
measured nominal hold and recovery failures, while slow-corner setup still
fails. **These are block results; full PCIe Gen3 x4, qualified RC and main-chip
timing/production acceptance remain open.**

The [delivery inventory](../hw/soc/pcie-evidence/20261005-divider-layout-and-tx-timing/delivery-inventory.json)
binds seven new divider source files, complete native captures, independent
reviews and immutable public assets. [Report 130](130-pcie-feedback-margin-and-durable-capture.md)
retains the loaded schematic results, RX12 timing improvement and CI repairs.

## The actual current divider has its own GDS and LEF

The new standalone layout contains 34 HBT devices, 33 resistors, six MIM
capacitors and 18 finite substrate contacts. It preserves the current
conditioner's two 4 µm pullup resistors. It exposes seven real ports:
`CLKP`, `CLKN`, `QP`, `QN`, `DIV_AVDD`, `AVSS` and `SUB`. It does not reuse
the older composite divider layout that embedded an obsolete VCO circuit.

The [generator](../hw/soc/flow/make_pcie_clock_div4_v7.py) produces the geometry;
the [V2 checker](../hw/soc/flow/check_pcie_clock_div4_v7_v2.py) binds native
DRC/LVS and LEF results to the exact source and layout. The
[finite result](../hw/soc/pcie-evidence/20261005-divider-layout-and-tx-timing/divider/finite-ready.json)
records **21 completed native stages**:

| Native check | Actual result |
| --- | --- |
| Main DRC | 0 violations |
| Hierarchical and flattened LVS | Both match 74/74 compared devices and seven ports |
| Native LEF check | Seven typed ports pass |
| Off-grid geometry fault | Rejected; six actual markers |
| Eight modified reference circuits | All rejected |
| Six actual open/short geometry faults | All rejected |
| Missing/blocked LEF pin faults | Both rejected |

That is four positive checks and 17 deliberately failing controls. Their native
FAIL statuses remain in the evidence; a rejected fault is not relabelled as a
passing circuit. Forty-two source/lifecycle controls and eighteen native-schema
controls accompany the physical checks.

The first native attempt had zero DRC violations and a matching hierarchical
LVS, then its auxiliary parameter parser rejected authentic extracted fields:
resistor `ps=0u` and MIM area/perimeter. That failed attempt is preserved.
V2 accepts exactly the native zero resistor field and arithmetically checked
MIM area/perimeter, while retaining strict dimensions, multiplicity, body and
connectivity checks. The GDS bytes are unchanged between the two attempts.

The [independent native review](../hw/soc/pcie-evidence/20261005-divider-layout-and-tx-timing/divider/native02-peer-rx/review.json)
reads all 434 completed-capture members, native inputs/outputs, raw DRC
markers and sixteen saved LVS databases. One clock-open fault demonstrates
why a comparison status alone is insufficient: its incomplete extracted
circuit can report a match while the real clock port is absent. The strict
port/deck checks reject that case. No physical simulation was rerun merely to
package this review.

This closes the finite standalone geometry/connectivity prototype. Divider
wire extraction, loaded post-layout division, clock-bank integration, PLL/CDR
behavior, PVT/jitter, analog pads/ESD and main-chip integration still require
their own results.

## TX02 closes the measured hold and recovery misses

TX02 completes detailed signal routing with zero router DRC violations and
the same logical netlist that passed the binary proof and physical-port tests.
Fresh nominal extraction then gives the following measured values:

| Cell corner, shared nominal RC | Setup, ns | Hold, ns | Recovery, ns | Removal, ns |
| --- | ---: | ---: | ---: | ---: |
| Slow | **−0.390164** | +0.037020 | +0.181834 | +0.126949 |
| Typical | +1.245844 | +0.062288 | +1.513403 | +0.122353 |
| Fast | +2.121003 | +0.085442 | +2.318610 | +0.123462 |

Relative to TX01, slow setup improves by 73.134 ps, hold by 52.447 ps and
recovery by 352.097 ps. The former hold value of −0.015427 ns and recovery
value of −0.170263 ns become positive. Removal remains positive but decreases
by 56.424 ps; the result does not hide that tradeoff. Slow setup remains a
failure at the unchanged 4 ns clock and I/O constraints.

The [saved-output review](../hw/soc/pcie-evidence/20261005-divider-layout-and-tx-timing/tx02/repair02-peer/review.json)
binds the route and nominal extraction to 3,850 state bits, 11,680 compared
functions, ten actual kernel fault controls, ten binding controls and three
native TX port cases. It also checks all 150 unconnected clock-load output
pins against their correctly annotated input nets. Extraction contains
38,643 nets, 1,624,278 capacitance entries and 227,627 nonzero resistance
entries. One nominal RC model is reused across the three cell libraries;
these are not independent qualified RC process corners.

The complete 90-member capsule and its validation/package receipts pass both
authenticated and anonymous download checks. The first publication stopped
when a generic package filename already belonged to another immutable asset.
Its failure is retained. Publication then succeeded with a unique filename
containing identical package bytes; no previous public asset was replaced.

TX03 is a separate follow-up candidate targeting the actual remaining slow
paths. Its source, global-route estimates and later verification must be
kept distinct from these completed TX02 measurements. RX13, resumed PLL
acquisition and further divider wire work likewise do not alter the results
reported here.
