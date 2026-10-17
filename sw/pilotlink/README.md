# Pilot serial driver
<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

`PilotLink` exposes asynchronous register access, checked state clearing,
configuration, signed four-bit weight loading and per-timestep event execution.
Offsets and bit positions come from `golden.regmap_gen`. Add `sw` to
`PYTHONPATH`; no simulator or serial package is imported by the core driver.

```python
from pilotlink import PilotLink
from golden.regmap_gen import ADDR

# transport implements async send_frame(bytes) and recv_frame() -> bytes.
# Supply the elaborated hardware geometry, NOT a reduced CFG_NEUR value.
link = PilotLink(transport, neurons=8, axons=8, poll_limit=400)
assert await link.geometry() == (8, 8)  # active counts after hardware reset
await link.state_clear()              # disables, clears, writes/verifies all state words
await link.configure(threshold=8, v_reset=0, leak_shift=3)
await link.load_weights([[1] * 8 for _ in range(8)], neurons=8)
await link.enable(scrub=True)
events = await link.run_frames([[0, 1], [], [2]])
```

One register frame is exactly five bytes: `{write, byte_offset >> 2}` then
four bytes of data, most significant first. The command byte's reply is ignored;
the following four bytes are the register result. Even writes consume their
reply. Mode 0 requires `SER_SCK <= clk/4`, chip select asserted for at least
one serial-clock period before the first edge, and at least one full period
of deselection between frames. These are the frozen `pilot_top.v` section 2
requirements, not ordinary SPI defaults.

Operations on the same link must not overlap. Configuration and weight writes
require the node disabled and idle. `state_clear` is destructive startup work:
after STATE_CLR and bounded idle polling it writes/reads each neuron address,
all twenty payload bits high, then zero. This establishes complete state/check
words even in the mapped implementation that retains unknown refractory state
after zero-only initialization. It never clears error counters. A bad readback
raises an error before enable. `load_weights` uses the supplied **physical**
neuron stride; reducing CFG_NEUR does not change that SRAM layout.

`run_frames` validates axon indices, emits SPIKE commands followed by TICK, and
drains after each command. It handles output backpressure by polling/popping.
All polling has a count bound; transport I/O must additionally have a time bound.
No partial request or response is retried, because a write may have committed
or an EVQ_OUT read may already have popped an event.

The backends are:

- `cocotb_transport.CocotbTransport(dut, clock_ns=10, half_ns=40)` drives the
  submitted TT pin interface. A pin shadow preserves falling edges across
  simulator delta cycles. It runs independently of the frozen pilot tests.
- `host.SerialTransport(port)` wraps an opened pySerial port with finite positive
  `timeout` and `write_timeout`. It requires the binary bridge below, not a UART
  console. A short transfer permanently rejects further traffic on that object;
  reset bridge alignment and reopen the port explicitly. The backend uses the
  documented [pySerial read/write API](https://pyserial.readthedocs.io/en/stable/pyserial_api.html).
- `rp2040.RP2040SPI` is a standalone MicroPython file; copy it to the board.
  Supply a mode-0, MSB-first `machine.SPI` or `machine.SoftSPI` object configured
  at `serial_hz`, and a chip-select `machine.Pin` callable. Supply the actual
  system clock as `system_hz`. Pin assignments are board-specific and have no
  defaults. The endpoint uses [MicroPython's simultaneous SPI transfer API](https://docs.micropython.org/en/latest/library/machine.SPI.html)
  and explicitly waits before/after chip select.

To bridge a host serial adapter to RP2040 SPI, call `serve_once(uart, endpoint)`
repeatedly on a dedicated `machine.UART` with finite `timeout` and `timeout_char`.
The protocol is five raw request bytes and five raw reply bytes, one outstanding
transaction. No REPL, terminal translation or console logging may share that
UART. A partial request/response stops the bridge; do not catch that exception
and resume midstream. This bridge supplies no additional link CRC, replay
protection or firmware framing recovery. It is a bring-up transport, not a
qualified spacecraft communication link. There is no direct USB-CDC firmware
or assumed TinyTapeout demo-board pin mapping.

Verification:

```sh
PYTHONPATH=sw .venv/bin/python -m pytest -q sw/tests/test_pilotlink.py
make -C hw/soc/tb/cocotb -f Makefile.pilotlink
```

The cocotb test uses the public API on unchanged RTL through TT pins, compares
all emitted events and neuron state with the integer golden model, and forces
eight simultaneous spikes through a five-event buffered path. A separate cancelled-write test verifies CS release and that a partial frame
does not change the register. Host and RP2040
transport tests use API fakes to check byte order, bounded failures, select gaps
and cleanup. Physical FTDI/RP2040/shuttle hardware has not been exercised.
