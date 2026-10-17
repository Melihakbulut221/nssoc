# 128 — PCIe packet identity and finite VCO tuning
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Verified continuation — 5 October 2026

The receive event interface now preserves TLP/DLLP identity even when CRC
rejects a packet. A separate physical VCO revision produces measured
frequencies on both sides of 8 GHz with its actual local wire model.
The next parser revision reduces mapped area and preplacement delay.
**Slow and typical parser setup still fail. Full PCIe Gen3 x4, final
timing and main-chip physical integration remain open.**

The [delivery inventory](../hw/soc/pcie-evidence/20261005-vco-bracket-and-packet-identity/delivery-inventory.json)
pins 32 new source files, 54 compact evidence files and 15 immutable public
assets. The [delivery audit](../hw/soc/pcie-evidence/20261005-vco-bracket-and-packet-identity/delivery-audit/pcie-phase19-delivery-20261005/archive-audit.json)
reads seven complete local capsules, rehashing all 1,087 members against
the retained authenticated and anonymous publication receipts. It also
recounts saved packet-type simulator XML and fully decompresses all seven
compiled programs. This audit does not rerun completed DUT tests.
The [previous report](127-pcie-owned-events-and-physical-repairs.md) is an
unchanged historical result.

## Packet identity survives a rejected CRC

Consumer V6 adds four `event_packet_dllp_o` bits to the ordered event
bundle. Each bit captures the original descriptor type at the same owner
entry used for sequence, length and verdict. Capture happens before the
good/bad/null decision, so a rejected DLLP retains its identity. The bits
remain registered while the event bundle is stalled; later descriptors
cannot change a held event. Reset, flush, epoch faults and unused lanes
mask them with the corresponding event-valid bits.

Recovered-events V2 forwards this field through the raw four-lane
composition. The original body path, abort priority and normal-end drain
accounting are unchanged. This closes the missing type-sideband item in
report 127; it does not implement the downstream credit/replay policy.

The [finite validation](../hw/soc/pcie-evidence/20261005-vco-bracket-and-packet-identity/event-packet-type/pcie-event-packet-type-20261005/validation.json)
records nine distinct pytest controls: two inverse source checks, eight
leaf port cases, eleven raw-lane port cases and five actual RTL mutants.
The positive cases include 256 alternating bad-TLP/bad-DLLP packets across
owner wrapping and stalls, plus flush and epoch masking. The faults force
a zero type, omit the bad-packet type, substitute the live descriptor,
remove valid masking, or disconnect the wrapper output. The last produces
an observed unknown/high-impedance output in Icarus; it is not a compiler
failure counted as a logic rejection.

The [source peer](../hw/soc/pcie-evidence/20261005-vco-bracket-and-packet-identity/event-packet-type/pcie-event-packet-type-20261005/source-only-peer.json)
checks both literal inverse bridges and the held-owner/type association.
The complete capsule retains both positive and deliberately faulty runs.
No whole-composition native mapping, routed timing or physical CDC
qualification is inferred from these RTL results.

## VCOv6: measured finite tuning endpoints

Six MIM geometries change relative to V5. The local physical generator
retains 62 device records, including 13 finite contacts, with six public
ports. Native 560-rule DRC reports zero violations; strict deep and flat
LVS match. The diagnostic wire network has 889 resistors and 765
capacitors, 145 metal terminals, 56 explicit body/well terminals and
20 conductors. Thirteen actual RC corruption controls accompany the
network checks. This remains a local diagnostic extraction model.

| Same nominal wire circuit and 50 fF load per public clock pin | Frequency | Complete signed 300 mV cycles |
| --- | ---: | ---: |
| Control 0.60 V | 8.163823902 GHz | 48 |
| Control 0.85 V | 7.642295659 GHz | 45 |

