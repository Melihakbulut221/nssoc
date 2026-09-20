# 97 — UART reception and software contract
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

The console now implements independent 8N1 transmit and receive paths.
`soc_top.uart_rx_i` feeds a two-flop synchronizer in `soc_uart`; reset leaves
reception disabled and the line should idle high. A board without a receiver
must tie this input high. Both directions use `8 * (SCALER + 1)` system clocks
per bit, with a 12-bit scaler. The receiver latches its divider at each start
bit, validates the start midpoint, then samples eight bits LSB first and the
stop midpoint. Changing SCALER during reception affects the next frame.

## 1. Registers and compatibility

Offsets follow the APBUART layout at UART0's generated base `0xFF900000`.
The [official GRLIB manual](https://download.gaisler.com/products/GRLIB/doc/grip.pdf),
June 2026 section 18, defines the reference receiver/error semantics.
This implementation has one holding byte per direction and a project-specific
level interrupt. It does not implement parity, flow control, a FIFO, break
status, debug or capability registers.

| Offset | Register | Implemented behavior |
|---|---|---|
| `0x00` | DATA | Write queues TX bits 7:0. Read returns and consumes the RX byte only on a completed APB ACCESS; empty reads return zero. SETUP is inert. |
| `0x04` | STATUS | DR bit 0: unread RX data. TS bit 1: TX completely idle. TE bit 2: TX holding register empty. OV bit 4: sticky RX overrun. FE bit 6: sticky invalid stop bit. Bit 7: legacy project TX holding-full flag. Other bits zero. |
| `0x08` | CTRL | RE bit 0, TE bit 1, RI bit 2 and TI bit 3; all reset to zero. Unsupported bits read zero. |
| `0x0C` | SCALER | Bits 11:0, reset zero; maximum bit period is 32,768 clocks. |

STATUS error bits are individually **write-zero-to-clear**. Writing ones
preserves those errors; writing zero clears both. A new hardware error in the
same cycle wins over software clearing it. An invalid stop bit discards that
frame and sets FE. The receiver then waits for the input to return high, so a
held-low line does not manufacture more errors after clearing FE. A valid
frame arriving while an unread byte remains sets OV and preserves that older
byte. A simultaneous DATA read and valid arrival consumes the old byte and
keeps the new byte without overrun. Disabling RE aborts a partial frame while
preserving unread data and error flags; reset clears them all.

Two compatibility limits are explicit. GRLIB calls STATUS bit 7 **TH** and
bit 9 **TF**; existing nssoc software used bit 7 as holding-full, and this ABI
is preserved. Interrupt behavior is the level expression
`(TI && TE_status) || (RI && (DR || OV || FE))`, rather than GRLIB's
holding-register event pulse. Software must consume pending RX data and clear
errors, or disable the relevant interrupt enable. Merely acknowledging the
CPU interrupt does not clear its peripheral source.

## 2. CPU and verification

The existing UART source reaches Ibex fast interrupt line 0, MIE/MIP bit 16,
`mcause=0x80000010`, vector `mtvec + 0x40`. The firmware interrupt stub masks
that MIE bit after recording the cause. The driver must clear the peripheral
source before re-enabling MIE.

Run the serial/APB tests and the CPU integration test with:

```sh
make -C hw/soc/tb/cocotb -f Makefile.soc_uart_rx
make -C hw/soc/tb/cocotb -f Makefile.soc_uart
python3 hw/soc/flow/uart_rx_probe.py --prepare hw/soc/out/uart-rx
bash hw/soc/out/uart-rx/run_rtl.sh
python3 hw/soc/flow/uart_rx_probe.py --prepare hw/soc/out/uart-rx-negative --corrupt-byte
bash hw/soc/out/uart-rx-negative/run_rtl.sh
make -C hw/soc/formal uart
bash scripts/check_uart_native.sh
```

Use fresh output directories. The normal cocotb inventory includes the RX
suite; hosted hardware CI also executes the real-CPU positive and corrupted
serial-byte controls, plus the mapped UART tests with untouched IHP models.
The native runner needs Yosys, Icarus and the hardware Python environment;
it fetches the checksum-pinned model/Liberty subset, or uses an explicit PDK
directory. This subset is not a physical PDK installation. Seven RX tests cover input phase, representative and
maximum dividers, malformed input, false starts, overrun, disable/reset,
per-frame divider changes, concurrent TX/RX, two-percent baud mismatch at
SCALER=7, and DATA-read timing swept across frame completion. Unknown sampled
pin or bus values fail the tests. The mismatch experiment is not a general
analog baud-tolerance specification.

The CPU test boots the normal CRT, receives through the external serial pin,
reads ordinary APB registers, exercises RI masking and sticky-error clearing,
and wakes from WFI through the real UART interrupt. Six externally transmitted
frames complete five software phases. A changed external data bit must produce
the exact expected failure mask; a generic simulator failure is rejected.

The formal contract checks APB/control/status/interrupt semantics with arbitrary
RX input. It does not prove serial payload correctness, CDC reliability or
radiation tolerance. The UART is not fault hardened. Final mapped whole-SoC
replay, routing, timing, CDC/MTBF, pad integration and silicon acceptance remain
separate product gates. Older layouts and their DRC results predate RX.

The [21 September measured record](evidence/uart-receive-20260921.json) binds
RTL, native models, contracts, firmware and runners to their hashes: **24
RTL tests and 24 mapped-cell tests pass**, comprising 14 TX/APB, seven RX and
three TX race tests. Five compiled RX mutations and five peripheral formal
mutations are rejected. The real CPU test passes five phases in 3,251 cycles;
its changed-byte control reports the required failure mask. The mapped block
contains 113 flip-flops and 9,842.2128 square micrometers of standard-cell
area; this is synthesis area, not a routed die measurement.
