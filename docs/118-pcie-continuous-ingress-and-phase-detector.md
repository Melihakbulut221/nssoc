# 118 — Continuous PCIe ingress and transistor phase detection
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured progress — 4 October 2026

The receive front end now accepts a continuous 32-bit word on each of four
logical lanes, reconstructs fixed 130-bit blocks, descrambles them and delivers
bounded packets. A separate original transistor phase detector and charge pump
passes its nominal primitive tests. Actual analog wire extraction and digital
post-route timing expose failures that remain open. **Full Gen3 x4, PLL/CDR,
main-chip physical integration and production qualification are not complete.**

Source commit `73355015788665ed2b5a79c03eb38d02546734e5` contains the frozen implementation and receipts.
The [root verification record](https://github.com/Melihakbulut221/nssoc/blob/73355015788665ed2b5a79c03eb38d02546734e5/hw/soc/pcie-evidence/20261004-continuous-rx-and-pfd/root-verification.json)
binds 124 passing focused pytest cases with no skips. Native port, circuit and
independent review cases below are separate runs, not additional unique pytest
cases. [Document 117](117-pcie-routed-receive-duplex-and-thermal.md) retains the
previous physical and thermal snapshot.

## Continuous input and packet ownership

The ingress consumes every input clock without backpressure. Its 160-bit lane
reservoir preserves all 65 residual positions across the 130/32 boundary. Full
FIFO replacement allows a simultaneous pop and push; a true overflow invalidates
the epoch and requires an explicit restart. The caller still supplies block
alignment, lane deskew and the Data Stream epoch. Variable-length SKP Ordered
Sets, block search, CDC and analog sampling are outside this interface.

The standalone ingress maps to 11,756 IHP cells and passes four native cases.
Five FIFO depths pass the same RTL cases; ten compiled HDL faults are rejected.
An independent oracle checks 32,500 cycles across five depths and all residual
positions, with four additional actual HDL fault controls.

The combined front end maps to **54,368 IHP cells** and passes six native cases.
Its full-block GF(2) descrambler advances only on an accepted block. A new framer
fast path consumes whole IDL blocks without spending sixteen byte-parser cycles.
It uses packet context: an all-zero TLP/DLLP body is payload, and a pending
nonzero successor owns its following blocks. Packed successors, end-of-block
lookahead, nullification, held packets, damaged headers and restart are tested.
Ten real HDL faults are rejected; an independent review also exercises four
context cases and 3,000 scalar-LFSR cycles with eight compiled faults.

The original four-entry integrated FIFO overflowed during a legitimate packet
burst, and the overflow indication lagged invalidation by one cycle. Both failed
runs remain preserved. A sixteen-entry FIFO and direct fault propagation repair
those finite cases. **The byte-wide packet consumer still cannot sustain dense
x4 packet traffic.** A tested overflow is explicit; adding a finite FIFO does not
remove this bandwidth limit. A wide consumer is a separate development step.

The [complete frontend receipt](https://github.com/Melihakbulut221/nssoc/blob/73355015788665ed2b5a79c03eb38d02546734e5/hw/soc/pcie-evidence/20261004-continuous-rx-and-pfd/frontend-development.json)
and [public native archive](https://github.com/Melihakbulut221/nssoc/blob/73355015788665ed2b5a79c03eb38d02546734e5/hw/soc/pcie-evidence/20261004-continuous-rx-and-pfd/frontend-release.json)
include the earlier failed cases and initial mutation-coverage failures. Native
Icarus logs retain unsupported timing-check warnings and an OSS wrapper Python
executable diagnostic; all six tests execute, but this is not SDF timing or a
clean-diagnostic claim. CI now runs the ingress and combined front end as separate
RTL/native/mutation jobs.

## Original transistor phase detector and charge pump

The circuit contains 111 native HV MOS devices and one physical poly resistor.
Two static master/slave flip-flops, a delayed common reset and switched current
mirrors implement phase detection and charge pumping. Internal clocks, ideal
logic gates and behavioral current sources are absent. The testbench provides
external clocks, reset, supplies and control-node loads.

At nominal 2.5 V, 27 °C and 100 MHz, sixteen positive native cases pass and five
actual transistor faults are rejected with clean numerical and electrical
screens. An independent review flattens every primitive, checks documented MOS
geometry ranges and remeasures eight complete public waveforms, including every
fault. This is a bounded nominal result, not a PVT or closed-loop qualification.

The original source mirror produced approximately 23% zero-phase charge mismatch.
Its raw failure is retained. Changing its width from 8 to 6.4 µm reduces nominal
zero-phase mismatch to 0.064%. A +2 ns phase error produces approximately
+7.540 µA; −2 ns produces −9.268 µA. The unequal nonzero-error gains remain
measured limitations. The separately declared 20/10 ps timestep comparison
changes charge, pulse width and supply metrics by at most 0.0616%, with a net
pump difference of 1.94 nA.

The [native validation](https://github.com/Melihakbulut221/nssoc/blob/73355015788665ed2b5a79c03eb38d02546734e5/hw/soc/pcie-evidence/20261004-continuous-rx-and-pfd/pfd-native.json)
and [independent raw review](https://github.com/Melihakbulut221/nssoc/blob/73355015788665ed2b5a79c03eb38d02546734e5/hw/soc/pcie-evidence/20261004-continuous-rx-and-pfd/pfd-peer.json)
retain the exact scope and all 21 full-wave release references. The existing VCO
has negative tuning gain, so loop polarity must be reversed. The physical
divider currently supplies divide-by-four; a genuine additional divide-by-twenty
chain is needed for 8 GHz/100 MHz feedback. Neither an ideal feedback divider nor
standalone pump success establishes PLL lock.

## Native wire precision and an explicit analog boundary

The initial 932-probe extraction contained auxiliary marker disconnections.
Using only the 804 actual device/port anchors preserves all 128 physical
conductor components, but still exposed native capacitance accumulation and
serialization discrepancies. Both failed captures remain available.

A private, separately versioned Magic precision repair now reproduces all
32,855 wire resistors and the native point/mutual-capacitance accounting under
the unchanged strict tolerances. Five native wire fixtures, thirteen real
capture corruptions and a fresh root replay pass. This repairs numerical
conservation and export fidelity; it does not qualify the underlying physical
capacitance model or install a replacement production extractor.

The hybrid composer preserves all 351 intrinsic devices, 748 metal terminal
anchors, 313 body/well terminals and 109 finite contacts. Named terminal mapping
handles PMOS and ESD-model pin order explicitly. Exact PDK contact geometry gives
81.6667 Ω per selected contact. Substrate spreading is still unresolved:
`BODY_ESD_RETURN` and `WIRE_CREF` remain separate, explicit external boundaries.
The full hybrid initializes cleanly at zero bias; that is not powered operation.

A separate passive experiment retains every wire R/C but omits intrinsic
junction loads. At 8 GHz, emitter-to-sampler differential gain is 0.606–0.608
with ideal emitter sources, 0.535–0.536 with 25 Ω per source, and 0.475–0.476
with 50 Ω. DC gain is one. These conditional measurements demonstrate a real
interconnect loading problem; they are not extracted oscillator performance.
The [strict wire result](https://github.com/Melihakbulut221/nssoc/blob/73355015788665ed2b5a79c03eb38d02546734e5/hw/soc/pcie-evidence/20261004-continuous-rx-and-pfd/wire-precision-v3.json)
and [hybrid/native transfer receipt](https://github.com/Melihakbulut221/nssoc/blob/73355015788665ed2b5a79c03eb38d02546734e5/hw/soc/pcie-evidence/20261004-continuous-rx-and-pfd/wire-hybrid.json)
preserve the raw network, failure controls and boundary assumptions.

## Detailed routing does not yet close timing

Both standalone RXv2 and repaired TXv3 have zero final signal-router DRC markers.
Their actual nominal extracted RC still fails the unchanged 4 ns constraint:

| Actual nominal RC, slow cell corner | Setup (ns) | Data hold (ns) | Recovery (ns) | Removal (ns) |
|---|---:|---:|---:|---:|
| RXv2 before the next repair | −1.139151 | −0.067221 | +1.297444 | +0.471319 |
| TXv3 after sizing and rerouting | −0.796714 | +0.108338 | −0.208271 | +0.103013 |

The same nominal RC is used for three cell corners; these are not RC process
corners. RX's subsequent 1,227 cell upsizes and 149 hold buffers preserve all
1,796 state identities and 5,419 binary functions, and pass the original six
native port cases. Its new detailed route and extraction must finish before
timing acceptance. TX buffering attempts fail native route-tree coverage checks;
those failures remain recorded. A separately versioned pipeline is being tested.
No clock relaxation, false path or positive estimated slack replaces extraction.

The [RX route/repair proof](https://github.com/Melihakbulut221/nssoc/blob/73355015788665ed2b5a79c03eb38d02546734e5/hw/soc/pcie-evidence/20261004-continuous-rx-and-pfd/rx-postroute01.json)
and [TX fresh extraction](https://github.com/Melihakbulut221/nssoc/blob/73355015788665ed2b5a79c03eb38d02546734e5/hw/soc/pcie-evidence/20261004-continuous-rx-and-pfd/tx-drt03.json)
link complete public archives. These are signal-only standalone layouts, without
completed power grids, full foundry GDS checks or main-chip adoption.

## Thermal method and a newly identified model-range limit

The version-four thermal method adds cycle minimum/maximum envelopes to cycle
means, rejecting growing ripple that a mean-only gate can miss. Its finite
controls, original-data replay and independent method review pass. The second
1 µs simulation is still running and publishes every full waveform chunk without
decimation. The original first-case failure remains unchanged; paired convergence
has not been accepted.

Source inspection also finds that the frozen VCOv3 uses one 32 µm HV PMOS while
the exact model documents a validated width range of 0.30–10 µm. This inherited
limitation applies to the trim/thermal experiments as well. Their captures remain
useful diagnostics, but cannot demonstrate validated model geometry. A separate
four-device 8 µm revision is being evaluated; no equivalence is presumed.
The [exact source/model witness](https://github.com/Melihakbulut221/nssoc/blob/73355015788665ed2b5a79c03eb38d02546734e5/hw/soc/pcie-evidence/20261004-continuous-rx-and-pfd/thermal-inherited-mos-width.json)
and [version-four method receipt](https://github.com/Melihakbulut221/nssoc/blob/73355015788665ed2b5a79c03eb38d02546734e5/hw/soc/pcie-evidence/20261004-continuous-rx-and-pfd/thermal-v4.json)
record these boundaries.

Remaining product gates include actual feedback and CDR acquisition, continuous
wide packet retirement, Ordered Sets and LTSSM, physically viable supply/clock
routing, body/parasitic and ESD stress validation, main-chip integration and the
earlier SRAM, full-chip LVS/timing and manufacturing requirements. None is marked
closed by the primitive, RTL or standalone router results above.
