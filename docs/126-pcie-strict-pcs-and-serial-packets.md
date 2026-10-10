# 126 — Strict PCS decisions and packets from recovered lane input
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

## Measured development — 5 October 2026

A bounded four-lane RTL receiver now connects recovered raw input to
CRC-qualified packet output. Its strict cohort stage accepts SKP only after
a real parser EDS decision and drains accepted packets at a complete ending
ordered set. That stage separately passes actual IHP cell simulation.
**These results do not close complete PCIe Gen3 x4, LTSSM, physical CDC,
SERDES/clocking, routed timing, qualified RC/ESD or main-chip integration.**

The [finite delivery inventory](../hw/soc/pcie-evidence/20261005-strict-pcs-and-serial-packets/delivery-inventory.json)
pins **21 new source files**, 18 already published source dependencies,
28 copied compact evidence files and ten immutable public assets. Five
complete local capsules were checked against their retained authenticated
and anonymous release hashes: **1,706 members** were rehashed. This review
did not redownload the assets or rerun HDL, SAT or analog simulations. The
[previous report](125-pcie-sds-cohorts-and-native-validation.md) remains an
unchanged dated snapshot.

## Parser-owned EDS and strict lane cohorts

The strict deskew V2 contract starts with one fresh, externally qualified
SDS cohort after coordinated reset/arm. Logical lanes remain fixed at 0–3,
and each lane's first post-SDS block must be DATA. A consumed DATA quartet
owns one subsequent parser decision; a decision without that ownership is
a fault. The bench supplies the decision four cycles later, including the
case where a decision and the next quartet are accepted together.

An EDS byte pattern inside a packet body cannot authorize SKP. Only the
parser's EDS token decision permits the next ordered-set cohort. Normal SKP
must have equal length on all four lanes; consecutive SKP and DATA directly
after EDS are rejected. Complete EIOS or EIEOS on all four lanes ends the
stream. Mixed ending types, missing lanes, malformed padding and unknown
ordered sets fault within the declared 64-cycle skew bound. Held output
remains stable under backpressure.

| Experiment | Full scenarios | Actual RTL faults | Mapping scope |
| --- | ---: | ---: | --- |
| Strict leaf RTL | 4 positive + 15 expected-fault | 10 | Icarus RTL |
| Strict leaf native method V3 | Same 19 scenarios | Same 10, each mapped separately | 11 SG13 maps; 1,603 baseline cells |
| Composed raw-to-packet receiver | 15 complete cases | 8 unique wiring faults | Icarus RTL; no whole-receiver SG13 replay |

The [native leaf receipt](../hw/soc/pcie-evidence/20261005-strict-pcs-and-serial-packets/strict-native/native-v3/ready.json)
records **29 completed cell-model simulations** and 33 method preflight
controls. This version maps the baseline and every mutant afresh; it does
not reuse an earlier leaf map. The adapter verifies the synthesized default
parameter is exactly 64 and preserves the port oracle. Each faulty RTL must
produce its intended diagnostic; tool or compiler failure cannot count as
successful rejection.

All 29 closed VVP programs were losslessly compressed and fully decompressed
for byte/hash comparison before raw copies were removed. They preserve
**71,168,673 compiled bytes**. The run used a 2 GiB process address-space
cap, one CPU, no elapsed-time cutoff, a 1 GiB scratch entry gate and a
528 MiB shared free-space floor. Its maximum owned storage was 28,690,146
bytes. These are functional simulations with a 4 ns bench clock and 1 ns
observation offset, not SDF timing, metastability or physical lane-rate
qualification. Parser decisions are external inputs in this leaf experiment.

## Actual raw lanes through CRC-qualified retirement

The new composition connects four independent recovered-clock 32-bit inputs
through local SDS-locking lane alignment, complete-record CDC, ordered-set
LFSR/parity handling, strict cohort deskew and integrity framer V8. Its
output carries 128 data bits, per-byte keep, packet boundaries, DLLP type
and sequence metadata. Packet bytes remain quarantined until the integrity
verdict permits release. This composition does not yet connect the owned
descriptor/DLLP event consumer or establish complete controller throughput.

The [full RTL evidence](../hw/soc/pcie-evidence/20261005-strict-pcs-and-serial-packets/strict-pcs/root-delivery/validation.json)
includes all 32 raw bit phases, lane skew, held output, SKP after actual EDS,
payload EDS patterns, CRC failure, EDB nullification, reset/restart and
normal ending while packet retirement is stalled. It also exercises
forbidden SKP, unequal lengths, mixed endings and framing errors. Scrambled
data parity reports a lane error without retraining. A separate LFSR
diagnostic does not alter packet state.

Framer V8 is a bounded adapter of V7: it supplies an owned block decision
and token-context EDS indication, pauses ingress at EDS while allowing
retirement, and accepts a separate complete-cohort stop signal. EDS alone
does not end the packet epoch. After a normal complete ending, a later
transport fault remains visible at the lane interface but cannot discard
an already accepted packet still draining. A coordinated reset starts the
next epoch. The actual control stalls output for 2 µs and exercises this
later transport fault.

