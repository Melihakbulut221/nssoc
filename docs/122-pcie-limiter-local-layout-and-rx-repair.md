# 122 — PCIe limiter-local layout and receive-path repair
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Source-bound development — 4 October 2026

The local VCO now starts with actual extracted development wires and reaches
its declared output-swing threshold at two bias points. Receive-path changes
also improve early timing and detailed-wire setup slack. These are measured
block advances; **full Gen3 x4, PLL/CDR lock, complete SERDES/PCS/LTSSM,
qualified RC/ESD and main-chip physical integration remain open**.

Source commit `22091f8caded90ef8c574d339c0524048e97a527` binds
[278 distinct root-run focused checks](https://github.com/Melihakbulut221/nssoc/blob/22091f8caded90ef8c574d339c0524048e97a527/hw/soc/pcie-evidence/20261004-limiter-local-and-rx-repair/root-verification.json).
Native runs, independent waveform reductions and author-side checks are
recorded separately and are not added to that count. Earlier failures remain
available; [document 121](121-pcie-owned-receive-and-wire-feedback.md) retains
its original measurements.

## Actual local VCO geometry and wires

The separate limiter-local v2 layout retains all **62 circuit devices** and
thirteen finite contacts. It measures **560 × 407.03 µm**, passes **560 main
DRC categories with zero markers**, strict deep and flat transistor LVS,
six LEF-port checks and twenty deliberately corrupted physical/reference
cases. Three preceding geometry failures remain in the
[public layout capsule](https://github.com/Melihakbulut221/nssoc/blob/22091f8caded90ef8c574d339c0524048e97a527/hw/soc/pcie-evidence/20261004-limiter-local-and-rx-repair/limiter-local-layout-release.json).

The complete development wire network retains **446 resistors and 496
capacitors**. Its 151 geometry probes, twenty connected conductors and full
441-entry collapsed capacitance matrix are checked; thirteen native-output
mutations are rejected. Seventy-three passive cases and four complete powered
captures are preserved. With a 2.3 V supply, 50 fF per output and the unchanged
6–12 ns measurement window:

| Native case | Public clock edges | Mean frequency | Differential extrema | ±300 mV screen |
| --- | ---: | ---: | --- | --- |
| Intrinsic reference, 0.85 V control | 48 | 8.067168 GHz | approximately ±418 mV | Pass |
| Actual wires, 0.85 V control | 39 | 6.413742 GHz | −215.155 / +226.695 mV | Fail |
| Actual wires, 0.4 V control | 42 | 6.950343 GHz | −337.302 / +344.307 mV | Pass |
| Actual wires, 0.6 V control | 41 | 6.718168 GHz | −322.478 / +331.354 mV | Pass |

All thirty HBT electrical screens pass in these four finite captures. A root
review independently rereads every sample, clock crossing and HBT bound from
all three public wired archives. These results **do not establish 8 GHz,
steady-state operation, PVT, thermal equilibrium or RF-qualified extraction**.
The [aggregate record](https://github.com/Melihakbulut221/nssoc/blob/22091f8caded90ef8c574d339c0524048e97a527/hw/soc/pcie-evidence/20261004-limiter-local-and-rx-repair/limiter-local-wire-validation.json)
and [independent reduction](https://github.com/Melihakbulut221/nssoc/blob/22091f8caded90ef8c574d339c0524048e97a527/hw/soc/pcie-evidence/20261004-limiter-local-and-rx-repair/limiter-local-wire-root-bias-wave-peer.json)
retain that distinction.

The 0.4 V run also exposed a **337,464-byte executor-budget overshoot** during
final compression drain; its valid electrical measurements do not erase that
resource failure. A separate v3 controller checks writes and final drain while
reserving receipt space. Three actual FIFO subprocess controls exercise clean
drain and both resource failures. The subsequent 0.6 V run remains within the
original 80 MiB owned-scratch budget. Circuit, measurement windows and electrical
limits are unchanged.

## PLL acquisition remains a measured failure at 400 ns

Both fresh 400 ns transistor-loop runs preserve all 539 devices, zero-source
startup and 64 native OFF flags. All 539 finite electrical screens pass with
no numerical diagnostics. Full public replay covers **66,978,688 values at
5 ps** and **132,694,422 values at 2.5 ps**. The original fixed 100 ppm frequency
and 50 ps phase-span criteria still fail:

| Final 300–400 ns window | Feedback mean | Phase span |
| --- | ---: | ---: |
| 5 ps step | 99.857551 MHz | 128.387 ps |
| 2.5 ps step | 99.893442 MHz | 96.004 ps |

No-slip and control-voltage screens pass. The two final frequency observations
differ by about 359 ppm, so timestep convergence is also unproven. The
[5 ps record](https://github.com/Melihakbulut221/nssoc/blob/22091f8caded90ef8c574d339c0524048e97a527/hw/soc/pcie-evidence/20261004-limiter-local-and-rx-repair/pll400-long5-validation.json)
and [2.5 ps record](https://github.com/Melihakbulut221/nssoc/blob/22091f8caded90ef8c574d339c0524048e97a527/hw/soc/pcie-evidence/20261004-limiter-local-and-rx-repair/pll400-long25-validation.json)
remain failures. A separately declared 1 µs acquisition method uses the same
thresholds at 800–900 ns and 900–1000 ns, plus an independently defined rolling
window. Its source and runtime controls are committed; an ongoing native run
is not a passing lock result.

## Receive consumers, parser timing and actual routed repair

The new DLLP consumers rendezvous complete six-bit owner identifiers and
sixteen-bit epochs with four ordered descriptors and body handshakes. Good
packets wait for accepted body EOP; bad and nullified descriptors discard their
owner. TLP data remains full-width. V1/v2/v3 pass the finite raw-x4 composition
and malformed/abort controls. Nine public-port comparison cases include true
8,191-byte counter overflow; three intentionally different implementations
are rejected. V3 additionally checks all 262,144 local arithmetic inputs.

**The native consumer attempts do not pass.** V1 exhausts its 2 GiB address
space during synthesis. V2 maps to **269,767 cells**, then its simulator compiler
exhausts that limit before executing any port case. V3 preserves the behavior
but grows to **335,046 cells** and hits the same compiler failure. Its prefix
arithmetic is therefore not an area improvement. Exact failed outputs and
source revisions are in the
[v3 native receipt](https://github.com/Melihakbulut221/nssoc/blob/22091f8caded90ef8c574d339c0524048e97a527/hw/soc/pcie-evidence/20261004-limiter-local-and-rx-repair/consumer-v3-native-failure-validation.json).
Shared input-byte compaction is a separate follow-up, not a rewritten v3 pass.

A separate three-edit integrity-parser v2 speculates over the candidate block
before commit. All 27 finite controls and five old/new miter/source controls
pass. Balanced mapping uses **70,495 cells**. Every one of 267,604 imported
native pin bits preserves its driver graph. The complete 8,426-state semantic
bijection is recovered before ABC optimization; whole native equivalence is a
separate pending computation in this snapshot. At the unchanged 4 ns clock,
slow-corner preplacement setup improves from **−10.986376 ns to −7.136116 ns**;
TT and FF remain **−3.078468 ns** and **−0.629122 ns**. This is still a timing
failure and not a placed/routed result.

The separate byte-RX repair resizes 631 distinct cells. All **1,804 state bits
and 5,443 next-state/clock/reset/output functions** match the preceding native
circuit; ten injected proof-boundary faults are rejected and all six physical
netlist port cases pass. Fresh detailed routing completes with zero router DRC
errors and an unchanged logical netlist. Fresh nominal OpenRCX gives:

| Cell corner | Setup | Hold |
| --- | ---: | ---: |
| SS | −0.900703 ns | −0.089521 ns |
| TT | +0.969737 ns | −0.023910 ns |
| FF | +2.031864 ns | +0.023813 ns |

SS setup improves from −1.337970 ns, but setup and hold remain open. The 78
unannotated driver names are unused clock-load outputs in the exported netlist.
The same nominal wire model is reused across cell corners; it is not qualified
RC-corner signoff. Complete databases, SPEF, methods, proofs and original
admission failures are preserved in the
[public repair capture](https://github.com/Melihakbulut221/nssoc/blob/22091f8caded90ef8c574d339c0524048e97a527/hw/soc/pcie-evidence/20261004-limiter-local-and-rx-repair/rx-public-rx-sizeonly-release.json).
Subsequent buffering and hold repair are independent candidates requiring new
equivalence, routing and extraction. None of these block results constitutes
full-chip DRC/LVS, PCIe compliance or manufacturing approval.

The subsequent [variable SKP and native receive record](123-pcie-variable-skp-and-native-receive.md) retains this snapshot while adding complete native consumer cases, variable SKP reception, later VCO wire measurements and verification entry-point repairs.
