#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Only the verified new geometry model binding changes; original acceptance stays exact."""
import ast,hashlib,json
from pathlib import Path
from check_tx_v5_return64_builder import check as original_check
ROOT=Path(__file__).resolve().parents[1]
MODELS={'compact': 'a85673ca1ba0f03b053bd4f262ff53f08190752ae50ce3f969260378f6ed299a', 'wire': '6867d82254023dde8210ca05c614585db9d1f3bbe22eae401451d935be78340b'}
OLD_MODELS=['718b8bbd43addc78705792a540129cac962d76daca74106e7e10ef635ee173d0', '8a7dfcc19c91a8d13539e04c149ee5b33ef960de3eabdfe08939741bfda7fbd7']
BASE_SHA='274a192286d21b9d709e0dd882deb265770ab8b32853f4c3a456689a908700ff'
NEW_SHA='315fb2621627df29c09bac26350ec92884a55363a8b69f1856dbc3f988c9aef3'
ADAPTER_SHA='dd7c21950bdb37a93f0cd52635f9a57e58cc2a8a8e0d1a751d5b4b0dc133bbc4'

def check():
    prior=original_check()
    base=(ROOT/'scripts/cloud_tx_v5_return64_builder.py').read_text()
    new=(ROOT/'scripts/cloud_tx_v5_columns_builder.py').read_text()
    assert hashlib.sha256(base.encode()).hexdigest()==BASE_SHA
    assert hashlib.sha256(new.encode()).hexdigest()==NEW_SHA
    expected=base
    for a,b in zip(OLD_MODELS,MODELS.values(),strict=True):
        assert expected.count(a)==1;expected=expected.replace(a,b)
    a='Exact v5 return64 composition39087377122 only; no prior geometry accepted.'
    b='Exact v5 columns composition39111549216 only; no prior geometry accepted.'
    assert expected.count(a)==1;expected=expected.replace(a,b)
    assert expected==new,'Stimulus, solver, model or engineering gate changed'
    pin=json.loads((ROOT/'docs/evidence/tx-v5-columns-composition-pass-20261018.json').read_text())
    assert pin['source_run']==39111549216 and pin['model_sha256']==MODELS
    allowed=[]
    for n in ast.walk(ast.parse(new)):
        if isinstance(n,ast.Compare) and isinstance(n.left,ast.Call) and isinstance(n.left.func,ast.Name) and n.left.func.id=='sha' and len(n.left.args)==1 and isinstance(n.left.args[0],ast.Name) and n.left.args[0].id=='assembled_core':
            assert len(n.ops)==1 and isinstance(n.ops[0],ast.In)
            allowed.append(ast.literal_eval(n.comparators[0]))
    assert allowed==[tuple(MODELS.values())]
    assert not set(OLD_MODELS+['0'*64])&set(allowed[0])
    old=(ROOT/'scripts/cloud_tx_v5_return64_clock_adapter.py').read_text()
    adapter=(ROOT/'scripts/cloud_tx_v5_columns_clock_adapter.py').read_text()
    assert hashlib.sha256(adapter.encode()).hexdigest()==ADAPTER_SHA
    assert old.count('import cloud_tx_v5_return64_builder as tree')==1
    assert old.replace('import cloud_tx_v5_return64_builder as tree','import cloud_tx_v5_columns_builder as tree')==adapter
    delta=json.loads((ROOT/'scripts/tx-v5-columns-wave-source-delta.json').read_text())
    before=(ROOT/delta['baseline']).read_text();after=(ROOT/delta['candidate']).read_text()
    assert hashlib.sha256(before.encode()).hexdigest()==delta['baseline_sha256']
    assert hashlib.sha256(after.encode()).hexdigest()==delta['candidate_sha256']
    for row in delta['changes']:
        assert before.count(row['before'])==row['count']
        before=before.replace(row['before'],row['after'])
    assert before==after,'Loaded controller changed outside exact new physical bindings'
    return dict(status='PASS_ONLY_EXACT_COLUMNS_MODEL_BINDING_CHANGED',original=prior,base_sha256=BASE_SHA,adapted_sha256=NEW_SHA,models=MODELS,unchanged_solver_stimuli_and_review=True,all_44_clock_faults_unchanged=True,loaded_controller_exact_delta=True)
if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
