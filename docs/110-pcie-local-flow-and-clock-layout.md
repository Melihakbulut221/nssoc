# 110 — PCIe local flow control, CPU integration and native clock layouts
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured boundary — 4 October 2026

The GR801-class open-source product remains the objective. This record closes
specific development gaps in local receive-buffer ownership, transmitted flow
control, the SoC packet connection, clocked receiver geometry and a bounded
analog startup protocol. **It does not close full PCIe Gen3 x4.** PLL/CDR,
complete SERDES/PCS/LTSSM, the serial-to-packet clock crossing, qualified analog
parasitics/ESD and main-chip physical integration remain open.

The frozen source and native captures are at commit
`f2d235180dbb35c260716d54d4f3f151a577d92e`. Its
[root verification receipt](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/root-checks.json) records 162 focused tests and
67 adjacent/core guards; these groups overlap and are not added into a
product-coverage total. Native component simulations are separately recorded.
The new `pcie-buffered-soc` workflow repeats local credits and APB arbitration
in RTL/native IHP cells, plus an independently prepared real-CPU packet test.
A workflow definition or pending run is not a successful result.

## Local receive capacity and transmitted FC

`soc_pcie_rx_credit` owns two dedicated slots for each admitted posted and
non-posted class. The development default holds up to eight TLP DWORDs
(38 encoded sequence/TLP/LCRC bytes). Arrival order is retained across TLPs;
a separate six-byte DLLP slot can bypass a stalled transaction consumer.
The local header/data advertisements derive from actual storage. A slot
returns cumulative credit only after a newly accepted packet has consumed it
and the slot is released. Corrupt, duplicate and future-sequence traffic
cannot manufacture credits.

`soc_pcie_fc_tx` emits actual CRC-protected InitFC1, InitFC2 and UpdateFC
messages. Initialization depends on transmitted handshakes and peer progress;
it is not tied high. Packet-level arbitration holds a whole FC/DLLP/TLP frame
through output stalls. The peer may confirm initialization by sending a TLP
once the local InitFC2 triplet has actually been transmitted, avoiding a
circular prerequisite between receive acceptance and transmit initialization.

The combined endpoint is completer-only: requester admission is structurally
zero and no outbound non-posted requests or outstanding requester tags exist.
Completion credits are advertised as infinite in this profile; unexpected
incoming completions request recovery before reaching APB. The standalone
queue also tests finite completion storage, which is not an endpoint claim.
The classic VC0 rules and primary references are retained in the
[source-bound receipt](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/rx-flow.json).

**13 RTL and the same 13 native-cell cases pass**, including 2,050-packet
header/data rollover, actual initialization and output stalls. Ten executable
RTL faults are rejected. The native FC transmitter, generic queue and combined
wrapper respectively contain 805, 10,889 and 21,634 IHP cells. The
[complete compact capsule](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/rx-flow.tar.xz) and
[independent source/raw-result review](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/rx-flow-peer.json) preserve the evidence.
This does not establish the mandatory 128-byte PCIe maximum-payload capability,
line-rate timing, every transaction-ordering rule or a complete controller.
The current register backend handles one-DWORD transactions; local timers
remain explicitly cycle-based development values.

## Actual CPU and PCIe packet integration

`SOC_PCIE_PACKET` adds an optional, same-clock byte-packet profile to
`soc_top`. BAR0 maps only the existing GPIO slot, at CPU address `0xFF902000`.
A two-master APB arbiter shares that real peripheral path with the Ibex CPU.
It captures a request, issues a fresh SETUP, and preserves ownership through
ACCESS/wait cycles. Responses go only to the granted master. Completed
transactions change round-robin preference; a waiting master is not starved.

Review found a concrete interaction with the existing timeout bridge: a CPU
request parked in ACCESS after timeout could be captured again after a late
slave response. Per-master completion guards now require deselection or a
new SETUP before recapture. Normal continuous-PSEL, back-to-back APB accesses
still rearm correctly. Withdrawal and reset cannot leave a stale access.
GPIO has word writes, so a partial PCIe write is rejected before selecting the
peripheral. A posted write has no fabricated completion; the packet path
reports its backend error pulse.

