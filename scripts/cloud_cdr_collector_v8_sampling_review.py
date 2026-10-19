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
from cloud_cdr_collector_v8_mim_streamed import bind_native,START,STOP,STEP,UI
from cloud_tx_stream import read_streamed_wave
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
    out=ROOT/('cloud-cdr-collector-v8-sampling-review-'+args.case);out.mkdir(exist_ok=False);reports.OUT=out
    source=ROOT/('cloud-cdr-collector-v8-sampling-review-input-'+args.case)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=args.case,accepted=False,full_phy_accepted=False,qualified_pex=False,
        scope='Read-only diagnosis of original failed whole native PD484 wire captures. Original acceptance gates remain failed. No fitted latency, no scaled RC, no synthetic internal waveform or new transient.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['graph_controls']=graph_controls()
        pinfile=ROOT/'docs/evidence/cdr-collector-v8-streamed-native-input-20261019.json';pin=json.loads(pinfile.read_text());case=pin['cases'][args.case]
        selected=['native/wave.raw','composed/composition.json','composed/pd484-mim-wire.spice','planes/native-planes.json']
        prior,proof=reports.restore_report('cdr-collector-v8-mim-streamed-'+args.case,pin['run'],case['summary_sha256'],case['parts_sha256'],source,selected)
        assert prior['source_head']==pin['source_head'] and prior['case']==args.case and prior['sources_unchanged']
        assert not prior['data_passed'] and not prior['devices_passed'] and prior['status']=='REJECTED_WHOLE_MIM_PD484_LOADED'
        assert case['report']==prior
        r['native_source']=proof;r['original_status']=prior['status'];save()
        contract=json.loads((source/'composed/composition.json').read_text());planes=json.loads((source/'planes/native-planes.json').read_text())
        text=(source/'composed/pd484-mim-wire.spice').read_text();bound=bind_native(text,contract,planes)
        assert bound==prior['binding'] and contract['counts']==dict(devices=484,R=15490,C=11535)
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
        assert len(resistors)==15490 and len(capacitors)==11535
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
        wavepath=source/'native/wave.raw'
        t,values,capture=read_streamed_wave(wavepath,prior['vectors'],STOP,STEP)
        assert capture==prior['raw_capture']
        r['capture']=capture;active=t>=START;ta=t[active]
        external={p:'0'if p in ('avss','sub','wire_cref')else p for p in contract['interface']}
        def global_node(n):return external.get(n,'xpd.'+n.lower())
        def v(n):
            n=bound['aliases'].get(n,n)
            return np.zeros(len(t))if n=='0'else values['v('+n+')']
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
        # Preserve the original three sampling phases. Resolve the actual native
        # data-pair bases through the same collector witnesses; never fit latency.
        sampling={};phase_summary={}
        expected_bases={'a':('dp','dn'),'b':('dp','dn'),'c':('cup','cun'),'d':('dup','dun')}
        for tag in 'abcd':
            positive=records[bound['probe_witnesses'][tag+'qn']['device']]
            negative=records[bound['probe_witnesses'][tag+'qp']['device']]
            pt={z['terminal']:z for z in positive['terminals']};nt={z['terminal']:z for z in negative['terminals']}
            assert pt['E']['native_cluster']==nt['E']['native_cluster']
            nets=tuple(logical[(z['native_cluster'],z['native_net'])]for z in (pt['B'],nt['B']))
            assert nets==expected_bases[tag],(tag,nets)
            nodes=[global_node(z['node'])for z in (pt['B'],nt['B'])]
            input_delta=v(nodes[0])-v(nodes[1]);output_delta=v('xpd.'+tag+'qp')-v('xpd.'+tag+'qn')
            expected=np.array(prior['expected_samples'][tag]);sign=expected*2-1
            edges=START+(np.arange(1,256)+(0 if tag=='b'else .5))*UI
            phases={};records_by_phase={}
            for phase in (.3,.6,.9):
                times=edges+phase*UI;output=np.interp(times,t,output_delta)*sign
                phases[str(phase)]=dict(samples=255,wrong_sign_samples=int(np.count_nonzero(output<=0)),below_100mv_samples=int(np.count_nonzero(output<.1)),minimum_signed_margin_v=float(output.min()))
                records_by_phase[str(phase)]=dict(time_s=times.tolist(),signed_output_v=output.tolist())
            assert sum(z['wrong_sign_samples']for z in phases.values())==repro[tag]['wrong_sign_samples']
            assert sum(z['below_100mv_samples']for z in phases.values())==repro[tag]['below_100mv_samples']
            assert abs(min(z['minimum_signed_margin_v']for z in phases.values())-repro[tag]['minimum_signed_margin_v'])<1e-12
            inputs={}
            for phase in (-.1,0.,.1,.2,.3,.6,.9):
                times=edges+phase*UI;di=np.interp(times,t,input_delta);cm=np.interp(times,t,(v(nodes[0])+v(nodes[1]))/2)
                inputs[str(phase)]=dict(time_s=times.tolist(),differential_v=di.tolist(),commonmode_v=cm.tolist(),signed_against_original_expected_v=(di*sign).tolist())
            sampling[tag]=dict(actual_native_input_devices=[positive['instance'],negative['instance']],actual_native_base_nodes=nodes,logical_base_nets=list(nets),expected_bits=expected.tolist(),output=records_by_phase,inputs=inputs)
            phase_summary[tag]=dict(output_at_original_phases=phases,input_at_nominal_edge=dict(minimum_signed_v=float(min(inputs['0.0']['signed_against_original_expected_v'])),different_sign_count=sum(x<=0 for x in inputs['0.0']['signed_against_original_expected_v'])))
        r['fixed_sampling_phase_review']=phase_summary
        (out/'fixed-sampling-review.json').write_text(json.dumps(dict(samples=sampling,interpretation='Read-only native terminal samples at fixed original edges/phases. Input signs outside acquisition are diagnostic only, not a new acceptance gate. No changed latency, stimulus, threshold or original rejection.'),indent=2)+'\n')
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
            current=values['@q.xpd.'+name+'.qnpn13g2[ic]'];nx=float(parser.number(dev['parameters']['nx']))
            peak_ic=float(abs(current).max()/nx);assert abs(peak_ic-old['maximum_alltime_abs_ic_per_emitter_a'])<1e-15
            assert abs(float(abs(vc-ve).max())-old['maximum_alltime_abs_vce_v'])<1e-12
            assert abs(float(abs(vb-ve).max())-old['maximum_alltime_abs_vbe_v'])<1e-12
            mapping={k:dict(native_cluster=z['native_cluster'],native_net=z['native_net'],logical_net=logical.get((z['native_cluster'],z['native_net'])),node=ns[k])for k,z in ts.items()}
            worst=int(np.flatnonzero(active)[np.argmin((vc-ve)[active])])
            instant=dict(time_s=float(t[worst]),bit_position=float((t[worst]-START)/UI),collector_v=float(vc[worst]),base_v=float(vb[worst]),emitter_v=float(ve[worst]),vce_v=float(vc[worst]-ve[worst]),vbe_v=float(vb[worst]-ve[worst]))
            h=dict(device=name,native_id=dev['native_id'],terminals=mapping,minimum_active_vce_v=measured,maximum_alltime_abs_ic_per_emitter_a=peak_ic,current_at_minimum_vce_a=float(current[worst]),minimum_vce_instant=instant,base_voltage=stats(vb),emitter_voltage=stats(ve),collector_voltage=stats(vc));hbts.append(h)
            if measured<.4 or old['maximum_alltime_abs_vce_v']>1.6 or old['maximum_alltime_abs_vbe_v']>1 or old['maximum_alltime_abs_ic_per_emitter_a']>=.003:failed.append(h)
        expected_failed={name for name,old in prior['device_checks'].items()if old['minimum_active_vce_v']<.4 or old['maximum_alltime_abs_vce_v']>1.6 or old['maximum_alltime_abs_vbe_v']>1 or old['maximum_alltime_abs_ic_per_emitter_a']>=.003}
        assert {'xpd.'+x['device']for x in failed}==expected_failed and len(failed)>0
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
        clock_reviews=[]
        reference=v('cp')-v('cn')
        for i,a in enumerate(hbts):
            for b in hbts[i+1:]:
                aa,bb=a['terminals'],b['terminals'];nets={aa['B']['logical_net'],bb['B']['logical_net']}
                if aa['E']['native_cluster']!=bb['E']['native_cluster']or nets not in ({'cp','cn'},{'s0p','s0n'},{'s1p','s1n'}):continue
                plus,minus=(aa,bb)if aa['B']['logical_net'].endswith('p')else(bb,aa)
                delta=v(plus['B']['node'])-v(minus['B']['node']);cross=np.flatnonzero(np.signbit(delta[:-1])!=np.signbit(delta[1:]));crossings=[]
                for index in cross:
                    when=float(t[index]-delta[index]*(t[index+1]-t[index])/(delta[index+1]-delta[index]))
                    if when>=START:crossings.append(dict(time_s=when,rising=bool(delta[index+1]>delta[index])))
                phases={}
                for phase in (0.,.1,.25,.4,.5,.6,.75,.9):
                    times=START+(np.arange(1,256)+phase)*UI;local=np.interp(times,t,delta);reference_samples=np.interp(times,t,reference)
                    phases[str(phase)]=dict(min_v=float(local.min()),max_v=float(local.max()),mean_v=float(local.mean()),external_min_v=float(reference_samples.min()),external_max_v=float(reference_samples.max()),different_sign_samples=int(np.count_nonzero(np.signbit(local)!=np.signbit(reference_samples))))
                clock_reviews.append(dict(devices=[a['device'],b['device']],positive_base=plus['B'],negative_base=minus['B'],differential=stats(delta),first16_zero_crossings=crossings[:16],active_zero_crossing_count=len(crossings),fixed_UI_phase_samples=phases))
        assert clock_reviews
        r['clock_distribution_review']=dict(pairs=clock_reviews,interpretation='Actual native base voltages at fixed original source-clock phases. Zero crossings are listed without fitting or shifting any acceptance window; no new acceptance claim.')
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
        # Separate the measured intrinsic load drop from the actual wire drop
        # to each collector. No DC current approximation or adjusted sampling.
        load_reviews=[];load_ids=[]
        for name,dev in records.items():
            if dev['model']!='rppd':continue
            if parser.number(dev['parameters']['w'])!=parser.number('32u') or parser.number(dev['parameters']['l'])!=parser.number('2.12u'):continue
            ts={z['terminal']:z for z in dev['terminals']};a=ts['rppd_1'];b=ts['rppd_2']
            assert a['native_net']=='avdd'
            sinks=[q for q in hbts if q['terminals']['C']['native_cluster']==b['native_cluster'] and q['terminals']['C']['native_net']==b['native_net']]
            assert len(sinks)==2
            load_ids.append(name)
            va,vb=v(global_node(a['node'])),v(global_node(b['node']))
            for q in sinks:
                vc=v(q['terminals']['C']['node'])
                load_reviews.append(dict(load=name,collector=q['device'],native_net=b['native_net'],logical_net=logical.get((b['native_cluster'],b['native_net'])),native_parameters=dev['parameters'],supply_wire_drop=stats(v('avdd')-va),intrinsic_load_drop=stats(va-vb),load_to_collector_wire_drop=stats(vb-vc),total_external_to_collector_drop=stats(v('avdd')-vc)))
        assert len(load_ids)==16 and len(set(load_ids))==16 and len(load_reviews)==32
        r['sampler_load_and_collector_wire_drop_review']=load_reviews
        assert all(sha(source/n)==prior['outputs'][n]for n in selected)
        r['sources_unchanged']=True;r['status']='COMPLETE_NATIVE_CDR_HYBRID_PATH_DIAGNOSIS_ORIGINAL_GATES_REMAIN_FAILED'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
