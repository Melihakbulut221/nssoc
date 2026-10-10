# 135 — NPU write-frontier capture and callback correction
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Result — 5 October 2026

The two jobs in [run 37187157260](https://github.com/Melihakbulut221/nssoc/actions/runs/37187157260)
finished with a postprocessing failure. Their original receipts remain failed.
The actual original-design boot passed **28 checks** at cycle 1,596,123;
the timing candidate failed after **24 checks** at cycle 3,000,096. Neither
candidate adoption nor final whole-chip timing is accepted.

The EVQ monitor records a callback from its continuously assigned `watched`
vector, while each old event's `all` field reads the current live vector.
Reconvergent activity within one simulator time can change the live vector
before the callback runs. Requiring the two scalar values to match was an
incorrect parser assumption. A native buffer/XOR circuit reproduces this
case without modifying or forcing the observed design.

The corrected parser preserves the scalar prior/new chain and requires it to
match **every settled sample**. It records live-vector disagreements separately:
18 in the original capture and six in the candidate. Both complete chains
reconcile at all 161 samples. This is a review of recorded callback history,
not proof that every internal simulator delta was captured. Both downloaded
artifact ZIPs match GitHub's SHA-256 metadata; all **228 members** match their
extracted bytes and source/result inventories.

The candidate's first newly observed unknown is now located at cycle
**1,569,426**, at the EVQ output FIFO's write-pointer bit-zero D input.
The preceding capture's boundary did not include the three upstream state
outputs `sync_push`, `u_lif.u_op_a.bits`, and `u_lif.op_b`. This locates a
measurement boundary; it does not yet establish the original cause.

## Next paired native measurement

The new source-bound diagnostic includes the complete combinational
predecessors of the write-pointer input and those three state registers'
D/clock/reset inputs, stopping at actual sequential boundaries. Native
clock-gate and reset interfaces retain their real ports.

| Frozen netlist | Selected cells | Observed scalars | Sequential boundaries |
| --- | ---: | ---: | ---: |
| Original | 2,048 | 7,040 | 625 |
| Candidate | 2,041 | 7,033 | 625 |

Each conductor is identified from the exact native port map, with native
sequential internal fields retained. Sparse event records contain only the
changed scalar and its prior value; initialization and settled samples retain
complete vectors. This avoids copying a 7,000-bit live vector into every event
and removes the false atomic-snapshot interpretation.

The 3,000,000-cycle workload, firmware, vendor memories, reset, cell models,
and both full synthesized netlists remain unchanged. No state forcing,
substitute storage model, timing exception or adopted RTL repair is introduced.
The new [workflow](../.github/workflows/timing-npu-write-trace.yml) preserves
startup and final artifacts for both variants, including failed boots.

Before dispatch, **115 focused tests** passed, five native cell/observer
controls retained their original output trajectories, and an independent source
review checked both complete native netlists and rejected twelve copied-binding
faults. The [startup evidence](evidence/npu-write-frontier-startup-20261005.json)
pins sources, exact input artifacts, measurements and review receipts. These
preflight results do not claim a completed new full-chip run.

PCIe physical work continues separately in [report 134](134-pcie-divider-wire-and-rx13-timing.md).
The complete PHY, qualified RC and final whole-chip timing remain open.

The complete frozen failed captures and this startup are now included in the
[public delivery in report 136](136-pcie-loaded-divider-and-write-frontier.md).
