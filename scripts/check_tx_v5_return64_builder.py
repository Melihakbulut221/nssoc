#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Only exact new model binding may change; stimuli, solver and review stay frozen."""
import ast,hashlib,json
from pathlib import Path
from check_tx_balanced_v5_builder import check as original_check
ROOT=Path(__file__).resolve().parents[1]
MODELS={'compact': '718b8bbd43addc78705792a540129cac962d76daca74106e7e10ef635ee173d0', 'wire': '8a7dfcc19c91a8d13539e04c149ee5b33ef960de3eabdfe08939741bfda7fbd7'}
OLD_MODELS=['3eaa9cf89be3df3128c96244a990c928f42561fda53fc7c98d9560b97865d75c', '9cb8fa3ee5ff492f13fbf786e1b1c8ca602abb16ecfb22ad291f2a87d676369c']
BASE_SHA='f3e13d4270b754b7420de2b70021bbbb69a79a373999fc8b2fe6a11ee92352e3'
NEW_SHA='274a192286d21b9d709e0dd882deb265770ab8b32853f4c3a456689a908700ff'
ADAPTER_SHA='7d4ec6ae4df3a1e96086ef2117c3c63702ba35ef85e3e35083523a1857dc6201'
def check():
    prior=original_check()
    base=(ROOT/'scripts/cloud_tx_balanced_v5_builder.py').read_text()
    new=(ROOT/'scripts/cloud_tx_v5_return64_builder.py').read_text()
    assert hashlib.sha256(base.encode()).hexdigest()==BASE_SHA
    assert hashlib.sha256(new.encode()).hexdigest()==NEW_SHA
    expected=base
    for a,b in zip(OLD_MODELS,MODELS.values(),strict=True):
        assert expected.count(a)==1;expected=expected.replace(a,b)
    a='Exact v5 composition39065064557 only; no prior geometry accepted.'
    b='Exact v5 return64 composition39087377122 only; no prior geometry accepted.'
    assert expected.count(a)==1;expected=expected.replace(a,b)
    assert expected==new,'Stimulus, solver, model or engineering gate changed'
    pin=json.loads((ROOT/'docs/evidence/tx-v5-return64-composition-pass-20261018.json').read_text())
    assert pin['source_run']==39087377122 and pin['model_sha256']==MODELS
    allowed=[]
    for n in ast.walk(ast.parse(new)):
        if isinstance(n,ast.Compare) and isinstance(n.left,ast.Call) and isinstance(n.left.func,ast.Name) and n.left.func.id=='sha' and len(n.left.args)==1 and isinstance(n.left.args[0],ast.Name) and n.left.args[0].id=='assembled_core':
            assert len(n.ops)==1 and isinstance(n.ops[0],ast.In)
            allowed.append(ast.literal_eval(n.comparators[0]))
    assert allowed==[tuple(MODELS.values())]
    assert not set(OLD_MODELS+['0'*64])&set(allowed[0])
    old=(ROOT/'scripts/cloud_tx_balanced_v5_clock_adapter.py').read_text()
    adapter=(ROOT/'scripts/cloud_tx_v5_return64_clock_adapter.py').read_text()
    assert hashlib.sha256(adapter.encode()).hexdigest()==ADAPTER_SHA
    assert old.count('import cloud_tx_balanced_v5_builder as tree')==1
    assert old.replace('import cloud_tx_balanced_v5_builder as tree','import cloud_tx_v5_return64_builder as tree')==adapter
    return dict(status='PASS_ONLY_EXACT_RETURN64_MODEL_BINDING_CHANGED',original=prior,base_sha256=BASE_SHA,adapted_sha256=NEW_SHA,models=MODELS,unchanged_solver_stimuli_and_review=True,all_44_clock_faults_unchanged=True)
if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
