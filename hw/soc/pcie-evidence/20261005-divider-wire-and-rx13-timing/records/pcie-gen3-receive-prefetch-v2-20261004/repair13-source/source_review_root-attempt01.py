# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent saved-source RX13 review; never executes the candidate."""
import ast
import hashlib
import json
from pathlib import Path
import re

B = Path('hw/soc/out/pcie-gen3-receive-prefetch-v2-20261004')
S = B / 'repair13-source'


def pin(path):
    data = Path(path).read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def verify(path, expected):
    assert pin(path) == {k: expected[k] for k in ('bytes', 'sha256')}, path


bridge = json.loads((S / 'derivation.json').read_text())
old = Path(bridge['before']['path']).read_text()
new = Path(bridge['after']['path']).read_text()
verify(bridge['before']['path'], bridge['before'])
verify(bridge['after']['path'], bridge['after'])
forward = old
for change in bridge['changes']:
    assert forward.count(change['before']) == 1
    forward = forward.replace(change['before'], change['after'], 1)
assert forward == new
backward = new
for change in reversed(bridge['changes']):
    assert backward.count(change['after']) == 1
    backward = backward.replace(change['after'], change['before'], 1)
assert backward == old
trees = [ast.parse(x) for x in (old, new)]
funcs = [{n.name: ast.dump(n, include_attributes=False)
          for n in tree.body if isinstance(n, ast.FunctionDef)} for tree in trees]
assert funcs[0] == funcs[1]
assigns = {}
for n in trees[1].body:
    if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
        if n.targets[0].id in ('targets', 'upsizes', 'EXACT_BASELINE_PINS'):
            assigns[n.targets[0].id] = ast.literal_eval(n.value)
for path, expected in assigns['EXACTLINE_PINS' if 'EXACTLINE_PINS' in assigns else 'EXACT_BASELINE_PINS'].items():
    verify(path, expected)

route = Path('/dev/shm/nssoc-rx-prefetch-v2-repair12-drt-01')
cells = {}
verilog = (route / 'routed.v').read_text()
for m in re.finditer(r'\b(sg13g2_\w+)\s+(\w+)\s*\((.*?)\);', verilog, re.S):
    master, name, body = m.groups()
    assert name not in cells
    cells[name] = (master, dict(re.findall(r'\.(\w+)\s*\(\s*([^()]+?)\s*\)', body)))
assert len(cells) > 10000
libpath = re.search(r'read_liberty -corner slow \{([^}]+)\}', (route / 'route.tcl').read_text())[1]
libtext = Path(libpath).read_text()


def named_blocks(text, kind):
    result = {}
    pattern = re.compile(r'\b' + re.escape(kind) + r'\s*\(\s*"?([\w]+)"?\s*\)\s*\{')
    for m in pattern.finditer(text):
        depth = 1
        end = m.end()
        while depth:
            assert end < len(text)
            depth += (text[end] == '{') - (text[end] == '}')
            end += 1
        result[m[1]] = text[m.end():end-1]
    return result


libcells = named_blocks(libtext, 'cell')
pinlib = {name: named_blocks(body, 'pin') for name, body in libcells.items()}
directions = {name: {pn: re.search(r'\bdirection\s*:\s*(\w+)\s*;', body)[1]
                    for pn, body in ports.items()} for name, ports in pinlib.items()}
observed = []
for t in assigns['targets']:
    master, ports = cells[t['name']]
    assert master == t['master'] and ports[t['output_pin']] == t['net']
    assert directions[master][t['output_pin']] == 'output'
    actual = []
    outputs = []
    for name, (cm, cp) in cells.items():
        for pn, net in cp.items():
            if net != t['net']:
                continue
            direct = directions[cm][pn]
            if direct == 'input':
                actual.append(name + '/' + pn)
            elif direct == 'output':
                outputs.append(name + '/' + pn)
            else:
                raise AssertionError((name, pn, direct))
    assert sorted(actual) == sorted(t['loads'])
    assert outputs == [t['name'] + '/' + t['output_pin']]
    bports = pinlib[t['buffer']]
    assert directions[t['buffer']]['A'] == 'input'
    assert directions[t['buffer']]['X'] == 'output'
    assert re.search(r'function\s*:\s*"([^"]+)"', bports['X'])[1].strip() == 'A'
    observed.append({'driver': t['name'], 'master': master, 'net': t['net'],
                     'actual_input_loads': sorted(actual), 'buffer': t['buffer']})
upsize_checks = []
for name, before, after in assigns['upsizes']:
    assert cells[name][0] == before
    assert directions[before] == directions[after]
    for pn, direction in directions[before].items():
        if direction == 'output':
            fun = [re.search(r'function\s*:\s*"([^"]+)"', pinlib[c][pn])[1]
                   for c in (before, after)]
            assert fun[0] == fun[1]
    upsize_checks.append({'instance': name, 'before': before, 'after': after,
                          'pin_directions_and_output_function_identical': True})

native_log = Path('/dev/shm/nssoc-rx-prefetch-v2-repair12-detailed-rc-01/native.log').read_text()
critical = native_log.split('EXTRACTED_NOMINAL_RC_slow_max\n')[1].split('EXTRACTED_NOMINAL_RC_slow_min\n')[0]
for t in assigns['targets']:
    assert re.search(r'\s' + re.escape(t['name'] + '/' + t['output_pin']) + r'\s', critical), t
for name, _, _ in assigns['upsizes']:
    assert re.search(r'\s' + re.escape(name) + r'/(X|Y)\s', critical), name
assert '-0.521801   slack (VIOLATED)' in critical
assert not Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-13').exists()
result = {'status': 'PASS_INDEPENDENT_RX13_SOURCE_REVIEW', 'findings': [],
          'candidate': pin(bridge['after']['path']), 'derivation': pin(S/'derivation.json'),
          'source_freeze': pin(S/'source-freeze.json'), 'method': pin(__file__),
          'full_forward_inverse': True, 'identical_functions': sorted(funcs[0]),
          'all_baseline_pins_match': True, 'parsed_native_cell_count': len(cells),
          'liberty': {'path': libpath, **pin(libpath)}, 'isolations': observed,
          'upsizes': upsize_checks, 'all_targets_on_actual_slow_paths': True,
          'limits': {'cpu': 8, 'address_space_bytes': 2684354560,
                     'entry_free_bytes': 1073741824, 'shared_floor_bytes': 553648128,
                     'healthy_elapsed_timeout': None},
          'scope': 'Source-only. Fresh unchanged-resource native candidate is authorized; new equivalence, port replay, DRT and RC are still mandatory. No timing gain or physical acceptance.'}
(S/'source-only-peer-root.json').write_text(json.dumps(result, indent=2)+'\n')
print(result['status'], len(observed), 'isolations', len(upsize_checks), 'upsizes')
