#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact linear wire-only DC resistance sensitivity; never a waveform/signoff gate."""
import json,os,math
from pathlib import Path
from collections import defaultdict
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
import build_pcie_local_vco_hybrid_v6 as parser
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-cdr-strapped-v6-path-review-nominal_early'
SOURCE=ROOT/'cloud-cdr-strapped-v6-path-review-input-nominal_early'

def solve(edges,start,stop):
    assert start!=stop
    adj=defaultdict(set)
    for name,a,b,r in edges:
        assert a!=b and math.isfinite(r)and r>0
        adj[a].add(b);adj[b].add(a)
    seen={start};stack=[start]
    while stack:
        n=stack.pop()
        for v in adj[n]-seen:seen.add(v);stack.append(v)
    if stop not in seen:raise ValueError('Disconnected requested wire terminals')
    nodes=sorted(seen-{stop});idx={n:i for i,n in enumerate(nodes)}
    selected=[e for e in edges if e[1]in seen];ii=[];jj=[];vv=[]
    for name,a,b,r in selected:
        g=1/r
        for n in (a,b):
            if n!=stop:ii.append(idx[n]);jj.append(idx[n]);vv.append(g)
        if a!=stop and b!=stop:
            ii.extend((idx[a],idx[b]));jj.extend((idx[b],idx[a]));vv.extend((-g,-g))
    lap=coo_matrix((vv,(ii,jj)),shape=(len(nodes),len(nodes))).tocsc()
    rhs=np.zeros(len(nodes));rhs[idx[start]]=1.
    volts=splu(lap).solve(rhs);assert np.isfinite(volts).all()
    residual=float(np.max(np.abs(lap@volts-rhs)));assert residual<1e-7,('KCL residual',residual)
    v=dict(zip(nodes,volts,strict=True));v[stop]=0.;effective=float(v[start]);assert effective>0
    parts=[]
    for name,a,b,r in selected:
        current=float((v[a]-v[b])/r);contribution=r*current*current
        parts.append(dict(resistor=name,from_node=a,to_node=b,resistance_ohm=r,unit_injection_current_a=current,effective_R_contribution_ohm=contribution,sensitivity_dReff_dR=current*current))
    energy=sum(e['effective_R_contribution_ohm']for e in parts)
    assert abs(energy-effective)<=1e-7*max(1.,effective),('Unit-current energy identity',energy,effective)
    return dict(from_node=start,to_node=stop,effective_wire_R_ohm=effective,energy_sum_ohm=energy,kcl_residual_a=residual,nodes=len(seen),resistors=len(selected),dominant_edges=sorted(parts,key=lambda e:e['effective_R_contribution_ohm'],reverse=True)[:12])

def controls():
    edges=[('ab','a','b',2.),('bc','b','c',3.),('ac','a','c',10.)]
    a=solve(edges,'a','c');b=solve(edges,'c','a');series=solve(edges[:2],'a','c')
    assert abs(a['effective_wire_R_ohm']-10/3)<1e-12 and abs(a['effective_wire_R_ohm']-b['effective_wire_R_ohm'])<1e-12 and abs(series['effective_wire_R_ohm']-5)<1e-12
    try:solve(edges,'a','isolated')
    except ValueError:pass
    else:raise AssertionError('Accepted disconnected wire as zero resistance')
    changed=solve([('ab','a','b',20.),*edges[1:]],'a','c')
    assert changed['effective_wire_R_ohm']>a['effective_wire_R_ohm']
    return dict(analytic_parallel_series=True,reciprocity=True,disconnected_rejected=True,actual_resistor_increase_detected=True)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    f=OUT/'result.json';original=json.loads(f.read_text())
    assert original['status']=='COMPLETE_NATIVE_CDR_HYBRID_PATH_DIAGNOSIS_ORIGINAL_GATES_REMAIN_FAILED'and original['sources_unchanged']and not original['accepted']
    (OUT/'original-path-result.json').write_text(json.dumps(original,indent=2)+'\n')
    r=dict(original)
    try:
        files=[SOURCE/'composed/pd484-mim-wire.spice',SOURCE/'composed/composition.json',SOURCE/'planes/native-planes.json',Path(__file__),ROOT/'scripts/cloud_cdr_strapped_v6_path_review.py']
        protected={str(p):sha(p)for p in files};contract=json.loads(files[1].read_text());planes=json.loads(files[2].read_text())
        assert contract['counts']==dict(devices=484,R=3286,C=3855)
        edges=[]
        for row in parser.statements(files[0].read_text())[1:-1]:
            if row[0].startswith('R'):
                assert len(row)==4;edges.append((row[0],row[1].lower(),row[2].lower(),float(parser.number(row[3]))))
        assert len(edges)==3286
        physical={}
        for anchor in planes['anchors']:
            key=(anchor['native_cluster'],anchor['native_name'])
            assert physical.setdefault(key,anchor['logical_net'])==anchor['logical_net']
        devices={d['instance'].lower():d for d in contract['device_records']};raw={v.lower():k for k,v in contract['wire_node_map'].items()}
        evaluations=[]
        for load in original['sampler_load_and_collector_wire_drop_review']:
            d=devices[load['load']];q=devices[load['collector']]
            ts={x['terminal']:x for x in d['terminals']};qt={x['terminal']:x for x in q['terminals']}
            for kind,a,b in [('supply','avdd',ts['rppd_1']['node'].lower()),('load_to_collector',ts['rppd_2']['node'].lower(),qt['C']['node'].lower())]:
                if a==b:raise AssertionError('Unexpected aliased finite-contact wire')
                result=solve(edges,a,b)
                for e in result['dominant_edges']:
                    e['raw_wire_nodes']=[raw[e['from_node']],raw[e['to_node']]]
                    e['fraction_of_effective_R']=e['effective_R_contribution_ohm']/result['effective_wire_R_ohm']
                evaluations.append(dict(kind=kind,load=load['load'],collector=load['collector'],logical_net=load['logical_net'],actual_waveform_drop=load['supply_wire_drop'if kind=='supply'else'load_to_collector_wire_drop'],wire_solution=result))
        assert len(evaluations)==64
        r['linear_wire_resistance_diagnosis']=dict(controls=controls(),evaluations=evaluations,protected_inputs=protected,interpretation='1A is a mathematical test excitation of unchanged linear R network only, not actual device current. Energy contributions equal R*i^2; sensitivities identify wire resistors whose physical reduction can reduce DC effective R. Other terminals float in this calculation. This is not the multi-terminal operating point, transient delay, effective device loading, EM current, extracted RF qualification or a new acceptance gate. Original failed waveform results remain authoritative.')
        assert all(sha(Path(p))==v for p,v in protected.items())
        r['status']='COMPLETE_NATIVE_WIRE_R_SENSITIVITY_ORIGINAL_CDR_GATES_REMAIN_FAILED'
    except BaseException as e:r.update(status='FAIL_WIRE_R_DIAGNOSIS',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=f};f.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
