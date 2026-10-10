# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Replay closed native arms with only a Path adapter; preserve failed controller."""
from pathlib import Path
import importlib.util
import json
import sys

B = Path(__file__).absolute().parent
R = B.parents[3]
sys.path.insert(0, str(R / 'scripts'))
import run_cloud_alu_physical as base


def load(path):
    return json.loads(Path(path).read_text())


def check():
    state = load(B / 'pair02-status.json')
    assert state['status'] == 'FAILED_PRESERVED'
    assert state['error'] == 'AttributeError("\'str\' object has no attribute \'stat\'")'
    identity = state['controller']
    proc = Path('/proc') / str(identity['pid']) / 'stat'
    if proc.exists():
        raw = proc.read_text(); fields = raw[raw.rfind(')') + 2:].split()
        assert fields[19] != str(identity['start_ticks']) or fields[0] == 'Z'
    freeze = load(B / 'source-freeze06.json')
    source = B / 'pair02-original/methods/scripts/run_npu_eco_physical.py'
    old = source.read_text()
    assert base.pin(source) == freeze['sources'][str(R / 'scripts/run_npu_eco_physical.py')]
    broken = "pin(entry['path'])"
    fixed = "pin(Path(entry['path']))"
    assert old.count(broken) == 1 and fixed not in old
    assert old.replace(broken, fixed) == (R / 'scripts/run_npu_eco_physical.py').read_text()
    peer = load(B / 'saved-template-peer-rx01.json')
    assert peer['status'] == 'PASS_INDEPENDENT_SAVED_NPU_TEMPLATE_CONTROL06' and peer['findings'] == []
    assert peer['control'] == state['native_template_control'] == base.pin(B / 'template-control06/control.json')
    assert peer['freeze'] == base.pin(B / 'source-freeze06.json')
    assert peer['source_peer'] == base.pin(B / 'source-only-peer-pll06.json')
    for variant in ('original', 'factored'):
        result = B / ('pair02-' + variant) / 'result.json'
        assert state['completed'][variant]['result'] == base.pin(result)
        assert state['completed'][variant]['status'] == 'FRESH_NPU_PHYSICAL_COMPLETE_ESTIMATE_ONLY'
    spec = importlib.util.spec_from_file_location('npu_pair02_captured_producer', source)
    captured = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(captured)
    assert captured.ROOT == B / 'pair02-original/methods'
    original_pin = captured.pin
    captured.pin = lambda path: original_pin(Path(path))
    # All comparison body, readiness, raw endpoint and geometry checks remain
    # the captured producer's exact code. Both arms' output manifests include
    # their full method copies, so neither is validated against mutable source.
    comparison = captured.compare(B / 'pair02-original', B / 'pair02-factored')
    return dict(status='RECOVERED_SAVED_COMPARISON_NO_NATIVE_RERUN',
                original_failed_controller=base.pin(B / 'pair02-status.json'),
                captured_producer=base.pin(source), fixed_product=base.pin(R / 'scripts/run_npu_eco_physical.py'),
                method=base.pin(Path(__file__)), native_arms=state['completed'],
                source_peer=base.pin(B / 'source-only-peer-pll06.json'),
                template_peer=base.pin(B / 'saved-template-peer-rx01.json'),
                comparison=comparison, native_reexecuted=False,
                scope='Both original native arms completed and rechecked their inputs. Preserve the failed final Python comparison, normalize only its serialized Path argument, then independently reparse complete saved captures under the exact archived producer. Global-route estimates only; no adoption.')


if __name__ == '__main__':
    result = check()
    out = B / 'pair02-comparison-recovered01.json'
    assert not out.exists()
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