The preserved failure history matters:

- The first leaf mutation sweep had three failed controls: two literal
  replacement-count guards and one diagnostic mismatch. Corrected targeted
  controls and the final complete 29-test run are retained alongside them.
- The first missing-parser-reset mutant survived because the fixture reset
  before the registered halt became visible. The corrected oracle waits
  and checks the actual halt/reset path; the original survival remains.
- Earlier packet sources allowed a later transport fault to abort normal
  draining. A separate stopped-epoch guard corrects that behavior. The
  lost-stop mutant then required the actual bounded incomplete-drain
  diagnostic; its earlier wrong expectation is also preserved.

The archive audit independently recounted **22 saved packet XML results**,
including earlier attempts, and checked all 818 capsule members. The first
12-case bench was reconstructed and matched against its original captured
input hash; it is not presented as a historically saved source file. Runtime
pins are rechecked where the original producer emitted them, without
inventing a historical runtime inventory for the direct leaf. The archive's
filename contains “native”, but this whole composition's evidence is RTL
execution, separate from the SG13 leaf campaign above. See the
[scoped audit](../hw/soc/pcie-evidence/20261005-strict-pcs-and-serial-packets/archive-audits/agent-inventory/archive-audit.json).

## Separate predecode candidate: finite controls only

Integrity V9 registers 32 bits of literal token/header metadata beside each
DWORD in the current and next block buffers. Data and metadata follow the
same load, shift, replacement and reset priorities, including simultaneous
next-to-current movement and new input. EDS still requires its original
word-position condition; a decoded byte pattern alone does not change that
condition. V9 branches from V7 and is **not** substituted into the strict
V8 composition in this delivery.

Its [controls receipt](../hw/soc/pcie-evidence/20261005-strict-pcs-and-serial-packets/integrity-v9-controls/pcie-integrity-v9-20261005/pcie-integrity-v9-core-controls-validation-20261005.json)
records **32 pytest executions covering 31 distinct predicates**; the
inverse source bridge is executed twice. Coverage includes 294,924 literal
word cases, 4,096 companion-buffer transitions, 13 direct default-150 port
cases and 13 cycle-exact V7/V9 comparisons. All 24 actual RTL mutants are
rejected: nine decoder, five buffer, eight public-behavior and two miter
faults.

Three SAT proofs cover every binary 32-bit DWORD for the literal decoder at
limits 18, 150 and 4118, with three actual fault counterexamples. They do
not prove the whole sequential parser or arbitrary independent corruption
of the companion state. The separate source peer checks the literal source
bridge and buffer association without rerunning the tests. Native mapping,
import and timing work are outside this controls-only acceptance; no mapped
port replay, maximum whole-DUT profile or timing closure is inferred.

## Addenda to previously delivered integrity versions

The deferred [V5 default capsule](../hw/soc/pcie-evidence/20261005-strict-pcs-and-serial-packets/integrity-v5-default/pcie-integrity-v5-20261005/pcie-integrity-v5-default-controls-validation-20261005.json)
now adds its complete standalone evidence: 20 pytest executions cover 19
distinct predicates, 13 direct cases, 13 V4/V5 cycle comparisons and 15
actual RTL faults. Its separately published compiled-program preservation
receipt is included; this delivery's local capsule audit did not fetch that
separate archive again. The earlier cache SAT evidence and slow/typical
timing failures keep their original scopes.

The original [V7 maximum-4118 direct profile](../hw/soc/pcie-evidence/20261005-strict-pcs-and-serial-packets/integrity-v7-maximum/pcie-integrity-v7-20261005/pcie-integrity-v7-max4118-validation-20261005.json)
has now completed **13/13 cases** in one pytest execution. This updates the
earlier pending state through a new addendum without rewriting that
snapshot. It does not establish a maximum-capacity cycle miter, native
mapping or physical timing. The encoded 4118-byte capacity does not cover
a 4096-byte payload with a four-DWORD header and digest requiring 4122 bytes.
Original V5/V6 maximum whole-DUT campaigns remain outside completed scope.

## Remaining physical and system gates

The new VCOv5 physical/powered candidates and ongoing owned-event integration
are excluded from this source allowlist. RX repair10 routing has completed,
but this delivery does not contain a completed new extracted-RC/timing
verdict. The restarted tighter 1 µs PLL experiment and its timestep pair
also have no new acceptance in this inventory. The earlier HTTP 422 release
capacity failure remains preserved; new public capsules use the immutable
continuation release documented in report 125.

Full LTSSM and training behavior, truncated ending sets, recovery policy,
physical CDC and clock qualification, sustainable complete-controller
operation, routed setup/hold with qualified coupling, full-chip DRC/LVS/ESD,
manufacturing review and silicon validation remain open. The
[product acceptance contract](92-product-acceptance.md) continues to govern
delivery of the complete chip.
