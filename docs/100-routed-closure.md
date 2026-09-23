# 100 — Routed timing and full-transistor verification

Latest measurement: the [actual-segment replay](evidence/global-route-segment-replay-20260923.json)
avoids the defective estimated-SPEF exporter and reproduces in-memory timing.
Its three-corner global-route estimates have no slew, capacitance or negative
hold violations, but slow setup remains **-3.657322 ns**. Detailed-route RCX
verification and full foundry DRC are pending; full transistor LVS has failed.
No final physical or manufacturing gate is declared closed.

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
