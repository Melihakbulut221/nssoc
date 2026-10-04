# 107 — PCIe receive integrity and native analog preamplifier

Later work: [docs/108](108-pcie-packet-and-bank-integration.md) adds transmit
CRC/sequence handling, actual ACK/NAK DLLPs, an RX load-margin revision and
four-lane analog-bank integration. The original sources and results below
remain historical evidence, including their failed load extension.

## Scope — 4 October 2026

The open-source GR801 counterpart remains the product objective. This change
implements two missing receive-side building blocks: a digital packet-integrity
boundary and an SG13G2 transistor-level differential preamplifier. They are
separate development blocks. There is no connection between the analog output
and the byte-stream input: a slicer, clock recovery, deserializer, physical
coding and link training are still required between them. Neither block is
instantiated in `soc_top` or the full-chip layout.

## Digital implementation and interface

[`soc_pcie_crc32_byte.v`](../hw/soc/rtl/pcie/soc_pcie_crc32_byte.v) implements
the reflected CRC-32 byte recurrence (polynomial `EDB88320`).
[`soc_pcie_lcrc_rx.v`](../hw/soc/rtl/pcie/soc_pcie_lcrc_rx.v) buffers a whole
packet and releases its TLP bytes only after a clean, accepted EOP, aligned
bounded length and CRC residue `DEBB20E3`. The CRC seed is `FFFFFFFF`.
[`soc_pcie_tlp_integrity.v`](../hw/soc/rtl/pcie/soc_pcie_tlp_integrity.v)
connects this quarantine through a byte-to-DWORD assembler to the existing
transaction backend. This prevents a corrupt packet from writing APB registers
or changing BAR/memory-enable state before its integrity is known.

The input is a project-local ready/valid byte stream, not PIPE. A frame contains
`{reserved[3:0], sequence[11:8]}`, `sequence[7:0]`, the TLP octets, then four
complemented, low-octet-first LCRC bytes. SOP/EOP delimit this entire frame;
framing symbols are absent. CRC covers both prefix octets and every TLP bit,
including reserved fields. Header octets form numerical DWORDs MSB first;
payload octets put the first byte in APB bits 7:0. Sequence and reserved outputs
are metadata valid at `packet_good_o`; they are not completion-associated tags.

The default bound is eight TLP DWORDs, with a three-DWORD minimum. Physical
error on any received byte, malformed length and excess capacity reject the
packet. Overflow drains to EOP or a new SOP. A new SOP restarts a partial frame;
reset clears buffered state. A paused partial packet requires SOP or reset;
there is no receive timeout. Output remains stable under backpressure.

