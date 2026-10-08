# 155 — PCIe ring payload fault isolation
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Result — 8 October 2026

V28 removes combinational parser-fault qualification from the seven ring
payload fields while retaining the existing ownership controller. It improves
slow setup by **112.250 ps** against [V27](154-pcie-frontier-epoch-quarantine.md),
but still fails the unchanged 4 ns target. This candidate is **not accepted for
main-chip integration**. The [retention record](../hw/soc/pcie-evidence/20261008-integrity-v28/retention01.json)
contains source hashes, control counts and the native comparison.

| Liberty corner | Setup worst slack (ns) | Hold worst slack (ns) |
| --- | ---: | ---: |
| Slow | −3.098615 | +0.401006 |
| Typical | −0.479839 | +0.260313 |
| Fast | +1.039268 | +0.176086 |

The screen retains the original clock, three libraries, loads, input delays
and native repair method. It uses ideal clocks before placement, not routed
parasitics. Positive hold here is not final hold closure. Slow setup improves
93.067 ps against V23, but is still negative. Native mapping grows from 93,601
to 96,821 cells; the timing gain is accompanied by 3,220 additional mapped cells.

## Changed circuit and checks

The [generator](../scripts/generate_pcie_integrity_payload_v28.py) pins V27 and
checks an exact inverse of its three source edits. The old pending-command
loop now runs in its own sequential writer, guarded by reset, enable, active
epoch and command validity. It writes data, keep, SOP, EOP, DLLP type, sequence
and packet tag together, preserving lane order and wrap addressing.

On a parser-fault edge, these contents may change while the unchanged control
logic invalidates active, pending-command, descriptor and output ownership.
The new epoch must overwrite all fields before publishing their frontier.
This does not bypass CRC, alter parser results, remove finite-capacity checks
or replace fault handling with a successful status.

The [HDL tests](../sw/tests/test_pcie_gen3_integrity_v28_payload.py) reuse the
unaltered nineteen-case serial-packet oracle and compare public outputs with
V26 over 34,248 cycles. The fixture changes only the candidate module name to
fit the existing runner; actual V28 source and the fixture are both retained.
Fifteen real pending-command fault edges are observed. Eleven actually change
the candidate's ring contents while the reference holds them. The observer
checks all seven fields of every slot against the saved pending command,
checks that the reference contents do not change, and verifies ownership
cancellation. There is no forcing of internal RTL state.

All seven host predicates pass: generator inversion, the nineteen-scenario
positive campaign and five deliberate mutations. The mutations bypass pending
data, drop byte masks, advance the write address, lose packet tags or suppress
the final payload command. Each is rejected by an actual named HDL assertion;
compilation failure is not accepted as detection. These are nested finite
checks, not additive product coverage or an all-state proof. MAX4118, complete
mapped functional equivalence and serial PHY qualification remain separate.

## Physical boundary and retention

The import proof checks all 352,373 mapped cell-pin bits, 24 ports and six
deliberate graph faults. All six native stages complete. The [new worst path](../hw/soc/pcie-evidence/20261008-integrity-v28/slow-critical-path.txt)
is `framer.remaining[4]` to `framer.output_keep[0]`: parser-fault qualification
still reaches output payload control. Further repair must preserve same-edge
accepted data, stalled output behavior and fault/restart quarantine.

The [113-member raw capsule](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261006-pcie-closure/pcie-integrity-v28-payload-20261008.tar.gz)
retains controls, sources, methods and all three native RAM work directories.
It is 30,039,649 bytes, SHA256
`afa31dbc77cc7ce3673418b882212f6772d176ef319cb2adff822dcbccdd5fbb`.
Every member has been replayed locally; the full anonymous public download also matches the byte count and SHA256. Root review is recorded explicitly;
there is no external independent review claim.

Full PLL/CDR/SERDES, PCS/LTSSM/controller operation, qualified RC and actual
serial PHY placement/routing into the main chip remain open. No chip GDS or
host-link acceptance is produced by this experiment. Interface integration
and its necessary dependencies remain the active priority.
