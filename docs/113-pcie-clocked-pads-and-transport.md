# 113 — Clocked PCIe pads, native device extraction and TX transport
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured progress — 4 October 2026

Subsequent TX timing, divider and native tap results are recorded in
[document 114](114-pcie-timing-divider-and-native-taps.md); the measurements below
retain their original source revision and scope.

The stronger clock circuit from [document 112](112-pcie-driven-clock-and-scrambling.md)
now has an actual routed connection to the four-lane analog bank and its sixteen
serial pads. Separate TX transport modules pass native cell functional checks.
A native extractor correction now measures repeated HBT emitter geometry. These
are concrete steps toward the open GR801-class SoC; a complete Gen3 x4 link and
main-chip physical integration remain open.

Source and native evidence commit: `e3e167830d3d7496eb4911d09c7db715930ba88d`.
The [root source/capsule review](https://github.com/Melihakbulut221/nssoc/blob/e3e167830d3d7496eb4911d09c7db715930ba88d/hw/soc/pcie-evidence/20261004-physical-path/root-source-capsule-review.json)
checks eleven whole archives, their available member inventories and 29 live
source pins. These hash checks support reproducibility; they do not replace
native simulation or signoff. The new physical and analog source controls also
passed 191 focused local tests, with 44 separate native-extractor source tests.

## Actual clock and pad geometry

The clocked bank connects eight differential clock branches from the frozen
strong-driver VCO to the frozen receiver/sampler parent. Its GDS has 54 ports,
122 expanded HBT instances, 81 resistors, six MIM capacitors, one PMOS,
108 finite substrate taps and one n-well tap. Main-deck DRC has zero violations
across 560 categories; deep and flat LVS pass. Twenty-three actual schematic
and geometry counterexamples, including all eight clock opens, are rejected.
See the [clocked-bank receipt and archive identity](https://github.com/Melihakbulut221/nssoc/blob/e3e167830d3d7496eb4911d09c7db715930ba88d/hw/soc/pcie-evidence/20261004-physical-path/clocked-bank.json).

The padded wrapper adds sixteen real bondpads, thirty-two native ESD diodes and
sixteen routed serial conductors. All nine parent geometries retain their
conductive/device layers under native zero-XOR checks. This wrapper has 56
ports and 232 combined devices in native LVS. Main-deck DRC again has zero
violations across 560 categories; deep/flat LVS and the LEF pin/obstruction
checks pass. All 29 actual negative controls are rejected, including each
serial open and incorrect supply/body connections. The
[padded-bank receipt](https://github.com/Melihakbulut221/nssoc/blob/e3e167830d3d7496eb4911d09c7db715930ba88d/hw/soc/pcie-evidence/20261004-physical-path/padded-clocked-bank.json)
and [native GDS/LEF/control archive](https://github.com/Melihakbulut221/nssoc/raw/e3e167830d3d7496eb4911d09c7db715930ba88d/hw/soc/pcie-evidence/20261004-physical-path/padded-clocked-bank.tar.xz)
preserve the first checker preflight failure as well as final passing runs.

The diode return is the shared substrate, explicitly named `ESD_RETURN`.
The 108 finite `SUB`–`ESD_RETURN` taps remain present; `AVSS` and the three
analog supply rails remain distinct. This changes the parent body connection
and its impedance. It is not an isolated ground, an ESD stress qualification,
a high-frequency pad/channel qualification or proof that the clock still meets
its selected loaded transient bounds after routing. This separate macro is
not instantiated in the main chip.

## Native HBT multiplicity correction

A private Magic source/technology extension measures connected emitter
components on the actual geometry plane. It checks equal rectangular geometry
and a common electrical node, then emits the measured multiplicity. It uses no
instance-name inference or prescribed emitter count. The unchanged fixture
now produces the correct C/B/E connections, 70 nm × 900 nm emitter dimensions
and Nx values of 1, 2 and 4 in all eight orientations.

A duplicate unchanged-layout positive also passes. Five physical faults are
rejected: a missing finger is measured as Nx=3, a narrowed emitter as 30 nm,
a collector/base short merges ports, an emitter-via open reports different
nodes, and a removed tap changes the substrate connection. The source build
and [native controls](https://github.com/Melihakbulut221/nssoc/blob/e3e167830d3d7496eb4911d09c7db715930ba88d/hw/soc/pcie-evidence/20261004-physical-path/hbt-multiplicity-v3.json)
retain the failed first plane-selection draft. Without the opt-in parameter,
the previous and new private runtimes produce identical native device and
connectivity records. The original installed runtime and PDK are unchanged.

**Finite substrate taps still extract incorrectly in this native PEX path.**
Passing KLayout LVS of the physical macro does not repair that separate Magic
model. The bounded HBT fixture is not qualified full-bank parasitic extraction.

## Divider and tuning results, including failed cases

The real cascaded divider connects the driven VCO to two CML divide-by-two
stages. The first conditioner version passes six of eight positive cases.
The second doubles the relevant resistor lengths and increases its physical
feed-forward MIM size: seven of eight positive cases now pass. The hot-fast
headroom failure improves from 0.363 V to 0.421 V minimum VCE under unchanged
limits. Hot-slow still fails second-stage regeneration; it is not accepted.
Both versions reject four actual functional faults and all final native
startups are numerically clean. Full waves are publicly archived and checked
through authenticated and anonymous downloads. The
[divider v1 receipt](https://github.com/Melihakbulut221/nssoc/blob/e3e167830d3d7496eb4911d09c7db715930ba88d/hw/soc/pcie-evidence/20261004-physical-path/divider-v1.json)
and [divider v2 receipt](https://github.com/Melihakbulut221/nssoc/blob/e3e167830d3d7496eb4911d09c7db715930ba88d/hw/soc/pcie-evidence/20261004-physical-path/divider-v2.json)
separate native measurements, author waveform replay and the bounded independent
source/deck review; the peer did not independently remeasure every waveform.

The coarse-tuning circuit uses actual switched MIM capacitance and native MOS
switches. Forty-two v1 executions produce six of seven strict same-code 8 GHz
corner brackets. Two additional bias-v2 pilots do not close the final corner.
All forty-four complete native waves have been
[published in eight verified chunks](https://github.com/Melihakbulut221/nssoc/blob/e3e167830d3d7496eb4911d09c7db715930ba88d/hw/soc/pcie-evidence/20261004-physical-path/trim-full-waves-release.json).
The original frozen trim receipt records its earlier unpublished state; this
later publication receipt supplies the archive bridge without rewriting it.

At the remaining fast corner, two longer 40 ns executions pass electrical
safety and the unchanged final functional spread limit. They still fail the
explicit thermal-convergence test: the last four 2 ns mean frequencies span
about 435 ppm and the dominant model thermal-node rate is 0.165 V/ns. Halving
the time step changes the final mean frequency by only 42.6 ppm; that agreement
does not establish thermal equilibrium. The original 4–12 ns failure remains
visible. The [40 ns receipt](https://github.com/Melihakbulut221/nssoc/blob/e3e167830d3d7496eb4911d09c7db715930ba88d/hw/soc/pcie-evidence/20261004-physical-path/trim-thermal40.json)
therefore explicitly records a failed convergence screen. No closed PLL or CDR
has been established by these tuning/division experiments.

## Actual TX transport and measured timing failure

The fixed transport scrambles 128 payload bits per logical lane with explicit
byte advance/XOR and after-block reseed controls, retains the two-bit header,
and connects the result to the actual 130/32 gearbox. Three RTL cases and the
same three native TT-cell cases pass; the native design has 16,498 IHP cells.
An independent bit-cell/serial-queue oracle checks masks, stalls, headers,
reset/flush and a saturated run of 494 blocks / 2,006 output words without
word bubbles. Eight real RTL mutations are rejected. Three actual process
lifetime tests cover the corrected timeout cleanup; both earlier timeout and
surviving-child failures remain in the
[fixed-path capture](https://github.com/Melihakbulut221/nssoc/blob/e3e167830d3d7496eb4911d09c7db715930ba88d/hw/soc/pcie-evidence/20261004-physical-path/tx_path.json).

Functional cell simulation does not establish the 4 ns clock target. Actual
cell-only STA with the same native TT library, an ideal 4 ns clock, 0.2 ns I/O
delays, 0.1 ns input transition and 0.01 pF output load gives **−46.20 ns setup
slack**. Preplacement repair adds 2,301 real buffers and improves this to
**−11.28 ns**, while reported minimum slack remains +0.26 ns. The remaining
critical path crosses the conditional scrambler feedback. These development
constraints and unplaced results are preserved in the
[timing failure capture](https://github.com/Melihakbulut221/nssoc/blob/e3e167830d3d7496eb4911d09c7db715930ba88d/hw/soc/pcie-evidence/20261004-physical-path/tx-path-timing-baseline.json).
No clock relaxation, false path or timing acceptance was applied.

A separate four-lane reservoir handles total block lengths of 66, 98, 130, 162
and 194 bits, retaining headers and rejecting length codes 5–7. Four RTL cases
pass. Native coverage is the exact union of three original cases and one added
remainder-drain case against the identical 13,107-cell netlist; the selected
additional invocation explicitly excludes the other three cases. This is not
reported as four tests in one native invocation. The new CI job runs all four
by default. Eight real HDL faults and three process-lifetime controls pass.
The [variable-length source-bound capture](https://github.com/Melihakbulut221/nssoc/blob/e3e167830d3d7496eb4911d09c7db715930ba88d/hw/soc/pcie-evidence/20261004-physical-path/variable_tx.json)
retains the escaped 30-bit readiness fault and the later directed test that
rejects it; a 31-bit threshold was equivalent because counts are always even.

These interfaces transport caller-supplied contents. Complete ordered-set
policy, training-sequence DC balance, SKP insertion/deletion, receive rate
compensation, lane alignment/deskew, SERDES and LTSSM remain separate work.
Closed PLL/CDR, qualified extracted timing and ESD, main-chip clock/reset/CDC
and pad integration, older Ethernet/NPU timing failures, full-chip I/O LVS,
DFT and manufacturing approval remain open.
