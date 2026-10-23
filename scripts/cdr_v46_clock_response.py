#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Same measured-clock equations; exact v46 diagnosis filename only.
import json
from cloud_cdr_v43_intrinsic_mutator import np,pair_transitions,summary,sha
def clock_response(t,v,w,devices,out,edges_by_stage,ui):
    diag=json.loads((out/'v44-l39-early-native-diagnosis.json').read_text())
    delta=v('cp')-v('cn');a,b=delta[:-1],delta[1:]
    ref={}
    for direction in ('rising','falling'):
        ids=np.flatnonzero((a<0)&(b>=0)if direction=='rising'else(a>0)&(b<=0))
        ref[direction]=t[ids]-a[ids]*(t[ids+1]-t[ids])/(b[ids]-a[ids])
    stages={}
    for tag,edges in edges_by_stage.items():
        graph=diag['stages'][tag]['latches']['native_graph']
        response=pair_transitions(t,graph,devices,v,w,edges,ui)
        direction='falling'if tag=='b'else'rising';rows=[];offsets=[]
        for i,edge in enumerate(edges,1):
            hits=ref[direction][abs(ref[direction]-edge)<=.45*ui]
            row=dict(bit_index=i,original_edge_s=float(edge),source_crossing_count=len(hits))
            if len(hits)==1:
                row['source_crossing_s']=float(hits[0]);offsets.append(float(hits[0]-edge))
            rows.append(row)
        stages[tag]=dict(selector_pairs=response,source_direction=direction,source_rows=rows,
            source_minus_original_edge_s=summary(offsets)if offsets else None,
            missing_or_ambiguous_source_edges=sum(r['source_crossing_count']!=1 for r in rows))
    report=dict(stages=stages,new_acceptance_gate=False,clocks_or_samples_modified=False,
      scope='Actual loaded cp/cn source-port and selector pair crossings on complete new native capture, original edge windows unchanged. External ideal source is not substituted for measured port.')
    path=out/'selector-clock-response.json';path.write_text(json.dumps(report,indent=2)+'\n')
    return dict(path=path.name,sha256=sha(path),source_offsets={tag:s['source_minus_original_edge_s']for tag,s in stages.items()},missing_or_ambiguous={tag:s['missing_or_ambiguous_source_edges']for tag,s in stages.items()})
