#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native hot VCE extrema from the exact original full capture; no resimulation."""
import json,os
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-cdr-sampler-headroom-review'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    pin=json.loads((ROOT/'docs/evidence/cdr-sampler-headroom-hot-device-rejection-20261018.json').read_text());p=pin['cases']['hot_low'];original=p['report']
    r=dict(status='RUNNING',accepted=False,full_phy_accepted=False,source_head=os.environ['GITHUB_SHA'],native_run=pin['run'],original_status=original['status'],extrema={})
    try:
        before,proof=reports.restore_report('cdr-sampler-headroom-hot_low',pin['run'],p['summary_sha256'],p['parts_sha256'],OUT/'source',['native/wave.dat','native/bench.cir','native/native.log'])
        assert before==original and original['data_passed']and not original['devices_passed']
        r['source']=proof;path=OUT/'source/native/wave.dat'
        with path.open()as stream:header=stream.readline().lower().split()
        vectors=original['vectors'];assert header==['time',*vectors]
        wave=np.loadtxt(path,skiprows=1);t=wave[:,0]
        assert np.isfinite(wave).all()and wave.shape[1]==len(vectors)+1 and t[0]==0 and abs(t[-1]-34.25e-9)<1e-15 and np.all(np.diff(t)>0)and np.diff(t).max()<=.3125e-12*1.00001
        data={name:wave[:,i+1]for i,name in enumerate(vectors)};active=np.flatnonzero(t>=2e-9)
        def voltage(node):return np.zeros(len(t))if node=='0'else data['v('+node+')']
        for name,device in original['devices'].items():
            vc,vb,ve,vs=map(voltage,device['nodes']);vce=vc-ve;idx=active[np.argmin(vce[active])]
            assert abs(float(vce[idx])-original['device_checks'][name]['minimum_active_vce_v'])<1e-12
            if vce[idx]>=.4:continue
            current=data['@q.'+name+'.qnpn13g2[ic]']
            ids=list(range(max(0,idx-3),min(len(t),idx+4)))
            r['extrema'][name]=dict(device=device,index=int(idx),time_s=float(t[idx]),vce_v=float(vce[idx]),vbe_v=float(vb[idx]-ve[idx]),ic_a=float(current[idx]),sampled_clock_phase_ui=float(((t[idx]-2e-9)/125e-12)%1),native_points=[dict(time_s=float(t[j]),values={n:float(values[j])for n,values in data.items()})for j in ids])
        assert set(r['extrema'])=={'xsamp.xs.xdp','xsamp.xs.xdn','xsamp.xs.xlp','xsamp.xs.xln'}
        r.update(status='COMPLETE_NATIVE_HOT_FOUR_VCE_EXTREMA_REPRODUCED_NOT_ACCEPTANCE',capture_sha256=sha(path),rows=len(t),native_limits_unchanged=True)
    except BaseException as error:r.update(status='FAIL_REVIEW',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
