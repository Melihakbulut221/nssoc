"""Independent whole-source/lifecycle review; do not import or run producers."""
from pathlib import Path
import ast
import difflib
import hashlib
import json

R = Path.cwd()
B = Path(__file__).resolve().parent
P = B / 'continuation-policy01.json'


def pin(p):
    p = Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size, sha256=hashlib.file_digest(f, 'sha256').hexdigest())


policy = json.loads(P.read_text())
assert pin(P) == dict(bytes=7500, sha256='bd7898cb8462a3982e934d7a78f0aff76ef3b9370a5fe108aeac3a954444954c')
for name, value in policy['method_pins'].items():
    assert pin(name) == value
for name, value in policy['source_pins'].items():
    assert pin(R / name) == value
ledger = json.loads((B / 'native-source-bridges03.json').read_text())
assert len(ledger['bridges']) == 9
reviews = []
for i, row in enumerate(ledger['bridges']):
    a, b = Path(row['parent']), Path(row['new'])
    assert pin(a) == row['parent_pin'] and pin(b) == row['new_pin']
    before, after = a.read_text(), b.read_text()
    assert ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True))) == row['whole_diff']
    if i < 7:
        assert after.replace('v23', 'v22').replace('V23', 'V22') == before
    reviews.append(dict(parent=str(a), parent_pin=pin(a), new=str(b), new_pin=pin(b), full_delta_checked=True, exact_version_only=i < 7))

def funcs(text):
    return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(text).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}

# Last two bodies were fully read. Mapping's entire native tail, signal handlers,
# resource functions, ABC script and 150-byte input profile remain exact.
old_map = Path(ledger['bridges'][7]['parent']).read_text()
new_map = (B / 'run_balanced_map03.py').read_text()
normalized = new_map.replace('v23', 'v22').replace('V23', 'V22')
assert funcs(normalized) == funcs(old_map)
cut = 'def save():(B/\'result.json\').write_text'
assert normalized[normalized.index(cut):] == old_map[old_map.index(cut):]
assert "script='strash; balance -x; &get -n; &nf; &put\\n'" in new_map
assert 'saved_peer[\'validation\']==pin(CORE)' in new_map
assert "validation['pytest_executions']==47" in new_map
assert "validation['historical_failed_executions']==10" in new_map
assert "len(validation['meaningful_miter_mutants'])==11" in new_map
assert "len(validation['promotion_burst'])==2" in new_map

controller = (B / 'continue_native03.py').read_text()
old_controller = Path(ledger['bridges'][8]['parent']).read_text()
stage_new = next(n for n in ast.parse(controller).body if isinstance(n, ast.FunctionDef) and n.name == 'stage')
stage_old = next(n for n in ast.parse(old_controller).body if isinstance(n, ast.FunctionDef) and n.name == 'stage')
stage_source = ast.get_source_segment(controller, stage_new)
old_stage_source = ast.get_source_segment(old_controller, stage_old)
sanitized = "{k:v for k,v in os.environ.items()if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')}"
assert stage_source.replace(sanitized, 'os.environ') == old_stage_source
assert "owner.check();record['status']='COMPLETE_NATIVE_SCREEN_FINITE_REVIEW_AND_PUBLICATION_REQUIRED'\n owner.check()" in controller
assert "if explicit_stop():record.update(status='CANCELLED_RETAINED'" in controller
assert "controls_review['validation']==pin(core)" in controller
assert "stage('import_graph_proof',[sys.executable,str(B/'prove_balanced_import.py')])" in controller
assert 'prove_balanced_import02.py' not in controller
stages = []
for node in ast.walk(ast.parse(controller)):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'stage':
        label = ast.literal_eval(node.args[0])
        path_node = node.args[1].elts[1].args[0]
        filename = ast.literal_eval(path_node.right)
        stages.append((label, filename))
assert len(stages) == 7 and {name for _, name in stages} == set(policy['actual_stage_paths'])
for label, filename in stages:
    assert pin(B / filename) == policy['actual_stage_paths'][filename]
    assert not (B / (label + '.controller.log')).exists()

life = (B / 'native_lifecycle02.py').read_text()
assert 'if p.returncode is not None:' in life and 'ALREADY_REAPED_NO_SIGNAL' in life
assert life.index('if boot!=self.boot_id or current!=self.birth:') < life.index('os.killpg(')
assert 'REFUSED_BIRTH_OR_GROUP_MISMATCH_NO_SIGNAL' in life
for name in ('run_balanced_map03.py', 'balanced_import02.py', 'balanced_preplacement02.py'):
    text = (B / name).read_text()
    assert 'OwnedNative(' in text and 'free_floor(' in text and 'SIG_BLOCK' in text
    assert 'SIG_SETMASK' in text and 'kill_and_reap()' in text
    assert text.index('OwnedNative(') < text.index('SIG_SETMASK')
    assert '2*1024**3' in text and '528*1024**2' in text
sta = (B / 'balanced_preplacement02.py').read_text()
assert 'create_clock -name development_clock -period 4.0 [get_ports clk_i]' in sta
assert policy['CPU'] == 6 and policy['AS_bytes'] == 2 * 1024**3 and policy['clock_period_ns'] == 4.0
ancestor = policy['native_lifecycle_ancestry']
assert pin(ancestor['peer']) == ancestor['pin']
parent_peer = json.loads(Path(ancestor['peer']).read_text())
assert not parent_peer['findings']

launcher = B / 'detach_native01.py'
launch = launcher.read_text()
assert str(pin(P)) in launch
for token in [".open('x')", 'stdin=subprocess.DEVNULL', 'start_new_session=True', 'close_fds=True', "str(R/'.venv/bin/python')", 'PYTHONEXECUTABLE', "not (B/'continuation-status01.json').exists()"]:
    assert token in launch
for p in policy['fresh_outputs']:
    assert not Path(p).exists() and p in launch
assert not (B / 'continuation-status01.json').exists()
v = Path(policy['controls']['validation']['path'])
c = Path(policy['controls']['independent_peer']['path'])
assert pin(v) == {k: policy['controls']['validation'][k] for k in ('bytes', 'sha256')}
assert pin(c) == {k: policy['controls']['independent_peer'][k] for k in ('bytes', 'sha256')}
assert json.loads(c.read_text())['validation'] == pin(v)

result = dict(status='PASS_SOURCE_ONLY_V23_NATIVE_CONTINUATION', policy=pin(P), findings=[],
    launcher=pin(launcher), method=pin(__file__), full_source_bridges=reviews,
    all_frozen_method_and_product_pins_rehashed=True, stages=stages,
    lifecycle_ancestry=ancestor, map_native_tail_and_functions_exact=True,
    controller_stage_exact_except_three_environment_override_exclusions=True,
    actual_control_merge_bound=True, historical_failures_retained=10,
    unchanged_clock_period_ns=4.0, CPU=6, address_space_bytes=2 * 1024**3,
    entry_floor_bytes=1024**3, native_continuous_and_terminal_floor_bytes=528 * 1024**2,
    healthy_elapsed_watchdog_seconds=None, previous_actual_lifecycle_controls_reused=True,
    reviewed_methods_executed=False, no_new_native_started=True,
    scope='Whole-source independent review, seven version-only inverse bodies, two complete control-gate/controller deltas and exact actual stage path binding. Earlier six actual lifecycle controls retained through byte-exact ownership helper and native tail. Fresh map/boundary/import/graph/4ns STA measurements and saved-result peer remain required; no timing or PHY acceptance.')
out = B / 'native-source-only-peer01.json'
assert not out.exists()
out.write_text(json.dumps(result, indent=2) + '\n')
print(result['status'], pin(out))
