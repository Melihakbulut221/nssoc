#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read existing complete native startup captures, never resimulate or waive gates."""
import hashlib,json,os,subprocess,tarfile
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cloud_tx_stream import read_streamed_wave
from cloud_tx_step_factorial import wave_difference,STOP
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-startup-wave-diagnosis'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38789786404-1-tree-step-factorial/'

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_run=38789786404,source_head=os.environ['GITHUB_SHA'],
        scope='Read-only waveform diagnosis of existing complete native startup captures. Plot windows and interpolation are diagnostic only. All original inputs, complete raw samples and original1mV/full34ns/bit/device/PVT/physical gates remain unchanged.')
    try:
        summary_path=OUT/'source-summary.json';fetch(BASE+'tx-step-factorial-38789786404-1.summary.json','d5983fd5a49ad2ba603631712505de80cb725a231dfbbadd1fc1b6b142ac3154',summary_path)
        source=json.loads(summary_path.read_text());assert source['study']=='charge_bracket' and not source['accepted']
        packed=OUT/'source.tar.gz';fetch(BASE+'tx-step-factorial-38789786404-1.tar.gz','90394c65cbb5afe8f58f45f9b6d2e6ae7420c1e902ff6a62868f483c17b71d19',packed)
        assert packed.stat().st_size==104696029
        captures={}
        with tarfile.open(packed) as archive:
            for label,row in source['cases'].items():
                if not row['complete']:continue
                name=label+'/wave.raw';raw=archive.extractfile('cloud-tx-step-factorial/'+name).read()
                assert hashlib.sha256(raw).hexdigest()==source['outputs'][name]
                path=OUT/'captures'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
                vectors=row['capture']['logical_vector_order'][1:]
                t,v,receipt=read_streamed_wave(path,vectors,STOP,row['tmax_s'])
                assert receipt==row['capture'];captures[label]=(t,v)
        packed.unlink()
        coarse='tstep0.125-tmax0.125';fine='tstep0.125-tmax0.0625';tc,vc=captures[coarse];tf,vf=captures[fine]
        result['original_pair']=wave_difference(captures[coarse],captures[fine],list(vc))
        assert abs(result['original_pair']['worst_voltage_difference_v']-source['comparisons']['charge14_125_to_62p5']['worst_voltage_difference_v'])<1e-15
        ranking=[]
        for name in vc:
            if not name.startswith('v('):continue
            delta=vc[name]-np.interp(tc,tf,vf[name]);over=np.flatnonzero(abs(delta)>1e-3);peak=int(np.argmax(abs(delta)))
            if not len(over):continue
            start=int(over[0]);around=np.arange(max(0,peak-32),min(len(tc),peak+33));center=float(tc[peak])
            fidx=np.flatnonzero(abs(tf-center)<=5e-12)
            ranking.append(dict(vector=name,first_over_1mv_s=float(tc[start]),peak_s=center,peak_v=float(abs(delta[peak])),
                native_coarse_peak_window={'time_s':tc[around].tolist(),'voltage_v':vc[name][around].tolist(),'delta_v':delta[around].tolist()},
                native_fine_5ps_peak_window={'time_s':tf[fidx].tolist(),'voltage_v':vf[name][fidx].tolist()}))
        ranking.sort(key=lambda x:x['first_over_1mv_s']);result['first_divergence']=ranking
        result['source_drives_differences']={name:result['original_pair']['every_vector'][name] for name in ['v(avdd)','v(dvdd)','v(d0p0)','v(d0n0)']}
        names=['v(mr)','v(xtree.n_i50)','v(clkbias)','v(mp)']
        fig,axes=plt.subplots(4,2,figsize=(14,13),layout='constrained')
        colors=['#2456a6','#d85735','#3a934d','#8a4fa3']
        selected=[coarse,fine,coarse+'-charge16',fine+'-charge19']
        for axrow,name in zip(axes,names):
            diff=result['original_pair']['every_vector'][name];center=diff['time_s']
            for label,color in zip(selected,colors):
                t,v=captures[label];m=(t>=.5e-9)&(t<=1.05e-9)
                axrow[0].plot(t[m]*1e9,v[name][m],color=color,label=label,linewidth=.8)
                m=abs(t-center)<=10e-12
                axrow[1].plot((t[m]-center)*1e12,v[name][m],color=color,linewidth=.9,marker='.',markersize=2)
            axrow[0].set(title=name+' startup',xlabel='time (ns)',ylabel='V')
            axrow[1].set(title=name+f' near worst difference at {center*1e9:.6f} ns',xlabel='offset from peak (ps)',ylabel='V')
            for ax in axrow:ax.grid(alpha=.2)
        axes[0,0].legend(fontsize=6)
        fig.suptitle('Existing native captures: diagnostic windows only; original whole-wave gate remains failed')
        fig.savefig(OUT/'startup-native-comparison.png',dpi=150);plt.close(fig)
        result['window_max_difference_v']=[]
        for start in np.arange(.5e-9,1.2e-9,25e-12):
            m=(tc>=start)&(tc<start+25e-12);assert m.any()
            values={name:float(np.max(abs(vc[name][m]-np.interp(tc[m],tf,vf[name])))) for name in vc if name.startswith('v(')}
            worst=max(values,key=values.get);result['window_max_difference_v'].append(dict(start_s=float(start),end_s=float(start+25e-12),vector=worst,difference_v=values[worst]))
        result['status']='COMPLETE_EXISTING_NATIVE_WAVEFORM_DIAGNOSIS_NOT_ACCEPTANCE'
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'}
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
