# 129 — PCIe loaded feedback and routed RX timing
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Verified continuation — 5 October 2026

The physical VCO wire model now drives an actual transistor divider and
feedback counter. Both nominal control endpoints pass the finite electrical
and division checks. A separate two-resistor revision increases the measured
minimum VCE by approximately 33 mV. RX11 detailed routing and extracted
nominal timing have also been recovered and independently reviewed after
shutdown. **RX setup still fails, the disconnected-clock electrical screen
still fails, and complete PCIe Gen3 x4/main-chip integration remains open.**

The [delivery inventory](../hw/soc/pcie-evidence/20261005-loaded-feedback-and-rx-timing/delivery-inventory.json)
pins 41 frozen engineering source files, compact evidence and immutable public
assets. Its [capsule audit](../hw/soc/pcie-evidence/20261005-loaded-feedback-and-rx-timing/delivery-audit/pcie-phase20-delivery-20261005/archive-audit.json)
rehashes every member of every declared capsule against retained authenticated
and anonymous download receipts. Completed DUT simulations are not repeated
by this packaging audit. [Report 128](128-pcie-packet-identity-and-vco-tuning.md)
remains an unchanged historical result.

## Real divider loading and observed feedback

The composed probe contains 437 device records: the 62-record physical VCO,
73-device HBT divider and 302-device CMOS feedback section. The 64 HBT native
OFF flags are read back. The VCO retains its 889-resistor/765-capacitor wire
model and 50 fF load on each public clock pin, now with the actual divider
input load. The divider and CMOS counter remain schematic models; their
parasitics and layouts are not inferred from the VCO layout.

Both fixed-control probes run for 34 ns with a 5 ps maximum timestep at
27 °C. They use the same zero-source operating-point procedure and strict
numerical diagnostics. There is no ideal internal clock. Each nominal
capture has 6,818 rows and 786 columns: 5,358,948 native values.

| Original loaded circuit | VCO frequency | Feedback frequency | Complete signed 300 mV cycles | Minimum settled HBT VCE |
| --- | ---: | ---: | ---: | ---: |
| Control 0.60 V | 8.103256196 GHz | 101.258936 MHz | 242 | 0.425827 V |
| Control 0.85 V | 7.601285705 GHz | 94.997325 MHz | 227 | 0.406109 V |

The [finite result](../hw/soc/pcie-evidence/20261005-loaded-feedback-and-rx-timing/loaded-vco/pcie-vco-v6-feedback-v1-20261005/finite-ready.json)
retains the actual edge counts through /4 and /80, all 437 device screens,
original waveforms and independent reductions. The latter import none of the
producer's measurement functions. They check all binary values, device bounds,
native flags, frequencies and complete cycles. The prior bare-VCO probe used
12 ns/1 ps; the frequency difference between that probe and this one cannot
be attributed solely to loading.

Two actual faults are distinguished from capture errors:

- The original disconnected-clock capture lost an observed public node and
  ended with an observer error. V2 explicitly retains that observation without
  changing the circuit. A fresh complete native capture then fails 11 functional
  checks and two HBT headroom checks. Its minimum VCE is 0.305671 V; it is not
  counted as an electrically healthy negative control.
- The actual counter modification produces /64 instead of /80, while all
  437 electrical screens pass. The wrong-modulus fault is correctly accepted
  as a detected functional fault; its native functional FAIL remains recorded.

The four independent waveform reviews cover 21,452,298 values in total.
The portable source/observation controls use tracked, byte-identical fixtures;
they do not require a developer's private RAM paths. The original observer
failure, initial independent archive-selection mistake and interrupted
publication are preserved alongside their separate corrections.

## Two real resistor dimensions increase nominal headroom

The next probe changes only the first divider conditioner's two upward-bias
`rppd` lengths from 8 to 6.4 µm, with width 1 µm unchanged. Exact inverse
source checks reconstruct all predecessor SPICE files. Flattened device
comparisons retain all 437 identities and change only those two length fields.
The measurement code, supplies, loads, wire model, windows and thresholds are
unchanged. Eleven source controls and a separate source review precede the
native measurements.

| Matched 34 ns/5 ps capture | L8 minimum VCE | L6.4 minimum VCE | Change | L6.4 result |
| --- | ---: | ---: | ---: | --- |
| Nominal 0.85 V | 0.406109 V | 0.439333 V | +33.224 mV | All 437 screens and /4, /80 checks pass |
| Nominal 0.60 V | 0.425827 V | 0.458475 V | +32.647 mV | All 437 screens and /4, /80 checks pass |
| Disconnected clock, 0.60 V | 0.305671 V | 0.343411 V | +37.740 mV | Two headroom screens and 11 functional checks still fail |

The [paired evidence](../hw/soc/pcie-evidence/20261005-loaded-feedback-and-rx-timing/bias-vco/pcie-vco-v6-feedback-bias-v1-20261005/paired-comparison.json)
binds both actual graphs and numeric profiles. New nominal frequencies are
7.601418303 GHz at 0.85 V and 8.103334867 GHz at 0.60 V. Peak recorded HBT
current at 0.60 V is 2.771520 mA/Nx, below the unchanged 3 mA/Nx development
screen. Three independent full-wave reviews accompany the
[finite result](../hw/soc/pcie-evidence/20261005-loaded-feedback-and-rx-timing/bias-vco/pcie-vco-v6-feedback-bias-v1-20261005/finite-ready.json).

