#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Map failed native TX devices and wire paths to the actual v5 physical hierarchy.

No waveform rerun or RC scaling. Restored physical sources must match every source
file pinned by the original loaded simulation. Shortest resistor paths are path
sums, not effective resistance, extracted delays, or PHY acceptance.
"""
import heapq,json,math,os,re,tarfile
from collections import defaultdict
from pathlib import Path
from route_cloud_newer_postcts import fetch,sha
import build_pcie_local_vco_hybrid_v6 as parser
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-tx-return64-bias-return'

def shortest(graph,start):
    dist={start:0.};prev={};q=[(0.,start)]
    while q:
        value,node=heapq.heappop(q)
        if value!=dist[node]:continue
        for nxt,res,name in graph[node]:
            new=value+res
            if new<dist.get(nxt,math.inf):dist[nxt]=new;prev[nxt]=(node,res,name);heapq.heappush(q,(new,nxt))
    return dist,prev

def box(raw):
    b=list(map(float,re.findall(r'-?\d+(?:\.\d+)?',raw)));assert len(b)==4
    return b

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,
        scope='Exact failed v5 native HBTs mapped to source physical macro/terminals and raw resistor paths. No new transient, source waveform change, device edit or physical repair acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        wavepin=json.loads((ROOT/'docs/evidence/tx-return64-full-wire-rejection-20261018.json').read_text())
        run=wavepin['run'];group='tx-v5-return64-wave-wire-nominal-none';stem=f'{group}-{run}-1'
        url=f'https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-{run}-1-{group}/{stem}.summary.json'
        fetch(url,wavepin['summary_sha256'],OUT/'original-wave-summary.json');wave=json.loads((OUT/'original-wave-summary.json').read_text())
        assert wave['source_head']==wavepin['source_head']and wave['source_unchanged']and not wave['electrical_screen_passed']
        pin=json.loads((ROOT/'docs/evidence/tx-return64-path-review-pass-20261018.json').read_text());review=pin['report']
        assert review['sources_unchanged']and review['original_gates_reproduced']and review['native_source']['summary_sha256']==wavepin['summary_sha256']
        cp=json.loads((ROOT/'docs/evidence/tx-v5-return64-composition-pass-20261018.json').read_text())
        assert cp==wave['source']
        packed=ROOT/'tx-return64-bias-return-source.tar.gz';fetch(cp['url'],cp['sha256'],packed);assert packed.stat().st_size==cp['bytes']
        dest=ROOT/'cloud-tx-return64-bias-return-input';dest.mkdir()
        with tarfile.open(packed)as tar:tar.extractall(dest,filter='data')
        packed.unlink();P=dest/'cloud-tx-balanced-v5-return64-assembly'
        token='/source/cloud-tx-balanced-v5-return64-assembly/'
        expected={n.split(token,1)[1]:h for n,h in wave['protected_inputs'].items()if token in n}
        actual={str(p.relative_to(P)):sha(p)for p in P.rglob('*')if p.is_file()}
        assert expected and actual==expected,'Physical source differs from original simulated model source'
        r['verified_physical_files']=actual;r['composition_source']=dict(run=cp['source_run'],summary_sha256=cp['summary_sha256'],archive_sha256=cp['sha256']);save()
        physical=json.loads((P/'result.json').read_text());layout=json.loads((P/'layout/result.json').read_text());loc=json.loads((P/'wire96/device-locations01.json').read_text());anchors=json.loads((P/'wire96/anchors08.json').read_text());binding=json.loads((P/'binding96/binding01.json').read_text())
        assert physical['variant']=='budget_balanced_v5'and physical['source_head']=='671f86f8d41fafc474ecb879ba4438ced28c1ff7'
        assert physical['placement_pitch']==dict(name='original',column_um=1000.,row_um=600.,inverse_topology_matches_original=True)
        assert physical['return_rail']==cp['return_rail'] and physical['return_rail']['profile']=='wide64'and physical['return_rail']['trunk_and_bus_width_um']==64.
        devices={d['native_id']:d for d in loc['devices']};assert len(devices)==1674
        model=P/'wire96/tree1674-wire01.spice';assert sha(model)==wave['model_sha256']==cp['model_sha256']['wire']
        rows=parser.statements(model.read_text());graph=defaultdict(list);parent={};R=[];C=[]
        def root(n):
            parent.setdefault(n,n)
            while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
            return n
        for row in rows[1:-1]:
            if row[0][0].lower()not in ('r','c'):continue
            assert len(row)==4
            name,a,b=row[0],row[1].lower(),row[2].lower();value=float(parser.number(row[3]));assert math.isfinite(value)and value>=0
            if name[0].lower()=='r':
                assert value>0;graph[a].append((b,value,name));graph[b].append((a,value,name));parent[root(a)]=root(b);R.append((name,a,b,value))
            else:C.append((name,a,b,value))
        assert len(R)==116611 and len(C)==77471
        ports=[x.lower()for x in binding['native_ports']];public={}
        for p in ports:public.setdefault(root(p),[]).append(p)
        assert all(len(v)==1 for v in public.values()),'Public ports unexpectedly share conductor'
        caps=defaultdict(float)
        for _,a,b,value in C:
            for k in {root(a),root(b)}:caps[k]+=value
        dx,dy=layout['origin_translation_um'];bounds={}
        for name,place in layout['placements'].items():
            b=box(place['bbox_um']);bounds[name]=[b[0]+dx,b[1]+dy,b[2]+dx,b[3]+dy]
        models={row[0].lower():row for row in rows[1:-1]if row[0].lower().startswith('x')}
        cache={};mapped=[]
        for failure in review['failed_hbt_terminal_review']:
            match=re.fullmatch(r'xtree\.xd(\d+)',failure['device']);assert match
            did=int(match[1]);d=devices[did];dbox=box(d['pcell']['bbox'])
            hits=[n for n,b in bounds.items()if b[0]-1e-9<=dbox[0]and b[1]-1e-9<=dbox[1]and b[2]+1e-9>=dbox[2]and b[3]+1e-9>=dbox[3]]
            assert len(hits)==1,(did,hits);macro=hits[0]
            modelrow=models[f'xd{did:04d}'];assert modelrow[5].lower()=='npn13g2'
            assert ['xtree.'+n.lower()for n in modelrow[1:5]]==failure['native_binding']['terminals']
            terms=[]
            for label,node in zip(('C','B','E','S'),modelrow[1:5],strict=True):
                node=node.lower();matches=[a for a in anchors['rows']if a['device']==did and a['terminal']==label]
                assert len(matches)==1
                ar=matches[0]
                if ar['disposition']=='ACTUAL_TERMINAL_METAL_POINT_REFERENCE':assert ar['wire_anchor'].lower()==node
                term=dict(terminal=label,node=node,native_anchor=ar,voltage=failure['terminal_voltages'][label]['voltage'])
                if node in graph:
                    component=root(node);term['incident_wire_capacitance_f']=caps[component]
                    pp=public.get(component,[]);term['public_ports_same_conductor']=pp
                    if pp:
                        port=pp[0]
                        if port not in cache:cache[port]=shortest(graph,port)
                        dist,prev=cache[port];assert node in dist
                        trace=[];at=node
                        while at!=port:
                            other,res,name=prev[at];trace.append(dict(element=name,from_node=other,to_node=at,resistance_ohm=res));at=other
                        term['shortest_resistor_path_from_public']=dict(port=port,resistance_ohm=dist[node],segment_count=len(trace),largest_segments=sorted(trace,key=lambda x:x['resistance_ohm'],reverse=True)[:12])
                terms.append(term)
            mapped.append(dict(device=failure['device'],native_id=did,macro=macro,kind=layout['placements'][macro]['kind'],macro_bbox_um=bounds[macro],native_device=d,terminals=terms,original_gate=failure['original_gate']))
        assert len(mapped)==28
        r['failed_device_physical_paths']=mapped
        r['parent_return_geometry_before_origin_translation']=layout['parent_return_geometry_before_origin_translation']
        r['return_rail']=physical['return_rail'];r['origin_translation_um']=[dx,dy]
        r['failed_input_routes']=[x for x in layout['signal_routes']if any(n.startswith(('p4_','a.','b.'))for n in x['endpoints'])]
        r['physical_source_scope']=layout['scope'];r['native_counts']=dict(devices=1674,R=len(R),C=len(C))
        # Read exact native terminal observations, without another transient.
        reports.OUT=OUT
        rr,rp=reports.restore_report('tx-return64-path-review',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'terminal-review',['all-hbt-terminal-voltages.json'])
        assert rr==review and rr['sources_unchanged']and rr['original_gates_reproduced']
        vp=OUT/'terminal-review/all-hbt-terminal-voltages.json'
        assert sha(vp)==rr['outputs']['all-hbt-terminal-voltages.json']
        volts=json.loads(vp.read_text());hbt={}
        for b in binding['devices']:
            if b['model'].lower()!='npn13g2':continue
            did=b['native_id'];name='xtree.'+b['instance'].lower()
            assert name in volts and name in wave['review']['hbt_devices']
            nodes={k.upper():v.lower()for k,v in b['native_nodes'].items()}
            assert set(nodes)=={'C','B','E','S'}
            row=models[b['instance'].lower()];assert row[5].lower()=='npn13g2'
            for label,node in zip(('C','B','E','S'),row[1:5],strict=True):
                assert volts[name][label]['node']=='xtree.'+node.lower()
            dbox=box(devices[did]['pcell']['bbox'])
            matches=[tag for tag,bb in bounds.items()if bb[0]-1e-9<=dbox[0]and bb[1]-1e-9<=dbox[1]and bb[2]+1e-9>=dbox[2]and bb[3]+1e-9>=dbox[3]]
            assert len(matches)==1
            hbt[name]=dict(native_id=did,macro=matches[0],native_nodes=nodes,voltage=volts[name],gate=wave['review']['hbt_devices'][name],parameters=b['parameters'])
        assert len(hbt)==589
        references={n:d for n,d in hbt.items()if d['native_nodes']['C']==d['native_nodes']['B']and d['native_nodes']['E']=='avss'}
        assert {d['macro']for d in references.values()}==set(layout['placements']), 'Each actual macro must contain its native diode reference'
        groups=[];seen=set()
        for name,ref in references.items():
            related={n:d for n,d in hbt.items()if n!=name and d['native_nodes']['B']==ref['native_nodes']['B']and d['native_nodes']['E']=='avss'and d['native_nodes']['C']!=d['native_nodes']['B']}
            assert related and all(d['macro']==ref['macro']for d in related.values())
            rv=ref['voltage'];rows=[]
            for tail_name,tail in related.items():
                assert tail_name not in seen;seen.add(tail_name);tv=tail['voltage']
                de=tv['E']['voltage']['mean_v']-rv['E']['voltage']['mean_v']
                db=tv['B']['voltage']['mean_v']-rv['B']['voltage']['mean_v']
                rows.append(dict(device=tail_name,native_id=tail['native_id'],parameters=tail['parameters'],gate=tail['gate'],terminal_voltages=tv,tail_minus_reference_emitter_mean_v=de,tail_minus_reference_base_mean_v=db,tail_minus_reference_vbe_mean_v=db-de))
            groups.append(dict(macro=ref['macro'],reference_device=name,reference_native_id=ref['native_id'],logical_reference_net=ref['native_nodes']['B'],reference_parameters=ref['parameters'],reference_gate=ref['gate'],reference_terminal_voltages=rv,tails=rows))
        assert groups and seen
        r['reference_to_tail_bias']=sorted(groups,key=lambda x:x['macro'])
        r['bias_return_source']=rp;r['bias_reference_count']=len(references);r['bias_tail_count']=len(seen)
        r['bias_scope']='Original native active-window terminal means and instantaneous gates, same logical mirror references but actual distinct wire nodes. Differences are observations, not fitted gains, effective impedance or acceptance. No model, layout or stimulus changed.'
        assert all(sha(P/n)==h for n,h in expected.items())
        r['sources_unchanged']=True;r['status']='COMPLETE_NATIVE_TX_REFERENCE_TAIL_RETURN_DIAGNOSIS_NOT_REPAIR'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
