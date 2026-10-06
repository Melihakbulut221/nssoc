# 142 — Matched chip placement and routed receiver repair
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured result — 6 October 2026

Both original and repaired NPU netlists complete fresh placement, clock-tree
synthesis and global routing locally. The repaired input reduces violating
endpoint counts but worsens the worst setup path. **Neither result closes
chip timing.** Separately, the RX16one receiver finishes detailed routing with
zero router DRC violations and improves its extracted slow-corner setup by
101.025 ps; its unchanged 4 ns target remains unmet.

These results follow the [successful strict repaired boot](141-pcie-capacitor-layout-and-repaired-boot.md).
The [delivery inventory](../hw/soc/pcie-evidence/20261006-chip-placement-and-routed-rx/delivery-inventory.json)
binds the completed experiments, independent reviews, preserved failures and
public archives. Ongoing post-route repairs and analog experiments are not
accepted results in this record.

## SRAM template import fixed without changing physical constraints

The first local placement attempt stops at the strict DEF-template reader.
Its command contains the technology, standard-cell and I/O LEFs but omits
the two SRAM LEFs already configured in the design. The raw log records 32
unknown SRAM-master references: sixteen of each macro type.

The [narrow command adapter](../hw/soc/pnr/npu_eco_template_lefs.py) adds only
those two LEFs. It preserves the complete template and strict matching.
An actual OpenROAD control imports the same template successfully; independent
replay parses both raw DEF files and the native geometry tables, verifying
all **32 SRAM placements, 301 signal pin boxes**, die/core bounds and DBU.
The failing attempt is retained. The terminal `control.json` is authoritative;
intermediate `execute()` snapshots that still say RUNNING remain unmodified.

The [physical flow](../hw/soc/pnr/npu_eco_physical_flow.py) then applies the
same correction to both fresh netlist-only arms. Both retain the original
configuration, core 20 ns clock, Ethernet clock constraints, all three cell
corners and fixed macro/pin geometry. The earlier failed candidate's proof
and boot guards remain unchanged.

## Fresh global-route comparison: fewer violations, worse worst setup

| Metric | Original | Factored repair |
| --- | ---: | ---: |
| Worst setup slack | −16.372498 ns | −18.724608 ns |
| Setup violating endpoints | 1,476 | 1,334 |
| Worst hold slack | −2.482277 ns | −2.263391 ns |
| Hold violating endpoints | 6,415 | 6,200 |
| Slew violations | 436 | 512 |
| Capacitance violations | 186 | 168 |
| Instances | 89,764 | 90,179 |

The worst setup path regresses by 2.352110 ns while hold improves by 218.885 ps.
The raw maximum/minimum reports also retain asynchronous recovery/removal
groups. The complete endpoint census contains 20,138 original and 20,163
factored endpoints; unrepresented or unconstrained paths are not counted as
passing timing checks.

This is a new matched experiment, not a replacement for the older repaired
C10 timing frontier. Its inherited fresh-placement recipe omits post-CTS
timing repair and stops at global routing plus a fresh audit. The standard
post-GRT electrical and setup/hold repair stages are subsequent work. SRAM
timing is still black-boxed where qualified macro Liberty is unavailable;
these standard-cell measurements cannot establish full-chip timing closure.

Both native arms return successfully and rehash their input files. The final
Python comparison then encounters a serialized string passed to a Path-only
file hasher. The [runner correction](../scripts/run_npu_eco_physical.py)
converts that input to `Path`; two regression controls use real saved JSON
and file hashing, including rejection of a changed boot file. All **70
focused physical/control tests pass**.

An additive recovery imports the exact captured producer and normalizes only
the hasher's path argument. It reruns the complete saved-data comparison,
including prerequisites, method copies, raw timing and geometry, without
repeating physical work. Independent review rehashes all 460 arm outputs and
recounts the two complete endpoint populations. The original failed
controller record is preserved; the recovered comparison is separate.

The [complete physical archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261005-pcie-continuation/nssoc-npu-eco-fresh-physical-pair02-20261006.tar.xz)
retains 700 members, including the failed predecessor and native template
control. It is 158,525,968 bytes with SHA-256
`0b763a478c1f7a94a9803836dd53351e38199bed0a35bc0617f3513fab40fc2a`.

## RX16one: actual routed improvement, remaining setup failure

The receiver repair completes detailed routing and fresh nominal wire-RC
extraction. The final router reports zero DRC violations; this is not a
foundry rule-deck or full-chip DRC signoff. The result has no reported maximum
slew or capacitance violations.

| Cell corner, nominal RC | Setup | Hold | Recovery | Removal |
| --- | ---: | ---: | ---: | ---: |
| Slow | −0.301453 ns | +0.060995 ns | +0.292329 ns | +0.960725 ns |
| Typical | +1.302556 ns | +0.086321 ns | +1.614447 ns | +0.649433 ns |
| Fast | +2.196354 ns | +0.110991 ns | +2.417492 ns | +0.465347 ns |

The previous RX14a slow setup was −0.402478 ns. The measured gain survives
actual routing and RC extraction, but the new slow result still fails the
same 4 ns constraint. All four timing classes are reported separately.

The complete binary proof covers 1,804 state bits and 5,443 functions, with
ten actual negative controls and six native public-port cases. Independent
saved-result review checks all 110 archive members, 36 real timing paths,
the complete SPEF values and 78 CTS input bindings. The later independent
review is included additively in Git; it does not replace the earlier public
archive. All three immutable release assets have authenticated and anonymous
readbacks.

The [complete routed receiver archive](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20261005-pcie-continuation/pcie-rx-repair16one-route-nominal-rc-and-peer-20261006.tar.xz)
is 35,857,152 bytes with SHA-256
`d9370e2e06307bfd6b7966a5e0baa294bb1c43402bb5a427ee8bee3f2938f3bb`.
This remains a standalone receiver experiment using nominal RC. Neither its
proof nor zero router DRC grants qualified process-RC, complete PHY or chip
integration acceptance.

## Next physical work

The factored chip's completed views provide the parent for standard post-GRT
electrical and timing repair under the unchanged configuration. New results
must preserve fixed geometry, recheck complete timing/electrical data and
prove the exported physical netlist's function before adoption. The routed
receiver's remaining setup paths require another bounded repair. Full PHY,
qualified SRAM/RC, final setup/hold, complete chip DRC/LVS and manufacturer
approval remain open.
