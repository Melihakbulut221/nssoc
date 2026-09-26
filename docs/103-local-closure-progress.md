# 103 — Local closure progress, 26 September 2026
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

This continuation implements and checks the next work identified by
[the product audit](102-remaining-product-gaps.md). No final product or foundry
acceptance is recorded. Every receipt identifies the source and measurement scope.

## Prepared source regression

The [complete pytest replay](evidence/prepared-pytest-bb5ddb1-20260926.json)
checks source `bb5ddb1` in a fresh local clone with pinned Ibex/TinyTapeout
dependencies. All **1,707 cases pass with zero failures and zero skips** in
375.78 seconds. All 1,669 previous testcase identities remain present; 38
new cases cover status, analog measurement and release-asset validation.
The fourteen previously skipped fixture cases all execute successfully.
The original unpublished intermediate controller count error is retained
in the archive and is separate from this successful final-source replay.
Publication after this source commit changes only documentation, records
and ignore/licence metadata; running physical/formal jobs retain their own
source identities. This does not replace their acceptance requirements.

## Current RTL and native memory replay

The [audited local replay](evidence/local-rtl-regression-1baeb63-20260926.json)
runs source `1baeb635453dccc8b122c0fc40ff3ee1613159a1` in a separate local
checkout, with unchanged tracked inputs and the explicit `full` interface
profile. The canonical cocotb discovery reports **508 passed, zero failures**.
Its 46 XML files contain sixteen actual skips:

* Twelve select encoder versus decoder DUTs. Each skipped case passes under
  the other DUT configuration.
* Three select appropriate one-bit versus wider TMR test configurations.
  Each skipped case passes at an applicable width.
* One tests disabled optional interfaces and applies only to `base`.
  The complementary base replay passes eight cases, including this one.
  Its six full-only skips all pass in the full replay.

The runner's seventeenth skip delegates native SRAM parity to a separate tool
environment. That driver subsequently passes all six profiles: 8,192-word
plain/ECC RAM and 16,384-word plain RAM, each with registered/unregistered reads.
The deliberately corrupted macro fails the functional comparison as required.
These results do not qualify replacement SRAM transistor timing or ROM contents.
The earlier fourteen pytest skips are a separate, already completed campaign.

The archive contains full logs, XML, input identities and audit code. The one
untracked `hw/soc/ext` symlink in the test checkout is recorded; it supplies
prepared dependencies. No tracked RTL/test source was altered. Frozen pilot
FI/gl/glfi reruns remain excluded by the canonical discovery and are not counted
as passes. Whole-core RVFI and final netlist/timing verification remain open.

## SRAM and status records

The [DP timestep comparison](evidence/sram-repaired-dp-timestep-20260926.json)
publishes the completed 25 ps waveform, forty transition comparisons, two
rejected measurement faults and retained failed initial attempts. The largest
delay difference from 50 ps is 0.020866732 ns. This closes the unpublished-result
item, with no extrapolated signoff or complete-characterization claim.

The status generator now accepts the newer complete pytest receipt and exact
32-SRAM geometry receipt. Its guards reject failed/incomplete counts, wrong
source/GDS identities and unsupported timing/manufacturing promotion. The old
physical timing row is explicitly historical. A fresh 170-task mandatory formal
sweep is running locally; the older published sweep is not relabeled current.

## Native resistor TX

`tx_cml_rsil.spice` and `tx_bank4_rsil.spice` replace the experimental TX's ideal
loads with native three-terminal IHP `rsil` devices, including self-heating.
Each load uses a 10 µm by 70.215 µm resistor body. The external predriver,
reference current, termination and illustrative PDN remain ideal stimuli.
`characterize_pcie_tx_rsil.py` crosses all three HBT corners with all three
resistor corners, three temperatures and three supplies, then adds bank/load,
fault and timestep cases: 97 actual simulations per reference-current setting.

The initial 2 mA reference fails the existing engineering screen in eight cases:
hot-corner transistor voltage margin falls below 0.4 V. The failed run is
retained. With a 1.5 mA reference, all 94 non-faulty cases meet the same
screen and all three faulty controls are rejected. Minimum screened transistor
voltage is 0.429866 V and minimum signed sample margin is 0.227035 V; the
maximum load branch current is 9.809433 mA. The model predicts at most 1.108751 K
resistor temperature rise in these non-faulty cases. The 0.5 ps comparison
changes margin by 0.000000474 V and supply power by 0.000040809 percent.
No voltage-margin threshold was relaxed.

