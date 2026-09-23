# 100 — Routed timing and full-transistor verification

Latest [actual ECO24 routed RCX/STA](evidence/eco24-extracted-timing-20260923.json)
reduces slow setup failure to **−3.254664 ns** and slow slew violations to **75**.
Capacitance violations are now **zero in all three corners**, and all three
worst hold slacks are positive. The original 20 ns core/8 ns Ethernet constraints
and 0.95/1.05 derates are unchanged. This remains a nominal-RC, unfilled-layout
measurement; setup and slew closure are still open.
ECO19 now [passes locked full main DRC with recommended rules](evidence/eco19-recommended-main-drc-20260923.json):
**560 categories, zero markers**. Its [independent foundry antenna check](evidence/eco19-supplemental-physical-20260923.json)
also passes with 31 categories and zero markers; density fails with 157 markers. The original unfilled baseline also passes main DRC with
recommended rules off (549 categories, zero markers).
Its new [complete density-filled layout](evidence/full-core-fill-density-20260923.json)
passes the separate density deck, closing the previous 158 density markers
for that baseline. These are distinct GDS inputs: its density result does not
transfer to ECO19. Filled-layout main/antenna checks remain open.
Full transistor LVS fails; overall physical/manufacturing
closure remains open.

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
STA subsequently completed from this exact ECO19 database. Their actual
results are recorded below and supersede the estimated counts in this table.

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
firmware gate and entered implementation. It subsequently exhausted its
300-minute implementation limit in post-CTS repair; the verified checkpoint
and bounded continuation are recorded below.
The [native-cell qualification run](https://github.com/Melihakbulut221/nssoc/actions/runs/35804632644)
at `95cbb15c0b41e26f2a2bd9086f5b8a6cb8b4e4e6` separately tests the enabled
core pipeline with untouched IHP cell/SRAM models in both interface profiles.
It subsequently passes both profiles, without SDF, as recorded below; that
functional result cannot replace extracted timing. The native
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
The subsequent detailed-route/RCX flow uses the actual ODB geometry, rather
than this rejected global-route SPEF; its actual results are recorded below.

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
margin is only 11.8 ps. Subsequent detailed routing and extracted-RC checks
report failures below; this is not a final accepted layout. The unchanged
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
completed main-rule result into supplemental acceptance. The complete
baseline density measurement finishes at 07:00 TRT on 23 September with
**158 markers and a failing verdict**, despite KLayout exiting zero. Its
input is the same original baseline GDS identified above. Cell filler
insertion does not itself prove that metal density rules pass.

The [complete density receipt](evidence/baseline-density-and-rcx-20260923.json)
records 151 local minimum-density violations in Metal2 through Metal5 and
seven global violations in Activ, Metal2 through Metal5 and TopMetal1/2.
Global densities printed by the locked deck are:

| Layer | Density | Minimum |
| --- | ---: | ---: |
| Activ | 34.83% | 35% |
| Metal2 | 20.10% | 35% |
| Metal3 | 23.34% | 35% |
| Metal4 | 18.95% | 35% |
| Metal5 | 2.56% | 35% |
| TopMetal1 | 6.28% | 25% |
| TopMetal2 | 5.66% | 25% |

The [raw archive](evidence/baseline-density-and-rcx-20260923.tar.gz) retains
the report, execution log and verified input identities. No density limit
or rule is relaxed. The hierarchical fill attempt subsequently times out
after 1,800 seconds; this also remains a failed experiment.

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
35-window vendor-macro core run subsequently completed generation; its physical
acceptance remains open. Small controls establish no fill-aware timing.

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

## Extracted SPEF conservation control

The capacitance auditor accepts explicit coupling entries only with
`--allow-coupling`. Each net's declared total must equal its serialized
ground and coupling entries within the existing rounding tolerance. The
default still rejects coupled files. This checks serialization integrity;
it does not establish a correct coupling model or unique physical total
capacitance across nets.

The original baseline's actual OpenRCX SPEF passes for all 95,587 nets,
including 1,946,224 coupling entries. An exact first-net excerpt passes;
deleting either one original pin-node capacitance or one original coupling
entry fails. Sixteen tests cover both grounded and coupled behavior. The
[source-bound receipt and controls](evidence/baseline-density-and-rcx-20260923.json)
retain these results. The earlier estimated-SPEF failures remain rejected;
this result qualifies neither new routed SPEF nor fill-aware timing.

## Bounded input geometry for fill generation

The IHP [chip-finishing documentation](https://ihp-open-pdk-docs.readthedocs.io/en/latest/finishing/filler.html)
also identifies `gdsfill` as a fill-generation option. A separate experiment
pins [its Rust source](https://github.com/aesc-silicon/gdsfill/tree/db268cbf366dd219d1e077d9b2c68782c48c00c5)
and changes only the two SG13G2 boundary selectors to the explicit core marker.
The unmodified tool correctly rejects the absent seal ring. This adapter does
not create a physical seal ring or qualify the core as a finished die.

The [small controls](evidence/gdsfill-controls-20260923.json) retain a real
failure: default targets pass recommended main DRC but leave two TopMetal
density violations on the 100 micrometre control. Raising the fill target
for both upper metals to 60% produces a control with no main or density
markers; original geometry is retained. Foundry rules and spacing checks
remain unchanged. The direct full-core attempt still exceeds its 12 GiB
allocation limit after 28.49 seconds and is rejected.

The replacement clips actual input geometry to each window plus a 30
micrometre context halo. Layer indices keep their original GDS layer and
datatype identities. Each filled clip passes a geometry-preservation audit;
only added fill polygons inside the window are merged into the unchanged
complete hierarchy. Subsequent windows include already generated fill.
Actual complete-layout GDS checkpoints and their hashes are retained after
each window. Resume verifies the original inputs and latest checkpoint.

A 200 micrometre control completes two windows, resumes for two more, and
passes final geometry preservation, recommended main DRC (560 categories,
zero markers) and density. A deliberately wrong checkpoint digest is
rejected before filling. The complete 35-window Rust core generation and
density check subsequently passed, as recorded below.
Its first complete-layout checkpoint independently preserves all 425 original
cells and their instance graph, adding one fill-only cell with 22,063 polygons.
This verifies that first checkpoint's geometry preservation, not physical
acceptance of the partial fill or completion of the other 34 windows.
The [reproducer archive](evidence/gdsfill-controls-20260923.tar.gz) includes
corresponding Rust source, the boundary patch, Python orchestration, exact
controls and [component notices](evidence/gdsfill-controls-20260923-NOTICES.txt).
These controls do not establish complete-core DRC, density, LVS or fill-aware
parasitic/timing acceptance.

## Rejecting invalid density normalization

A real filled window exposes a false acceptance in the report-only density
gate. Its declared 500 by 500 micrometre boundary excludes the 30 micrometre
context halo, but the locked deck counts the halo material in its global
numerators. The deck logs `Shapes exist outside boundary.` without adding a
violation marker. Its zero-marker report therefore cannot establish density
compliance. The runner now rejects that warning as an **ERROR**, even when
KLayout exits successfully, and requires the density log to be present.
The foundry deck and density thresholds are unchanged.

The [physical controls](evidence/density-boundary-guard-20260923.json) retain
the original misleading report and its corrected rejection. A tightly clipped
diagnostic copy of the same region instead reports two real violations:
Metal2 is 29.26% and Metal3 is 34.07%, against the 35% minimum. These are
regional measurements; the accepted full-chip verification input will not
be cropped or have failing regions excluded.

An independent 100 micrometre control passes with the new runner. Adding a
5 by 5 micrometre Metal2 rectangle outside its unchanged boundary produces
the **same zero-marker report**, but is correctly rejected from the logged
boundary inconsistency. Thirty-three runner/preparation tests pass, including
missing-log and boundary-warning cases. The [raw archive](evidence/density-boundary-guard-20260923.tar.gz)
includes both small physical GDS inputs, all diagnostic reports, historical
and corrected runner snapshots, the lock and tests. This guard covers the
reported normalization warning; it is not full-core density closure.

## Actual RC extraction after ECO19 routing

The [new routed measurement](evidence/eco19-extracted-timing-20260923.json)
supersedes the earlier estimated-RC electrical counts for this layout.
Detailed routing finishes with zero router DRC markers. The subsequent
independent OpenROAD antenna check reports zero violating nets and pins.
Fresh RCX produces 96,100 nets; every net passes the serialized-capacitance
conservation audit, including 1,949,542 coupling entries. This arithmetic
check does not establish RC-model accuracy or timing closure.

The original 20 ns core and 8 ns Ethernet constraints and 0.95/1.05 derates
remain in force. All three configured Liberty corners use nominal extracted
RC. Results are:

| Configured corner | Setup slack, ns | Hold slack, ns | Slew violations | Capacitance violations |
| --- | ---: | ---: | ---: | ---: |
| Fast | +3.240561 | -0.006398 | 0 | 2 |
| Typical | +2.422747 | +0.125240 | 0 | 2 |
| Slow | -4.326671 | +0.295344 | 101 | 2 |

The flow fails its timing gates. Both capacitance violations are physical
loads above the 0.300 pF limit: `fanout3467/X` at 0.330216 pF and
`fanout3099/X` at 0.305765 pF. Two fast-corner hold paths start at
`_117085_/Q` and end at `_122627_/D` and `_122647_/D`.

The reports retain 256 disconnected pins classified as noncritical, zero
critical disconnected pins, and 1,048 raw unannotated nets filtered to zero
by the flow. Those raw counts are not erased or represented as universally
complete connectivity/annotation. Clock reports explicitly contain core,
Ethernet RX/TX and generated GTX clocks; the base-SDC warning precedes the
custom Ethernet clock definitions.

The [evidence archive](evidence/eco19-extracted-timing-20260923.tar.gz)
includes step states, exact output netlist/constraints, all three electrical
and clock reports, worst-slack reports, and minimum-slack path excerpts for
each path group. Complete large path reports remain locally hash-pinned.
The fresh GDS is exported from the new DEF with inherited GDS views removed;
its separate recommended main, antenna and density checks remain pending.
This is not full-RC-corner, post-density-fill or SRAM-interior LVS acceptance.

## Complete core fill and density result

All 35 windows of the original-baseline Rust fill run completed. The
[generation receipt](evidence/full-core-fill-generation-20260923.json) verifies
every checkpoint digest and full-layout preservation of all 425 original cells
and their instance graph. The output adds 35 fill-only cells containing 896,230
shape definitions. The [generation archive](evidence/full-core-fill-generation-20260923.tar.gz)
retains orchestration, configuration, logs and geometry audits; large GDS
checkpoints remain locally hash-pinned.

The whole output GDS then [passes the locked density deck](evidence/full-core-fill-density-20260923.json):
zero markers, successful tool exit, unchanged inputs and no outside-boundary
warning. Sanity checks are enabled. Original-baseline global/local density
failures totalled 158 markers; none remain on this filled input. Reported global
densities are Activ 38.89%, GatPoly 26.75%, Metal1–5 38.77%, 37.84%, 40.49%,
47.58%, 47.62%, and TopMetal1–2 41.95%, 43.43%.
The [raw density archive](evidence/full-core-fill-density-20260923.tar.gz)
retains the complete log, report, input identities and unchanged runner.

This is the original baseline with the explicit DEF core boundary, not ECO19.
The filled GDS still needs its own main DRC and antenna results, complete LVS,
and fill-aware parasitic/timing verification. Unfilled ODB/SPEF timing is not
inherited by this GDS-only fill result.

## Hosted timeout checkpoints and bounded continuation

The [pipeline and matched-control receipts](evidence/hosted-pipeline-resume-20260923.json)
retain both interrupted runs at `e5f610cec8ffab23500303190fa09fdf48300675`.
Each exhausted its 300-minute implementation limit. The control had reached
an antenna-rerouting iteration inside detailed routing; its last complete
state is step 37, before detailed routing. The pipeline candidate reached
iteration 140 of a 600-iteration post-CTS search; its last complete state is
step 28, immediately after CTS timing analysis. Neither supplies an accepted
final route or extracted timing result. Inherited intermediate slow/typical
metrics include invalid, extremely large slacks and are not verdicts.

Both downloaded artifact hashes and all ten checkpoint views per run verify.
The pipeline checkpoint is restored in a separate checkout of its exact
source commit; all 139 recorded source/configuration inputs verify. The
normal post-CTS search was configured with an iteration value of 100, matching
the post-global-route setting. This value is not a global runtime bound: setup
search applies its pass limit per endpoint, and hold search checks its bound
between whole endpoint passes. Separate process deadlines bound wall time. Timing thresholds, clocks, derates and final checkers
are unchanged. Twenty-four interface-flow tests and Ruff pass. Local candidate
continuation waits for the current main DRC and sufficient memory; it still
requires logic checking, routing, fresh extraction and independent timing.

The only historical RTL difference from the current request register is the
addition of two `default_nettype` directives. Their removal reproduces the
original bytes exactly. A separate module comparison with common `async2sync`
normalization proves all 141 equivalence cells; a deliberately wrong request
output is rejected. Initial attempts unsupported by the asynchronous SAT model
remain recorded as errors. This module result does not relabel the historical
whole-SoC physical or native-boot result as current-head acceptance.

The [archive](evidence/hosted-pipeline-resume-20260923.tar.gz) and
[notices](evidence/hosted-pipeline-resume-20260923-NOTICES.txt) retain hosted
metadata, interrupted-stage logs, restoration/proof scripts and controls.
The complete large hosted ZIP files and restored physical views remain locally
hash-pinned.

## SRAM annotation-only correction is insufficient

A [read-only enclosure check](evidence/sram-marker-enclosure-20260923.json)
tests whether the original CDL widths could be represented by corrected LVS
markers without changing fabricated metal. Each of the six original bit-cell
resistors specifies 0.26 micrometre width in the CDL, whereas its marker is
0.20 by 0.60 micrometres. Expanding only the short dimension to 0.26 leaves
0.036 square micrometres outside the original metal drawing for **every**
resistor. The proposed correction therefore cannot fit within the existing
metal geometry. No marker, mask, reference, rule or tolerance was changed.
The result retains both source hashes, the complete reproducer and raw output;
it rules out this annotation-only hypothesis without claiming LVS closure.

## Complete main-rule partition controls

The new `hw/soc/flow/check_ihp_drc_partitioned.py` runs the locked main deck in
**two sequential processes**, using its existing table selector. It requires all
37 tables: 18 FEOL/geometry tables and 19 BEOL tables. Recommended checks remain
on, and no rule, region or cell is excluded. Separate processes release FEOL
connectivity data before BEOL starts; a full-core memory improvement has not yet
been measured.

The [control evidence](evidence/drc-partition-controls-20260923.json) compares the
complete main deck with both parts on clean and deliberately faulty layouts.
Category names/descriptions and marker geometries match exactly: **560 categories,
0 markers** on the positive control and **3 markers** on the negative control
(`Act.a`, `LU.b`, `M1.a`). The standalone runner also passes the positive control
and returns failure on the negative control. It rejects missing/duplicate tables,
changed category inventories, inconsistent counts, failed processes and changed
inputs. Its category fingerprints cover 443 FEOL/geometry categories plus 117
BEOL categories. The selected DRC preparation/result/partition tests pass **55/55**.

The [archive](evidence/drc-partition-controls-20260923.tar.gz) preserves the small
GDS controls, raw reports, commands, source hashes and reproducer. These controls
validate this execution method only; they do not establish full-core DRC, antenna,
density, LVS or production acceptance. The active monolithic ECO19 run continues
with its original pinned runner.

## Floating-fill field extraction controls

The [small field experiment](evidence/fill-field-controls-20260923.json) compares
two 5 by 0.5 micrometre Metal1 rails, with and without two separate 1 by 0.5
micrometre floating fill rectangles. KLayout-PEX 0.4.4 retains both fill bodies;
FasterCap 6.0.7 solves their nominal IHP technology model. Each fill body has its
own unknown potential. A Schur reduction enforces zero net charge on each;
grounding the fill is explicitly rejected as a different circuit.

At an actual 12 micrometre field margin, the reduced A/B diagonal capacitances
are 0.671055/0.671101 fF without fill and 0.684853/0.685252 fF with fill.
The corresponding mutual capacitance magnitude rises from approximately
0.102749 to 0.115399 fF. An independent 8 micrometre domain changes the reduced
matrix elements by at most **1.207%**. The experimental comparison uses a 2%
tolerance; it is not a calibrated process-corner accuracy bound. The solver
uses Galerkin discretization and a 0.005 refinement criterion. No measured
matrix is forcibly symmetrized.

Independent checks require finite positive diagonals, nonpositive coupling,
near reciprocity, bounded row sums and a positive-definite symmetric part.
A three-capacitor circuit with two floating nodes checks the reduction against
its analytic result. A separate mesh closure check operates on the generator's
0.0001 micrometre grid: closed and T-junction controls pass; missing, duplicate
and reversed faces fail. Removing a real signal triangle also fails in all four
exported models. These checks concern the numerical surface mesh, not mask DRC.

Two earlier zero-exit collocation results fail numerical checks and remain
rejected. The installed export CLI also parses field-margin/geometry-check
options without forwarding them: a requested 4 micrometre domain actually
used its 8 micrometre default. The attempted duplicate-domain comparison is
rejected. Only explicit API options, measured bounding boxes and independently
checked meshes support the accepted 8/12 micrometre comparison. The original
package is unchanged. Raw logs reparse to the recorded matrices exactly;
recorded input/mesh hashes verify. Dependency wheel RECORD checks were performed
after the experiment and are labelled accordingly.

The [archive](evidence/fill-field-controls-20260923.tar.gz) and
[notices](evidence/fill-field-controls-20260923-NOTICES.txt) retain small geometries,
models, meshes, solver logs, rejected attempts and reproduction scripts.
The dummy connectivity schematic is not an LVS reference. This result supplies
no whole-chip fill-aware SPEF, validated resistance extraction, minimum/maximum
RC corners or final timing acceptance. Full-chip fill-aware verification remains
open, alongside setup, hold, electrical-limit and SRAM LVS closure.

## ECO19 complete recommended main DRC

The newly streamed ECO19 GDS, SHA-256
`983b4dc8fa54a0e23193b309949e38b6a31ff83961ff02895653d16082a1e9a5`,
[passes the complete locked main deck](evidence/eco19-recommended-main-drc-20260923.json)
with recommended checks enabled. KLayout 0.30.7 reports **560 categories and
zero markers**, successful exit and 9,826.04 seconds of rule execution. The
complete category-name/description fingerprint matches the validated inventory;
all recorded GDS, deck, lock and runner hashes verify independently before
publication. The [archive](evidence/eco19-recommended-main-drc-20260923.tar.gz)
retains the complete report, log, command, identities and reproducer.

This closes this exact GDS's main-deck gate. It does not substitute for the
separate foundry antenna/density checks, SRAM-interior LVS, fill-aware extraction
or final timing. The original-baseline filled GDS and later repair candidates
require their own measurements. No violations, rule tables or cells were waived.

## Rejected circuit and SRAM geometry alternatives

The [hypothesis measurements](evidence/closure-hypotheses-20260923.json) retain
two isolated register-file alternatives with matched synthesis and zero-wire
STA. Correcting each stored word before read selection increases area from
159,272.9082 to 210,282.1182 square micrometres and slow register-to-read arrival
from 3.283180 to 3.426965 ns. Explicit one-hot read selection produces
159,943.2534 square micrometres and 3.317870 ns. Both also worsen address-to-read
arrival in all three corners. Neither changes tracked RTL or supplies a
whole-SoC result; no equivalence or physical acceptance is claimed for them.

SRAM experiments retain the independent original CDL dimensions. Symmetric
widening of actual metal and markers to 0.26 by 0.60 micrometres introduces
ten locked spacing failures: eight `M2.b` and two `M3.b`. A bounded asymmetric
alternative preserves all six local resistor terminal pairs, with a bijection
of 15 Metal2 and five Metal3 conductor partitions. Shorted and missing-metal
controls fail. Other flattened witness layers and texts are unchanged.
An earlier hierarchy-handling attempt retained child markers and accidentally
produced two 0.64 micrometre lengths; it is separately rejected.

The corrected local geometry was then inserted into a **separate copy** of the
complete 256x16 SRAM macro. All 168 other cells preserve their shape, text and
instance fingerprints. Full recommended main DRC passes the original macro
with 560 categories and zero markers, but the copied candidate fails with
**19,200 `M3.b` markers**. Local spacing/connectivity success therefore does not
survive the actual macro context. This candidate is rejected before adoption;
no original PDK GDS, CDL, rule, tolerance or production layout changes.

The [archive](evidence/closure-hypotheses-20260923.tar.gz) and
[component notices](evidence/closure-hypotheses-20260923-NOTICES.txt) retain raw
reports, copied candidates, scripts, source hashes and rejected attempts.
SRAM closure still requires a coherent macro design/reference pair and complete
verification; changing mask metal would also require new characterization.


## ECO19 supplemental checks and retained ECO24 repair

The [fresh supplemental measurements](evidence/eco19-supplemental-physical-20260923.json)
use the same ECO19 GDS as the 560-category main DRC pass. Foundry antenna checking
passes all 31 reported categories with zero markers. The separate density deck,
with boundary sanity checking enabled, reports **157 markers** in 18 categories:
one Activ global failure; Metal2–5 global failures and 37/29/36/48 respective
window failures; and one failure on each top-metal layer. The
[raw archive](evidence/eco19-supplemental-physical-20260923.tar.gz) preserves both
successful tool exits and the density wrapper's expected failing exit. Antenna's
log has no runtime footer; completion is established by its completed wrapper,
successful tool exit and complete report inventory, not an invented runtime.

The [ECO24 repair](evidence/eco24-functional-repair-20260923.json) completes 300
setup iterations and retains a saved checkpoint. Its independent retained-cell
logic comparison passes for 73,531 cells: 343 additional positive buffers,
53 equivalent size substitutions and 86 equivalent input permutations. SRAM
interfaces remain exact opaque equations; this proof does not inspect their
transistor interiors. The initial repair uses ECO19's actual nominal extracted
loads, followed by refreshed global-route estimates. The intermediate setup
estimate is still **−2.586 ns**; the final hold-repair estimate is +0.052 ns.
Neither is a fresh routed-corner acceptance result.

A subsequent, separately recorded `setup25` experiment crashes with signal 11 in
`SizeUpMove` before producing an accepted checkpoint. Its preserved log and
inputs are in the [repair archive](evidence/eco24-functional-repair-20260923.tar.gz).
The upstream [similar crash report](https://github.com/The-OpenROAD-Project/OpenROAD/issues/10210)
does not establish this instance's cause. The failed experiment is rejected.
The proven ECO24 state has now completed independent detailed routing, extraction
and STA, with the actual measurements recorded below. A new candidate epoch
disables buffer removal and limits each path repair pass to one change. The original 20 ns/8 ns periods and 0.95/1.05 derates
remain unchanged. Bounded process-group supervision also terminates descendants
on timeout; an intentionally TERM-resistant child verifies this behavior.

## Independent SRAM replacement prototype

A new [128x8 research macro](evidence/independent-sram-prototype-20260923.json)
provides a coherent independently generated circuit/layout pair. It uses
[Chips4Makers' SG13G2 generator](https://gitlab.com/Chips4Makers/c4m-pdk-ihpsg13g2)
at commit `987abb383bcf659258c2f6c890a0f0ebcaaeccbf`, with recorded dependency
commits. Its upstream flow skips SRAM DRC/LVS and leaves Liberty generation
unfinished; those are not accepted as verification. The generator supports
128/256/512-word configurations, so this prototype cannot directly replace the
SoC's larger and dual-port SRAM macros.

The original generated geometry has 384 pSD contact-enclosure violations.
Adding the missing implant enclosure outside active silicon removes them:
1.9584 square micrometres in 384 regions, at most 15 nm growth, with active
doping classification and all other layers unchanged. LVS then identifies
unresolved VDD connections. Two actual Metal4 straps and ten Via3 connections
join five VDD and five VSS rails; the independent schematic remains byte-identical.
The LVS syntax adapter changes only 151 MOS instance designators from `X` to
`M`, with unchanged pins, models and dimensions and an exact reverse comparison.
It never constructs the reference from the extracted layout.

The strapped macro passes **560-category recommended main DRC**, **31-category
antenna checking**, and strict inspection of transistor LVS: **44 matching
circuit pairs and 7,282 devices on each side**, with no unresolved extraction
warnings. The foundry deck's existing SP6T hierarchy integration stays enabled;
no new implicit-net waiver or black box is added. Deliberately doubling a
bitcell pull-up width in a negative reference fails comparison, as does an
actual Metal4 VDD–VSS short. Both raw failing controls are retained.

The first standalone density result is rejected because hierarchical placement
boundaries omit parts of the actual layout. A separate export declares one
132 by 60 micrometre outline enclosing every shape and preserves all other
layer regions. Adding 338 fill shapes preserves the original geometry. This
filled copy again passes main DRC, antenna and transistor LVS, but retains
**three global density failures: Activ, Metal2 and Metal3**. This small macro is
not a whole die; its eventual placement and chip density must be checked in
context. Neither changing the normalization area nor ignoring these failures
is claimed as closure.

The original generated behavioral model writes the previous clocked address
and fails a directed two-address test. A separate corrected copy writes the
current address and passes 1,536 checks over all 128 words and four patterns.
A 7,282-MOS schematic simulation independently confirms writes/reads of A5/C3
at addresses 0/1. The same small pattern passes tt/1.2V/25°C, ss/1.08V/125°C and
ff/1.32V/−40°C with 5 fF ideal output loads and 50 MHz stimulus. Halving the
maximum step from 0.1 to 0.05 ns changes sampled typical outputs by at most
0.339 mV. All accepted transients reach their full stop time without convergence
warnings; an earlier aborted startup is retained as rejected. These tests use
a specified supply ramp and first-write sequence, not arbitrary power-up.

The [archive](evidence/independent-sram-prototype-20260923.tar.gz) and
[notices](evidence/independent-sram-prototype-20260923-NOTICES.txt) include generated
GDS/circuit views, actual repairs, raw reports/waveforms, negative controls and
reproduction scripts. The later all-address attempt and numerical controls are
reported below; the original archive remains an unchanged historical receipt.
PEX, complete functional/PVT characterization, setup/hold and Liberty models,
capacity/port-compatible banking, final chip verification and reliability remain
open. The existing SoC SRAM and failing full-chip LVS are unchanged.


## SRAM all-address attempt and numerical controls

The [new numerical-control receipt](evidence/sram-convergence-controls-20260923.json)
retains an actual failure: the first 5,120 ns all-address transistor trial
aborts at **226.917 ns**, with a timestep-collapse diagnostic at q0. The simulator
returns zero, but the verifier rejects its incomplete waveform. It is not a
full-memory pass.

The same circuit, models, startup and first 300 ns of stimulus were then run
with a 0.05 ns maximum step under trapezoidal and second-order Gear integration.
The first Gear attempt hits its 900-second wall-time bound before reaching the
stop time and remains rejected. Repeating that unchanged numerical case with
an 1,800-second bound completes in 1,190 seconds. Both methods complete all
15 writes without convergence diagnostics; independently reparsed outputs
differ by at most **0.124972 mV**, below the 1 mV comparison tolerance.

A new 128-write/128-read, 5,120 ns half-step trial follows these controls and is
still running at this receipt's timestamp. The [archive](evidence/sram-convergence-controls-20260923.tar.gz)
and [notices](evidence/sram-convergence-controls-20260923-NOTICES.txt) retain the
failed and timed-out attempts, complete control waveforms and scripts. This
closes only the short numerical-control check. Complete memory functionality,
PEX/PVT characterization, density, SoC integration and full-chip LVS remain open.

## Bound hold repair without changing acceptance

The separate pipeline candidate's post-CTS hold search keeps adding buffers
while its worst slack remains −2.555 ns. The regular physical flow now bounds
hold repair with **`-max_iterations 1000`**, independently of the existing 100-iteration
setup bound. Both actual LibreLane 3.0.5 post-CTS/post-global-route templates
retain their repair calls and final view export. Missing or duplicated template
anchors fail before a generated script is written. The focused Python/Tcl
regressions pass 34 tests.

The already running, unmodified search remains a separate comparison. A fresh
setup-100/hold-1000 epoch starts from the same saved source-bound CTS state;
its continuation requires functional proof and fresh routing/extraction.
An iteration limit saves a measurable intermediate state; it never changes
clocks, derates, electrical limits or the final failing timing classification.

Runtime follow-up clarifies this parameter's granularity: the pinned
[OpenROAD hold implementation](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/rsz/src/RepairHold.cc)
checks the limit between complete passes over its failing endpoints. The
counter increments inside that pass, so a first pass containing 9,395 endpoints
can exceed 1,000 before the next limit check. It is not a strict bound on the
displayed endpoint counter or wall time. The separate process timeout remains
necessary. The running experiment and its saved inputs are unchanged.


## Correct a cumulative SRAM slew-conversion defect

A [minimal timing-engine regression](../hw/soc/flow/check_sta_load_slew.py)
uses one unchanged IHP buffer and one SRAM. One connected mask input passes
in the original tool. With 64 electrically equivalent mask inputs, the original
OpenSTA 2.7.0 reports a 1.06524014 ns driver transition but SRAM pin transitions
ranging from 1.42032015 to **105,566,200 ns**. Each sink should receive the same
single threshold conversion: `(40 / 0.5) / (60 / 1) = 4/3`.

Inspection of the pinned OpenSTA source identifies the shared driver-slew
variable being modified inside the load loop. The measured local backport
uses a fresh load-slew variable for each pin, corresponding to the
[upstream correction](https://github.com/The-OpenROAD-Project/OpenSTA/commit/818596f25aff382d8a085d4464b3b1b9d481e30b).
Separate original and corrected executables are built from the same pinned
source. The original fails the 64-load control in all three library corner
sets; the corrected version passes all one-load and 64-load checks with less
than 0.00000012 ns conversion error. The native image is also retained as a
failing control. The existing fast mapping uses −40°C standard cells and −55°C
SRAM models; these controls do not establish uniform-temperature qualification.

The [receipt](evidence/sta-load-threshold-repair-20260923.json),
[archive](evidence/sta-load-threshold-repair-20260923.tar.gz) and
[component notices](evidence/sta-load-threshold-repair-20260923-NOTICES.txt) retain
original/modified source, build records, complete miniature controls, raw timing
reports and reproducibility scripts. External Liberty implementations and
executables are separately obtained inputs. Genuine electrical violations of
the deliberately heavily loaded probe remain visible: this PASS concerns the
calculation, not the design's slew limit.

Replaying the same actual ECO19 routed netlist, saved SDC and nominal extracted
SPEF with both executables produces **identical setup, hold, slew-count and
capacitance-count results in all three corner sets**. Therefore this correction
does not remove ECO19's real −4.326671 ns setup failure, 101 slow slew failures,
two capacitance failures per corner or fast hold failure. Separate zero-wire
pre-PNR diagnostics lose the spurious huge SRAM values but still fail on
unbuffered control/reset fanout; those are not routed results. The pinned
LibreLane/OpenROAD image and already running jobs remain unchanged. The fixed
standalone STA is an independently measured candidate, not a blanket tool-flow
or manufacturing acceptance.

## Independent 256x16 dual-port SRAM physical checks

The [dual-port prototype receipt](evidence/independent-dp-sram-prototype-20260923.json)
extends the independent SRAM work to 256 words of 16 bits, two clocks and two
byte-write enables per port. The initial one-enable generator request fails
because this factory requires eight bits per enable. The successful two-enable
generation retains that rejected attempt. Its independent schematic has 88
terminals; all match the actual GDS pin-label inventory. The simulator-to-LVS
adapter changes only 162 primitive instance designators, with a reversible
comparison of every pin, model and dimension.

The original layout fails 2,560 `Cnt.g2` checks and retains an unresolved supply
must-connect requirement. Adding 13.056 µm² of implant outside active regions,
then 18 Via3 connections and two internal Metal4 supply straps, resolves these
specific physical defects. The independent circuit reference is unchanged.
The repaired layout passes **560 recommended main DRC categories**, **31 antenna
categories**, and strict transistor LVS: **52 matching circuit pairs and 36,776
recursive MOS devices**, with no unresolved extraction diagnostics. No SRAM
interior is blackboxed. A physical VDD–VSS short and a deliberately wrong
transistor width each produce a real LVS mismatch. Initial postprocessor errors
from a Python environment lacking KLayout remain recorded separately from the
successful, version-recorded re-audits.

A separate 322×119 µm standalone outline encloses all mask geometry. Adding
1,877 fill shapes preserves the original circuit geometry and again passes
main DRC, antenna and LVS. Density still fails four global minimum checks:

| Layer | Measured density | Required minimum |
|---|---:|---:|
| Activ | 27.68% | 35% |
| Metal1 | 32.71% | 35% |
| Metal2 | 33.58% | 35% |
| Metal3 | 34.83% | 35% |

These are results from the unchanged foundry deck, with boundary sanity enabled.
Fill-tool progress estimates are not density acceptance. No rule is waived and
the normalization boundary is not reduced.

The upstream behavioral model writes the previous latched address on both ports.
A separate copy changing four write indices passes **1,540 checks**, including
all addresses, both ports, alternating byte masks and concurrent accesses to
different addresses. The original fails the same test. This does not establish
transistor/model equivalence, simultaneous same-address behavior or 125 MHz
operation. The original physical receipt predates the separately recorded
nominal transistor result below.

The [raw archive](evidence/independent-dp-sram-prototype-20260923.tar.gz) and
[notices](evidence/independent-dp-sram-prototype-20260923-NOTICES.txt) preserve the
generated circuit/GDS, geometry repairs, all completed reports and fault controls.
Density, extracted timing, complete PVT/function characterization, Liberty/LEF,
native bit-mask/MEN/BIST compatibility and SoC integration remain open. Existing
SoC SRAMs and the failing complete-chip LVS are unchanged.

An upstream alternative was checked before treating this as a replacement path:
the official [28 January 2026 GDS update](https://github.com/IHP-GmbH/IHP-Open-PDK/commit/994d7f6a886da628ff64cbe47d5a151eef893ce5)
for the existing vendor 256x16 two-port macro leaves 168 internal cells and all
top instances unchanged. Its only geometry change is the top placement boundary
on layer 189/4. The archived comparison therefore finds no transistor,
interconnect or bitcell-resistor correction in that update. It is not adopted
as an LVS fix, and no new LVS success is inferred from the version change.

## ECO24 actual extracted timing and next repair

The [new completed measurement](evidence/eco24-extracted-timing-20260923.json)
uses a fresh detailed route and nominal SPEF, SHA-256
`2df4bfa9cc026692522c57c49bab4a9a18119fe16dca62d7bc1b80caf65ea5c6`.
All 96,443 nets pass serialized-capacitance conservation; this arithmetic check
does not establish physical RC accuracy or complete parasitic annotation.

| Liberty corner, nominal extracted RC | Worst setup (ns) | Worst hold (ns) | Slew violations | Capacitance violations |
|---|---:|---:|---:|---:|
| Fast | +3.282231 | +0.036887 | 0 | 0 |
| Typical | +2.137891 | +0.147579 | 0 | 0 |
| Slow | **−3.254664** | +0.273627 | **75** | 0 |

The flow exits **2** because real final timing/electrical checks fail. It reports
zero router DRC violations, zero OpenROAD antenna nets/pins and zero critical
disconnected pins; all raw disconnected and unannotated counts are preserved in
the receipt and raw checks. No counts are waived to claim full closure.
The [archive](evidence/eco24-extracted-timing-20260923.tar.gz) retains reports,
exact netlist/SDC, state identities and minimum reported path excerpts per group.
Its fresh unfilled GDS is
`af8ccf9bb86db5decd6ea0e075936d991fdb8df00a033e01cd419f319668d699`.
**ECO19's foundry DRC/antenna passes do not qualify this different GDS.**

The worst slow path starts at register-file address bit `raddr_b_i[1]`, passes
through register selection/ECC and processor logic, and ends at `_119494_`.
The path includes a minimum-drive NAND4 with 0.129041 pF reported load and
1.938393 ns cell delay. The worst slew is 3.171175 ns against a 2.507400 ns limit.
A separate ECO27 experiment uses these actual loads and a 40-percent slew repair
margin, followed by refreshed global routing and bounded timing repair.
The physical limits themselves are unchanged. Its estimates, even if improved,
will require a new logic proof, detailed route, extraction and independent checks.
The separate request/writeback pipeline candidate also remains under evaluation.

Final setup/slew closure, relevant min/max RC corners, fill-aware extraction,
all foundry decks on the accepted filled layout and complete SRAM-interior LVS
remain release requirements. Passing nominal-RC hold and capacitance in this
specific measurement closes neither those requirements nor the full audit.

## Dual-port nominal transistor simulation and independent stimulus audit

The [completed schematic simulation](evidence/dp-sram-nominal-transistors-20260923.json)
uses all 36,776 MOS devices of the independent 256x16 circuit, nominal
1.2 V/25 °C models, two 50 MHz clocks offset by 10 ns and 5 fF output loads.
There are no forced initial states or extracted wire parasitics. Over 90 ns,
port 1 writes `A55A` and `C33C` to addresses 0 and 1; two port-1 and four
port-2 settled 16-bit observations all match. Model/convergence diagnostics
are absent. An independent waveform audit verifies both clocks, supply and
every address/data/write-enable stimulus bit at those observations. Six controls
corrupt an address, output or clock, truncate the waveform, insert NaN or reverse
time; all are rejected.

The first Sparse-solver run reaches its 3,600-second wall limit and remains
**failed/incomplete**. The completed KLU run takes 1,140.950 seconds with the same
circuit, stimuli, models and 0.05 ns maximum step; only the solver option and
wave output path differ. A separate completed 128x8 control compares four
settled samples against Sparse, with maximum output difference `1e-11 V`.
This does not imply full-waveform solver agreement or a benchmarked speedup;
the runs experienced different concurrent host loads.

The [raw archive](evidence/dp-sram-nominal-transistors-20260923.tar.gz) preserves
the timeout, completed logs/waves, benches, tool/model identities, scripts and
independent fault controls. The next half-step and hot/slow/cold/fast trials
remain separate pending measurements. Port-2 writes, transistor-level byte masks,
all addresses and collisions, PEX, Liberty/LEF and complete SoC integration are
still open. The existing full-chip LVS failure is unchanged.

## Independent 512x64 SRAM bank: physical checks and remaining density failure

The [new bank prototype](evidence/independent-sp512-sram-prototype-20260923.json)
scales the independent single-port circuit to **512 words × 64 bits**, with
eight byte enables. The generator explicitly rejects a 2048-word request;
that failed attempt is retained. Four such banks and a qualified interface
wrapper would be needed for one existing 2048x64 macro. No replacement has
been integrated into the SoC.

The independent schematic contains **202,510 MOS devices**. The original
generated footprint is 719.14 × 168.775 µm. Implant enclosure repairs add
47.0016 µm² outside existing active regions; two internal Metal4 supply straps
and 22 Via3 connections join the 11 VDD and 11 VSS rails. These changes preserve
the independently generated schematic. All **148 terminals** have matching
GDS labels and pin regions contained in actual conductors.

| Independent check | Strapped layout | Filled layout |
|---|---|---|
| Recommended main DRC | 560 categories, 0 markers | 560 categories, 0 markers |
| Antenna DRC | 31 categories, 0 markers | 31 categories, 0 markers |
| Strict transistor LVS | 46 matching circuit pairs | 46 matching circuit pairs |
| Density, including boundary sanity | **43 markers** | **1 marker: active density** |

The filled export has an enclosing **720 × 170 µm** outline and **5,903 added
fill shapes**. Every original shape and instance is preserved. Its remaining
active-area density is **25.786%**, below the **35%** global minimum. Metal
density and boundary markers are resolved, but standalone density still fails;
the final integrated chip must satisfy the global rules on its own geometry.
The outline is not reduced and no rule is waived.

Two independent fault controls introduce a real VDD/VSS short and change a
reference transistor width. Each is rejected with 45 matching pairs and one
nonmatching pair. A separate behavioral copy corrects eight write-address
indices and passes **9,218 checks** over all 512 addresses, all eight byte
masks, write-disabled reads and registered read selection; the original model
fails the same bench. This does not prove transistor/model equivalence.

The [raw archive](evidence/independent-sp512-sram-prototype-20260923.tar.gz) and
[notices](evidence/independent-sp512-sram-prototype-20260923-NOTICES.txt) retain
the independent circuits/layouts, repairs, failed capacity attempt, checks,
fault controls and exact source/tool identities. Transistor operation/PVT,
extracted timing, characterized Liberty, routing-access LEF, native enable/BIST
compatibility and bank composition remain open. These standalone results do
not close the existing full-chip SRAM-interior LVS or routed setup/slew failures.

## Separate OpenROAD tool qualification and setup-crash follow-up

The [read-only qualification receipt](evidence/openroad26-readonly-qualification-20260923.json),
[raw reports and replay scripts](evidence/openroad26-readonly-qualification-20260923.tar.gz)
and [component notices](evidence/openroad26-readonly-qualification-20260923-NOTICES.txt)
record a separately extracted OpenROAD `26Q2-1164-g08f67ee5ec` executable. The
original LibreLane image and PDK remain unchanged. The public Ubuntu 24.04
package is identified by SHA-256
`f3f1eeaa18f327503f72cc45dcef5b1514ec2e89726ec53b4553bf4f951168a3`;
project-local runtime packages, executable, wrappers and resolved shared objects
are also hashed. Nothing was installed into the system.

[Upstream PR 10225](https://github.com/The-OpenROAD-Project/OpenROAD/pull/10225)
fixes stale input-path handling in resizer moves, including the `SizeUpMove`
chain implicated by the earlier `setup25` crash. Git ancestry confirms that the
new binary's source includes that fix and another 513 commits. This is a reason
to test the newer tool, not proof that the fix alone explains this design's crash.

All six one-load/64-load slew controls pass across the configured fast, typical
and slow libraries. Reading the original `setup25` ODB reproduces its output
netlist byte for byte: 98,441 instances, 96,653 nets and 144 top-level ports.
The retained-cell checker separately passes for 73,531 cells and 24,910 positive
buffers, with no resizing or pin permutation. The four clock periods remain
20/8/8/8 ns.

Read-only replay of the exact completed ECO24 netlist, SDC and nominal SPEF also
completes in all three corners. The maximum setup/hold difference is
`0.000001776357 ns` (about 1.8 fs); violation counts are identical. Slow setup
remains **−3.254662 ns**, hold **+0.273628 ns**, with **75 slew violations and zero
capacitance violations**. This comparison does not close any physical failure.
The first replay's decimal-format assertion and first probe's missing output
directory error are retained with the corrected runs.

A separate bounded replay of the original `setup25` repair script **failed**
after 2,526.83 seconds. The executable aborted in
`rsz::SizeUpGenerator::loadStageContext` with a timing-graph `TableBlock` vector
assertion. The [follow-up receipt](evidence/physical-tool-format-followup-20260923.json)
and [complete failure log and diagnostic scripts](evidence/physical-tool-format-followup-20260923.tar.gz)
preserve this negative result. No completed repaired state or new routed result
was accepted. The completed read-only tests do not establish optimization,
routing compatibility, foundry DRC/LVS or signoff.

The later [upstream endpoint-path correction](https://github.com/The-OpenROAD-Project/OpenROAD/pull/11215)
addresses references invalidated by earlier committed repair moves. A separate
source build containing this correction is being prepared for qualification;
it has not yet demonstrated a fix for this design's failure.

An unchanged-design compatibility experiment also found that the newer OpenDB
schema cannot be read directly by the original tool. A DEF round trip preserves
the exact geometry and passes retained-cell logic checking, but loses routing
guides. Explicitly importing the text guides restores their counts and boxes,
while 96,443 nets still differ in guide metadata. Any future cross-version
candidate therefore needs regenerated global routing and a fresh detailed
route, extraction and timing run. This experiment does not authorize reusing
the old routed results for a new candidate.

### Dual-port SRAM half-step and temperature/voltage controls

The independent 256×16 dual-port prototype now also completes three 90 ns
schematic controls: typical 1.2 V/25 °C with a 25 ps maximum step, slow
1.08 V/125 °C and fast 1.32 V/−40 °C with 50 ps steps. All six settled word
observations pass in each run, with no simulator/model/convergence diagnostics.
The typical half-step comparison changes settled outputs by at most
**8.727358 µV**, below the declared 1 mV tolerance.

The [receipt](evidence/dp-sram-pvt-controls-20260923.json),
[complete waveforms, benches and logs](evidence/dp-sram-pvt-controls-20260923.tar.gz)
and [notices](evidence/dp-sram-pvt-controls-20260923-NOTICES.txt) retain an
independent audit of all stimulus bits, both clocks and supply at 18 read
observations. Twenty-one deliberately corrupted-wave controls are rejected.
An initial failed audit control is retained: inconsistent floating-point time
conversion selected the other equidistant sample for mutation. Using the same
time expression for observation and mutation fixes that auditor defect without
changing any circuit or simulation waveform.

These are two-address, 50 MHz, 5 fF schematic tests. They do not establish
125 MHz operation, full address/mask/collision coverage, extracted timing,
Liberty characterization or native SoC integration. The existing full-chip SRAM
LVS failure remains open.

## Experimental RC-model comparison on the same ECO24 route

The [12-corner comparison](evidence/eco24-experimental-rc-comparison-20260923.json)
and its [report archive](evidence/eco24-experimental-rc-comparison-20260923.tar.gz)
keep the routed geometry, netlist, 20/8/8/8 ns clocks and derates unchanged.
Four RC extraction rule sets are each combined with the same three Liberty
corners. The original nominal rules reproduce all previously published metrics.
All four SPEFs contain 96,443 nets and pass the limited capacitance arithmetic
check; that does not validate the physical RC values.

| RC rule set | Slow setup (ns) | Slow hold (ns) | Slow slew violations | Slow capacitance violations |
| --- | ---: | ---: | ---: | ---: |
| Existing nominal | −3.254664 | +0.273627 | 75 | 0 |
| Experimental Magic minimum | −22.536873 | +0.497673 | 10,695 | 2,017 |
| Experimental Magic nominal | −26.533215 | +0.379753 | 13,801 | 2,547 |
| Experimental Magic maximum | −30.642238 | +0.184382 | 16,909 | 3,092 |

The experimental maximum model also fails fast-corner setup/hold
(−0.011536/−0.027719 ns). The [pinned upstream configuration](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/5e6d592e4002946a4616f798c357f0f3c06cf3b6/ihp-sg13g2/libs.tech/librelane/config.tcl)
enables the existing nominal rules and leaves the Magic-derived alternatives
commented as experimental choices. None is promoted here to a qualified
manufacturing corner. Their substantially different results require model
validation, rather than selecting whichever model passes.

A separate replay using the qualified newer OpenROAD executable confirms the
experimental nominal model's slow setup near **−26.533173 ns**, with the same
13,801 slew violations. Capacitance counts differ by 20 (2,547 versus 2,527);
therefore this is not an assertion of exact cross-version electrical-check
equivalence. The original nominal model's zero-capacitance result is explicitly
limited to that model. Min/max RC qualification, fill-aware extraction and full
physical acceptance remain open. Earlier custom-corner LEF mapping and auditor
startup errors are preserved alongside the corrected run.

The [independent coupling audit](evidence/physical-tool-format-followup-20260923.json)
checks all four generated SPEFs for finite nonnegative capacitances, node
ownership, equal mirrored coupling values and missing or duplicate entries.
All 96,443 nets in each model pass these bookkeeping checks. Five deliberately
corrupted miniature inputs are rejected. The larger experimental coupling sums
are therefore not explained by unpaired or duplicate coupling records; this
does not establish which model matches fabricated interconnect.

The setup iteration scope was checked against both the pinned
[February implementation](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/rsz/src/RepairSetup.cc)
and the newer
[legacy setup policy](https://github.com/The-OpenROAD-Project/OpenROAD/blob/08f67ee5ecd14db5a42be8c610bbfd1ccf079299/src/rsz/src/policy/SetupLegacyPolicy.cc).
The configured pass limit is applied to each endpoint. The newer trial's
progress counter consequently continued past 100 before the assertion failure;
this did not mean completion or a missing timeout. An independent three-hour
process deadline also bounded the trial.
