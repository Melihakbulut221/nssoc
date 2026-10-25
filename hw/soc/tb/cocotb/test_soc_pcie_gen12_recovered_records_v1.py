# SPDX-License-Identifier: Apache-2.0
"""Composed frozen raw32/codec/record collector and exact asynchronous FIFO."""
import cocotb
from cocotb.triggers import Timer
from pcie_gen12_record_cdc_harness import DEPTH,Link,stream_words

@cocotb.test()
async def both_polarities_all_offsets_and_errors(d):
    link=Link(d,composed=True,wr_ps=4000,rd_ps=4103,phase_ps=311)
    await link.start()
    for polarity in (0,1):
        for rd in (0,1):
            for offset in range(32):
                await link.reset('wr',polarity=polarity)
                before=link.reads
                await link.feed(stream_words(offset,polarity,rd,count=3,random_codes=True),gap=2)
                await link.drain()
                assert link.reads-before==3
    # Every raw10 value at every nonframing position, including late errors.
    await link.reset('rr',polarity=1)
    before=link.reads
    await link.feed(stream_words(0,1,1,count=1024,random_codes=True),gap=1)
    await link.drain()
    assert link.reads-before==1024
    assert link.oracle.code_errors>0 and link.oracle.rd_errors>0
    assert set(range(1,16))<=link.positions[1]  # code errors at all noninitial slots
    assert set(range(1,16))<=link.positions[2]  # disparity errors at all noninitial slots
    assert {0,7}<=link.positions[3]
    assert link.writes==link.reads
    link.close()

@cocotb.test()
async def first_public_word_and_startup_reset(d):
    link=Link(d,composed=True);await link.start()
    for polarity in (0,1):
        for domain in ('wr','rr'):
            # Release while one clock is stopped, then reset again during startup.
            before=link.reads
            await link.reset(domain,stopped='wr',polarity=polarity,
                             prefill=stream_words(0,polarity,count=2))
            await link.until(lambda:not link.pending);await link.drain()
            assert link.reads-before==2
            assert link.value('boundary_valid_o')
            link.sig(domain).value=1
            await Timer(1000,unit='ps')
            link.sig(domain).value=0
            await Timer(2000,unit='ps')  # Below the frozen startup barrier length.
            before=link.reads
            # Queue before release: first live writer low phase already presents COM.
            await link.reset(domain,stopped='rd',polarity=polarity,
                             prefill=stream_words(0,polarity,count=2))
            await link.until(lambda:not link.pending);await link.drain()
            assert link.reads-before==2
    link.close()

@cocotb.test()
async def partial_raw_batch_and_complete_record_epoch_reset(d):
    link=Link(d,composed=True);await link.start()
    # Five raw words per record. Every prefix length exercises raw residue,
    # pending decoded batch, partial record or full queued record at reset.
    for polarity in (0,1):
        for cut in range(1,16):
            await link.reset('rr',polarity=polarity)
            link.ready=False
            await link.feed(stream_words(3,polarity,count=4)[:cut],gap=1)
            # No drain: reset through in-flight and held complete states.
            await link.reset('wr'if cut&1 else 'rr',polarity=1-polarity)
            link.ready=True;before=link.reads
            await link.feed(stream_words(0,1-polarity,count=4),gap=1);await link.drain()
            assert link.reads-before==4
    link.close()

@cocotb.test()
async def polarity_change_and_known_loss_stop_epoch(d):
    link=Link(d,composed=True);await link.start()
    # A polarity change after every possible candidate-symbol prefix faults,
    # even without a raw word on the change edge. Already delivered prefix is legal.
    for slot in range(16):
        await link.reset('wr',polarity=0)
        word_count=(slot*10+31)//32
        offset=32*word_count-10*slot
        words=stream_words(offset,0,count=3)
        await link.feed(words[:word_count],gap=2)
        await Timer(40000,unit='ps')
        assert len(link.partial)==slot,(slot,len(link.partial))
        link.allow_fault=True;link.polarity=1
        await link.fault_visible(overflow=False)
        await link.reset('rr',polarity=1)
        await link.feed(stream_words(0,1,count=2),gap=1);await link.drain()
    link.allow_fault=True;link.loss=True
    await link.fault_visible(overflow=False)
    link.close()

@cocotb.test()
async def composed_capacity_and_common_pause(d):
    link=Link(d,composed=True);await link.start()
    link.ready=False;link.allow_fault=True
    link.pending.extend(stream_words(0,0,count=DEPTH+12))
    await link.fault_visible(overflow=True)
    assert link.writes==DEPTH+2
    await link.reset('rr')
    link.ready=False
    await link.feed(stream_words(0,0,count=2),gap=1)
    await link.until(lambda:link.value('rv'))
    link.pause_wr=True;await Timer(20000,unit='ps');link.ready=True
    await link.until(lambda:not link.expected)
    await Timer(100000,unit='ps')
    assert not link.value('rf') and link.value('rn')
    link.pause_wr=False
    await link.reset('wr')
    before=link.reads
    await link.feed(stream_words(0,0,count=16),gap=1);await link.drain()
    assert link.reads-before==16
    link.close()
