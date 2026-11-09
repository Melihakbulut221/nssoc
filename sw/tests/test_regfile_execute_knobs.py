# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Register-file execute-path knobs against a golden model (docs/ibex-execute-timing.md).

Runs hw/soc/tb/tb_regfile_exec.v at each knob combination: random writes
and reads with back-to-back write-then-read hazards, single and double
upsets injected into data and check flip-flops (the pending register
included), report checks, and a scrubbed final sweep. BADPRE corrupts
the predecode once and must stop the run.
"""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [ROOT / 'hw/soc/rtl/ibex_regfile_secded.v', ROOT / 'hw/rtl/secded_enc.v',
           ROOT / 'hw/rtl/secded_dec.v', ROOT / 'hw/soc/tb/tb_regfile_exec.v']

CONFIGS = {
    'default': {},
    'corrpre': {'CORRPRE': 1},
    'chkdefer': {'CHKDEFER': 1},
    'corrpre_chkdefer': {'CORRPRE': 1, 'CHKDEFER': 1},
    'corrpre_rdpre': {'CORRPRE': 1, 'RDPRE': 1},
    'corrpre_chkdefer_rdpre': {'CORRPRE': 1, 'CHKDEFER': 1, 'RDPRE': 1},
    'rdraw_chkdefer_rdpre': {'RDRAW': 1, 'CHKDEFER': 1, 'RDPRE': 1},
    'corrpre_chkdefer_noscrub': {'CORRPRE': 1, 'CHKDEFER': 1, 'SCRUB': 0},
    'chkdefer_noscrub': {'CHKDEFER': 1, 'SCRUB': 0},
}


def run(tmp_path, params, define=True):
    iverilog, vvp = shutil.which('iverilog'), shutil.which('vvp')
    if not iverilog or not vvp:
        pytest.skip('Icarus is required')
    binary = tmp_path / 'tb.vvp'
    command = [iverilog, '-g2005', '-s', 'tb_regfile_exec', '-o', str(binary)]
    if define:
        command.append('-DSOC_RF_EXEC')
    command += ['-Ptb_regfile_exec.%s=%d' % kv for kv in params.items()]
    command += list(map(str, SOURCES))
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if compiled.returncode != 0:
        return compiled.returncode, compiled.stdout + compiled.stderr
    result = subprocess.run([vvp, '-n', str(binary)], capture_output=True, text=True,
                            timeout=600)
    return result.returncode, result.stdout + result.stderr


@pytest.mark.parametrize('name', sorted(CONFIGS))
def test_golden_model_hazards_and_injected_upsets(tmp_path, name):
    code, output = run(tmp_path, CONFIGS[name])
    assert code == 0 and '\nPASS' in output, output[-3000:]
    assert 'failures=0' in output, output[-3000:]


def test_the_default_build_is_the_file_without_the_define(tmp_path):
    """Without SOC_RF_EXEC the file is the one every default build reads,
    and the shipped configurations run clean against the same model..."""
    for params in ({}, {'CORRPRE': 1}, {'SCRUB': 0}):
        code, output = run(tmp_path, params, define=False)
        assert code == 0 and '\nPASS' in output, output[-2000:]


@pytest.mark.parametrize('knob', ['CHKDEFER', 'RDPRE', 'RDRAW'])
def test_a_knob_without_its_define_stops_elaboration(tmp_path, knob):
    """...and a knob without it is refused rather than silently ignored."""
    code, output = run(tmp_path, {knob: 1}, define=False)
    assert code != 0 and 'SOC_RF_EXEC' in output, output[-2000:]


def test_a_wrong_predecode_stops_the_run(tmp_path):
    code, output = run(tmp_path, {'CORRPRE': 1, 'RDPRE': 1, 'BADPRE': 1})
    assert code != 0 and 'RDPRE predecode mismatch' in output, output[-3000:]


def test_nothing_in_the_design_builds_the_raw_read():
    """RDRAW is a measurement: only the two flows that measure it may
    reach it, from a variable that defaults to 0."""
    for path in list((ROOT / 'hw/soc/rtl').glob('*.v')) + \
            list((ROOT / 'hw/soc/flow').glob('*.sh')):
        if path.name in ('syn_soc_top.sh', 'sim_soc.sh'):
            continue
        text = path.read_text()
        assert 'RDRAW 1' not in text and '.RDRAW(1)' not in text, path.name
    assert 'IBEX_RF_RDRAW:-0' in (ROOT / 'hw/soc/flow/syn_soc_top.sh').read_text()
    assert 'SOC_RF_RDRAW:-0' in (ROOT / 'hw/soc/flow/sim_soc.sh').read_text()
