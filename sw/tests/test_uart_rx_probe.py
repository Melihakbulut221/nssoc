# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject incomplete CPU reception evidence, including a silent peer corruption."""
import importlib.util
from pathlib import Path
import subprocess
import pytest

SCRIPT = Path(__file__).resolve().parents[2]/'hw/soc/flow/uart_rx_probe.py'
spec = importlib.util.spec_from_file_location('uart_rx_probe', SCRIPT)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


@pytest.fixture
def complete():
    return '''RECORD done=1 slept=1 expired=0 cycles=5138 budget=100000
RECORD sig=a1170001 mask=00000000 rounds=5 exit=00000000 magic=600dc0de
RECORD traps=0 nmis=0 wdog1=0 wdog2=0 wdog3=0
RECORD alert_minor=0 alert_int=0 alert_bus=0 dblfault=0
RECORD console_chars=19 console_framing=0
RECORD console_tail=   Sa1170001M00000000
UART_RX frames=6 sleep_wakes=1
RECORD end
'''


def test_complete_and_explicit_negative_control(complete):
    assert probe.check_log(complete)['status'] == 'PASS'
    negative = complete.replace('mask=00000000','mask=00000001').replace('exit=00000000','exit=00000001').replace('M00000000','M00000001')
    assert probe.check_log(negative, True)['status'] == 'EXPECTED DATA FAILURE'
    with pytest.raises(ValueError):
        probe.check_log(negative)
    with pytest.raises(ValueError):
        probe.check_log(complete, True)


@pytest.mark.parametrize('old,new', [
    ('rounds=5','rounds=4'), ('done=1','done=0'), ('expired=0','expired=1'),
    ('nmis=0','nmis=1'), ('alert_minor=0','alert_minor=1'),
    ('console_framing=0','console_framing=1'), ('frames=6','frames=5'),
    ('sleep_wakes=1','sleep_wakes=0'), ('cycles=5138','cycles=100000'),
    ('Sa1170001M00000000','Sa1170000M00000000'), ('RECORD end\n',''),
    ('RECORD end\n','RECORD end\nRECORD end\n'),
    ('RECORD end\n','RECORD mask=00000000\nRECORD end\n'),
    ('RECORD end\n','ERROR: simulator failure\nRECORD end\n'),
])
def test_reject_partial_or_corrupted_verdict(complete, old, new):
    with pytest.raises(ValueError):
        probe.check_log(complete.replace(old, new))


def test_isolated_preparation_and_shell_quoting(tmp_path):
    source = probe.SOC/'tb/uart_rx_monitor.vh'
    before = source.read_bytes()
    output = tmp_path/"receiver's path with space"
    probe.prepare(output, True)
    assert source.read_bytes() == before
    bench = (output/'tb_uart_rx.v').read_text()
    assert "rx_probe_frame(8'h34,1'b1)" in bench
    assert '.uart_rx_i  (rx_probe_pin)' in bench
    for name in ['run_rtl.sh','build_rtl.sh','build_sw.sh']:
        subprocess.run(['bash','-n',str(output/name)], check=True)
    with pytest.raises(FileExistsError):
        probe.prepare(output)
    probe.verify_sources(output)
    (output/'tb_uart_rx.v').write_text(bench+'\n// changed after preparation\n')
    with pytest.raises(ValueError, match='Input changed'):
        probe.verify_sources(output)


def test_changed_source_anchor_rejected():
    with pytest.raises(ValueError):
        probe.once('twice twice', 'twice', 'replacement')
