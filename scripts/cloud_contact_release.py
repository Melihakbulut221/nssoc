# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Release only the eight fixed nets proven to touch the prior ECO routes."""
import copy,hashlib,json,os
from pathlib import Path
REVIEW_SHA='5c6dfcc0efeb3fa6f5a0aaeaf2e8e04fd1c9ed9eb3386f7a5499d3723ab2296a'
def diagnosed_nets():
    path=Path(__file__).resolve().parents[1]/'docs/evidence/cloud-protected-contact-diagnosis-20261016.json'
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==REVIEW_SHA
    r=json.loads(raw);assert r['status']=='COMPLETE_SOURCE_BOUND_CONTACT_DIAGNOSIS_NOT_REPAIR' and r['source_unchanged']
    assert r['source']['run']==38834266592 and r['source']['summary_sha256']=='7fcdd4a26f94e2089b4249dc7ab3226827ddab395e0128306aa91706815f51f9'
    assert len(r['pairs'])==r['contact_shape_pairs']==25 and r['contact_net_pairs']==8
    names=set()
    for row in r['pairs']:
        assert {row[s]['route_selection'] for s in ('a','b')}=={'protected','changed_or_new'}
        assert all(row[s]['kind'] in ('wire','via') for s in ('a','b'))
        names.update(row[s]['net'] for s in ('a','b') if row[s]['route_selection']=='protected')
    assert len(names)==8
    return sorted(names)
def configured_nets():
    enabled=os.environ.get('NSSOC_RELEASE_CONTACT_NETS','0');assert enabled in ('0','1')
    return diagnosed_nets() if enabled=='1' else []
def validate_route_proof(proof,candidate):
    assert proof['status']=='PASS_UNCHANGED_NATIVE_FIXED_WIRES_AFTER_DETAILED_ROUTE'
    released=proof.get('released_contact_nets',[])
    assert released==candidate.get('released_contact_nets',[])
    if released:
        assert released==diagnosed_nets() and candidate['contact_diagnosis_sha256']==REVIEW_SHA
        assert proof['contact_diagnosis_sha256']==REVIEW_SHA
    assert proof['protected_wired_nets']==113506-len(released)
    assert proof['selected_routed_nets']==100+len(released)
    return True
def controls():
    original=dict(status='PASS_UNCHANGED_NATIVE_FIXED_WIRES_AFTER_DETAILED_ROUTE',protected_wired_nets=113506,selected_routed_nets=100)
    assert validate_route_proof(original,{})
    names=diagnosed_nets();candidate=dict(released_contact_nets=names,contact_diagnosis_sha256=REVIEW_SHA)
    good=dict(original,protected_wired_nets=113498,selected_routed_nets=108,**candidate)
    assert validate_route_proof(good,candidate)
    for key,value in [('released_contact_nets',names[:-1]),('protected_wired_nets',113499),('selected_routed_nets',107),('contact_diagnosis_sha256','0'*64)]:
        bad=copy.deepcopy(good);bad[key]=value
        try:validate_route_proof(bad,candidate)
        except AssertionError:pass
        else:raise AssertionError('Altered contact release proof accepted: '+key)
    try:validate_route_proof(original,candidate)
    except AssertionError:pass
    else:raise AssertionError('Hidden released nets accepted')
    return dict(original_contract_preserved=True,exact_eight_contact_nets=names,negative_controls=5)
if __name__=='__main__':print(json.dumps(controls()))
