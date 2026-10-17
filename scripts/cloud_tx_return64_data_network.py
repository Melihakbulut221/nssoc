#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Measure original intermacro metal R/C; never substitute a loaded transient."""
import json,os
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
from analyze_cloud_metal_resistance import parse
from cloud_tx_tree32_return_network import sparse_resistance,controls
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-return64-data-network'
MODEL='capture/source/cloud-tx-tree32-return64-assembly/wire96/tree1674-wire01.spice'

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,
        scope='Exact original60intermacro data conductor networks. Native metal R only for unit-current DC solves; original wire C census, semiconductor/parasitic capacitance excluded. No predicted eye, delay, circuit repair or PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-return64-diagnosis-20261017.json').read_text())
        prior,proof=reports.restore_report('tx-return64-diagnosis',pin['source_run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',[MODEL,'capture/all-interfaces.json','capture/native/contract.json'])
        assert prior['status']=='COMPLETE_SOURCE_BOUND_WIRE_FAILURE_DIAGNOSIS_NOT_REPAIR_OR_ACCEPTANCE'
        assert prior['original_review_exactly_reproduced']and not prior['accepted']and not prior['full_phy_accepted']
        assert prior['source_head']==pin['source_head']
        result['source']=proof;result['solver_controls']=controls();save()
        model=OUT/'source'/MODEL
        assert sha(model)==prior['source']['model_sha256']=='acde00f937c0bc576d608b51c079b984b8379900834c01d4cd74d7bfff34200f'
        text=model.read_text().lower();ports,devices,edges=parse(text)
        assert len(devices)==1674 and len(edges)==114909 and ports[-1]=='wire_cref'
        parent={}
        def root(n):
            parent.setdefault(n,n)
            while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
            return n
        for _,a,b,_ in edges:parent[root(a)]=root(b)
        assert 'wire_cref'not in parent
        caps=[];names=set()
        for line in text.splitlines():
            f=line.split()
            if f and f[0].startswith('c'):
                assert len(f)==4 and f[0]not in names and f[1]!=f[2] and 'wire_cref'in f[1:3]
                names.add(f[0]);node=f[1]if f[2]=='wire_cref'else f[2];value=float(f[3])
                assert node in parent and np.isfinite(value)and value>0
                caps.append((f[0],node,value))
        assert len(caps)==76614
        contract=json.loads((OUT/'source/capture/native/contract.json').read_text())
        interfaces=json.loads((OUT/'source/capture/all-interfaces.json').read_text())
        maps=contract['interface_probes'];assert interfaces['modes']['wire']==maps
        result['model_counts']=dict(devices=len(devices),R=len(edges),C=len(caps))
        eg={};cg={}
        for e in edges:eg.setdefault(root(e[1]),[]).append(e)
        for c in caps:cg.setdefault(root(c[1]),[]).append(c)
        measured=[];used=set()
        keys=sorted(k for k in maps if not k.startswith('d'))
        assert len(keys)==60
        for key in keys:
            targets=[n.removeprefix('xtree.').lower()for n in maps[key]]
            assert len(targets)==len(set(targets))==3 and all(n in parent for n in targets)
            comps={root(n)for n in targets};assert len(comps)==1
            component=comps.pop();assert component not in used;used.add(component)
            actual_bases=[(name,dev['nodes'][1])for name,dev in devices.items()if dev['model']=='npn13g2'and root(dev['nodes'][1])==component]
            assert sorted(n for _,n in actual_bases)==sorted(targets)
            contacts=[]
            for name,dev in devices.items():
                if dev['model']!='rppd':continue
                for index,node in enumerate(dev['nodes'][:2]):
                    if root(node)==component:
                        other=dev['nodes'][1-index]
                        contacts.append(dict(device=name,terminal=index,node=node,other_node=other,parameters=dev['parameters'],other_on_avss=root(other)==root('avss')))
            assert len(contacts)==2 and sum(x['other_on_avss']for x in contacts)==1,(key,contacts)
            all_caps=cg[component];total=sum(x[2]for x in all_caps)
            solves=[]
            for contact in contacts:
                m=sparse_resistance(eg[component],contact['node'],targets)
                solves.append(dict(source_native_resistor_terminal=contact,measurement=m))
            base=key[:-1];wave=next(x for x in prior['all62_differential_input_pairs']if x['input']==base)
            measured.append(dict(conductor=key,stage=wave['stage'],native_hbt_bases=actual_bases,native_endpoints=interfaces['references'][key]['endpoints'],
                original_wire_capacitance_f=total,wire_capacitors=len(all_caps),native_resistor_terminal_solves=solves,
                original_pair_wave_result={k:wave[k]for k in ('samples','minimum_margin_v','wrong_sign_samples','below_150mv_samples')},
                largest_native_wire_capacitors=sorted([dict(name=n,node=node,farads=c)for n,node,c in all_caps],key=lambda x:x['farads'],reverse=True)[:12]))
            result['conductors']=measured;save()
        assert len(measured)==len(used)==60
        result['stage_wire_capacitance_f']={stage:dict(conductors=len(rows),minimum=min(x['original_wire_capacitance_f']for x in rows),maximum=max(x['original_wire_capacitance_f']for x in rows),total=sum(x['original_wire_capacitance_f']for x in rows))for stage in sorted({x['stage']for x in measured})for rows in [[x for x in measured if x['stage']==stage]]}
        assert sha(model)==prior['source']['model_sha256']
        result['status']='COMPLETE_SOURCE_BOUND_DATA_METAL_R_C_DIAGNOSIS_NOT_TRANSIENT_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['method_hashes']={str(p.relative_to(ROOT)):sha(p)for p in [Path(__file__),ROOT/'scripts/analyze_cloud_metal_resistance.py',ROOT/'scripts/cloud_tx_tree32_return_network.py',ROOT/'scripts/compare_cloud_routed_endpoints.py']}
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save();print(result['status'],flush=True)
if __name__=='__main__':main()
