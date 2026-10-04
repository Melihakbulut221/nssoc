# 120 — PCIe feedback loop, wide receive and compact VCO
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured development — 4 October 2026

A real transistor feedback chain now connects the VCO, divide-by-four stage,
divide-by-twenty stage and phase detector. The first short closed-loop simulation
passes its finite device checks after a separately recorded measurement correction.
A four-DWORD receive path also passes native-cell simulation. The smaller VCO
has actual DRC/LVS-checked geometry with four separate W=8 µm control devices.

**Full Gen3 x4, PLL lock/CDR, complete SERDES/PCS/LTSSM, qualified parasitics/ESD,
main-chip physical integration and production approval remain open.** Routing,
CRC-capable native synthesis and further analog experiments continue separately.

Source commit `af2b6fa3a0f9f4de3e0e5add84b92e3900eef7b2` contains the
[root verification record](https://github.com/Melihakbulut221/nssoc/blob/af2b6fa3a0f9f4de3e0e5add84b92e3900eef7b2/hw/soc/pcie-evidence/20261004-loop-and-wide-rx/root-verification.json):
**181 distinct focused pytest checks passed, zero failed, zero skipped** in five
root-run groups. Other native cases, independent waveform reviews and the agent's
17 portable/27 integrity controls are separate evidence, not additional unique
root pytest cases. [Document 119](119-pcie-registered-paths-and-physical-power.md)
retains the preceding source-bound snapshot and its original failures.

## Real feedback and finite startup

The first CMOS divide-by-twenty implementation exceeded the 1.5 V development
terminal screen during midstream reset. The separate v2 circuit adds 21 actual
2 × 2 µm MIM capacitors while retaining the original 281 devices. Its 302-device
native campaign passes seven positive cases and rejects three actual circuit
faults. An independent reset-wave review remeasures all 4,749 samples and
302-device bounds, including a 1.458687 V maximum low-voltage terminal magnitude
and exactly 20 incoming CML rises per complete feedback period. These are finite
nominal results; the output duty cycle is approximately 18%.
The [feedback receipt](https://github.com/Melihakbulut221/nssoc/blob/af2b6fa3a0f9f4de3e0e5add84b92e3900eef7b2/hw/soc/pcie-evidence/20261004-loop-and-wide-rx/feedback-v2.json)
and [independent raw review](https://github.com/Melihakbulut221/nssoc/blob/af2b6fa3a0f9f4de3e0e5add84b92e3900eef7b2/hw/soc/pcie-evidence/20261004-loop-and-wide-rx/feedback-v2-root-peer.json)
bind the sources and preserved full waveforms.

A 424-device prerequisite then connects the actual VCO v4, HBT divide-by-four
and CMOS divide-by-twenty. It produces 8.002960 GHz and 100.048 MHz with exactly
80 VCO rises in both complete feedback periods. Two loaded phase-detector tests
establish the physical feedback polarity for the VCO's negative tuning gain.
The connected 539-device circuit uses real polysilicon bias resistors and a
10 × 10 µm MIM filter; it contains no ideal internal divider, detector or
control-voltage clamp.

The first 34 ns connected capture retains an original failed current-observer
result. Its PMOS model reports positive channel-current magnitude; the original
observer incorrectly negated it. A separate v2 analysis establishes the corrected
sign against independent native clamp-current measurements, then replays all
5,693,618 values of the unchanged full capture. Six actual-wave observation
faults are rejected. This is a measurement correction, not a second native run.

The short feedback remains **97.803459 MHz**, so it does not establish 100 MHz
lock. Phase lead contracts from 2.613 to 2.384 ns, and VCTRL spans approximately
0.813–1.102 V. The maximum HBT current is **2.998103 mA/Nx**, only **1.897 µA/Nx**
below the unchanged 3 mA development screen. Longer acquisition, timestep
convergence, PVT, thermal settling and jitter remain necessary. The
[loop record](https://github.com/Melihakbulut221/nssoc/blob/af2b6fa3a0f9f4de3e0e5add84b92e3900eef7b2/hw/soc/pcie-evidence/20261004-loop-and-wide-rx/loop-startup.json)
and [public archive receipt](https://github.com/Melihakbulut221/nssoc/blob/af2b6fa3a0f9f4de3e0e5add84b92e3900eef7b2/hw/soc/pcie-evidence/20261004-loop-and-wide-rx/loop-startup-release.json)
preserve all four native experiments, 45 lossless public waveform parts and the
original failed interpretation.

## Wide receive and packet integrity

The new framing path accepts continuous fixed Data Blocks and processes four
DWORD steps per clock. Two packet banks quarantine incomplete packets; the
128-bit output carries byte-valid, SOP/EOP, DLLP and per-DWORD sequence metadata.
Extended ring tags prevent a wrapped packet from releasing stale metadata.
The frozen framing version retains encoded bytes and does not check CRC.

At the 150-byte native profile it maps to **57,611 IHP cells** and passes all
nine native cases. The 4,118-byte profile is RTL-tested only. An independent
serial byte oracle checks 855 blocks, 38,246 emitted bytes, 1,025 good packets
and 175 nullified packets; an actual payload-XOR fault is rejected. Ring-tag
bounds are separately checked at both capacities. The first over-rate stimulus
failure, costly automatic FSM extraction and failed Python simulator startup
remain archived. A corrected, explicitly pinned native runtime reuses the exact
mapped netlist. Its 17 portable controls run both complete RTL profiles and
15 actual HDL faults. See the [native record](https://github.com/Melihakbulut221/nssoc/blob/af2b6fa3a0f9f4de3e0e5add84b92e3900eef7b2/hw/soc/pcie-evidence/20261004-loop-and-wide-rx/wide-native.json)
and [independent peer](https://github.com/Melihakbulut221/nssoc/blob/af2b6fa3a0f9f4de3e0e5add84b92e3900eef7b2/hw/soc/pcie-evidence/20261004-loop-and-wide-rx/wide-root-peer.json).
A packaging-only [inventory reconciliation](https://github.com/Melihakbulut221/nssoc/blob/af2b6fa3a0f9f4de3e0e5add84b92e3900eef7b2/hw/soc/pcie-evidence/20261004-loop-and-wide-rx/wide-rtl-final-inventory.json)
binds all 311 final RTL archive members without changing the earlier manifest.

A separate integrity v1 implementation adds parallel LCRC32 and DLLP CRC16
before packet commitment. Normal TLPs, deliberately inverted LCRC plus EDB,
and invalid CRCs receive distinct outcomes. Two complete 12-case RTL profiles
and 25 actual HDL mutations pass their expected checks. Polynomial equations
and 596 vectors have independent checks, including three PCI-SIG DLLP examples.
An initial DLLP residue literal error is retained with its failed trace.
[Integrity evidence](https://github.com/Melihakbulut221/nssoc/blob/af2b6fa3a0f9f4de3e0e5add84b92e3900eef7b2/hw/soc/pcie-evidence/20261004-loop-and-wide-rx/integrity-rtl.json)
is RTL-only at this snapshot: native synthesis is running. Neither path yet
provides complete variable SKP/ordered-set handling, lane deskew, CDC, LTSSM or
the sustained receive-credit/replay connection to the main chip.

CI includes both wide paths and the revised byte receiver. The matrix uses the
same explicit Python runtime location and a 360-minute job ceiling. Local
healthy native jobs have no elapsed-time watchdog. Unsupported Icarus timing
checks and the OSS Python-wrapper diagnostic remain recorded; these passes do
not establish SDF timing or clean simulator logs.

## Receiver physical timing

The separate prefetch v2 byte receiver removes redundant reset qualification
inside already reset-qualified sequential branches and uses a registered next
read position. Its complete public-port miter passes at six capacities, including
4,118 bytes. It maps to 14,540 cells and passes six native cases. After placement
and global routing, an actual buffer on the long read-shift wire improves setup.
The exact repaired netlist matches all **1,804 states and 5,443 Boolean
functions**, rejects ten proof controls and passes the six physical port tests.

| Cell corner | Setup, ns | Data hold, ns | Recovery, ns | Removal, ns |
| --- | ---: | ---: | ---: | ---: |
| SS | +0.124792 | +0.043483 | +1.015921 | +0.652267 |
| TT | +1.580431 | +0.082205 | +2.052392 | +0.463175 |
| FF | +2.288765 | +0.115465 | +2.681026 | +0.353743 |

These are **global-route estimates** at the unchanged 4 ns clock, 0.2 ns I/O
delay, 0.1 ns input slew and 0.01 pF output load. Detailed RX and TX v4 routing
continue; fresh extraction is required afterward. The older negative extracted
slacks remain failures. The [prefetch receipt](https://github.com/Melihakbulut221/nssoc/blob/af2b6fa3a0f9f4de3e0e5add84b92e3900eef7b2/hw/soc/pcie-evidence/20261004-loop-and-wide-rx/prefetch-v2.json)
binds the physical proof and archive. A subsequent test-only PATH discovery
change is explicitly separated from the frozen archive and rechecked with all
nine miter controls.

## Physical supply, compact VCO and thermal limits

Replaying the original 351-device bank with the repaired supply metal raises
minimum HBT VCE from 7.744 to 156.627 mV and reduces bound failures from 19 to
8. Representative native 1 mA path measurements improve from 71.660 to 17.558 Ω
at a sampler return and from 112.073 to 15.767 Ω at the VCO return. Nevertheless,
the full wired bank still has **zero clock crossings in the 2–4 ns window**.
Its remaining failure cannot be closed by the DRC/LVS result alone. An
[independent full-wave review](https://github.com/Melihakbulut221/nssoc/blob/af2b6fa3a0f9f4de3e0e5add84b92e3900eef7b2/hw/soc/pcie-evidence/20261004-loop-and-wide-rx/powered-overlay-root-peer.json)
rechecks both captures, all 122 HBT bounds and 49 native DC paths.

The separate VCO v4 layout is **760 × 407.03 µm** and contains all **62 native
devices**, including four separate W=8 µm PMOS, 12 finite substrate taps and one
finite N-well tap. It has zero violations across 560 main DRC categories,
strict unsimplified deep and flat LVS matches, six LEF pins, all routing-layer
obstructions and 19 rejected geometry/reference/LEF faults. The first real
supply/control short and checker false negative are preserved. Its
[geometry record](https://github.com/Melihakbulut221/nssoc/blob/af2b6fa3a0f9f4de3e0e5add84b92e3900eef7b2/hw/soc/pcie-evidence/20261004-loop-and-wide-rx/compact-vco.json)
is not yet a powered post-layout or main-chip result.

Eight odd-grid native fixtures additionally validate the area-product patch.
Promoting the multiplication changes a 3 × 3 / 2 area from integer 4 to 4.5;
resistance and source capacitance remain bound, while distribution and floating
roundoff changes are explicitly retained in the [supplement](https://github.com/Melihakbulut221/nssoc/blob/af2b6fa3a0f9f4de3e0e5add84b92e3900eef7b2/hw/soc/pcie-evidence/20261004-loop-and-wide-rx/odd-area-results.json).
This is extractor validation, not qualified RF/substrate parasitics.

Both 1 µs thermal captures are now preserved in 62 lossless public parts. The
limited mean/envelope screen passes with frequencies 7.702927 and 7.703253 GHz,
a 42.3027 ppm difference. An independent trajectory review rehashes 614 inputs,
134 outputs and all 62 publication receipts, and recomputes the stored-node
gates. It does not remeasure the complete 3.2 GB compressed raw waveform set.
The [thermal record](https://github.com/Melihakbulut221/nssoc/blob/af2b6fa3a0f9f4de3e0e5add84b92e3900eef7b2/hw/soc/pcie-evidence/20261004-loop-and-wide-rx/long-thermal-pair.json)
retains the original endpoint failures and incomplete v2 outcome. These captures
still use the earlier W=32 µm model-range-limited VCO; they do not qualify v4,
8 GHz lock or production thermal behavior.
