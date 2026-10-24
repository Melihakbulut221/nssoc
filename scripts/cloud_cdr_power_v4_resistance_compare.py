#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare actual CDR power access resistance, without assuming waveform improvement."""
import json,os
from collections import Counter
from pathlib import Path
import numpy as np
import networkx as nx
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as parser
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr-power-v4-resistance-compare'

def native_match(old,new,oldgeo,newgeo):
    def index(c):return {d['native_id']:d for d in c['device_records']}
    a,b=index(old),index(new);assert set(a)==set(b)==set(range(1,485))
    ga={d['native_id']:d for d in oldgeo['devices']};gb={d['native_id']:d for d in newgeo['devices']}
    assert set(ga)==set(gb)==set(a)
    public=set(old['interface']);assert public==set(new['interface'])
    mapping={};reverse={}
    for i in a:
        x,y=a[i],b[i]
        assert x['model']==y['model'] and x['parameters']==y['parameters']
        assert ga[i]['model']==gb[i]['model'] and ga[i]['parameters']==gb[i]['parameters']
        assert ga[i]['pcell']['transform']==gb[i]['pcell']['transform'],(i,'Physical primitive moved')
        assert [t['terminal']for t in x['terminals']]==[t['terminal']for t in y['terminals']]
        for u,v in zip(x['terminals'],y['terminals'],strict=True):
            p,q=u['native_net'],v['native_net']
            assert mapping.setdefault(p,q)==q and reverse.setdefault(q,p)==p
            if p in public or q in public:assert p==q
    return dict(devices=484,native_net_bijection=mapping,primitive_transforms_exact=True,ordered_terminal_topology_and_parameters_exact=True)

