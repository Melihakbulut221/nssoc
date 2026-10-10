# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""DLLP CRC proof, independent numeric vectors and actual port fault controls."""
from pathlib import Path
import random
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from cocotb_results import count_results  # noqa: E402


def normal_crc(data):
    value = 0xffff
    for octet in data:
        for bit in range(8):
            feedback = ((value >> 15) ^ (octet >> bit)) & 1
            value = ((value << 1) & 0xffff) ^ (0x100b if feedback else 0)
    reflected = int(f'{value:016b}'[::-1], 2)
    return ((~reflected) & 0xffff).to_bytes(2, 'little')


@pytest.mark.parametrize('payload,crc', [('00000000', 'b362'), ('10000000', '5805'),
                                        ('00000fff', '25a8'), ('10000abc', '7bca')])
def test_literal_classic_dllp_vectors(payload, crc):
    assert normal_crc(bytes.fromhex(payload)).hex() == crc


def test_normal_vs_reciprocal_crc_polynomial_on_every_header():
    for nak in (0, 0x10):
        for sequence in range(4096):
            data = bytes((nak, 0, sequence >> 8, sequence & 255))
            value = 0xffff
            for octet in data:
                value ^= octet
                for _ in range(8):
                    value = (value >> 1) ^ (0xd008 if value & 1 else 0)
            assert normal_crc(data) == ((~value) & 0xffff).to_bytes(2, 'little')


@pytest.mark.parametrize('wrong', [False, True])
def test_crc_relation_all_24_input_bits_and_wrong_polynomial_counterexample(tmp_path, wrong):
    yosys = shutil.which('yosys')
    if not yosys:
        pytest.skip('Actual Yosys required')
    text = (ROOT/'hw/soc/rtl/pcie/soc_pcie_crc16_byte.v').read_text()
    if wrong:
        assert text.count("16'hd008") == 1
        text = text.replace("16'hd008", "16'hd009")
    rtl = tmp_path/'crc.v'
    rtl.write_text(text)
    capability = subprocess.run([yosys, '-Q', '-T', '-p', 'help chformal'], capture_output=True, text=True, check=True)
    (tmp_path/'capability.log').write_text(capability.stdout)
    lower = 'chformal -lower; ' if '-lower' in capability.stdout else ''
    proof = ROOT/'hw/soc/formal/pcie_crc16_byte_formal.v'
    command = (f'read_verilog -formal {rtl} {proof}; prep -top pcie_crc16_byte_formal -flatten; '
               + lower + 'select -assert-count 1 t:$assert; select -assert-none t:$assume t:$check; select *; '
               + 'sat ' + ('' if wrong else '-verify ') + f'-prove-asserts -show-inputs -dump_json {tmp_path}/cex.json')
    result = subprocess.run([yosys, '-Q', '-T', '-p', command], capture_output=True, text=True, timeout=45)
    (tmp_path/'proof.log').write_text(result.stdout+result.stderr)
    assert result.returncode == 0
    assert ('model found: FAIL' if wrong else 'no model found: SUCCESS') in result.stdout
    if wrong:
        assert (tmp_path/'cex.json').stat().st_size > 0


def test_actual_primitive_state_basis_and_random_vectors(tmp_path):
    if not shutil.which('iverilog') or not shutil.which('vvp'):
        pytest.skip('Actual Icarus required')
    rng = random.Random(0xc16)
    vectors = [(state, byte) for state in (0, 65535) for byte in range(256)]
    vectors += [(1 << bit, value) for bit in range(16) for value in (0, 1, 2, 4, 8, 16, 32, 64, 128)]
    vectors += [(rng.randrange(65536), rng.randrange(256)) for _ in range(1024)]
    checks = []
    for i, (state, byte) in enumerate(vectors):
        value = int(f'{state:016b}'[::-1], 2)
        for bit in range(8):
            feedback = ((value >> 15) ^ (byte >> bit)) & 1
            value = ((value << 1) & 65535) ^ (0x100b if feedback else 0)
        expected = int(f'{value:016b}'[::-1], 2)
        checks.append(f"s=16'h{state:04x};b=8'h{byte:02x};#1;if(y!==16'h{expected:04x})$fatal(1,\"vector{i}\");")
    tb = tmp_path/'tb.v'
    tb.write_text('module tb;reg[15:0]s;reg[7:0]b;wire[15:0]y;soc_pcie_crc16_byte d(s,b,y);initial begin\n'
                  +'\n'.join(checks)+'\n$display("CRC16_PASS");$finish;end endmodule\n')
    exe = tmp_path/'sim'
    subprocess.run(['iverilog', '-g2012', '-s', 'tb', '-o', str(exe), str(tb), str(ROOT/'hw/soc/rtl/pcie/soc_pcie_crc16_byte.v')], capture_output=True, check=True)
    result = subprocess.run(['vvp', str(exe)], capture_output=True, text=True, check=True)
    assert result.stdout.splitlines().count('CRC16_PASS') == 1
    assert len(vectors) == 1680


@pytest.mark.parametrize('file,before,after', [
    ('soc_pcie_crc16_byte.v', "16'hd008", "16'hd009"),
    ('soc_pcie_acknak_tx.v', '4:tx_data_o=~crc[7:0]', '4:tx_data_o=crc[7:0]'),
    ('soc_pcie_packet_tx.v', 'wire chosen=locked ?', "wire chosen=1'b0 ?"),
    ('soc_pcie_packet_tx.v', 'if(tx_ready_i && tx_eop_o)', 'if(tx_ready_i)')])
def test_real_packet_controls_reject_crc_and_arbitration_faults(tmp_path, file, before, after):
    if not shutil.which('iverilog') or not (Path(sys.executable).parent/'cocotb-config').is_file():
        pytest.skip('Actual Icarus/cocotb required')
    rtl = tmp_path/'rtl'
    rtl.mkdir()
    for name in ('soc_pcie_crc16_byte.v', 'soc_pcie_acknak_tx.v', 'soc_pcie_packet_tx.v'):
        shutil.copyfile(ROOT/'hw/soc/rtl/pcie'/name, rtl/name)
    path = rtl/file
    text = path.read_text()
    assert text.count(before) == 1
    path.write_text(text.replace(before, after))
    out = tmp_path/'run'
    result = subprocess.run([sys.executable, str(ROOT/'scripts/check_pcie_packets.py'),
                             '--out', str(out), '--rtl-dir', str(rtl)], capture_output=True, text=True, timeout=180)
    assert result.returncode == 1
    passed, failed, skipped = count_results([out/'results.xml'])
    assert passed+failed == 4 and failed > 0 and skipped == 0
