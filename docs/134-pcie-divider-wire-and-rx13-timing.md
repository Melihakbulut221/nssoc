# 134 — Divider wire extraction and RX13 routed timing
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Result — 5 October 2026

The divider's actual layout now has a checked wire RC network. RX13 also
completes detailed routing with zero router DRC and improves its slow-corner
setup slack by 80.198 ps. **RX setup still fails; these results do not close
the complete PCIe PHY or whole-chip timing.**

| Nominal RC with cell corner | Setup, ns | Hold, ns | Recovery, ns | Removal, ns |
| --- | ---: | ---: | ---: | ---: |
| Slow | **−0.441603** | +0.021680 | +0.423293 | +0.837033 |
| Typical | +1.223677 | +0.052567 | +1.712991 | +0.556355 |
| Fast | +2.179489 | +0.071704 | +2.494802 | +0.391889 |

The RX clock remains 4 ns. Slow setup was −0.521801 ns in RX12; slow hold
was +0.035180 ns, so this improvement also reduces hold margin by 13.500 ps.
The next repair must preserve that remaining margin. These are three cell
corners with nominal extracted RC, not a qualified RC-corner signoff.

## RX13 implementation and checks

Six buffer isolations and four cell upsizes target RX12's measured critical
paths. The fresh router preserves the proved candidate netlist and reports
zero router DRC. The saved binary comparison covers 1,804 state elements and
5,443 combinational targets, with ten actual fault controls and six native
port cases. No completed simulation or routing was repeated for packaging.

The [saved RX13 review](../hw/soc/pcie-evidence/20261005-divider-wire-and-rx13-timing/records/pcie-gen3-receive-prefetch-v2-20261004/repair13-peer/review.json)
retains the actual timing paths and extraction accounting. SPEF contains
21,252 nets, 800,317 capacitor entries and 113,565 resistor entries, with no
zero-valued resistors. The 78 unannotated outputs are verified unconnected
CTS load outputs; their clock inputs are present in the extracted nets.
No partially annotated nets are reported. The maximum slew/capacitance
report is empty. None of these observations replaces full-chip DRC/LVS.

## Divider geometry and wire RC

The saved unsimplified layout extraction retains all **91 physical devices**
and 283 device terminals: 198 metal terminals and 85 body/well terminals.
The latter retain their original identities and remain outside the wire-only
resistance model. Native extraction has 38 electrical clusters and 34
auxiliary clusters; each auxiliary cluster is explicitly checked to contain
no device terminal, conductor or public pin. The simplified LVS device count
of 74 from [report 131](131-pcie-divider-layout-and-tx-repair.md) is not used
to discard physical taps here.

The actual Magic extraction produces **312 resistors and 618 capacitors**.
All 205 probes—198 metal terminals and seven public ports—connect into the
expected 37 resistor networks. The source, baseline and exported collapsed
capacitance matrices agree across all 306 nonzero edges of the 38 × 38 matrix.
Each native resistor value and each point/mutual capacitance attachment is
also checked. Intrinsic aliases are never inserted as resistor edges to hide
opens. A separate [root readback](../hw/soc/pcie-evidence/20261005-divider-wire-and-rx13-timing/records/pcie-divider-v7-wire-rc-v1-20261005/root-saved-rc-peer.json)
reconstructs the graph and capacitance accounting without importing the
producer or its graph library.

Four copied-input binding faults and thirteen raw RC corruption controls
are detected. The first RC control harness expected an edge-multiset error
after deleting the first resistor. In this layout that resistor connects the
clock port to its only terminal, so the stricter connectivity check rejects
the open earlier. The initial failed harness is retained. An independently
reviewed V2 changes only that expected diagnostic and the result filename;
the saved native extraction and positive auditor remain unchanged.

The wire RC result is not yet a loaded divider simulation, an RF parasitic
qualification, substrate resistance extraction, PVT qualification or main-chip
integration. The next analog experiment connects this measured wire network
to the original divider devices and loaded VCO while preserving body nets.

## Captures and remaining work

The [delivery inventory](../hw/soc/pcie-evidence/20261005-divider-wire-and-rx13-timing/delivery-inventory.json)
binds four complete public capsules, eight authenticated/anonymous-verified
assets and **484 fully rehashed archive members**. Compact records retain the
V1–V5 geometry failures, first RC harness failure, strict correction, source
reviews and raw timing evidence. The RX publication's interrupted anonymous
transfer and successful bounded retry are both preserved.

This delivery contains closed evidence; it does not adopt a new full PHY.
RX14, V19, the large-packet extension, TX routing and the interrupted PLL run
have separate active records and are not counted as passing here. Remaining
work includes RX setup, full integrity-path timing, loaded analog RC checks,
qualified extraction and whole-chip production verification.
