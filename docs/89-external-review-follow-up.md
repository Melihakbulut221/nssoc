<!--
SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
SPDX-License-Identifier: CC-BY-4.0
-->
# 89 — External review follow-up and interface target

2026-09-19. Starting revision: `31ef551271d28b06bec280c7d9418e04084a9456`.
The user-supplied `nssoc-external-review.md` describes an older mirror.
Its reproduction commands are evaluated against the starting revision before
changing the implementation. This record supplements [docs/86](86-the-external-review.md)
and [docs/87](87-engineering-closure.md); historical measurements stay historical.

## Reproduction and outstanding acceptance

* `bash scripts/ci_local.sh all`: **16 passed, 0 failed, 7 skipped** before
  edits. The skips are six absent historical run trees and Pandoc. F0a–c do
  not reproduce. F0d needs a fresh recorded run after the implementation changes.
* Fresh depth-one clone of `codex/complete-open-work`, using the workspace
  Python environment: `python -m pytest -q -rs`: **600 passed, 38 skipped**.
  Yosys is available. F6's fewer-than-30-skips criterion remains **open**.
  Missing build products cannot be called tool absence. The recorded metrics
  added by docs/86 improve reproducibility but do not satisfy that whole criterion.
* `verilator --lint-only --no-timing -Wall -Ihw/rtl -Ihw/soc/rtl
  hw/soc/rtl/soc_npu.v`: no SYNCASYNCNET and no errors; other warning classes
  remain. F1's reported reset misuse does not reproduce.
* F2's crash-PC connection and POR-domain record already exist. The fresh
  `CRASH_DUMP_DEMO` run passes with PC `0xff9fe000` after watchdog recovery,
  two boots and **331964 cycles**. F5's orphans
  have explicit dispositions. F8's real-codec contract and pinned upstream
  equivalence have been proved; the core-level instruction gaps remain as
  documented in docs/63 and docs/87. No repeat of the old seven-engine sweep.
* **F3 does reproduce at integration level:** the timeout-capable bridge had
  its event output disconnected, and the SoC instantiated it with timeout off.
  CAN now uses a wait-state APB/Wishbone bridge, invalidating the historical
  all-slaves-ready rationale.
* F4's flash timing assumptions exist in `soc_top_qspi_io.sdc`, but the current
  implementation profile does not yet source them. Flow integration and an
  extracted timing measurement remain open.
* F7 and section 5 are documentation requests in the review. The routing
  keep-out experiment and missing silicon components are listed in ROADMAP.
  The latest physical baseline remains **219 Magic boxes, 11,048 KLayout
  markers, failing slow setup and fast/typical hold**, with the exact scopes
  and provenance in [docs/88](88-interface-integration.md). It is not signoff.

## APB fault containment and retained telemetry

`soc_top.APB_TIMEOUT` now defaults to **256 ACCESS clocks**: 5.12 us at
50 MHz. `SOC_APB_TIMEOUT` selects the same parameter in simulation and synthesis.
Zero reproduces the disabled configuration; the bridge block's own default stays
zero. A normal CAN register handshake completes well before this bound.

On timeout the bridge returns one fabric error and keeps APB PSEL, PENABLE,
address and write payload stable until system reset. A late PREADY cannot produce
another response. This quarantines the **whole APB bus**, including UART and
BUSSTAT. Firmware can use RAM and ROM to handle the error; watchdog recovery is
needed to read the retained record through APB. This is not an APB abort protocol.

BUSSTAT enables its optional ninth source when the top timeout is nonzero:

| Register | Offset | Meaning |
|---|---:|---|
| STATUS | 0x000 | Bit 9: timeout sticky; bit 8 remains the existing IRQ indication |
| IRQEN | 0x004 | Bit 9 enables the timeout source; bit 8 remains reserved |
| CLR | 0x018 | Bit 9 clears timeout count/sticky; a concurrent event wins |
| CNT_APBTO | 0x02C | 16-bit saturating timeout count |

