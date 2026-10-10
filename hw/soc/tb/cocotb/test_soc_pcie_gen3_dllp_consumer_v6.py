# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent ordered packet/field oracle at the CRC-qualified ownership boundary."""

from collections import deque
import random
import zlib
import cocotb
from cocotb.triggers import Timer

INPUTS = [
    "body_valid_i",
    "body_data_i",
    "body_keep_i",
    "body_sop_i",
    "body_eop_i",
    "body_dllp_i",
    "body_sequence_i",
    "body_owner_i",
    "descriptor_valid_i",
    "descriptor_owner_i",
    "descriptor_sequence_i",
    "descriptor_bytes_i",
    "descriptor_good_i",
    "descriptor_nullified_i",
    "descriptor_crc_bad_i",
    "descriptor_dllp_i",
]
EVENTS = [
    ("event_owner_o", 6),
    ("event_sequence_o", 12),
    ("event_bytes_o", 13),
    ("event_kind_o", 4),
    ("event_raw_dllp_o", 32),
    ("event_ack_sequence_o", 12),
    ("event_fc_phase_o", 2),
    ("event_fc_class_o", 2),
    ("event_fc_header_o", 8),
    ("event_fc_data_o", 12),
    ("event_packet_dllp_o", 1),
]


def crc16(data):
    r = 65535
    for byte in data:
        for bit in range(8):
            feedback = ((r >> 15) ^ (byte >> bit)) & 1
            r = (r << 1) & 65535
            if feedback:
                r ^= 0x100B
    r ^= 65535
    return bytes(int(f"{(r >> s) & 255:08b}"[::-1], 2) for s in (8, 0))


def packet(index, kind=0, seq=None, status=0, body=None):
    seq = (4090 + index) % 4096 if seq is None else seq
    is_dllp = kind != 0
    if is_dllp:
        if body is None:
            tag = (
                0,
                0x10,
                0x40,
                0x50,
                0x60,
                0xC0,
                0xD0,
                0xE0,
                0x80,
                0x90,
                0xA0,
                0x41,
                0x20,
            )[index % 13]
            head = (index * 29) & 255
            credit = (index * 317) & 4095
            body = bytes(
                (tag, head >> 2, ((head & 3) << 6) | (credit >> 8), credit & 255)
            )
        data = body + crc16(body)
    else:
        h = seq.to_bytes(2, "big") + bytes.fromhex("000000011234567800001000")
        data = h + zlib.crc32(h).to_bytes(4, "little")
    return dict(
        owner=index % 64,
        seq=0 if is_dllp else seq,
        data=data,
        dllp=is_dllp,
        status=status,
    )


def expected_old(p):
    owner, seq, size = p["owner"], p["seq"], len(p["data"])
    if p["status"]:
        return (owner, seq, size, p["status"], 0, 0, 0, 0, 0, 0)
    if not p["dllp"]:
        return (owner, seq, size, 0, 0, 0, 0, 0, 0, 0)
    b0, b1, b2, b3 = p["data"][:4]
    word = int.from_bytes(p["data"][:4], "little")
    if b0 in (0, 0x10):
        return (
            owner,
            seq,
            size,
            3 if b0 == 0 else 4,
            word,
            ((b2 & 15) << 8) | b3,
            0,
            0,
            0,
            0,
        )
    if b0 in (0x40, 0x50, 0x60, 0xC0, 0xD0, 0xE0, 0x80, 0x90, 0xA0):
        return (
            owner,
            seq,
            size,
            5,
            word,
            0,
            {1: 0, 3: 1, 2: 2}[b0 >> 6],
            (b0 >> 4) & 3,
            ((b1 & 63) << 2) | (b2 >> 6),
            ((b2 & 15) << 8) | b3,
        )
    return (owner, seq, size, 6, word, 0, 0, 0, 0, 0)


def expected(p):
    return expected_old(p)+(int(p["dllp"]),)


def body_words(p):
    if p["status"]:
        return []
    data = p["data"]
    chunks = [data[:2]] + [data[i : i + 4] for i in range(2, len(data), 4)]
    return [
        (
            int.from_bytes(v, "little"),
            (1 << len(v)) - 1,
            1 if i == 0 else 0,
            8 if i == len(chunks) - 1 else 0,
            (1 << len(v)) - 1 if p["dllp"] else 0,
            p["seq"],
            p["owner"],
        )
        for i, v in enumerate(chunks)
    ]


