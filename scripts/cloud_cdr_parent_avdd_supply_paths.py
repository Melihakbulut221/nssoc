#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read native wire paths and unavoidable wire bridges; no effective-R or new simulation."""
import heapq,json,math,os
from collections import defaultdict
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as parser
from cloud_cdr_parent_avdd_v13_mim_streamed import bind_native
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-cdr-parent-avdd-supply-paths'

def paths(graph,start):
    distance={start:0.};previous={};queue=[(0.,start)]
    while queue:
        value,node=heapq.heappop(queue)
        if value!=distance[node]:continue
        for other,resistance,name in graph[node]:
            proposed=value+resistance
            if proposed<distance.get(other,math.inf):
                distance[other]=proposed;previous[other]=(node,name)
                heapq.heappush(queue,(proposed,other))
    return distance,previous

def bridges(graph,start):
    # Edge identity, not parent-node identity, handles parallel resistors.
    entry={start:0};exit_order={};low={start:0};parent={};found=[]
    stack=[(start,iter(graph[start]))];clock=1
    while stack:
        node,adj=stack[-1]
        try:
            other,resistance,name=next(adj)
        except StopIteration:
            stack.pop();exit_order[node]=clock
            if node in parent:
                above,edge=parent[node]
                low[above]=min(low[above],low[node])
                if low[node]>entry[above]:found.append((edge,node))
            continue
        if node in parent and name==parent[node][1]:continue
        if other in entry:
            low[node]=min(low[node],entry[other]);continue
        parent[other]=(node,name);entry[other]=low[other]=clock;clock+=1
        stack.append((other,iter(graph[other])))
    return entry,exit_order,found

