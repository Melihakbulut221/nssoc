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
    meta=json.loads(subprocess.check_output(['gh','api',P+'actions/artifacts/14170009078']))
    assert meta['workflow_run']['id']==43727364585 and meta['workflow_run']['head_sha']=='ed63d8541533f9823beb2321eddba32c00625843' and not meta['expired']
    producer=json.loads(subprocess.check_output(['gh','api',P+'actions/runs/43727364585']));assert producer['conclusion']=='failure' and producer['run_attempt']==1 and producer['head_sha']==meta['workflow_run']['head_sha']
    archive_sha256='b12f0418e94da9228f4aa349f0b99af3a6aa11d682fbcfa7b4ca9dcce02172ff'
    assert meta['digest']=='sha256:'+archive_sha256
    archive=Path('/tmp/loaded650-native.zip')
    with archive.open('wb') as f:subprocess.run(['gh','api',P+'actions/artifacts/14170009078/zip'],stdout=f,check=True,timeout=1200)
    assert digest(archive)==archive_sha256
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        def unique(s):
            found=[n for n in names if n.endswith(s)];assert len(found)==1,(s,found);return found[0]
        report=json.loads(z.read(unique('derived/loaded-n1-nominal_late.json')))
        assert report['source_head']=='ed63d8541533f9823beb2321eddba32c00625843'
        assert report['sources_unchanged'] and report['returncode']==0 and not report['diagnostics']
        assert report['status']=='REJECTED_WHOLE_MIM_ACTUAL650_LOADED'
        contracts=[n for n in names if n.endswith('.json') and z.getinfo(n).file_size==1509851]
        contracts=[n for n in contracts if hashlib.sha256(z.read(n)).hexdigest()=='6095d786d9ba65d967c7029b0753ef8f4316dcfb463a5aacb801565a90d5fad1']
        assert len(contracts)==1
        contract=json.loads(z.read(contracts[0]));assert contract['physical_devices']==650
        raw=Path('/tmp/loaded650-wave.raw')
        with z.open(unique('native/loaded-n1-nominal_late/wave.raw')) as inp,raw.open('wb') as out:
            import shutil
            shutil.copyfileobj(inp,out,1024*1024)
    assert digest(raw)==report['raw_capture']['raw_sha256']=='c19b5649b288d2024a9c6932bd2750051cb270f52a02751fdf6c1e645e8c61cb'
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
                        data_source_diff_v=float(v('dp')[j]-v('dn')[j]),clock_port_after_buffer_diff_v=float(v('cp')[j]-v('cn')[j]))
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
    # Preserve exact logical/physical identities and first failing native rows.
    devices=contract['devices']; by_id={dev['native_id']:dev for dev in devices}
    assert len(by_id)==650
    rows=sorted(set(rec['native_row'] for values in observations.values() for rec in values['failed_samples'][:3]))
    topology=[]
    for dev in devices:
        if dev['model']!='npn13g2':continue
        name='xpd.'+dev['instances'][0]['name'].lower()
        physical=bound['groups']['npn13g2'][name]
        vc,vb,ve,vs=map(v,physical['nodes'])
        ic=d['@q.'+name+'.qnpn13g2[ic]']
        topology.append(dict(device=name,native_id=dev['native_id'],logical_terminals=dev['logical_terminals'],original_source=dev['original_source'],physical=physical,
            active_ranges_v={key:[float(val[active].min()),float(val[active].max())]for key,val in [('c',vc),('b',vb),('e',ve),('vce',vc-ve)]},
            sample_context=[dict(native_row=j,time_s=float(t[j]),vc_v=float(vc[j]),vb_v=float(vb[j]),ve_v=float(ve[j]),native_model_ic_a=float(ic[j]))for j in rows]))
    assert len(topology)==124
    save('actual-hbt-topology-context.json',topology)
    # Every resistor retains its logical terminals and intrinsic geometry. This
    # maps measured headroom to its real load branch without changing RC.
    save('actual-resistor-topology.json',[dev for dev in devices if dev['model']=='rppd'])
    clock=[]
    for dev in topology:
        logic=dev['logical_terminals']
        if logic.get('B') not in ('cp','cn'):continue
        vb=v(dev['physical']['nodes'][1]);ref=v(logic['B']);other=v('cn' if logic['B']=='cp' else 'cp')
        delta=vb-(ref+other)/2
        expected=1 if logic['B']=='cp' else -1
        events=[]
        # Local base crossing versus ideal source clock edge; report missing
        # crossings rather than adjusting the original sample gates.
        for i in range(8,256):
            edge=START+(i+.5)*UI
            mask=(t>=edge-.1*UI)&(t<=edge+.9*UI);ids=np.flatnonzero(mask)
            directed=delta[ids]*expected
            cross=np.flatnonzero((directed[:-1]<=0)&(directed[1:]>0))
            events.append(dict(bit_index=i,crossings=len(cross),first_crossing_delay_s=None if not len(cross) else float(t[ids[int(cross[0])+1]]-edge)))
        found=[x['first_crossing_delay_s']for x in events if x['first_crossing_delay_s']is not None]
        clock.append(dict(device=dev['device'],logical_terminals=logic,physical_base=dev['physical']['nodes'][1],measured_reference='Local base relative to source clock commonmode; native crossing rows, no interpolation.',missing_crossings=sum(x['crossings']==0 for x in events),minimum_delay_s=min(found)if found else None,maximum_delay_s=max(found)if found else None,events=events))
    save('clock-base-crossings.json',clock)
    from cdr_mos650_full650_loaded import clock as frozen_clock
    drive={}
    for pin,positive in [('clk_inp',True),('clk_inn',False)]:
        pwl=frozen_clock(1.0,positive,False)
        nums=list(map(float,pwl.replace('PWL(','').replace(')','').replace('+','').split()))
        assert len(nums)%2==0
        points=np.array(nums).reshape(-1,2)
        ideal=np.interp(t,points[:,0],points[:,1])
        # Original10ohm sources end at PREBUFFER clk_inp/clk_inn, not cp/cn.
        current=(ideal-v(pin))/10.0
        drive[pin]=dict(original_series_resistance_ohm=10,maximum_active_abs_source_current_a=float(abs(current[active]).max()),
            active_rms_source_current_a=float(np.sqrt(np.trapezoid(current[active]**2,t[active])/(t[active][-1]-t[active][0]))),
            maximum_active_abs_voltage_drop_v=float(abs(ideal[active]-v(pin)[active]).max()),
            analysis='KCL at original10ohm branch before buffer using clk_inp/clk_inn; not buffer output or per-transistor current.')
    truth={}
    for tag,left,right in [('x','a','b'),('y','c','b')]:
        output=v(tag+'p')-v(tag+'n');left_delta=v('xpd.'+left+'qp')-v('xpd.'+left+'qn');right_delta=v('xpd.'+right+'qp')-v('xpd.'+right+'qn')
        table={}
        for i in range(1,256):
            for phase in [.6,.75,.9]:
                at=START+(i+.5+phase)*UI
                lv=float(np.interp(at,t,left_delta));rv=float(np.interp(at,t,right_delta));ov=float(np.interp(at,t,output))
                # Only classify real stable inputs; no relabelling acceptance.
                if abs(lv)<.1 or abs(rv)<.1:continue
                key=str(int(lv>0))+str(int(rv>0));table.setdefault(key,[]).append(ov)
        truth[tag]={key:dict(samples=len(values),minimum_output_diff_v=min(values),maximum_output_diff_v=max(values),mean_output_diff_v=float(np.mean(values)),wrong_xor_sign=sum(value*(1 if key[0]!=key[1] else -1)<=0 for value in values),below_xor_100mv=sum(value*(1 if key[0]!=key[1] else -1)<.1 for value in values))for key,values in table.items()}
    save('clock-source-demand.json',drive)
    save('comparator-observed-input-truth.json',dict(table=truth,scope='Diagnostic actual sampler-input truth table; original ideal-bit acceptance remains unchanged and failed.'))

    save('sampling-localization.json',observations)
    save('device-headroom-localization.json',bad)
    summary=dict(status='PASS_READ_ONLY_BUFFERED_FAILURE_LOCALIZATION',accepted=False,full_phy_accepted=False,
        producer_run=43727364585,producer_head=report['source_head'],artifact=14170009078,artifact_sha256=archive_sha256,
        raw_capture={k:v for k,v in cap.items() if k!='logical_vector_order'},phase_average_v=report['phase_average_v'],phase_gate=report['phase_gate'],
        devices_below_vce_gate=bad,sampling={k:{a:b for a,b in val.items() if a!='failed_samples'} for k,val in observations.items()},
        scope='Read-only failed buffered waveform; source current uses prebuffer nodes. Original sample gates reproduced exactly; nearest native context points separately labelled. No changed circuit, stimuli, timing gates, native simulation or acceptance.')
    assert digest(raw)==cap['raw_sha256']
    assert summary['artifact_sha256']==meta['digest'].removeprefix('sha256:')
    save('result.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('devices_below_vce_gate','sampling','raw_capture')},indent=2))
try:run()
except BaseException:
    save('failure.json',dict(traceback=traceback.format_exc(),accepted=False));raise
