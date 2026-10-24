# 150 — Loaded PLL observation capture passes bounded controls
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured result — 6 October 2026

The connected 570-instance PLL experiment initially failed while setting up
waveform observations: the simulator rejected one oversized `save` command.
The corrected driver emits nine smaller commands and retains the complete
observation list. **49 current capture, storage, lifecycle and native-command
controls pass.** A separate source-composition campaign passes twelve checks.
These results establish bounded capture behavior, not a functioning or locked
570-instance PLL.

The [delivery inventory](../hw/soc/pcie-evidence/20261006-loaded-pll-observation-controls/delivery-inventory.json)
binds the frozen methods, failed captures, corrected controls, independent
reviews and public archive. Active source-03 tuning outputs and mutable
journals are excluded. No later completion is inferred from this snapshot.

## Circuit composition and observation failure

The circuit combines the earlier **455-instance loaded oscillator/divider
chain** with **115 schematic instances**: 102 in the phase/frequency detector,
ten in the charge pump and three in the loop filter. Within the existing
455, 62 oscillator and 91 divider instances have the recorded physical-model
correspondence; the remaining 302 implement schematic feedback. This mixed
composition is not a complete extracted PLL layout.

Both loop-polarity variants are preserved. The source-composition checks
contain two positive cases and ten deliberate graph changes; all twelve
give their expected result. They do not select a polarity or establish a
tuning range.

The first intended 34 ns capture reports `save: too many args.` and remains
an error. Its consumed 65,596-byte header and preceding sources are retained.
The saved upstream ngspice 47 source identifies a 1,000-argument command
limit. The corrected driver divides the unchanged 1,133 requested observations
into **nine save commands: eight groups of 128 and one of 109**. Time supplies
the additional column, giving 1,134 columns in the native raw table.

## What the passing controls establish

| Current control group | Passing cases | Recorded scope |
| --- | ---: | --- |
| Finite capture | 11 | Complete finite rows and declared observation shape; malformed and non-finite captures rejected |
| Storage | 23 | Short writes, header/trailer checks, capacity and free-space failure handling |
| Process lifecycle | 7 | Owned child execution and normal, error and signal cleanup |
| Native command and observation checks | 8 | Save-command batching, complete ordered variable table and deliberate header faults |
| **Current total** | **49** | Source-composition checks are counted separately |

The positive native command control runs for **2 ps and produces 19 rows**.
It checks the complete observation census, the declared startup operating
point and 64 startup OFF flags. Missing, duplicated or reordered observations
are rejected, and the retained original native failure is checked as a negative
control without rerunning the oversized command. This short startup experiment does **not** prove the intended 34 ns
tuning behavior, settled electrical limits, division, pump response or lock.

The 49-case total combines the exact retained finite, storage and lifecycle
controls with the eight native command checks. Historical failed tests and
source corrections remain visible; they are not relabelled as clean passes.
Two initial independent-reader attempts also remain: one assumed the wrong
archive-member convention, and one expected a nonexistent summary field.
The corrected reader checks the saved evidence without rerunning simulation.

## Finite delivery and remaining limits

The immutable public capsule contains **380 members**. Independent review
rehashes 841 bound paths, streams every archive member and verifies five
completed publication transports, including complete authenticated and
anonymous readbacks. Compact text records are copied into Git; binary
fixtures and upstream source remain accessible through exact member/hash
mappings to the public capsule. Upstream ngspice copyright and licence texts
remain intact in that capsule and are not relicensed as project code.

Capture retention covers bytes already received by the reader. The gzip file
is synchronized at close; this is not a power-loss durability or resumable
solver-checkpoint guarantee. The longer clamped-voltage experiments have
separate results and are outside this finite packet.

The [455-instance divider result](147-pcie-loaded-divider-numerical-agreement.md)
retains its own finite scope. The connected circuit still needs measured
tuning sign and range, pump reachability, selected feedback polarity,
closed-loop acquisition, numerical and PVT checks, and complete physical
integration. Formal verification of the complete PHY, CDR, protocol/link
behavior and final chip acceptance remain open.
