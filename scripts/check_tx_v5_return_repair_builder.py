#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import ast,hashlib,json
from pathlib import Path
from check_tx_v5_columns_builder import check as prior_check
ROOT=Path(__file__).resolve().parents[1]
def check():
    prior=prior_check()
    for d in json.loads((ROOT/'scripts/tx-v5-return-repair-wave-source-delta.json').read_text())['files']:
        raw=(ROOT/d['baseline_path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['baseline_sha256'];s=raw.decode()
        for e in d['edits']:
            assert s.count(e['before'])==e['count'];s=s.replace(e['before'],e['after'])
        actual=(ROOT/d['candidate_path']).read_bytes();assert actual==s.encode() and hashlib.sha256(actual).hexdigest()==d['candidate_sha256']
    pin=json.loads((ROOT/'docs/evidence/tx-v5-return-repair-composition-pass-20261018.json').read_text())
    eq=json.loads((ROOT/'docs/evidence/tx-v5-return-model-equivalence-pass-20261018.json').read_text())
    assert eq['run']==39137222470 and eq['report']['status']=='PASS_NATIVE1674_COMPACT_MODEL_TOPOLOGY_EQUIVALENCE_WITH_THREE_FAULTS'
    assert eq['report']['sources']['candidate']['compact_sha256']==pin['model_sha256']['compact']
    assert eq['report']['sources']['candidate']['summary_sha256']==pin['summary_sha256']
    assert len(eq['report']['controls'])==3 and all(v['rejected']for v in eq['report']['controls'])
    assert pin['source_run']==39136227539
    new=(ROOT/'scripts/cloud_tx_v5_return_repair_builder.py').read_text();allowed=[]
    for n in ast.walk(ast.parse(new)):
        if isinstance(n,ast.Compare) and isinstance(n.left,ast.Call) and isinstance(n.left.func,ast.Name) and n.left.func.id=='sha' and len(n.left.args)==1 and isinstance(n.left.args[0],ast.Name) and n.left.args[0].id=='assembled_core':
            assert len(n.ops)==1 and isinstance(n.ops[0],ast.In)
            allowed.append(ast.literal_eval(n.comparators[0]))
    assert allowed==[tuple(pin['model_sha256'].values())]
    old=json.loads((ROOT/'docs/evidence/tx-v5-columns-composition-pass-20261018.json').read_text())
    assert not set(old['model_sha256'].values())&set(allowed[0])
    return dict(status='PASS_ONLY_REPAIRED_NATIVE_MODEL_BINDINGS_CHANGED',prior=prior,models=pin['model_sha256'],compact_topology_equivalence_run=eq['run'],unchanged_stimulus_solver_review_and_clock_faults=True)
if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
