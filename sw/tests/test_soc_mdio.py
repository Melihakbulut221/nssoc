# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exercise real C management driver against an independent pin-level PHY model."""
from pathlib import Path
import resource
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT / 'hw/soc/tb/sw'
CC = shutil.which('cc')
pytestmark = pytest.mark.skipif(CC is None, reason='host C compiler is not installed')
HARNESS = r'''
#include <assert.h>
#include <stdlib.h>
#include <stdint.h>
#include "lib/soc_hal.h"
#include "lib/soc_mdio.h"
#include "soc_eth.h"
static unsigned pins=2, pos, clocks, frames, accesses, waits, reads, writes;
static unsigned bits[64], phy_address=3, op, phy, reg, line=1;
static unsigned absent, stuck_low, ignore_config, bmsr_reads, ready_pair;
static uint16_t regs[32], payload;
static uint64_t now, last_fall, last_rise;
static unsigned field(unsigned start, unsigned length) {
    unsigned value=0;
    for (unsigned i=0;i<length;++i) value=(value<<1)|bits[start+i];
    return value;
}
static void delay(void *context, unsigned us) {
    assert(context == &now && (us == 1 || us == 1000));
    if (us == 1000) ++waits;
    now += us;
}
uint32_t soc_read32(uintptr_t address) {
    assert(address == ETH_MDIO && (pins&1) && !(pins&4));
    assert(now-last_rise >= 1); ++reads; ++accesses;
    return pins|(line<<8);
}
void soc_write32(uintptr_t address, uint32_t value) {
    assert(address == ETH_MDIO && !(value&~7u)); ++accesses;
    /* Data/direction cannot change while clock remains high. */
    if ((pins&1) && (value&1)) assert(value==pins);
    if ((pins&1) && !(value&1)) {
        assert(now-last_rise >= 1); last_fall=now;
    }
    if (!(pins&1) && (value&1)) {
        assert(now-last_fall >= 1); last_rise=now; ++clocks;
        bits[pos]=(value>>1)&1;
        if (pos<46) {
            assert(value&4);
            if (pos<32) assert(bits[pos]==1);
            if (pos==45) {
                assert(field(32,2)==1);
                op=field(34,2); phy=field(36,5); reg=field(41,5);
                assert(op==1 || op==2);
                payload=regs[reg];
                if (op==2 && reg==1) {
                    ++bmsr_reads;
                    if (ready_pair) {
                        payload=0x0108;
                        if (bmsr_reads/2>=ready_pair) payload|=0x0024;
                    }
                    /* Link status is latch-low on first read of each pair. */
                    if (bmsr_reads&1) payload&=~4u;
                }
            }
        } else if (op==2) {
            assert(!(value&4));
            line=pos==46 ? 1 : pos==47 ? 0 : ((payload>>(63-pos))&1);
            if (absent || phy!=phy_address) line=1;
            if (stuck_low) line=0;
        } else {
            assert(value&4);
            if (pos==46) assert(bits[pos]==1);
            if (pos==47) assert(bits[pos]==0);
        }
        if (++pos==64) {
            if (op==1 && !absent && phy==phy_address) {
                ++writes;
                if (!ignore_config) regs[reg]=(uint16_t)field(48,16);
            }
            pos=0; ++frames;
        }
    }
    pins=value;
}
static void finished(void) {
    assert(pins==2 && pos==0 && clocks==frames*64);
}
static soc_mdio bus={delay,&now};
static void start(void) {
    regs[1]=0x0108; regs[15]=0x2000;
    assert(!soc_eth_phy_start_1000fd(&bus,phy_address));
    assert(regs[4]==1 && regs[9]==0x200 && regs[0]==0x1340 && writes==3);
    finished(); bmsr_reads=0;
}
int main(int argc,char **argv) {
    assert(argc==2); unsigned test=(unsigned)atoi(argv[1]); uint16_t value=0x5aa5;
    switch(test) {
    case 0:
        regs[7]=0xa65b; assert(!soc_mdio_read(&bus,3,7,&value));
        assert(value==0xa65b && frames==1 && reads==18); break;
    case 1:
        assert(!soc_mdio_write(&bus,3,7,0x5a96));
        assert(regs[7]==0x5a96 && frames==1 && writes==1 && !reads); break;
    case 2:
        absent=1; assert(soc_mdio_read(&bus,3,7,&value)==SOC_MDIO_NO_ACK);
        assert(value==0x5aa5 && frames==1 && reads==18); break;
    case 3:
        stuck_low=1; assert(soc_mdio_read(&bus,3,7,&value)==SOC_MDIO_NO_ACK);
        assert(value==0x5aa5); break;
    case 4:
        assert(soc_mdio_read(&bus,4,7,&value)==SOC_MDIO_NO_ACK); break;
    case 5:
        phy_address=31; regs[31]=0xffff; assert(!soc_mdio_read(&bus,31,31,&value));
        assert(value==0xffff); break;
    case 6:
        phy_address=0; assert(!soc_mdio_write(&bus,0,0,0)); assert(writes==1); break;
    case 7:
        assert(soc_mdio_read(&bus,32,0,&value)==SOC_MDIO_INVALID && !accesses); break;
    case 8:
        assert(soc_mdio_read(&bus,0,32,&value)==SOC_MDIO_INVALID && !accesses); break;
    case 9:
        assert(soc_mdio_read(&bus,3,0,0)==SOC_MDIO_INVALID && !accesses); break;
    case 10:
        assert(soc_mdio_write(0,3,0,0)==SOC_MDIO_INVALID && !accesses); break;
    case 11:
        bus.delay_us=0; assert(soc_mdio_write(&bus,3,0,0)==SOC_MDIO_INVALID && !accesses); break;
    case 12:
        start(); break;
    case 13:
        regs[1]=0x100; regs[15]=0x2000;
        assert(soc_eth_phy_start_1000fd(&bus,3)==SOC_MDIO_UNSUPPORTED && !writes); break;
    case 14:
        regs[1]=8; regs[15]=0x2000;
        assert(soc_eth_phy_start_1000fd(&bus,3)==SOC_MDIO_UNSUPPORTED && !writes); break;
    case 15:
        regs[1]=0x108; regs[15]=0x1000;
        assert(soc_eth_phy_start_1000fd(&bus,3)==SOC_MDIO_UNSUPPORTED && !writes); break;
    case 16:
        regs[1]=0x108; regs[15]=0x2000; ignore_config=1;
        assert(soc_eth_phy_start_1000fd(&bus,3)==SOC_MDIO_CONFIG); break;
    case 17:
        assert(soc_eth_phy_wait_1000fd(&bus,3,0)==SOC_MDIO_TIMEOUT && !accesses); break;
    case 18:
        start(); ready_pair=3; regs[10]=0x3800;
        assert(!soc_eth_phy_wait_1000fd(&bus,3,3));
        assert(bmsr_reads==6 && waits==2); break;
    case 19:
        start(); ready_pair=3; regs[10]=0x3800;
        assert(soc_eth_phy_wait_1000fd(&bus,3,2)==SOC_MDIO_TIMEOUT);
        assert(bmsr_reads==4 && waits==1); break;
    case 20:
        start(); regs[1]=0x12c; regs[10]=0xb800;
        assert(soc_eth_phy_wait_1000fd(&bus,3,2)==SOC_MDIO_PHY_FAULT); break;
    case 21:
        start(); regs[1]=0x138;
        assert(soc_eth_phy_wait_1000fd(&bus,3,2)==SOC_MDIO_PHY_FAULT); break;
    case 22:
        start(); regs[1]=0x12c; regs[10]=0x3400;
        assert(soc_eth_phy_wait_1000fd(&bus,3,2)==SOC_MDIO_TIMEOUT); break;
    case 23:
        start(); regs[1]=0x12c; regs[10]=0x1800;
        assert(soc_eth_phy_wait_1000fd(&bus,3,2)==SOC_MDIO_TIMEOUT); break;
    case 24:
        start(); regs[4]|=0x100; regs[1]=0x12c; regs[10]=0x3800;
        assert(soc_eth_phy_wait_1000fd(&bus,3,2)==SOC_MDIO_CONFIG); break;
    case 25:
        start(); regs[9]|=0x100;
        assert(soc_eth_phy_wait_1000fd(&bus,3,2)==SOC_MDIO_CONFIG); break;
    case 26:
        start(); regs[0]|=0x4000;
        assert(soc_eth_phy_wait_1000fd(&bus,3,2)==SOC_MDIO_CONFIG); break;
    case 27:
        start(); absent=1;
        assert(soc_eth_phy_wait_1000fd(&bus,3,2)==SOC_MDIO_NO_ACK); break;
    case 28:
        regs[7]=0; assert(!soc_mdio_read(&bus,3,7,&value)); assert(value==0); break;
    case 29:
        absent=1; assert(soc_eth_phy_start_1000fd(&bus,3)==SOC_MDIO_NO_ACK && !writes); break;
    default: assert(0);
    }
    finished(); return 0;
}
'''