The two actual benches differ only in the control-source endpoint. Both
pass the declared 30-HBT screens. At 0.60 V, the recorded minimum VCE is
0.526776 V and peak collector current is 2.768186 mA/Nx; at 0.85 V they
are 0.571242 V and 1.686334 mA/Nx. These screens use the documented
measurement windows: lower VCE/current over 6–12 ns and upper VCE over
0–12 ns. They are not an all-device lifetime or thermal qualification.

The [frozen result](../hw/soc/pcie-evidence/20261005-vco-bracket-and-packet-identity/vco-v6/pcie-vco-v6-local-v1-wire-20261005/validation.json)
and additive [independent full-wave peer](../hw/soc/pcie-evidence/20261005-vco-bracket-and-packet-identity/vco-v6/pcie-vco-v6-local-v1-wire-20261005/peer-validation.json)
retain 12,011 samples per bias and all 93 complete signed cycles. The
original ready receipt's peer-pending statement is preserved; the later
peer is a separate result. Grouped inherited and new test totals overlap
and are not summed as unique tests.

The measured endpoints bracket 8 GHz. They do not measure an exact 8 GHz
control voltage or establish PLL lock. Separate ideal body/reference
connections remain explicit. Real divider loading, longer settling, PVT,
phase noise, jitter, thermal behavior and qualified RF parasitics require
their own results; no main-chip layout acceptance follows from this macro.

## Integrity V11: remove late feedback from ingress payload writes

V11 separates the ingress payload writer from the late full/ready/pop
feedback. The original validity, pointer, fault and public-interface
priorities remain. Invalid hidden FIFO contents may differ; valid slots
and public cycles must still match the frozen V10 implementation.

The [finite and native delivery](../hw/soc/pcie-evidence/20261005-vco-bracket-and-packet-identity/integrity-v11/pcie-integrity-v11-20261005/ready-finite.json)
records 20 distinct pytest controls, 24,576 literal FIFO cycles across
three depths, 13 direct public cases, 13 V10/V11 public cycle comparisons
and 14 actual RTL faults. The first coverage fixture failed because its
ready stimulus emptied the FIFO too early; those failures are retained.
The corrected stimulus covers full-plus-pop and full-without-pop without
changing the DUT to make the test pass.

| Unchanged 4 ns preplacement profile | Native cells | SS setup | TT setup | FF setup |
| --- | ---: | ---: | ---: | ---: |
| V10, previous result | 85,054 | −3.838124 ns | −0.970022 ns | +0.709167 ns |
| V11 | 83,778 | −3.552011 ns | −0.758690 ns | +0.856405 ns |

V11 removes 1,276 mapped cells and improves slow setup by 0.286113 ns.
The exact import check covers 313,142 pin bits, 9,410 flip-flops and
24 public ports, with six actual graph faults. Hold is positive in all
three cell corners. **Slow and typical setup remain failures.** These are
preplacement measurements, not routed timing or whole mapped-function
proof. The V11 candidate is not silently substituted into the delivered
owned-event composition.

## PLL comparison method and outstanding physical work

The [predeclared timestep comparison method](../hw/soc/pcie-evidence/20261005-vco-bracket-and-packet-identity/pll-pair-method/pair-v1-source/ready-finite.json)
has 29 distinct controls, exercised under Python 3.12 and 3.14. Repeating
them under two interpreters does not make 58 distinct controls. The
source/receipt and synthetic edge checks validate the method; they do
not establish a passing pair of real PLL captures.

The tighter 2.5 ps, 1 µs capture was interrupted at the user's shutdown
request near 594 ns and restarted from time zero with the same frozen
circuit and criteria in a new output directory. Its stopped history is
retained. No timestep-pair, lock or jitter acceptance is claimed here.

Fresh TX02 and RX11 detailed routes, the loaded VCO feedback experiment
and the next parser timing repair continue separately from this finite
source cut. Final extracted timing must follow actual routing; global
route estimates are not a substitute. Controller credit/replay behavior,
LTSSM/training, full SERDES/CDR/PLL, physical clocks/CDC, qualified RC/ESD,
whole-chip DRC/LVS, SRAM/DFT requirements and production approval remain
open obligations.
