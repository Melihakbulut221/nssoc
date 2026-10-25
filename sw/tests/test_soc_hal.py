# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compile the real HAL with fake MMIO; test bounded I/O and console ABI."""
from pathlib import Path
import resource
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]
SW = ROOT/'hw/soc/tb/sw'
CC = shutil.which('cc')
pytestmark = pytest.mark.skipif(CC is None, reason='host C compiler is not installed')

HARNESS = r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "lib/soc_hal.h"
#include "soc_interfaces.h"
static unsigned reads, pops, writes, byte_reads, byte_writes, ready_after;
static uint32_t status, received;
static char output[128];
static uintptr_t write_address[128], byte_address;
static uint32_t write_value[128];
static uint8_t byte_value;
uint32_t soc_read32(uintptr_t address) {
    if (address == SOC_UART0_BASE + SOC_UART_STATUS_OFF)
        return ++reads >= ready_after ? status : 0;
    assert(address == SOC_UART0_BASE + SOC_UART_DATA_OFF);
    ++pops; return received;
}
void soc_write32(uintptr_t address, uint32_t value) {
    assert(writes < sizeof(output));
    write_address[writes] = address; write_value[writes] = value;
    output[writes++] = (char)value;
}
uint8_t soc_read8(uintptr_t address) {
    ++byte_reads; byte_address = address; return byte_value;
}
void soc_write8(uintptr_t address, uint8_t value) {
    ++byte_writes; byte_address = address; byte_value = value;
}
int main(int argc, char **argv) {
    assert(argc == 2);
    ready_after = 1; status = 4; received = 0xa6;
    uint8_t value = 0x5a;
    switch (atoi(argv[1])) {
    case 0:
        assert(soc_uart_try_putc(0xa5, 0) == -1 && !reads && !writes); break;
    case 1:
        ready_after = 3;
        assert(soc_uart_try_putc(0xa5, 2) == -1 && reads == 2 && !writes); break;
    case 2:
        ready_after = 3;
        assert(!soc_uart_try_putc(0xa5, 3) && reads == 3 && writes == 1);
        assert(write_address[0] == SOC_UART0_BASE + SOC_UART_DATA_OFF && write_value[0] == 0xa5); break;
    case 3:
        status = 0;
        assert(soc_uart_try_putc(0xa5, 100) == -1 && reads == 100 && !writes); break;
    case 4:
        assert(soc_uart_try_getc(&value, 2) == -1 && value == 0x5a && reads == 2 && !pops && !writes); break;
    case 5:
        assert(soc_uart_try_getc(0, 2) == -2 && !reads && !pops && !writes); break;
    case 6:
        status = 1; ready_after = 2;
        assert(!soc_uart_try_getc(&value, 2) && value == 0xa6 && reads == 2 && pops == 1 && !writes); break;
    case 7:
        status = 1;
        assert(soc_uart_try_getc(&value, 0) == -1 && value == 0x5a && !reads && !pops && !writes); break;
    case 8:
        soc_uart_init(37, 7);
        assert(writes == 2 && !reads);
        assert(write_address[0] == SOC_UART0_BASE + SOC_UART_SCALER_OFF && write_value[0] == 37);
        assert(write_address[1] == SOC_UART0_BASE + SOC_UART_CTRL_OFF && write_value[1] == 7); break;
    case 9:
        ready_after = 3; soc_uart_putc('Q');
        assert(reads == 3 && writes == 1 && output[0] == 'Q'); break;
    case 10:
        soc_uart_puts("A\n"); soc_uart_hex32(0x1abcde23, 1); soc_uart_hex32(0, 0);
        assert(writes == 20 && !memcmp(output, "A\n0x1abcde2300000000", 20)); break;
    case 11:
        soc_uart_hex32(0xffffffff, 0);
        assert(writes == 8 && !memcmp(output, "ffffffff", 8)); break;
    case 12:
        soc_uart_puts(""); assert(!reads && !writes); break;
    case 13:
        status = 0xfffffffd;
        assert(!soc_wait32(SOC_UART0_BASE + SOC_UART_STATUS_OFF, 7, 5, 1) && reads == 1 && !writes); break;
    case 14:
        assert(soc_wait32(SOC_UART0_BASE + SOC_UART_STATUS_OFF, 4, 0x14, 2) == -1 && reads == 2); break;
    case 15:
        assert(soc_wait32(SOC_UART0_BASE + SOC_UART_STATUS_OFF, 0, 0, 0) == -1 && !reads); break;
    case 16:
        soc_can_write(3, 0xa5);
        assert(byte_writes == 1 && byte_address == SOC_CAN_BASE + 3 && byte_value == 0xa5 && !writes);
        assert(soc_can_read(3) == 0xa5 && byte_reads == 1 && !reads && !pops); break;
    case 17:
        ready_after = 4;
        assert(soc_if_wait(SOC_UART0_BASE, SOC_UART_STATUS_OFF, 4, 4, 3) == -1 && reads == 3 && !writes); break;
    default: assert(0);
    }
    if (atoi(argv[1]) != 8)
        for (unsigned n=0; n<writes; ++n) assert(write_address[n] == SOC_UART0_BASE + SOC_UART_DATA_OFF);
    return 0;
}
'''


@pytest.fixture(scope='module')
def harness(tmp_path_factory):
    directory = tmp_path_factory.mktemp('soc-hal')
    source = directory/'host.c'
    source.write_text(HARNESS)
    executable = directory/'host'
    subprocess.run([CC, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-DSOC_HAL_TEST_IO', '-I', str(SW), str(source),
                    str(SW/'lib/soc_hal.c'), '-o', str(executable)], check=True)
    return executable


@pytest.mark.parametrize('case', range(18), ids=[
    'tx-zero-budget', 'tx-timeout', 'tx-last-poll', 'tx-never-ready',
    'rx-timeout-no-pop', 'rx-null-no-io', 'rx-pop-once', 'rx-zero-budget',
    'init-order', 'blocking-console-waits', 'console-format', 'hex-high-bits',
    'empty-string', 'masked-wait', 'impossible-value-times-out', 'zero-mask-budget',
    'can-stays-byte-wide', 'interface-wait-bound',
])
def test_real_hal_io_contract(harness, case):
    subprocess.run([str(harness), str(case)], check=True, timeout=5)


def test_production_accessors_are_exact_width(tmp_path):
    # Compile without test hooks. Local volatile objects verify the public
    # inline functions independently of the simulated UART hook path.
    source = tmp_path/'width.c'
    source.write_text('''#include <assert.h>
