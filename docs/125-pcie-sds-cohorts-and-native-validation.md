# 125 — SDS cohorts, native lane tests and retained timing failures
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured development — 5 October 2026

Local SDS locking and bounded common-clock lane deskew now pass actual IHP
cell simulation, including independently mapped faulty RTL. A separate x4
RTL composition advances the descrambler through complete ordered sets and
checks scrambled-data parity. Complete binary state-function equivalence
also closes the earlier default-capacity integrity V1/V2 mapping comparison.
**The newer integrity candidates still fail slow and typical setup. Full
PCIe Gen3 x4, qualified PLL/CDR/SERDES, complete PCS/LTSSM, physical CDC,
main-chip integration, qualified RC/ESD and product approval remain open.**

The [finite delivery inventory](../hw/soc/pcie-evidence/20261005-sds-cohorts-and-native-validation/delivery-inventory.json)
pins ready source files, copied compact receipts and immutable public assets.
Its verification rehashes local source and receipt bytes; it does not rerun
all experiments or download their complete archives again. Each publication
receipt records its original authenticated and anonymous hash roundtrips.
The [previous report](124-pcie-pll-acquisition-and-recovered-lanes.md)
remains an unchanged snapshot.

## Native local SDS lock and cohort transport

The lane V3 RTL recognizes the complete SDS ordered set locally and disables
further EIEOS searching before a common-clock roundtrip. This prevents an
EIEOS-shaped data payload from changing an already locked alignment.
Reset, force and alignment loss clear the lock. Aligned EIEOS classification
is separate from realignment; SDS requires the ordered-set header and the
exact full pattern. Variable SKP lengths remain 66/98/130/162/194 bits.

| Actual mapped experiment | Baseline SG13G2 cells | Complete cases | Separately mapped RTL faults |
| --- | ---: | ---: | ---: |
| Lane V3, native method V4 | 5,207 | 11 positive | 24 |
| SDS deskew V1, native adapter V2 | 1,185 | 3 positive + 17 expected-fault scenarios | 10 |

The lane campaign contains **25 actual maps and 35 completed simulations**;
the deskew campaign contains **11 maps and 30 completed simulations**.
The 14 lane-method and 38 deskew-adapter preflight controls include process
cleanup, source/model guards and lossless preservation. Every closed VVP is
gzip-compressed and fully decompressed for byte/hash comparison before its
raw copy is removed: **462,269,425 bytes across 35 lane programs**, and
**57,273,714 bytes across 30 deskew programs**, remain recoverable. See the
[lane receipt](../hw/soc/pcie-evidence/20261005-sds-cohorts-and-native-validation/lane-native/native-v4/ready.json)
and [deskew receipt](../hw/soc/pcie-evidence/20261005-sds-cohorts-and-native-validation/deskew-native/native-v2/ready.json).

The first deskew native runner failed elaboration before any DUT simulation:
its parameter override targeted a synthesized module without a parameter.
That [failure remains public](../hw/soc/pcie-evidence/20261005-sds-cohorts-and-native-validation/deskew-native/native-v1/failure-publication.json).
The new adapter proves the mapped JSON's default skew parameter is exactly
64, preserves the original oracle bench and removes only that literal
override. The successful run reuses the exact original baseline map and
maps all ten mutants independently. An intended fault must produce its
specific diagnostic; a compiler failure cannot satisfy the rejection gate.

These are functional cell-model simulations at the declared 4 ns bench
clock with a 1 ns observation offset. They do not establish SDF timing,
metastability behavior or a qualified physical lane rate. **Native adapter
V2 validates deskew RTL V1; it is not the later strict-cohort RTL V2.**

## Four lanes, complete records and ordered-set state

The earlier deskew RTL's **30 checks** comprise 20 port scenarios and ten
actual mutations. Its contract requires one fresh, LTSSM-qualified SDS
cohort after reset, bounded skew, and DATA immediately after each lane's
SDS. It pairs DATA by ordinal and exposes SKP records separately. The
recovered-x4 V2 wrapper passes nine full raw-port cases and resolves twelve
distinct controls; thirteen pytest executions include the corrected
targeted repetition. This is bounded transport, not a proof that arbitrary
independent SKP lengths satisfy a complete link protocol. The
[RTL receipt](../hw/soc/pcie-evidence/20261005-sds-cohorts-and-native-validation/sds-x4-v2/root-delivery/validation.json)
retains the first POR unknown, an over-restrictive inactive-ready fixture
and early mutation-oracle failures.

