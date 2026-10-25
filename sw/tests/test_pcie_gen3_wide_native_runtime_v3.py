# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound reuse controls and actual cocotb interpreter discovery."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('wide_runtime_v3', ROOT / 'scripts/check_pcie_gen3_continuous_rx_wide_native_v3.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


@pytest.fixture
def mapped(tmp_path):
    sources = [tmp_path / n for n in ('rtl.v', 'cells.v', 'cells.lib')]
    for p in sources:
        p.write_text('fixture ' + p.name)
    (tmp_path / 'mapped.v').write_text('module frozen; endmodule\n')
    (tmp_path / 'map.ys').write_text('synth -top frozen -nofsm -noabc; check -assert;\n')
    (tmp_path / 'map.log').write_text('completed\n')
    (tmp_path / 'mapped.json').write_text(json.dumps({'modules': {'soc_pcie_gen3_continuous_rx_wide': {'cells': {'u': {'type': 'sg13g2_inv_1'}}}}}))
    result = dict(mapping_strategy='explicit_no_fsm_optimization_v2', max_encoded_bytes=150,
                  top='soc_pcie_gen3_continuous_rx_wide', mode='native', commands=[dict(returncode=0)],
                  inputs={str(p): m.pin(p) for p in sources}, runtime={},
                  outputs={n: m.pin(tmp_path / n) for n in ('mapped.v', 'mapped.json', 'map.ys', 'map.log')}, mapped_cells=1)
    path = tmp_path / 'result.json'
    path.write_text(json.dumps(result))
    return path, sources, result


def check(fixture):
    path, sources, _ = fixture
    return m.bind_mapping(path, sources[:1], sources[1], sources[2], 150)


def test_completed_map_is_reusable(mapped):
    assert check(mapped)['mapped_cells'] == 1


@pytest.mark.parametrize('name', ['mapped.v', 'mapped.json', 'map.ys', 'map.log', 'rtl.v', 'cells.v', 'cells.lib'])
def test_actual_file_mutation_rejected(mapped, name):
    (mapped[0].parent / name).write_text('changed')
    with pytest.raises((ValueError, KeyError)):
        check(mapped)


@pytest.mark.parametrize('field,value', [('max_encoded_bytes', 4118), ('mapped_cells', 2), ('top', 'wrong'), ('mode', 'rtl'), ('commands', [dict(returncode=1)])])
def test_wrong_profile_or_incomplete_map_rejected(mapped, field, value):
    mapped[2][field] = value
    mapped[0].write_text(json.dumps(mapped[2]))
    with pytest.raises(ValueError):
        check(mapped)


def test_unimplemented_cells_rejected_with_current_pin(mapped):
    p = mapped[0].parent / 'mapped.json'
    p.write_text(p.read_text().replace('sg13g2_inv_1', '$logic_not'))
    mapped[2]['outputs']['mapped.json'] = m.pin(p)
    mapped[0].write_text(json.dumps(mapped[2]))
    with pytest.raises(ValueError, match='native cell census'):
        check(mapped)


def test_actual_cocotb_runtime_and_corrected_make_recipe(tmp_path):
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONHOME', 'PYTHONPATH', 'PYTHONEXECUTABLE')}
    venv = ROOT / 'hw/soc/tools/cocotb-venv/bin'
    env['PATH'] = str(venv) + ':' + str(ROOT / 'hw/soc/tools/oss-cad-suite/bin') + ':' + env['PATH']
    interpreter = subprocess.check_output([str(venv / 'cocotb-config'), '--python-bin'], env=env, text=True).strip()
    assert Path(interpreter).parent == venv
    discovery = subprocess.check_output([interpreter, '-c', 'import pygpi,cocotb,sys; print(sys.version_info[:2]);print(pygpi.__file__);print(cocotb.__file__)'], env=env, text=True)
    assert '(3, 12)' in discovery and 'cocotb-venv' in discovery
    # Execute the actual new Makefile's parse-time interpreter expression.
    wrapper = tmp_path / 'probe.mk'
    wrapper.write_text('include ' + str(ROOT / 'hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_wide_runtime_v3') + '\n.PHONY: probe\nprobe:\n\t@"$(PCIE_PYTHON)" -c "import pygpi,sys; print(pygpi.__file__);print(sys.version_info[:2])"\n')
    outcome = subprocess.run(['make', '-f', str(wrapper), '--no-print-directory', 'probe'], env=env, cwd=tmp_path, capture_output=True, text=True)
    assert outcome.returncode == 0, outcome.stdout + outcome.stderr
    assert 'No such file' not in outcome.stderr
    assert 'pygpi' in outcome.stdout and '(3, 12)' in outcome.stdout
