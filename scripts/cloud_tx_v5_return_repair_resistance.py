#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Diagnostic DC resistance of the actual TX return graph; not a waveform model."""
import hashlib,json,os,re,tarfile
from collections import Counter
from pathlib import Path
import numpy as np
import networkx as nx
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
import build_pcie_local_vco_hybrid_v6 as parser
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-v5-return-repair-resistance'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,simulation_rerun=False,scope='DC unit-current resistance of unchanged native metal graph only. Capacitors are open only for this static diagnostic. No dynamic waveform, rail-current estimate, parasitic replacement or layout acceptance.')
    try:
        inputs=ROOT/'hw/soc/out/cloud-tx-v5-return-repair-assembly'
        source=json.loads((inputs/'composition-result.json').read_text())
        assert source['status']=='PASS_ACTUAL_TREE1674_SOURCE_BOUND_RC_COMPOSITION_AND_FAULTS_REQUIRES_TRANSIENT'
        assert source['source_head']==os.environ['GITHUB_SHA']
        assert source['source']['source_run']==39135318667
        assert all(sha(inputs/p)==v for p,v in source['outputs'].items())
        receipts={p:dict(sha256=sha(inputs/p)) for p in ['composition-result.json','binding96/binding01.json','layout/result.json','wire96/device-locations01.json','wire96/tree1674-wire01.spice']}
        binding=json.loads((inputs/'binding96/binding01.json').read_text())
        interface=json.loads((inputs/'wire96/all-interface-probes.json').read_text())
        layout=json.loads((inputs/'layout/result.json').read_text())
        locations=json.loads((inputs/'wire96/device-locations01.json').read_text())
        for rel in ['layout/result.json','wire96/device-locations01.json']:
            expected=[v for p,v in interface['inputs'].items() if p.endswith('/'+rel)]
            assert expected==[sha(inputs/rel)]
        text=(inputs/'wire96/tree1674-wire01.spice').read_text();rows=parser.statements(text)
        baseline=json.loads((ROOT/'docs/evidence/tx-v5-columns-native-return-diagnosis-20261018.json').read_text())
        assert baseline['run']==39133064102 and baseline['summary_sha256']=='696c27c19cab691a46dc1f48a1f72c12574e8cf78cf226df0741419a804cf41a'
        prior={(v['physical_macro'],v['native_id']):v for v in baseline['report']['return_paths']}
        r['baseline_source']=dict(run=baseline['run'],summary_sha256=baseline['summary_sha256'])
        assert rows[0][0].lower()=='.subckt'and rows[-1][0].lower()=='.ends'and'avss'in rows[0][2:]
        cards={row[0].lower():row for row in rows[1:-1]};assert len(cards)==len(rows)-2
        counts=Counter(row[0][0].upper()for row in rows[1:-1]);assert counts==dict(X=1674,R=116611,C=77471)
        graph=nx.Graph();resistors=[]
        for row in rows[1:-1]:
            if not row[0].upper().startswith('R'):continue
            assert len(row)==4 and row[1]!=row[2]
            ohm=float(parser.number(row[3]));assert np.isfinite(ohm)and ohm>0
            resistors.append((row[0],row[1],row[2],ohm));graph.add_edge(row[1],row[2])
        component=nx.node_connected_component(graph,'avss');assert'avdd'not in component and'sub'not in component
        edges=[row for row in resistors if row[1]in component];assert all(b in component for _,a,b,v in edges)
        nodes=sorted(component-{'avss'});index={n:i for i,n in enumerate(nodes)};ii=[];jj=[];vv=[]
        for _,a,b,v in edges:
            g=1/v
            for n in (a,b):
                if n!='avss':ii.append(index[n]);jj.append(index[n]);vv.append(g)
            if a!='avss'and b!='avss':
                ii.extend([index[a],index[b]]);jj.extend([index[b],index[a]]);vv.extend([-g,-g])
        matrix=coo_matrix((vv,(ii,jj)),shape=(len(nodes),len(nodes))).tocsc();factor=splu(matrix)
        dx,dy=layout['origin_translation_um']
        def rect(raw):
            values=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)));assert len(values)==4;return values
        boxes={}
        for tag,item in layout['placements'].items():
            l,b,rr,t=rect(item['bbox_um']);boxes[tag]=(l+dx,b+dy,rr+dx,t+dy)
        locations={d['native_id']:d for d in locations['devices']};selected=[];solutions={}
        for d in binding['devices']:
            if d['model']!='npn13g2'or d['native_nodes']['E']!='avss':continue
            row=cards[d['instance'].lower()];assert row[5]=='npn13g2';point=row[3];assert point in component and point!='avss'
            box=rect(locations[d['native_id']]['pcell']['bbox']);owners=[tag for tag,b in boxes.items()if box[0]>=b[0]-1e-9 and box[1]>=b[1]-1e-9 and box[2]<=b[2]+1e-9 and box[3]<=b[3]+1e-9];assert len(owners)==1
            current=np.zeros(len(nodes));current[index[point]]=1.;volts=factor.solve(current)
            residual=float(np.max(np.abs(matrix@volts-current)));assert residual<1e-7
            effective=float(volts[index[point]]);assert np.isfinite(volts).all()and effective>0
            def voltage(n):return 0. if n=='avss'else float(volts[index[n]])
            branches=[]
            for name,a,b,ohm in edges:
                drop=voltage(a)-voltage(b);power=drop*drop/ohm
                branches.append(dict(name=name,nodes=[a,b],resistance_ohm=ohm,unit_injection_current_a=drop/ohm,unit_injection_loss_w=power))
            energy=sum(x['unit_injection_loss_w']for x in branches);assert abs(energy-effective)<1e-7*max(1,effective)
            entry=dict(instance=d['instance'],native_id=d['native_id'],physical_macro=owners[0],native_emitter_net='avss',wire_emitter_point=point,nx=d['parameters']['nx'],effective_return_resistance_ohm=effective,kcl_maximum_residual_a=residual,unit_current_total_loss_w=energy,top20_loss_branches=sorted(branches,key=lambda x:x['unit_injection_loss_w'],reverse=True)[:20])
            selected.append(entry)
            if d['native_id']in (114,115):solutions[d['native_id']]=(point,volts.copy())
        assert len(selected)==len(prior)
        delta=[]
        for v in selected:
            old=prior[v['physical_macro'],v['native_id']]
            assert old['nx']==v['nx'] and old['instance']==v['instance']
            before=old['effective_return_resistance_ohm'];after=v['effective_return_resistance_ohm']
            delta.append(dict(instance=v['instance'],native_id=v['native_id'],physical_macro=v['physical_macro'],before_ohm=before,after_ohm=after,change_ohm=after-before,change_percent=100*(after/before-1)))
        r['resistance_comparison']=delta
        r['comparison_scope']='Static metal return resistance only. Original failed waveform is not a measurement of this repaired geometry. No electrical acceptance.'
        assert set(solutions)=={114,115}
        pa,va=solutions[114];pb,vb=solutions[115];ab=float(va[index[pb]]);ba=float(vb[index[pa]]);assert abs(ab-ba)<1e-8*max(1,abs(ab))
        r.update(status='COMPLETE_NATIVE_RETURN_DC_GRAPH_DIAGNOSIS_NOT_WAVEFORM_ACCEPTANCE',source=source,verified_files=receipts,native_census=dict(counts),return_graph_nodes=len(component),return_graph_resistors=len(edges),emitter_points=len(selected),return_paths=sorted(selected,key=lambda x:x['effective_return_resistance_ohm'],reverse=True),reciprocity=dict(inject114_observe115_ohm=ab,inject115_observe114_ohm=ba),method_sha256=sha(Path(__file__)))
        assert all(sha(inputs/p)==v['sha256']for p,v in receipts.items());r['sources_unchanged']=True
        print(json.dumps(dict(status=r['status'],return_nodes=len(component),return_R=len(edges),worst=[{k:x[k]for k in ('instance','physical_macro','effective_return_resistance_ohm')}for x in r['return_paths'][:12]],final=[{k:x[k]for k in ('instance','physical_macro','effective_return_resistance_ohm')}for x in r['return_paths']if x['native_id']in (114,115)]),indent=2),flush=True)
    except BaseException as e:r.update(status='FAIL_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
