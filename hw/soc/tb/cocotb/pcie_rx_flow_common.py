# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent normal-polynomial FC oracle; only public byte-frame helpers."""

from test_soc_pcie_tlp_integrity import frame_bytes, tlp_bytes
from test_soc_pcie_tlp_stream import request, response, CID, BAR
from test_soc_pcie_packet_tx import expected_dllp


def fc_frame(phase, cls, header, data):
    body = bytes(
        (
            (0x40, 0xC0, 0x80)[phase] + cls * 16,
            header >> 2,
            ((header & 3) << 6) | (data >> 8),
            data & 255,
        )
    )
    value = 0xFFFF
    for octet in body:
        for bit in range(8):
            feedback = ((value >> 15) ^ (octet >> bit)) & 1
            value = ((value << 1) & 0xFFFF) ^ (0x100B if feedback else 0)
    reflected = int(f"{value:016b}"[::-1], 2)
    return body + ((~reflected) & 65535).to_bytes(2, "little")


def decode_fc(frame):
    assert len(frame) == 6
    phase = {0x40: 0, 0xC0: 1, 0x80: 2}[frame[0] & 0xC0]
    cls = (frame[0] >> 4) & 3
    header = (frame[1] << 2) | (frame[2] >> 6)
    data = ((frame[2] & 15) << 8) | frame[3]
    assert cls < 3 and frame == fc_frame(phase, cls, header, data)
    return phase, cls, header, data


__all__ = [
    "fc_frame",
    "decode_fc",
    "frame_bytes",
    "tlp_bytes",
    "request",
    "response",
    "CID",
    "BAR",
    "expected_dllp",
]
