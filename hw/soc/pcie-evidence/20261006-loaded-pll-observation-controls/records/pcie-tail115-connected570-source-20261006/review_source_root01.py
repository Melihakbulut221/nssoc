"""Independent source graph and bounded tuning-contract review; no native run."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import os
import shutil
import subprocess
import sys

B = Path(__file__).resolve().parent
def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())

freeze = B / 'source-freeze01.json'
assert pin(freeze) == dict(bytes=35763, sha256='961db3c0f582da14ddfa73cd3da648e3ab10b3424e362a7df9dda55c765f400a')
frozen = json.loads(freeze.read_text())
for path, expected in frozen['inputs'].items():
    assert pin(path) == expected, path
assert len(frozen['inputs']) == 150
composition = json.loads((B / 'composition01.json').read_text())
contract = json.loads((B / 'tuning-contract01.json').read_text())
bridges = json.loads((B / 'source-bridges01.json').read_text())
terminal_counts = dict(npn13g2=4, rppd=3, cap_cmim=2, sg13_hv_pmos=4,
                       sg13_hv_nmos=4, sg13_lv_pmos=4, sg13_lv_nmos=4, ptap1=2, ntap1=2)
actual = {}
for label, expected in composition['variants'].items():
    definitions = {}
    paths = [*(B / 'includes01').iterdir(), B / f'loop-{label}01.spice']
    current = None
    for path in paths:
        for raw in path.read_text().lower().splitlines():
            if not raw.strip() or raw.lstrip().startswith('*'):
                continue
            words = raw.split()
            if words[0] == '.subckt':
                assert current is None and words[1] not in definitions
                current = words[1]
                definitions[current] = (words[2:], [])
            elif words[0] == '.ends':
                assert current and words[1:] in ([], [current])
                current = None
            else:
                assert current and words[0][0] in 'xrc'
                definitions[current][1].append(words)
        assert current is None
    models = {}
    wires = {}
    def visit(kind, instance, nets, ancestors=()):
        assert kind not in ancestors
        ports, body = definitions[kind]
        assert len(ports) == len(nets) == len(set(ports))
        aliases = dict(zip(ports, nets))
        def node(n):
            return '0' if n == '0' else aliases.get(n, instance + '.' + n)
        seen = set()
        for words in body:
            assert words[0] not in seen
            seen.add(words[0])
            full = instance + '.' + words[0]
            if words[0][0] in 'rc':
                assert len(words) == 4
                wires[full] = dict(path=full, kind=words[0][0], nets=[node(n) for n in words[1:3]], value=words[3])
                continue
            first_param = next((i for i, word in enumerate(words) if '=' in word), len(words))
            model = words[first_param-1]
            connections = [node(n) for n in words[1:first_param-1]]
            if model in definitions:
                assert first_param == len(words)
                visit(model, full, connections, ancestors + (kind,))
            else:
                assert len(connections) == terminal_counts[model]
                params = dict(word.split('=', 1) for word in words[first_param:])
                assert len(params) == len(words[first_param:])
                models[full] = dict(path=full, model=model, nets=connections, params=params)
    visit(*expected['root'])
    assert models == {row['path']: row for row in expected['devices']}
    assert wires == {row['path']: row for row in expected['wire_elements']}
    assert len(models) == 570 and Counter(row['kind'] for row in wires.values()) == {'r': 1271, 'c': 1414}
    assert sum(len(row['nets']) for row in models.values()) == 2097
    assert len(expected['safety_records']) == 570 and len(expected['startup_hbt_paths']) == 64
    assert {row['path']: row['terminals'] for row in expected['safety_records']} == {p: r['nets'] for p, r in models.items()}
    assert len(expected['observation_vectors']) == len(set(expected['observation_vectors'])) == 1132
    for row in models.values():
        assert all(n == '0' or f'v({n})' in expected['observation_vectors'] for n in row['nets'])
    assert not expected['polarity_selected']
    assert not any(line.startswith('VCTRL ') for line in expected['fixture'])
    assert [line for line in expected['fixture'] if line.startswith('CLOAD')] == ['CLOAD_CLKP clkp 0 50f', 'CLOAD_CLKN clkn 0 50f']
    bridge = bridges[label]
    original = [x for x in bridge['original_complete_text'].splitlines() if x and not x.startswith('*')]
    derived = [x for x in bridge['resulting_complete_text'].splitlines() if x and not x.startswith('*')]
    assert original[3:-1] == derived[3:-1] == bridge['unchanged_filter_lines']
    assert (B / f'loop-{label}01.spice').read_text() == bridge['resulting_complete_text']
    assert derived[2].split()[1:3] == (['fb', 'ref'] if label == 'negative' else ['ref', 'fb'])
    actual[label] = dict(devices=len(models), intrinsic_terminals=2097, wire_r=1271, wire_c=1414, vectors=1132)
assert contract['preserved_design']['retuning_permitted'] is False
assert contract['loaded_tuning_fixture']['output_and_maxstep_s'] == 3.125e-13
assert contract['voltage_domain']['grid_v'] == [i / 10 for i in range(26)]
assert contract['voltage_domain']['initial_diagnostic_order_v'] == [.5, .6, .7]
assert contract['connected_next_gate']['external_vctrl_source_forbidden'] is True
assert contract['connected_next_gate']['candidate_unselected_until_tuning_pass'] is True
assert composition['native_deck_and_runner_not_created'] and composition['safety_implementation_pending']
copy = B / 'peer-controls01'
copy.mkdir()
for name in ('compose_source01.py', 'check_source_controls01.py', 'composition01.json', 'tuning-contract01.json', 'loop-negative01.spice', 'loop-positive01.spice'):
    shutil.copy2(B / name, copy / name)
shutil.copytree(B / 'includes01', copy / 'includes01')
env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONEXECUTABLE', 'PYTHONOPTIMIZE', 'LD_PRELOAD')}
with (copy / 'run.log').open('x') as log:
    subprocess.run([sys.executable, str(copy / 'check_source_controls01.py')], check=True, env=env, stdout=log, stderr=subprocess.STDOUT)
replayed = json.loads((copy / 'source-controls01.json').read_text())
assert replayed['outcomes'] == json.loads((B / 'source-controls01.json').read_text())['outcomes']
assert len(replayed['outcomes']) == 12 and all(r['passed'] for r in replayed['outcomes'])
result = dict(status='PASS_SOURCE_ONLY_570_COMPOSITION_AND_TUNING_CONTRACT', freeze=pin(freeze), findings=[],
              source=pin(__file__), pinned_inputs=150, independent_model_and_wire_expansion=actual,
              actual_copied_source_controls=12, controls=pin(copy / 'source-controls01.json'),
              native_authorized=False, polarity_selected=False,
              scope='Complete independent SPICE terminal/parameter/wire expansion and source-filter/detector bridges agree. All12 copied-source controls independently rerun. Safety rows are planned inherited predicates, not measured safety. Tuning clamp is characterization only; force subtraction is a necessary quasistatic condition, not dynamic reachability/stability. Actual clamped570/PFD-idle and13-device pump runner/checker, raw capacity and negative controls require separate review before native dispatch.')
(B / 'source-contract-peer-root01.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(status=result['status'], inputs=150, variants=actual, controls=12)))
