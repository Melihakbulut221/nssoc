# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Mode-0 backend on the submitted TT pin interface, outside the frozen tests."""
from cocotb.triggers import RisingEdge, Timer


class CocotbTransport:
    def __init__(self, dut, *, clock_ns=10, half_ns=40):
        if half_ns < 2 * clock_ns:
            raise ValueError('serial clock must not exceed system clock / 4')
        self.dut, self.half = dut, half_ns
        self.pending = None
        self.active = False
        self.shadow = int(dut.ui_in.value)

    def _drive(self, bit, value):
        self.shadow = (self.shadow & ~(1 << bit)) | (int(value) << bit)
        self.dut.ui_in.value = self.shadow

    async def send_frame(self, frame):
        if len(frame) != 5:
            raise ValueError('exactly five bytes required')
        if self.active or self.pending is not None:
            raise RuntimeError('prior frame is still pending')
        self.active = True
        try:
            # Synchronize simulation phase; hardware has no common clock phase.
            await RisingEdge(self.dut.clk)
            self.shadow = int(self.dut.ui_in.value)
            self._drive(0, 0)
            self._drive(1, 0)
            await Timer(2 * self.half, unit='ns')
            reply = bytearray()
            for byte in frame:
                value = 0
                for bit in range(7, -1, -1):
                    self._drive(2, (byte >> bit) & 1)
                    await Timer(self.half, unit='ns')
                    self._drive(0, 1)
                    await Timer(1, unit='ns')
                    value = (value << 1) | (int(self.dut.uo_out.value) & 1)
                    await Timer(self.half - 1, unit='ns')
                    self._drive(0, 0)
                reply.append(value)
            await Timer(self.half, unit='ns')
            self._drive(0, 0)
            self._drive(1, 1)
            await Timer(2 * self.half, unit='ns')
            self.pending = bytes(reply)
        except BaseException:
            # Cleanup cannot await: cocotb cancellation forbids a cancelled
            # task from yielding again. Recovery needs a full deselect gap.
            self._drive(0, 0)
            self._drive(1, 1)
            self.pending = None
            raise
        finally:
            self.active = False

    async def recv_frame(self):
        if self.active or self.pending is None:
            raise RuntimeError('no completed frame')
        result, self.pending = self.pending, None
        return result
