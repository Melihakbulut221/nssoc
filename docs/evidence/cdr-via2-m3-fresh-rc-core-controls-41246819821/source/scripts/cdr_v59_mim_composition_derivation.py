#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Derive the frozen compositor without rewriting digits introduced by data."""
import ast,hashlib,re
SOURCE_SHA='c87d213c8676f58d989fc85c91b0408d5c1581cd69f14f96d96ed2e986d299a8'
MODEL='nssoc_cdr_pd500_resistor_mim_wire_v59'
def derive(source,nr,nc):
    assert hashlib.sha256(source.encode()).hexdigest()==SOURCE_SHA
    assert type(nr)is int and type(nc)is int and min(nr,nc)>0
    changes={'nssoc_cdr_pd394_wire_v1':MODEL,'8933':str(nr),'7649':str(nc),'16582':str(nr+nc),
      '394':'500','1134':'1446','776':'978','751':'953','383':'493','==111':'==113'}
    pattern=re.compile('|'.join(re.escape(x)for x in sorted(changes,key=len,reverse=True)))
    pieces=[];records=[];cursor=0;length=0;counts={k:0 for k in changes}
    for match in pattern.finditer(source):
        prefix=source[cursor:match.start()];pieces.append(prefix);length+=len(prefix)
        before=match.group();after=changes[before];counts[before]+=1
        records.append(dict(before=before,after=after,generated_start=length,generated_end=length+len(after)))
        pieces.append(after);length+=len(after);cursor=match.end()
    pieces.append(source[cursor:]);text=''.join(pieces)
    assert all(counts.values()),counts
    restored=text
    for r in reversed(records):
        a,b=r['generated_start'],r['generated_end'];assert restored[a:b]==r['after']
        restored=restored[:a]+r['before']+restored[b:]
    assert restored==source
    ast.parse(text)
    required=[
      "MODEL='"+MODEL+"'",
      "dict(R="+str(nr)+",C="+str(nc)+")",
      "counts=dict(devices=500,R="+str(nr)+",C="+str(nc)+")",
      "geometry['native_device_count']==500 and geometry['native_terminal_count']==1446 and geometry['wire_component_count']==113",
      "anchors['logical_anchor_count']==anchors['physical_anchor_count']==978",
      "ACTUAL_TERMINAL_METAL_POINT_REFERENCE=953,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=493",
      "PASS_PD500_ALL"+str(nr+nc)+"_WIRE_ELEMENTS",
    ]
    assert all(text.count(value)==1 for value in required),required
    return text,dict(original_sha256=SOURCE_SHA,adapted_sha256=hashlib.sha256(text.encode()).hexdigest(),
      non_cascading_simultaneous_source_edits=True,reverse_reconstruction_exact=True,records=records,counts=counts)
def controls(source):
    positive=[]
    for nr,nc in [(394,751),(17649,8933),(8933,16582),(37649,111394)]:
        _,proof=derive(source,nr,nc);positive.append(dict(R=nr,C=nc,sha256=proof['adapted_sha256']))
    rejected=[]
    for name,args in [('changed_frozen_source',(source+'\n',1,1)),('zero_R',(source,0,1)),
      ('negative_C',(source,1,-1)),('boolean_R',(source,True,1))]:
        try:derive(*args)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Accepted '+name)
    assert len(positive)==len(rejected)==4
    return dict(status='PASS_NONCASCADING_MEASURED_COUNT_DERIVATION',positive_collision_cases=positive,rejected=rejected)
