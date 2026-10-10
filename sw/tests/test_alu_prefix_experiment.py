# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure immutable-input and complete-ALU proof contract checks; no native work."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
try:
    SPEC = importlib.util.spec_from_file_location('cloud_alu', ROOT/'scripts/run_cloud_alu_prefix.py')
    ALU = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(ALU)
finally:
    sys.path.pop(0)


@pytest.fixture
def lock():
    return json.loads((ROOT/ALU.LOCK).read_text())


@pytest.fixture
def restored(tmp_path, lock):
    bundle = tmp_path/'inputs'
    ALU.validate_lock(lock)
    ALU.restore(ROOT/lock['archive']['path'], bundle, lock)
    return bundle


def test_exact_original_and_only_addition_changes(restored, lock):
    original = (restored/lock['original_alu']).read_bytes()
    candidate, negative = ALU.prefix.prepare(original)
    assert hashlib.sha256(candidate).hexdigest() == ALU.prefix.CANDIDATE_SHA
    assert hashlib.sha256(negative).hexdigest() == ALU.prefix.NEGATIVE_SHA
    assert candidate.decode().replace(ALU.prefix.PREFIX, ALU.prefix.OLD).encode() == original
    assert negative.replace(b"{carry_g[6][31:0],1'b1}", b"{carry_g[6][31:0],1'b0}") == candidate
    assert 'RV32B' in original.decode()  # The full ALU, not a toy addition module.


def test_changed_generated_default_fails(restored, lock):
    data = (restored/lock['original_alu']).read_bytes()
    with pytest.raises(ValueError, match='differs from C10'):
        ALU.prefix.prepare(data+b'\n')


def test_complete_output_miter_has_no_constraints_or_internal_matching(tmp_path):
    script = ALU.prefix.miter(tmp_path/'original file.v', tmp_path/'candidate file.v')
    assert script.count('chparam -set RV32B 0 ibex_alu') == 2
    assert 'miter -equiv -flatten gold gate miter' in script
    assert 'memory_map\nopt_clean\nsat -verify -prove trigger 0 -show-inputs -show-outputs' in script
    assert '-set-assumes' not in script and 'equiv_make' not in script and '-timeout' not in script
    assert 'original file.v"' in script
    with pytest.raises(ValueError, match='Invalid Yosys path'):
        ALU.prefix.miter('injection\nsat', 'candidate.v')


@pytest.mark.parametrize('flag', list(ALU.PROFILE))
def test_different_profile_rejected(lock, flag):
    lock['source_parameters'][flag] = 0
    with pytest.raises(ValueError, match='profile changed'):
        ALU.validate_lock(lock)


@pytest.mark.parametrize('target', ['snapshot', 'tracked'])
def test_snapshot_and_current_source_pin_changes_rejected(lock, target):
    if target == 'snapshot':
        lock['files'][lock['original_alu']]['sha256'] = '0'*64
    else:
        name = next(iter(lock['tracked_sources']))
        lock['tracked_sources'][name]['sha256'] = '0'*64
    with pytest.raises(ValueError):
        ALU.validate_lock(lock)


def test_snapshot_matches_all_receipt_inputs_and_current_sources(restored, lock):
    assert len(lock['origins']) == 89
    assert len(lock['tracked_sources']) == 47
    assert len(lock['files']) == 99
    for name, expected in lock['tracked_sources'].items():
        ALU.common.verify_file(ROOT/name, expected)
    assert (restored/'notices/ibex/NOTICE').is_file()
    assert all((restored/'LICENSES'/(name+'.txt')).is_file() for name in
               ['Apache-2.0', 'CERN-OHL-W-2.0', 'LGPL-2.1-or-later', 'MIT', 'CC-BY-4.0'])


def test_relocated_full_profile_recipe_inputs_and_single_candidate(tmp_path, restored, lock):
    output = tmp_path/'synthesis'
    output.mkdir()
    original_dir = Path(lock['original_synthesis']).relative_to(lock['original_repo'])
    shutil.copytree(restored/'repo'/original_dir/'boot-rom', output/'boot-rom')
    alu = tmp_path/'prepared'/'candidate.v'
    alu.parent.mkdir()
    alu.write_bytes(ALU.prefix.prepare((restored/lock['original_alu']).read_bytes())[0])
    template = (restored/'recipe/c10.ys').read_text()
    recipe = ALU.synthesis_recipe(template, restored, output, alu, lock)
    assert recipe.count(str(alu)) == 1
    assert lock['original_repo'] not in recipe and lock['original_pdk'] not in recipe
    inputs = ALU.validate_recipe_inputs(recipe, restored, output, alu)
    assert len(inputs) > 70
    assert inputs[str(alu)]['sha256'] == ALU.prefix.CANDIDATE_SHA
    # Reverse only the prescribed path substitutions: every synthesis instruction
    # and parameter must remain exactly the original historical recipe.
    undo = recipe.replace(str(alu), lock['original_repo']+'/hw/soc/gen/ibex_alu.v')
    undo = undo.replace(str(output), lock['original_synthesis'])
    undo = undo.replace(str(restored/'repo'), lock['original_repo'])
    undo = undo.replace(str(restored/'pdk'), lock['original_pdk'])
    assert undo == template
    alu.unlink()
    with pytest.raises(ValueError, match='Missing or escaped synthesis input'):
        ALU.validate_recipe_inputs(recipe, restored, output, alu)


