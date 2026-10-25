# 123 — Variable SKP reception, native packet consumers and clock layout
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Source-bound development — 5 October 2026

The variable-length SKP receiver now passes actual IHP cell simulation, and
compacting the DLLP consumer lets its complete six-case native regression run
within a separately declared 4 GiB process limit. Local VCO layouts also have
new transistor, geometry and complete waveform evidence. **Full PCIe Gen3 x4,
PLL/CDR lock, complete SERDES/PCS/LTSSM, qualified RC/ESD and main-chip physical
integration remain open.** These are separate block results, not a combined
working serial link or manufacturing approval.

Source commit `e3b7d6de61bdd2a4310e32443769ed1adad351c6` binds the
[finite evidence and source inventory](https://github.com/Melihakbulut221/nssoc/blob/e3b7d6de61bdd2a4310e32443769ed1adad351c6/hw/soc/pcie-evidence/20261005-pcs-clock-and-native-receive/root-verification.json).
The [preceding record](122-pcie-limiter-local-layout-and-rx-repair.md) keeps
its original failures and measurements. Complete native inputs, mapped
circuits, logs, waveforms and deliberately corrupted cases are available in
the immutable public capsules referenced by each receipt below.

## Variable-length SKP reception

A separate lane-aligner v2 receives an uninterrupted 32-bit recovered-clock
stream without input backpressure. After exact EIEOS acquisition it preserves
normal 130-bit blocks and SKP blocks with 4, 8, 12, 16 or 20 `AA` symbols,
followed by `E1` and three retained trailer bytes. Including the sync header,
the five lengths are **66, 98, 130, 162 and 194 bits**. The receiver validates
the received prefix and SKP_END boundary, masks unused output bits and resumes
at the actual next block boundary. Trailer LFSR interpretation remains a
separate responsibility.

These lengths and boundary behavior follow Altera's
[Gen3 transceiver description](https://docs.altera.com/r/docs/683779/current/stratix-v-device-handbook-volume-2-transceivers/supported-features-for-pcie-gen3).
The [Intel PIPE 7.1 interface specification](https://cdrdv2.intel.com/v1/dl/getContent/643108)
describes four-symbol compensation and related error handling in sections
6.1.4, 8.14 and 8.27. The `AA`/`E1` encoding is additionally corroborated by a
[public patent disclosure](https://patents.google.com/patent/CN103713689A/en),
which is not treated as normative protocol authority. The reference PDF is
not redistributed in the project capsules.

Five positive scenarios cover all 32 input bit phases, all 25 length
transitions, malformed prefixes, interrupted maximum-length blocks, reset and
reacquisition, and single-bit EIEOS corruption. Twelve actual RTL mutations
are rejected by the independent output oracle. The same cases pass/reject
as intended after **thirteen independent native mappings**; the unmodified
candidate contains **5,192 SG13G2 cells**. The
[native receipt](https://github.com/Melihakbulut221/nssoc/blob/e3b7d6de61bdd2a4310e32443769ed1adad351c6/hw/soc/pcie-evidence/20261005-pcs-clock-and-native-receive/skp-native-result.json)
uses the original cell models and explicit 4 ns testbench clock. It establishes
finite functional behavior, without SDF or physical timing acceptance. Clock
compensation, asynchronous crossing, lane deskew, polarity and LTSSM remain
integration work.

## Smaller DLLP consumer reaches native simulation

Consumer v5 keeps all 64 owner entries, six-bit owner identifiers, sixteen-bit
epochs and thirteen-bit byte counters. Four body contexts share input gathering;
ordered forwarding handles repeated owners within one beat, and a static
last-writer scatter preserves descriptor/body/release priority. No owner or
counter width is reduced.

Forty finite RTL controls include public old/new comparisons, full counter
arithmetic, forwarding faults and **2,560 arbitrary prestate cases** that compare
all 64 entries, twelve fields per entry and the next-state/public outputs.
Balanced mapping shrinks from **198,647 cells in v4 to 128,490 in v5** (35.32%).
This is a mapped cell-count reduction, not a measured physical area or timing
result.

| Frozen attempt | Native compiler | Actual port cases |
| --- | --- | --- |
| v4, original 2 GiB limit | `std::bad_alloc` | None executed |
| v4, separate 4 GiB limit | `std::bad_alloc` | None executed |
| v5, original 2 GiB limit | `std::bad_alloc` | None executed |
| v5, separate 4 GiB limit | Pass | **6 passed, 0 failed, 0 skipped** |

The separate v5 replay uses the exact prior 128,490-cell netlist, source,
models and six case identities; it does not resynthesize or change the clock.
Its initial 8 GiB available-memory and 1.3 GiB scratch gates, continuous 2 GiB
available-memory and 528 MiB scratch floors, and absent elapsed-time watchdog
remain explicit in the
[completed replay evidence](https://github.com/Melihakbulut221/nssoc/blob/e3b7d6de61bdd2a4310e32443769ed1adad351c6/hw/soc/pcie-evidence/20261005-pcs-clock-and-native-receive/consumer-v5-4g-validation.json).
Earlier failures are retained as failures. Physical implementation and timing
of this consumer are still required.

## CRC acceleration does not close parser timing

Integrity parser v3 replaces serial CRC recurrences with parallel GF(2)
transforms for carried and newly started packets. The source-bound controls
check 1,691 basis/zero/random transforms, 32,768 arbitrary parser states and
real arithmetic/control faults. An additional independent alignment oracle
covers all sixteen DWORD start positions; it catches a fault that the earlier
finite alignment coverage missed. The preserved 12-case baseline and one-case
alignment extension jointly cover the 13 cases in direct and miter modes at
two packet limits; this is recorded as a union of actual runs.

The candidate maps to **74,394 cells**, and every one of **279,568 imported
native pin bits** matches the mapped connectivity graph. At the unchanged
4 ns constraint, actual preplacement setup remains **−6.858448 ns at SS,
−2.868497 ns at TT and −0.516430 ns at FF**. All are failures. The
[native comparison](https://github.com/Melihakbulut221/nssoc/blob/e3b7d6de61bdd2a4310e32443769ed1adad351c6/hw/soc/pcie-evidence/20261005-pcs-clock-and-native-receive/integrity-v3-timing-comparison.json)
and structural word-support analysis of the mapped path point to the ordered four-word control
chain as the next repair target. Complete native equivalence and physical
placement/routing are separate gates.

## Local clock geometry: preserve the measured regression

Local VCO v3 changes the bias/ground returns and keeps all 62 devices. V4
starts from v3 and enlarges six actual ring transistor terminal escapes and
via arrays. Each has zero markers across 560 main DRC categories, strict deep
and flat 62-device transistor LVS, six physical ports and actual corrupted
geometry/reference controls. These checks concern the separate VCO cell.

Fresh development extraction retains **547 R / 561 C** for v3 and
**883 R / 765 C** for v4. At the same 0.6 V control, 2.3 V supply, 50 fF per
output and 6–12 ns measurement interval:

| Local geometry | Native clock frequency | Complete ±300 mV cycles | All 30 HBT electrical screens |
| --- | ---: | ---: | --- |
| v3 bias-return repair | **7.273200 GHz** | 42 | Pass |
| v4 ring terminal/via expansion | **7.215390 GHz** | 43 | Pass |

V4 lowers the six ring-path resistances from approximately 43–53 Ω to
19–26 Ω, but the complete circuit oscillates about **0.795% more slowly**.
The real capacitance/coupling changes remain in the model; no ideal short or
R-only substitution is used to claim improvement. A separate exact-source supplement completes the offline v3/v4 composer
inputs omitted by an earlier packaging glob; the original capsule remains
unchanged. Independent root reductions
reread every native sample, all HBT bounds and every complete output cycle.
The [v4 result and regression](https://github.com/Melihakbulut221/nssoc/blob/e3b7d6de61bdd2a4310e32443769ed1adad351c6/hw/soc/pcie-evidence/20261005-pcs-clock-and-native-receive/local-v4-wire-validation.json)
remain below 8 GHz and are not RF-qualified PEX, PVT, jitter, BER or ESD signoff.
The next candidate starts from the better v3 geometry and targets emitter
return stacks separately.

At this source snapshot the separate 1 µs PLL acquisition experiment was
still running.
Its new reviewer has 31 controls plus an actual public raw-part replay and
four corrupted-part rejections. This verifies the review method, not full-run
lock. The earlier paired 400 ns frequency/phase failures remain unchanged.

## Repair the hosted verification entry points

The generic cocotb runner previously invoked the SoC PCIe Makefile without
the specialized source list, CPU ROM or usable cocotb configuration. The
Makefile now dispatches to the existing real checker, prepares pinned core and
interface sources when absent, and returns its actual exit status and fresh
XML. Both normal and isolated initially unprepared checkouts pass the two
real CPU/PCIe cases; two HDL fault controls fail as expected. Global test
counting, locking and the actual RTL are unchanged.

The lint gate also now compiles 34 hash-bound historical PCIe modules under
an actual isolated Yosys `default_nettype none`/`-noautowire` frontend check.
A real undeclared-wire counterexample rejected the first wrapper design,
whose trailing restoration to `wire` defeated Yosys's check; that failed
attempt is preserved. The corrected compiler invocation rejects the fault.
New unregistered RTL still requires in-file guards, and changed historical
source bytes fail the manifest check.

Whole base-SoC lint passes with the original diagnostic debt. The prior
conditional PCIe insertion moved existing source lines; **164 ledger entries
across profiles now point to byte-identical relocated lines**. No warning
category, message, column, multiplicity or architectural reason is waived or
removed. This is verified in the
[guard and lint evidence](https://github.com/Melihakbulut221/nssoc/blob/e3b7d6de61bdd2a4310e32443769ed1adad351c6/hw/soc/pcie-evidence/20261005-pcs-clock-and-native-receive/nettypes-validation.json).
The in-progress routed RX/TX repairs, full-chip LVS and final timing remain
separate work; these software checks do not close them.

Two lane-aligner headers were subsequently corrected to the project's existing
CERN-OHL-W hardware policy. The exact inverse bridge preserves every executable
RTL byte and updates only source identity constants in the native runners and
manifest. Original Apache-tagged files and native receipts remain at the
source commit above; historical cell runs are not relabeled as runs of new
bytes. The [comment-only bridge](../hw/soc/pcie-evidence/20261005-pcs-clock-and-native-receive/license-comment-bridge.json)
records all seven changed files and the 39+1 successful RTL/lifecycle test union,
including the first stale-hash assertion failure.

The [subsequent acquisition and recovered-lane record](124-pcie-pll-acquisition-and-recovered-lanes.md) preserves this snapshot and adds the first independently replayed 1 µs PLL result, native CDC, four-lane RTL, local SDS locking and fresh nominal extracted receiver timing.