The [complete experiment record](evidence/pcie-native-resistor-20260926.json)
links numbered lossless archives containing both 97-case matrices, original
waveforms and physical checks. Its verdict remains **REVIEW**: 31 corrected-run
cases contain numerical/startup warnings and the compiler emits three warnings
about constant `$simparam` evaluation. Neither the successful engineering
screen nor the publication-integrity verdict waives these issues.

The native resistor PCell has a generated GDS and separately checked schematic:
560 main DRC categories have zero markers, three-terminal LVS matches, and an
incorrect-width schematic fails. The first two-terminal schematic attempt
failed the native reader and is preserved. The corrected unit has an implicit,
untapped substrate; it does not provide the complete TX substrate connection.

Nine DC checks verify the temperature ratios and self-heating response against
the explicit TC1/TC2 law. A prior naive absolute-resistance calculation failed
and remains failed: that simple sheet/contact formula omits compact-model width
and field terms. It is retained as an informational estimate, not an exact
oracle. OpenVAF compiler warnings are retained and the model is not qualified.

The [IHP process current limits](https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/02_process_control_params.html#maximum-current-densities)
make contact and metal geometry relevant to lifetime. A PCell's displayed body
current estimate does not establish terminal current capacity. Contact/bar
current, substrate taps, routing/PEX and final TX geometry still need closure.
This work does not supply RX/CDR/PLL, serializer, complete protocol controller,
PHY integration or PCIe compliance evidence.

The generator's final [licence-header adjustment](evidence/pcie-load-generator-header-equivalence-20260926.json)
is byte-distinct but has exactly the same Python AST and generated header text
as the source archived with the physical measurement. No measured geometry or
netlist was altered. A previously published large diagnostic archive is linked
at its immutable GitHub revision to keep the documentation site within its
existing 64 MiB asset budget; the archive remains in the repository.

The new raw archives in this continuation are delivered as
[release assets](https://github.com/Melihakbulut221/nssoc/releases/tag/evidence-20260926-local-closure),
with [SHA-256, sizes and retrieval instructions](evidence/README.md#new-raw-evidence-delivery)
kept in Git. This follows the external review's binary-delivery requirement.

## RC coupling diagnostic

A [new matrix comparison](evidence/rc-grounding-diagnostic-20260926.json) tests
whether grounding every reference coupling explains the RC mismatch. It does
not: 13,138 pairs still differ. The coupled reference totals 27.418462 pF; the
fully grounded approximation totals 46.855160 pF, versus 43.910549 pF in the
actual RC export. This changes neither the extracted circuit nor its failed
acceptance verdict. The upstream [ResReadCapacitor implementation](https://github.com/RTimothyEdwards/magic/blob/fd12c39c37f26a0fe6e04698b1011e31b8bd3229/resis/ResReadExt.c)
contains a signal-extraction path that adds each coupling to both terminal
node capacitances. That observation motivates the diagnostic; it does not
prove that grounding is the only source of the measured discrepancy.

## Ethernet software continuation

The [PHY management driver](90-gigabit-ethernet.md#phy-management-software-26-september-2026)
adds tested Clause 22 access, configuration readback and bounded gigabit-only
negotiation through the existing MDIO register. This closes the absent software
management routine sub-item, with host-model and RV32 compile evidence only.
It does not close DMA, external PHY/pad integration, board tests or wire-rate
acceptance. The earlier 1,707-test receipt remains bound to `bb5ddb1`; this
subsequent driver has its own explicit test inventory.

## Complete experimental TX cell layout

The [TX cell evidence](evidence/pcie-tx-cell-20260926.json) now covers a complete
experimental current-steering cell: four native `npn13G2` instances with emitter
multiplicities 1/8/8/8, two 10 µm × 70.215 µm native `rsil` loads, eight native
2 µm × 2 µm substrate contacts and routed Metal1–Metal5 connections. This is
one TX cell; it is not a complete PCIe PHY or integrated four-lane chip macro.

The final GDS passes all 560 main DRC categories with zero markers. Strict LVS
matches seven combined devices, including the parallel-combined substrate
contact, with no extraction diagnostics. Wrong resistor width, wrong HBT
multiplicity, missing contact and wrong input connection each produce an actual
`NoMatch`. The failed first geometry remains in the archive: Metal2 spacing,
an incorrectly placed substrate label and an omitted schematic tap model were
corrected without suppressing rules or disabling tap extraction.

The layout-derived device netlist is translated to the native simulation models
with its actual terminals and substrate contact retained. The native area and
perimeter formula gives 10.208333 Ω for the combined contacts. Three zero-volt
current probes are the only added measurement devices. All **87 single-cell
cases** complete: 84 normal cases pass the existing screen and three injected
faults are rejected. The minimum sampled signed differential margin is
0.227035 V. Twenty-seven simulations retain numerical/startup warnings, and
OpenVAF retains three constant-`$simparam` warnings. The result is an engineering
screen requiring review, not model or PCIe compliance qualification.

Peak measured load and tail currents are 9.799280 mA and 13.249469 mA. The
layout was widened after this measurement: load via stacks have two rows, the
tail collector has two rows, the reference collector has four columns, and the
shared tail/ground buses are 8 µm wide. The final DRC/LVS replay passes again.
Its translated device model is **byte-identical** to the simulated model; this
transfers only device connectivity/model results, not metal parasitic timing.
Actual GDS cut counts are audited. Nominal capacity calculations use the
[IHP 105°C current table](https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/02_process_control_params.html#maximum-current-densities).
They do not establish current sharing, native bar-contact limits, 125°C
lifetime derating, package behavior or foundry EM acceptance.

The generator is [make_pcie_tx_cell.py](../hw/soc/flow/make_pcie_tx_cell.py).
The strict [device-netlist adapter](../scripts/translate_pcie_tx_cell.py) and
existing load monitor pass 36 targeted tests with zero skips. This is a scoped
new test run, not a replacement for the earlier complete pytest receipt.
The raw GDS, LVS database, every simulation waveform, warnings, scripts and
failed iterations are delivered through the
[TX/SRAM evidence release](https://github.com/Melihakbulut221/nssoc/releases/tag/evidence-20260926-tx-cell-sram-arcs).
Metal/substrate PEX, RX/CDR/PLL, serialization, full controller, pad/ESD and chip
integration remain open.

## Repaired SRAM read-constraint measurement

The [completed read-arc evidence](evidence/sram-repaired-dp-read-arcs-20260926.json)
uses eight fresh transistor simulations of the repaired DP capacitance-only
layout at TT, 1.2 V, 25°C, 100 ps input ramps and 5 fF load. It measures only
rising `a2[0]` at the read clock. Correct capture plus at most 5% per-bit delay
degradation passes at −250 ps and fails at −265.625 ps. The measured bracket is
15.625 ps wide; the solver maximum step remains 25 ps. This is not a claim of
physical accuracy finer than that numerical step.

The same waveforms independently show retention of the old word when the
address changes 265.625 ps after the read clock; a 250 ps delay does not retain
it. This is a complementary capture/retention observation, **not a separately
simulated hold constraint** or a delay-degradation hold table. Four setup and
four retention measurement faults are rejected. The failed initial retention
method preflight is preserved and superseded by the audited method. Every
waveform and input digest is checked before publication.

Full slew/load/PVT and transition coverage, write/data/mask constraints, pulse
widths, leakage/internal power, coupled RC and independent Liberty validation
still need completion. The long SP corner and mandatory formal campaigns have
separate live status and are not promoted to PASS by these completed sub-items.

The [next corner methods](evidence/sram-corner-step25-methods-20260926.json)
are published separately as a **running-job snapshot**, not a result: SS at
1.08 V/125°C and FF at 1.32 V/−40°C repeat the 78 ns pattern at 25 ps. An observer
waits for successful completion and checks exact model/stimulus identity before
comparing all forty transitions with the completed 50 ps patterns. These runs
retain nominal geometry capacitances and do not supply RC process corners.

## RC reader defect isolated and repaired

The [native ground-capacitance experiment](evidence/magic-groundcap-reader-20260926.json)
closes a specific reader defect: intrinsic node capacitance was omitted from
the distributed RC total. Two isolated tool configurations each pass four
actual-cell comparisons and reject 24 deliberately corrupted controls. The
combined configuration preserves the earlier fractional-sheet and port-alias
repairs. Twenty targeted software tests pass. No installed PDK or active
simulation input was modified.

The comparison proves exact weighted resistor/MOS topology and per-net input
capacitance increments, including repeated native node records. It does not
prove spatial placement: coordinate metadata differences remain explicit.
The [complete historical diagnostic inputs](evidence/rc-stage-inputs-20260926.json)
also preserve the independently measured coupling-loss failure. A new repaired
full-DP extraction is running; this is not final RC acceptance or final STA.

The [SS/FF timestep replays](evidence/sram-dp-corner-timestep-20260926.json)
subsequently completed: both 78 ns patterns pass at 25 ps, with forty observed
read transitions compared per corner against the 50 ps results. Maximum delay
changes are 16.273267 ps for SS and 22.532888 ps for FF. These are completed
capacitance-only numerical checks at one load/slew, not complete characterization.
The separate [full-RC audit methods](evidence/repaired-dp-rc-audit-methods-20260926.json)
were captured while waiting for extraction and contain no acceptance verdict.

The [full-DP source preflight](evidence/repaired-dp-rc-source-preflight-20260926.json)
checks all 350,997 native input records against the accepted repaired
capacitance-only source and rejects a missing coupling. Final RC serialization
and the separate long SP/formal campaigns remain unfinished.

## Destructive SRAM test engine and raw port

The new `hw/soc/rtl/dft/soc_sram_mbist.v` runs a six-element March C-minus
sequence over each raw memory word, repeating it with all-zero and bit-partition
backgrounds. A final all-zero pass both clears and verifies the array. For a word
width W and depth D, the complete schedule contains
`10 * D * (ceil(log2(W)) + 2)` accesses. Read latency is an explicit positive
parameter; no bus backpressure is supported. Non-power-of-two depths and widths
are supported. This is independently written RTL, not a port of a vendor's
software routine. The [Microchip memory-test background](https://onlinedocs.microchip.com/oxy/GUID-1BC922B5-0BDE-4D42-AC92-68359BB22BEC-en-US-1/GUID-81A68B22-3BC9-479D-A63A-DAD6B44A852F.html)
explains the underlying March algorithm; its word-oriented implementation and
coverage claims are not claimed for this different repeated-background schedule.

On the first failed comparison the engine stops and retains address, expected
and observed words, March element and background. Completion, failure and abort
are separate sticky results, cleared by a newly accepted start or reset. A held
start does not repeat a completed destructive test; starts while busy are ignored.
Reset and abort suppress requests, including before the next sampling edge.
RTL X/Z reads fail the simulation comparison; this is not an X detector in silicon.

`soc_sram_test_port.v` arbitrates one synchronous raw memory port. An explicit
`test_mode_i` ownership grant isolates functional traffic while the engine owns
the port, including after completion. Revoking that grant aborts the test before
functional ownership resumes. Test writes enable every physical data bit;
functional write masks are preserved. This wrapper does not switch clocks.
Integrators must first quiesce every other port/master, bypass ECC/scrubbing,
provide a trusted start/status path, and reinitialize encoded memory before boot.
Raw zeros are not automatically a valid codeword for every ECC implementation.

The independent testbench checks the entire operation trace, not just a done bit.
It enumerates stuck-at, transition, address-alias, inversion-coupling and
state-coupling faults in a 4-word by 4-bit model. Its fault models are explicit
executable models, not a percentage of silicon defect coverage. Larger healthy
models check all addresses and word bits, multiple read latencies and non-power-of-two
parameters. Controller mutations test whether comparison, address traversal,
background generation, final clearing and abort failures are actually rejected.
The port bench additionally exercises competing functional writes, masked writes,
reset/ownership revocation and read corruption. A synthesized gate-level replay
uses the same port assertions.

Reproduce the digital tests with:

```sh
python3 -m pytest sw/tests/test_soc_sram_mbist.py -q
python3 scripts/check_sram_mbist_native.py --pdk "$PDK_ROOT/ihp-sg13g2" --output /tmp/mbist-native
```

The second command requires Icarus and actual IHP model files; missing prerequisites
fail, rather than creating a passing skipped campaign. It executes normal,
abort, ownership-revocation, reset and corrupted-read cases on the native
512x16, 1024x32 and 2048x64 single-port functional models. These vendor models
are not transistor models of the replacement SRAM geometry.

P10 remains open at product scope. These modules are not instantiated in
`soc_top`, and no scan chain, ATPG report, test-pad/JTAG access, dual-port collision
coverage, retention/mask-line test, at-speed characterization or assembled-chip
MBIST result is supplied by this addition. Integrating them changes the netlist
and requires a new physical and timing campaign; the existing accepted GDS is
not represented as containing this logic.

## Completed local verification and delivery

The [mandatory formal replay](evidence/formal-170-local-20260926.json) completed
all **170 tasks** at source `1baeb635453dccc8b122c0fc40ff3ee1613159a1`:
54 pilot and 116 SoC tasks. Every saved source copy and task log was checked again
before packaging. Six historical exclusions remain explicit. The working copy
has an upstream dependency symlink and two generated proof directories; these
are recorded, rather than describing it as wholly pristine. Of 190 broad source
pins, only the status-rendering script differs at the later publication source.
This is not a proof of the new MBIST, whole-core RVFI or M-extension obligations.

The [MBIST digital receipt](evidence/sram-mbist-digital-20260926.json) records
36 passing targeted cases, including five synthesized-port replays, plus fifteen
native IHP functional-model port cases. The small 4x4 array campaign executes
1,277 explicit faulty scenarios: 64 stuck/transition cases, twelve address aliases,
240 inversion-coupling cases, 960 state-coupling cases and one unknown-read case.
Six deliberately broken controller variants are detected. The initial abort
fixture and synthesized-module parameter failures are retained with their corrected
replays. Standalone Verilator lint reports no warnings or errors. All these are
digital component checks, with the chip-level limitations stated above.

A fresh local checkout of `299f86ea23cee729cfc3c7a389b292ca079fa883`, with
regenerated pinned Ibex and interface dependencies, completed
[`ci_local.sh all`](evidence/local-ci-mbist-20260926.json): **1,825 pytest passes,
zero failures, zero skips**. All fourteen formerly skipped tests execute.
The separate front-door tally is twenty passing gates, zero failures and six
skips for absent historical physical run directories. Pandoc and builtin document
builds, paper build, licensing, mirror generation and prepared SoC lint execute.
This does not recreate those six historical physical runs.

The earlier run in the long-lived working tree had four pytest failures. Corrections
add the two standalone modules to the unbuilt-in-product ledger, pin ten previously
published evidence files omitted from the digest manifest, restrict the response
register guard to actual project files rather than tool-cache directories, and
make the output-escape test independent of pytest's temporary-directory location.
That first run also reports 644 undispositioned historical/experimental formal
outputs. The passing fresh-checkout gate does not erase or disposition those old
working-tree records; P13's historical evidence reconciliation remains open.

Six lossless archives are available through the
[verified release manifest](evidence/mbist-formal-assets-20260926.json).
They separate passing component/formal/SP receipts, rejected RC extraction,
queued methods and the prior/final CI runs. The release is an engineering
prerelease, not a product release. README selects the new source-bound pytest
and formal receipts; physical acceptance remains bound to the previously measured
32-SRAM core. No manufacturing approval or complete-product closure is recorded.

## Power-on SRAM MBIST integrated into soc_top

`SOC_SRAM_MBIST` now connects the existing March engine to the **actual system
RAM raw row port**, below ECC and ahead of the four 2048x64 macro banks. Its
8192-row, 64-bit address space includes every data/check bit and all bank
boundaries. It uses the functional A ports with full test write masks; vendor
BIST clock/port pins remain parked. No clock mux is added. The named physical
product flow, `implement_interfaces.sh`, enables this integration by default;
legacy direct synthesis remains reproducible with the feature disabled.

The engine starts once after synchronized external power-on reset. CPU, fabric,
peripherals and RAM codec/scrubber remain in system reset until successful
completion. Functional raw requests are additionally isolated at the memory
mux. The raw read bank selector belongs to the POR domain so it can follow
MBIST while the CPU domain is stopped. The watchdog itself stays in POR until
MBIST finishes; a subsequent watchdog reset preserves the result and does not
rerun the destructive test. External reset cancels outstanding requests and
starts a fresh complete test. A comparison failure or abnormal engine abort
keeps the functional domain in reset.

`soc_top` exposes `mbist_busy_o`, `mbist_done_o`, `mbist_failed_o`, the 13-bit
physical row address, 64-bit expected/actual values, three-bit March element and
eight-bit background. Address bits 12:11 identify the macro bank and 10:0 the
row. Results persist until external reset. An abnormal internal termination
sets failure even when there is no comparison address; this is not a silicon
fault diagnosis. These are digital core outputs, **not implemented test pads or
JTAG registers**. Software is not required to start the test and cannot bypass a
failed test.

This profile requires writable 8192-row RAM and the immutable logic ROM;
unsupported memory/ROM builds fail elaboration or flow preflight. The final
MBIST pass clears/checks raw zero. For this repository's specific byte SECDED
code, that is an encoded zero, subsequently verified through real CPU reads.
The immutable boot image is never overwritten. Historical SRAM-ROM builds do
not silently acquire a destructive test.

The chip bench instantiates real `soc_top` and Ibex with IHP native **functional**
SRAM models. A healthy schedule has 655,360 raw accesses, 163,840 per bank, and
completes at cycle 983,048 of the bench. Its assembly ROM reads all 8192 zero
words, then writes/reads every word and exercises byte stores through ECC. It
services the watchdog during this long software test. Other cases exercise POR
interruption/restart, a warm watchdog reset, a raw check-bit fault in each bank,
and illegal controller state. First-failure metadata, memory isolation and
fail-closed reset behavior are checked. Test logs containing a fatal/error are
rejected even when they also contain a pass marker.

Reproduce the chip-level functional campaign after preparing Ibex, interface
bundles and the pinned tools:

```sh
python3 scripts/check_soc_mbist_integration.py --simulator verilator \
  --profile base --pdk "$PDK_ROOT/ihp-sg13g2" \
  --output hw/soc/out/mbist-chip-base
python3 scripts/check_soc_mbist_integration.py --simulator verilator \
  --profile full --pdk "$PDK_ROOT/ihp-sg13g2" \
  --output hw/soc/out/mbist-chip-full
```

The full profile additionally requires the repository's explicit LGPL interface
selection. Verilator results are two-state functional evidence, not X-propagation,
at-speed, retention, DRC/LVS or STA evidence. The runner also supports Icarus
13 or newer. The separate accepted four-state campaign below stops after the
complete raw test and reset release; it is not a full firmware replay in Icarus.
The physical launcher rejects a supplied pre-MBIST netlist when the MBIST
profile is enabled. It records the profile in implementation inputs and forwards
the same define and sources through synthesis and P&R.

This closes the previous **uninstantiated system-RAM MBIST** limitation. It does
not test Ethernet dual-port FIFO SRAM, add scan/ATPG/debug access, or qualify
replacement SRAM silicon. Existing routed GDS, LVS and timing reports predate
this netlist change and remain evidence only for their original source.


The [chip integration receipt](evidence/sram-mbist-chip-integration-20260926.json)
records **14 passing cases** across the base/full interface profiles, a separate
complete healthy four-state native-model raw MBIST/reset-release run, and four
rejected integration mutations. The latter deliberately bypass reset isolation,
reset the read-bank selector in the wrong domain, hide comparison failure or
hide abnormal abort. These are executable digital fault controls, not a silicon
coverage percentage. The six lint profiles retain identical diagnostic identities
and multiplicities, with updated source lines and no new warning waiver.
SG13G2 synthesis retains four system-RAM and sixteen Ethernet macros; the latter
remain outside MBIST. The 59,094-cell mapped design is a new netlist, not a routed
or timing-qualified layout.

A mapped native-cell Verilator compatibility check failed before whole-chip
simulation (native flip-flop reset/capture); its failure is retained and no
mapped-chip simulation pass is claimed. Earlier testbench time-bound/watchdog
and verdict-parser failures are also preserved separately from accepted runs.
The final parser rejects fatal diagnostics even following a pass banner.

At source `fad89ce`, the [fresh local CI receipt](evidence/local-ci-mbist-chip-20260926.json)
contains **1,836 pytest passes, zero failures and zero pytest skips**. All 14
previously skipped tests executed. The front-door CI reports 20 passes and six
explicit unavailable historical physical-tree skips, which are not new physical
passes. Both documentation renderers and the prepared whole-SoC lint passed.
The [release manifest](evidence/mbist-chip-assets-20260926.json) binds the two
raw-evidence archives, including source snapshots, logs, preliminary failures
and licence notices. No earlier GDS/LVS/STA receipt is promoted to this source.

## Ethernet FIFO MBIST and refreshed physical integration

The `SOC_SRAM_MBIST=1 SOC_ETH_SRAM=1` synthesis profile now selects
`SOC_ETH_MBIST` as well. Both 2048-word Ethernet FIFOs instantiate eight
256x16 dual-port SRAMs directly. A guarded transformation of the pinned upstream
FIFO replaces its memory and first read pipeline stage without adding a cycle.
The upstream checkout remains unchanged, and both interface manifests hash the
transformation. Unsupported depth/width/non-frame configurations fail elaboration.
Legacy profiles retain inferred memory and their original interface.

Each FIFO uses its existing write and read clocks, with no clock switching:

1. Port A runs the six-background March campaign over all 2048 x 16 bits.
2. Port B reads every zero left by A before it may overwrite anything.
3. Port B runs the same complete March campaign.
4. Port A reads every zero left by B before releasing the memory.

That is 122,880 March accesses per port plus 2,048 cross-port reads per direction,
**249,856 test accesses per FIFO**. All physical bits, including the six unused
payload bits, are exercised. The test has no claimed exhaustive silicon defect
coverage percentage; retention, at-speed timing, arbitrary simultaneous dual
writes and analog read/write collision qualification are separate matters.

POR asserts asynchronously and releases through a two-flop chain in each clock
domain. Sticky handshakes cross two-flop synchronizers. Functional FIFO requests
remain isolated until both ports pass. Comparison failure or controller abort
holds the chip in reset; the top-level `mbist_done_o`/`mbist_failed_o` aggregate
system RAM and both FIFOs. `eth_mbist_done_o[1:0]` and
`eth_mbist_failed_o[1:0]` identify TX (bit 0) and RX (bit 1). Existing detailed
fault address/data outputs still describe **system RAM only**. These are core
signals, not implemented test pads or JTAG access.

Both external GMII clocks must be supplied during power-on testing. A missing
clock prevents boot rather than silently bypassing a memory. The board/PHY must
provide these clocks before firmware starts; software MDIO initialization cannot
be a prerequisite for the clocks needed by MBIST. A watchdog reset or Ethernet
flush resets functional logic without destroying live SRAM by rerunning MBIST.
External POR reruns the complete test.

The replacement SRAM technology map now supports reads and byte-uniform writes
on both DP ports, including output hold when read enable is low. Vendor BIST
pins remain disabled: tests access the real A/B functional ports. Macro geometry
and independent CDL are reused only with exact hashes; new control logic needs
fresh routing and transistor LVS. Old GDS acceptance is not transferred.

Reproduce functional verification with the pinned tools and prepared interfaces:

```sh
python3 scripts/check_eth_mbist.py --pdk "$PDK_ROOT/ihp-sg13g2" \
  --output hw/soc/out/eth-mbist-native
python3 scripts/check_soc_mbist_integration.py --eth-mbist \
  --simulator verilator --profile full --pdk "$PDK_ROOT/ihp-sg13g2" \
  --output hw/soc/out/eth-mbist-chip
SOC_ETH_MBIST=1 GL_IVERILOG=/path/to/icarus-13-or-newer/bin/iverilog \
  bash hw/soc/flow/test_eth_sram.sh hw/soc/out/eth-mbist-mapped-mac
```

`check_eth_mbist.py --replacement-model PATH` additionally tests the real
replacement adapter against the explicitly supplied independent digital SRAM
contract model. This is functional evidence, not transistor characterization.
Native mapped-cell simulation also requires a compatible Cocotb/Python runtime;
the tool wrapper must not overwrite it with an incompatible bundled Python.

**Verification checkpoint:** new full-interface placement/routing, mapped MAC
simulation and final source-bound regression are in progress locally. New layout
DRC/LVS is not yet accepted; SRAM Liberty/RC, final STA and manufacturing approval
remain separate open gates. Results and exact artifact hashes will replace this
checkpoint when the runs complete.
