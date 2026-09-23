# 100 — Routed timing and full-transistor verification

Latest measurement: the [actual-segment replay](evidence/global-route-segment-replay-20260923.json)
avoids the defective estimated-SPEF exporter and reproduces in-memory timing.
Its three-corner global-route estimates have no slew, capacitance or negative
hold violations, but slow setup remains **-3.657322 ns**. Detailed-route RCX
verification is pending. The original routed baseline now passes the locked
upstream main DRC rules: 549 report categories, zero markers, successful tool
exit and unchanged inputs. This result does not transfer to the new layouts.
Full transistor LVS still fails; overall physical/manufacturing closure is open.

## Baseline measured on 23 September 2026

[Hosted run 35743942451](https://github.com/Melihakbulut221/nssoc/actions/runs/35743942451)
completed detailed routing but **failed** its final timing and electrical
checks. It does not certify the current SoC for production. The complete
548,770,688-byte artifact was downloaded and SHA-256 verified; the
[baseline receipt](evidence/routed-closure-baseline-20260923.json) binds the
actual ODB, DEF, powered/unpowered netlists, SDC, nominal SPEF and GDS.

| Liberty corner, nominal extracted RC | Worst setup (ns) | Worst hold (ns) | Slew violations | Capacitance violations |
|---|---:|---:|---:|---:|
| Fast | +3.194093 | +0.042922 | 9 | 7 |
| Typical | +1.779902 | +0.184535 | 11 | 6 |
| Slow | **−7.173567** | +0.291907 | **313** | **6** |

The final router reports zero DRC errors and zero antenna nets/pins. Those
checks do not replace foundry DRC or extracted LVS. The original hosted
configuration disabled those separate foundry checks.

An independent single-corner OpenSTA 2.7.0 replay reproduces the slow setup
and hold values exactly. This failure is therefore not explained away by
the earlier multi-corner/generated-clock diagnostic problem. The constraints
remain 20 ns for the core, 8 ns for Ethernet, with early/late derates of
0.95/1.05. No clock relaxation or new timing exception is used for closure.

## Physical repair and functional safeguards

The initial critical paths run from the Ibex register-file address registers
through decode, register-file selection and ALU/bus logic. Long buffer chains
and heavily loaded combinational drivers contribute to the delay. SRAM outputs
also exceed their characterized capacitance limits.

An iterative sizing experiment reduces the slow estimate to −4.929801 ns
while using the original wire parasitics. **That is not a post-route result.**
Its local logic/state equations pass the source-bound
[ECO checker](../hw/soc/flow/check_eco_logic.py). The checker contracts only
library-proven positive, stateless buffers; it compares retained state and
macro input equations and exhaustively checks proposed Boolean pin permutations.
It rejects altered state, inverted buffers, asymmetric pin swaps, cycles,
multiple drivers and undriven inputs. Unchanged opaque library cells require
the same master and identical input equations. This does not prove SRAM
interiors, timing, analog behavior, initialization or extracted connectivity.

The next optimization rebuilds global routes after removing the old signal
wires and legalizing resized cells. Reusing the detailed wires caused a
failed routing-tree repair attempt; that attempt is retained as a failure.
An earlier extracted-parasitic repair also terminated in an OpenROAD journal
assertion. Neither failed attempt contributes an accepted output.

All global-route repair candidates require subsequent functional checking,
legalization, detailed routing, new parasitic extraction and independent
three-corner STA. An optimizer progress line cannot close the timing gate.

## Full-transistor LVS schematic

[transistor_schematic.py](../hw/soc/flow/transistor_schematic.py) constructs
the schematic side from the actual powered implementation Verilog and the
original vendor standard-cell and SRAM CDL. Yosys only elaborates connectivity.
Its temporary interfaces are replaced by the complete original transistor
subcircuits in the emitted schematic; SRAM macros are not empty blackboxes.

The measured baseline contains 387,315 implementation instances and 332 unique
CDL definitions. Exact repeated definitions are deduplicated; conflicting
device bodies, omitted source directives, missing input/power pins and bus
width mismatches fail. CDL bus ordering and escaped SRAM supply names are
preserved. The 585 deliberately disconnected scalar outputs are checked against
vendor Verilog output declarations and receive distinct floating nets; missing
inputs are never treated this way. The reusable tool reproduces the prototype
schematic exactly apart from its comment header.

The source receipts and concise raw logs are retained in the
[measurement archive](evidence/routed-closure-baseline-20260923.tar.gz).
Constructing this schematic is **not an LVS pass**. The complete GDS is being
compared against it using the locked, unmodified IHP KLayout LVS deck. The
comparison database, explicit final verdict and input identities must all be
checked before accepting a result. Existing SRAM model/extraction failures
documented in [docs/93](93-ihp-drc-update.md) are not waived.

## Foundry checks and remaining acceptance

At this dated snapshot, full-chip foundry DRC and transistor LVS are running
and have no accepted final verdict. DRC uses the unmodified upstream main
rules at commit `5e6d592e4002946a4616f798c357f0f3c06cf3b6`, deep mode, without
cell or region exclusions. Optional recommended rules are off, matching the
previous controlled deck comparison; this scope is explicit and is not an
unqualified fabrication release. Final repaired geometry needs its own checks.

The new schematic and equation-checker controls, together with the existing
physical-ECO regression, pass 95 tests. The current routed baseline still fails
setup/electrical acceptance. Full manufacturing verification, pad/package
integration and PCIe PHY integration remain separate open product gates in
[docs/92](92-product-acceptance.md).


## Optional core pipeline candidate, 2026-09-23

Sizing and load buffering leave paths from protected register data through
syndrome correction, ALU/address generation and fabric selection, or back into
protected write data. The candidate introduces two independent parameters,
`CORE_REQ_REG` and `CORE_WB_STAGE`, both defaulting to zero. The latter selects
Ibex's existing writeback stage. The former inserts
[`soc_req_pipe`](../hw/soc/rtl/soc_req_pipe.v) between the core's data-request
port and the fabric, before arbitration. `SOC_CORE_REQ_REG` and
`SOC_CORE_WB_STAGE` select them explicitly in the simulation and synthesis
scripts; historical/default builds keep their previous behavior.

The request register transfers a 69-bit address/write/byte-enable/data token
on upstream grant. It holds that token until downstream grant, permits one
pending token and has no combinational downstream-grant path or fallthrough.
It adds one request stage and a bubble between accepted tokens. Ordered
responses retain the existing return path. Both endpoints use the common
system reset; reset discards a pending token. Only valid state needs reset:
payload is meaningful when the downstream request is asserted. The register
uses the ungated core clock, and its valid request wakes the existing bus gate.

The [source-bound block receipt](evidence/core-request-pipeline-20260923.json)
and [raw proof/control archive](evidence/core-request-pipeline-20260923.tar.gz)
retain the successful runs and deliberately failing mutations.

The real RTL passed a 1,200-cycle scoreboard with 209 accepted requests,
207 delivered requests, two reset-discarded requests and 714 stalled cycles.
The three new formal tasks passed bounded checking to 24 steps, induction
with depth 12, and four reachability covers. Inputs are unconstrained after
the initial reset, including payload changes during stalls and grants while
empty. Checks cover token order/content, occupancy, stable blocked output,
reset clamping and absence of overwrite/bypass. Four deliberate RTL mutations
(payload corruption, early release, overwrite and bypass) fail both the
scoreboard and bounded formal assertions. These are block-level results,
not a whole-processor equivalence proof.

A source-list guard initially found two fault-injection entrypoints missing
the new module. Both lists were corrected; the guard and five RTL cases then
passed. The first wider guard run remains recorded as 99 passed / one failed,
not rewritten as a clean run. The formal inventory now has 122 SoC tasks in
29 jobs, with the same six historical exclusions.

The full-interface, native-SRAM synthesis with both parameters enabled has
70,376 mapped cells and 9,601 flip-flops. This is a candidate only. Its matched
whole-CPU simulations and placement measurement are still pending at this
snapshot. No timing result is inferred from cell count or combinational depth.
Pre-placement STA also cannot qualify this candidate: unbuffered clocks and
high-fanout nets drive the cell models outside useful ranges. The original
20 ns / 8 ns clocks, corner set and 5% timing derates remain the physical
acceptance constraints. The delivered implementation entrypoint does not yet
select this candidate by default.

## Completed transistor LVS and processor controls

The later [full-chip LVS result](evidence/full-chip-transistor-lvs-20260923.json)
is **FAIL**. The deck finished, wrote the complete 1.39 GB comparison database,
and the independent auditor checked that finished file. All input hashes
remained unchanged. The tool process returned zero, but the deck explicitly
reported a mismatch; process completion is not a successful LVS verdict.
The [compact raw archive](evidence/full-chip-transistor-lvs-20260923.tar.gz)
contains the deck log, audited circuit inventory, exact input receipt and
extracted/reference bodies of the three failing SRAM child circuits.

Of 90 circuit pairs, 79 match, five are schematic-only mismatches, three do not
match and three are skipped. The nonmatching children are
`RSC_IHPSG13_CDLYX1_DUMMY`, `RSC_IHPSG13_DFPQD_MSAFFX2P` and
`RSC_IHPSG13_WLDRVX8`. Their failures prevent comparison of both SRAM macro
types and `soc_top`. Thus the result does not establish top-level connectivity.
The dummy cell has the vendor `lvsres` versus extracted `res_metal1` model
difference. The sense amplifier exposes separate `VDD!` and `VDD!$1` networks;
the word-line driver has two extracted PMOS devices in this hierarchy versus
four reference devices. These reproduce the context-sensitive macro/extraction
problems measured in [docs/93](93-ihp-drc-update.md). No resistor alias, implicit
power connection, blackbox, geometry exclusion or modified comparison rule is
accepted as a fix. Full DRC is still pending in this snapshot.

The [whole-processor controls](evidence/core-pipeline-controls-20260923.json)
and their [raw logs](evidence/core-pipeline-controls-20260923.tar.gz) also
supersede the earlier pending candidate status.
With `CORE_REQ_REG=0, CORE_WB_STAGE=0`, both Icarus 14 development and Icarus 12
pass the complete 28-check firmware in 647,591 cycles. The isolated request
register (`1,0`) passes the same firmware in 700,166 cycles, handing over from
the loader at cycle 358,606. All three successful runs decode 1,094 UART
characters with zero framing errors, observe watchdog counts 1/0/0, and check
six QSPI frames with zero datasheet violations.

The combined (`1,1`) candidate fails boot acceptance in both simulators. The
isolated writeback (`0,1`) candidate also remains in the loader's trap loop
without handing over through 600,000 cycles. Those failing diagnostic runs
were intentionally stopped; they are not completed timeout benchmarks. The
request register's block proof and successful `1,0` firmware run do not qualify
Ibex's writeback option. The `1,1` placement experiment was cancelled before
detailed placement/clock-tree acceptance. Existing zero defaults remain in
effect. Timing-driven placement is now being measured on the successful
`0,0` control using the same clock periods, corners and derates.

## Store/branch correction and complete candidate firmware

The [later correction](evidence/core-writeback-branch-fix-20260923.json)
identifies the writeback failure rather than bypassing the firmware check.
In the pinned CPU, a taken branch behind a store awaiting its response can
use the comparison result as its target when writeback is enabled without
the dedicated branch-target ALU. A short independent program reproduces the
exact wrong target `254 - 2008 = 0xfffff926`, also seen in the loader failure.
The default two-stage CPU passes that program; the unsupported writeback-only
combination fails; writeback with the dedicated branch-target ALU passes.

`soc_top` now selects both CPU options with `CORE_WB_STAGE`. Its zero default
still selects the historical configuration. No vendor sources are changed.
The [regression](../hw/soc/tb/tb_ibex_branch_stall.v) exercises response delays
of 1, 2, 3, 5 and 8 cycles with writeback off and on, checks one accepted store
and the subsequent delayed readback, and detects the two shared-ALU negative
controls. Thirteen hazard/configuration tests pass; together with the request
register tests, 18 pass on both Icarus 12 and the project Icarus 14 development
build. The implementation/configuration suite adds coverage for forwarding and
recording both core parameters: 42 focused tests pass. The initial pytest
collection error and all earlier failing processor runs remain recorded.

With request register, writeback and branch-target ALU enabled together, the
complete protected SoC passes all 28 firmware checks in **630,363 cycles**.
It hands over to RAM at cycle 307,606, decodes 1,094 UART characters without
framing errors, observes watchdog counts 1/0/0 and six QSPI frames without
datasheet violations. Full-interface synthesis has 69,944 cells, 9,600
flip-flops and 20 SRAM instances. Reported standard-cell area is
1,079,471.232 square micrometres; it excludes the SRAM footprints. The 191
unique synthesis warnings / 199 occurrences remain disclosed.

The [raw archive](evidence/core-writeback-branch-fix-20260923.tar.gz) retains
the source identities, firmware logs, negative controls and synthesis report.
These results do not establish whole-ISA equivalence, native-gate behavior or
physical timing. The physical workflow has an explicit `core_pipeline` input,
default false, and runs the hazard tests and complete CPU firmware before
implementing the enabled candidate. The implementation receipt now records
both pipeline parameters and the corresponding branch-target ALU selection.

## Incremental electrical repair and cross-corner rejection

The [incremental-repair measurement](evidence/incremental-electrical-20260923.json)
starts from the original CPU configuration and applies three bounded
incremental routing/repair passes with 20% electrical repair margins.
It reaches zero slow-corner slew and capacitance violations in the running
OpenROAD session, while setup remains negative. The resulting netlist passes
the restricted sizing/buffering equation check against the original routed
implementation. Repeated runs produce the identical netlist.

Exporting the estimated global-route parasitics and loading them into separate
STA processes reveals remaining violations:

| Liberty corner | Setup WNS (ns) | Hold WNS (ns) | Slew violations | Capacitance violations |
| --- | ---: | ---: | ---: | ---: |
| Fast | +3.667775 | -0.293292 | 11 | 0 |
| Typical | +2.551240 | -0.040082 | 3 | 0 |
| Slow | -2.898450 | +0.423281 | 0 | 0 |

This candidate is **not accepted**. Besides these violations, the fresh slow
SPEF import does not numerically reproduce the in-memory setup result of
-3.657322 ns. The subsequent integrity audit below identifies omitted pin-node
wire capacitance and rejects the imported result. Neither value is final
extracted timing. An earlier export incorrectly called the RCX exporter,
which reported no extraction data and produced no SPEF; its STA attempts are
explicitly invalid. The corrected export uses the tool's documented global
routing estimator and verifies that the file exists. All reports and the
failed export control are in the [measurement archive](evidence/incremental-electrical-20260923.tar.gz).

The separate timing-driven placement attempt on the original CPU was stopped
during its first resizer iteration after growing to approximately 11 GB of
virtual memory alongside the full DRC process. It produced no accepted
detailed-placement result. The duplicate deep-mode DRC attempt was also
stopped for memory; the complete unchanged-deck tiling-mode check continues.
No interrupted check is counted as a pass, and the completed full LVS failure
above remains an open manufacturing gate.

## Electrical and hold ECOs: exported timing rejected after integrity audit

The [next measured ECOs](evidence/incremental-multicorner-20260923.json)
insert eleven local buffers at the fast-corner SRAM slew endpoints, followed
by eleven delay cells at the remaining negative hold endpoints. Each change
is legalized and incrementally routed. Independent imports of the resulting
ECO19 global-route SPEF originally gave the following numbers. **The subsequent
capacitance-conservation audit below rejects this SPEF; these biased results
are retained for diagnosis and do not close any three-corner timing or
electrical gate.**

| Liberty corner | Setup WNS (ns) | Hold WNS (ns) | Slew violations | Capacitance violations |
| --- | ---: | ---: | ---: | ---: |
| Fast | +3.667775 | +0.000411 | 0 | 0 |
| Typical | +2.596816 | +0.152010 | 0 | 0 |
| Slow | -2.898450 | +0.423281 | 0 | 0 |

The original apparent removal of electrical and negative-hold violations is
withdrawn as a closure result. Slow setup fails even with the underestimated
capacitance; this is not an accepted final layout.
Detailed routing, antenna/connectivity checks, RC extraction and three-corner
STA have been started from this exact ECO19 database. Their results are
pending and cannot be inferred from the table.

Both ECO18 and ECO19 pass the restricted netlist equation check against the
original routed design: 72,992 retained cells, 266 equivalent size changes and
102 Boolean input permutations. ECO19 adds 513 positive buffers/delay cells
relative to that original netlist. This proof excludes timing, analog behavior,
SRAM internals, initialization, CDC and extracted physical connectivity.
All 1,048 unannotated drivers in each imported SPEF measurement are checked
against the source-bound netlist and library interfaces: 585 are disconnected
declared outputs, and 463 have no logical sinks. There is no loaded missing
driver in that list; this does not establish RC accuracy.

An additional control imports the same ECO18 SPEF into both OpenROAD and
standalone OpenSTA. They reproduce exactly the same slow setup and hold
numbers. This localized the difference to the exported/imported parasitics,
rather than those two STA front ends. The integrity audit below subsequently
identified omitted capacitance. Both results still fail setup. The
[raw archive](evidence/incremental-multicorner-20260923.tar.gz) retains the
scripts, reports, bounded logic proofs and annotation audits.

The separate [pipelined-core physical run](https://github.com/Melihakbulut221/nssoc/actions/runs/35803297886)
at `e5f610cec8ffab23500303190fa09fdf48300675` passed its hosted hazard/full-CPU
firmware gate and entered implementation. No physical result is available yet.
The [native-cell qualification run](https://github.com/Melihakbulut221/nssoc/actions/runs/35804632644)
at `95cbb15c0b41e26f2a2bd9086f5b8a6cb8b4e4e6` separately tests the enabled
core pipeline with untouched IHP cell/SRAM models in both interface profiles.
It is pending, without SDF, and cannot replace extracted timing. The native
workflow now has a default-off `core_pipeline` input, validates and records
the requested core parameters before acquiring tools, and retains the RTL
parameter overrides. Seven native-preparation controls pass, including
invalid-selector rejection and recording the baseline/enabled configurations.

### Estimated SPEF integrity failure

The pinned estimator [adds half of each pin stub's wire capacitance to the
pin node](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/est/src/MakeWireParasitics.cpp#L336).
Its [SPEF writer skips ground-capacitance entries for pin nodes](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/dbSta/src/SpefWriter.cc#L200),
despite including them in each `D_NET` total. This is wire capacitance;
the `PIN_CAP NONE` convention for Liberty pin capacitance does not restore it.

The [independent integrity audit](evidence/estimated-spef-integrity-20260923.json)
finds a deficit in every one of ECO19's 96,100 exported nets, totaling about
94.228 pF. For example, `_013646_` declares 0.0162618 pF but serializes
0.015831794 pF. The 0.000430006 pF deficit accounts for the observed load
capacitance difference on that path. ECO17 and ECO18 fail the same check.
The previous imported timing tables remain recorded, explicitly invalid as
closure evidence; the restricted Boolean proofs and unloaded-driver audits
have separate scopes and still stand.

The new [grounded estimated-SPEF guard](../hw/soc/flow/audit_estimated_spef.py)
requires per-net capacitance conservation with rounding tolerance and rejects
truncated, coupled or unsupported input. Twelve controls include this actual
omission pattern, restoration of the missing entry, units, zero-capacitance
nets and malformed inputs. It does not certify RC accuracy or extracted
timing. No guessed capacitances are inserted into the measured files.
The running detailed-route/RCX flow uses the actual ODB geometry, rather than
this rejected global-route SPEF, and remains the next verification boundary.

### Independent replay from actual routing segments

The [replacement measurement](evidence/global-route-segment-replay-20260923.json)
does not export estimated SPEF. It records the actual global-route segment
graph, loads that graph with `read_global_route_segments` in a fresh OpenROAD
process, and estimates/reports timing in memory at all three Liberty corners.
The ODB, DEF, netlist, SDC and routing guides are all byte-identical to ECO19.
The fresh slow result reproduces the original in-memory setup and hold values
within 0.000001 ns, resolving the previous measurement discrepancy without
inventing replacement capacitances.

| Liberty corner, nominal estimated RC | Setup WNS (ns) | Hold WNS (ns) | Slew violations | Capacitance violations |
| --- | ---: | ---: | ---: | ---: |
| Fast | +3.643677 | +0.011810 | 0 | 0 |
| Typical | +2.579708 | +0.159314 | 0 | 0 |
| Slow | **-3.657322** | +0.435448 | 0 | 0 |

These measurements establish the electrical/negative-hold result only for
this estimated routing graph. Slow setup still fails and the minimum hold
margin is only 11.8 ps. The exact same geometry is undergoing detailed routing
and extracted-RC checks; it is not a final accepted layout. The unchanged
netlist reuses the verified ECO19 Boolean proof, and the unannotated-driver
report is byte-identical to its checked list of 1,048 unloaded outputs.

The [replay archive](evidence/global-route-segment-replay-20260923.tar.gz)
contains the actual segment graph, producer/replay scripts, all corner reports,
source identities and the rejected guide-only diagnostic. Merely reading
guide rectangles emits `GRT-0008` and does not restore the full routing graph;
that diagnostic is explicitly invalid. The rejected SPEF-based tables above
remain rejected rather than being retroactively accepted by this new result.

## Physical power-open controls for hierarchical LVS

A [two-inverter physical control](evidence/must-connect-lvs-controls-20260923.json)
tests hierarchical power connections without altering any production layout or
pinned rule deck. Two original IHP inverter cells have separate VDD islands;
the parent either contains their Metal1 bridge or omits exactly that bridge.
An independent geometry comparison confirms that this is the only layout
difference. A separately copied diagnostic deck requests a cell-scoped
implicit connection and explicitly selects strict or permissive top-level
handling.

The joined, strict case passes. The cut, strict case fails extraction with a
must-connect error. Deleting the reference NMOS also fails comparison. The
cut, permissive case exposes a dangerous distinction: all circuit pairs match
and the deck prints success, while the database still records an unresolved
physical connection warning. The previous comparison-only auditor accepted
that case; this behavior is reproduced from the recorded earlier revision.

The auditor now reads database extraction diagnostics as well as circuit
pairs and the final text verdict. It rejects warnings, errors, unknown
severities and outstanding must-connect requirements; ordinary informational
entries remain visible. The same valid joined report still passes, while the
hidden open is now rejected. Twenty-four unit controls and the real report
replays validate this change. The [raw archive](evidence/must-connect-lvs-controls-20260923.tar.gz)
contains both GDS variants, reference/negative CDL, reports, exact experimental
deck, source identities and the legacy/fixed audit outcomes.

[KLayout's documented strict top-level mode](https://www.klayout.de/doc/manual/lvs_connect.html)
provides a way to require the physical parent connection rather than assume
it. These controls validate that mechanism and the auditor, **not the actual
SRAM macros or the SoC**. Their existing LVS failures remain open; no blanket
power merge, resistor alias, geometry exclusion or SRAM blackbox is accepted.

## Native mapped qualification of the timing candidate

The [completed candidate run](https://github.com/Melihakbulut221/nssoc/actions/runs/35804632644)
at `95cbb15c0b41e26f2a2bd9086f5b8a6cb8b4e4e6` passes **both base and full
interface profiles** with request registration, writeback and branch-target
ALU enabled. Each native IHP gate simulation completes 28 firmware checks in
630,363 cycles, with zero failure mask, watchdog counts 1/0/0, no flash timing
violations and no UART framing errors. The native SCRUBCTL positive and
negative controls also pass. The earlier pending native-candidate status above
is superseded by this result.

The [source-bound receipt](evidence/core-pipeline-native-boot-20260923.json)
checks both downloaded artifact digests and all 16 recorded gate inputs per
profile against retained files, the exact run commit and the locked original
PDK models. Synthesis logs independently confirm the enabled parameters.
The tested workflow omitted the RTL parameter file because its artifact path
had the wrong filename; the receipt records that omission. Commit `73a6759`
fixes subsequent retention. The [raw archive](evidence/core-pipeline-native-boot-20260923.tar.gz)
includes both profiles' netlists, firmware, ROMs, logs, model locks and results.
This is four-state functional gate simulation without SDF or memory preload;
physical timing, DRC, LVS and silicon qualification remain separate.

## Reachable source-side transistor hierarchy

The schematic builder now emits only vendor definitions reachable from the
actual implementation cell types. Every retained subcircuit body and the
powered top connectivity remain verbatim. Unresolved, recursive and
parameterized subcircuit calls fail explicitly. This removes uninstantiated
library alternatives from the comparison input without discarding any used
device or rewriting its connectivity. The original baseline source schematic
reduces from 333 definitions to 150 with identical retained bodies and top.
Twenty-nine schematic-builder controls and 24 LVS-auditor controls pass.
This input normalization is not an extracted LVS pass; context-dependent
SRAM hierarchy and model differences still require separate resolution.

## Completed main-rule DRC of the routed baseline

The [source-bound DRC receipt](evidence/routed-baseline-main-drc-20260923.json)
records **PASS, zero markers across 549 report categories** for the complete
original `soc_top` GDS, SHA-256
`c8dc9462313e5f3484111a8ed23d683fedb18b2e1b7e65bec636efc8309ec838`.
KLayout 0.30.7 completes the unchanged upstream `5e6d592` main deck in its
official tiling mode, using four threads, 500 micrometre tiles and 30 micrometre
borders. Rule execution takes 10,650.74 seconds. Tool exit zero and every
recorded input digest are verified separately from the zero-marker report.

A real physical negative control uses the same tool/deck and adds one
0.02 micrometre-wide Metal1 rectangle beside an original vendor inverter.
It reports exactly one `M1.a` violation. Although KLayout exits zero, the
report-aware gate correctly fails this case. The [raw archive](evidence/routed-baseline-main-drc-20260923.tar.gz)
retains both complete reports, logs, commands, locks and the negative geometry.

No cell, region or main rule is excluded. Optional recommended rules remain
off. This result covers the exact original routed core, rather than all
supplementary rules, pads/package or silicon acceptance. The ECO19 and new
pipelined-core layouts need their own checks after routing. Baseline timing
and full transistor LVS remain unsuccessful.

## SRAM resistor-width mismatch and rejected reader generalization

The [SRAM diagnosis](evidence/sram-width-diagnosis-20260923.json) retains a
small original bit-cell GDS tree and its verbatim vendor CDL. The six physical
Metal2/Metal3 resistor markers are each 0.20 by 0.60 micrometres, while all six
CDL resistor statements specify width 0.26 and length 0.60 micrometres.
The drawing-metal intersections fully cover the markers, so the difference
is already present in the source geometry and reference, independent of the
experimental reader. The generic layout bit-cell name and size-qualified
schematic bit-cell name are both preserved in the witness.

An isolated original Metal1 dummy cell does match when a copied reader
implements the [documented Metal1 `lvsres` width/length comparison](https://ihp-open-pdk-docs.readthedocs.io/en/latest/verification/lvs/04_05_res.html).
Doubling reference width, doubling length or deleting the resistor each
fails. This bounded result **does not justify applying a Metal1 alias to the
whole SRAM**. Inspection of its context-flattened graph finds 8,336 Metal2
and 8,384 Metal3 resistor definitions, plus the shared Metal1 dummy definition;
physical widths include 0.20 and 0.24 micrometres. The global Metal1 experiment
is explicitly rejected. Width comparison is not disabled and the vendor
reference is not rewritten from the extracted result.

Separate strict power-connection and hierarchy experiments resolve some
child-comparison obstacles while preserving devices, but never establish a
passing macro. The unseeded full graph comparison reaches its 600-second
bound; seeded KLayout and supplemental Netgen comparisons are stopped after
the invalid model generalization is identified. None is accepted as a pass.
The [diagnostic archive](evidence/sram-width-diagnosis-20260923.tar.gz) includes
the width witness, positive/negative controls, copied deck changes, input
hashes, graph dumps and the last completed failing macro database. Original
PDK files and production checks remain unchanged. A consistent, independently
justified SRAM reference and extraction treatment are still required for LVS.

## Separate supplemental DRC runs

The checked-in `hw/soc/flow/check_ihp_drc.py` runner also selects the locked
upstream antenna and density decks. Each invocation requires a fresh output
directory and records the exact deck, execution mode, input hashes and report.
Density enables the upstream boundary sanity checks and disables precheck mode;
its upstream implementation requires deep mode. Recommended rules can be
enabled for a separate main-deck measurement. Unsupported combinations and
decks absent from the immutable lock fail before execution.

```sh
python hw/soc/flow/check_ihp_drc.py routed.gds --top soc_top \
  --tag routed-main-recommended --mode tiling --recommended
python hw/soc/flow/check_ihp_drc.py routed.gds --top soc_top \
  --tag routed-antenna --deck antenna
python hw/soc/flow/check_ihp_drc.py routed.gds --top soc_top \
  --tag routed-density --deck density
```

Run these commands in the pinned physical environment. They do not turn the
completed main-rule result into supplemental acceptance. A separate complete
baseline density measurement is in progress as of 23 September, 06:02 TRT;
it has no final verdict yet. Its input is the same original baseline GDS
identified above. Cell filler insertion does not itself prove that metal
density rules pass.

The [small physical controls](evidence/supplemental-drc-controls-20260923.json)
exercise the added switches with the actual locked deck and KLayout 0.30.7.
With recommended checks enabled, the original inverter passes all 560 report
categories; its narrow-Metal1 negative reports one `M1.a` marker and fails.
A 100 by 100 micrometre boundary around the inverter fails nine global density
checks before fill. Filling that same region passes both the density deck and
the recommended main deck. A separate geometry audit retains every original
shape and original instance while permitting 13 new fill-cell definitions;
deleting original Metal1 geometry is correctly rejected. The
[raw archive](evidence/supplemental-drc-controls-20260923.tar.gz) retains the
positive and negative layouts, reports, copied macros and commands.

The original vendor fill macros select `EdgeSeal.holes`; the baseline core
contains no EdgeSeal drawing or prBoundary shapes. An unmodified invocation
therefore has an empty fill region and is not accepted as successful fill.
For the separate core experiment, copies of the macros select an explicit
prBoundary derived from the actual DEF DIEAREA, with their spacing and shape
rules unchanged. This adds a boundary marker, not a fabricated seal ring.
Full-core filling remains under investigation. The small controls do not qualify
the full layout or its timing; the effects of floating fill on parasitics
must also be addressed before accepting timing for a filled layout.

This distinction follows the [OpenRCX input model](https://openroad.readthedocs.io/en/latest/main/src/rcx/README.html):
extraction uses the routed LEF/DEF database. The GDS-only fill experiment does
not update that database, so reusing its previous SPEF would omit the added
geometry. Inspection of the pinned
[OpenROAD context construction](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/rcx/src/extFlow.cpp#L991)
also shows explicit net-shape traversal; the 50 pinned RCX source files examined
contain no `dbFill` or `getFills` reference. This source inspection is not a
numerical fill-capacitance validation. A justified extraction treatment for
floating fill remains required.

The first flat full-core fill attempt stops with `std::bad_alloc` after
909.69 seconds under its 12 GiB address-space limit, without an accepted output.
The [memory-scaling controls](evidence/core-fill-memory-controls-20260923.json)
retain that failure and two alternatives. Hierarchical Boolean operations,
flattened only at the final fill calls, reproduce the small flat control's
complete per-cell geometry and instance graph with no additions or removals.
A second method processes bounded windows with a 30 micrometre context halo.
Four 50 micrometre windows cover the small control; its original geometry is
retained and both recommended main DRC and density pass. The
[raw evidence](evidence/core-fill-memory-controls-20260923.tar.gz) includes
the actual per-window macros. The single-process full-core clipped attempt
also reaches its memory limit during the third window after two completed
windows, without an accepted complete GDS. Its replacement runs each window
in a fresh process and writes a GDS checkpoint with verified source/output
hashes after each window. On the small control, this reproduces all 47 cells'
geometry and instance graph from the single-process result exactly. The
35-window full-core checkpointed run remains pending; small controls establish
neither full-core completion nor fill-aware timing.

## Pipeline integration regression repair

The complete local `make check` run found two integration regressions after
1,470 passing tests: the new request register lacked implicit-net guards,
and its formal jobs were unreachable from the normal Make target. Both are
fixed without changing the register logic or default pipeline settings.
The [verification receipt](evidence/reqpipe-integration-20260923.json) records
26 passing targeted tests and fresh `bmc`, `prove` and `cover` results reached
through `make -C hw/soc/formal reqpipe`.

All four lint profiles pass with their previously recorded warnings: 987 for
base, 1,015 for full, 1,012 for base SRAM/logic-ROM and 1,040 for full
SRAM/logic-ROM. Only existing `soc_top` diagnostic line coordinates moved;
warning codes, messages, multiplicities and dispositions are unchanged.
The [raw archive](evidence/reqpipe-integration-20260923.tar.gz) retains both
the original failures and the post-fix measurements. The complete check is
not reported clean: its historical formal-output disposition audit failed,
and missing Pandoc and the configured flow interpreter were skips. These
targeted results do not replace a current complete formal sweep, mapped-boot
qualification or routed timing/LVS acceptance.
