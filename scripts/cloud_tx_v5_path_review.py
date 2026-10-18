#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Locate native TX full-wire stage failures without changing or resimulating it."""
import json,os,re
from pathlib import Path
import numpy as np
import cloud_tx_balanced_v5_builder as tree
from cloud_tx_stream import read_streamed_wave
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-v5-path-review'

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,
        scope='Original failed full-wire 32:1 native capture. No new simulation, model edit, phase fit, original-bit substitution or threshold change. Reproduce all original gates before localizing failed stages and HBT headroom.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-v5-full-wire-rejection-20261018.json').read_text())
        source=ROOT/'cloud-tx-v5-path-review-input'
        selected=['native/wave.raw','native/op.dat','native/contract.json','all-interfaces.json']
        prior,proof=reports.restore_report('tx-balanced-v5-wave-wire-nominal-none',pin['run'],pin['summary_sha256'],pin['parts_sha256'],source,selected)
        assert prior['source_head']==pin['source_head']and prior['source_unchanged']and not prior['electrical_screen_passed']
        assert prior['core_counts']==dict(devices=1674,R=116611,C=77471)
        for path in (ROOT/'scripts/cloud_tx_balanced_v5_builder.py',ROOT/'scripts/cloud_tx_stream.py'):
            match=[h for p,h in prior['protected_inputs'].items()if p.endswith('/scripts/'+path.name)]
            assert match==[sha(path)]
        contract=json.loads((source/'native/contract.json').read_text())
        assert contract['streams']==32 and len(contract['hbt'])==604 and len(contract['mos'])==512 and len(contract['interface_probes'])==124
        review=tree.review(source/'native',contract)
        assert review==prior['review'],'Original full waveform engineering gates did not reproduce exactly'
        assert len(review['failed_hbts'])==8 and not review['all_engineering_gates_passed']
        r['native_source']=proof;r['original_gates_reproduced']=True
        r['original_signal_gate']=review['signals'];r['original_interfaces']=review['interfaces'];save()
        t,values,capture=read_streamed_wave(source/'native/wave.raw',contract['vectors'],tree.STOP,contract['condition']['step_ps']*1e-12)
        assert capture==prior['review']['capture_transport']
        r['capture']={k:v for k,v in capture.items()if k!='logical_vector_order'}
        active=t>=tree.START;ta=t[active]
        def v(n):return np.zeros(len(t))if n=='0'else values['v('+n+')']
        def stats(q):
            a=q[active]
            return dict(min_v=float(a.min()),max_v=float(a.max()),mean_v=float(np.trapezoid(a,ta)/(ta[-1]-ta[0])))
        failed=[]
        for name,gate in review['failed_hbts'].items():
            d=contract['hbt'][name];ns=d['terminals'];assert len(ns)==4
            data_roles=[label for label,nodes in contract['interface_probes'].items()if ns[1]in nodes]
            failed.append(dict(device=name,native_binding=d,original_gate=gate,terminal_voltages={label:dict(node=node,voltage=stats(v(node)))for label,node in zip(('C','B','E','S'),ns,strict=True)},physical_data_base_roles=data_roles))
        r['failed_hbt_terminal_review']=failed
        inputs=[];mapping=contract['interface_probes'];labels=sorted({n[:-1]for n in mapping})
        for label in labels:
            if label in ('a','b'):stride,offset=2,0 if label=='a'else 1
            elif label.startswith('d'):stride,offset=32,int(label[1:])
            else:
                match=re.fullmatch(r'p(4|8|16)_(\d+)',label);assert match,label
                stride,offset=map(int,match.groups())
            assert offset<stride
            indices=[i for i in range(256)if i%stride==offset];assert indices
            times=np.array([tree.START+(i+phase)*tree.UI for i in indices for phase in (.3,.5,.7)])
            signs=np.repeat([2*contract['bits'][i]-1 for i in indices],3)
            rows=[]
            for pn in mapping[label+'p']:
                for nn in mapping[label+'n']:
                    vp,vn=v(pn),v(nn);margin=np.interp(times,t,vp-vn)*signs
                    cm=np.interp(times,t,(vp+vn)/2)
                    rows.append(dict(positive_node=pn,negative_node=nn,samples=len(margin),minimum_signed_margin_v=float(margin.min()),wrong_sign_samples=int((margin<=0).sum()),below_150mv_samples=int((margin<.15).sum()),sample_commonmode_range_v=[float(cm.min()),float(cm.max())],active_commonmode=stats((vp+vn)/2),active_differential=stats(vp-vn)))
            inputs.append(dict(label=label,stride=stride,offset=offset,terminal_pairs=rows,total_wrong_sign=sum(x['wrong_sign_samples']for x in rows),minimum_signed_margin_v=min(x['minimum_signed_margin_v']for x in rows)))
        for stride,key in ((2,'final'),(4,'level_4'),(8,'level_8'),(16,'level_16')):
            actual=sum(x['total_wrong_sign']for x in inputs if x['stride']==stride)
            assert actual==review['interfaces'][key]['wrong_sign_samples'],(stride,actual)
        r['physical_input_groups']=sorted(inputs,key=lambda x:(x['minimum_signed_margin_v'],x['label']))
        r['tree_plan']=contract['tree_plan']
        r['clock_references']=contract.get('clock_refs',[])
        r['external_clock_commonmodes']=review['clock_common_mode_range_v']
        (OUT/'all-hbt-terminal-voltages.json').write_text(json.dumps({name:{label:dict(node=node,voltage=stats(v(node)))for label,node in zip(('C','B','E','S'),dev['terminals'],strict=True)}for name,dev in contract['hbt'].items()},indent=2)+'\n')
        assert all(sha(source/n)==prior['outputs'][n]for n in selected)
        r['sources_unchanged']=True;r['status']='COMPLETE_NATIVE_TX_V5_PATH_REVIEW_ORIGINAL_GATES_REMAIN_FAILED'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
