# 157 — PCIe fault timing improvement and native verification recovery
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured results — 8 October 2026

Two interface prerequisites advance: V30 improves receiver preplacement setup
by **481.175 ps** against [V28](155-pcie-payload-epoch-quarantine.md), and a
separate native verification driver completes the twelve V1 packet scenarios
whose previous GitHub job ended during mapping. **The unchanged 4 ns target
still fails. Complete PHY and main-chip integration remain open.**

| V30 Liberty corner | Setup worst slack (ns) | Hold worst slack (ns) |
| --- | ---: | ---: |
| Slow | −2.617440 | +0.401006 |
| Typical | −0.163554 | +0.260411 |
| Fast | +1.227998 | +0.176192 |

V30 branches from V28; it does not adopt the
[rejected V29](156-pcie-output-transfer-timing-rejection.md) output writer.
The same original 4 ns clock, libraries, loads, input delays, mapping method
and preplacement repair are used. CPU affinity changes from core 6 to core 7
to isolate the two local experiments; both retain one core and the same
2 GiB address-space limit. There is no elapsed-time kill of healthy native work.
These are ideal-clock, wire-load estimates, not routed or qualified-RC timing.

## Balanced fault accumulation

The [generator](../scripts/generate_pcie_integrity_fault_v30.py) hash-pins V28
and verifies the exact inverse of four edits. The parser previously accumulated
one sticky fault flag across four DWORDs. Each word now sets its own flag under
the unchanged procedural guards; a balanced OR combines them. Every flag starts
at literal zero and can only be assigned literal one. CRC decisions, parser
state, fault timing, packet contents, ownership and external handshakes are
unchanged. No failure condition is removed or delayed.

The [serial campaign](../sw/tests/test_pcie_gen3_integrity_v30_fault.py) passes
all nineteen unchanged independent packet scenarios and 34,248 public-cycle
comparisons with the V26 reference. The new read-only observer compares 28,006
active pre-edge parser decisions, including sixteen actual token faults. That
traffic covers fault-word mask `0x7`; it does not by itself cover the fourth
word. Three deliberate faulty reductions are rejected by a named HDL assertion.

A separate [direct block-port campaign](../sw/tests/test_pcie_gen3_integrity_v30_fault_positions.py)
places an invalid token at each of the sixteen DWORD positions in a real
512-bit input block. All sixteen fault edges pass the V28/V30 public comparison
and the expected one-word flag check, covering all four parser words (`0xf`).
A mutation that suppresses fourth-word faults is rejected. No internal state
is forced. There are seven host predicates in total, including generator
inversion and the four rejected mutations. This is finite coverage of the
150-byte profile, not MAX4118 or complete mapped/all-state equivalence.

Native mapping produces 96,821 cells, the same count as V28. The complete
import comparison checks 352,383 pin bits, 24 ports and six deliberately
incorrect graphs. All six native stages finish. The remaining worst path is
`framer.remaining[4]` to `framer.commit_ptr[6]`. Slow and typical setup are still
negative, so V30 is not accepted for main-chip integration. See the
[timing and retention record](../hw/soc/pcie-evidence/20261008-balanced-fault/retention01.json).

## Recovery of the timed-out native V1 verification

[GitHub run 37678369906](https://github.com/Melihakbulut221/nssoc/actions/runs/37678369906)
completed fourteen jobs but cancelled the integrity V1 job after approximately
six hours. Its complete 529,385-byte artifact ZIP has SHA256
`72480551ec0d31257c0ff9ba464ba179c7a827c37ebcb7e5241755d6bfd77aa9`.
The recovered RTL result has twelve passing scenarios. The native result is
still `RUNNING`, with neither `mapped.v` nor `mapped.json`; it is not a native
pass. The last retained map-log stage is ABC extraction. Buffered output does
not identify which inner ABC operation consumed the remaining time, and no
specific deadlock is inferred. The
[recovery review](../hw/soc/pcie-evidence/20261008-native-integrity-recovery/prior-recovery-review01.json)
verifies every ZIP member and binds the old source/model hashes.

The additive [native V2 driver](../scripts/check_pcie_gen3_continuous_rx_integrity_native_v2.py)
keeps the original RTL, twelve-case oracle, strict IHP models, simulator-version
guard, no-FSM synthesis, memory limit and failure checks. Five reversible edits
introduce and pin the explicit ABC recipe
`strash; balance -x; &get -n; &nf; &put`. The historical driver is unchanged.
Only the integrity V1 component selects this new driver in the workflow; all
other components, mutation checks and the maximum RTL profile remain present.

The local mapped result contains **71,028 IHP cells**. All **twelve native
packet scenarios pass with zero failures or skips**, with 925.89 seconds of
simulation wall time reported by cocotb. Separately, twenty-seven original
RTL mutation and independent polynomial predicates pass. Two full positive
profile tests were deselected from that additional control run; the native
run is the 150-byte profile and does not claim a maximum-size native result.
The [retention record](../hw/soc/pcie-evidence/20261008-native-integrity-recovery/retention01.json)
contains the exact bounded result. Different local/cloud hosts and tool
builds prevent treating these durations as a controlled speedup benchmark.

The OSS simulator wrapper sets `PYTHONEXECUTABLE` to `tabbypy3`. Cocotb records
an unexpected-executable-name diagnostic while loading Python 3.12.4 and
successfully completing all twelve scenarios. That original diagnostic is
retained; this is not a claim of a diagnostic-free runtime. The workflow is
parsed, its exact three-line change is inverted, and all fourteen shell
blocks pass `bash -n`. Actionlint is unavailable locally; no actionlint pass
is claimed. Existing healthy cloud jobs were neither cancelled nor duplicated.
The new workflow still requires confirmation on its future exact source head.

## Raw evidence and integration limit

Both raw capsules retain sources, failures, methods and complete local native
outputs. Every archive member is verified locally, and full anonymous public
downloads match both archives byte-for-byte by SHA256. External tools and PDKs
are pinned, not bundled, except the unmodified IHP libraries inside the
original recovered GitHub ZIP, whose licence notices are preserved.

| Capsule | Bytes | Members | SHA256 |
| --- | ---: | ---: | --- |
| [V30 fault timing](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/pcie-integrity-v30-fault-20261008.tar.gz) | 29,432,068 | 105 | `054bf30dc7ab147a6f2b675b7af836eed1f4236154a47a237853159835e4eb18` |
| [V1 native recovery](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/pcie-integrity-v1-native-recovery-20261008.tar.gz) | 36,197,313 | 293 | `7f9020c5a5a08d0a665bca8814fda41787dc9fac90b042acaba4f3b828be2184` |

Review is performed by the root agent, without an external independent-review
claim. Neither experiment produces a new main-chip GDS. PLL/CDR, complete
SERDES/PCS/LTSSM, qualified parasitics and analog pads, actual serial PHY
connection and chip-level physical verification remain open. Interface
integration and its necessary dependencies remain the active priority.