def solve(text,contract):
    rows=parser.statements(text);assert Counter(r[0][0]for r in rows[1:-1])==dict(X=484,R=3538,C=4038)
    graph=nx.Graph();edges=[]
    for row in rows[1:-1]:
        if not row[0].startswith('R'):continue
        name,a,b,number=row;a=a.lower();b=b.lower();res=float(parser.number(number))
        assert np.isfinite(res)and res>0 and a!=b
        edges.append((name,a,b,res));graph.add_edge(a,b)
    targets={}
    for d in contract['device_records']:
        for t in d['terminals']:
            if t['native_net']in ('avdd','avss')and t['anchor']is not None:
                key=f"{d['native_id']}:{t['terminal']}"
                assert key not in targets
                targets[key]=dict(native_id=d['native_id'],instance=d['instance'],model=d['model'],terminal=t['terminal'],rail=t['native_net'],node=t['node'].lower())
    result={};matrices={}
    for rail in ('avdd','avss'):
        comp=nx.node_connected_component(graph,rail)
        assert not (set(('avdd','avss','wire_cref'))-{rail})&comp
        nodes=sorted(comp-{rail});index={n:i for i,n in enumerate(nodes)}
        es=[e for e in edges if e[1]in comp];assert all(e[2]in comp for e in es)
        ii=[];jj=[];vv=[]
        for _,a,b,res in es:
            for node in (a,b):
                if node!=rail:ii.append(index[node]);jj.append(index[node]);vv.append(1/res)
            if a!=rail and b!=rail:ii.extend((index[a],index[b]));jj.extend((index[b],index[a]));vv.extend((-1/res,-1/res))
        mat=coo_matrix((vv,(ii,jj)),shape=(len(nodes),len(nodes))).tocsc();factor=splu(mat)
        solutions=[]
        for key,t in targets.items():
            if t['rail']!=rail:continue
            point=t['node'];assert point in comp and point!=rail
            inj=np.zeros(len(nodes));inj[index[point]]=1
            volts=factor.solve(inj);assert np.isfinite(volts).all()
            residual=float(np.max(abs(mat@volts-inj)));assert residual<1e-7
            effective=float(volts[index[point]]);assert effective>0
            def v(n):return 0. if n==rail else float(volts[index[n]])
            losses=[dict(name=name,nodes=[a,b],resistance_ohm=res,unit_current_loss_w=(v(a)-v(b))**2/res)for name,a,b,res in es]
            energy=sum(x['unit_current_loss_w']for x in losses);assert abs(energy-effective)<1e-7*max(1,effective)
            result[key]=dict(t,effective_resistance_ohm=effective,kcl_residual_a=residual,unit_current_total_loss_w=energy,top5_loss_branches=sorted(losses,key=lambda x:x['unit_current_loss_w'],reverse=True)[:5])
            solutions.append((point,volts))
        assert len(solutions)>=2
        p,vp=solutions[0];q,vq=solutions[-1];forward=float(vp[index[q]]);reverse=float(vq[index[p]])
        assert abs(forward-reverse)<1e-8*max(1,abs(forward))
        matrices[rail]=dict(nodes=len(comp),resistors=len(es),reciprocity_ohm=[forward,reverse])
    return dict(targets=result,rails=matrices)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,scope='Actual native power-access DC unit-current comparison at every supply terminal. Not actual operating current, rail drop, transient or closed-loop acceptance; no reduced model replaces original waveform decks.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        data={};protected=[];r['sources']={}
        for tag,prefix in [('baseline','cdr-parallel-v3'),('candidate','cdr-power-v4')]:
            pin=json.loads((ROOT/f'docs/evidence/{prefix}-mim-composition-pass-20261018.json').read_text())
            selected=['pd484-mim-wire.spice','composition.json']
            model,proof=reports.restore_report(prefix+'-mim-composition',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/tag/'model',selected)
            assert model==pin['report']and model['sources_unchanged']and len(model['controls'])==19
            cap=json.loads((ROOT/f'docs/evidence/{prefix}-mim-parent-capture-pass-20261018.json').read_text())
            names=['source/wire/device-locations01.json']
            capture,cp=reports.restore_report(prefix+'-mim-parent-rc',cap['run'],cap['summary_sha256'],cap['parts_sha256'],OUT/tag/'physical',names)
            assert capture==cap['report']and capture['sources_unchanged']
            assert capture['model_binding_source']['summary_sha256']==model['model_source']['summary_sha256']
            c=json.loads((OUT/tag/'model/composition.json').read_text());assert c==model['composition']
            g=json.loads((OUT/tag/'physical'/names[0]).read_text())
            text=(OUT/tag/'model/pd484-mim-wire.spice').read_text();data[tag]=(c,g,text)
            protected.extend((OUT/tag/'model'/n,model['outputs'][n])for n in selected)
            protected.extend((OUT/tag/'physical'/n,capture['outputs'][n])for n in names)
            r['sources'][tag]=dict(model=proof,physical=cp)
        old,oldgeo,oldtext=data['baseline'];new,newgeo,newtext=data['candidate']
        r['native_equivalence']=native_match(old,new,oldgeo,newgeo)
        # Actual identity corruptions must fail before solving candidate graphs.
        import copy
        r['identity_controls']=[]
        for name in ('changed_primitive_position','changed_device_width','changed_supply_terminal'):
            altered=copy.deepcopy(new);geo=copy.deepcopy(newgeo)
            if name=='changed_primitive_position':geo['devices'][0]['pcell']['transform']='INVALID_PHYSICAL_TRANSFORM'
            elif name=='changed_device_width':altered['device_records'][0]['parameters']['w']='999u'
            else:
                t=next(t for d in altered['device_records']for t in d['terminals']if t['native_net']=='avss');t['native_net']='avdd'
            try:native_match(old,altered,oldgeo,geo)
            except (AssertionError,ValueError):r['identity_controls'].append(dict(name=name,rejected=True))
            else:raise AssertionError('Accepted '+name)
        r['baseline']=solve(oldtext,old);r['candidate']=solve(newtext,new);a=r['baseline']['targets'];b=r['candidate']['targets'];assert set(a)==set(b)
        diffs=[]
        for key in a:
            assert all(a[key][n]==b[key][n]for n in ('native_id','model','terminal','rail'))
            before=a[key]['effective_resistance_ohm'];after=b[key]['effective_resistance_ohm']
            diffs.append(dict(key=key,rail=a[key]['rail'],model=a[key]['model'],before_ohm=before,after_ohm=after,delta_ohm=after-before,reduction_percent=100*(before-after)/before))
        r['comparison']=sorted(diffs,key=lambda x:x['delta_ohm']);r['changed_model_bytes']=oldtext!=newtext
        assert all(sha(p)==expected for p,expected in protected)
        r.update(status='COMPLETE_NATIVE_POWER_ACCESS_COMPARISON_NOT_TRANSIENT_ACCEPTANCE',sources_unchanged=True)
        print(json.dumps(dict(status=r['status'],largest_reductions=r['comparison'][:8],largest_increases=r['comparison'][-8:]),indent=2),flush=True)
    except BaseException as e:r.update(status='FAIL_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
