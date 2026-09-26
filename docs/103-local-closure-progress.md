# 103 — Local closure progress, 26 September 2026
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

This continuation implements and checks the next work identified by
[the product audit](102-remaining-product-gaps.md). No final product or foundry
acceptance is recorded. Every receipt identifies the source and measurement scope.

## Prepared source regression

The [complete pytest replay](evidence/prepared-pytest-bb5ddb1-20260926.json)
checks source `bb5ddb1` in a fresh local clone with pinned Ibex/TinyTapeout
dependencies. All **1,707 cases pass with zero failures and zero skips** in
375.78 seconds. All 1,669 previous testcase identities remain present; 38
new cases cover status, analog measurement and release-asset validation.
The fourteen previously skipped fixture cases all execute successfully.
The original unpublished intermediate controller count error is retained
in the archive and is separate from this successful final-source replay.
Publication after this source commit changes only documentation, records
and ignore/licence metadata; running physical/formal jobs retain their own
source identities. This does not replace their acceptance requirements.

## Current RTL and native memory replay

The [audited local replay](evidence/local-rtl-regression-1baeb63-20260926.json)
runs source `1baeb635453dccc8b122c0fc40ff3ee1613159a1` in a separate local
checkout, with unchanged tracked inputs and the explicit `full` interface
profile. The canonical cocotb discovery reports **508 passed, zero failures**.
Its 46 XML files contain sixteen actual skips:

* Twelve select encoder versus decoder DUTs. Each skipped case passes under
  the other DUT configuration.
* Three select appropriate one-bit versus wider TMR test configurations.
  Each skipped case passes at an applicable width.
* One tests disabled optional interfaces and applies only to `base`.
  The complementary base replay passes eight cases, including this one.
  Its six full-only skips all pass in the full replay.

The runner's seventeenth skip delegates native SRAM parity to a separate tool
environment. That driver subsequently passes all six profiles: 8,192-word
plain/ECC RAM and 16,384-word plain RAM, each with registered/unregistered reads.
The deliberately corrupted macro fails the functional comparison as required.
These results do not qualify replacement SRAM transistor timing or ROM contents.
The earlier fourteen pytest skips are a separate, already completed campaign.

The archive contains full logs, XML, input identities and audit code. The one
untracked `hw/soc/ext` symlink in the test checkout is recorded; it supplies
prepared dependencies. No tracked RTL/test source was altered. Frozen pilot
FI/gl/glfi reruns remain excluded by the canonical discovery and are not counted
as passes. Whole-core RVFI and final netlist/timing verification remain open.

## SRAM and status records

The [DP timestep comparison](evidence/sram-repaired-dp-timestep-20260926.json)
publishes the completed 25 ps waveform, forty transition comparisons, two
rejected measurement faults and retained failed initial attempts. The largest
delay difference from 50 ps is 0.020866732 ns. This closes the unpublished-result
item, with no extrapolated signoff or complete-characterization claim.

The status generator now accepts the newer complete pytest receipt and exact
32-SRAM geometry receipt. Its guards reject failed/incomplete counts, wrong
source/GDS identities and unsupported timing/manufacturing promotion. The old
physical timing row is explicitly historical. A fresh 170-task mandatory formal
sweep is running locally; the older published sweep is not relabeled current.

## Native resistor TX

`tx_cml_rsil.spice` and `tx_bank4_rsil.spice` replace the experimental TX's ideal
loads with native three-terminal IHP `rsil` devices, including self-heating.
Each load uses a 10 µm by 70.215 µm resistor body. The external predriver,
reference current, termination and illustrative PDN remain ideal stimuli.
`characterize_pcie_tx_rsil.py` crosses all three HBT corners with all three
resistor corners, three temperatures and three supplies, then adds bank/load,
fault and timestep cases: 97 actual simulations per reference-current setting.

The initial 2 mA reference fails the existing engineering screen in eight cases:
hot-corner transistor voltage margin falls below 0.4 V. The failed run is
retained. With a 1.5 mA reference, all 94 non-faulty cases meet the same
screen and all three faulty controls are rejected. Minimum screened transistor
voltage is 0.429866 V and minimum signed sample margin is 0.227035 V; the
maximum load branch current is 9.809433 mA. The model predicts at most 1.108751 K
resistor temperature rise in these non-faulty cases. The 0.5 ps comparison
changes margin by 0.000000474 V and supply power by 0.000040809 percent.
No voltage-margin threshold was relaxed.

The [complete experiment record](evidence/pcie-native-resistor-20260926.json)
links numbered lossless archives containing both 97-case matrices, original
waveforms and physical checks. Its verdict remains **REVIEW**: 31 corrected-run
cases contain numerical/startup warnings and the compiler emits three warnings
about constant `$simparam` evaluation. Neither the successful engineering
screen nor the publication-integrity verdict waives these issues.

The native resistor PCell has a generated GDS and separately checked schematic:
560 main DRC categories have zero markers, three-terminal LVS matches, and an
incorrect-width schematic fails. The first two-terminal schematic attempt
failed the native reader and is preserved. The corrected unit has an implicit,
untapped substrate; it does not provide the complete TX substrate connection.

Nine DC checks verify the temperature ratios and self-heating response against
the explicit TC1/TC2 law. A prior naive absolute-resistance calculation failed
and remains failed: that simple sheet/contact formula omits compact-model width
and field terms. It is retained as an informational estimate, not an exact
oracle. OpenVAF compiler warnings are retained and the model is not qualified.

The [IHP process current limits](https://ihp-open-pdk-docs.readthedocs.io/en/latest/process_specs/02_process_control_params.html#maximum-current-densities)
make contact and metal geometry relevant to lifetime. A PCell's displayed body
current estimate does not establish terminal current capacity. Contact/bar
current, substrate taps, routing/PEX and final TX geometry still need closure.
This work does not supply RX/CDR/PLL, serializer, complete protocol controller,
PHY integration or PCIe compliance evidence.

The generator's final [licence-header adjustment](evidence/pcie-load-generator-header-equivalence-20260926.json)
is byte-distinct but has exactly the same Python AST and generated header text
as the source archived with the physical measurement. No measured geometry or
netlist was altered. A previously published large diagnostic archive is linked
at its immutable GitHub revision to keep the documentation site within its
existing 64 MiB asset budget; the archive remains in the repository.

The new raw archives in this continuation are delivered as
[release assets](https://github.com/Melihakbulut221/nssoc/releases/tag/evidence-20260926-local-closure),
with [SHA-256, sizes and retrieval instructions](evidence/README.md#new-raw-evidence-delivery)
kept in Git. This follows the external review's binary-delivery requirement.

## RC coupling diagnostic

A [new matrix comparison](evidence/rc-grounding-diagnostic-20260926.json) tests
whether grounding every reference coupling explains the RC mismatch. It does
not: 13,138 pairs still differ. The coupled reference totals 27.418462 pF; the
fully grounded approximation totals 46.855160 pF, versus 43.910549 pF in the
actual RC export. This changes neither the extracted circuit nor its failed
acceptance verdict. The upstream [ResReadCapacitor implementation](https://github.com/RTimothyEdwards/magic/blob/fd12c39c37f26a0fe6e04698b1011e31b8bd3229/resis/ResReadExt.c)
contains a signal-extraction path that adds each coupling to both terminal
node capacitances. That observation motivates the diagnostic; it does not
prove that grounding is the only source of the measured discrepancy.
