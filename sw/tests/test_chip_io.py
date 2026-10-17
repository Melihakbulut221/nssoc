# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run mailbox RTL and reject behaviorally meaningful faults."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('chip_generator', ROOT/'scripts/generate_chip_io.py')
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)
RTL = ROOT/'hw/soc/rtl/chip/soc_status_serial.v'
TB = ROOT/'hw/soc/tb/tb_soc_status_serial.v'


@pytest.mark.parametrize('mutation', [None, 'live_bus', 'never_ack', 'wrong_shift', 'stale_ready', 'no_reset'])
def test_serial_status_cdc_behavior(tmp_path, mutation):
    compiler, runtime = shutil.which('iverilog'), shutil.which('vvp')
    assert compiler and runtime, 'Icarus is required; no unexecuted RTL pass'
    text = RTL.read_text()
    mutations = {
        'live_bus': ('shift <= snapshot;', 'shift <= status_i;'),
        'never_ack': ('ack <= req_sync;', "ack <= 1'b0;"),
        'wrong_shift': ("shift <= {1'b0, shift[WIDTH-1:1]};", "shift <= {shift[WIDTH-2:0], 1'b0};"),
        'stale_ready': ('(consumed == test_req_i)', "1'b1"),
        'no_reset': ('valid <= 0;', 'valid <= 1;'),
    }
    if mutation:
        old, new = mutations[mutation]
        assert old in text
        text = text.replace(old, new)
    source = tmp_path/'serial.v'; source.write_text(text)
    binary = tmp_path/'run.vvp'
    build = subprocess.run([compiler, '-g2012', '-s', 'tb_soc_status_serial', '-o', str(binary),
                            str(source), str(TB)], capture_output=True, text=True, timeout=30)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([runtime, str(binary)], capture_output=True, text=True, timeout=30)
    if mutation:
        assert run.returncode != 0 and 'FATAL' in run.stdout, run.stdout + run.stderr
    else:
        assert run.returncode == 0 and 'PASS status serial:' in run.stdout, run.stdout + run.stderr


def test_generation_does_not_mutate_contract():
    contract = json.loads(generator.CONTRACT.read_text())
    before = json.dumps(contract, sort_keys=True)
    text, cells = generator.generate(contract)
    assert json.dumps(contract, sort_keys=True) == before
    assert len(cells) == 106 and len({c['instance'] for c in cells}) == 106
    assert 'soc_top u_core' in text


@pytest.mark.parametrize('error', ['direction', 'width', 'repeated_pad_source', 'frame_overlap'])
def test_contract_mismatches_are_rejected(error):
    contract = json.loads(generator.CONTRACT.read_text())
    if error == 'direction':
        contract['core_ports']['gpio_i']['direction'] = 'output'
    elif error == 'width':
        contract['core_ports']['gpio_o']['width'] = 15
    elif error == 'repeated_pad_source':
        contract['bidirectional'][1]['input'] = 'gpio_i'
    else:
        contract['status_lsb_first'][1]['lsb'] = 0
    with pytest.raises(ValueError):
        generator.generate(contract)


def test_host_frame_decoder():
    spec = importlib.util.spec_from_file_location('chip_status', ROOT/'sw/golden/chip_status.py')
    host = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host)
    value = ((0x4d420001 << 160) | (0xa6 << 151) | (5 << 148) |
             (0x0123456789abcdef << 84) | (0xfedcba9876543210 << 20) |
             (0x1234 << 7) | (2 << 5) | (3 << 3) | 6)
    frame = value.to_bytes(24, 'little')
    assert host.decode(frame) == dict(busy=0, done=1, failed=1, eth_done=3,
                                      eth_failed=2, fail_address=0x1234,
                                      expected=0xfedcba9876543210,
                                      actual=0x0123456789abcdef, phase=5, background=0xa6)
    for bad in (frame[:-1], frame+b'\0', frame[::-1],
                (value ^ (1 << 160)).to_bytes(24,'little'),
                (value | (1 << 159)).to_bytes(24,'little')):
        with pytest.raises(ValueError):
            host.decode(bad)