def compile_driver(directory, driver):
    source = directory/'phy.c'
    source.write_text(HARNESS)
    exe = directory/'phy'
    subprocess.run([CC, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-DSOC_HAL_TEST_IO', '-I', str(SW), '-I', str(SW/'lib'),
                    str(source), str(driver), '-o', str(exe)], check=True)
    return exe


@pytest.fixture(scope='module')
def harness(tmp_path_factory):
    return compile_driver(tmp_path_factory.mktemp('mdio'), SW/'lib/soc_mdio.c')


@pytest.mark.parametrize('case', range(30))
def test_real_driver_at_phy_pins(harness, case):
    subprocess.run([str(harness), str(case)], check=True, timeout=5)


@pytest.mark.parametrize('before,after,case', [
    ('send_bits(bus, 2, 2);', 'send_bits(bus, 0, 2);', 1),
    ('ack != 0', 'ack != 1', 2),
    ('i < 16', 'i < 15', 0),
    ('(gigabit & 0x3800u) == 0x3800u', '(gigabit & 0x3000u) == 0x3000u', 22),
])
def test_wire_and_acceptance_faults_are_rejected(tmp_path, before, after, case):
    text = (SW/'lib/soc_mdio.c').read_text()
    assert text.count(before) == 1
    mutant = tmp_path/'mutant.c'
    mutant.write_text(text.replace(before, after))
    executable = compile_driver(tmp_path, mutant)
    def no_core():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    result = subprocess.run([str(executable), str(case)], capture_output=True,
                            text=True, timeout=5, preexec_fn=no_core)
    assert result.returncode != 0 and 'Assertion' in result.stderr
