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