def controls():
    edges=[('ab','a','b',1.),('bc','b','c',2.),('ac','a','c',9.),('cd','c','d',4.),
           ('de1','d','e',5.),('de2','d','e',6.)]
    graph=defaultdict(list)
    for name,a,b,r in edges:graph[a].append((b,r,name));graph[b].append((a,r,name))
    d,p=paths(graph,'a');assert d==dict(a=0.,b=1.,c=3.,d=7.,e=12.)
    lo,hi,cut=bridges(graph,'a');assert cut==[('cd','d')]
    assert {n for n in lo if lo['d']<=lo[n]<hi['d']}=={'d','e'}
    assert paths(graph,'isolated')[0]=={'isolated':0.}
    assert bridges(graph,'isolated')[2]==[]
    return dict(known_shortest_paths=True,cycle_not_a_bridge=True,
                parallel_edges_not_bridges=True,bridge_disconnects_expected_subtree=True,
                disconnected_not_zero_resistance=True)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
           full_phy_accepted=False,qualified_pex=False,no_new_simulation=True)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['controls']=controls()
        pin=json.loads((ROOT/'docs/evidence/cdr-parent-avdd-v13-fullwave-nominal_late-20261019.json').read_text())
        old=pin['report'];assert old['status']=='REJECTED_WHOLE_MIM_PD484_LOADED'
        assert old['devices_passed'] and not old['data_passed'] and old['sources_unchanged']
        cp=json.loads((ROOT/'docs/evidence/cdr-parent-avdd-v13-mim-composition-pass-20261019.json').read_text())
        composition,proof=reports.restore_report('cdr-parent-avdd-v13-mim-composition',cp['run'],
            cp['summary_sha256'],cp['parts_sha256'],OUT/'model',
            ['pd484-mim-wire.spice','composition.json'])
        pp=json.loads((ROOT/'docs/evidence/cdr-parent-avdd-v13-planes-pass-20261019.json').read_text())
        plane_report,plane_proof=reports.restore_report('cdr-parent-avdd-v13-planes',pp['run'],
            pp['summary_sha256'],pp['parts_sha256'],OUT/'planes',['native-planes.json'])
        assert old['composition_source']['summary_sha256']==cp['summary_sha256']
        assert old['native_plane_source']['summary_sha256']==pp['summary_sha256']
        model=OUT/'model/pd484-mim-wire.spice';contract_file=OUT/'model/composition.json'
        planes_file=OUT/'planes/native-planes.json'
        for path,oldname in [(model,'composed/pd484-mim-wire.spice'),
                             (contract_file,'composed/composition.json'),(planes_file,'planes/native-planes.json')]:
            assert sha(path)==old['outputs'][oldname]
        frozen={str(p):sha(p)for p in [model,contract_file,planes_file,Path(__file__)]}
        contract=json.loads(contract_file.read_text());planes=json.loads(planes_file.read_text())
        assert contract['counts']==dict(devices=484,R=16010,C=11677)
        assert bind_native(model.read_text(),contract,planes)==old['binding']
        graph=defaultdict(list);edges={}
        for row in parser.statements(model.read_text())[1:-1]:
            if row[0][0]!='R':continue
            assert len(row)==4
            name,a,b,value=row[0],row[1].lower(),row[2].lower(),float(parser.number(row[3]))
            assert name not in edges and math.isfinite(value) and value>0
            edges[name]=dict(nodes=[a,b],resistance_ohm=value)
            graph[a].append((b,value,name));graph[b].append((a,value,name))
        assert len(edges)==16010
        rails={}
        for rail in ('avdd','avss'):
            terminals=[]
            for device in contract['device_records']:
                for term in device['terminals']:
                    if term['native_net']!=rail or term['anchor']is None:continue
                    terminals.append(dict(device=device['instance'],terminal=term['terminal'],
                                          node=term['node'].lower(),model=device['model']))
            assert terminals and rail in graph
            distance,previous=paths(graph,rail);entry,finish,cut=bridges(graph,rail)
            assert set(distance)==set(entry)
            prior_paths={(q['device'].lower(),q['terminal']):q for q in
                         json.loads((ROOT/'docs/evidence/cdr-parent-avdd-v13-late-native-diagnosis-20261019.json').read_text())['report']['supply_terminal_review']
                         if q['rail']==rail}
            routes=[]
            for target in terminals:
                node=target['node'];assert node in distance
                oldpath=prior_paths[(target['device'].lower(),target['terminal'])]
                assert abs(distance[node]-oldpath['shortest_resistor_path_ohm'])<1e-8
                path=[];walk=node
                while walk!=rail:
                    above,name=previous[walk];path.append(name);walk=above
                path.reverse()
                routes.append(dict(**target,shortest_resistor_path_ohm=distance[node],
                    original_native_voltage_from_external=oldpath['voltage_from_external'],
                    resistor_path=[dict(name=name,**edges[name])for name in path]))
            cuts=[]
            for name,child in cut:
                affected=[dict(device=t['device'],terminal=t['terminal'],node=t['node'])for t in terminals
                          if entry[child]<=entry[t['node']]<finish[child]]
                if not affected:continue
                cuts.append(dict(name=name,**edges[name],disconnected_terminals=affected,
                                 disconnected_terminal_count=len(affected)))
            cuts.sort(key=lambda x:(x['disconnected_terminal_count'],x['resistance_ohm']),reverse=True)
            rails[rail]=dict(reachable_wire_nodes=len(distance),terminals=len(terminals),
                original_path_metrics_reproduced=True,shortest_paths=routes,unavoidable_wire_bridges=cuts)
        assert all(sha(Path(p))==h for p,h in frozen.items())
        r.update(status='COMPLETE_EXACT_NATIVE_SUPPLY_PATH_AND_BRIDGE_REVIEW_NOT_ELECTRICAL_ACCEPTANCE',
            source_run=pin['run'],source_summary_sha256=pin['summary_sha256'],
            model_source=proof,plane_source=plane_proof,rails=rails,protected_inputs=frozen,
            sources_unchanged=True,
            scope='Only actual extracted wire-resistor graph. Paths are resistance upper bounds, not effective resistance. Bridges are cuts in this wire graph, not complete transistor-circuit current paths. Existing waveform terminal drops are reproduced from pinned diagnosis; no inferred branch current, fitted RC, altered waveform, changed acceptance or new transient.')
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
