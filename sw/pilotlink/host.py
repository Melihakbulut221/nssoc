# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded pySerial bridge backend. The device must run the documented 5-byte bridge.

Reads/writes may have side effects: never retry a partially completed exchange.
An error poisons this backend until the port and bridge are reset/reopened.
Blocking I/O is bounded by the caller-configured serial timeouts.
"""

import math


class SerialTransport:
    def __init__(self, port):
        if any(t is None or not math.isfinite(t) or t <= 0 for t in (port.timeout, port.write_timeout)):
            raise ValueError('finite positive serial read and write timeouts required')
        self.port, self.pending, self.failed = port, None, False

    async def send_frame(self, frame):
        if self.failed:
            raise IOError('transport alignment lost; reset bridge and reopen port')
        if self.pending is not None:
            raise RuntimeError('prior reply has not been received')
        if len(frame) != 5:
            raise ValueError('exactly five bytes required')
        try:
            if self.port.write(frame) != 5:
                raise IOError('partial bridge request')
            # pySerial read(size) obeys its total read timeout. No unbounded
            # flush() or retry loop follows a potentially committed write.
            reply = self.port.read(5)
            if len(reply) != 5:
                raise TimeoutError('incomplete bridge response')
            self.pending = bytes(reply)
        except BaseException:
            self.failed = True
            raise

    async def recv_frame(self):
        if self.failed or self.pending is None:
            raise IOError('no complete bridge response')
        reply, self.pending = self.pending, None
        return reply