Record descrambler V1 resets its LFSR on EIEOS, advances it through non-SKP
ordered sets including SDS, and preserves it across SKP. Its parity check
uses scrambled DATA and resets at the declared SDS/SKP boundaries. A parity
mismatch reports a lane error without retraining. This closes a missing
state transition in the earlier externally seeded data-only primitive;
that old primitive is not silently relabeled as an ordered-set receiver.

The record block has **28 passing RTL checks: 17 positive executions and
11 actual mutants**. Recovered-x4 V3 has **11 raw-port cases executed in two
complete suites**, twelve actual wiring mutants and two invalid-depth
controls. Its initial pytest result was 14 pass/1 fail: a faulty ignored
ready signal was caught by the parity/LFSR diagnostic before the fixture's
expected epoch fault. A one-predicate correction then passed; the original
failure and source remain archived. The
[complete receipt](../hw/soc/pcie-evidence/20261005-sds-cohorts-and-native-validation/record-x4-v3/root-delivery/validation.json)
also distinguishes a reconstructed first test file from historically
captured files and limits the added runtime inventory accordingly.

Strict EDS/parser decisions, equal normal-SKP cohort policy and the next
raw-to-packet composition are separate ongoing revisions. They are excluded
from this report's ready source allowlist. None of these RTL compositions
establishes a full LTSSM, physical rate compensation or a complete Gen3 link.

## Complete earlier proof; newer timing remains a failure

Both actual monolithic and partitioned ABC checks finish equivalent for
the exact default-150 integrity V1/V2 native graphs. The completed closure
covers **8,426 state flip-flops, 8,560 unconstrained inputs, 25,588
D/clock/reset/public-output functions and 34,148 ordered AIGER symbols**.
All **4,288 partition IDs** appear exactly once. The
[completed proof receipt](../hw/soc/pcie-evidence/20261005-sds-cohorts-and-native-validation/integrity-v2-proof/terminal-proof-peer/pcie-integrity-v2-complete-native-equivalence-validation-20261005.json)
preserves both earlier failed attempts and identifies tool inventories
added only at seal. This proves binary same-state transition functions
between those maps, not protocol conformance, arbitrary-X behavior, all
parameters, reset timing or physical timing closure.

Later candidates change retirement caching, packet metadata selection and
capacity arithmetic. Their unchanged 4 ns preplacement profile reports:

| Candidate | Slow setup slack | Typical setup slack | Fast setup slack | Result |
| --- | ---: | ---: | ---: | --- |
| Integrity V5 | −5.616894 ns | −2.064867 ns | +0.013858 ns | Setup FAIL |
| Integrity V6 | −4.668128 ns | −1.500196 ns | +0.370961 ns | Setup FAIL |
| Integrity V7 | −4.563619 ns | −1.428937 ns | +0.421192 ns | Setup FAIL |

V5's separate cache invariant is now universally proved for binary
one-step transitions at pointer widths 7 and 12, with five actual
counterexamples. It assumes the old cache equals the old verdict lookup;
initialization and reachable-state quarantine remain separate reasoning.
V6's metadata network has a separate universal binary proof at both widths
and five counterexamples. Its default-capacity RTL evidence comprises
26 public cases, 32,768 finite arbitrary parser prestates, and 524,288
maximum-width literal-network cases. Those finite parser tests are not a
whole-parser formal proof.

V7 also passes 26 default-capacity public cases, 67,584 binary capacity
states, 131,072 scalar bindings including X patterns, and 18 actual mutants.
Its capacity arithmetic does not claim identical pessimism for arbitrary
X-valued retirement. These scopes and the actual preplacement failures are
kept in the [component inventory](../hw/soc/pcie-evidence/20261005-sds-cohorts-and-native-validation/delivery-inventory.json).
The original V5/V6 maximum-4118 compilers and V7 maximum-4118 simulation
remain pending. No completed maximum whole-DUT result, new whole-mapped
function proof, routed timing or full native port replay is inferred.

