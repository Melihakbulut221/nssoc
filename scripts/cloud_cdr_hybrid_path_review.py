#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read unchanged native CDR RISERS captures and locate distributed-wire losses.

This runs no new transient and changes no device, wire value, bit or threshold.
Shortest resistor paths are path-resistance upper bounds, not effective resistance
or qualified delay. Capacitance totals are incident wire capacitance, not loading
including intrinsic devices. Only the original native waveform supplies voltages.
"""
import argparse,heapq,json,math,os
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as parser
from route_cloud_newer_postcts import sha
from cloud_cdr_hybrid_mim_loaded import bind_native,START,STOP,STEP,UI
ROOT=Path(__file__).resolve().parents[1]

def shortest(graph,start):
    distance={start:0.};queue=[(0.,start)]
    while queue:
        value,node=heapq.heappop(queue)
        if value!=distance[node]:continue
        for other,resistance in graph[node]:
            proposal=value+resistance
            if proposal<distance.get(other,math.inf):
                distance[other]=proposal;heapq.heappush(queue,(proposal,other))
    return distance

def graph_controls():
    graph={'a':[('b',2.),('c',10.)],'b':[('a',2.),('c',3.)],'c':[('a',10.),('b',3.)],'isolated':[]}
    assert shortest(graph,'a')==dict(a=0.,b=2.,c=5.)
    assert shortest(graph,'isolated')=={'isolated':0.}
    return dict(shortest_path_parallel_route=True,disconnected_node_not_assigned_zero=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--case',choices=['nominal_early','nominal_late'],required=True);args=ap.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/('cloud-cdr-hybrid-path-review-'+args.case);out.mkdir(exist_ok=False);reports.OUT=out
    source=ROOT/('cloud-cdr-hybrid-path-review-input-'+args.case)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=args.case,accepted=False,full_phy_accepted=False,qualified_pex=False,
        scope='Read-only diagnosis of original failed whole native PD406 wire captures. Original acceptance gates remain failed. No fitted latency, no scaled RC, no synthetic internal waveform or new transient.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['graph_controls']=graph_controls()
        pinfile=ROOT/'docs/evidence/cdr-hybrid-full-wire-rejection-20261018.json';pin=json.loads(pinfile.read_text());case=pin['cases'][args.case]
        selected=['native/wave.dat','composed/composition.json','composed/pd406-mim-wire.spice','planes/native-planes.json']
        prior,proof=reports.restore_report('cdr-hybrid-mim-loaded-'+args.case,pin['run'],case['summary_sha256'],case['parts_sha256'],source,selected)
        assert prior['source_head']==pin['source_head'] and prior['case']==args.case and prior['sources_unchanged']
        assert not prior['data_passed'] and not prior['devices_passed'] and prior['status']=='REJECTED_WHOLE_MIM_PD406_LOADED'
        assert case['report_excerpt']=={k:prior[k]for k in case['report_excerpt']}
        r['native_source']=proof;r['original_status']=prior['status'];save()
        contract=json.loads((source/'composed/composition.json').read_text());planes=json.loads((source/'planes/native-planes.json').read_text())
        text=(source/'composed/pd406-mim-wire.spice').read_text();bound=bind_native(text,contract,planes)
        assert bound==prior['binding'] and contract['counts']==dict(devices=406,R=9970,C=7795)
        logical={}
        for a in planes['anchors']:
            key=(a['native_cluster'],a['native_name']);assert logical.setdefault(key,a['logical_net'])==a['logical_net']
        records={d['instance'].lower():d for d in contract['device_records']}
        for name,dev in bound['groups']['npn13g2'].items():assert dev['native_id']==records[name[4:]]['native_id']
        rows=parser.statements(text);graph=defaultdict(list);parent={};resistors=[];capacitors=[]
        def root(n):
            parent.setdefault(n,n)
            while parent[n]!=n:
                parent[n]=parent[parent[n]];n=parent[n]
            return n
        def join(a,b):parent[root(a)]=root(b)
        for row in rows[1:-1]:
            if row[0][0]not in ('R','C'):continue
            assert len(row)==4
            a,b=row[1].lower(),row[2].lower();value=float(parser.number(row[3]));assert math.isfinite(value)and value>=0
            if row[0].startswith('R'):
                assert value>0
                graph[a].append((b,value));graph[b].append((a,value));join(a,b);resistors.append((row[0],a,b,value))
            else:capacitors.append((row[0],a,b,value))
        assert len(resistors)==9970 and len(capacitors)==7795
        terms=defaultdict(list)
        for dev in records.values():
            for terminal in dev['terminals']:
                if terminal['anchor']is None:continue
                n=terminal['node'].lower();assert n in graph
                terms[root(n)].append(dict(device=dev['instance'],model=dev['model'],terminal=terminal['terminal'],node=n,native_cluster=terminal['native_cluster'],native_net=terminal['native_net']))
        groups={}
        for component,tt in terms.items():
            identities={(t['native_cluster'],t['native_net'])for t in tt};assert len(identities)==1
            key=next(iter(identities));groups[component]=dict(native_cluster=key[0],native_net=key[1],logical_net=logical.get(key),terminals=tt,R_count=0,C_incident_count=0,sum_wire_R_ohm=0.,incident_wire_C_f=0.,internal_wire_C_f=0.,cref_wire_C_f=0.)
        for name,a,b,value in resistors:
            k=root(a);assert root(b)==k
            if k in groups:groups[k]['R_count']+=1;groups[k]['sum_wire_R_ohm']+=value
        for name,a,b,value in capacitors:
            ka,kb=root(a),root(b)
            for k in {ka,kb}&groups.keys():
                g=groups[k];g['C_incident_count']+=1;g['incident_wire_C_f']+=value
                if ka==kb:g['internal_wire_C_f']+=value
                if 'wire_cref'in (a,b):g['cref_wire_C_f']+=value
        for k,g in groups.items():
            if g['logical_net']in (None,'avdd','avss','sub'):continue
            nodes=sorted({t['node']for t in g['terminals']});pairs=[]
            for i,n in enumerate(nodes):
                distance=shortest(graph,n)
                for other in nodes[i+1:]:
                    assert other in distance
                    pairs.append(dict(from_node=n,to_node=other,shortest_resistor_path_ohm=distance[other]))
            g['largest_shortest_resistor_paths']=sorted(pairs,key=lambda x:x['shortest_resistor_path_ohm'],reverse=True)[:5]
        (out/'wire-network-review.json').write_text(json.dumps(dict(conductors=list(groups.values()),native_counts=dict(R=len(resistors),C=len(capacitors)),interpretation='Incident wire capacitance only. Shortest R paths are not effective R or extracted delay.'),indent=2)+'\n')
        r['wire_network_summary']=dict(components_with_device_terminals=len(groups),largest_wire_capacitance_nets=sorted([dict(logical_net=g['logical_net'],native_net=g['native_net'],incident_wire_C_f=g['incident_wire_C_f'],cref_wire_C_f=g['cref_wire_C_f'],R_count=g['R_count'])for g in groups.values()if g['logical_net']not in (None,'avdd','avss','sub')],key=lambda g:g['incident_wire_C_f'],reverse=True)[:20]);save()
        wavepath=source/'native/wave.dat'
        with wavepath.open()as f:header=f.readline().lower().split()
        assert header==['time',*prior['vectors']]
        wave=np.loadtxt(wavepath,skiprows=1);t=wave[:,0]
        assert wave.shape[1]==len(header) and np.isfinite(wave).all()and t[0]==0 and abs(t[-1]-STOP)<1e-15 and np.all(np.diff(t)>0)and np.diff(t).max()<=STEP*1.00001
        r['capture']=dict(rows=len(t),columns=len(header),stop_s=float(t[-1]),max_step_s=float(np.diff(t).max()),sha256=sha(wavepath))
        index={n:i for i,n in enumerate(header)};active=t>=START;ta=t[active]
        external={p:'0'if p in ('avss','sub','wire_cref')else p for p in contract['interface']}
        def global_node(n):return external.get(n,'xpd.'+n.lower())
        def v(n):
            n=bound['aliases'].get(n,n)
            return np.zeros(len(t))if n=='0'else wave[:,index['v('+n+')']]
        def stats(values):
            q=values[active]
            return dict(min_v=float(q.min()),max_v=float(q.max()),mean_v=float(np.trapezoid(q,ta)/(ta[-1]-ta[0])),rms_v=float(np.sqrt(np.mean(q*q))))
        repro={}
        for tag in 'abcd':
            expected=prior['expected_samples'][tag];edges=np.array([START+(i+(0 if tag=='b'else .5))*UI for i in range(1,256)])
            delta=v('xpd.'+tag+'qp')-v('xpd.'+tag+'qn')
            sample_times=(edges[:,None]+np.array([.3,.6,.9])*UI).reshape(-1)
            signed=np.interp(sample_times,t,delta)*np.repeat(np.array(expected)*2-1,3)
            check=prior['sampler_checks'][tag]
            assert int(np.count_nonzero(signed<=0))==check['wrong_sign_samples'] and int(np.count_nonzero(signed<.1))==check['below_100mv_samples'] and abs(float(signed.min())-check['minimum_signed_margin_v'])<1e-12
            repro[tag]=dict(wrong_sign_samples=check['wrong_sign_samples'],below_100mv_samples=check['below_100mv_samples'],minimum_signed_margin_v=float(signed.min()))
        r['original_sampler_reproduction']=repro
        terminal_stats={}
        for name,dev in records.items():
            for term in dev['terminals']:
                node=global_node(term['node']);key=name+':'+term['terminal']
                terminal_stats[key]=dict(node=node,native_cluster=term['native_cluster'],native_net=term['native_net'],logical_net=logical.get((term['native_cluster'],term['native_net'])),voltage=stats(v(node)))
        (out/'terminal-voltage-review.json').write_text(json.dumps(terminal_stats,indent=2)+'\n')
        failed=[];hbts=[]
        for name,dev in records.items():
            if dev['model']!='npn13g2':continue
            ts={z['terminal']:z for z in dev['terminals']};ns={k:global_node(z['node'])for k,z in ts.items()};vc,vb,ve=map(v,[ns['C'],ns['B'],ns['E']])
            old=prior['device_checks']['xpd.'+name];measured=float((vc-ve)[active].min());assert abs(measured-old['minimum_active_vce_v'])<1e-12
            mapping={k:dict(native_cluster=z['native_cluster'],native_net=z['native_net'],logical_net=logical.get((z['native_cluster'],z['native_net'])),node=ns[k])for k,z in ts.items()}
            worst=int(np.flatnonzero(active)[np.argmin((vc-ve)[active])])
            instant=dict(time_s=float(t[worst]),bit_position=float((t[worst]-START)/UI),collector_v=float(vc[worst]),base_v=float(vb[worst]),emitter_v=float(ve[worst]),vce_v=float(vc[worst]-ve[worst]),vbe_v=float(vb[worst]-ve[worst]))
            h=dict(device=name,native_id=dev['native_id'],terminals=mapping,minimum_active_vce_v=measured,minimum_vce_instant=instant,base_voltage=stats(vb),emitter_voltage=stats(ve),collector_voltage=stats(vc));hbts.append(h)
            if measured<.4 or old['maximum_alltime_abs_vce_v']>1.6 or old['maximum_alltime_abs_vbe_v']>1 or old['maximum_alltime_abs_ic_per_emitter_a']>=.003:failed.append(h)
        expected_failed={name for name,old in prior['device_checks'].items()if old['minimum_active_vce_v']<.4 or old['maximum_alltime_abs_vce_v']>1.6 or old['maximum_alltime_abs_vbe_v']>1 or old['maximum_alltime_abs_ic_per_emitter_a']>=.003}
        assert {'xpd.'+x['device']for x in failed}==expected_failed and len(failed)==6
        r['failed_hbt_terminal_review']=failed
        # Actual waveform rail voltages paired with graph paths, without fitting
        # an effective resistance or substituting a DC-only approximation.
        rail_reviews=[]
        for rail in ('avdd','avss'):
            distances=shortest(graph,rail)
            for name,dev in records.items():
                for term in dev['terminals']:
                    if term['native_net']!=rail or term['anchor']is None:continue
                    local=term['node'].lower();assert local in distances
                    key=name+':'+term['terminal']
                    rail_reviews.append(dict(rail=rail,device=name,terminal=term['terminal'],node=local,voltage=terminal_stats[key]['voltage'],voltage_from_external=stats(v(global_node(local))-v(global_node(rail))),shortest_resistor_path_ohm=distances[local]))
        r['supply_terminal_review']=rail_reviews
        pair_reviews=[]
        for i,a in enumerate(hbts):
            for b in hbts[i+1:]:
                aa,bb=a['terminals'],b['terminals']
                if aa['E']['native_cluster']!=bb['E']['native_cluster'] or aa['B']['native_cluster']==bb['B']['native_cluster']:continue
                if aa['E']['logical_net']in ('avss','sub'):continue
                pair_reviews.append(dict(devices=[a['device'],b['device']],base_nets=[aa['B']['logical_net']or aa['B']['native_net'],bb['B']['logical_net']or bb['B']['native_net']],collector_nets=[aa['C']['logical_net']or aa['C']['native_net'],bb['C']['logical_net']or bb['C']['native_net']],base_differential=stats(v(aa['B']['node'])-v(bb['B']['node'])),base_commonmode=stats((v(aa['B']['node'])+v(bb['B']['node']))/2),collector_differential=stats(v(aa['C']['node'])-v(bb['C']['node']))))
        r['native_shared_emitter_pair_review']=pair_reviews
        drops=[]
        for k,g in groups.items():
            if g['logical_net']in (None,'avdd','avss','sub'):continue
            drivers=[z for z in g['terminals']if z['model']=='npn13g2'and z['terminal']=='C']
            sinks=[z for z in g['terminals']if z['model']=='npn13g2'and z['terminal']=='B']
            for a in drivers:
                for b in sinks:
                    if a['device']==b['device']:continue
                    delta=stats(v(global_node(a['node']))-v(global_node(b['node'])))
                    drops.append(dict(logical_net=g['logical_net'],collector=a,base=b,wire_voltage_difference=delta))
        r['collector_to_base_wire_differences']=sorted(drops,key=lambda x:x['wire_voltage_difference']['rms_v'],reverse=True)
        assert all(sha(source/n)==prior['outputs'][n]for n in selected)
        r['sources_unchanged']=True;r['status']='COMPLETE_NATIVE_CDR_HYBRID_PATH_DIAGNOSIS_ORIGINAL_GATES_REMAIN_FAILED'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
