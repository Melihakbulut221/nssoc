# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""TX-independent scalar serial encoder and ordered public-byte oracle."""

from collections import deque
import os
import zlib
import cocotb
from cocotb.triggers import Timer

MAXIMUM = int(os.environ.get("PCIE_WIDE_MAX_BYTES", "150"))
RING = 1 << (((MAXIMUM + 2) // 4 + 15).bit_length())
SEEDS = (0x1DBFBC, 0x0607BB, 0x1EC760, 0x18C0DB)


def crc4(length):
    x = int(f"{length:011b}"[::-1], 2) << 4
    for bit in range(14, 3, -1):
        if x & (1 << bit):
            x ^= 0x13 << (bit - 4)
    return x


def tlp(sequence, payload=0, four=False, zero=False):
    count = (payload // 4 if payload else 1) & 1023
    h = bytes(
        (
            sequence >> 8,
            sequence & 255,
            (0x40 if payload else 0) | (0x20 if four else 0),
            0,
            count >> 8,
            count & 255,
        )
    ) + bytes.fromhex("1234567800001000")
    if four:
        h += bytes.fromhex("00000001")
    h += (
        bytes(payload)
        if zero
        else bytes((i * 37 + sequence + 9) & 255 for i in range(payload))
    )
    return h + zlib.crc32(h).to_bytes(4, "little")


def wire_tlp(data, nullify=False):
    if nullify:
        data = data[:-4] + bytes(b ^ 255 for b in data[-4:])
    count = (len(data) + 2) // 4
    c = crc4(count)
    parity = (count.bit_count() + c.bit_count()) & 1
    seq = int.from_bytes(data[:2], "big")
    token = bytes(
        (
            (count & 15) * 16 + 15,
            (count >> 4) | parity * 128,
            c * 16 + (seq >> 8),
            seq & 255,
        )
    )
    return token + data[2:] + (bytes.fromhex("c0c0c0c0") if nullify else b"")


def dllp(body):
    assert len(body) == 4
    # Independent normal-polynomial serial reference; RTL uses reflected
    # literal GF(2) transforms and does not share this implementation.
    r = 0xFFFF
    for byte in body:
        for bit in range(8):
            feedback = ((r >> 15) ^ (byte >> bit)) & 1
            r = (r << 1) & 0xFFFF
            if feedback:
                r ^= 0x100B
    r ^= 0xFFFF
    crc = bytes(int(f"{(r >> shift) & 255:08b}"[::-1], 2) for shift in (8, 0))
    return body + crc


def wire_dllp(data):
    assert len(data) == 6
    return bytes.fromhex("f0ac") + data


def serial_words(data, bad_header=False):
    data += bytes((-len(data)) % 1024)
    states = list(SEEDS)
    bits = [[] for _ in range(4)]
    for block in range(len(data) // 64):
        for lane in range(4):
            bits[lane] += [int(bad_header and block == 0 and lane == 0), 1]
            for byte_number in range(16):
                v = data[block * 64 + byte_number * 4 + lane]
                for bit in range(8):
                    s = states[lane]
                    out = s >> 22
                    bits[lane].append(((v >> bit) & 1) ^ out)
                    s = (s * 2) & 0x7FFFFF
                    if out:
                        for exponent in (21, 16, 8, 5, 2, 0):
                            s ^= 1 << exponent
                    states[lane] = s
    return [
        sum(bits[l][base + k] << (l * 32 + k) for l in range(4) for k in range(32))
        for base in range(0, len(bits[0]), 32)
    ]


class Ports:
    def __init__(self, d):
        self.d = d
        self.expected = deque()
        self.partial = bytearray()
        self.held = None
        self.completed = self.good = self.nullified = self.errors = self.ends = 0
        self.max_good_per_cycle = 0
        self.crc_bad = 0
        self.verdicts = []
        self.null_sequences = []
        self.residues = set()
        self.check_ownership = False
        self.descriptor_ready = True
        self.expected_descriptors = deque()
        self.body_owners = deque()
        self.current_owner = None
        self.descriptor_held = None
        self.seen_descriptors = 0
        self.max_descriptors = 0

    async def cycle(
        self, word=0, ready=True, start=False, reset=False, flush=False, abort=False
    ):
        d = self.d
        d.descriptor_ready_i.value = int(self.descriptor_ready)
        d.clk_i.value = 0
        d.rst_ni.value = int(not reset)
        d.flush_i.value = int(flush)
        d.stream_start_i.value = int(start)
        d.stream_abort_i.value = int(abort)
        d.word_i.value = word
        d.ready_i.value = int(ready)
        await Timer(2, unit="ns")
        valid = int(d.valid_o.value)
        fault = int(d.framing_error_o.value) or int(d.overflow_o.value)
        if reset or flush or start or abort:
            assert not valid
            self.held = None
        elif valid:
            beat = tuple(
                int(getattr(d, k).value)
                for k in ("data_o", "keep_o", "sop_o", "eop_o", "dllp_o", "sequence_o")
            )
            if self.held is not None:
                assert beat == self.held, "held wide beat changed"
            self.held = beat if not ready else None
            data, keep, sop, eop, dllp, seq = beat
            assert keep and not ((sop | eop | dllp) & ~keep), (
                "empty beat or metadata outside keep"
            )
            if ready:
                for i in range(16):
                    if not (keep >> i) & 1:
                        continue
                    assert self.expected, "unexpected/nullified packet escaped"
                    expected, kind = self.expected[0]
                    assert bool((sop >> i) & 1) == (not self.partial), (
                        "SOP byte position"
                    )
                    assert bool((dllp >> i) & 1) == kind, "packet type"
                    assert ((seq >> (12 * (i // 4))) & 4095) == (
                        0 if kind else int.from_bytes(expected[:2], "big")
                    ), "sequence per DWORD"
                    self.partial.append((data >> (8 * i)) & 255)
                    assert len(self.partial) <= len(expected)
                    assert bool((eop >> i) & 1) == (
                        len(self.partial) == len(expected)
                    ), "EOP byte position"
                    if len(self.partial) == len(expected):
                        assert self.partial == expected, "ordered packet bytes"
                        self.expected.popleft()
                        self.partial.clear()
                        self.completed += 1
        elif self.held is not None:
            assert fault or int(d.halted_o.value), (
                "held beat vanished without public fault"
            )
            self.held = None
        if self.check_ownership:
            quiet = reset or flush or start or abort
            mask = int(d.descriptor_valid_o.value)
            assert mask in (0, 1, 3, 7, 15), "descriptor prefix"
            desc = tuple(
                int(getattr(d, k).value)
                for k in (
                    "descriptor_valid_o",
                    "descriptor_owner_o",
                    "descriptor_sequence_o",
                    "descriptor_bytes_o",
                    "descriptor_good_o",
                    "descriptor_nullified_o",
                    "descriptor_crc_bad_o",
                    "descriptor_dllp_o",
                )
            )
            if quiet:
                assert not mask, "descriptor visible during epoch invalidation"
                self.descriptor_held = None
                self.current_owner = None
            elif mask:
                if self.descriptor_held is not None:
                    assert desc == self.descriptor_held, "held descriptor changed"
                self.descriptor_held = desc if not self.descriptor_ready else None
                if self.descriptor_ready:
                    self.max_descriptors = max(self.max_descriptors, mask.bit_count())
                    for slot in range(mask.bit_count()):
                        assert self.expected_descriptors, "unexpected descriptor"
                        good, null, bad = ((desc[k] >> slot) & 1 for k in (4, 5, 6))
                        assert good + null + bad == 1, (
                            "one precise integrity disposition"
                        )
                        got = (
                            (desc[1] >> (slot * 6)) & 63,
                            (desc[2] >> (slot * 12)) & 4095,
                            (desc[3] >> (slot * 13)) & 8191,
                            bool((desc[7] >> slot) & 1),
                            "good" if good else "null" if null else "bad",
                        )
                        assert got == self.expected_descriptors.popleft(), (
                            "ordered owned descriptor",
                            got,
                        )
                        self.seen_descriptors += 1
            elif self.descriptor_held is not None:
                assert fault or int(d.halted_o.value), (
                    "held descriptor silently vanished"
                )
                self.descriptor_held = None
            if not quiet and valid and ready:
                owners = int(d.owner_o.value)
                for byte in range(16):
                    if not (keep >> byte) & 1:
                        continue
                    owner = (owners >> ((byte // 4) * 6)) & 63
                    if (sop >> byte) & 1:
                        assert self.current_owner is None and self.body_owners
                        self.current_owner = self.body_owners.popleft()
                    assert self.current_owner == owner, (
                        "body/descriptor ownership mismatch"
                    )
                    if (eop >> byte) & 1:
                        self.current_owner = None
        d.clk_i.value = 1
        await Timer(2, unit="ns")
        good = int(d.packet_good_o.value)
        null = int(d.packet_nullified_o.value)
        bad = int(d.packet_crc_bad_o.value)
        kind = int(d.packet_dllp_o.value)
        assert not (good & null or good & bad or null & bad), (
            "inconsistent integrity verdict"
        )
        self.crc_bad += bad.bit_count()
        sequences = int(d.packet_sequence_o.value)
        self.good += good.bit_count()
        self.max_good_per_cycle = max(self.max_good_per_cycle, good.bit_count())
        self.nullified += null.bit_count()
        self.errors += int(d.framing_error_o.value)
        self.ends += int(d.stream_end_o.value)
        for i in range(4):
            if (good | null | bad) & (1 << i):
                self.verdicts.append(
                    (
                        (sequences >> (i * 12)) & 4095,
                        bool(kind & (1 << i)),
                        "good"
                        if good & (1 << i)
                        else "null"
                        if null & (1 << i)
                        else "bad",
                    )
                )
            if null & (1 << i):
                self.null_sequences.append((sequences >> (i * 12)) & 4095)

    async def begin(self):
        self.expected.clear()
        self.partial.clear()
        await self.cycle(reset=True)
        await self.cycle(start=True)

    async def send(self, raw, ready=lambda n: True, bad_header=False, tail_blocks=32):
        for n, w in enumerate(serial_words(raw + bytes(tail_blocks * 64), bad_header)):
            self.residues.add((32 * n) % 130)
            await self.cycle(w, ready=ready(n))

    def drained(self):
        assert not self.expected and not self.partial, "packet output not drained"
        assert not int(self.d.overflow_o.value) and not int(self.d.halted_o.value), (
            "unexpected finite-buffer fault"
        )


@cocotb.test()
async def sustained_minimum_packets_exceed_every_buffer(d):
    p = Ports(d)
    await p.begin()
    packets = [tlp(i) for i in range(1024)]
    p.expected.extend((x, False) for x in packets)
    await p.send(b"".join(map(wire_tlp, packets)))
    p.drained()
    assert p.completed == p.good == 1024 and p.errors == 0 and len(p.residues) == 65
    await p.begin()
    base = p.completed
    good = p.good
    packets = [dllp(bytes(((i + k * 41) & 255 for k in range(4)))) for i in range(4096)]
    p.expected.extend((x, True) for x in packets)
    await p.send(b"".join(map(wire_dllp, packets)))
    p.drained()
    assert (
        p.completed - base == p.good - good == 4096
        and p.max_good_per_cycle >= 2
        and p.errors == 0
    )


@cocotb.test()
async def maximum_zero_packets_cross_blocks_and_verdict_wrap(d):
    p = Ports(d)
    await p.begin()
    payload = 4096 if MAXIMUM == 4118 else 128
    count = 6 if MAXIMUM == 4118 else 64
    packets = [
        tlp(i + 7, payload=payload, four=True, zero=(i % 2 == 0)) for i in range(count)
    ]
    assert len(packets[0]) == MAXIMUM
    p.expected.extend((x, False) for x in packets)
    await p.send(b"".join(map(wire_tlp, packets)), tail_blocks=96)
    p.drained()
    assert p.completed == p.good == count and p.errors == 0


@cocotb.test()
async def all65_partial_raw_abort_phases_restart_exactly(d):
    p = Ports(d)
    for phase in range(65):
        await p.begin()
        raw = serial_words(bytes(2048))
        for word in raw[:phase]:
            await p.cycle(word)
        await p.cycle(abort=True)
        assert int(d.halted_o.value)
        await p.cycle(start=True)
        data = tlp(phase)
        p.expected.append((data, False))
        before = p.completed
        await p.send(wire_tlp(data), tail_blocks=16)
        p.drained()
        assert p.completed == before + 1
    assert p.errors == 65


@cocotb.test()
async def edb_quarantine_and_eds_release_drain(d):
    p = Ports(d)
    await p.begin()
    a, b = tlp(0x411), tlp(0x422, payload=128)
    p.expected.append((b, False))
    await p.send(wire_tlp(a, True) + wire_tlp(b))
    p.drained()
    assert p.completed == 1 and p.nullified == 1 and p.null_sequences == [0x411]
    await p.begin()
    before = p.completed
    data = tlp(0x733)
    p.expected.append((data, False))
    raw = bytes(40) + wire_tlp(data) + bytes.fromhex("1f809000")
    assert len(raw) == 64
    await p.send(raw, ready=lambda n: n > 50)
    p.drained()
    assert (
        p.completed == before + 1
        and p.ends == 1
        and not int(d.active_o.value)
        and p.errors == 0
    )


@cocotb.test()
async def actual_full_ring_replacement_and_late_stall_overflow(d):
    p = Ports(d)
    packets = [
        tlp(i, payload=4096 if MAXIMUM == 4118 else 128, four=True) for i in range(4)
    ]
    raw = serial_words(
        b"".join(map(wire_tlp, packets)) + bytes(max(4096, (RING + 32) * 4))
    )
    await p.begin()
    failure = None
    for n, w in enumerate(raw):
        await p.cycle(w, ready=False)
        if int(d.overflow_o.value):
            failure = n
            break
    assert failure is not None and int(d.halted_o.value), (
        "real finite ring overflow required"
    )
    await p.cycle(start=True)
    assert not int(d.overflow_o.value)
    base = p.completed
    p.expected.extend((x, False) for x in packets)
    for n, w in enumerate(raw):
        await p.cycle(w, ready=n >= failure)
    p.drained()
    assert p.completed - base == len(packets), (
        "same-edge retirement must allow the full ring replacement"
    )
    # Reset/flush dominates simultaneous start and invalidates all ownership.
    await p.cycle(start=True, flush=True)
    assert not int(d.active_o.value) and not int(d.valid_o.value)


@cocotb.test()
async def malformed_tokens_and_headers_never_release_quarantine(d):
    p = Ports(d)
    data = tlp(0x62)
    wire = wire_tlp(data)
    bad_stp = bytearray(wire)
    bad_stp[2] ^= 0x10
    bad_stp[1] ^= 0x80  # CRC wrong but parity deliberately preserved
    bad_header = bytearray(data)
    bad_header[2] ^= 0x40
    variants = [
        (bytes(bad_stp), False),
        (wire_tlp(bytes(bad_header)), False),
        (wire + bytes.fromhex("11223344"), False),
        (bytes.fromhex("c0c0c0c0"), False),
        (bytes(64), True),
    ]
    for raw, bad in variants:
        await p.begin()
        before = p.errors
        await p.send(raw, bad_header=bad, tail_blocks=16)
        assert (
            p.errors == before + 1
            and int(d.halted_o.value)
            and not int(d.active_o.value)
        )
        assert not p.expected and not p.partial
        await p.cycle(start=True)
        x = tlp(0x98)
        p.expected.append((x, False))
        await p.send(wire_tlp(x), tail_blocks=16)
        p.drained()


@cocotb.test()
async def bounded_stalls_preserve_all_wide_metadata(d):
    p = Ports(d)
    await p.begin()
    items = []
    raw = b""
    for i in range(512):
        if i % 3 == 0:
            x = dllp(bytes(4))
            items.append((x, True))
            raw += wire_dllp(x)
        else:
            x = tlp(i, payload=128 if i % 7 == 0 else 0, zero=True)
            items.append((x, False))
            raw += wire_tlp(x)
    p.expected.extend(items)
    await p.send(raw, ready=lambda n: not (100 <= n % 1000 < 104), tail_blocks=96)
    p.drained()
    assert p.completed == len(items) and p.errors == 0


@cocotb.test()
async def verdict_tag_reuse_cannot_nullify_an_older_live_tail(d):
    p = Ports(d)
    await p.begin()
    raw = b""
    discarded = []
    for repeat in range(4):
        old = tlp(0x610 + repeat, payload=4096 if MAXIMUM == 4118 else 128, four=True)
        bad = tlp(0x620 + repeat)
        p.expected.append((old, False))
        discarded.append(0x620 + repeat)
        # New SOP uses the same ring address but a different extended pointer.
        # Two accepted beats free8physical slots; a merely held beat frees none.
        # Complete2R slots per pattern, then reuse both extended tag generations.
        raw += (
            wire_tlp(old)
            + bytes(RING * 4 - len(wire_tlp(old)))
            + wire_tlp(bad, True)
            + bytes(RING * 4 - 24)
        )
    assert len(raw) == 8 * RING * 4
    await p.send(
        raw,
        ready=lambda n: not (len(p.partial) >= 30 and p.nullified <= p.completed),
        tail_blocks=96,
    )
    p.drained()
    assert (
        p.completed == 4
        and p.nullified == 4
        and p.null_sequences == discarded
        and p.errors == 0
    )


@cocotb.test()
async def start_without_abort_reseeds_and_discards_prior_epoch(d):
    p = Ports(d)
    await p.begin()
    await p.send(bytes(64 * 24), tail_blocks=0)
    await p.cycle(start=True)
    data = tlp(0x552)
    p.expected.append((data, False))
    await p.send(wire_tlp(data), tail_blocks=16)
    p.drained()
    assert p.completed == 1 and p.good == 1 and p.errors == 0


@cocotb.test()
async def primary_trace_crc_vectors_and_adjacent_bad_dllps(d):
    p = Ports(d)
    await p.begin()
    golden = [
        bytes.fromhex(x) for x in ("00000003504e", "00000004370c", "100000021a32")
    ]
    for x in golden:
        assert dllp(x[:4]) == x
    raw = b""
    expected_events = []
    for i in range(128):
        for good in golden:
            bad = bytearray(good)
            bad[4 + i % 2] ^= 1 << (i % 8)
            raw += wire_dllp(good) + wire_dllp(bytes(bad))
            p.expected.append((good, True))
            expected_events += [(0, True, "good"), (0, True, "bad")]
    await p.send(raw)
    p.drained()
    assert p.verdicts == expected_events
    assert p.good == p.completed == p.crc_bad == 384 and p.errors == 0


@cocotb.test()
async def tlp_crc_coverage_residue_nullification_and_successor(d):
    p = Ports(d)
    await p.begin()
    raw = b""
    events = []
    original = tlp(0xABC, payload=128, four=True)
    # Sequence, reserved header fields, payload ends and every LCRC bit.
    mutations = [(0, 1), (1, 1), (6, 8), (17, 4), (len(original) - 5, 32)]
    mutations += [
        (len(original) - 4 + j, 1 << bit) for j in range(4) for bit in range(8)
    ]
    for index, (where, mask) in enumerate(mutations):
        bad = bytearray(original)
        bad[where] ^= mask
        bad = bytes(bad)
        seq = int.from_bytes(bad[:2], "big")
        successor = tlp(index)
        raw += wire_tlp(bad) + wire_tlp(successor)
        p.expected.append((successor, False))
        events += [(seq, False, "bad"), (index, False, "good")]
    # Valid inverse + EDB is nullified; normal CRC + EDB is corrupt.
    raw += wire_tlp(original, True) + wire_tlp(original) + bytes.fromhex("c0c0c0c0")
    events += [(0xABC, False, "null"), (0xABC, False, "bad")]
    # Inverse LCRC without EDB must not become a normal good packet.
    inverse = original[:-4] + bytes(x ^ 255 for x in original[-4:])
    last = tlp(0xFFF)
    raw += wire_tlp(inverse) + wire_tlp(last)
    p.expected.append((last, False))
    events += [(0xABC, False, "bad"), (0xFFF, False, "good")]
    await p.send(raw, tail_blocks=96)
    p.drained()
    assert p.verdicts == events
    assert p.crc_bad == len(mutations) + 2 and p.nullified == 1 and p.errors == 0


@cocotb.test()
async def incomplete_maximum_packet_cannot_release_any_byte(d):
    p = Ports(d)
    await p.begin()
    packet = tlp(0x815, payload=4096 if MAXIMUM == 4118 else 128, four=True)
    p.expected.append((packet, False))
    wire = wire_tlp(packet)
    raw = serial_words(wire + bytes(4096))
    last = len(wire) - 1
    final_crc_bit = (last // 64) * 130 + 2 + ((last % 64) // 4 + 1) * 8
    for n, w in enumerate(raw):
        await p.cycle(w)
        if (n + 1) * 32 < final_crc_bit:
            assert p.good == 0 and p.completed == 0 and not p.partial and p.crc_bad == 0
    p.drained()
    assert p.good == p.completed == 1 and p.errors == 0


async def owned_begin(d):
    p = Ports(d)
    p.check_ownership = True
    await p.begin()
    return p


def add_owned(p, packets):
    raw = bytearray()
    for index, (data, kind, status) in enumerate(packets):
        owner = index & 63
        sequence = 0 if kind else int.from_bytes(data[:2], "big")
        p.expected_descriptors.append((owner, sequence, len(data), kind, status))
        if status == "good":
            p.expected.append((data, kind))
            p.body_owners.append(owner)
        wire = wire_dllp(data) if kind else wire_tlp(data, nullify=status == "null")
        if status == "bad":
            wire = wire[:-1] + bytes([wire[-1] ^ 1])
        raw += wire
    return bytes(raw)


@cocotb.test()
async def ownership_long_generation_sequence_wrap(d):
    p = await owned_begin(d)
    packets = []
    for i in range(1200):
        kind = i % 3 != 0
        data = (
            dllp(bytes((0, 0, i >> 8, i & 255)))
            if kind
            else tlp((4095 + i // 3) & 4095, zero=True)
        )
        status = (
            "bad" if i % 17 == 1 else "null" if not kind and i % 19 == 0 else "good"
        )
        packets.append((data, kind, status))
    raw = add_owned(p, packets)
    for i, word in enumerate(serial_words(raw + bytes(4096))):
        p.descriptor_ready = i % 79 >= 3
        await p.cycle(word, ready=i % 151 >= 2)
    p.drained()
    assert not p.expected_descriptors and not p.body_owners and p.current_owner is None
    assert p.seen_descriptors == 1200 and p.max_descriptors >= 2


@cocotb.test()
async def descriptors_hold_while_body_drains(d):
    p = await owned_begin(d)
    packets = [
        (dllp(bytes((0, 0, 0, i))), True, "good" if i % 3 else "bad") for i in range(20)
    ]
    raw = add_owned(p, packets)
    for i, word in enumerate(serial_words(raw + bytes(4096))):
        p.descriptor_ready = i >= 90
        await p.cycle(word)
        if i == 89:
            assert p.completed == sum(x[2] == "good" for x in packets)
            assert p.seen_descriptors == 0 and p.descriptor_held is not None
    p.drained()
    assert not p.expected_descriptors and p.seen_descriptors == 20


@cocotb.test()
async def body_holds_after_descriptors_retired(d):
    p = await owned_begin(d)
    packets = [(dllp(bytes((0, 0, 0, i))), True, "good") for i in range(12)]
    raw = add_owned(p, packets)
    for i, word in enumerate(serial_words(raw + bytes(4096))):
        await p.cycle(word, ready=i >= 18)
        if i == 17:
            assert p.seen_descriptors == 12 and p.completed == 0
            assert p.held is not None
    p.drained()
    assert not p.expected_descriptors and not p.body_owners


@cocotb.test()
async def bad_descriptors_fill_owner_slots_fail_closed(d):
    p = await owned_begin(d)
    packets = [(dllp(bytes((0, 0, 0, i))), True, "bad") for i in range(80)]
    raw = add_owned(p, packets)
    p.descriptor_ready = False
    for word in serial_words(raw + bytes(1024)):
        await p.cycle(word)
    assert int(d.overflow_o.value) and int(d.halted_o.value)
    assert p.completed == 0 and p.seen_descriptors == 0
    p.expected_descriptors.clear()
    p.descriptor_ready = True
    await p.cycle(start=True)
    raw = add_owned(p, [(dllp(bytes.fromhex("00000003")), True, "good")])
    for word in serial_words(raw + bytes(1024)):
        await p.cycle(word)
    p.drained()
    assert p.seen_descriptors == 1 and not p.expected_descriptors


@cocotb.test()
async def flush_invalidates_both_held_interfaces(d):
    p = await owned_begin(d)
    raw = add_owned(p, [(tlp(4095), False, "good")])
    words = serial_words(raw + bytes(1024))
    p.descriptor_ready = False
    for word in words[:18]:
        await p.cycle(word, ready=False)
    assert p.held is not None and p.descriptor_held is not None
    epoch = int(d.epoch_o.value)
    await p.cycle(flush=True)
    assert int(d.epoch_o.value) != epoch
    p.expected.clear()
    p.expected_descriptors.clear()
    p.body_owners.clear()
    p.descriptor_ready = True
    await p.cycle(start=True)
    raw = add_owned(p, [(tlp(4095, zero=True), False, "good")])
    for word in serial_words(raw + bytes(1024)):
        await p.cycle(word)
    p.drained()
    assert not p.expected_descriptors and p.current_owner is None


@cocotb.test()
async def held_body_prevents_owner_slot_reuse(d):
    p = await owned_begin(d)
    packets = [(dllp(bytes(4)), True, "good")] + [
        (dllp(bytes((0, 0, 0, i))), True, "bad") for i in range(80)
    ]
    raw = add_owned(p, packets)
    for word in serial_words(raw + bytes(1024)):
        await p.cycle(word, ready=False)
    assert int(d.overflow_o.value) and int(d.halted_o.value), (
        "live owner slot silently reused"
    )
    assert p.completed == 0 and p.seen_descriptors <= 32
    if MAXIMUM == 4118:
        # R2048 can hold this entire wire burst. The32owner limit, not ring
        # capacity, must stop allocation at the still-held first body's slot.
        # Descriptor output pipeline may stillhold thelasttwo when globalabort
        # invalidates pendingrecords; countthe32 precise parserverdicts instead.
        assert p.good + p.crc_bad + p.nullified == 32, (
            "exact32 completedSOP obligations before owner overflow"
        )


@cocotb.test()
async def same_edge_descriptor_release_allows_full_owner_replace(d):
    packets = [(dllp(bytes((0, 0, i >> 8, i & 255))), True, "bad") for i in range(100)]
    p = await owned_begin(d)
    raw = add_owned(p, packets)
    words = serial_words(raw + bytes(2048))
    p.descriptor_ready = False
    failure = None
    for i, word in enumerate(words):
        await p.cycle(word)
        if int(d.overflow_o.value):
            failure = i
            break
    assert failure is not None and p.seen_descriptors == 0
    p = await owned_begin(d)
    add_owned(p, packets)
    for i, word in enumerate(words):
        p.descriptor_ready = i >= failure
        await p.cycle(word)
    p.drained()
    assert p.seen_descriptors == 100 and not p.expected_descriptors


@cocotb.test()
async def same_edge_body_eop_releases_reallocated_owner(d):
    packets = [(dllp(bytes(4)), True, "good")] + [
        (dllp(bytes((0, 0, 0, i))), True, "bad") for i in range(80)
    ]
    p = await owned_begin(d)
    raw = add_owned(p, packets)
    words = serial_words(raw + bytes(2048))
    failure = None
    for i, word in enumerate(words):
        await p.cycle(word, ready=False)
        if int(d.overflow_o.value):
            failure = i
            break
    assert failure is not None and p.completed == 0
    p = await owned_begin(d)
    add_owned(p, packets)
    for i, word in enumerate(words):
        await p.cycle(word, ready=i >= failure)
    p.drained()
    assert p.seen_descriptors == 81 and not p.expected_descriptors
    assert p.completed == 1 and not p.body_owners