## Local VCO wire changes and actual bias failures

The separate V6 and V7 physical revisions preserve the circuit while
changing local routing. V6 uses a 553-resistor/563-capacitor hybrid graph;
V7 uses 889 resistors/767 capacitors. Each has 73 passive native comparisons.
V7's 652 via cuts, native DRC/LVS and 21 physical fault controls establish
its stated geometry/connectivity scope, not qualified RF extraction.

| Physical revision / VCTRL | Native frequency | Complete signed-swing cycles | Electrical screen |
| --- | ---: | ---: | --- |
| V6 / 0.60 V | 7.540860476 GHz | 44 | All 30 HBT screens pass |
| V7 / 0.60 V | 7.570422211 GHz | 44 | All 30 HBT screens pass |
| V7 / 0.40 V | 7.699337 GHz | Retained full capture | Six ring current failures |
| V7 / 0.85 V | 7.076119 GHz | 42 | All 30 HBT screens pass |

The operating swing floor stays at signed 300 mV. At 0.40 V the six real
ring devices reach approximately **3.58–3.64 mA per emitter**, exceeding the
unchanged current limit; faster oscillation does not make that point pass.
The [bias-point receipt](../hw/soc/pcie-evidence/20261005-sds-cohorts-and-native-validation/vco-local-v7/pcie-vco-v4-local-v7-wire-20261005/bias-points-validation.json)
preserves both full waveforms, the first resource-admission failure and the
old-release upload failure. These measured points do not bracket 8 GHz;
they also do not establish that all possible tuning is impossible.
PVT, thermal settling, body spreading resistance, qualified RF extraction,
loop behavior and full PHY integration remain open. A new VCO circuit/layout
draft is explicitly outside this delivery.

## Publication continuity and the interrupted tighter PLL run

The old immutable evidence release reached **1,000 assets**. GitHub rejected
the next upload with HTTP 422, and the tighter 2.5 ps PLL acquisition
experiment stopped at **379.169 ns**. It has no 1 µs analog verdict and no
completed timestep comparison. The earlier independently replayed 5 ps,
1 µs nominal acquisition result remains unchanged.

An additive publisher selects the
[continuation release](https://github.com/Melihakbulut221/nssoc/releases/tag/evidence-20261005-pcie-continuation).
Its eight controls and real authenticated/anonymous readback are recorded
in the [rollover receipt](../hw/soc/pcie-evidence/20261005-sds-cohorts-and-native-validation/publication-rollover/pcie-phase16-delivery-20261005/pcie-evidence-release-rollover-20261005.json).
Old assets were neither replaced nor deleted. A separate publication-only
PLL launcher passes 15 controls on each of Python 3.12 and 3.14, plus an
independent root execution of all 15. Its
[literal source bridge](../hw/soc/pcie-evidence/20261005-sds-cohorts-and-native-validation/pll-publication/publication-v2-source/source-freeze.json)
preserves the circuit, deck, measurement and process lifecycle. A fresh
matched 2.5 ps, 1 µs run has started from time zero; no result or paired
convergence verdict is available at this snapshot. No electrical, thermal,
frequency, phase or timestep limit has been relaxed. The
[interrupted capture receipt](../hw/soc/pcie-evidence/20261005-sds-cohorts-and-native-validation/pll-publication/publication-limit-failure/pcie-pll-acquisition-publication-failure-validation-20261005.json)
retains 59 published parts, the failed part and the unparsed tail.

## Remaining integration gates

Native functional evidence, local geometry checks and partial formal
relations remain separate from system acceptance. Required work includes
the complete strict PCS/packet integration, sustainable controller behavior,
clock and reset qualification, setup/hold closure with qualified coupled
RC, full-chip DRC/LVS/ESD, manufacturing review and silicon validation.
The [product acceptance contract](92-product-acceptance.md) still governs
delivery of the complete chip.
