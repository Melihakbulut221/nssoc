# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native boot preparation must be self-contained without altering a PDK."""
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / 'hw/soc/flow' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_native_lock_covers_every_runner_model_and_mapping_liberty():
    lock = json.loads((ROOT / 'hw/soc/pnr/ihp-native-boot.lock.json').read_text())
    module('prepare_ihp_drc').validate_lock(lock)
    models = module('sim_logic_boot_gl').SRAM_MODELS
    prefix = 'ihp-sg13g2/libs.ref/'
    # Include the actual memory_libmap dependency declared by synthesis, not
    # just the simulator's models. The first hosted replay caught its absence.
    source = (ROOT / 'hw/soc/flow/syn_soc_top.sh').read_text()
    mapping_libs = re.findall(r'\$SG13G2_SRAM_DIR/lib/([^"\s]+)', source)
    assert mapping_libs, 'The Ethernet mapping Liberty dependency was not found'
    assert {r['path'] for r in lock['files']} == {
        'LICENSE', prefix + 'sg13g2_stdcell/verilog/sg13g2_stdcell.v',
        prefix + 'sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib',
        *(prefix + 'sg13g2_sram/verilog/' + name for name in models),
        *(prefix + 'sg13g2_sram/lib/' + name for name in mapping_libs),
    }
    assert lock['commit'] == 'c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'


def test_native_wrapper_refuses_existing_evidence_without_network():
    # Existing checked-in source directory deliberately has the wrong scope.
    result = subprocess.run(['bash', 'scripts/check_soc_native_boot.sh', 'hw/soc/rtl'],
                            cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 2
    assert 'output must be inside' in result.stderr


def test_native_wrapper_refuses_overwriting_completed_output(tmp_path):
    # Reproduce a minimal checkout inside tmp_path; the refusal must happen
    # before even looking for tools, model locks or download scripts.
    root = tmp_path / 'checkout'
    scripts = root / 'scripts'
    scripts.mkdir(parents=True)
    script = scripts / 'check_soc_native_boot.sh'
    script.write_bytes((ROOT / 'scripts/check_soc_native_boot.sh').read_bytes())
    output = root / 'hw/soc/out/existing'
    output.mkdir(parents=True)
    evidence = output / 'result.json'
    evidence.write_text('{"passed":false}\n')
    result = subprocess.run(['bash', str(script), str(output)], text=True, capture_output=True)
    assert result.returncode == 2
    assert 'Refusing to replace existing evidence' in result.stderr
    assert evidence.read_text() == '{"passed":false}\n'


@pytest.mark.parametrize('selectors', [None, ('1', '1'), ('1', '0'), ('bad', '1')])
def test_native_core_selection_is_validated_and_recorded_before_tools(tmp_path, selectors):
    root = tmp_path / 'checkout'
    scripts = root / 'scripts'
    scripts.mkdir(parents=True)
    script = scripts / 'check_soc_native_boot.sh'
    script.write_bytes((ROOT / 'scripts/check_soc_native_boot.sh').read_bytes())
    flow = root / 'hw/soc/flow'
    flow.mkdir(parents=True)
    # Stop at the first dependency boundary; never download or simulate here.
    (flow / 'prepare_ihp_native_boot.py').write_text('raise SystemExit(77)\n')
    env = {k: v for k, v in os.environ.items()
           if k not in ('SOC_CORE_REQ_REG', 'SOC_CORE_WB_STAGE')}
    env['SOC_INTERFACE_PROFILE'] = 'full'
    if selectors is not None:
        env.update(zip(('SOC_CORE_REQ_REG', 'SOC_CORE_WB_STAGE'), selectors))
    output = root / 'hw/soc/out/qualify'
    result = subprocess.run(['bash', str(script), str(output)], env=env,
                            text=True, capture_output=True)
    if selectors == ('bad', '1'):
        assert result.returncode == 2
        assert 'core selectors must be 0 or 1' in result.stderr
        assert not output.exists()
    else:
        assert result.returncode == 77
        record = json.loads((output / 'core-configuration.json').read_text())
        req, wb = map(int, selectors or ('0', '0'))
        assert record['CORE_REQ_REG'] == req
        assert record['CORE_WB_STAGE'] == record['CORE_BRANCH_TARGET_ALU'] == wb
        assert record['interface_profile'] == 'full'
        assert record['status'].startswith('requested configuration;')
