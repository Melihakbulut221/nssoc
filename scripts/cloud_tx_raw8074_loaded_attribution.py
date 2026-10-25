#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Attribute the rejected complete8074 TX capture without modifying any samples."""
import json,os,traceback
from pathlib import Path
from collections import Counter
import numpy as np
import compare_cloud_routed_endpoints as reports
import cloud_tx_p4_drive3_builder as review
from cloud_tx_stream import read_streamed_wave
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-tx-raw8074-loaded-attribution'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],no_new_simulation=True,electrical_accepted=False,full_phy_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        frozen=json.loads((ROOT/'scripts/tx-raw8074-attribution-methods.json').read_text())
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        pin=json.loads((ROOT/'docs/evidence/tx-raw8074-fullwave-rejection-20261021.json').read_text())
        prior,proof=reports.restore_report('tx-raw8074-native-cross-none',39592603205,
          '4278a70c17d52cb5ec0318bfa0d94257fb37e31976c8c3ca6de44cb3df4746cb',
          '89eef11dbc84a1e5a7767e640fba5d51b6341161a45ace94162e2378cdb7d4f9',
          OUT/'source',['work/wave.raw','work/contract.json','work/op.dat'])
        assert prior['status']=='REJECTED_ACTUAL8074_ORIGINAL_LOADED_GATES' and prior['full_capture'] and prior['native_exit_code']==0
        assert prior['sources_unchanged'] and not prior['diagnostics']
        assert prior['review']['signals']==pin['review']['signals']
        case=OUT/'source/work';contract=json.loads((case/'contract.json').read_text())
        actual=review.review(case,contract)
        assert actual==prior['review'],'Original complete-capture/gate reproduction changed'
        result['original_review_reproduced']=True;result['wave_source']=proof
        result['original_rejection']=dict(signals=actual['signals'],interfaces=actual['interfaces'],failed_hbts=len(actual['failed_hbts']),failed_mos=len(actual['failed_mos']))
        ip=json.loads((ROOT/'docs/evidence/tx-raw8074-interfaces-pass-20261021.json').read_text())
        names=['interfaces.json','composed/composition.json','composed/intrinsic/native.json']
        ir,ipr=reports.restore_report('tx-raw8074-interfaces',ip['run'],ip['summary_sha256'],ip['parts_sha256'],OUT/'physical',names)
        assert ir==ip['report'] and ir['sources_unchanged']
        assert all(sha(OUT/'physical'/p)==ir['outputs'][p]for p in names)
        interfaces=json.loads((OUT/'physical/interfaces.json').read_text())
        comp=json.loads((OUT/'physical/composed/composition.json').read_text())
        native=json.loads((OUT/'physical/composed/intrinsic/native.json').read_text())
        assert interfaces['modes']['wire']==contract['interface_probes']
        assert len(comp['device_records'])==8074
        result['interface_source']=ipr
        t,values,transport=read_streamed_wave(case/'wave.raw',contract['vectors'],review.STOP,contract['condition']['step_ps']*1e-12)
        assert transport==actual['capture_transport'];active=t>=review.START
        zeros=np.zeros_like(t)
        def volt(n):
            return zeros if n=='0' else values['v('+n+')']
        def terminal(n):
            return '0' if n.lower() in ('avss','sub','wire_cref') else n.lower() if n.lower() in {p.lower()for p in comp['interface']} else 'xtree.'+n.lower()
        def span(a):
            x=np.asarray(a)[active]
            assert len(x)and np.isfinite(x).all()
            return dict(minimum=float(x.min()),median=float(np.median(x)),maximum=float(x.max()))
        ports={p['name']:p['cluster']for p in native['ports']}
        result['rails']={}
        for rail in ('avdd','avss','dvdd'):
            connected={}
            for d in comp['device_records']:
                for q in d['terminals']:
                    if q['native_cluster']==ports[rail]:
                        connected.setdefault(terminal(q['node']),[]).append(dict(instance=d['instance'],model=d['model'],terminal=q['terminal']))
            assert connected
            external=volt('0'if rail=='avss'else rail)
            rows={}
            for node,devices in connected.items():
                rows[node]=dict(voltage=span(volt(node)),external_minus_local=span(external-volt(node)),devices=devices)
            result['rails'][rail]=dict(terminal_planes=len(rows),lowest=min(rows,key=lambda k:rows[k]['voltage']['minimum']),highest=max(rows,key=lambda k:rows[k]['voltage']['maximum']),planes=rows)
        result['interfaces_by_logical_input']={}
        for group,stride in [('cmos',32),('final',2),('level_4',4),('level_8',8),('level_16',16)]:
            collected={}
            for i,bit in enumerate(contract['bits']):
                prefix=('a'if i%2==0 else'b')if group=='final'else f'd{i%32}'if group=='cmos'else f'p{stride}_{i%stride}'
                row=collected.setdefault(prefix,dict(margins=[],common_modes=[],wrong=[]))
                for phase in (.3,.5,.7):
                    at=review.START+(i+phase)*review.UI
                    for pn in contract['interface_probes'][prefix+'p']:
                        for nn in contract['interface_probes'][prefix+'n']:
                            p,n=(float(np.interp(at,t,volt(v)))for v in (pn,nn))
                            margin=(p-n)*(2*bit-1);row['margins'].append(margin);row['common_modes'].append((p+n)/2)
                            if margin<=0:row['wrong'].append(dict(bit_index=i,phase=phase,time_s=at,pnode=pn,nnode=nn,margin_v=margin))
            summarized={}
            for key,row in collected.items():
                margins=np.array(row['margins']);cm=np.array(row['common_modes'])
                terms=[q for leg in ('p','n')for q in interfaces['references'][key+leg]['terminals']]
                hbts=['xtree.'+q['instance'].lower()for q in terms]
                assert len(hbts)==6 and len(set(hbts))==6 and all(h in contract['hbt']for h in hbts)
                summarized[key]=dict(samples=len(margins),minimum_margin_v=float(margins.min()),wrong_sign_samples=int((margins<=0).sum()),
                    below_150mv_samples=int((margins<.15).sum()),common_mode_range_v=[float(cm.min()),float(cm.max())],
                    below_1v8_samples=int((cm<1.8).sum()),above_2v05_samples=int((cm>2.05).sum()),
                    actual_data_hbts=hbts,failed_data_hbts={h:actual['failed_hbts'][h]for h in hbts if h in actual['failed_hbts']},
                    wrong_samples=row['wrong'])
            assert sum(v['samples']for v in summarized.values())==actual['interfaces'][group]['samples']==6912
            assert sum(v['wrong_sign_samples']for v in summarized.values())==actual['interfaces'][group]['wrong_sign_samples']
            result['interfaces_by_logical_input'][group]=summarized
        result['hbt_failure_modes']=dict(below_original_vce_floor=sum(v['min_post_vce_v']<.4 for v in actual['hbt_devices'].values()),
            above_original_vce_ceiling=sum(v['max_whole_abs_vce_v']>1.6 for v in actual['hbt_devices'].values()),
            above_original_vbe_ceiling=sum(v['max_whole_abs_vbe_v']>1 for v in actual['hbt_devices'].values()),
            above_original_current_ceiling=sum(v['max_whole_abs_ic_per_emitter_a']>.003 for v in actual['hbt_devices'].values()))
        result['failed_hbts']=actual['failed_hbts']
        assert sha(case/'wave.raw')==actual['capture_transport']['raw_sha256']
        result['observed_raw']={k:v for k,v in actual['capture_transport'].items() if k!='logical_vector_order'}
        result['capture_retention']='Complete original raw remains in immutable39592603205 release; delete only this observer temporary restored copy after reproducing all original checks.'
        (case/'wave.raw').unlink()
        assert all(sha(ROOT/p)==h for p,h in frozen.items())
        result.update(status='ATTRIBUTED_REJECTED_FULL8074_NATIVE_WAVE_TO_ACTUAL_RAIL_AND_INPUT_PLANES_NOT_REPAIR_OR_ACCEPTANCE',sources_unchanged=True,
          next_action='Use measured local rail/common-mode/physical input failures to select a real circuit or routing correction; do not shift the original bit oracle or weaken bounds.')
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
        print(json.dumps({k:result.get(k)for k in ('status','error','original_review_reproduced','hbt_failure_modes')}),flush=True)
if __name__=='__main__':main()
