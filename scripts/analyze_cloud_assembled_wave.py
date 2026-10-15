#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Diagnose exact assembled-core native wave failures without changing their oracle."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tarfile
import numpy as np
import networkx as nx
from run_cloud_tx_layout_repair import ROOT, fetch, sha
import run_cloud_tx_mux4 as mux
from analyze_cloud_tx_tree_wave import transition_table
from cloud_tx_stream import read_streamed_wave
from build_pcie_local_vco_hybrid_v6 import statements, number


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--placement-profile',choices=('baseline','compact_vertical','compact_m5_supply'),default='baseline')
    args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    spec=json.loads((ROOT/'docs/evidence/pcie-tree4-assembly-input-20261015.json').read_text())
    selected=spec if args.placement_profile=='baseline' else spec['placement_variants'][args.placement_profile]
    cases=[(s,c) for s in selected['loaded_studies']for c in s['cases']if c['condition']=='hot_low' and c['mode']=='wire' and c['fault']=='none']
    assert len(cases)==1
    study,record=cases[0]
    out=ROOT/'hw/soc/out/cloud-tx-tree-assembly';out.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',placement_profile=args.placement_profile,source_run=study['run'],source=record,
        native_acceptance_changed=False,qualified_pex=False,serial_phy_complete=False)
    try:
        packed=out/'wave-source.tar.gz';fetch(record['url'],record['sha256'],packed)
        assert packed.stat().st_size==record['bytes']
        root='cloud-tx-mux4/'
        geometry=root+'inputs/assembled-core/hw/soc/out/cloud-tx-tree-assembly/'
        wanted={root+'result.json':'original-summary.json',root+'native/contract.json':'native/contract.json',
            root+'native/wave.raw':'native/wave.raw',root+'native/op.dat':'native/op.dat',root+'native/bench.cir':'native/bench.cir',
            **{geometry+n:n for n in ['wire96/tree162-wire01.spice','wire96/anchors08.json','wire96/tree-interface-probes.json','binding96/binding01.json']}}
        found=set()
        with tarfile.open(packed,'r|gz')as tar:
            for entry in tar:
                if entry.name not in wanted:continue
                assert entry.isfile() and entry.name not in found
                target=out/wanted[entry.name];target.parent.mkdir(parents=True,exist_ok=True)
                with tar.extractfile(entry)as src,target.open('xb')as dst:
                    import shutil
                    shutil.copyfileobj(src,dst)
                found.add(entry.name)
        assert found==set(wanted)
        assert sha(out/'original-summary.json')==record['summary_sha256']
        prior=json.loads((out/'original-summary.json').read_text());scope=prior['assembled_core_scope']
        assert scope.get('placement_profile','baseline')==args.placement_profile
        assert scope['source']['sha256']==selected['verified_composition']['sha256']
        for name in ['contract.json','wave.raw','op.dat','bench.cir']:
            assert sha(out/'native'/name)==prior['outputs']['native/'+name]
        for name in ['wire96/tree162-wire01.spice','wire96/tree-interface-probes.json','binding96/binding01.json']:
            assert sha(out/name)==scope['source']['outputs'][name]
        # The anchor JSON was included in the source-bound composition input.
        composition_anchor_key=next(k for k in scope['source']['controls']['inputs'] if k.endswith('/anchors08.json'))
        assert sha(out/'wire96/anchors08.json')==scope['source']['controls']['inputs'][composition_anchor_key]
        contract=json.loads((out/'native/contract.json').read_text())
        assert hashlib.sha256(bytes(contract['bits'])).hexdigest()==record['signals']['source_bits_sha256']
        assert contract['interface_probes']==scope['interface_probes']['modes']['wire']
        fresh=mux.review(out/'native',contract)
        # Re-review also executes the new missing/alias/coverage guards. No
        # approximation, phase fitting or changed pass/fail result is permitted.
        for key in ['signals','interfaces','hbt_devices','mos_devices','failed_hbts','failed_mos','all_engineering_gates_passed']:
            assert fresh[key]==prior['review'][key],key
        t,values,transport=read_streamed_wave(out/'native/wave.raw',contract['vectors'],mux.STOP,contract['condition']['step_ps']*1e-12)
        def v(node):return values['v('+node+')']
        delay=transition_table(t,v('sp')-v('sn'),v('mp')-v('mn'),v('op')-v('on'),contract['bits'])
        failed=[]
        for index,bit in enumerate(contract['bits']):
            for phase in (.3,.5,.7):
                at=mux.START+(index+phase)*mux.UI
                margin=float(np.interp(at,t,v('op')-v('on'))*(2*bit-1))
                if margin>=.1:continue
                branch='a' if index%2==0 else 'b'
                nodes=['sp','sn','mp','mn','op','on',*contract['interface_probes'][branch+'p'],*contract['interface_probes'][branch+'n']]
                failed.append(dict(index=index,bit=bit,previous_bit=contract['bits'][index-1] if index else None,phase=phase,margin_v=margin,
                    transition=next((r for r in delay['events']if r['index']==index),None),
                    trace=[dict(time_s=float(at+dt*1e-12),offset_from_original_sample_ps=dt,
                        volts={n:float(np.interp(at+dt*1e-12,t,v(n)))for n in nodes})for dt in (-10,-5,0,5,10)]))
        assert len(failed)==record['signals']['below_100mv_samples']
        # Read the actual distributed-wire capacitor burden and a physical
        # resistor-path upper bound between stage output and each final base.
        rows=statements((out/'wire96/tree162-wire01.spice').read_text())
        graph=nx.Graph()
        for row in rows[1:-1]:
            if not row[0].startswith('R'):continue
            x,y=row[1:3];res=float(number(row[3]))
            # Parallel edges use conductance addition; the resulting shortest
            # path remains a path bound, NOT a full network effective resistance.
            previous=graph.get_edge_data(x,y,{}).get('resistance')
            graph.add_edge(x,y,resistance=res if previous is None else 1/(1/res+1/previous))
        binding=json.loads((out/'binding96/binding01.json').read_text())
        anchors=json.loads((out/'wire96/anchors08.json').read_text());by={(r['device'],r['terminal']):r for r in anchors['rows']}
        refs=json.loads((out/'wire96/tree-interface-probes.json').read_text())['references']
        intermacro={}
        for label,ref in refs.items():
            net=ref['endpoints'][0]['native_net'];sinks=ref['intrinsic_terminals'];group=nx.node_connected_component(graph,sinks[0]['wire_anchor'])
            candidates=[]
            for d in binding['devices']:
                if d['model']!='rppd' or number(d['parameters']['w'])!=number('4u') or number(d['parameters']['l'])!=number('1.8u'):continue
                for term,native in d['native_nodes'].items():
                    if native==net and term!='rppd_sub':candidates.append(by[d['native_id'],term])
            assert len(candidates)==1
            source=candidates[0]['wire_anchor'];assert source in group
            cap_out=cap_internal=0.;external={}
            for row in rows[1:-1]:
                if not row[0].startswith('C'):continue
                x,y=row[1:3];value=float(number(row[3]));ix,iy=x in group,y in group
                if ix and iy:cap_internal+=value
                elif ix or iy:
                    cap_out+=value;other=y if ix else x;external[other]=external.get(other,0.)+value
            intermacro[label]=dict(native_net=net,source_terminal=candidates[0],sinks=sinks,wire_nodes=len(group),
                external_capacitance_f=cap_out,within_conductor_capacitance_f=cap_internal,
                wire_cref_capacitance_f=external.get('wire_cref',0.),
                path_resistance_upper_bounds_ohm={r['wire_anchor']:nx.shortest_path_length(graph,source,r['wire_anchor'],weight='resistance')for r in sinks},
                qualification='DC resistor path upper bounds and exact exported lumped C totals only; no RF/effective-resistance or substrate qualification.')
        result.update(status='COMPLETE_ASSEMBLED_SOURCE_BOUND_FAILURE_AND_INTERMACRO_DIAGNOSIS_NOT_ACCEPTANCE',
            original_review_preserved=True,failed_samples=failed,transition_delays=delay,intermacro=intermacro,
            fresh_review={k:fresh[k]for k in ['signals','interfaces','failed_hbts','failed_mos','all_engineering_gates_passed']},
            capture={k:transport[k]for k in ['raw_sha256','columns','start_s','end_s','max_step_s','complete_unmodified_rows']})
        packed.unlink()
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()}
        (out/'diagnosis-result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:result[k]for k in ['status','placement_profile']}),flush=True)


if __name__=='__main__':main()
