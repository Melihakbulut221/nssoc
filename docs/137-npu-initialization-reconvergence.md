# 137 — NPU initialization reconvergence and mapped repair
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured result — 6 October 2026

A native-cell unit test reproduces an initialization defect in the rejected
whole-chip timing candidate. A one-gate Boolean factoring experiment corrects
that isolated failure. **The repaired full-chip boot and physical timing are
not yet accepted.** No firmware, memory model, reset sequence or timing
constraint is relaxed.

The completed [paired write trace](https://github.com/Melihakbulut221/nssoc/actions/runs/37364220044)
is a successful diagnostic job, not a successful candidate qualification.
Its unchanged original netlist passes power-on MBIST and all 28 firmware
checks at cycle 1,596,123. The candidate completes only 24 checks and fails
at cycle 3,000,096. The complete callback histories contain 162,284 and
240,141 events respectively; all 161 settled snapshots in each capture
reconcile with their recorded scalar changes.

## Failure location

The candidate already has 40 unknown sequential outputs when the observation
window opens: refractory bit zero for each of the eight neurons, and four
associated ECC bits per neuron. The original has no unknown sequential
outputs in that selected boundary. The candidate's first newly observed
unknown appears at cycle 1,569,425 when an existing unknown is unmasked;
this event is later than the storage initialization defect.

The original and candidate's exact refractory-bit D-input cones contain
1,480 and 1,483 native combinational cells. Each stops at 628 actual
sequential outputs. The small test applies synthetic inputs at these
boundaries: `STATE_CLR=6`, neuron address zero, and unknown memory data.
The original produces `0`; the candidate produces `X`. With known zero
memory inputs, both produce `0`. These are isolated unit inputs, not a
replacement or forced state in the full SoC simulation. Twenty-one anonymous
boundary names differ between the netlists and are kept distinct.

The failing shared refractory-bit data function is implemented by the
candidate's native NAND3 `_103491_` and O21AI `_103492_` cells:

```text
F = ~((a | b) & ~(a & c & d))
a = _026035_; b = _043474_; c = _032758_; d = _043517_
```

During the failing unit case, `a=X`, `b=0`, and `c=d=1`. The two branches
reconverge as `X & ~X`, so the native gate model cannot establish the
binary-constant result. Factoring this exact function as
`a ? (c & d) : ~b` makes both native mux data inputs equal to one in this
case, allowing the actual IHP mux model to produce one and the downstream
memory D input to become zero.

## Experimental repair and controls

[The source-pinned transformer](../scripts/prepare_npu_reconvergence_eco.py)
replaces only `_103492_` with an inverter, an AND2 and a native mux. The
original NAND3 remains present. A complete inverse comparison preserves
every other source byte, all sequential cells, clock/reset connections and
ports. All 16 binary assignments of the replaced function are equal. This
is intentionally **not universal four-state equivalence**: resolving this
reconvergent unknown is the purpose of the transformation.

[Native controls](../scripts/check_npu_reconvergence_eco.py) apply all 256
four-state input combinations, retain every result and check all originally
defined outputs. An actually miswired mux is rejected by the independent
binary reference. The complete repaired unit cone then produces
`original=0, candidate=X, factored=0` for the failing clear case; both known
memory controls remain zero. An independent review verifies the gate
binding, native mux truth table, exact source inverse and saved executions.
The focused source/boot-boundary suite passes **57 tests, with no skips**.

[The new full-chip runner](../scripts/run_cloud_npu_init_eco.py) preserves
the original preparation and both compiled simulations. It changes only
the selected netlist and compilation output path, checks that every other
input remains identical, and calls the existing strict MBIST/28-check boot
runner. The original three-million-cycle bound and vendor SRAM models remain
unchanged. A failed repaired boot makes the job fail. Passing this boot would
still require physical implementation and fresh final timing before adoption.

## Reproducibility and open work

The [delivery record](evidence/npu-init-reconvergence-20261006.json) binds
the local results, method freeze, independent review and public readback.
The [complete capture](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261005-pcie-continuation/nssoc-npu-init-reconvergence-20261006.tar.xz)
has 538 fully rehashed members and 11,679,096 bytes; SHA-256 is
`6d7fbfec058771392f453c1788001e31972ab084ece4df78c4f2f3fd5db882e0`.
It includes both full input netlists, the actual native model, complete
captured logs, unit designs, methods, failed attempts and component notices.

The first saved-data review classified sequential outputs by the observation
pin rather than by their actual source driver; its zero count is superseded
by `root-write-review02.json`, which follows the complete driver graph and
finds the 40 outputs above. Both review attempts remain in the archive.

Full PHY, qualified SRAM/RC, final whole-chip timing, complete manufacturing
verification and manufacturer approval remain open. This diagnosis does
not change the separate physical failures in
[report 136](136-pcie-loaded-divider-and-write-frontier.md).
