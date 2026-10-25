#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Measure actual native retime metal networks without changing intrinsic devices."""
import json,os
from collections import defaultdict
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as parser
from run_cloud_tx_layout_repair import sha
from cloud_cdr_source_access_headroom import rect,owner
from cloud_cdr_xor_v15_retime_chain import latch_graph,latch_graph_faults,retime_input_chain,retime_chain_faults
from review_tx_minimax_data_networks import pair_resistances,controls
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-cdr-v16-retime-passive-networks'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False)
    try:
        r['passive_solver_controls']=controls()
        pin=json.loads((ROOT/'docs/evidence/cdr-retime-data-v16-fullwave-nominal_late-20261020.json').read_text())
        names=['composed/pd484-mim-wire.spice','composed/composition.json','planes/native-planes.json']
        prior,proof=reports.restore_report('cdr-retime-data-v16-mim-streamed-nominal_late',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'wave',names)
        assert prior==pin['report']and prior['sources_unchanged']and prior['returncode']==0 and not prior['diagnostics']
        assert prior['devices_passed']and not prior['data_passed']and prior['status']=='REJECTED_WHOLE_MIM_PD484_LOADED'
        cp=json.loads((ROOT/'docs/evidence/cdr-retime-data-v16-mim-parent-capture-pass-20261020.json').read_text())
        gn=['source/wire/device-locations01.json','source/parent/layout/result.json']
        captured,cproof=reports.restore_report('cdr-retime-data-v16-mim-parent-rc',cp['run'],cp['summary_sha256'],cp['parts_sha256'],OUT/'geometry',gn)
        assert captured==cp['report']and captured['sources_unchanged']
        assert prior['validation_prerequisite']['spec']['capture_summary_sha256']==cp['summary_sha256']
        contract=json.loads((OUT/'wave/composed/composition.json').read_text())
        planes=json.loads((OUT/'wave/planes/native-planes.json').read_text())
        layout=json.loads((OUT/'geometry/source/parent/layout/result.json').read_text())
        locations=json.loads((OUT/'geometry/source/wire/device-locations01.json').read_text())
        assert contract['counts']==dict(devices=484,R=17674,C=12709)
        devices={d['native_id']:d for d in locations['devices']};records={d['native_id']:d for d in contract['device_records']}
        assert len(devices)==484 and devices.keys()==records.keys()
        placements={n:rect(p['bbox_um'])for n,p in layout['placements'].items()};assert len(placements)==16
        owned={}
        for name,dev in prior['devices'].items():
            d=devices[dev['native_id']];card=records[dev['native_id']]
            assert d['model'].lower()==card['model']=='npn13g2'and 'xpd.'+card['instance'].lower()==name
            assert card['parameters']==dev['parameters']
            owned[name]=owner(rect(d['pcell']['bbox']),placements)
        assert len(owned)==116
        logical={}
        for a in planes['anchors']:
            value=(a['native_cluster'],a['native_name']);assert logical.setdefault(a['logical_net'],value)==value
        assert len(logical)==51
        stages={};latch_controls={}
        for tag in 'abcd':
            point=prior['binding']['sampler_points'][tag+'qp']
            matched=[n for n,d in prior['devices'].items()if d['nodes'][0]==point];assert len(matched)==1
            macro=owned[matched[0]];members={n:d for n,d in prior['devices'].items()if owned[n]==macro}
            terms={n:{x['terminal']:x for x in records[d['native_id']]['terminals']}for n,d in members.items()}
            qp=prior['binding']['sampler_points'][tag+'qp'];qn=prior['binding']['sampler_points'][tag+'qn']
            graph=latch_graph(members,terms,qp,qn)
            latch_controls[tag]=latch_graph_faults(members,terms,qp,qn);assert len(latch_controls[tag])==3
            stages[tag]=dict(physical_macro=macro,latches=dict(native_graph=graph))
        owners={i:owner(rect(d['pcell']['bbox']),placements)if records[i]['model']in ('rppd','cap_cmim')else'nonpassive'for i,d in devices.items()}
        path=OUT/'wave/composed/pd484-mim-wire.spice'
        rows=[[v.lower()for v in row]for row in parser.statements(path.read_text())]
        assert rows[0][0]=='.subckt'and rows[-1][0]=='.ends'
        edges=[];caps=[];union=parser.Union()
        for row in rows[1:-1]:
            if row[0].startswith('r'):
                assert len(row)==4;value=float(parser.number(row[3]));assert value>0 and row[1]!=row[2]
                edges.append((row[0],row[1],row[2],value));union.join(row[1],row[2])
            elif row[0].startswith('c'):
                assert len(row)==4;value=float(parser.number(row[3]));assert value>=0
                caps.append((row[0],row[1],row[2],value))
            else:assert row[0].startswith('x')
        assert len(edges)==17674 and len(caps)==12709
        components=defaultdict(list)
        for e in edges:components[union.find(e[1])].append(e)
        assert len(components)==111
        capacitance=defaultdict(lambda:dict(incident_c_f=0.,reference_c_f=0.,internal_c_f=0.,cross_component_c_f=0.))
        for _,a,b,c in caps:
            ra=union.find(a)if a in union.parent else None;rb=union.find(b)if b in union.parent else None
            for root in {ra,rb}-{None}:
                x=capacitance[root];x['incident_c_f']+=c
                key='internal_c_f'if ra==rb else'reference_c_f'if'wire_cref'in(a,b)or'sub'in(a,b)else'cross_component_c_f'
                x[key]+=c
        def node(n):return n.lower().removeprefix('xpd.')
        def segment(label,source,targets):
            source=node(source);targets=[node(n)for n in targets]
            assert source in union.parent and all(n in union.parent for n in targets)
            root=union.find(source);assert all(union.find(n)==root for n in targets)
            return dict(label=label,source=source,targets=targets,physical_component=root,
                wire_resistors=len(components[root]),wire_capacitance=capacitance[root],
                metal_pair_resistances=pair_resistances(components[root],source,targets))
        chains={}
        for tag in ('c','d'):
            graph=retime_input_chain(tag,records,owners,logical,stages)
            faults=retime_chain_faults(tag,records,owners,logical,stages);assert len(faults)==3
            legs={}
            for polarity,leg in graph['legs'].items():
                def terminal(part,side):return leg[part][side]['node']
                paths=[
                    segment('collector_to_retime_filter',leg['source_collector'],[terminal('filter_series','first'),terminal('filter_cap','first')]),
                    segment('filter_output_to_sampler',terminal('filter_series','second'),[terminal('filter_cap','second'),terminal('filter_shunt','first'),terminal('sampler_series','first')]),
                    segment('sampler_series_to_master_base',terminal('sampler_series','second'),[leg['master_base'],terminal('sampler_bias','second')]),
                    segment('avdd_to_sampler_bias','avdd',[terminal('sampler_bias','first')]),
                    segment('avss_to_filter_shunt','avss',[terminal('filter_shunt','second')])]
                legs[polarity]=dict(native_chain=leg,metal_segments=paths)
            chains[tag]=dict(native_graph_faults=faults,legs=legs)
        assert all(sha(OUT/'wave'/n)==prior['outputs'][n]for n in names)
        assert all(sha(OUT/'geometry'/n)==captured['outputs'][n]for n in gn)
        r.update(status='COMPLETE_NATIVE_CDR_RETIME_PASSIVE_NETWORKS_ORIGINAL_SAMPLING_REMAINS_FAILED',
            waveform_source=proof,physical_source=cproof,latch_graph_controls=latch_controls,chains=chains,
            original_rejection_preserved=True,sources_unchanged=True,
            scope='Actual R-only effective resistance and separate wireC on native collector/filter/sampler/rail components. Intrinsic rppd/MIM/HBT models are not linearized or bypassed. No R*C delay, waveform pass, substrate/RF qualification or closed-loop claim. Source fullwave rejection retained; raw waveform not copied for this passive measurement.')
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
