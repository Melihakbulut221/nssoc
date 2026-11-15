# SPDX-License-Identifier: Apache-2.0
"""Read-only localization of authenticated failed native loaded650 capture."""
import json, subprocess, zipfile, hashlib, traceback
from pathlib import Path
import numpy as np
from cdr_mos650_full650_loaded import read_streamed_wave, STOP, STEP, START, UI
P='repos/Melihakbulut221/nssoc/'
OUT=Path('loaded650-localization'); OUT.mkdir(exist_ok=True)
def digest(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(name,obj): (OUT/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def run():
    meta=json.loads(subprocess.check_output(['gh','api',P+'actions/artifacts/14158082074']))
    assert meta['workflow_run']['id']==43697553951 and not meta['expired']
    expected='1f6167012365bc7bffcc85bad084d0824021ec6d1c963d1dc3a5537f22b114c3'
    assert meta['digest']=='sha256:'+expected
    archive=Path('/tmp/loaded650-native.zip')
    with archive.open('wb') as f:subprocess.run(['gh','api',P+'actions/artifacts/14158082074/zip'],stdout=f,check=True,timeout=1200)
    assert digest(archive)==expected
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        def unique(s):
            found=[n for n in names if n.endswith(s)];assert len(found)==1,(s,found);return found[0]
        report=json.loads(z.read(unique('derived/loaded-n1-nominal_late.json')))
        assert report['source_head']=='30d59883a29c0c64f5855884a26aeb39783900ae'
        assert report['sources_unchanged'] and report['returncode']==0 and not report['diagnostics']
        assert report['status']=='REJECTED_WHOLE_MIM_ACTUAL650_LOADED'
        raw=Path('/tmp/loaded650-wave.raw')
        with z.open(unique('native/loaded-n1-nominal_late/wave.raw')) as inp,raw.open('wb') as out:
            import shutil
            shutil.copyfileobj(inp,out,1024*1024)
    assert digest(raw)==report['raw_capture']['raw_sha256']=='fb95656a71a54217d4b7215571b5d8ac48513d0f17fd8736dd526b744125aa3a'
    t,d,cap=read_streamed_wave(raw,report['vectors'],STOP,STEP)
    bound=report['binding']; aliases=bound['aliases']; active=t>=START
    def v(n):
        n=aliases.get(n,n);return np.zeros(len(t)) if n=='0' else d['v('+n+')']
    observations={}
    for tag in 'abcdxy':
        sampler=tag in 'abcd'
        pos,neg=('xpd.'+tag+'qp','xpd.'+tag+'qn') if sampler else (tag+'p',tag+'n')
        delta=v(pos)-v(neg)
        bits=report['expected_samples'][tag] if sampler else report['expected_comparisons'][tag]
        phases=(.3,.6,.9) if sampler else (.6,.75,.9)
        records=[];wrong=0;below=0;minimum=1e9
        for i,bit in enumerate(bits,1):
            edge=START+(i+(0 if tag=='b' else .5))*UI
            for phase in phases:
                at=edge+phase*UI;signed=float(np.interp(at,t,delta))*(2*bit-1)
                wrong+=signed<=0;below+=signed<.1;minimum=min(minimum,signed)
                if signed<.1:
                    j=int(np.searchsorted(t,at));assert j<len(t)
                    rec=dict(bit_index=i,expected=bit,phase_ui=phase,query_time_s=at,native_row=j,native_time_s=float(t[j]),signed_margin_v=signed,
                        previous_input=report['source_bits'][i-1],current_input=report['source_bits'][i],
                        data_source_diff_v=float(v('dp')[j]-v('dn')[j]),clock_source_diff_v=float(v('cp')[j]-v('cn')[j]))
                    for name,p,n in [('data_a','xpd.adp','xpd.adn'),('data_c','xpd.cdp','xpd.cdn'),('select0','xpd.s0p','xpd.s0n'),('select1','xpd.s1p','xpd.s1n')]:
                        rec[name+'_diff_v']=float(v(p)[j]-v(n)[j])
                    records.append(rec)
        prior=report['sampler_checks' if sampler else 'comparisons'][tag]
        assert wrong==prior['wrong_sign_samples'] and below==prior['below_100mv_samples']
        assert abs(minimum-prior['minimum_signed_margin_v'])<1e-12
        grouped={}
        for rec in records:
            key=str(rec['previous_input'])+str(rec['current_input'])
            grouped[key]=grouped.get(key,0)+1
        observations[tag]=dict(wrong_sign_samples=wrong,below_100mv_samples=below,minimum_signed_margin_v=minimum,failed_samples_by_transition=grouped,failed_samples=records)
    bad=[]
    for name,dev in bound['groups']['npn13g2'].items():
        vc,vb,ve,_=map(v,dev['nodes']);vce=vc-ve;ids=np.flatnonzero(active&(vce<.4))
        if len(ids):
            j=int(ids[np.argmin(vce[ids])]);bad.append(dict(device=name,nodes=dev['nodes'],minimum_active_vce_v=float(vce[j]),time_s=float(t[j]),native_row=j,violating_rows=len(ids),vc_v=float(vc[j]),vb_v=float(vb[j]),ve_v=float(ve[j]),native_model_ic_a=float(d['@q.'+name+'.qnpn13g2[ic]'][j]),note='Native model ic is not asserted to be full terminal current.'))
    save('sampling-localization.json',observations)
    save('device-headroom-localization.json',bad)
    summary=dict(status='PASS_READ_ONLY_FAILURE_LOCALIZATION',accepted=False,full_phy_accepted=False,
        producer_run=43697553951,producer_head=report['source_head'],artifact=14158082074,artifact_sha256=expected,
        raw_capture={k:v for k,v in cap.items() if k!='logical_vector_order'},phase_average_v=report['phase_average_v'],phase_gate=report['phase_gate'],
        devices_below_vce_gate=bad,sampling={k:{a:b for a,b in val.items() if a!='failed_samples'} for k,val in observations.items()},
        scope='Read-only original failed waveform. Original sample gates reproduced exactly; nearest native context points separately labelled. No changed circuit, stimuli, timing gates, native simulation or acceptance.')
    assert digest(raw)==cap['raw_sha256']
    save('result.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('devices_below_vce_gate','sampling','raw_capture')},indent=2))
try:run()
except BaseException:
    save('failure.json',dict(traceback=traceback.format_exc(),accepted=False));raise
