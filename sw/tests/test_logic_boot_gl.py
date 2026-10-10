# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject a gate boot replay that silently uses a different ROM or workload."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('boot_gl', ROOT / 'hw/soc/flow/sim_logic_boot_gl.py')
gl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gl)


@pytest.fixture
def builds(tmp_path):
    syn, fw = tmp_path / 'syn', tmp_path / 'firmware'
    for directory in (syn, fw):
        (directory / 'boot-rom').mkdir(parents=True)
        (directory / 'boot-rom/soc_logic_boot_rom.v').write_text('fixed ROM contents')
    (fw / 'test_soc.bin').write_bytes(b'loader')
    manifest = dict(rtl_sha256=gl.digest(syn / 'boot-rom/soc_logic_boot_rom.v'),
                    image_sha256=gl.digest(fw / 'test_soc.bin'))
    for directory in (syn, fw):
        (directory / 'boot-rom/manifest.json').write_text(json.dumps(manifest))
    (syn / 'soc_top.netlist.v').write_text(
        ''.join(f'RM_IHPSG13_1P_2048x64_c2_bm_bist ram{i} ();\n' for i in range(4)) +
        ''.join(f'RM_IHPSG13_2P_256x16_c2_bm_bist eth{i} ();\n' for i in range(16)))
    return syn, fw, manifest


def test_exact_loader_builds(builds):
    syn, fw, manifest = builds
    assert gl.validate_builds(syn, fw) == manifest


@pytest.mark.parametrize('which', ['image', 'rtl', 'manifest', 'legacy', 'missing_macro'])
def test_changed_or_incompatible_build_rejected(builds, which):
    syn, fw, manifest = builds
    if which == 'image':
        (fw / 'test_soc.bin').write_bytes(b'other loader')
    elif which == 'rtl':
        (syn / 'boot-rom/soc_logic_boot_rom.v').write_text('different encoded contents')
    elif which == 'manifest':
        manifest['first_image_word'] = 99
        (fw / 'boot-rom/manifest.json').write_text(json.dumps(manifest))
    elif which == 'legacy':
        with (syn / 'soc_top.netlist.v').open('a') as stream:
            stream.write('RM_IHPSG13_1P_1024x32_c2_bm_bist rom ();\n')
    else:
        p = syn / 'soc_top.netlist.v'
        p.write_text(p.read_text().replace('RM_IHPSG13_2P_256x16_c2_bm_bist eth15 ();\n', ''))
    with pytest.raises(ValueError):
        gl.validate_builds(syn, fw)


@pytest.mark.parametrize('problem', ['none', 'missing', 'duplicate', 'unaligned', 'outside', 'alias'])
def test_status_symbols_are_distinct_aligned_ram_words(monkeypatch, problem):
    rows = ['00001e64 B exit_code', '00001e68 B exit_magic',
            '00001e9c B checks', '00001ea0 B fails']
    if problem == 'missing':
        rows.pop()
    elif problem == 'duplicate':
        rows.append(rows[0])
    elif problem == 'unaligned':
        rows[-1] = '00001ea1 B fails'
    elif problem == 'outside':
        rows[-1] = '00008000 B fails'
    elif problem == 'alias':
        rows[-1] = '00001e64 B fails'
    monkeypatch.setattr(gl.subprocess, 'check_output', lambda *a, **kw: '\n'.join(rows))
    if problem == 'none':
        assert gl.read_symbols('nm', Path('app.elf'))['checks'] == 0x1e9c
    else:
        with pytest.raises(ValueError):
            gl.read_symbols('nm', Path('app.elf'))


def test_timeout_is_not_a_pass_and_keeps_output(tmp_path):
    log = tmp_path / 'run.log'
    result = gl.run_logged([sys.executable, '-c',
                           'import time; print("started", flush=True); time.sleep(5)'], log, 0.2)
    assert result['returncode'] == 124
    assert log.read_text() == 'started\n'
    with pytest.raises(FileExistsError):
        gl.run_logged([sys.executable, '-c', 'pass'], log, 1)


@pytest.mark.parametrize('code,banner,expected', [(0, True, True), (1, True, False),
                                                 (0, False, False), (124, False, False)])
def test_native_cell_gate_requires_process_and_assertions(tmp_path, monkeypatch, code, banner, expected):
    library = tmp_path / 'cells.v'
    library.write_text('unchanged vendor model')
    def fake_run(command, path, timeout):
        path.write_text('NATIVE_CELL_GATE PASS\n' if banner else '')
        return dict(command=command, returncode=code, elapsed_s=0)
    monkeypatch.setattr(gl, 'run_logged', fake_run)
    result = gl.check_native_cell('iverilog', '/tools/iverilog', library, tmp_path / 'gate')
    assert result['passed'] == expected
    assert library.read_text() == 'unchanged vendor model'


def test_changed_native_model_rejected(tmp_path, monkeypatch):
    library = tmp_path / 'cells.v'
    library.write_text('original')
    def fake_run(command, path, timeout):
        path.write_text('NATIVE_CELL_GATE PASS\n')
        library.write_text('changed during execution')
        return dict(command=command, returncode=0, elapsed_s=0)
    monkeypatch.setattr(gl, 'run_logged', fake_run)
    assert not gl.check_native_cell('iverilog', '/tools/iverilog', library, tmp_path / 'gate')['passed']
