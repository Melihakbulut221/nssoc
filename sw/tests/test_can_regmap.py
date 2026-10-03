# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bank aliases, the immutable byte ABI and prepared RTL must agree."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'regmap'))
import generate_can as gen


def test_generated_can_outputs_and_compiled_c_agree(tmp_path):
    spec = gen.load()
    for name, text in gen.outputs(spec).items():
        assert (ROOT / name).read_text() == text
    namespace = {}
    exec((ROOT / 'sw/golden/can_regs_gen.py').read_text(), namespace)
    checks = ['#include "soc_can_regs.h"']
    for bank, regs in spec['banks'].items():
        assert namespace['CAN_' + bank] == regs
        for name, value in regs.items():
            checks.append(f'_Static_assert(SOC_CAN_{bank}_{name}_OFF == {value}, "{bank}/{name}");')
    subprocess.run(['cc', '-std=c11', '-Werror', '-x', 'c', '-c', '-',
                    '-I', str(ROOT / 'hw/soc/tb/sw'), '-o', str(tmp_path / 'offsets.o')],
                   input='\n'.join(checks), text=True, capture_output=True, check=True)


def test_frozen_byte_abi_and_intentional_bank_aliases():
    banks = gen.load()['banks']
    assert len(gen.values(gen.load())) == 70
    # Independent pre-migration byte-ABI fingerprint, not an output digest.
    assert hashlib.sha256(json.dumps(banks, sort_keys=True).encode()).hexdigest() == '8e92918e15ae7edc7cd0b194494d6b46b53512c021e3e176729d9c0a6594b19b'
    assert banks['BASIC_RESET']['ACR0'] == banks['EXTENDED']['IER']
    assert banks['EXTENDED_TX'] == banks['EXTENDED_RX']
    assert banks['EXTENDED_RESET']['ACR0'] == banks['EXTENDED_TX']['DATA0']
    for bank in ('BASIC_TX', 'BASIC_RX', 'EXTENDED_TX', 'EXTENDED_RX'):
        offsets = banks[bank]
        assert all(offsets[f'DATA{i}'] == offsets['DATA0'] + i for i in range(len(offsets)))


@pytest.mark.parametrize('defect', ['schema_bool', 'width', 'read_width', 'missing_bank',
                                   'unknown_bank', 'missing_register', 'duplicate_offset',
                                   'negative', 'overflow', 'bool_offset', 'string_offset'])
def test_invalid_bank_maps_are_rejected(tmp_path, defect):
    spec = copy.deepcopy(gen.load())
    if defect == 'schema_bool': spec['schema'] = True
    elif defect == 'width': spec['address_bits'] = 7
    elif defect == 'read_width': spec['register_read_bits'] = 8
    elif defect == 'missing_bank': spec['banks'].pop('BASIC_RX')
    elif defect == 'unknown_bank': spec['banks']['UNKNOWN'] = {}
    elif defect == 'missing_register': spec['banks']['COMMON'].pop('MODE')
    else: spec['banks']['COMMON']['MODE'] = {
        'duplicate_offset': 1, 'negative': -1, 'overflow': 32,
        'bool_offset': False, 'string_offset': '0'}[defect]
    path = tmp_path / 'bad.yaml'; path.write_text(yaml.safe_dump(spec))
    with pytest.raises(ValueError): gen.load(path)


@pytest.fixture(scope='module')
def legacy_can_sources(tmp_path_factory):
    # Deliberately the immutable PRE-migration snapshot, not the current
    # prepared-source fixture whose transformation has since changed.
    from evidence import recorded_bundle
    output = tmp_path_factory.mktemp('legacy-can')
    root = recorded_bundle(ROOT / 'docs/evidence/prepared-sources-20260921.json',
                           output, live_root=output / 'pre-migration-reference')
    bundle = (root / 'hw/soc/gen/interfaces-full.bundle.vh').read_text()
    return {name: re.search(r'// Source: ext/can/rtl/verilog/' + re.escape(name) +
                           r'\n(.*?)(?=\n// Source:|\Z)', bundle, re.S)[1]
            for name in ('can_registers.v', 'can_top.v', 'can_fifo.v')}