The event is `apb_timeout && s_rvalid[2]`, one clock per returned timeout error,
not the persistent quarantine level. Counter and sticky reset only on POR;
IRQEN resets on every system reset. No existing offset, interrupt line or source
bit moved. The firmware header and generated memory-map description carry this.

Verification commands:

```sh
scripts/run_cocotb.sh soc_busstat
make -C hw/soc/formal busstat apb npu OSS_CAD_SUITE=/path/to/oss-cad-suite
python -m pytest -q sw/tests/test_soc_synthesis_guards.py -k 'fault_counters or fault_lines'
SOC_MEM_RDREG=1 SOC_REQ_REG=1 SOC_RF_SYNPRE=1 \
  SW_DEFINES=-DAPB_TIMEOUT_DEMO SOC_VVP_ARGS=+apb_timeout_demo \
  bash hw/soc/flow/sim_soc.sh hw/soc/out/apb-timeout-demo
```

The block regression passes **12 tests**. All **8 BUSSTAT, 5 APB and 3 NPU**
formal tasks pass. The counter-retention synthesis guard passes at both timeout
settings; the connection guard also passes. The added formal parameter point
checks saturation at width 4, proves the shipping width 16, checks bit-9 mapping,
and covers retained evidence across system reset. The whole-SoC demo passes:
one load-access fault, late PREADY ignored, return to software checked in RAM
before watchdog stage 2, two boots, retained count 1 and IRQEN 0 on the second
boot. It finishes after **463419 cycles**. Source hashes, block synthesis
commands, proof statuses and the complete CPU transcript are retained in
[the machine-readable record](evidence/apb-timeout-20260919.json).

Mapped block cost, Yosys 0.33, identical `synth; dfflibmap; abc; clean; stat`
commands and SG13G2 typical library at PDK commit
`c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c`:

| Block/configuration | Cells | Cell area (um2) |
|---|---:|---:|
| APB timeout 0 | 193 | 6265.1232 |
| APB timeout 256 | 279 | 7418.9682 |
| BUSSTAT timeout source off | 794 | 13427.3160 |
| BUSSTAT timeout source on | 892 | 15000.5898 |

Combined block delta: **184 cells, 2727.1188 um2**. These are independently
mapped blocks, not an estimate of placed whole-chip growth. The previous GDS
in docs/88 predates this RTL change and cannot validate it.

## Confirmed interface target

The user's target is **PCIe Gen3 x4 and Gigabit Ethernet**, in addition to
SpaceWire, CAN, SPI and I2C. The four latter interfaces are integrated as described
in docs/88. PCIe and Ethernet were absent from that layout.

Gigabit Ethernet requires a MAC, packet buffering, clock-domain crossings and
an external PHY interface. PCIe Gen3 x4 requires a compatible 8 GT/s four-lane
PHY plus link/controller integration. A TLP-only adapter or FPGA hard-IP wrapper
is not evidence of a complete ASIC PCIe link. No PCIe PHY is instantiated in the
current IHP core, and no PCIe completion claim is made.

**2026-09-19 follow-up:** docs/90 records the now-implemented Gigabit GMII MAC,
native SRAM gate-level packet tests and CPU interrupt test. docs/91 records
the PCIe IP investigation. The old routed baseline still cannot validate the
new RTL.

**F6 digest correction:** the prior test comment incorrectly said the review did
not request extending `docs/80-artefact-digests.tsv`. It explicitly does.
`scripts/artefact_digests.py --write-evidence` now pins the committed JSON records
while preserving every historical run digest, and `test_artefact_digests.py`
checks exact file coverage, size and SHA-256 on a fresh clone. This closes the
digest sub-item; it does not turn missing DEF/netlist evidence into a pass or
claim that the fewer-than-30-skips criterion is met.

## F4: explicit QSPI constraints and extracted remeasurement

The first twelve-macro Ethernet interface profile sources `soc_interfaces.sdc`,
which sources the existing QSPI fragment in both P&R and final STA. The default
QSPI sampling RTL and divider remain unchanged. Before routing this new profile,
the completed docs/88 layout was re-timed with its extracted SPEF and explicit
QSPI budgets in run `qspi-review-20260919` (LibreLane 3.0.5, same pinned PDK).
Only STAPostPNR ran in this replay; it did not place or repair a new layout.

