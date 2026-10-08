# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Small RV32I ROM: CPU Ethernet loopback plus GPIO, without a debug backdoor."""


def firmware():
    words, labels, branches = [], {}, []

    def emit(word):
        words.append(word)

    def label(name):
        labels[name] = len(words) * 4

    def addi(rd, rs, imm):
        emit(((imm & 4095) << 20) | (rs << 15) | (rd << 7) | 0x13)

    def lui(rd, upper):
        emit((upper << 12) | (rd << 7) | 0x37)

    def load(rd, rs, offset):
        emit((offset << 20) | (rs << 15) | (2 << 12) | (rd << 7) | 3)

    def store(rs2, rs1, offset):
        emit(
            ((offset >> 5) << 25)
            | (rs2 << 20)
            | (rs1 << 15)
            | (2 << 12)
            | ((offset & 31) << 7)
            | 0x23
        )

    def bitand(rd, rs, imm):
        emit((imm << 20) | (rs << 15) | (7 << 12) | (rd << 7) | 0x13)

    def branch(rs1, rs2, target, unequal=False):
        branches.append((len(words), rs1, rs2, target, int(unequal)))
        emit(0)

    lui(1, 0xFF902)  # GPIO
    lui(2, 0xFF91A)  # Ethernet, existing generated APB slot 0x1a
    addi(3, 0, -1)
    store(3, 1, 8)  # output enable
    addi(3, 0, 3)
    store(3, 2, 0)  # enable both MAC directions
    lui(10, 0x80000)  # expected RX_VALID bit
    addi(11, 0, 60)
    addi(12, 0, 59)
    label("frame")
    addi(4, 0, 0)
    label("tx")
    load(5, 2, 4)
    bitand(5, 5, 1)
    branch(5, 0, "tx")
    addi(6, 4, 0)
    branch(4, 12, "not_last", True)
    addi(6, 6, 256)
    label("not_last")
    store(6, 2, 8)
    addi(4, 4, 1)
    branch(4, 11, "tx", True)
    addi(4, 0, 0)
    label("rx")
    load(5, 2, 4)
    bitand(5, 5, 2)
    branch(5, 0, "rx")
    load(6, 2, 12)
    emit((10 << 20) | (4 << 15) | (7 << 7) | 0x33)  # add x7,x4,x10
    branch(4, 12, "rx_not_last", True)
    addi(7, 7, 256)
    label("rx_not_last")
    branch(6, 7, "fail", True)
    addi(4, 4, 1)
    branch(4, 11, "rx", True)
    load(5, 2, 16)
    bitand(5, 5, 0x1FC)  # any FIFO/frame/FCS error
    branch(5, 0, "fail", True)
    addi(3, 0, 1)
    store(3, 1, 0x74)  # successful frame toggles GPIO bit zero
    branch(0, 0, "frame")
    label("fail")
    lui(3, 8)  # GPIO bit15 is the sticky firmware failure signature
    store(3, 1, 0x54)
    branch(0, 0, "fail")
    for index, rs1, rs2, target, fn in branches:
        delta = labels[target] - 4 * index
        assert -4096 <= delta < 4096 and delta % 2 == 0
        value = delta & 8191
        words[index] = (
            ((value >> 12) << 31)
            | (((value >> 5) & 63) << 25)
            | (rs2 << 20)
            | (rs1 << 15)
            | (fn << 12)
            | (((value >> 1) & 15) << 8)
            | (((value >> 11) & 1) << 7)
            | 0x63
        )
    assert len(words) < 2016
    return "".join(f"{w:08x}\n" for w in words + [0x13] * (2016 - len(words)))
