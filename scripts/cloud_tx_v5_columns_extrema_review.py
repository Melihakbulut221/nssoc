#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read actual full native TX capture; locate device extrema without rerunning SPICE."""
import hashlib,json,os
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
from cloud_tx_stream import read_streamed_wave
from cloud_tx_v5_columns_builder import START,STOP,UI
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-v5-columns-extrema-review'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,simulation_rerun=False)
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-v5-columns-native-full-wire-rejection-20261018.json').read_text())
        stage=json.loads((ROOT/'docs/evidence/tx-v5-columns-native-stage-diagnosis-20261018.json').read_text())['report']
        assert len(stage['failed_devices'])==24 and not stage['accepted']
        selected=['native/wave.raw','native/contract.json','native/bench.cir']
        prior,proof=reports.restore_report('tx-v5-columns-wave-wire-nominal-none',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',selected)
        assert prior['status']==pin['status'] and prior['source_head']==pin['source_head'] and prior['review']==pin['review']
        assert not prior['accepted'] and not prior['diagnostics']
        r['source']=proof;r['source_outputs']={p:sha(OUT/'source'/p)for p in selected}
        assert all(v==prior['outputs'][p]for p,v in r['source_outputs'].items())
        contract=json.loads((OUT/'source/native/contract.json').read_text());raw=OUT/'source/native/wave.raw'
        assert START==2e-9 and UI==125e-12 and STOP==START+256*UI
        t,values,transport=read_streamed_wave(raw,contract['vectors'],STOP,contract['condition']['step_ps']*1e-12)
        assert transport==prior['review']['capture_transport'];r['transport']=transport
        active=np.flatnonzero(t>=START);zeros=np.zeros_like(t)
        def volt(node):return zeros if node=='0'else values['v('+node+')']
        measured={};indexes={}
        for name,d in contract['hbt'].items():
            c,b,e,s=(volt(n)for n in d['terminals']);ce=c-e;be=b-e;current=values['@q.'+name+'.qnpn13g2[ic]']/d['nx']
            m=dict(min_post_vce_v=float(ce[active].min()),max_post_vce_v=float(ce[active].max()),max_whole_abs_vce_v=float(abs(ce).max()),max_whole_abs_vbe_v=float(abs(be).max()),max_whole_abs_ic_per_emitter_a=float(abs(current).max()))
            m['passed']=m['min_post_vce_v']>=.4 and m['max_whole_abs_vce_v']<=1.6 and m['max_whole_abs_vbe_v']<=1 and m['max_whole_abs_ic_per_emitter_a']<=.003
            measured[name]=m;indexes[name]=int(active[np.argmin(ce[active])])
        assert len(measured)==604 and measured==prior['review']['hbt_devices']
        failed={n:m for n,m in measured.items()if not m['passed']};assert failed==prior['review']['failed_hbts']
        assert set(failed)=={d['instance']for d in stage['failed_devices']}
        r['all604_original_hbt_metrics_identical']=True;r['failed_devices']=[]
        for d in stage['failed_devices']:
            name=d['instance'];native=contract['hbt'][name];i=indexes[name]
            assert d['measured']==failed[name] and native['nx']==float(d['compact_binding']['parameters']['nx'])
            macro=d['physical_macro'];clock='s'if macro=='f'else's'+macro
            cp,cn=clock+'p',clock+'n';assert 'v('+cp+')'in values and 'v('+cn+')'in values
            public_nodes=list(dict.fromkeys([cp,cn,'avdd','avss',*d['compact_binding']['native_nodes'].values()]))
            public_nodes=[n for n in public_nodes if n=='0'or'v('+n+')'in values]
            def sample(j):
                terminals=dict(zip(('C','B','E','S'),[float(volt(n)[j])for n in native['terminals']],strict=True))
                return dict(row=j,time_s=float(t[j]),terminals_v=terminals,vce_v=terminals['C']-terminals['E'],vbe_v=terminals['B']-terminals['E'],ic_per_emitter_a=float(values['@q.'+name+'.qnpn13g2[ic]'][j]/native['nx']),public_nodes_v={n:float(volt(n)[j])for n in public_nodes},clock_common_mode_v=float((volt(cp)[j]+volt(cn)[j])/2),clock_difference_v=float(volt(cp)[j]-volt(cn)[j]))
            worst=sample(i);assert worst['vce_v']==failed[name]['min_post_vce_v']
            node_stats={n:dict(minimum_v=float(volt(n)[active].min()),median_v=float(np.median(volt(n)[active])),maximum_v=float(volt(n)[active].max()))for n in public_nodes}
            r['failed_devices'].append(dict(instance=name,native_id=d['native_id'],physical_macro=macro,nx=native['nx'],actual_native_terminal_nodes=dict(zip(('C','B','E','S'),native['terminals'],strict=True)),compact_binding=d['compact_binding'],measured=failed[name],minimum_vce_sample=worst,neighbor_samples=[sample(j)for j in range(max(int(active[0]),i-4),min(len(t),i+5))],public_node_poststartup_ranges=node_stats))
        r['clock_common_mode_range_v']=prior['review']['clock_common_mode_range_v']
        r['method_hashes']={p:sha(ROOT/p)for p in ['scripts/cloud_tx_stream.py','scripts/cloud_tx_v5_columns_builder.py',str(Path(__file__).relative_to(ROOT))]}
        assert all(sha(OUT/'source'/p)==v for p,v in r['source_outputs'].items())
        r['source_files_unchanged']=True
        # Only the restored disposable runner copy is removed. The pinned original
        # full wave and release parts remain immutable and available in GitHub.
        del t,values,c,b,e,s,ce,be,current,zeros
        raw.unlink();r['restored_raw_copy_removed_after_full_validation']=True
        r['status']='COMPLETE_NATIVE24_HBT_EXTREMA_WITH_IDENTICAL604_DEVICE_GATES_NOT_ACCEPTANCE'
        print(json.dumps(dict(status=r['status'],devices=[{k:d[k]for k in ('instance','physical_macro','minimum_vce_sample')}for d in r['failed_devices']]),indent=2),flush=True)
    except BaseException as e:r.update(status='FAIL_REVIEW',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