The classic LCRC coverage and bit mapping were checked against indexed
PCI-SIG Base Specification sections 3.5.2 / Table 3-3, hosted by
[Intel](https://www.intel.com/content/dam/support/us/en/programmable/support-resources/fpga-wiki/asset03/pci-express-base-r2.1.pdf).
Direct PDF retrieval was unavailable during this run; this is not a completed
normative Gen3 compliance review. Independent normal-polynomial, reflected RTL,
literal-vector and `zlib` oracles are engineering cross-checks, not substitutes
for that review.

Sequence acceptance, ACK/NAK, replay, credits, transmission LCRC, DLLPs, ECRC,
full Endpoint capabilities, Root Port behavior, LTSSM and four-lane coding are
not implemented by this change. The existing backend still supports its
documented bounded transaction subset; a CRC-valid unsupported transaction may
be rejected there. The TX side remains its DWORD completion stream. The
single-clock byte interface does not demonstrate sustained Gen3 line rate.

### Executed digital checks

The [port/control receipt](evidence/pcie-integrity-controls-20261004.json) and
[raw control archive](evidence/pcie-integrity-controls-20261004.tar.xz) record
six RTL cases, 13 focused regression tests, 1,824 CRC state/byte vectors and an
unconstrained 40-input-bit combinational CRC relation proved by Yosys SAT.
Changing the polynomial produces a retained counterexample. This proves the
byte recurrence, not the complete packet state machine or PCIe protocol.
The pinned Yosys version required lowering its `$check` representation to an
assertion before SAT; the corrected runner verifies one assertion and no
assumptions. The initial tool failure and both old/new-tool controls are retained.

Port tests cover all 176 single-bit corruptions of a 22-byte frame, every
physical-error byte, byte order, 3DW/4DW headers, configuration/APB effects,
exact capacity versus one extra byte, reserved/sequence prefix values,
backpressure and reset. Three actual RTL mutations—CRC bypass, reversed payload
byte lanes and ignored backpressure—fail those same tests.

An independent [IHP mapping/replay](evidence/pcie-integrity-native-20261004.json)
maps the default wrapper to **3,361 SG13G2 cells**; the same six port cases pass
with zero skips on the unmodified native cell models. Its
[raw archive](evidence/pcie-integrity-native-20261004.tar.gz) contains the mapped
netlist, synthesis/simulation logs and XML, including an earlier Python launcher
failure. That environment selection was corrected before the final fresh run.
`-gspecify` is enabled, but Icarus reports unsupported timing checks; no SDF,
placement, extracted timing or full-chip equivalence is claimed.

```sh
python3 scripts/check_pcie_integrity.py --out /tmp/pcie-integrity-rtl
python3 -m pytest -q sw/tests/test_pcie_integrity.py
python3 scripts/check_pcie_integrity_native.py \
  --out /tmp/pcie-integrity-native \
  --yosys /path/to/yosys --iverilog-dir /path/to/icarus/bin \
  --liberty /path/to/sg13g2_stdcell_typ_1p20V_25C.lib \
  --models /path/to/sg13g2_stdcell.v
```

Use a Python environment containing the pinned `hw/requirements.txt` packages,
Icarus 13 or newer for native delayed inputs, and the exact c4b8b4e5 IHP library
bytes checked by the native driver. `pcie-transaction.yml` now runs these checks
and retains their raw outputs. Hosted execution is a separate result from the
local measurements above.

## Analog circuit and external assumptions

[`rx_hbt_rsil.spice`](../hw/soc/analog/pcie/rx_hbt_rsil.spice) implements a
continuously biased differential pair with a current-mirror tail. All four
HBTs use the native four-terminal `npn13G2` model: reference multiplicity 1,
tail and input pair multiplicity 4. Four native three-terminal self-heating
`rsil` resistors supply split input termination and collector loads. The
substrate terminal is distinct from analog ground.

| Item | Device or explicit testbench assumption |
|---|---|
| Input terminations | Nominal 50 ohm from each input to external VCM; `w=10um`, `l=70.215um` |
| Collector loads | Nominal 150 ohm to AVDD; `w=2um`, `l=41.785um` |
| Supply / reference | Nominal AVDD 1.8 V, external IREF 0.5 mA |
| Input bias | External VCM 1.36 V; the earlier 1.20 V attempt failed the retained 0.4 V tail headroom screen |
| Stimulus | 8 GT/s NRZ sources through explicit 50-ohm source resistances; source amplitude and loaded pad amplitude differ |
| Output design load | 100 fF per pin; larger loads are separate margin experiments |
| Missing circuitry | On-chip bias reference, ESD/pads, channel/package, CTLE/DFE, offset cancellation, clocked slicing and CDR |

The characterizer uses pinned native HBT/resistor model bytes with self-heating
enabled. It retains actual simulator logs and compressed raw waveforms. Finite
transient samples do not erase operating-point initialization warnings.

### Analog results and unresolved limits

The [analog receipt](evidence/pcie-rx-analog-20261004.json) and
[native results](evidence/pcie-rx-analog-native-20261004.json) contain
**96 transient cases**: the 81-way cross product of
three HBT corners, three resistor corners, three temperatures (-40/27/125 C)
and three supplies (1.71/1.80/1.89 V), plus 15 waveform, bias, load, timestep
and fault controls. There are also nine small-signal AC cases. These are
pre-layout device-netlist simulations at the stated external bias/load.

All 81 PVT cases pass the retained waveform/stress screen at 100 fF per
output. The minimum signed differential margin over the sampled 0.3/0.5/0.7 UI
phases is **115.132 mV**, at worst-case HBT/resistor, 125 C, 1.71 V. These
sampled margins are not a BER or PCIe eye-mask measurement. All six deliberate
negative controls are rejected: absent bias, swapped outputs, overload, tiny
input, low common mode and clipping from excess bias.

The 150 fF extension reaches **96.363 mV**, below the unchanged 100 mV
engineering criterion, so the complete campaign status remains
**`FAIL_RX_PREAMP_SCREEN`**. Some hot cases also show native thermal-model
NaN/singular-matrix initialization followed by dynamic-gmin recovery and finite
transients. Alternative starting guesses did not remove those warnings and
were not adopted. No numerical-clean or production-qualification claim follows
from the passing subset. Halving the nominal timestep changes margin by
22.68 microvolt and supply power by roughly 0.000052%; two timesteps do not
establish extrapolated convergence.

At nominal balanced bias, measured differential input impedance is approximately
99.761-j0.0027 ohm at 1 MHz, 97.348-j9.779 ohm at 4 GHz and
93.094-j16.356 ohm at 8 GHz. Loaded differential gain at 4 GHz is approximately
3.334-j1.553. These AC results include compact-model device capacitance, not
extracted routing/pads/package or a qualified return-loss measurement.

The [full raw review](evidence/pcie-rx-analog-full-review-20261004.json)
remeasured all 96 captured waves and nine AC tables and inventoried numerical
warnings in 29 cases. The permanent
18.65 MB capsule ([part 1](evidence/pcie-rx-analog-20261004.tar.gz.part1),
[part 2](evidence/pcie-rx-analog-20261004.tar.gz.part2)) retains all case
logs/decks/metrics, all nine AC tables, and four losslessly compressed waves:
nominal, worst PVT, 150 fF and half timestep. Its
[inventory](evidence/pcie-rx-analog-capsule-20261004.json) identifies the exact
retained bytes. The [retained-wave review](evidence/pcie-rx-analog-retained-review-20261004.json)
can be reproduced from that capsule; the other 92 waves must be regenerated
after the local RAM scratch disappears. The unadopted initializer experiment's
[raw control logs](evidence/pcie-rx-initializer-controls-20261004.tar.gz) remain
available as well.
The [publication split receipt](evidence/pcie-rx-analog-publication-20261004.json)
pins both parts and verifies that their concatenation exactly reproduces the
original archive. This keeps each downloadable asset under the unchanged
16 MiB publication limit.

```sh
python3 scripts/characterize_pcie_rx.py \
  --pdk /path/to/c4b8b4e5/ihp-sg13g2 \
  --ngspice /path/to/ngspice --openvaf /path/to/openvaf \
  --out /dev/shm/nssoc-rx-full-fresh
python3 scripts/review_pcie_rx.py \
  --directory /dev/shm/nssoc-rx-full-fresh \
  --output /dev/shm/nssoc-rx-review-fresh.json
# Or extract the published capsule into a fresh RAM directory:
mkdir /dev/shm/nssoc-rx-replay
cat docs/evidence/pcie-rx-analog-20261004.tar.gz.part1 \
    docs/evidence/pcie-rx-analog-20261004.tar.gz.part2 \
    > /dev/shm/nssoc-rx-replay/capsule.tar.gz
tar -xzf /dev/shm/nssoc-rx-replay/capsule.tar.gz -C /dev/shm/nssoc-rx-replay
python3 scripts/review_pcie_rx.py \
  --directory /dev/shm/nssoc-rx-replay/capture --retained-waves \
  --output /dev/shm/nssoc-rx-retained-fresh.json
```

The producer's nonzero result for the failed load extension is expected and
must not be suppressed or reclassified as a passing campaign. A successful
review means captured evidence agrees with its measurements, not that the
receiver is qualified. The source-bound receipt records the actual ngspice 42,
OpenVAF 23.5.0 and unchanged PDK bytes used locally.

## Physical receiver cell

[`make_pcie_rx_cell.py`](../hw/soc/flow/make_pcie_rx_cell.py) generates actual
IHP PCells, metal/via connections, GDS, LEF and a geometry-derived comparison
schematic for the same fixed analog source. The cell is **167 x 158 um** with
nine accessible Metal5 ports. Its LEF obstructs all seven routing metal layers
except the boundary pin openings. There are four HBTs, four native resistors
and eight explicit square substrate taps. The reference distinguishes SUB
metal from device BULK through those taps; it does not replace the measured
tap areas/perimeters with fitted values.

[`check_pcie_rx_cell.py`](../hw/soc/flow/check_pcie_rx_cell.py) runs the
unmodified upstream IHP main DRC and transistor LVS decks. The new cell has
**zero markers across 560 main-rule categories** and a strict LVS match. Five
real reference faults (termination width, tail multiplicity, missing tap,
wrong input and bulk short) all fail LVS. A deliberately off-grid GDS produces
six DRC markers. OpenROAD reads the real LEF and verifies its dimensions,
ports, directions and obstructions; a missing VCM pin is rejected.

This is an individual preamplifier-cell result. Density, antenna, extracted
RC, EM, statistical matching and analog timing/electrical qualification have
not been established. The analog screens above use the device netlist, not
an extracted netlist of this GDS. A routable abstract is not a characterized
PHY macro, and this work does not repair the separate full-chip I/O tap LVS
issue.

The [physical receipt](evidence/pcie-rx-layout-20261004.json),
[native GDS/LEF/CDL and check capsule](evidence/pcie-rx-layout-20261004.tar.xz)
and [independent read-only review](evidence/pcie-rx-physical-peer-20261004.json)
bind these results to the exact sources. The review rehashes all 201 inputs,
57 native outputs and three generated views, independently rebuilds the
reference/faults and checks the actual LEF obstruction regions.

```sh
python3 hw/soc/flow/prepare_ihp_drc.py
python3 hw/soc/flow/prepare_ihp_lvs.py
hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage python \
  hw/soc/flow/make_pcie_rx_cell.py \
  --pdk /path/to/c4b8b4e5/ihp-sg13g2 --out /dev/shm/nssoc-rx-layout-fresh
python3 hw/soc/flow/check_pcie_rx_cell.py \
  --layout /dev/shm/nssoc-rx-layout-fresh \
  --pdk /path/to/c4b8b4e5/ihp-sg13g2 --out /dev/shm/nssoc-rx-checks-fresh
```

Use the pinned AppImage/PDK identified in the receipt. The two preparation
commands materialize the unchanged locked `5e6d592` verification decks. The
checker limits native child address space to 2 GiB, uses fresh output paths,
and checks source bytes before and after execution. It has no elapsed-time
watchdog.

## Remaining integration work

The next receiver stages are a clocked decision circuit and clock recovery,
followed by deserialization and lane/coding/training logic. Analog bias and
common-mode generation, supply/substrate coupling, extracted RC, channel/ESD
loading, mismatch, noise, jitter, BER and electrical compliance remain open.
The digital link layer must validate sequence/credits and provide replay before
host traffic can be authorized on the SoC fabric. Physical integration then
requires real clock/power/pad constraints and re-verification of the complete
chip. Individual receiver-cell DRC/LVS and gate-model packet tests do not close
the [product acceptance gate](92-product-acceptance.md).
