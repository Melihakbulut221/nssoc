# SPDX-License-Identifier: Apache-2.0
"""Public-port complete192-bit transport tests, independent of FIFO internals."""
import random
import cocotb
from cocotb.triggers import Timer
from pcie_gen12_record_cdc_harness import DEPTH,Link,MASK,records,split

@cocotb.test()
async def all192_bits_async_wraps(d):
    for wr,rd,phase in ((4000,4001,137),(4001,1900,617),(2900,4100,701)):
        link=Link(d,wr_ps=wr,rd_ps=rd,phase_ps=phase)
        await link.start()
        items=[split(1<<b)for b in range(192)]+[split(MASK^(1<<b))for b in range(192)]
        items+=records(0x912,1024)
        await link.feed(items,gap=3)
        await link.drain()
        assert link.writes==link.reads==1408
        link.close()

@cocotb.test()
async def held_all_fields_and_error_flags_are_payload(d):
    link=Link(d);await link.start()
    link.ready=False
    items=[split(MASK),split(0)]
    await link.feed(items,gap=4)
    await link.until(lambda:link.value('rv'))
    await Timer(150000,unit='ps')
    assert not link.value('wf')
    await link.drain()
    assert link.writes==link.reads==2
    link.close()

@cocotb.test()
async def exact_capacity_overflow_sticky_epoch(d):
    link=Link(d);await link.start()
    link.ready=False;link.allow_fault=True;link.gap=4
    link.pending.extend(records(123,DEPTH+8))
    await link.fault_visible(overflow=True)
    assert link.writes==DEPTH+2,(link.writes,DEPTH)
    await link.reset('rr')
    await link.feed(records(321,100),gap=3);await link.drain()
    assert link.reads==100
    link.close()

@cocotb.test()
async def resets_held_prefetch_and_startup_stopped_clock(d):
    link=Link(d);await link.start()
    for reset in ('wr','rr'):
        for stopped in ('wr','rd'):
            link.ready=False
            await link.feed(records(42,2),gap=4)
            await link.until(lambda:link.value('rv'))
            await link.reset(reset,stopped=stopped)
            link.ready=True
            await link.feed(records(43,40),gap=3);await link.drain()
    link.close()

@cocotb.test()
async def loss_without_valid_and_buffered_prefix(d):
    link=Link(d);await link.start()
    await link.feed(records(67,20),gap=3);await link.drain()
    before=link.reads
    # Empty-source loss is meaningful even without valid.
    link.allow_fault=True;link.loss=True
    await link.fault_visible(overflow=False)
    assert link.reads==before
    await link.reset('wr')
    link.ready=False
    await link.feed(records(68,2),gap=4)
    await link.until(lambda:link.value('rv'))
    link.ready=True;link.allow_fault=True;link.loss=True
    # The queue oracle admits any ordered prefix before synchronized fault.
    await link.fault_visible(overflow=False)
    assert before<=link.reads<=before+2
    link.close()

@cocotb.test()
async def mid_epoch_clock_pause_is_not_loss_detection(d):
    link=Link(d);await link.start()
    link.ready=False
    await link.feed(records(70,2),gap=4)
    await link.until(lambda:link.value('rv'))
    link.pause_wr=True;await Timer(20000,unit='ps')
    link.ready=True
    await link.until(lambda:not link.expected)
    await Timer(100000,unit='ps')
    assert link.value('wn') and link.value('rn') and not link.value('rf')
    # Hold known loss until the writer clock resumes; stopped writer cannot sample it.
    link.allow_fault=True;link.loss=True
    await Timer(50000,unit='ps')
    assert not link.value('rf')
    link.pause_wr=False;await link.fault_visible(overflow=False)
    await link.reset('rr')
    link.pause_rd=True;await Timer(20000,unit='ps')
    link.allow_fault=True;link.gap=3
    link.pending.extend(records(71,DEPTH+12))
    await link.until(lambda:link.value('wf'))
    assert link.value('wo') and not link.value('rf')
    # Fault reaches common only after its clock resumes.
    link.pause_rd=False;await link.fault_visible(overflow=True)
    link.close()
