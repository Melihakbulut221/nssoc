# 127 — Owned receive events and measured physical repairs
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured development — 5 October 2026

The bounded recovered-lane RTL path now delivers owned TLP data and ordered
controller events through the same CRC quarantine. Separate physical work
measures a smaller VCO's actual wire loading and fresh routed timing for
the earlier RX and TX components. **The VCOv5 measurements in this cut remain below 8 GHz, and the
digital timing failures remain failures. Complete PCIe Gen3 x4 and main-chip
physical acceptance are still open.**

The [finite delivery inventory](../hw/soc/pcie-evidence/20261005-owned-events-and-physical-repairs/delivery-inventory.json)
pins **29 new sources**, nine previously published V9 dependencies, 57
compact evidence files and **19 immutable public assets**. Seven selected
complete local capsules were checked against their retained authenticated
and anonymous publication receipts: **756 members** were rehashed. Saved
event-test XML and compressed compiled programs were independently read
back. This delivery audit did not redownload assets or rerun HDL, SAT or
analog simulation. The [previous report](126-pcie-strict-pcs-and-serial-packets.md)
remains an unchanged snapshot.

## Raw lanes to owned data and ordered events

The new composition preserves four independent recovered clocks, local SDS
alignment lock, complete-record CDC, ordered-set-aware scrambling state,
strict parser-owned EDS/SKP cohorts and CRC quarantine. Owned framer V3
adds that cohort decision/stop interface to the earlier owned framer.
Consumer V5 joins body and descriptor by the complete owner identity and
epoch, then exposes a 128-bit TLP body and up to four ordered event lanes.
It does not insert the earlier one-byte-per-cycle backend.

ACK, NAK, VC0 flow-control and unknown DLLPs retain their ordered event
identity. Bad-CRC and nullified packets produce distinct verdict events;
they do not become valid ACK/flow-control actions. This is an event
interface, not a complete credit/replay controller or LTSSM. Its epoch is
a bounded observational identity, not a promise of uniqueness forever.
The current bad-CRC event kind does not expose whether the rejected packet
was a TLP or DLLP; controller policy needs an explicit type sideband. The
separate consumer/interface revision for that gap is outside this cut.

Explicit abort or an upstream epoch fault suppresses pending handshakes.
A normal complete ending instead lets accepted data and events drain.
The wrapper counts accepted descriptors minus accepted events; public
stream-end waits for the remaining ordered events even after upstream
body/descriptor drain. Normal stream-stop alone does not flush the
consumer. Serial input cannot pause: output stalls consume finite storage,
and overflow aborts the epoch.

The [complete RTL receipt](../hw/soc/pcie-evidence/20261005-owned-events-and-physical-repairs/recovered-events/pcie-recovered-events-20261005/validation.json)
records **11 raw-port cases**, eight actual top-wiring fault rejections and
one inverse source check: ten distinct pytest controls. Cases cover all
32 raw bit phases, 1,200 dense DLLPs, packet integrity verdicts, ACK/NAK/FC,
held body/events, reset, abort, finite overflow and normal ending. The
complete 305-member capsule includes the earlier failed attempts:

- Some launches refused the scratch entry gate before simulation. They
  are resource refusals, not HDL failures.
- An earlier stall fixture held data before the ending set arrived and
  overflowed the finite buffer; its failed captures and exact benches remain.
- One drain-count mutant survived while body backpressure prevented the
  upstream ending. The corrected event-only stall lets the body drain and
  observes the missing final event wait; the original survival is retained.

The final independent saved-output review and this delivery's full-member
audit are separate from the earlier source-only peer. No whole-composition
SG13 mapping, SDF timing or physical CDC qualification is claimed.

## VCOv5: smaller real MIM loading, still below target

The frozen twelve-file VCOv5 revision has a source-derived local layout:
560-rule native DRC reports zero violations, and strict deep and flat LVS
match 62 devices and six ports. The passive diagnostic retains 145 metal
terminals, 56 body/well terminals, 13 finite contacts and 20 conductors,
with **889 resistors and 767 capacitors**. Export conservation and actual
corruption controls accompany those values; this is not a qualified full
parasitic extraction model.

| Finite nominal experiment | Frequency | Complete signed 300 mV cycles |
| --- | ---: | ---: |
| VCOv5 with actual wire network, control 0.60 V | 7.828369 GHz | 46 |
| Same circuit, control 0.55 V | 7.905641 GHz | 47 |

Both points pass the declared 30-HBT screens, but neither establishes an
8 GHz bracket. At 0.55 V, peak measured collector current is
**2.972523 mA/Nx**, leaving only **27.477 µA/Nx** to the project's 3 mA/Nx
screen. These are finite 12 ns nominal diagnostics: lower-VCE/current
screens use 6–12 ns and upper-VCE uses 0–12 ns. They are not all-device SOA,
thermal equilibrium, PVT, jitter or oscillator/PLL production acceptance.
Separate ideal body and capacitance-reference connections remain explicit.