def drive(d, descs, words):
    for n in INPUTS:
        getattr(d, n).value = 0
    d.descriptor_valid_i.value = (1 << len(descs)) - 1
    for name, width, key in [
        ("descriptor_owner_i", 6, "owner"),
        ("descriptor_sequence_i", 12, "seq"),
    ]:
        getattr(d, name).value = sum(p[key] << (width * i) for i, p in enumerate(descs))
    d.descriptor_bytes_i.value = sum(
        len(p["data"]) << (13 * i) for i, p in enumerate(descs)
    )
    for name, key in [
        ("descriptor_good_i", 0),
        ("descriptor_crc_bad_i", 1),
        ("descriptor_nullified_i", 2),
    ]:
        getattr(d, name).value = sum(
            (p["status"] == key) << i for i, p in enumerate(descs)
        )
    d.descriptor_dllp_i.value = sum(p["dllp"] << i for i, p in enumerate(descs))
    d.body_valid_i.value = bool(words)
    for pos, (name, width) in enumerate(
        [
            ("body_data_i", 32),
            ("body_keep_i", 4),
            ("body_sop_i", 4),
            ("body_eop_i", 4),
            ("body_dllp_i", 4),
            ("body_sequence_i", 12),
            ("body_owner_i", 6),
        ]
    ):
        getattr(d, name).value = sum(w[pos] << (width * i) for i, w in enumerate(words))


class Ports:
    def __init__(self, d, packets=()):
        self.d = d
        self.events = deque(expected(p) for p in packets)
        self.tlps = deque(p for p in packets if not p["dllp"] and not p["status"])
        self.partial = bytearray()
        self.held = None
        self.tlpheld = None
        self.max_events = 0
        self.accepted_events = 0

    async def step(self, descs=(), words=(), event_ready=1, tlp_ready=1):
        d = self.d
        d.clk_i.value = 0
        drive(d, descs, words)
        d.event_ready_i.value = event_ready
        d.tlp_ready_i.value = tlp_ready
        await Timer(2, unit="ns")
        assert not int(d.halted_o.value), "Unexpected fail-closed halt"
        mask = int(d.event_valid_o.value)
        assert mask in (0, 1, 3, 7, 15)
        bundle = (mask,) + tuple(int(getattr(d, n).value) for n, _ in EVENTS)
        if self.held is not None:
            assert bundle == self.held, "Held ordered event changed"
        self.held = bundle if mask and not event_ready else None
        if mask and event_ready:
            count = mask.bit_count()
            self.max_events = max(self.max_events, count)
            for i in range(count):
                got = tuple(
                    (int(getattr(d, n).value) >> (width * i)) & ((1 << width) - 1)
                    for n, width in EVENTS
                )
                assert self.events, "Unexpected/repeated event"
                assert got == self.events.popleft(), ("Ordered decode mismatch", got)
                self.accepted_events += 1
        t = (int(d.tlp_valid_o.value),) + tuple(
            int(getattr(d, n).value)
            for n in [
                "tlp_data_o",
                "tlp_keep_o",
                "tlp_sop_o",
                "tlp_eop_o",
                "tlp_sequence_o",
                "tlp_owner_o",
            ]
        )
        if self.tlpheld is not None:
            assert t == self.tlpheld, "Held TLP changed"
        self.tlpheld = t if t[0] and not tlp_ready else None
        if t[0] and tlp_ready:
            for lane in range(4):
                for b in range(4):
                    bit = lane * 4 + b
                    if (t[2] >> bit) & 1:
                        assert self.tlps, "Unexpected TLP body"
                        p = self.tlps[0]
                        assert ((t[5] >> (lane * 12)) & 4095) == p["seq"] and (
                            (t[6] >> (lane * 6)) & 63
                        ) == p["owner"]
                        assert bool((t[3] >> bit) & 1) == (not self.partial)
                        self.partial.append((t[1] >> (8 * bit)) & 255)
                        if (t[4] >> bit) & 1:
                            assert bytes(self.partial) == p["data"], (
                                "TLP body changed/dropped"
                            )
                            self.partial.clear()
                            self.tlps.popleft()
        accepted = (
            bool(descs) and int(d.descriptor_ready_o.value),
            bool(words) and int(d.body_ready_o.value),
        )
        d.clk_i.value = 1
        await Timer(2, unit="ns")
        return accepted

    async def drain(self):
        for _ in range(100):
            await self.step()
            if not self.events and not self.tlps and not self.partial:
                return
        raise AssertionError("Ordered events/body did not drain")


async def reset(d, epoch=1):
    d.rst_ni.value = 0
    d.flush_i.value = 0
    d.epoch_i.value = 0
    p = Ports(d)
    for _ in range(3):
        await p.step()
    d.rst_ni.value = 1
    d.epoch_i.value = epoch
    await p.step()
    await p.step()


async def run_packets(d, packets, stalls=False, delay_body=0, delay_desc=0):
    p = Ports(d, packets)
    ds = deque(packets)
    ws = deque(w for item in packets for w in body_words(item))
    descs = []
    words = []
    rng = random.Random(7341)
    body_stalls = 0
    for cycle in range(30000):
        if not descs and cycle >= delay_desc:
            descs = [ds.popleft() for _ in range(min(4, len(ds)))]
        if not words and cycle >= delay_body:
            words = [ws.popleft() for _ in range(min(4, len(ws)))]
        er = not stalls or rng.randrange(8) > 1
        tr = not stalls or rng.randrange(7) > 1
        da, ba = await p.step(descs, words, er, tr)
        if words and not ba:
            body_stalls += 1
        if da:
            descs = []
        if ba:
            words = []
        if not (ds or ws or descs or words):
            break
    else:
        raise AssertionError("Bounded source could not retire")
    await p.drain()
    assert not int(d.halted_o.value)
    return p, body_stalls


