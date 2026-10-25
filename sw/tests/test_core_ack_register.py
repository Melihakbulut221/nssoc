# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real candidate protocol simulation and rejection of unsupported adoption."""
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import prepare_core_ack_register as ack  # noqa: E402


def prepared(tmp_path):
    path=tmp_path/'prepared'
    ack.prepare(ROOT/'hw/soc/rtl/soc_req_pipe.v',path)
    return path


def test_exact_source_transform_is_reversible_and_does_not_edit_default(tmp_path):
    original=(ROOT/'hw/soc/rtl/soc_req_pipe.v').read_bytes()
    path=prepared(tmp_path); candidate=(path/'candidate.v').read_text()
    for before,after in reversed(ack.EDITS):candidate=candidate.replace(after,before,1)
    assert candidate.encode()==original
    assert (ROOT/'hw/soc/rtl/soc_req_pipe.v').read_bytes()==original
    receipt=ack.verify_prepared(path)
    assert receipt['upstream_ack_latency_added_cycles']==1
    assert receipt['downstream_request_latency_added_cycles']==1
    assert not receipt['actual_core_protocol_proved'] and not receipt['sequential_equivalence_proved']


def test_wrong_c10_input_rejected_before_output_creation(tmp_path):
    source=tmp_path/'wrong.v';source.write_bytes((ROOT/'hw/soc/rtl/soc_req_pipe.v').read_bytes()+b'\n')
    with pytest.raises(ValueError,match='exact C10'):ack.prepare(source,tmp_path/'output')
    assert not (tmp_path/'output').exists()


@pytest.mark.parametrize('fault',['candidate','source_pin','source_label','method','required_contract','core_proved','sequential_proved','adopted','gate','latency','edits','stability','reset','status'])
def test_changed_candidate_or_fabricated_core_acceptance_rejected(tmp_path,fault):
    path=prepared(tmp_path);receipt=json.loads((path/'preparation.json').read_text())
    if fault=='candidate':(path/'candidate.v').write_text((path/'candidate.v').read_text()+'\n')
    elif fault=='source_pin':receipt['sources']['candidate.v']='0'*64
    elif fault=='source_label':receipt['source_sha256']='0'*64
    elif fault=='method':receipt['method_sha256']='0'*64
    elif fault=='required_contract':receipt['required_actual_core_proofs']=[]
    elif fault=='core_proved':receipt['actual_core_protocol_proved']=True
    elif fault=='sequential_proved':receipt['sequential_equivalence_proved']=True
    elif fault=='adopted':receipt['candidate_adopted']=True
    elif fault=='latency':receipt['upstream_ack_latency_added_cycles']=0
    elif fault=='edits':receipt['edits']=[]
    elif fault=='stability':receipt['upstream_stability_is_required']=False
    elif fault=='reset':receipt['common_reset_is_only_legal_abort']=False
    elif fault=='status':receipt['status']='PASS_PRODUCTION'
    else:receipt['whole_soc_candidate_gate']='PASS'
    (path/'preparation.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError):ack.verify_prepared(path)


def test_real_rtl_contract_and_environment_negative_controls(tmp_path):
    result=ack.contract_tests(prepared(tmp_path),tmp_path/'native')
    assert result['status']=='PASS_EXPLICIT_MODULE_CONTRACT_CONTROLS_ONLY'
    rows={r['name']:r for r in result['cases']}
    assert len(rows)==7 and rows['held_and_stalled']['returncode']==0
    assert all(r['returncode']!=0 for name,r in rows.items() if name!='held_and_stalled')
    assert 'accepted=6 delivered=5 discarded=1' in (tmp_path/'native/held_and_stalled.log').read_text()
    assert not result['actual_core_protocol_proved'] and not result['sequential_equivalence_proved']
    assert result['required_actual_core_proofs']==ack.REQUIRED_CORE_PROOFS