The original [ready snapshot](../hw/soc/pcie-evidence/20261005-owned-events-and-physical-repairs/vco-v5/pcie-vco-v5-local-v1-wire-20261005/ready.json)
still says independent review was pending at its cut. The additive
[root full-wave peer](../hw/soc/pcie-evidence/20261005-owned-events-and-physical-repairs/vco-v5/pcie-vco-v5-local-v1-wire-20261005/peer-validation.json)
now checks every saved sample at both biases, all 93 complete signed cycles
and the recorded device screens. Its separate phase diagnostic reports
measured ring crossings; it does not turn delay decomposition into a new
timing or tuning qualification. Earlier current failures, resource refusals
and fixture errors remain in their original evidence.

## Integrity preplacement: V9 native result and V10 bank revision

Report 126 delivered V9's finite predecode controls. This addendum supplies
its native map, exact import graph and measured preplacement timing. V10
then separates current/next payload and metadata writes from the late fault
decision. Validity, state, CRC, commit and abort priorities remain unchanged.
Invalid hidden bank contents may differ on a fault edge; a valid initialized
bank must still match V9 before it can be consumed.

V10 has **19 distinct controls**, 8,192 literal bank cycles, 13 direct
default-150 cases, 13 cycle comparisons and 15 actual RTL mutants. Its
first ambiguous textual inverse check is preserved alongside the corrected
control. Neither finite cycle comparisons nor a source bridge constitute
an arbitrary-state proof of the whole parser.

| Same 4 ns preplacement profile | Native cells | Import pin bits | SS setup | TT setup | FF setup |
| --- | ---: | ---: | ---: | ---: | ---: |
| V9 | 85,127 | 317,316 | −3.927188 ns | −1.033623 ns | +0.680551 ns |
| V10 | 85,054 | 317,157 | −3.838124 ns | −0.970022 ns | +0.709167 ns |

Both exact import checks include six actual graph faults. V10 improves SS
setup by **0.089064 ns** while using 73 fewer mapped cells, but slow and
typical setup still fail. Hold is positive in the three reported corners.
These are preplacement screens under unchanged constraints, not placed or
routed timing, whole mapped-function proof or mapped-port simulation. The
[V9 receipt](../hw/soc/pcie-evidence/20261005-owned-events-and-physical-repairs/integrity-v9/pcie-integrity-v9-20261005/ready-finite.json)
and [V10 receipt](../hw/soc/pcie-evidence/20261005-owned-events-and-physical-repairs/integrity-v10/pcie-integrity-v10-20261005/ready-finite.json)
retain those limitations. V9/V10 are not substituted into the delivered
owned-event composition, and no maximum-4118 whole-DUT result is inferred.

## Actual routed RX10 and TX01 timing

These are the earlier standalone byte receiver and TXv4 components, not
the new whole recovered-event composition. Both complete detailed routes
report zero router DRC violations and preserve the previously proved and
port-replayed netlist byte for byte. Fresh OpenRCX extraction uses the
nominal PDK model; the same extracted RC is evaluated at three cell corners.
It is not three qualified RC process corners.

| Component and cell corner | Setup | Hold | Recovery | Removal |
| --- | ---: | ---: | ---: | ---: |
| RX10 slow | −0.696048 | +0.041660 | +0.325061 | +0.892300 |
| RX10 typical | +1.088547 | +0.074507 | +1.641940 | +0.595948 |
| RX10 fast | +2.100882 | +0.092947 | +2.439881 | +0.423325 |
| TX01 slow | −0.463298 | −0.015427 | −0.170263 | +0.183373 |
| TX01 typical | +1.203908 | +0.031497 | +1.297390 | +0.157340 |
| TX01 fast | +2.099793 | +0.069737 | +2.182591 | +0.147128 |

All table values are nanoseconds under the unchanged 4 ns and I/O
constraints, with propagated clock and no false-path or multicycle
exceptions. RX10 improves SS setup by 0.391247 ns relative to published
RX08. TX01 improves it by 0.629515 ns relative to its original routed
baseline. **RX setup remains open; TX setup, hold and recovery remain open.**

The [RX independent review](../hw/soc/pcie-evidence/20261005-owned-events-and-physical-repairs/rx10/repair10-peer/review.json)
replays the existing binary proof kernel on 1,804 state elements and 5,443
functions and recounts six saved native port cases. The
[TX independent review](../hw/soc/pcie-evidence/20261005-owned-events-and-physical-repairs/tx01/repair01-peer/review.json)
does the same for 3,850 states, 11,680 functions and three saved port cases.
Each retains ten actual proof-kernel fault controls; this review inspected
those controls rather than rerunning them. It does not claim an independent
proof algorithm or new simulator execution.

The reported unannotated outputs are **78 RX and 150 TX** input-only CTS
dummy loads. Each output is actually unconnected, and every corresponding
A input was independently found on its correct extracted SPEF clock net;
both reports have zero partially unannotated drivers. The TX count corrects
an earlier verbal count of 100. Full SPEF numeric censuses, source hashes,
logs, saved port results and complete physical capsules accompany the
classification. Native port logs retain the inherited GPI interpreter-path
warning; no clean-log claim replaces that evidence.

## Remaining work

Active VCOv6, integrity V11, RX11, TX02 and the restarted tighter PLL capture
are excluded from this source and result cut. No unfinished experiment is
counted as a passing timestep pair or timing repair. Full controller
throughput and policy, LTSSM/training, physical CDC/clocking, routed timing
with qualified coupling, ESD, full-chip DRC/LVS, manufacturing review and
silicon validation remain open under the
[product acceptance contract](92-product-acceptance.md).
