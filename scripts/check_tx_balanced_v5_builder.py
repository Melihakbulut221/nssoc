#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove the v5-specific builder changes only the exact model allowlist."""
import ast, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE_SHA='bb7f5c5ef736dd54c5ed560424d97d248894f4aa6fa6119f1e95c5f5c3df4b52'
ADAPTED_SHA='f3e13d4270b754b7420de2b70021bbbb69a79a373999fc8b2fe6a11ee92352e3'
MODELS={'compact': '3eaa9cf89be3df3128c96244a990c928f42561fda53fc7c98d9560b97865d75c', 'wire': '9cb8fa3ee5ff492f13fbf786e1b1c8ca602abb16ecfb22ad291f2a87d676369c'}
OLD="            assert sha(assembled_core) in ('163a6dfd92e563b2332632ce38fedac60d2b5358cfcc9e51331dfb540ac67ee1',\n                                           '83e128161062e8ca514177a17480874ae5229e789003264ac40da7185eb42118',\n                                           # Same cells in the native DRC/LVS and RC verified tight422 assembly.\n                                           'b6274c8964ae9c687a61107d5cff24c973680ec322f26e9af6de647ff74dce97',\n                                           '6d5e61e5418b9862c368019781bed8ab4c9f3d9884bbe2faebccbc4e591acb66',\n                                           # Fresh native geometry/RC composition39027347884;64um AVSS only.\n                                           'ce2b1f68486b000d1574ac202acaac2853b6ce4ea9f123f67ddedc6eebf711c2',\n                                           'acde00f937c0bc576d608b51c079b984b8379900834c01d4cd74d7bfff34200f')"
NEW="            # Exact v5 composition39065064557 only; no prior geometry accepted.\n            assert sha(assembled_core) in (\n                '3eaa9cf89be3df3128c96244a990c928f42561fda53fc7c98d9560b97865d75c',\n                '9cb8fa3ee5ff492f13fbf786e1b1c8ca602abb16ecfb22ad291f2a87d676369c')"
def check():
    base=(ROOT/'scripts/run_cloud_tx_mux4.py').read_bytes()
    adapted=(ROOT/'scripts/cloud_tx_balanced_v5_builder.py').read_bytes()
    assert hashlib.sha256(base).hexdigest()==BASE_SHA
    assert hashlib.sha256(adapted).hexdigest()==ADAPTED_SHA
    before=base.decode(); after=adapted.decode()
    assert before.count(OLD)==1 and after.count(NEW)==1
    assert before.replace(OLD,NEW,1)==after, 'Any other change requires separate review'
    receipt=json.loads((ROOT/'docs/evidence/tx-tree32-balanced-v5-composition-pass-20261017.json').read_text())
    assert receipt['source_run']==39065064557
    assert receipt['model_sha256']==MODELS
    allowed=[]
    for node in ast.walk(ast.parse(after)):
        if isinstance(node,ast.Compare) and isinstance(node.left,ast.Call) and isinstance(node.left.func,ast.Name) and node.left.func.id=='sha':
            if len(node.left.args)==1 and isinstance(node.left.args[0],ast.Name) and node.left.args[0].id=='assembled_core':
                assert len(node.ops)==1 and isinstance(node.ops[0],ast.In)
                allowed.append(ast.literal_eval(node.comparators[0]))
    assert allowed==[tuple(MODELS.values())]
    for stale in ('163a6dfd92e563b2332632ce38fedac60d2b5358cfcc9e51331dfb540ac67ee1','acde00f937c0bc576d608b51c079b984b8379900834c01d4cd74d7bfff34200f','0'*64):
        assert stale not in allowed[0]
    return dict(status='PASS_ONLY_EXACT_V5_MODEL_BINDING_CHANGED',base_sha256=BASE_SHA,adapted_sha256=ADAPTED_SHA,models=MODELS,unchanged_solver_and_review=True)
if __name__=='__main__': print(json.dumps(check(),sort_keys=True))
