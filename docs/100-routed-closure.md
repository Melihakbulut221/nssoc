# 100 — Routed timing and full-transistor verification

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