| Corner | Worst setup (ns) | Worst hold (ns) | Hold violations |
|---|---:|---:|---:|
| Fast | +8.591611 | -3.022404 | 27 |
| Typical | +3.809705 | -2.488044 | 14 |
| Slow | -5.774160 | -1.542460 | 15 |

The input/output assumptions make previously unconstrained requirements
visible. In particular, the conservative output hold budget fails; the old
standalone typical input setup margin did not establish IO timing closure.
Actual source-synchronous SCK, pad/package and board characterization remain
necessary before claiming a working physical flash interface. The original
divider arithmetic is in `soc_qspi.v` and docs/66. Native metrics, input hashes
and summary are in [the QSPI STA record](evidence/qspi-sta-20260919.json).

Reproduction uses `soc_top_qspi_io.sdc` after LibreLane's base SDC, the recorded
input netlist/ODB/SPEF, and `OpenROAD.STAPostPNR` for all three corners. The new
Ethernet profile uses the same QSPI fragment directly from the versioned flow.
The timing outcome remains failing; recording it satisfies the review's STA
measurement request without changing the default sampling behavior.
`scripts/run_cocotb.sh soc_qspi` passes **16 tests, zero failures/skips**.

## Further reproduction at abc0791

A clean remote clone of `abc079155d7c04d58f06e3c0e9d02df84549a0b8` passed
`scripts/ci_local.sh all --record`: **16 passed, zero failed, 7 skipped**, with
`tree-dirty=0`. Its exact row is appended to `ci-local-log.tsv`; the row names
the revision actually tested, not the later commit that stores the row.
An explicit `python -m pytest sw/tests -q -rs` in that clone measured
**605 passed, 38 skipped**. This does not close F6.

**F0a test correction, 2026-09-19:** the old public rejection test skipped and,
upstream, only asserted regex preconditions. It never called the production
rejection. `redact_fragment` now holds the unchanged production rule, and the
test invokes it with altered real file text. The public tree also runs the
two-generation idempotence test. All six mirror tests pass without skips,
including duplicate matches with a marker present. This changes test coverage,
not the redaction acceptance rule.

**F6 additional evidence:** a byte-for-byte copy of the first Ethernet run's
post-CTS step configuration is committed as
[postcts-config.json](evidence/interfaces-eth-pnr2-postcts-config.json).
`test_derate_is_a_float.py` checks its demoted integer on a clone and compares
bytes with the live checkpoint where present. This is evidence for one actual
LibreLane 3.0.5 checkpoint, not a reconstructed historical 1,529-step census.
Missing historical netlists, DEF and run reports remain distinct from missing
tools and cannot honestly be relabelled as tool skips.

The Ethernet SRAM mapping was subsequently replaced after measured 125 MHz
failure; docs/90 records the comparison and the new 24-macro physical profile.

The full RTL run passed **479 tests**, with zero failures and 15 explicit
skips. Core and NPU fault-injection builds also elaborate with the Ethernet
sources; these are compilation checks, not new fault campaigns. All three
GitHub jobs at `abc0791` completed successfully. Logs, digests, scopes and CI
results are retained in [the verification record](evidence/verification-20260919.json).

**Clean-clone correction after 895d6ca:** the added historical `postcts-config`
snapshot was picked up by the editable-input float guard after it became
tracked. That fresh run recorded **610 passed, 1 failed, 34 skipped**; its
front-door row is retained, including the failure. The snapshot really must
keep the integer the tool wrote. The input guard now excludes only
`docs/evidence/`, while the separate step-record test continues to check the
integer and compare the live bytes. Active P&R inputs still require a float.