The arbiter passes **six RTL and six 385-cell native cases**, with seven
actual source faults rejected. Its [receipt](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/apb-arbiter.json) and
[capsule](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/apb-arbiter.tar.xz) include the late-response regression.
The CPU fixture executes a real RV32I ROM program, with the default hardened
register file/memory and clock gates. No internal CPU net or register is
forced. CPU GPIO-bit-zero toggles continue while the packet peer initializes,
programs BAR0 and issues memory accesses. One test observes **817 CPU
transactions, 16 PCIe transactions, 39 contention cycles and 408 GPIO edges**.
A second verifies partial-write containment, wrong-BAR rejection, a truncated
packet at link loss, reinitialization and system reset. Both pass; deliberately
wrong slot decode and ignored byte enables are caught by the same fixture.
[Source, logs and receipt](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/soc-integration.json) and the
[full compact capture](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/soc-integration.tar.xz) retain these results.

With the optional macro absent, actual Icarus preprocessing produces the same
Verilog tokens as the preceding `a83e7bf` SoC. This preserves the default RTL
configuration; it is not a new whole-chip timing result. The optional packet
ports are not package pads and are not an on-chip PHY or PCIe host link.
The existing `nssoc_chip` physical assembly does not yet contain this profile.

## Native oscillator, sampler geometry and clocked bank

The new original `clock_vco_hbt.spice` circuit is a voltage-controlled,
three-stage differential CML oscillator. It uses **18 native HBTs, one HV PMOS,
nine self-heating resistors and six MIM capacitors**. A fixed 12.2×12 µm versus
12×12 µm MIM asymmetry initiates oscillation during the supply ramp. There is
no periodic ideal clock, behavioral gain/delay, forced initial condition or
UIC. A transistor limiter and emitter followers drive the clock output.

At the measured nominal 2.3 V supply, 0.85 V control and 50 fF per output,
it oscillates at **8.017758666 GHz**, with approximately ±0.478 V differential
swing and 1.243 V common mode. The half-timestep frequency change is 0.0228%.
This deterministic transient comparison is not phase-noise or random-jitter
characterization. The original 72-case campaign contains startup warnings in
nine hot cases and two physical screen failures. All original waves and
methods remain in the [299,407,360-byte native release asset](https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/pcie-vco-native-full-20261004.tar);
[authenticated and anonymous download hashes](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/vco-original-release.json)
match the local archive.

A separate startup-only revision preserves every circuit, ramp, model and
measurement threshold. It uses the documented native HBT OFF initialization
flag at a solved zero-source operating point, then applies the original ramps.
All 72 native initializations are clean; **66 of 68 positive screens pass** and
all four deliberate functional faults are rejected. The two physical limits
remain: control 1.30 V stops oscillation, and the hot HBT-BCS/MOS-SS corner has
minimum XBN VCE **0.399754325 V**, below the unchanged 0.4 V floor. The
[receipt](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/vco-startup.json), [summary](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/vco-startup-summary.json),
[complete compact capture](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/vco-startup.tar.xz) and
[two retained full waveforms](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/vco-startup-waves.tar.xz) preserve the separation
between numerical startup and physical operating range. Subsequent circuit
changes require a new version and new physical evidence.

The frozen sampler circuit now has native GDS/LEF and strict transistor LVS.
Four receive preamplifier outputs are connected to four samplers by eight
actual metal routes in bank v2. Bank v3 additionally connects both VCO clock
outputs to every sampler through eight actual clock branches, while retaining
independent 1.8 V, 2.5 V and 2.3 V supply rails and explicit substrate/well taps.

| Physical artifact | Main DRC | Strict LVS | Size / boundary |
| --- | --- | --- | --- |
| Sampler cell | 0 markers / 560 categories | 28 combined devices, 10 ports | 880×267.03 µm |
| Four-lane sampler bank v2 | 0 / 560 | 165 combined devices, 60 ports; deep and flat | 1070×2640 µm |
| VCO macro | 0 / 560 | 36 combined devices, 6 ports; deep and flat | 1400×277.03 µm |
| Clocked bank v3 | 0 / 560 | 200 combined devices, 54 ports; deep and flat | 1650×3000 µm |

