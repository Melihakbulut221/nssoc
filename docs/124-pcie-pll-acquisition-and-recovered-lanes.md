# 124 — Nominal PLL acquisition and recovered-lane integration
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured development — 5 October 2026

The first 1 µs nominal PLL acquisition passes its frozen frequency/phase-span
screen and an independent replay of every published sample. Complete-block
clock crossing now passes actual IHP cell simulation, and four recovered
lanes have a tested RTL composition. The latest standalone receiver route
has zero router DRC violations and positive nominal extracted hold slack in
all three cell corners. **Its slow-corner setup still fails. Full PCIe Gen3 x4,
qualified PLL/CDR/SERDES, complete PCS/LTSSM, main-chip physical integration,
qualified RC/ESD and product approval remain open.**

The [source and evidence inventory](../hw/soc/pcie-evidence/20261005-pll-acquisition-and-recovered-lanes/root-verification.json)
pins every file and links the immutable public captures. The
[previous record](123-pcie-variable-skp-and-native-receive.md) retains its
earlier results; these separate experiments are not a combined working link.

## First complete nominal PLL acquisition

The native experiment uses a 5 ps time step through 1 µs. Its reviewer
rehashed all **80 public parts, 202,716 rows and 167,443,416 binary64 values**,
recomputed all **539 device safety records**, and independently rebuilt the
actual clock edges, ordinals and acquisition windows. The reconstructed
edges are identical to the author's arrays.

| Fixed measurement interval | Frequency error | Phase span |
| --- | ---: | ---: |
| 800–900 ns | −19.970463 ppm | 1.797378 ps |
| 900–1000 ns | −15.734187 ppm | 1.416099 ps |

Both windows meet the unchanged 100 ppm and 50 ps limits without an ordinal
slip. This measures frequency error and phase **span**, not zero phase offset;
the static offset remains approximately 257–261 ps. The smallest current
margin is only **1.896511 µA** below the inherited 3 mA-per-emitter limit.
The [complete native and independent review receipt](../hw/soc/pcie-evidence/20261005-pll-acquisition-and-recovered-lanes/pll-first1us-pcie-pll-first1us-5ps-validation-20261005.json)
preserves the exact source, models, device predicates and diagnostic logs.

A separate matched 2.5 ps, 1 µs experiment is running with its comparison
limits declared before completion. It is not counted as a convergence pass.
The earlier 400 ns failures remain failures. PVT, jitter, thermal behavior,
physical loop extraction and qualified PLL/CDR operation are still required.

## Complete records across four recovered clocks

The new CDC transfers **200 bits per record**: all 194 received bits, the
three-bit length code and SKP/EIEOS/realignment metadata. It uses the exact
existing MIT-licensed Ethernet vendor `axis_async_fifo` copy. A depth of 32
means 32 RAM records plus two prefetched read records. The recovered input
cannot wait for backpressure: overflow, alignment loss or an illegal length
halts the epoch. Either clean level reset resets both domains; independent
release synchronizers and startup acknowledgments also handle a stopped clock.

The RTL checks cover three depths, and **16,513 mapped SG13G2 cells pass all
seven actual asynchronous port cases**, with zero failures or skips. Twelve
additional native-method controls include real parent termination, failed
evidence writes and scratch-floor cleanup. The
[native receipt](../hw/soc/pcie-evidence/20261005-pll-acquisition-and-recovered-lanes/cdc-native-validation.json)
retains simulator timing-check warnings. These are finite functional tests,
not metastability, SDF or physical CDC qualification.

The separate `soc_pcie_gen3_recovered_x4_v1` connects four frozen v2 aligners
and four CDCs. Seven full raw-port scenarios cover all 32 initial bit phases,
all five SKP lengths, independent recovered clocks, lane stalls, overflow,
loss, forced realignment and coordinated restart. Twelve distinct controls
include nine actual wiring faults and two invalid-depth elaborations. An
independent [source review](../hw/soc/pcie-evidence/20261005-pll-acquisition-and-recovered-lanes/recovered-x4-peer-review.json)
checks the reset and synchronized common-domain fault barrier. A buffered
prefix may retire before a fault crosses; downstream logic must discard the
aborted epoch. The outputs remain four **independent, unpaired lane streams**.
Common-clock availability is not lane deskew.

## Local SDS lock before the clock crossing

A separate v3 aligner recognizes the complete aligned SDS ordered set and
locks locally in the recovered clock domain. Once locked it suppresses EIEOS
search, so an EIEOS bit pattern inside legal Data Blocks cannot move the
boundary during the common-domain round trip. Exact aligned EIEOS blocks
are still classified with no realignment. Reset, force and actual alignment
loss clear the lock; variable SKP boundary adjustment remains active.