@cocotb.test()
async def sustained_two_dllps_per_cycle_and_sequence_wrap(d):
    await reset(d)
    packets = [
        packet(
            i,
            1,
            body=bytes(
                (
                    0 if i % 2 == 0 else 0x10,
                    0,
                    ((4090 + i) % 4096) >> 8,
                    (4090 + i) % 256,
                )
            ),
        )
        for i in range(1800)
    ]
    p, stalls = await run_packets(d, packets)
    assert p.max_events >= 2 and p.accepted_events == 1800
    assert stalls == 0, "Consumer inserted a sustained body/load bubble"


@cocotb.test()
async def mixed_fields_bad_null_and_independent_stalls(d):
    await reset(d)
    packets = [
        packet(
            i,
            0 if i % 5 == 0 else 1,
            status=2 if i % 35 == 0 else 1 if i % 11 == 0 else 0,
        )
        for i in range(1200)
    ]
    p, _ = await run_packets(d, packets, True, delay_body=11)
    assert p.max_events >= 2


@cocotb.test()
async def body_before_descriptor_reserved_bits_and_unknown_vc(d):
    await reset(d)
    bodies = [
        bytes.fromhex(x)
        for x in [
            "00fffabc",
            "10aaefff",
            "40ffeabc",
            "c0ffffff",
            "a0dfff01",
            "41000001",
            "20000001",
        ]
    ]
    packets = [packet(i, 1, body=bodies[i % len(bodies)]) for i in range(240)]
    await run_packets(d, packets, True, delay_desc=19)


@cocotb.test()
async def exact_id_full_replace_and_held_generation(d):
    await reset(d)
    packets = [packet(i, 1) for i in range(68)]
    p = Ports(d, packets)
    for i in range(0, 64, 2):
        pair = packets[i : i + 2]
        da, ba = await p.step(pair, [w for x in pair for w in body_words(x)], 0)
        assert da and ba
    pair = packets[64:66]
    words = [w for x in pair for w in body_words(x)]
    for _ in range(5):
        da, ba = await p.step(pair, words, 0)
        assert not da and not ba, "Held ID reused"
    da, ba = await p.step(pair, words, 1)
    assert da and ba, "Same-edge full replace lost"
    pair = packets[66:68]
    assert all(await p.step(pair, [w for x in pair for w in body_words(x)]))
    await p.drain()


@cocotb.test()
async def epoch_invalidates_both_halves_and_held_events(d):
    await reset(d)
    stale = [packet(i, 1) for i in range(4)]
    p = Ports(d, stale)
    await p.step(stale, [w for x in stale[:2] for w in body_words(x)], 0)
    await p.step(words=[w for x in stale[2:] for w in body_words(x)], event_ready=0)
    d.epoch_i.value = 2
    await Ports(d).step()
    await run_packets(d, [packet(i, 1) for i in range(180)])


@cocotb.test()
async def malformed_ownership_fails_closed_then_epoch_restarts(d):
    await reset(d)
    p = packet(0, 1)
    p["owner"] = 1
    await Ports(d).step([p])
    assert int(d.halted_o.value), "Out-of-order descriptor accepted"
    d.epoch_i.value = 2
    # The epoch mismatch masks outputs immediately and clears fault at the edge.
    d.clk_i.value = 0
    drive(d, (), ())
    await Timer(2, unit="ns")
    assert int(d.event_valid_o.value) == 0 and int(d.body_ready_o.value) == 0
    d.clk_i.value = 1
    await Timer(2, unit="ns")
    await run_packets(d, [packet(i, 1) for i in range(20)])


@cocotb.test()
async def bad_packet_type_survives_stalls_and_owner_wrap(d):
    await reset(d)
    packets=[packet(i,i%2,status=1) for i in range(256)]
    p,_=await run_packets(d,packets,True,delay_body=0)
    assert p.accepted_events==256 and p.max_events>=2


@cocotb.test()
async def packet_type_masked_on_flush_and_epoch_change(d):
    await reset(d)
    p=Ports(d,[packet(0,1,status=1)])
    await p.step([packet(0,1,status=1)],event_ready=0)
    await p.step(event_ready=0)
    assert int(d.event_packet_dllp_o.value)==1
    d.clk_i.value=0;d.flush_i.value=1
    await Timer(1,unit='ns')
    assert int(d.event_valid_o.value)==int(d.event_packet_dllp_o.value)==0,'Packet type escaped flush mask'
    d.flush_i.value=0;d.epoch_i.value=2
    await Timer(1,unit='ns')
    assert int(d.event_valid_o.value)==int(d.event_packet_dllp_o.value)==0,'Packet type escaped epoch mask'
    d.clk_i.value=1;await Timer(2,unit='ns')
    await run_packets(d,[packet(i,i%2,status=1) for i in range(32)])