Finite tap devices are retained; there is no global-net short or ignored-device
waiver. The physical reference explicitly represents the substrate and PMOS
well tap, instead of silently identifying them with supply metal. Ten sampler,
eleven bank-v2, twelve VCO and thirteen bank-v3 negative controls exercise
real geometry/reference errors, including clock opens/shorts and rail bridges.
Native OpenROAD LEF checks verify the actual pin and obstruction boundaries.
[Sampler/bank evidence](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/sampler-bank.json), [VCO evidence](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/vco-layout.json),
[clocked-bank evidence](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/clocked-bank.json) and its
[actual KLayout rendering](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/clocked-bank.png) retain the exact definitions.

These are separate development macros. Their long prototype routes and clock
fanout have not passed a post-layout 8 GT/s waveform test. DRC/LVS establishes
geometry/connectivity within the supplied deck, not RF performance. The older
padded bank remains a separate artifact: this clocked bank has not acquired
its pad/ESD ring or been placed into the complete SoC. Qualified resistance,
coupling, substrate/package effects, jitter, BER and ESD stress remain required.

## Bounded receiver/sampler startup protocol

A separate source-controlled native startup method uses all-zero independent
sources, no powered-state nodeset, and the actual per-HBT OFF initial-guess
flag. It solves zero-source OP and then ramps supply, bias, common-mode,
clock and data sources together. The flag is checked through native device
SHOW output; it does not disable transistor conduction during transient.
This preserves the original receiver and sampler circuit descriptions.

**81 receiver and 81 receiver-plus-sampler PVT cases pass** the unchanged
functional limits with clean numerical/model diagnostics. Six nominal/cold/hot
cross-version cases also pass on ngspice42/47. Worst sampler startup margin is
115.959 mV. A separate settled-bias experiment inserts 124 zero-volt terminal
ammeters whose contraction recovers the original circuits exactly. All 29-node
KCL residuals are below 2.4 fA in both native versions, against a 1 nA bound;
measured tail currents show active devices. The [summary](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/startup-summary.json),
[full method/capture](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/startup.tar.xz) and [independent review](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/startup-peer.json)
retain actual OP, current probes and fault dispositions.

The compact package covers **179 native executions**. Fifteen complete retained
waveforms were independently remeasured; three partial waveforms from failed
powered-start commands are preserved but not accepted as full transients.
Eighteen wave files are retained in the three
[public, hash-verified waveform archives](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/startup-waves-release.json).
The remaining matrix metrics are source-bound producer measurements, not a
claim of independently replaying every waveform. Default junction guesses and
OFF with fully powered sources reproduce failures; no-bias and swapped-output
faults fail the unchanged functional checks despite clean startup.

The new 1 ns startup begins from zero thermal state. The older fully powered
DC initialization preheated the compact models. Their short-transient margins
therefore represent different physical startup histories, not solver-equivalent
steady-state waveforms. The separate KCL experiment uses a slower 100 ns ramp
and 1 µs settling. This method closes the tested cold-start numerical protocol;
it does not fix arbitrary model initialization or implement an on-chip power
sequencer, reference/bias generator or startup controller.

## Reproduction and remaining closure

```sh
# Python 3.12/3.13 plus prepared pinned processor/interface RTL:
make soc-rtl-prepare
python3 scripts/check_pcie_soc.py --out /dev/shm/pcie-soc-fresh \
  --iverilog-dir /path/to/icarus/bin
python3 scripts/check_pcie_rx_flow.py --out /dev/shm/pcie-local-fresh
python3 scripts/check_pcie_apb_arbiter.py --out /dev/shm/pcie-arbiter-fresh
# Native options require the exact pinned IHP Liberty and Verilog cell models.
```

The individual receipts include exact native commands, source/PDK/runtime
hashes, model libraries, failures and scope exclusions. Captures are linked
directly from the frozen Git commit or external release to preserve the site's
existing 16 MiB per-asset and 96 MiB total publication budgets. Component
licences and model-source attribution are in [NOTICES](https://github.com/Melihakbulut221/nssoc/blob/f2d235180dbb35c260716d54d4f3f151a577d92e/hw/soc/pcie-evidence/20261004-integration/NOTICES.txt).

Next acceptance work is actual PLL/CDR feedback and recovered-clock operation;
full-speed serialization/deserialization and Gen3 PCS/LTSSM; complete negotiated
transaction capability and timing; real bias/power sequencing; qualified
coupled RC and post-layout lane/fanout validation; pad/ESD and main-chip
assembly with whole-chip timing, DRC and transistor LVS. None is marked closed
by the separate packet tests or macro connectivity results above.
