# Nominal routed core setup/hold result — 2026-11-19

## Verified result, scope and source

Fresh RC/STA run [44459123476](https://github.com/Melihakbulut221/nssoc/actions/runs/44459123476), head fd1630e82067aef73a85976449fb1cdec3030fbc, attempt 1, completed successfully. Artifact 14499837022 SHA256 a6ec8a0379054fabe7db001e5d1e3e9cdb0fd83d0f51c09f9baf123d655c79dc; all 134 manifest outputs verified. Each of the three `violator_list.rpt` files is empty of violations. These are fresh extracted results, not the historical `pre_route_corners` estimates retained in result.json.

| Cell corner | Setup violations | Setup worst slack (ns) | Hold violations | Hold worst slack (ns) | Slew | Fanout | Capacitance |
|---|---:|---:|---:|---:|---:|---:|---:|
| slow 1.08 V / 125 C | 0 | +0.021101343492022327 | 0 | +0.4491127596936628 | 502 | 210 | 52 |
| typical 1.20 V / 25 C | 0 | +7.419697954935824 | 0 | +0.1855848860450402 | 4 | 210 | 54 |
| fast 1.32 V / -40 C | 0 | +10.30343484139742 | 0 | +0.037160608975109796 | 0 | 210 | 60 |

Setup and hold TNS/WNS are zero in all three corners. Original 20 ns (50 MHz) and 5 percent derating remain; no timing exceptions or electrical bounds were relaxed. Slow setup improved from 19 violations / -0.19486635079340425 ns to zero / +0.021101343492022327 ns. Fast hold margin is unchanged, about 37 ps. These small margins must be protected through subsequent ECOs and cannot substitute for qualified min/max RC or complete chip signoff.

Physical source is run 44455684595, head b32fce23eb5cb79a1e9d9dbafcd023d6f4663e7d, routed ODB f381bd8d9e79ca38918d4bbda5c4014959a0e6966ac9a130d4ea9274d6a5192e. Native DRC and antenna nets/pins are zero; independent decoded wire/via/terminal geometry found zero inter-net contacts or disconnected nets. All 2113 clock records and 103079 unaffected non-power DEF records were preserved. The two common setup drivers were sized; six explicitly allowed data nets, including a proven shorting neighbor, were rerouted. Earlier five-net candidate 44452163259 was rejected for a real Metal2 contact despite native DRC zero.

Nominal SPEF SHA256 506a2e1c77670c6d69a944def37eb2ac36944502693b0251aa1b68abdad9044a contains 102969 nets. Per-net capacitance accounting has zero inconsistent nets. Source-bound annotation diagnosis reports 1403 unannotated drivers = 1288 disconnected outputs + 115 connected outputs with no sinks; partially unannotated drivers, missing native loads, unresolved load names and loaded unannotated drivers are zero. This diagnosis is not proof of complete interface or functional timing coverage. Do not change `accepted`, `final_timing_complete`, `qualified_rc_minmax`, `annotation_qualified` or `manufacturing_approval` to true on this evidence.

## Next work

Preserve this clean nominal setup/hold baseline. Close electrical violations with routed, antenna-aware ECOs and remeasure all corners after every admitted candidate. Prior exact connectivity inventory mapped 100 slew-violating nets, 210 fanout nets (all exceeding eight only after antenna diode loading; two are clocks) and 60 capacitance nets including nine SRAM outputs. See the separately verified electrical classification branch/tag `cloud-core-electrical-classification-20261119`, commit 5a29ec0ca2924d9467c39b0c4d5385cdde95abca, run 44454324152, artifact 14496404437 SHA256 ce08617f93fa768d52d5d92d5e53d981e2096b3a14da3ece4da8e45f7dac2cfd. That inventory predates the two setup resizes; current fresh counts are unchanged but any new ECO must bind to this new routed ODB.

Start with worst slew drivers nssoc_sta_i_55577 and nssoc_sta_i_54413 (nor4_1; nor4_2 exists), checking their current inputs and local geometry. For SRAM outputs, use local load isolation or shorter routes while retaining the macro max-cap limit. For fanout, solve diode loading and antenna protection together; no arbitrary diode removal, fanout waiver or clock-tree changes without hold/skew proof.

Production goal remains open: electrical closure, qualified RC corners/coverage, SRAM characterization, updated core in parent-chip hierarchy and final timing, transistor SRAM/I/O/full-chip LVS, foundry DRC, DFT/PDN/ESD/package/board and manufacturer approval. Package, PCB, QSPI model and attached devices are not selected; external timing remains unverified. PCIe/Ethernet are excluded by the approved scope. No tapeout or manufacturing approval is claimed.
