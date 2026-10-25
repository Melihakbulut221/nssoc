# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""The IRQ probe must distinguish a complete success from partial/negative runs."""
import importlib.util
from pathlib import Path
import subprocess

import pytest

SCRIPT=Path(__file__).resolve().parents[2]/'hw/soc/flow/external_irq_probe.py'
spec=importlib.util.spec_from_file_location('irq_probe',SCRIPT)
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


@pytest.fixture
def complete():
    return '''RECORD done=1 slept=1 expired=0 cycles=5138 budget=100000
RECORD sig=e1700002 mask=00000000 rounds=3 exit=00000000 magic=600dc0de
RECORD traps=0 nmis=0 wdog1=0 wdog2=0 wdog3=0
RECORD alert_minor=0 alert_int=0 alert_bus=0 dblfault=0
RECORD console_chars=19 console_framing=0
RECORD console_tail=   Se1700002M00000000
EXTIRQ assertions=4 sleep_wakes=2
RECORD end
'''


def test_complete_cpu_and_external_source_observations(complete):
    assert probe.check_log(complete)['status']=='PASS'


@pytest.mark.parametrize('old,new',[
    ('mask=00000000','mask=00000100'),
    ('exit=00000000','exit=00000001'),
    ('rounds=3','rounds=2'),
    ('nmis=0','nmis=1'),
    ('alert_bus=0','alert_bus=1'),
    ('console_framing=0','console_framing=1'),
    ('Se1700002M00000000','Se1700001M00000000'),
    ('assertions=4','assertions=3'),
    ('sleep_wakes=2','sleep_wakes=1'),
    ('cycles=5138','cycles=100000'),
    ('RECORD end\n',''),
    ('RECORD end\n','RECORD end\nRECORD end\n'),
    ('RECORD end\n','RECORD mask=00000000\nRECORD end\n'),
    ('RECORD end\n','ERROR: unrelated simulator failure\nRECORD end\n'),
])
def test_partial_or_corrupted_verdict_is_rejected(complete,old,new):
    with pytest.raises(ValueError):
        probe.check_log(complete.replace(old,new))


def test_negative_control_is_never_reported_as_a_passing_product(complete):
    negative=complete.replace('mask=00000000','mask=00000100').replace('exit=00000000','exit=00000100').replace('M00000000','M00000100')
    with pytest.raises(ValueError):
        probe.check_log(negative)
    assert probe.check_log(negative,True)['status']=='EXPECTED t0 FAILURE'
    with pytest.raises(ValueError):
        probe.check_log(complete,True)
    with pytest.raises(ValueError):
        probe.check_log(negative.replace('traps=0','traps=1'),True)


def test_preparation_isolated_and_shell_paths_quoted(tmp_path):
    output=tmp_path/'IRQ with space and quote\'s'
    crt=probe.SOC/'tb/sw/crt0.S';before=crt.read_bytes()
    result=probe.prepare(output,True)
    assert result['legacy_t0_negative_control']
    assert crt.read_bytes()==before
    for name in ['run_rtl.sh','run_gl.sh','build_sw.sh','build_rtl.sh','build_gl.sh']:
        subprocess.run(['bash','-n',str(output/name)],check=True)
    assert '--expect-t0-failure' in (output/'run_rtl.sh').read_text()
    assert 'ext_probe_irq' in (output/'tb_irq_rtl.v').read_text()
    assert 'ext_probe_irq' in (output/'tb_irq_gl.v').read_text()
    with pytest.raises(FileExistsError):
        probe.prepare(output)


def test_changed_legacy_control_anchor_fails_closed():
    source=(probe.SOC/'tb/sw/crt0.S').read_text()
    with pytest.raises(ValueError):
        probe.legacy_crt(source.replace('vec_fast12:', 'renamed_stub:'))
