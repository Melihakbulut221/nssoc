#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Intrinsic input/retime resistor sizing diagnosis on FROZEN v10 wire RC.

Changing intrinsic resistor width invalidates physical model correspondence.
This helper never produces a physically accepted model or qualified PEX.
"""
import copy,hashlib,json,re
from collections import Counter
MODEL_SHA="362c5e3430b4fa7410ac6ae658dcbd3cfc8df3fcc399b5db665439d40fb307ee"
CONTRACT_SHA="0a33699790c18dc53743cd58dc38544328e63b10b67db4f2665b1f29b82d5fed"
TARGET_IDS=[163, 164, 165, 166, 167, 168, 170, 171, 179, 180, 182, 183, 191, 192, 194, 195, 203, 204, 206, 207, 216, 217, 219, 221]
def sha(text):return hashlib.sha256(text.encode()).hexdigest()
def check_contract(contract):
    assert sha(json.dumps(contract,sort_keys=True,separators=(',',':')))==CONTRACT_SHA
    targets=[d for d in contract['device_records']if d['model']=='rppd'and d['parameters']['w']=='4u']
    assert [d['native_id']for d in targets]==TARGET_IDS
    assert Counter(d['parameters']['l']for d in targets)=={'3.6u':8,'2.4u':8,'5.4u':4,'12.6u':4}
    assert all(d['parameters']==dict(w='4u',l=d['parameters']['l'],ps='0u',b='0',m='1',sw_et='1')for d in targets)
    return targets
def resize(text,contract,width):
    assert width in (8,16),width
    assert sha(text)==MODEL_SHA
    targets=check_contract(contract)
    names={d['instance'].lower():d for d in targets}
    changed=[];lines=[]
    for line in text.splitlines(keepends=True):
        fields=line.split()
        name=fields[0].lower()if fields else ''
        if name in names:
            assert fields[4]=='rppd',fields
            assert dict(f.split('=')for f in fields[5:])==names[name]['parameters']
            replaced,n=re.subn(r'(?<!\S)w=4u(?=\s|$)','w='+str(width)+'u',line)
            assert n==1
            lines.append(replaced);changed.append(names[name]['native_id'])
        else:lines.append(line)
    assert sorted(changed)==sorted(TARGET_IDS)
    altered=''.join(lines);modified=copy.deepcopy(contract)
    for d in modified['device_records']:
        if d['native_id']in TARGET_IDS:d['parameters']['w']=str(width)+'u'
    def wire(t):return ''.join(line for line in t.splitlines(keepends=True)if line.startswith(('R','C')))
    assert wire(text)==wire(altered)
    assert sum(a!=b for a,b in zip(text.splitlines(),altered.splitlines()))==24
    return altered,modified,dict(status='DIAGNOSTIC_INTRINSIC_WIDTH_ONLY_FROZEN_WIRE_RC',
        physically_accepted=False,qualified_pex=False,geometry_matches_model=False,
        original_model_sha256=MODEL_SHA,modified_model_sha256=sha(altered),
        unchanged_wire_tokens_sha256=sha(wire(text)),resistor_width_um=width,
        changed_ids=changed,changed_count=24,original_width_um=4,
        scope='16 sampler input dividers and8 retime divider resistors; ONLY intrinsic width. Existing RC frozen and stale for changed geometry. Requires fresh PCell/layout/DRC/LVS/RC/full waveform before physical acceptance.')
def controls(text,contract):
    for w in (8,16):
        changed,c,a=resize(text,contract,w)
        assert a['changed_count']==24 and not a['geometry_matches_model']
    failures={}
    def rejected(name,fn):
        try:fn()
        except AssertionError:failures[name]=True
        else:raise AssertionError('Fault was accepted: '+name)
    rejected('unlisted_width4',lambda:resize(text,contract,4))
    rejected('unlisted_width32',lambda:resize(text,contract,32))
    rejected('changed_model_bytes',lambda:resize(text+'\n',contract,8))
    for label,field,value in [('changed_native_id','native_id',-1),('changed_native_model','model','ptap1')]:
        damaged=copy.deepcopy(contract)
        d=next(d for d in damaged['device_records']if d['native_id']==TARGET_IDS[0])
        d[field]=value
        rejected(label,lambda:resize(text,damaged,8))
    damaged=copy.deepcopy(contract)
    d=next(d for d in damaged['device_records']if d['native_id']==TARGET_IDS[0]);d['parameters']['w']='8u'
    rejected('changed_baseline_width',lambda:resize(text,damaged,8))
    assert len(failures)==6
    return failures