The [source acquisition and contract](../hw/soc/pcie-evidence/20261005-pll-acquisition-and-recovered-lanes/lane-sds-contract.json)
bind a PCI-SIG-authored Base 4.0 reference: section 4.2.2.2.1, pages 236–237,
and section 4.2.4.6/Table 4-14, page 279. The exact local PDF was checked
against the [reference mirror](https://www.pedestrian.com.cn/_downloads/d2f2495e73c44b8c3a8dfd4c399f50f0/PCIE_V4.0.pdf);
it is not redistributed. The Gen3 SDS encoding is OS header `01`, `E1`,
then fifteen `55` symbols.

**36 controls pass:** eleven real port cases, 24 actual RTL faults and an
exact v2 algorithm-conservation check. They include all bit phases,
cross-block false EIEOS patterns, incomplete and malformed SDS, and all 25
adjacent SKP-length transitions while locked. Native-cell replay is pending.
This source is separate from the four-lane v1 composition above. LTSSM state
qualification, first-Data-Block policy, deskew and the next integration remain
separate gates.

## VCO emitter returns improve the extracted result

Local VCO v5 expands ten real AVSS return via stacks, retaining all 62 devices
and their exact parameters. All 39 occupied layers are compared against v3;
changes are confined to the declared return-stack boxes. The independent
physical checks pass **560 main DRC categories with zero markers**, strict
deep and flat 62-device transistor LVS and six LEF ports. Actual malformed
geometry and reference controls reject.

Fresh development extraction retains **551 R, 564 C**, all 151 anchors and
the complete 441-entry collapsed coupling matrix. At the same 0.6 V control,
the complete circuit reaches **7.418179 GHz**, compared with v3's 7.273200 GHz
and the retained v4 regression of 7.215390 GHz. Every one of 30 HBT electrical
screens passes, and an independent full-wave reduction verifies **43 complete
cycles** with both signed 300 mV excursions. The
[complete independent waveform record](../hw/soc/pcie-evidence/20261005-pll-acquisition-and-recovered-lanes/vco5-wire-root-wave-peer.json)
does not remove the remaining 8 GHz deficit. Phase and geometry measurements
point to the long final ring-stage connection as the next physical target.
No ideal-short, R-only or relaxed electrical-limit substitution is used.

## Parser and routed receiver timing remain distinct

Integrity parser v4 replaces the serial control decision chain with ordered
Boolean transition composition. Its finite controls include 32,768 arbitrary
parser states, 8,192 independent frontier combinations, 4,736 transition
matrix vectors, 52 direct/miter port cases and 19 actual mutations. The native
map has **73,935 cells**; all **278,267 imported cell-pin bits** preserve the
mapped graph, with six actual graph faults rejected.

At the unchanged 4 ns target, its preplacement setup is **−5.968056 ns SS,
−2.315121 ns TT and −0.189406 ns FF**. All fail. The
[timing comparison](../hw/soc/pcie-evidence/20261005-pll-acquisition-and-recovered-lanes/integrity-v4-timing-comparison.json)
retains the initial signed-label import rejection and a report-parser mistake
that selected the first recovery path instead of the worst setup group.
The corrected parser takes the minimum across every required group. A separate
retirement-cache candidate is under verification; it is not included as a pass.

The smaller prefetch receiver's repair08 is a different implementation. Its
finished detailed route has zero router DRC violations and an unchanged
logical netlist. All 1,804 state bits and 5,443 next-state/output functions
match, ten proof faults are rejected and six actual physical-netlist port
cases pass. Fresh OpenRCX extraction from **that exact routed database** gives:

| Cell corner, same nominal RC | Setup slack | Hold slack |
| --- | ---: | ---: |
| SS | **−1.087295 ns** | +0.017370 ns |
| TT | +0.858905 ns | +0.046886 ns |
| FF | +1.957524 ns | +0.069723 ns |

The [route and extraction receipt](../hw/soc/pcie-evidence/20261005-pll-acquisition-and-recovered-lanes/rx-repair08-validation.json)
keeps the unchanged 4 ns clock, I/O assumptions and full reports. Hold passes
this finite nominal screen; slow setup still fails. Reusing one nominal RC
model across three cell corners does not establish RC process-corner signoff.
An [exact-method supplement](../hw/soc/pcie-evidence/20261005-pll-acquisition-and-recovered-lanes/rx-repair08-methods-validation.json)
completes the proof-kernel and successful replay launcher omitted from the
first capture glob, with a fresh proof replay over the archived graphs. The
original Python startup failure and all earlier timing failures remain intact.
Targeted wire-buffer repair10 and the transmitter's reroute continue as
separate candidates. Full-chip timing, LVS and production approval remain open.
