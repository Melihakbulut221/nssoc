# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject incomplete, corrupted or faulted CPU Ethernet test results."""
import importlib.util
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('eth_probe', ROOT / 'hw/soc/flow/ethernet_cpu_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

GOOD = '''RECORD site=-1 armed=1 hit=0 done=1 slept=1 expired=0
RECORD cycles=175253 budget=300000 sig=00043b07 mask=00000000 rounds=8
RECORD exit=00000000 magic=600dc0de
RECORD console_chars=19 console_hash=f48b7fa1 console_framing=0
RECORD traps=0 mcause=00000000 nmis=0
RECORD wdog1=0 wdog2=0 wdog3=0 wdog_rst_events=0
RECORD alert_minor=0 alert_int=0 alert_bus=0 dblfault=0 kicks=-1
ETH_GL frames=8 payload_bytes=2171 crc_checks=8
RECORD end
'''


def test_complete_gate_result_and_independent_payload_signature(tmp_path):
    path = tmp_path / 'gate.log'
    path.write_text(GOOD)
    result = probe.check_log(path, 'gl')
    assert result['payload_bytes'] == 2171
    assert result['signature'] == '00043b07'


@pytest.mark.parametrize('old,new', [
    ('sig=00043b07', 'sig=00043b08'),
    ('mask=00000000', 'mask=00000010'),
    ('rounds=8', 'rounds=7'),
    ('cycles=175253', 'cycles=300000'),
    ('console_framing=0', 'console_framing=1'),
    ('alert_minor=0', 'alert_minor=1'),
    ('wdog_rst_events=0', 'wdog_rst_events=1'),
    ('nmis=0', 'nmis=1'),
    ('armed=1', 'armed=0'),
    ('hit=0', 'hit=1'),
    ('crc_checks=8', 'crc_checks=7'),
    ('payload_bytes=2171', 'payload_bytes=2170'),
    ('RECORD end\n', ''),
    ('RECORD end', 'RECORD end\nRECORD end'),
    ('RECORD end', 'FATAL: packet error\nRECORD end'),
    ('RECORD end', 'RECORD sig=00043b07\nRECORD end'),
])
def test_bad_or_incomplete_result_fails(tmp_path, old, new):
    path = tmp_path / 'bad.log'
    path.write_text(GOOD.replace(old, new))
    with pytest.raises(ValueError):
        probe.check_log(path, 'gl')


def test_prepare_preserves_original_instruments_and_quotes_output(tmp_path):
    original = {p: p.read_bytes() for p in (probe.SOC / 'tb').glob('tb_soc_fi*.v')}
    out = tmp_path / 'probe with spaces'
    probe.prepare(out)
    for p, data in original.items():
        assert p.read_bytes() == data
    for script in out.glob('*.sh'):
        subprocess.run(['bash', '-n', str(script)], check=True)
    # Existing evidence must never be overwritten by preparation.
    with pytest.raises(FileExistsError):
        probe.prepare(out)


def test_template_drift_fails_closed():
    with pytest.raises(ValueError):
        probe.replace_once('changed', 'missing', 'replacement')
    with pytest.raises(ValueError):
        probe.replace_once('twice twice', 'twice', 'replacement')
