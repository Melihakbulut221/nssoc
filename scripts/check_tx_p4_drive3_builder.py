#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require unchanged original waveform gates and actual new topology comparison."""
import ast,hashlib,json
from pathlib import Path
from check_tx_v5_timing_priority_builder import check as prior_check
ROOT=Path(__file__).resolve().parents[1]
def check():
    prior=prior_check()
    from check_tx_p4_drive3_wave_sources import check as sources
    from check_tx_p4_drive3_composition_sources import check as composition
    sources();composition()
    pin=json.loads((ROOT/'docs/evidence/tx-p4-drive3-composition-pass-20261020.json').read_text())
    old=json.loads((ROOT/'docs/evidence/tx-fast-wire20-composition-pass-20261019.json').read_text())
    path=ROOT/'hw/soc/out/cloud-tx-p4-drive3-model-compare/result.json'
    eq=json.loads(path.read_text())
    assert eq['status']=='PASS_NATIVE1674_FOUR_P4_MASTER_SUBSTITUTION_WITH_THREE_FAULTS'
    assert eq['sources']['candidate']['source_run']==pin['source_run']==39450330853
    assert eq['sources']['candidate']['source_head']==pin['source_head']=='b47b573b1f5d609409215e53a8c9c41b75b61f70'
    for label,expected in (('candidate',pin),('baseline',old)):
        for field,source_field in (('compact_sha256','compact'),):
            assert eq['sources'][label][field]==expected['model_sha256'][source_field]
        assert eq['sources'][label]['summary_sha256']==expected['summary_sha256']
        assert eq['sources'][label]['archive_sha256']==expected['sha256']
    assert len(eq['controls'])==3 and all(c['rejected']for c in eq['controls'])
    assert {c['fault']for c in eq['controls']}=={'missing_device','changed_parameter','wrong_terminal'}
    assert eq['physical_identity_swap_rejected']and eq['old_low_drive_parameter_rejected']
    assert eq['reference_emitters']==863 and {x['tag']for x in eq['master_substitutions']}=={'p4_0','p4_1','p4_2','p4_3'}
    assert eq['comparison']['devices']==1674 and eq['comparison']['ports']==162
    assert eq['comparison']['all_public_names_fixed'] and eq['comparison']['all_device_parameters_exact']
    allowed=[]
    for n in ast.walk(ast.parse((ROOT/'scripts/cloud_tx_p4_drive3_builder.py').read_text())):
        if isinstance(n,ast.Compare)and isinstance(n.left,ast.Call)and isinstance(n.left.func,ast.Name)and n.left.func.id=='sha'and len(n.left.args)==1 and isinstance(n.left.args[0],ast.Name)and n.left.args[0].id=='assembled_core':
            assert len(n.ops)==1 and isinstance(n.ops[0],ast.In);allowed.append(ast.literal_eval(n.comparators[0]))
    assert allowed==[tuple(pin['model_sha256'].values())]
    assert not set(old['model_sha256'].values())&set(allowed[0])
    return dict(status='PASS_P4_DRIVE3_NATIVE_MODELS_WITH_ORIGINAL_STIMULUS_SOLVER_DEVICE_AND_CLOCK_GATES',
        prior=prior,models=pin['model_sha256'],native_equivalence=eq,
        native_equivalence_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        unchanged_stimulus_solver_review_and_clock_faults=True)
if __name__=='__main__':print(json.dumps(check(),sort_keys=True))
