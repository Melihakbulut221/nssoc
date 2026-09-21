# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Generated offset consistency, decoder binding and shipped ABI controls."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
module_spec = importlib.util.spec_from_file_location('peripheral_generator', ROOT/'regmap/generate_peripherals.py')
gen = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(gen)


def test_generated_outputs_are_current():
    result = subprocess.run([sys.executable, str(ROOT/'regmap/generate_peripherals.py'), '--check'],
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_original_register_abi_is_preserved():
    # Independent snapshot of the 105 existing offsets before migration;
    # changing YAML and all its outputs together must still trip this guard.
    specs = gen.load(ROOT/'regmap/peripherals')
    offsets = {block: {name: reg['offset'] for name, reg in spec['registers'].items()}
               for block, spec in specs.items()}
    assert len(offsets) == 12
    assert sum(map(len, offsets.values())) == 105
    assert hashlib.sha256(json.dumps(offsets, sort_keys=True).encode()).hexdigest() == \
        'a54e0ce33860a041c2d878ab4a7c6b8e15aeadec434675a73b824c090069b7de'


def test_c_python_and_rtl_values_agree(tmp_path):
    specs = gen.load(ROOT/'regmap/peripherals')
    namespace = {}
    exec((ROOT/'sw/golden/peripheral_regs_gen.py').read_text(), namespace)
    assertions = ['#include "soc_reg_offsets.h"', '#include "soc_memmap.h"']
    for block, spec in specs.items():
        relative, text = gen.rtl_output(spec, ROOT)
        assert text == (ROOT/relative).read_text()
        for name, reg in spec['registers'].items():
            literal = re.search(r'\b'+reg['rtl']+r"\s*=\s*\d+'h([0-9A-Fa-f]+);", text)
            assert literal and int(literal[1], 16) == namespace[block.upper()][name]
            value = int(literal[1], 16)
            assertions.append(f'_Static_assert(SOC_{block.upper()}_{name}_OFF == {value}, "{block}:{name}");')
        assertions.append(f'_Static_assert({spec["base"]} >= 0, "base exists");')
    result = subprocess.run(['cc', '-std=c11', '-Werror', '-x', 'c', '-c', '-',
                             '-I', str(ROOT/'hw/soc/tb/sw'), '-o', str(tmp_path/'offsets.o')],
                            input='\n'.join(assertions), text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('field,value', [
    ('schema', True), ('schema', 2), ('block', '../uart'), ('block', []),
    ('base', 'unknown'), ('address_bits', True), ('address_bits', 1),
    ('address_bits', 33), ('registers', {}),
])
def test_rejects_invalid_spec(tmp_path, field, value):
    spec = copy.deepcopy(gen.load(ROOT/'regmap/peripherals')['uart'])
    spec[field] = value
    (tmp_path/'uart.yaml').write_text(yaml.safe_dump(spec))
    with pytest.raises(ValueError):
        gen.load(tmp_path)


@pytest.mark.parametrize('offset', [-4, 1, 4096, True, '0x04'])
def test_rejects_unrepresentable_register_offset(tmp_path, offset):
    spec = copy.deepcopy(gen.load(ROOT/'regmap/peripherals')['uart'])
    spec['registers']['DATA']['offset'] = offset
    (tmp_path/'uart.yaml').write_text(yaml.safe_dump(spec))
    with pytest.raises(ValueError):
        gen.load(tmp_path)


@pytest.mark.parametrize('kind', ['yaml_key', 'offset', 'rtl', 'nonscalar_key'])
def test_rejects_ambiguous_definitions(tmp_path, kind):
    spec = copy.deepcopy(gen.load(ROOT/'regmap/peripherals')['uart'])
    if kind == 'offset': spec['registers']['STATUS']['offset'] = 0
    if kind == 'rtl': spec['registers']['STATUS']['rtl'] = 'REG_DATA'
    text = yaml.safe_dump(spec)
    if kind == 'yaml_key': text += '\nschema: 1\n'
    if kind == 'nonscalar_key': text += '\n? [a, b]\n: invalid\n'
    (tmp_path/'uart.yaml').write_text(text)
    with pytest.raises(ValueError):
        gen.load(tmp_path)


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'different_value'])
def test_rtl_binding_fails_closed(tmp_path, mutation):
    spec = gen.load(ROOT/'regmap/peripherals')['uart']
    path = tmp_path/'hw/soc/rtl/soc_uart.v'
    path.parent.mkdir(parents=True)
    text = (ROOT/'hw/soc/rtl/soc_uart.v').read_text()
    declaration = next(line for line in text.splitlines() if 'regmap:uart:DATA' in line)
    if mutation == 'missing': text = text.replace(declaration, '')
    elif mutation == 'duplicate': text += '\n'+declaration+'\n'
    else: text = text.replace(declaration, declaration.replace("12'h000", "12'h080"))
    path.write_text(text)
    if mutation == 'different_value':
        _, expected = gen.rtl_output(spec, tmp_path)
        assert expected != text  # --check rejects this stale RTL without writing it.
        assert path.read_text() == text
    else:
        with pytest.raises(ValueError, match='RTL binding'):
            gen.rtl_output(spec, tmp_path)


def test_generator_is_idempotent_and_check_does_not_write():
    expected = gen.outputs(gen.load(ROOT/'regmap/peripherals'))
    assert all((ROOT/path).read_text() == text for path, text in expected.items())
    assert 'generate_peripherals.py --check' in (ROOT/'scripts/ci_local.sh').read_text()


def test_removed_spec_register_cannot_leave_an_orphan_decoder():
    spec = copy.deepcopy(gen.load(ROOT/'regmap/peripherals')['uart'])
    del spec['registers']['STATUS']
    with pytest.raises(ValueError, match='Orphan'):
        gen.rtl_output(spec, ROOT)
