#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare exact native metal-only return networks; not loaded PHY acceptance."""
import json,os,re,tarfile,hashlib,shlex
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
from analyze_cloud_metal_resistance import parse,resistance as dense_resistance
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-tree32-return-network'

def sparse_resistance(edges,reference,targets):
    adjacency={};names=set()
    for name,a,b,r in edges:
        assert name not in names and a!=b and np.isfinite(r)and r>0
        names.add(name);adjacency.setdefault(a,set()).add(b);adjacency.setdefault(b,set()).add(a)
    assert reference in adjacency and targets and len(targets)==len(set(targets))
    reached={reference};todo=[reference]
    while todo:
        for n in adjacency[todo.pop()]-reached:reached.add(n);todo.append(n)
    assert set(targets)<=reached and reference not in targets
    nodes=sorted(reached-{reference});index={n:i for i,n in enumerate(nodes)}
    selected=[e for e in edges if e[1]in reached];rr=[];cc=[];vv=[]
    for _,a,b,r in selected:
        for n in (a,b):
            if n!=reference:rr.append(index[n]);cc.append(index[n]);vv.append(1/r)
        if a!=reference and b!=reference:
            rr.extend([index[a],index[b]]);cc.extend([index[b],index[a]]);vv.extend([-1/r,-1/r])
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(nodes),len(nodes))).tocsc()
    rhs=np.zeros((len(nodes),len(targets)))
    for col,n in enumerate(targets):rhs[index[n],col]=1
    lu=splu(matrix);voltage=lu.solve(rhs)
    # Iterative refinement addresses arithmetic residual only, never physical R values.
    for _ in range(3):voltage+=lu.solve(rhs-matrix@voltage)
    residual=float(abs(matrix@voltage-rhs).max())
    assert np.isfinite(voltage).all()and residual<1e-7,residual
    green=voltage[[index[n]for n in targets],:]
    assert np.allclose(green,green.T,rtol=1e-7,atol=1e-10)
    terminal={}
    for col,n in enumerate(targets):
        value=float(voltage[index[n],col]);power=[]
        for name,a,b,r in selected:
            va=0 if a==reference else voltage[index[a],col]
            vb=0 if b==reference else voltage[index[b],col]
            power.append(dict(name=name,nodes=[a,b],ohms=r,unit_current_power_w=float((va-vb)**2/r)))
        total=sum(p['unit_current_power_w']for p in power)
        assert value>0 and np.isclose(total,value,rtol=1e-7,atol=1e-10)
        terminal[n]=dict(effective_ohms=value,dissipated_w_at_1a=total,largest_power_edges=sorted(power,key=lambda p:p['unit_current_power_w'],reverse=True)[:12])
    return dict(nodes=len(reached),edges=len(selected),kcl_residual_a=residual,terminals=terminal,
        transfer_resistance_targets=targets,transfer_resistance_ohms=green.tolist(),
        scope='Linear native metal-only unit-current network. C open, semiconductor devices excluded, other intrinsic terminal loads open. No measured-load voltage prediction or native transient acceptance.')

def controls():
    edges=[('r1','g','a',1.),('r2','a','b',2.),('r3','g','b',3.)]
    result=sparse_resistance(edges,'g',['a','b']);dense=dense_resistance(edges,'g',['a','b'])
    assert np.isclose(result['terminals']['a']['effective_ohms'],5/6)
    assert np.isclose(result['terminals']['b']['effective_ohms'],1.5)
    for n in ('a','b'):assert np.isclose(result['terminals'][n]['effective_ohms'],dense['terminals'][n]['effective_ohms'],rtol=1e-12)
    failures=[]
    for kind,bad,targets in [('negative',[('r1','g','a',-1.)],['a']),('zero',[('r1','g','a',0.)],['a']),('duplicate',edges+[edges[0]],['a']),('missing_target',edges,['missing']),('repeated_target',edges,['a','a'])]:
        try:sparse_resistance(bad,'g',targets)
        except AssertionError:failures.append(kind)
        else:raise AssertionError('Invalid resistor network accepted: '+kind)
    return dict(analytic_and_dense_triangle_agree=True,rejected=failures)

