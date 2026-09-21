# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent GMII wire expectations: preamble, CRC32, padding and drops."""
import binascii
from peripheral_registers import ETH as _REG_OFFSETS
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer

CTRL, STATUS, TX, RX, EVENTS, IRQEN, MDIO, ID = _REG_OFFSETS['CTRL'], _REG_OFFSETS['STATUS'], _REG_OFFSETS['TX'], _REG_OFFSETS['RX'], _REG_OFFSETS['EVENTS'], _REG_OFFSETS['IRQEN'], _REG_OFFSETS['MDIO'], _REG_OFFSETS['ID']

async def cycles(d, n=1):
    for _ in range(n):
        await RisingEdge(d.clk_i)
    await Timer(1, units='ns')

async def setup(d):
    for name in ('rst_ni','psel_i','penable_i','pwrite_i','paddr_i','pwdata_i','pstrb_i','rxd_i','rx_dv_i','rx_er_i'):
        getattr(d,name).value = 0
    d.mdio_i.value = 1
    cocotb.start_soon(Clock(d.clk_i,20,units='ns').start())
    cocotb.start_soon(Clock(d.tx_clk_i,8,units='ns').start())
    await Timer(3,units='ns')
    cocotb.start_soon(Clock(d.rx_clk_i,8,units='ns').start())
    await cycles(d,8)
    d.rst_ni.value=1
    await cycles(d,20)
    await apb(d,CTRL,3)
    await cycles(d,20)

async def apb(d,addr,data=None,strobe=15,error=False):
    await FallingEdge(d.clk_i)
    d.psel_i.value=1; d.penable_i.value=0
    d.paddr_i.value=addr; d.pwrite_i.value=int(data is not None)
    d.pwdata_i.value=0 if data is None else data; d.pstrb_i.value=strobe
    await FallingEdge(d.clk_i)
    d.penable_i.value=1
    await Timer(1,units='ns')
    assert int(d.pready_o.value)==1
    assert int(d.pslverr_o.value)==int(error), (addr,data,error)
    value=int(d.prdata_o.value)
    await FallingEdge(d.clk_i)
    d.psel_i.value=0; d.penable_i.value=0
    return value

def wire_frame(payload):
    return b'\x55'*7+b'\xd5'+payload+binascii.crc32(payload).to_bytes(4,'little')

async def receive_wire(d):
    data=[]
    for _ in range(30000):
        await FallingEdge(d.tx_clk_i)
        if int(d.tx_en_o.value):
            assert not int(d.tx_er_o.value)
            data.append(int(d.txd_o.value))
        elif data:
            return bytes(data)
    raise AssertionError('MAC never transmitted a complete frame')

async def send_wire(d,payload,bad=False):
    frame=bytearray(wire_frame(payload))
    if bad: frame[-1]^=0x80
    for b in frame:
        await FallingEdge(d.rx_clk_i)
        d.rxd_i.value=b; d.rx_dv_i.value=1
    await FallingEdge(d.rx_clk_i)
    d.rx_dv_i.value=0
    for _ in range(12): await FallingEdge(d.rx_clk_i)

async def read_packet(d,expected):
    for _ in range(100):
        if await apb(d,STATUS)&2: break
    else: raise AssertionError('No received frame')
    got=[]
    for i in range(len(expected)):
        word=await apb(d,RX)
        assert word>>31==1
        assert ((word>>8)&1)==int(i==len(expected)-1)
        assert not word&512
        got.append(word&255)
    assert bytes(got)==expected

@cocotb.test()
async def tx_padding_crc_and_full_size_frame(d):
    await setup(d)
    for size in (42,1514):
        packet=bytes((n*13+7)&255 for n in range(size))
        monitor=cocotb.start_soon(receive_wire(d))
        for i,b in enumerate(packet):
            await apb(d,TX,b|(256 if i==size-1 else 0))
        got=await monitor
        assert got==wire_frame(packet.ljust(60,b'\0'))
        assert await apb(d,EVENTS)&1
        await apb(d,EVENTS,1)
    assert not await apb(d,EVENTS)&(1<<5)

@cocotb.test()
async def rx_frame_crosses_clocks_and_interrupts(d):
    await setup(d)
    packet=bytes(range(128))
    await apb(d,IRQEN,1<<9)
    await send_wire(d,packet)
    await cycles(d,30)
    assert int(d.irq_o.value)==1
    await read_packet(d,packet)
    await cycles(d,5)
    assert int(d.irq_o.value)==0
    await apb(d,RX,error=True)
    assert await apb(d,EVENTS)&2

@cocotb.test()
async def bad_fcs_is_discarded_and_next_frame_recovers(d):
    await setup(d)
    packet=bytes(range(90))
    await apb(d,IRQEN,1<<6)
    await send_wire(d,packet,bad=True)
    await cycles(d,50)
    assert not await apb(d,STATUS)&2
    assert await apb(d,EVENTS)&(1<<6)
    assert int(d.irq_o.value)==1
    await apb(d,EVENTS,255)
    assert int(d.irq_o.value)==0
    await send_wire(d,packet)
    await read_packet(d,packet)

@cocotb.test()
async def rx_overflow_preserves_committed_frame(d):
    await setup(d)
    packet=bytes((i+9)&255 for i in range(1514))
    await send_wire(d,packet)
    await send_wire(d,packet)
    await cycles(d,50)
    assert await apb(d,EVENTS)&(1<<4)
    await read_packet(d,packet)
    assert not await apb(d,STATUS)&2
    await send_wire(d,packet)
    await read_packet(d,packet)

@cocotb.test()
async def oversize_tx_and_flush_do_not_emit_partial_packets(d):
    await setup(d)
    for i in range(2200):
        await apb(d,TX,(i&255)|(256 if i==2199 else 0))
        assert not int(d.tx_en_o.value)
    await cycles(d,40)
    assert await apb(d,EVENTS)&(1<<8)
    for i in range(100): await apb(d,TX,i)
    await apb(d,CTRL,7)
    await cycles(d,30)
    packet=bytes(range(60))
    monitor=cocotb.start_soon(receive_wire(d))
    for i,b in enumerate(packet): await apb(d,TX,b|(256 if i==59 else 0))
    assert await monitor==wire_frame(packet)

@cocotb.test()
async def register_strobes_phy_pins_and_reset(d):
    await setup(d)
    assert await apb(d,ID)==0x474d4901
    await apb(d,0x100,error=True)
    await apb(d,ID,0,error=True)
    await apb(d,CTRL,0,strobe=0,error=True)
    assert await apb(d,CTRL)==3
    await apb(d,MDIO,5)
    assert int(d.mdc_o.value)==1 and int(d.mdio_o.value)==0 and int(d.mdio_oe_o.value)==1
    d.mdio_i.value=0
    await cycles(d,4)
    assert await apb(d,MDIO)==5
    await apb(d,IRQEN,0x3ff)
    await apb(d,IRQEN,0,strobe=1)
    assert await apb(d,IRQEN)==0x300
    await apb(d,CTRL,0)
    await apb(d,TX,256,error=True)
    d.rst_ni.value=0
    await cycles(d,5)
    d.rst_ni.value=1
    await cycles(d,20)
    assert await apb(d,CTRL)==0
    assert await apb(d,IRQEN)==0
    assert await apb(d,EVENTS)==0
    assert not int(d.mdio_oe_o.value)