The nominal margin improves; the disconnected-clock problem remains. The
0.4 V requirement is a declared development speed/headroom screen, not a
foundry safe-operating-area limit or evidence of physical damage. No exact
8 GHz operating point, PLL lock, PVT, thermal, jitter or RF extraction
qualification follows from these nominal short captures. The revised
divider dimensions still require their own physical layout and verification.

## RX11 routing survives shutdown; setup still needs repair

The route and RC jobs completed before shutdown. Their continuation stopped
because the independent reviewer referenced the previous RX10 candidate.
An additive correction selects RX11; the corresponding packaging path is
also corrected. The original failed review and controller remain immutable.
No completed routing, extraction, proof or simulator run was repeated to
repair that review-path defect.

The [saved-output review](../hw/soc/pcie-evidence/20261005-loaded-feedback-and-rx-timing/rx11/repair11-peer02/review.json)
confirms zero router DRC violations, byte-identical logical netlists and the
unchanged 4 ns clock/I/O constraints. The SPEF contains 21,238 nets, 802,415
capacitor entries and 113,529 resistor entries. All 78 reported unannotated
outputs are unconnected outputs of input-only CTS load cells; each associated
clock input is independently located on its correct extracted clock net.
There are zero partially unannotated drivers.

Slow-corner nominal setup is **−0.610481 ns**, improving by 0.085567 ns over
RX10; hold is **+0.030615 ns**. Reported slew/capacitance violations are zero.
The same nominal RC model is reused across three cell corners; these are not
three independent RC process corners. The retained binary proof covers 1,804
states/5,443 functions, ten actual kernel faults and six native port cases.
Original interpreter-path warnings remain in the captures. This evidence is
for the standalone byte receiver, not full-chip timing or a complete wide PCS.

## Rejected parser timing candidates remain recorded

Three separate experiments preserve the V11 baseline rather than replacing
it with an unmeasured improvement claim. Every row uses the original 4 ns
preplacement profile; none is routed signoff.

| Candidate | Mapped cells | SS setup | TT setup | FF setup |
| --- | ---: | ---: | ---: | ---: |
| V11, retained baseline | 83,778 | −3.552011 ns | −0.758690 ns | +0.856405 ns |
| V12, separate slot writers | 81,312 | −4.037508 ns | −1.078218 ns | +0.635542 ns |
| V13, quarantined speculative slot writes | 82,042 | −4.204973 ns | −1.189897 ns | +0.560291 ns |
| V14, constant-slot read selection | 86,186 | −8.255548 ns | −3.739168 ns | −1.067630 ns |

The finite receipts retain the
[V12](../hw/soc/pcie-evidence/20261005-loaded-feedback-and-rx-timing/integrity-v12/pcie-integrity-v12-20261005/ready-finite.json),
[V13](../hw/soc/pcie-evidence/20261005-loaded-feedback-and-rx-timing/integrity-v13/pcie-integrity-v13-20261005/ready-finite.json)
and [V14](../hw/soc/pcie-evidence/20261005-loaded-feedback-and-rx-timing/integrity-v14/pcie-integrity-v14-20261005/ready-finite.json)
source controls, actual RTL mutations, 13 direct cases and 13 public-cycle
comparisons per experiment. These overlapping counts are not summed as unique
tests. The V13 observer originally sampled an overflow indication too late;
its failed capture and separate observer-only correction are retained.

V14 maps to a 56-stage Boolean chain on its critical path. Independent literal
counterexamples also show that OR-combining selected payloads changes `Z` into
`X` in six fields. Its bounded binary/selected-X tests remain valid, but they
do not establish arbitrary four-state equivalence or prove those injected
states reachable in the whole DUT. All three candidates are rejected as timing
improvements; V11 itself still fails slow and typical setup.

## Recovery, CI and next physical work

After the actual power loss, all three agent checkpoints and the root RAM
archive rehashed successfully. Forty-eight frozen source pins matched, and
36 then-uncommitted sources were separately backed up. Completed results were
restored; the interrupted TX route restarted in a fresh directory. A new RX12
repair has its own candidate proof and port tests, followed by fresh routing.
Neither running route is counted as a completed result in this report.

The restarted long PLL capture had terminated before shutdown on an actual
GitHub TLS download failure. Its partial waveform and failed publication are
preserved. Reliable bounded publication is being repaired separately before
a fresh 1 µs capture; there is still no completed timestep-pair/lock result.

The GitHub `checks` job installed software requirements but omitted the pinned
cocotb hardware runtime. A bounded reproduction confirms that the Makefile
fallback repeatedly invokes itself when `cocotb-config` is absent. The workflow
now installs both requirement sets and checks the pinned runtime before the
suite. The old cancelled run also reported stale tracked-path licence counts;
the inventory is regenerated with this delivery. Local preparation checks do
not stand in for a completed new GitHub suite.

Final setup/hold/RC qualification, physical clocks and CDC, full SERDES/CDR/PLL,
LTSSM/training and controller policies, analog pads/ESD, main-chip integration,
SRAM/DFT obligations and actual manufacturing acceptance remain open.