**Verified follow-up at 882a4e0, recorded after restart:** the clean remote
clone completed with **611 passed, zero failures, 34 skipped** in the full
Python suite. The front-door result was **16 passed, zero failed, 7 skipped**,
with `tree-dirty=0`; its original row is now retained in `ci-local-log.tsv`.
The earlier failed run remains in the history and verification record.
The 34 remaining skips include absent build products and generated dependencies;
they do not meet F6's requirement that every remaining skip be tool/PDK absence.
All three GitHub jobs for shutdown checkpoint `5b196ca` also completed
successfully, independently of the local physical flow.

The 23 checkpoint artifact hashes verified after restart. The 24-macro physical
flow resumed at `OpenROAD.STAMidPNR-2` from the completed post-CTS repair
checkpoint. Its routing and final timing results are not yet available.

**F6 missing-artifact diagnostics:** placement, gate-coverage and shipped-netlist
checks now identify their historical DEF/netlist by its exact manifest path,
byte count and SHA-256. A current rebuild is explicitly a new measurement,
not a replacement for those historical bytes. The shared lookup refuses
conflicting identities and never borrows a hash from another run with the same
basename. These changes preserve skips and all existing assertions. The focused
regression passed **60 tests with 8 missing historical artifact skips**; the
frozen pilot rail-netlist check separately skipped with its exact identity.

A subsequent clean GitHub clone of `e2193ec` passed the complete front-door
command: **16 passing gates, zero failures, 7 skips**, `tree-dirty=0`. The full
Python suite measured **612 passed, zero failures, 34 skipped**. The additional
pass is the artifact-identity negative control; no missing-artifact skip was
converted into a pass. The original XML and log hashes are in the verification
record, and the measured CI row is appended unchanged.

### Prepared-source clone: five generated-dependency skips resolved

The same `e2193ec` clone was then prepared from pinned upstream sources using
`make -f hw/soc/tools.soc.mk fetch-sv2v fetch-ibex`, `sv2v_ibex.sh`,
`make soc-interfaces-prepare` and `ibex_fault_port.py`, before running the
complete Python suite again. It measured **617 passed, zero failures,
29 skipped**. The only tracked change in that clone was the earlier recorded
`ci-local-log.tsv` row; its RTL and tests were not edited. Commands, XML and
remaining skip reasons are in `verification-20260919.json`.

This is a prepared checkout, not the bare clone's result. Five actual upstream
compatibility/elaboration checks ran instead of skipping; no assertion was
removed. They also pass with the pinned CI OSS CAD Suite. `make soc-rtl-prepare`
now provides this preparation without downloading the firmware compiler, and
`make soc-prepared-guards` runs the five checks explicitly. The latter fails
early for absent generated inputs or Yosys; it does not download dependencies.
GitHub's formal/boot job runs it after preparation.

**F6 remains open:** the remaining skips still include absent historical
DEF/netlist/run trees. A prepared checkout below the numeric skip threshold
does not meet the requirement that every remaining skip be tool/PDK absence.
The full review and product acceptance inventory is in
[docs/92](92-product-acceptance.md).

### F2: requested cocotb method now exercised

2026-09-19. The earlier whole-CPU C/Verilog crash demonstration is now also
observed by `hw/soc/tb/integration/test_crash_recovery.py`. The existing firmware
provokes the actual double fault; cocotb observes it, waits through the watchdog
reset, then checks two accepted APB reads of `BOOTREG.CRASH` and the attempted
`0xdeadbeef` write between them. The returned PC is `0xff9fe000` both times.
No crash input, stored PC or APB response is forced. The register-map suite
also passes. Commands, counts, simulator time and file identities are in the
[crash cocotb record](evidence/crash-cocotb-20260919.json).

The first observer incorrectly sampled a combinational delta-cycle transition
as a synchronous fault and failed with PC `0x1d0`. Its log and XML are retained;
the corrected observer samples a settled half-cycle with the fault signal
still high. This changed the test, not the RTL. The earlier checklist's method
gap is now closed by a measured **one-test PASS, zero failures and skips**.
The separate C/Verilog test still checks complete firmware termination.

`make soc-crash-cocotb` builds and runs both checks. CI invokes the observer
after its existing whole-CPU crash program and retains the cocotb result.
The original register cost in docs/86 is unchanged: this addition is a test.