def native_geometry(source,cp,edges,measurement):
    # Map actual solver-edge endpoints, without claiming an edge is a straight segment.
    _,_,exported=parse((source/'wire96/rc03/wires.spice').read_text())
    rename=lambda n:n[2:]if n in {'P_'+p for p in cp}else n
    assert [(n,rename(a),rename(b),r)for n,a,b,r in exported]==edges
    coords={}
    for line in (source/'wire96/rc03/pump_wires.res.ext').read_text().splitlines():
        row=shlex.split(line)
        if row and row[0]=='rnode':
            assert len(row)==7 and row[1]not in coords
            coords[row[1]]=[int(row[4]),int(row[5])]
    anchors={v['label']:v['point_dbu']for v in json.loads((source/'wire96/anchors08.json').read_text())['anchors']}
    ports={}
    for line in (source/'wire96/rc03/pump_wires.ext').read_text().splitlines():
        row=shlex.split(line)
        if row and row[0]=='port':ports[row[1]]=[int(row[3]),int(row[4])]
    assert set(ports)==set(anchors)
    n=next(n for n,p in ports.items()if p[0]and anchors[n][0]);scale=anchors[n][0]/ports[n][0]
    assert scale>0
    assert max(abs(scale*x-y)for n,xy in ports.items()for x,y in zip(xy,anchors[n],strict=True))<=scale/2+1e-9
    original={n:(a,b,r)for n,a,b,r in exported};wanted={p['name']for t in measurement['terminals'].values()for p in t['largest_power_edges']}
    return dict(raw_to_anchor_dbu_scale=scale,edges={n:dict(ohms=original[n][2],native_nodes=list(original[n][:2]),raw_xy=[coords[a]for a in original[n][:2]],anchor_dbu_xy=[[x*scale for x in coords[a]]for a in original[n][:2]])for n in sorted(wanted)},
        scope='Coordinates of original native resistor endpoints only. No straight-segment or unique metal-layer attribution; no modified resistance.')

def analyze(label,filename):
    receipt=json.loads((ROOT/'docs/evidence'/filename).read_text());case=OUT/label;case.mkdir()
    packed=case/'source.tar.gz';fetch(receipt['url'],receipt['sha256'],packed);assert packed.stat().st_size==receipt['bytes']
    dest=case/'source';dest.mkdir()
    with tarfile.open(packed)as t:t.extractall(dest,filter='data')
    packed.unlink();source=dest/('cloud-tx-tree32-tight-assembly'if label=='tight'else'cloud-tx-tree32-headroom-assembly')
    summary=source/'composition-result.json';assert sha(summary)==receipt['summary_sha256'];report=json.loads(summary.read_text())
    assert report['status']=='PASS_ACTUAL_TREE1674_SOURCE_BOUND_RC_COMPOSITION_AND_FAULTS_REQUIRES_TRANSIENT'
    assert report['source_head']==receipt['source_head']and report['variant']=='budget_high3_trim'
    assert all(sha(source/n)==d for n,d in report['outputs'].items())
    cp,cd,ce=parse((source/'binding96/tree1674-compact01.spice').read_text())
    wp,wd,edges=parse((source/'wire96/tree1674-wire01.spice').read_text())
    assert not ce and wp==cp+['wire_cref']and set(cd)==set(wd)and len(cd)==1674
    assert len(edges)==receipt['counts']['R']and report['composition']['counts']==receipt['counts']
    assert report['topology']['no_intermacro_ideal_alias']and report['topology']['no_duplicate_child_rc']
    targets={}
    for name,dev in cd.items():
        actual=wd[name];assert(dev['model'],dev['parameters'])==(actual['model'],actual['parameters'])
        if dev['model']=='npn13g2'and dev['nodes'][2]=='avss':
            node=actual['nodes'][2];assert node not in targets
            targets[node]=dict(device=name,native_nodes=dev['nodes'],parameters=dev['parameters'],final_tail=(dev['nodes'][1]=='mr'and dev['nodes'][0]!='mr'))
    assert sum(t['final_tail']for t in targets.values())==2
    measured=sparse_resistance(edges,'avss',sorted(targets))
    for node,info in targets.items():measured['terminals'][node]['native_device']=info
    geometry=native_geometry(source,cp,edges,measured)
    return dict(source=receipt,composition_counts=report['composition']['counts'],grounded_hbt_emitters=len(targets),
        measurement=measured,native_endpoint_geometry=geometry,
        inputs={str(p.relative_to(case)):sha(p)for p in source.rglob('*')if p.is_file()})

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,loaded_voltage_prediction=False,qualified_pex=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        result['solver_controls']=controls();result['cases']={};save()
        for label,path in [('original','tx-tree32-headroom-composition-pass-20261017.json'),('tight','tx-tree32-tight-composition-pass-20261017.json')]:
            result['cases'][label]=analyze(label,path);save()
        result['status']='COMPLETE_EXACT_NATIVE_RETURN_NETWORK_DIAGNOSIS_NOT_LOADED_REPAIR'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['method_sha256']={str(p.relative_to(ROOT)):sha(p)for p in [Path(__file__),ROOT/'scripts/analyze_cloud_metal_resistance.py']}
        save();print(result['status'],flush=True)
if __name__=='__main__':main()