def canonical(text):
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    text = re.sub(r"(\d+)'d(\d+)", lambda m: f"{int(m[1])}'d{int(m[2])}", text)
    return re.sub(r'\s+', '', text)


@pytest.mark.parametrize('name', ['can_registers.v', 'can_top.v', 'can_fifo.v'])
def test_prepared_rtl_expands_to_identical_pinned_tokens(legacy_can_sources, name):
    original = legacy_can_sources[name]
    adapted = gen.adapt(name, original, gen.load())
    constants = dict(re.findall(r"localparam \[7:0\] (NSSOC_CAN_\w+) = 8'd(\d+);", adapted))
    assert constants
    expanded = re.sub(r"localparam \[7:0\] NSSOC_CAN_\w+ = 8'd\d+;\n", '', adapted)
    def expand(match):
        width = int(match[2]) + 1 if match[2] else 8
        return f"{width}'d{int(constants[match[1]])}"
    expanded = re.sub(r'(NSSOC_CAN_\w+)(?:\[(\d+):0\])?', expand, expanded)
    assert canonical(expanded) == canonical(original)
    assert not re.search(r"\baddr\s*(?:==|>=|<=|-)\s*\d+'d", adapted)


def test_modified_upstream_literal_or_map_cannot_silently_rebind(legacy_can_sources):
    original = legacy_can_sources['can_registers.v']
    for source, spec in [(original.replace("addr == 8'd0", "addr == 8'd30", 1), gen.load()),
                         (original, gen.load())]:
        if source == original: spec['banks']['COMMON']['MODE'] = 30
        with pytest.raises(ValueError, match='ABI mismatch'):
            gen.adapt('can_registers.v', source, spec)


def test_duplicate_yaml_keys_are_rejected(tmp_path):
    path = tmp_path / 'duplicate.yaml'
    path.write_text((ROOT / 'regmap/can.yaml').read_text() + '\nschema: 1\n')
    with pytest.raises(ValueError, match='Duplicate'): gen.load(path)


def normalized_pin_tests(text):
    maps = {'CAN_' + bank: regs for bank, regs in gen.load()['banks'].items()}
    maps['I2C'] = {'STATUS': 4}  # The old CAN negative test used this numeric alias.
    class Expand(ast.NodeTransformer):
        def visit_Subscript(self, node):
            self.generic_visit(node)
            if isinstance(node.value, ast.Name) and node.value.id in maps and isinstance(node.slice, ast.Constant):
                return ast.Constant(maps[node.value.id][node.slice.value])
            return node
        def visit_BinOp(self, node):
            self.generic_visit(node)
            if isinstance(node.op, ast.Add) and isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
                return ast.Constant(node.left.value + node.right.value)
            return node
    names = {'can_two_node_standard_frame_and_byte_lanes',
             'can_extended_id_eight_bytes_and_remote_frame'}
    functions = [node for node in ast.parse(text).body
                 if isinstance(node, ast.AsyncFunctionDef) and node.name in names]
    assert len(functions) == 2
    def canonical(node):
        # ast.dump changed empty-field formatting between Python 3.12/3.14.
        # Serialize semantic nodes ourselves, ignoring only absent/empty
        # optional fields and source locations, consistently on both versions.
        if isinstance(node, ast.AST):
            return {'node': type(node).__name__, **{
                field: canonical(value) for field, value in ast.iter_fields(node)
                if value is not None and value != []}}
        if isinstance(node, list):
            return [canonical(value) for value in node]
        return node
    return json.dumps([canonical(Expand().visit(node)) for node in functions], sort_keys=True)


def test_existing_can_frames_change_only_constant_spellings():
    source = (ROOT / 'hw/soc/tb/cocotb/test_soc_interfaces.py').read_text()
    actual = normalized_pin_tests(source)
    # Taken from the two pre-migration test ASTs after resolving old I2C[STATUS].
    assert hashlib.sha256(actual.encode()).hexdigest() == '6e56a349e45a5f119d2665485ef3b9ca7837b649318fc091bea3d0f038f740e6'
    anchor = 'async def can_two_node_standard_frame_and_byte_lanes(d):'
    assert source.count(anchor) == 1
    mutant = source.replace(anchor, anchor + '\n    assert False', 1)
    assert normalized_pin_tests(mutant) != actual
