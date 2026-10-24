#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound filter design experiment; existing wire RC is NOT candidate PEX."""
import hashlib,json
from pathlib import Path
from route_cloud_newer_postcts import fetch,sha
PARENT_SHA='91364a351fad4d376e6d168d85af6f63ff4076bfecd5af83192492bc514073fc'
REVIEW_SHA='89899b2b091046c12b3fd24105e074028a4c68e4eed8fd9cc2320aef9b050422'
INSTANCE='X_xpump_xd0001'
OLD='X_xpump_xd0001 xpump.t001_mim_top xpump.t001_mim_btm cap_cmim w=10.0u l=10.0u'
def target(size):
    assert type(size) is int and size in (9,11), 'Only declared9um/11um experiments'
    return OLD.replace('w=10.0u l=10.0u',f'w={size}.0u l={size}.0u')
def validate_delta(source,candidate,size):
    assert hashlib.sha256(source.encode()).hexdigest()==PARENT_SHA, 'Changed source'
    assert source.splitlines().count(OLD)==1
    expected=source.replace(OLD+'\n',target(size)+'\n')
    assert candidate==expected and candidate!=source, 'Unexpected delta outside exact capacitor dimensions'
    assert len(candidate.splitlines())==len(source.splitlines())
    return dict(instance=INSTANCE,original_record=OLD,candidate_record=target(size),size_um=size,
        source_sha256=PARENT_SHA,candidate_sha256=hashlib.sha256(candidate.encode()).hexdigest(),
        changed_intrinsic_records=1,wire_records_changed=0,other_intrinsic_records_changed=0,
        candidate_layout_generated=False,candidate_parasitics_extracted=False,
        wire_rc_scope='Frozen baseline estimates only; regenerate physical capacitor and all affected RC before physical acceptance.')
def prepare(source,size,out):
    fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38847244994-1-pll-loop-source/pll-loop-source-38847244994-1.summary.json',REVIEW_SHA,out/'filter-source-review.json')
    review=json.loads((out/'filter-source-review.json').read_text())
    assert review['status']=='COMPLETE_EXACT_PLL_DEVICE_AND_RESISTOR_COMPONENT_DIAGNOSIS_NOT_REPAIR'
    assert review['parent_source']['parent_sha256']==PARENT_SHA
    inv=review['inventory'];assert inv['device_count']==845 and inv['wire_count']==8648
    cap=[d for d in inv['devices'] if d['instance']==INSTANCE];assert len(cap)==1 and cap[0]['record']==OLD
    assert cap[0]['public_ports_by_terminal']==[['vctrl'],['avss']]
    controls=[]
    for n in (9,11):
        candidate=source.replace(OLD+'\n',target(n)+'\n');validate_delta(source,candidate,n)
        bad=[candidate+'* unapproved delta\n',source,candidate.replace('xpump.t001_mim_top','xpump.wrong',1),candidate.replace(target(n),target(n)+' m=2',1)]
        wire=next(l for l in candidate.splitlines() if l.startswith('R'))
        bad.append(candidate.replace(wire,wire+'0',1))
        for index,broken in enumerate(bad):
            try:validate_delta(source,broken,n)
            except AssertionError:controls.append(dict(size_um=n,case=index,rejected=True))
            else:raise AssertionError('Changed candidate accepted')
    for invalid in (8,10,12,9.0,True):
        try:target(invalid)
        except AssertionError:controls.append(dict(invalid_size=invalid,rejected=True))
        else:raise AssertionError('Undeclared candidate accepted')
    candidate=source.replace(OLD+'\n',target(size)+'\n');receipt=validate_delta(source,candidate,size)
    receipt.update(source_review_sha256=REVIEW_SHA,negative_controls=controls)
    return candidate,receipt
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--size-um',type=int,choices=(9,11),required=True);args=parser.parse_args()
    import cloud_pll_vbic_acquisition as acquisition
    acquisition.main(filter_cap_um=args.size_um)
