# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Standalone MicroPython mode-0 SPI endpoint and UART bridge (copy this file).

Pin assignment and clock frequencies must be supplied for the actual board.
No board-specific GPIO is guessed. The bridge is raw binary 5-byte request /
5-byte reply, one transaction at a time; no REPL or console text may share UART.
On a partial request it stops, so remaining bytes cannot become a new command.
"""


class RP2040SPI:
    def __init__(self, spi, cs, *, serial_hz, system_hz, sleep_us=None):
        if serial_hz <= 0 or system_hz <= 0 or 4 * serial_hz > system_hz:
            raise ValueError('SER_SCK must not exceed clk/4')
        if sleep_us is None:
            # This import runs only on MicroPython; CPython host tests inject
            # the clock. Keep the same failure on an unsupported host.
            from time import sleep_us as micropython_sleep_us  # type: ignore[attr-defined]
            sleep_us = micropython_sleep_us
        self.spi, self.cs, self.sleep_us = spi, cs, sleep_us
        self.gap_us = max(1, (1000000 + serial_hz - 1) // serial_hz)
        self.cs(1)
        self.sleep_us(self.gap_us)

    def exchange(self, frame):
        if len(frame) != 5:
            raise ValueError('exactly five bytes required')
        reply = bytearray(5)
        self.cs(0)
        try:
            self.sleep_us(self.gap_us)
            self.spi.write_readinto(frame, reply)
            self.sleep_us(self.gap_us)
        finally:
            self.cs(1)
            self.sleep_us(self.gap_us)
        return bytes(reply)


def serve_once(uart, spi):
    """UART must have finite timeout/timeout_char; call repeatedly from main."""
    if not uart.any():
        return False
    frame = uart.read(5)
    if frame is None or len(frame) != 5:
        raise OSError('partial request: stop and reset bridge/host alignment')
    reply = spi.exchange(frame)
    if uart.write(reply) != 5:
        raise OSError('partial response: stop and reset bridge/host alignment')
    return True
