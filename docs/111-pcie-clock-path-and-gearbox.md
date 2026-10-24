# 111 — Native clock-path corrections and four-lane gearbox
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured boundary — 4 October 2026

The GR801-class open-source product remains the objective. This development
step adds a real transistor divide-by-two, corrects its observed cold-corner
clock common mode with native resistors, and implements a four-lane fixed-block
gearbox. It also quantifies why the existing oscillator cannot drive the
prototype bank's long clock routes. **Full Gen3 x4 is still open.** These are
measured components, not a closed PLL/CDR, complete PCS/LTSSM or an operating
serial PCIe connection to the main chip.

The frozen source and compact evidence are at
`aa4834af5602bebcd67169b8af9b370c9a5bd270`. The
[root review](https://github.com/Melihakbulut221/nssoc/blob/aa4834af5602bebcd67169b8af9b370c9a5bd270/hw/soc/pcie-evidence/20261004-clock-path/root-review.json)
checks current source identities and records 85 focused/adjacent Python tests,
seven real gearbox mutations, and three RTL plus three native-cell port cases.
These are different scopes, not a product-coverage percentage. The analog
matrix results below are source-bound author measurements; there is no claim
that a second reviewer reran every native analog case.

## Oscillator headroom and actual bank load

`clock_vco_hbt_v2.spice` changes only the two limiter resistor lengths from
4.4 to 4.0 µm and gives the circuit a separate name. The original circuit and
its previous GDS/LVS evidence remain frozen. The observed minimum passing VCE
improves from 0.399754325 V to **0.443626317 V**, above the unchanged 0.4 V floor.
Nominal oscillation is approximately **8.021223 GHz**, with 0.43630 V peak
differential swing. The selected 72-case campaign has clean numerical startup,
66 of 68 positive screens passing, and four functional faults correctly rejected.
Control 1.20 V now fails the 0.3 V swing screen; control 1.30 V stops oscillation.
The headroom change trades operating range for margin; it is not an all-range pass.

Across 63 control-voltage points in seven selected corners, 48 pass the existing
electrical/clock screens. Only four of seven corners bracket 8 GHz within the
tested 0.60–1.30 V control range. The low-supply, worst-resistor/capacitor case
reaches only about 7.105 GHz at 0.60 V. Coarse tuning and a real feedback loop
remain necessary. A broad 1–20 GHz development screen is not Gen3 frequency
accuracy. The [headroom report](https://github.com/Melihakbulut221/nssoc/blob/aa4834af5602bebcd67169b8af9b370c9a5bd270/hw/soc/pcie-evidence/20261004-clock-path/headroom-summary.json),
[compact native capture](https://github.com/Melihakbulut221/nssoc/blob/aa4834af5602bebcd67169b8af9b370c9a5bd270/hw/soc/pcie-evidence/20261004-clock-path/headroom.tar.xz)
and [full-wave release hashes](https://github.com/Melihakbulut221/nssoc/blob/aa4834af5602bebcd67169b8af9b370c9a5bd270/hw/soc/pcie-evidence/20261004-clock-path/headroom-divider-waves-release.json)
retain the failures and exact method versions.

The bank-v3 capacitance capture identifies clock ground capacitances of
561.285/561.441 fF and incident mutual capacitances of 172.727910/180.919127 fF.
All 1,162 exported capacitance edges are accounted for. Applying collapsed loads
to the **original** native oscillator gives:

| Load per output | Peak differential swing | Unchanged 0.3 V screen |
| --- | --- | --- |
| 50/50 fF reference | about 0.478 V | Pass |
| Ground only, about 0.561 pF | about 0.164 V | Fail |
| Ground plus coupling, about 0.734/0.742 pF | about 0.125 V | Fail |
| Ground plus twice coupling, about 0.907/0.923 pF | about 0.101 V | Fail |

The four runs are numerically clean, and every retained waveform was remeasured
with the frozen producer. Coupling weights one and two are quiet/opposed-aggressor
approximations. This experiment excludes actual aggressor waveforms, route R/L,
substrate/package effects and sampler device loading; **it is not qualified PEX**.
It establishes a concrete need for stronger clock drive or shorter routes.
[Raw measurements](https://github.com/Melihakbulut221/nssoc/blob/aa4834af5602bebcd67169b8af9b370c9a5bd270/hw/soc/pcie-evidence/20261004-clock-path/fanout.json)
and the [public full capture](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/fanout-native.tar.xz)
preserve all four results.

## Real divide-by-two and common-mode correction

`clock_div2_hbt.spice` connects two existing native CML latches as a toggle
prescaler. Its clock comes from the transistor VCO; there is no periodic ideal
clock, behavioral divider, forced initial state or UIC. The first 12-case native
experiment passed nominal, half-step, slow-ramp and 100 fF cases, and rejected
four functional faults. Both cold exploratory cases divided correctly but
violated the 0.4 V transistor floor; both hot cases retained numerical warnings.
Those failures remain in the [v1 capture](https://github.com/Melihakbulut221/nssoc/blob/aa4834af5602bebcd67169b8af9b370c9a5bd270/hw/soc/pcie-evidence/20261004-clock-path/divider-v1.tar.xz).

Using VCO v2 and the verified zero-source/OFF initialization method removes the
four pilot startup diagnostics, but cold minima of 0.385608/0.368227 V still fail.
The separately frozen [v2 pilot](https://github.com/Melihakbulut221/nssoc/blob/aa4834af5602bebcd67169b8af9b370c9a5bd270/hw/soc/pcie-evidence/20261004-clock-path/divider-v2.json)
does not treat numerical convergence as electrical acceptance.

`clock_div2_conditioned_hbt.spice` adds four actual self-heating `rppd` devices:
a series resistor and a pull-up to the 2.5 V divider rail on each differential
clock. Nominal native model readback is 251.741 Ω series and 2,131.6 Ω pull-up.
The resulting common-mode shift fixes the observed cold-corner headroom issue
without changing the latch, compact-model equations or acceptance limits.

**All eight positive cases pass cleanly and all four actual functional faults
are rejected cleanly** in the new finite campaign. All 33 HBTs, 22 resistor
thermal nodes, both raw/conditioned clock swings, resistor currents and power
are observed. Across positive cases, minimum operating VCE is 0.4568465 V,
maximum full-capture VCE is 1.5809008 V and maximum full-capture collector
current per emitter is 1.905448 mA. Native OFF flags are read back for every HBT,
and the solved initial electrical/thermal state is zero.

Nominal input/output frequencies are approximately **8.02286/4.01140 GHz**.
Every output period spans two input periods, and each output transition follows
one successive input rising edge. Halving the timestep changes measured output
frequency by about 0.0229%. This is deterministic numerical consistency, not
phase noise or jitter. The [complete receipt](https://github.com/Melihakbulut221/nssoc/blob/aa4834af5602bebcd67169b8af9b370c9a5bd270/hw/soc/pcie-evidence/20261004-clock-path/divider-conditioned.json),
[compact capture](https://github.com/Melihakbulut221/nssoc/blob/aa4834af5602bebcd67169b8af9b370c9a5bd270/hw/soc/pcie-evidence/20261004-clock-path/divider-conditioned.tar.xz)
and [full-wave release receipt](https://github.com/Melihakbulut221/nssoc/blob/aa4834af5602bebcd67169b8af9b370c9a5bd270/hw/soc/pcie-evidence/20261004-clock-path/divider-conditioned-release.json)
include source pins, all prior failures and measurements. This local-clock
schematic has not inherited the old VCO's layout qualification and has not
been tested as a complete clocked four-lane bank or PLL feedback chain.

## Four-lane fixed-block gearbox

`soc_pcie_gen3_gearbox` implements four simultaneous synchronous lanes in both
directions: 130-bit blocks to 32-bit words and the reverse. Bit zero is first.
Transmit blocks use a common two-bit header across lanes; receive blocks return
each lane's raw header. Independent 160-bit reservoirs preserve partial blocks,
support simultaneous consumption/insertion and hold output under backpressure.
Reset or link flush drops partial data from all lanes together.

The [Intel transceiver handbook](https://www.intel.com/programmable/technical-pdfs/683779.pdf)
describes the 130-bit-block/32-bit-PMA gearbox role. This implementation is a
**fixed-size transport component**. Variable-length SKP, scrambling, framing
tokens, block synchronization, lane deskew, CDC and LTSSM are separate obligations;
no link-up or training result is fabricated.

Three port tests use independent per-lane serial-bit queues, not only a matching
encoder/decoder loopback. They cover randomized stalls, every even block/word
residue, saturated continuous transmit words, lane-distinct data, and reset/flush
inside partial blocks. The same three tests pass after mapping to **9,776 native
IHP cells**. Seven actual RTL mutations—wrong shifts, over-admission, lane mixing,
header reversal and stale flush—are rejected. Native simulation uses a 100 MHz
test clock with library models; it does not prove the physical 250 MHz word rate
needed for 8 GT/s. [Receipt and source pins](https://github.com/Melihakbulut221/nssoc/blob/aa4834af5602bebcd67169b8af9b370c9a5bd270/hw/soc/pcie-evidence/20261004-clock-path/gearbox.json)
and [native/mutation capture](https://github.com/Melihakbulut221/nssoc/blob/aa4834af5602bebcd67169b8af9b370c9a5bd270/hw/soc/pcie-evidence/20261004-clock-path/gearbox.tar.xz)
are preserved. The hosted `pcie-buffered-soc` workflow repeats these checks.

## Extraction and remaining integration

The full-bank resistance attempt remains rejected: missing device terminals,
incomplete signal-network output and incorrect HBT dimensions prevent qualified
device-plus-RC simulation. A separate 24-HBT/eight-orientation fixture proves a
two-line, project-local Magic axis correction for the 18 devices it originally
exported. Six rotated devices, emitter mapping and multiplicity remain open in
that frozen revision. [Axis evidence](https://github.com/Melihakbulut221/nssoc/blob/aa4834af5602bebcd67169b8af9b370c9a5bd270/hw/soc/pcie-evidence/20261004-clock-path/hbt-axis.json)
and [bank failure capture](https://github.com/Melihakbulut221/nssoc/blob/aa4834af5602bebcd67169b8af9b370c9a5bd270/hw/soc/pcie-evidence/20261004-clock-path/bank-extraction-failure.tar.xz)
keep that boundary explicit. Further extractor corrections require separate
native controls; the installed PDK and old captures remain unchanged.

The next closure steps are stronger clock drive under the measured load, tuning
range and cascaded feedback division, actual PLL/CDR, complete SERDES/PCS/LTSSM,
qualified device/route parasitics and ESD, then main-chip clock/reset/CDC/pad
integration with fresh whole-chip verification. Neither these component tests
nor the optional packet connection in [document 110](110-pcie-local-flow-and-clock-layout.md)
close those product requirements.

The next measured output-stage, layout, extraction and scrambling results are in
[document 112](112-pcie-driven-clock-and-scrambling.md).
