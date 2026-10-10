# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Concurrent real CPU/Ethernet/PCIe via public ports, never internal drives."""

import os
import zlib

import cocotb
from cocotb.triggers import Timer
from test_soc_pcie_soc import Bench
from pcie_rx_flow_common import BAR, CID, frame_bytes, request, response, tlp_bytes


class JointBench(Bench):
    def __init__(self, dut):
        super().__init__(dut)
        self.eth_frames = []
        self.eth_current = []
        self.eth_rx_queue = []
        self.eth_rx_current = []
        self.eth_gap = 0
        self.eth_tx_writes = 0
        self.eth_rx_reads = 0
        self.eth_before_mbist = 0
        self.joint_contentions = 0
        self.eth_task = None
        self.async_pcie = os.environ.get("JOINT_PCIE_ASYNC") == "1"
        self.half_ns = 2 if self.async_pcie else 10
        self.cpu_task = None

    async def ethernet(self):
        # Two independent 125 MHz clock phases; RX receives a whole captured
        # TX frame at wire speed, not a same-edge combinational loopback.
        d = self.d
        d.eth_tx_clk_i.value = 0
        d.eth_rx_clk_i.value = 0
        d.eth_rxd_i.value = 0
        d.eth_rx_dv_i.value = 0
        d.eth_rx_er_i.value = 0
        phase = 0
        while True:
            await Timer(2, unit="ns")
            phase = (phase + 2) % 8
            if phase == 0:
                d.eth_tx_clk_i.value = 1
            elif phase == 4:
                d.eth_tx_clk_i.value = 0
                if self.v("rst_ni"):
                    assert not self.v("eth_tx_er_o"), "MAC TX error"
                    if self.v("eth_tx_en_o"):
                        assert self.v("eth_mbist_done_o") == 3
                        self.eth_current.append(self.v("eth_txd_o"))
                    elif self.eth_current:
                        frame = bytes(self.eth_current)
                        self.eth_current.clear()
                        assert frame[:8] == b"\x55" * 7 + b"\xd5", frame.hex()
                        assert frame[8:-4] == bytes(range(60)), frame.hex()
                        assert frame[-4:] == zlib.crc32(frame[8:-4]).to_bytes(
                            4, "little"
                        )
                        self.eth_frames.append(frame)
                        self.eth_rx_queue.append(frame)
            elif phase == 2:
                d.eth_rx_clk_i.value = 1
            elif phase == 6:
                d.eth_rx_clk_i.value = 0
                if self.eth_rx_current:
                    d.eth_rxd_i.value = self.eth_rx_current.pop(0)
                    d.eth_rx_dv_i.value = 1
                else:
                    d.eth_rx_dv_i.value = 0
                    if self.eth_gap:
                        self.eth_gap -= 1
                    elif self.eth_rx_queue:
                        self.eth_rx_current = list(self.eth_rx_queue.pop(0))
                        self.eth_gap = 12

    async def tick(self, **kw):
        clock = self.d.pcie_clk_i if self.async_pcie else self.d.clk_i
        clock.value = 0
        for name, value in kw.items():
            getattr(self.d, name).value = value
        await Timer(self.half_ns, unit="ns")
        taken = self.v("rx_valid_i") and self.v("rx_ready_o")
        if not self.async_pcie:
            self.sample_cpu()
        self.sample_pcie()
        clock.value = 1
        await Timer(self.half_ns, unit="ns")
        return taken

    def sample_cpu(self):
        if self.v("rst_ni"):
            assert self.v("alerts_o") == 0, "CPU alert"
            assert not (self.v("gpio_o") & 0x8000), (
                "Firmware Ethernet data/status failure"
            )
            assert not self.v("eth_mbist_failed_o"), "Ethernet SRAM MBIST failure"
            assert not self.v("bus_error_o"), "Unexpected APB error"
            row = tuple(self.v(n) for n in ("bus_addr_o", "bus_write_o", "bus_data_o"))
            if self.v("cpu_access_o"):
                self.cpu.append(row)
                assert row[0] in (
                    0x2008,
                    0x2074,
                    0x1A000,
                    0x1A004,
                    0x1A008,
                    0x1A00C,
                    0x1A010,
                ), row
                assert not self.v("pcie_access_o"), "APB double acknowledgement"
                if row[0] == 0x1A008 and row[1]:
                    assert self.v("eth_mbist_done_o") == 3, "TX before MBIST completion"
                    self.eth_tx_writes += 1
                if row[0] == 0x1A00C and not row[1]:
                    index = self.eth_rx_reads % 60
                    expected = 0x80000000 | index | (0x100 if index == 59 else 0)
                    assert self.v("bus_read_data_o") == expected
                    self.eth_rx_reads += 1
            if self.v("pcie_access_o"):
                self.pcie.append(row)
                assert row[0] >> 12 == 2, "PCIe escaped GPIO BAR"
                self.eth_before_mbist += self.v("eth_mbist_done_o") != 3
            if self.v("contention_o"):
                self.contentions += 1
                self.joint_contentions += row[0] >> 12 == 0x1A
            gpio = self.v("gpio_o") & 1
            if self.prev_gpio is not None:
                self.edges += gpio != self.prev_gpio
            self.prev_gpio = gpio

    def sample_pcie(self):
        if self.v("rst_ni"):
            self.errors += self.v("error_o")
        if self.v("rst_ni") and self.v("link_up_i") and not self.v("retrain_done_i"):
            beat = tuple(
                self.v(n)
                for n in (
                    "tx_data_o",
                    "tx_sop_o",
                    "tx_eop_o",
                    "tx_dllp_o",
                    "tx_replay_o",
                )
            )
            if self.held is not None:
                assert self.v("tx_valid_o") and beat == self.held
            self.held = (
                beat if self.v("tx_valid_o") and not self.v("tx_ready_i") else None
            )
            if self.v("tx_valid_o") and self.v("tx_ready_i"):
                value, sop, eop, kind, replay = beat
                assert bool(sop) == (not self.partial)
                if sop:
                    self.kind, self.replay = kind, replay
                assert (kind, replay) == (self.kind, self.replay)
                self.partial.append(value)
                if eop:
                    self.frames.append((kind, replay, bytes(self.partial)))
                    self.partial.clear()
        else:
            self.partial.clear()
            self.held = None

    async def cpu_clock(self):
        self.d.clk_i.value = 0
        await Timer(7, unit="ns")
        while True:
            self.sample_cpu()
            self.d.clk_i.value = 1
            await Timer(10, unit="ns")
            self.d.clk_i.value = 0
            await Timer(10, unit="ns")

    async def reset(self):
        self.d.rst_ni.value = 0
        self.eth_task = cocotb.start_soon(self.ethernet())
        if self.async_pcie:
            self.cpu_task = cocotb.start_soon(self.cpu_clock())
        await self.tick(
            rst_ni=0,
            link_up_i=0,
            training_i=0,
            retrain_done_i=0,
            function_id_i=CID,
            rx_valid_i=0,
            rx_sop_i=0,
            rx_eop_i=0,
            rx_error_i=0,
            rx_dllp_i=0,
            rx_data_i=0,
            tx_ready_i=1,
        )
        await self.idle(8)
        await self.idle(100, rst_ni=1)

    async def ready(self):
        await self.reset()
        await self.initialize()
        await self.enable()
        # The real CPU keeps polling TX while destructive MBIST runs. Exercise
        # PCIe before release as well as during subsequent Ethernet traffic.
        await self.transact(request(0, BAR + 0x1C), response(data=0x1010F, lower=0x1C))
        # Six backgrounds * 2048 words * (1 + 4*3 + 2) = 184320
        # March clocks per port, plus 4096 cross-read clocks per port.
        # 50 MHz + 125 MHz sequential phases take 5.275648 ms, excluding
        # a few synchronizer/start cycles; 5.6 ms admits those explicitly.
        for _ in range(280000 * 10 // self.half_ns):
            if self.v("eth_mbist_done_o") == 3:
                break
            await self.tick()
        else:
            raise AssertionError("POR MBIST did not release within its cycle bound")
        if os.environ["JOINT_ETH_MBIST"] == "1":
            assert self.eth_before_mbist > 0, "PCIe was not exercised during MBIST"

    async def verify(self):
        for _ in range(30000 * 10 // self.half_ns):
            if self.edges >= 3:
                break
            await self.tick()
        assert (
            len(self.eth_frames) >= 3 and self.eth_rx_reads >= 180 and self.edges >= 3
        )
        assert self.eth_tx_writes >= 180 and self.errors == 0
        assert self.joint_contentions > 0, (
            "No actual CPU Ethernet / PCIe APB contention"
        )
        self.d._log.info(
            "JOINT_ETH_PCIE frames=%d tx_writes=%d rx_reads=%d firmware_frames=%d cpu=%d pcie=%d eth_contentions=%d pre_mbist_pcie=%d",
            len(self.eth_frames),
            self.eth_tx_writes,
            self.eth_rx_reads,
            self.edges,
            len(self.cpu),
            len(self.pcie),
            self.joint_contentions,
            self.eth_before_mbist,
        )


@cocotb.test()
async def simultaneous_cpu_ethernet_and_pcie(d):
    b = JointBench(d)
    await b.ready()
    for tag in range(40 if b.async_pcie else 16):
        await b.transact(request(0x40, BAR + 0x54, [0x100]), stall=True)
        assert b.v("gpio_o") & 0x100
        await b.transact(
            request(0, BAR + 0x1C, tag=tag), response(data=0x1010F, tag=tag, lower=0x1C)
        )
    await b.verify()


@cocotb.test()
async def pcie_link_loss_does_not_reset_ethernet(d):
    b = JointBench(d)
    await b.ready()
    for _ in range(40 if b.async_pcie else 8):
        await b.transact(request(0, BAR + 0x1C), response(data=0x1010F, lower=0x1C))
    before = b.eth_rx_reads
    payload = frame_bytes(tlp_bytes(request(0x40, BAR + 0x54, [0x200])), b.seq)
    for i, value in enumerate(payload[:9]):
        assert await b.tick(
            rx_valid_i=1, rx_data_i=value, rx_sop_i=i == 0, rx_eop_i=0, rx_dllp_i=0
        )
    await b.idle(6000 * 10 // b.half_ns, link_up_i=0)
    assert b.eth_rx_reads > before + 60 and not (b.v("gpio_o") & 0x200)
    assert b.v("eth_mbist_done_o") == 3 and not b.v("initialized_o")
    b.seq = b.txseq = 0
    await b.initialize()
    await b.enable()
    await b.transact(request(0x40, BAR + 0x54, [0x200]))
    assert b.v("gpio_o") & 0x200
    if b.async_pcie:
        # Cancel an actual captured controller APB request before the slower
        # destination can accept it. This exercises the main-chip CDC reset
        # wiring, in addition to the earlier partial-packet link loss.
        await b.wire(frame_bytes(tlp_bytes(request(0x40, BAR + 0x54, [0x400])), b.seq))
        for _ in range(200):
            if b.v("packet_request_o"):
                break
            await b.tick()
        else:
            raise AssertionError("Controller APB request was never observed")
        assert not (b.v("gpio_o") & 0x400)
        await b.idle(500, link_up_i=0)
        assert not (b.v("gpio_o") & 0x400), "Stale CDC write survived link loss"
        b.seq = b.txseq = 0
        await b.initialize()
        await b.enable()
        await b.transact(request(0x40, BAR + 0x54, [0x400]))
        assert b.v("gpio_o") & 0x400
    await b.verify()