#include "lib/soc_hal.h"
int main(void) {
    volatile uint32_t word = 0;
    volatile uint8_t bytes[3] = {0x12, 0x34, 0x56};
    soc_write32((uintptr_t)&word, 0xa5f01793u);
    assert(soc_read32((uintptr_t)&word) == 0xa5f01793u);
    soc_write8((uintptr_t)&bytes[1], 0xab);
    assert(soc_read8((uintptr_t)&bytes[1]) == 0xab);
    assert(bytes[0] == 0x12 && bytes[2] == 0x56);
    return 0;
}
''')
    executable = tmp_path/'width'
    subprocess.run([CC, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-I', str(SW), str(source), '-o', str(executable)], check=True)
    subprocess.run([str(executable)], check=True, timeout=5)


@pytest.mark.parametrize('old,new,case', [
    ('while (polls--)', 'while (polls-- + 1)', 0),
    ('if (!value) return -2;',
     'if (!value) return -2;\n    *value = (uint8_t)soc_read32(UART_DATA);', 4),
    ('if (soc_wait32(UART_STATUS, UART_TE, UART_TE, polls)) return -1;',
     '(void)soc_wait32(UART_STATUS, UART_TE, UART_TE, polls);', 1),
])
def test_reachable_io_mutations_are_rejected(tmp_path, old, new, case):
    source = (SW/'lib/soc_hal.c').read_text()
    assert source.count(old) == 1
    mutant = tmp_path/'mutant.c'
    mutant.write_text(source.replace(old, new))
    harness_source = tmp_path/'host.c'
    harness_source.write_text(HARNESS)
    executable = tmp_path/'mutant'
    subprocess.run([CC, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-DSOC_HAL_TEST_IO', '-I', str(SW), '-I', str(SW/'lib'),
                    str(harness_source), str(mutant), '-o', str(executable)], check=True)
    def disable_core_dump():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    result = subprocess.run([str(executable), str(case)], capture_output=True,
                            text=True, timeout=5, preexec_fn=disable_core_dump)
    assert result.returncode != 0 and 'Assertion' in result.stderr, result.stderr
