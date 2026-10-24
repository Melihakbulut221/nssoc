#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual raw-driver conductor resistance and capacitance, not fitted waveform RC."""
import json,os
from pathlib import Path
import numpy as np
import cloud_tx_input_driver_compact as physical
from cloud_tx_driver_compact_loaded import SOURCE
from build_pcie_local_vco_hybrid_v6 import statements,number
from route_cloud_newer_postcts import sha
ROOT=physical.ROOT;OUT=ROOT/'cloud-tx-driver-compact-wire-metrics'
def network_metrics(rows):
    rr=[r for r in rows if r[0].startswith('R')];cc=[r for r in rows if r[0].startswith('C')]
    assert rr and all(len(r)==4 and float(number(r[3]))>0 and r[1]!=r[2]for r in rr+cc)
    nodes={n for r in rr for n in r[1:3]};adj={n:set()for n in nodes}
    for r in rr:adj[r[1]].add(r[2]);adj[r[2]].add(r[1])
    unseen=set(nodes);components=[]
    while unseen:
        root=min(unseen);found={root};pending=[root]
        while pending:
            node=pending.pop()
            for neighbor in adj[node]-found:found.add(neighbor);pending.append(neighbor)
        unseen-=found;components.append(sorted(found))
    output=[]
    for component in components:
        public=[n for n in component if n in physical.PORTS];assert len(public)<=1
        reference=public[0]if public else component[0];others=[n for n in component if n!=reference];indices={n:i for i,n in enumerate(others)}
        g=np.zeros((len(others),len(others)));subset=[r for r in rr if r[1]in component]
        for r in subset:
            a,b=r[1:3];assert b in component;conductance=1/float(number(r[3]))
            for n in (a,b):
                if n!=reference:g[indices[n],indices[n]]+=conductance
            if a!=reference and b!=reference:g[indices[a],indices[b]]-=conductance;g[indices[b],indices[a]]-=conductance
        z=np.linalg.solve(g,np.eye(len(others)));residual=float(np.max(np.abs(g@z-np.eye(len(others)))))
        assert residual<1e-8 and np.max(np.abs(z-z.T))<1e-8
        diag=np.diag(z);effective=diag[:,None]+diag[None,:]-2*z;assert effective.min()>-1e-8
        i,j=np.unravel_index(np.argmax(effective),effective.shape)
        pair=(others[i],others[j]);value=float(effective[i,j])
        if diag.max()>value:k=int(np.argmax(diag));pair=(reference,others[k]);value=float(diag[k])
        byref={reference:0.}|{n:float(diag[i])for n,i in indices.items()}
        coupling=[r for r in cc if (r[1]in component)!=(r[2]in component)]
        internal=[r for r in cc if r[1]in component and r[2]in component]
        output.append(dict(nodes=component,reference=reference,public=public,resistors=len(subset),maximum_pair=dict(nodes=pair,ohms=value),reference_resistance_ohms=byref,
            crossing_capacitance_f=sum(float(number(r[3]))for r in coupling),internal_capacitance_f=sum(float(number(r[3]))for r in internal),
            conductance_condition_number=float(np.linalg.cond(g)),linear_solve_residual=residual))
    return output

def controls():
    data=network_metrics([['R1','a','b','2'],['R2','b','c','3']]);assert len(data)==1 and abs(data[0]['maximum_pair']['ohms']-5)<1e-12
    data=network_metrics([['R1','a','b','2'],['R2','a','b','2']]);assert abs(data[0]['maximum_pair']['ohms']-1)<1e-12
    for bad in ([['R1','a','a','1']],[['R1','a','b','0']]):
        try:network_metrics(bad)
        except AssertionError:pass
        else:raise AssertionError('Degenerate R accepted')
    return dict(series_and_parallel_exact=True,self_edge_and_zero_R_rejected=True)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,qualified_pex=False,controls=controls(),scope='Static actual extracted wire network only; no driver current, fitted time constant or physical acceptance. Intrinsic devices and finite contacts are never converted to wire aliases.')
    try:
        physical.OUT=OUT;source,prior=physical.restore(SOURCE);model=source/'driver100-wire.spice'
        assert sha(model)==prior['model_sha256']=='592a470367c40747b5625f200cbde91662a40268cae5568d985dea9010ae3c10'
        rows=statements(model.read_text());assert sum(r[0].startswith('R')for r in rows)==260 and sum(r[0].startswith('C')for r in rows)==300
        native=json.loads((source/'inputs/tx-driver-compact-intrinsic/cloud-tx-driver-compact-intrinsic/inputs/tx-driver-compact-junctions/cloud-tx-driver-compact-junctions/native.json').read_text())['native']['raw_flat_lvs']['devices']
        original={r['id']:r for r in native};bindings={}
        for r in prior['bindings']:
            for b in r['bindings']:
                logical=original[r['native_id']]['terminals'][b['terminal']]['logical_net']
                bindings.setdefault(b['node'],[]).append(dict(native_id=r['native_id'],terminal=b['terminal'],logical_net=logical,physical_reference=b['reference']))
        report=network_metrics(rows);assert len(report)==10
        for c in report:
            terminals={n:bindings[n]for n in c['nodes']if n in bindings};logical={r['logical_net']for records in terminals.values()for r in records};assert len(logical)==1
            c['logical_net']=logical.pop();c['terminals']=terminals
            c['maximum_pair']['bindings']=[bindings.get(n,[])for n in c['maximum_pair']['nodes']]
        result.update(status='COMPLETE_ACTUAL_DRIVER_WIRE_METRICS_NOT_ELECTRICAL_ACCEPTANCE',model_sha256=sha(model),source=SOURCE,conductors=sorted(report,key=lambda c:-c['maximum_pair']['ohms']))
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