def test_prepared_path_below_historical_checkout_not_relocated(restored, lock):
    alu = Path(lock['original_repo'])/'hw/soc/out/independent/candidate.v'
    output = alu.parent/'synthesis'
    bundle = alu.parent/'bundle'
    recipe = ALU.synthesis_recipe((restored/'recipe/c10.ys').read_text(), bundle,
                                 output, alu, lock)
    assert str(alu) in recipe
    assert recipe.count(str(alu)) == 1
    assert str(output/'soc_top.netlist.v') in recipe
    assert str(bundle/'repo/hw/soc/rtl/soc_top.v') in recipe


@pytest.mark.parametrize('mutation', ['no_alu', 'double_alu', 'pipeline', 'mbist', 'abc'])
def test_recipe_profile_or_input_drift_rejected(restored, lock, mutation):
    template = (restored/'recipe/c10.ys').read_text()
    if mutation == 'no_alu':
        template = template.replace('/hw/soc/gen/ibex_alu.v', '/wrong.v')
    elif mutation == 'double_alu':
        template += 'read_verilog '+lock['original_repo']+'/hw/soc/gen/ibex_alu.v\n'
    elif mutation == 'pipeline':
        template = template.replace('CORE_WB_STAGE 1', 'CORE_WB_STAGE 0')
    elif mutation == 'mbist':
        template = template.replace('SOC_ETH_MBIST', 'NO_ETH_MBIST')
    else:
        template = template.replace(' -D 20\n', ' -D 20000\n')
    with pytest.raises(ValueError):
        ALU.synthesis_recipe(template, restored, restored/'output', restored/'prepared.v', lock)


@pytest.mark.parametrize('code,text', [(0, 'PASS'), (1, 'SAT proof finished - no model found: SUCCESS!'),
                                     (1, 'ERROR: interrupted'), (0, 'SAT proof finished - model found: FAIL!')])
def test_positive_requires_real_native_success(code, text):
    with pytest.raises(ValueError, match='failed/incomplete'):
        ALU.validate_proof_log(code, text)


@pytest.mark.parametrize('code,text', [(0, 'ERROR: proof did fail!'), (1, 'ERROR: module not found'),
                                     (137, 'Killed'), (1, 'Timed out')])
def test_negative_requires_actual_counterexample_not_process_failure(code, text):
    with pytest.raises(ValueError, match='real counterexample'):
        ALU.validate_proof_log(code, text, negative=True)


def test_expected_proof_and_negative_outcomes():
    ALU.validate_proof_log(0, 'SAT proof finished - no model found: SUCCESS!')
    ALU.validate_proof_log(1, 'ERROR: Called with -verify and proof did fail!', negative=True)


@pytest.mark.parametrize('name,kind', [('../escape', 'file'), ('file', 'link'), ('file', 'duplicate')])
def test_unsafe_archives_rejected_before_native(tmp_path, name, kind):
    archive = tmp_path/'bad.tar.xz'
    payload = b'data'
    with tarfile.open(archive, 'w:xz') as sink:
        info = tarfile.TarInfo(name)
        if kind == 'link':
            info.type = tarfile.SYMTYPE
            info.linkname = '../escape'
            sink.addfile(info)
        else:
            info.size = len(payload)
            sink.addfile(info, io.BytesIO(payload))
            if kind == 'duplicate':
                sink.addfile(info, io.BytesIO(payload))
    lock = dict(archive=ALU.pin(archive), files={'file': dict(bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest())})
    with pytest.raises(ValueError):
        ALU.restore(archive, tmp_path/'out', lock)
    assert not (tmp_path/'escape').exists()


def test_corrupt_archive_pin_rejected(tmp_path, lock):
    mutated = copy.deepcopy(lock)
    mutated['archive']['sha256'] = '0'*64
    with pytest.raises(ValueError):
        ALU.restore(ROOT/lock['archive']['path'], tmp_path/'out', mutated)
    assert not (tmp_path/'out').exists()


def test_no_native_work_outside_cloud(tmp_path, monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    with pytest.raises(ValueError, match='cloud-only'):
        ALU.run('proof', tmp_path/'output', tmp_path/'work')
    assert not (tmp_path/'output').exists()
