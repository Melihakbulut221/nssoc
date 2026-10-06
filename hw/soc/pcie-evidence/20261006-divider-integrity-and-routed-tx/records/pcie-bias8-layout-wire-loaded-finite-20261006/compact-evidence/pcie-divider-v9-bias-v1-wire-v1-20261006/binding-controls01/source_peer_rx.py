# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read-only exact derivative audit; never executes the binder/control harness."""
import ast
import datetime
import hashlib
import json
import resource
from pathlib import Path

resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
B = Path(__file__).resolve().parent
W = B.parent
checked = {}


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        result = {'bytes': p.stat().st_size, 'sha256': hashlib.file_digest(f, 'sha256').hexdigest()}
    checked[str(p)] = result
    return result


def j(p):
    return json.loads(Path(p).read_text())


freeze_path = B / 'source-freeze.json'
freeze_pin = pin(freeze_path)
assert freeze_pin == {'bytes': 369110, 'sha256': '571655c1142d77545b5706571f891fc5873ccfbda465edec92a90296959c95cd'}
freeze = j(freeze_path)
assert len(freeze['inputs']) == 1646 and freeze['physical_mutation'] is False
for name, expected in freeze['inputs'].items():
    assert pin(name) == expected, name
bridge_path = B / 'source-bridge.json'
bridge = j(bridge_path)
parent = Path(bridge['parent'])
child = B / 'run.py'
assert str(child) == bridge['child']
assert pin(parent) == bridge['parent_pin'] and pin(child) == bridge['child_pin']
original, current = parent.read_text(), child.read_text()
assert bridge['replacements'] == [
    {'old': 'nssoc-div4-v8-cap-v1-', 'new': 'nssoc-div4-v9-bias-v1-', 'count': 3},
    {'old': 'PASS_DIVIDER_V8_CAP24_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY',
     'new': 'PASS_DIVIDER_V9_BIAS8_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY', 'count': 1},
]
forward = original
for edit in bridge['replacements']:
    assert forward.count(edit['old']) == edit['count']
    forward = forward.replace(edit['old'], edit['new'])
assert forward == current
inverse = current
for edit in reversed(bridge['replacements']):
    assert inverse.count(edit['new']) == edit['count']
    inverse = inverse.replace(edit['new'], edit['old'])
assert inverse == original
assert ast.dump(ast.parse(inverse)) == ast.dump(ast.parse(original))

tree = ast.parse(current)
assignments = {n.targets[0].id: n.value for n in tree.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)}
cases = ast.literal_eval(assignments['CASES'])
assert cases == ['positive', 'reference_clock_swap', 'reference_pullup_length', 'reference_missing_tap', 'native_mim_area_corruption']
g_root = Path(ast.literal_eval(assignments['G'].args[0]))
t_root = Path(ast.literal_eval(assignments['T'].args[0]))
assert g_root == Path('/dev/shm/nssoc-div4-v9-bias-v1-layout-01')
assert not t_root.exists() and not (B / 'result.json').exists()
binder = (W / 'bind_source_ids.py').read_text()
assert binder.count("G=Path('/dev/shm/nssoc-div4-v9-bias-v1-layout-01')") == 1
geometry = j(W / 'geometry-execution.json')
assert geometry['status'] == 'PASS_DIVIDER_V9_BIAS8_SAVED_NATIVE_GEOMETRY_AND_SOURCE_BIJECTION_ONLY'
assert len(geometry['steps']) == 7
for step in geometry['steps']:
    assert step['execution']['returncode'] == 0
for name, expected in geometry['outputs'].items():
    assert (checked.get(name) or pin(name)) == expected
assert geometry['resource_contract'] == {
    'cpu': 10, 'native_AS': 2147483648, 'own_scratch': 83886080,
    'reserve': 25165824, 'entry': 1073741824, 'continuous': 536870912,
    'healthy_elapsed_watchdog_seconds': None, 'failure_cleanup_grace_seconds': 5,
}
layout = j(g_root / 'result.json')
instances = {row['name']: row for row in layout['instances']}
assert instances['DIV__XFIRST__XSP']['nets'][0] == 'CLKP'
assert instances['DIV__XFIRST__XUP']['length_um'] == 4.0
assert 'TAP0' in instances
assert instances['DIV__XDP']['length_um'] == instances['DIV__XDN']['length_um'] == 8.0
native = j(W / 'device-location-geometry.json')
assert any(row['model'] == 'cap_cmim' and row['parameters']['A'] > 0 for row in native['devices'])
assert len(native['devices']) == 91

receipt = {
    'status': 'PASS_SOURCE_ONLY_DIVIDER_V9_BIAS8_BINDING_CONTROLS',
    'freeze': freeze_pin, 'findings': [],
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'independent_rehashed_frozen_inputs': len(freeze['inputs']),
    'parent': {'path': str(parent), **pin(parent)},
    'source': {'path': str(child), **pin(child)},
    'bridge': {'path': str(bridge_path), **pin(bridge_path)},
    'geometry_execution': pin(W / 'geometry-execution.json'),
    'review': [
        'Read the complete8611-byte harness; independent exact forward and inverse reconstruct all bytes from reviewed V8 parent. Only three path substrings and one positive status change.',
        'Five copied-input cases remain exact. Positive requires complete semantic equality except provenance inputs. Four negatives each declare one edit and require return1, no result artifact and their specific AssertionError source line.',
        'Copied binder differs solely by its private fixture G root and asserts exact inverse. Original source/native records are deep copies; all written inputs rehashed after execution. Actual V9 pull-down L8 and unchanged targeted first-stage pullup L4 verified.',
        'Frozen seven-function ownership/resource AST selection, private CPU10 globals, 2GiB native limit, 80MiB own/24MiB reserve, 1GiB entry/512MiB floor and terminal execute guards remain byte-identical. No healthy timeout introduced.',
        'All1646 prerequisites rehashed including production binder, completed geometry and runtime/PDK provenance; seven saved geometry returncodes zero and output hashes rebound. Independent saved geometry review remains a separate later gate.',
    ],
    'planned_cases': cases,
    'scope': 'Source-only. No control harness, producer import, binder, native extraction, EDA, process signal or negative case executed. Actual five-run result remains required before any saved-geometry/RC acceptance.',
    'method': {'path': str(Path(__file__)), **pin(__file__)},
}
out = B / 'source-only-peer-rx.json'
assert not out.exists()
out.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'path': str(out), **pin(out), 'inputs': len(freeze['inputs'])}))
