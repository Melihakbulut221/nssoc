#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual native half-cycle cascade before three-sample phase detection."""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import cloud_cdr_xor as primitive
import cloud_pll_pump_current as pump
from cloud_vbic_tree32_backend import backend_readback,readback_controls
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hw/soc/analog/pcie/rx_sampler_hbt_v2.spice'
SOURCE_SHA='2540014752d39b9cafceb81caf5c95b8be5bda947b8c1f14272940cf1aa4341f'
WRAPPER=ROOT/'hw/soc/analog/pcie/cdr_halfcycle_retime_v1.spice'
WRAPPER_SHA='d1e16573ce5b0ea30a8c37d13fe60867eee13310027e2247e2a2e09776635e52'
UI=125e-12;START=2e-9;STOP=START+258*UI;STEP=.3125e-12

def bind(text,output):
    sub={};current=None
    for line in text.lower().splitlines():
        f=line.split()
        if not f or f[0].startswith('*'):continue
        if f[0]=='.subckt':
            assert current is None and f[1]not in sub
            current=f[1];sub[current]=dict(ports=f[2:],rows=[])
        elif f[0]=='.ends':assert current==f[1];current=None
        else:assert current is not None;sub[current]['rows'].append(f)
    assert current is None and set(sub)=={'nssoc_cml_latch','nssoc_rx_sampler_hbt'}
    devices={};resistors={}
    def visit(top,path,ports,stack):
        assert top not in stack
        unit=sub[top];mapping=dict(zip(unit['ports'],ports,strict=True));seen=set()
        def node(n):return mapping.get(n,path+'.'+n)
        for f in unit['rows']:
            assert f[0].startswith('x')and f[0]not in seen;seen.add(f[0]);name=path+'.'+f[0]
            if len(f)>5 and f[5]=='npn13g2':
                assert name not in devices;params=dict(x.split('=')for x in f[6:]);assert params.keys()=={'nx'}
                devices[name]=dict(nodes=[node(n)for n in f[1:5]],nx=int(params['nx']))
            elif len(f)>4 and f[4]=='rppd':resistors[name]=dict(nodes=[node(n)for n in f[1:4]],parameters=f[5:])
            else:
                assert f[-1]in sub;visit(f[-1],name,[node(n)for n in f[1:-1]],stack+[top])
    visit('nssoc_rx_sampler_hbt','xsamp',['dp','dn',*output,'cp','cn','avdd','0','0','iref'],[])
    assert len(devices)==15 and len(resistors)==12
    assert sum(x['nx']for x in devices.values())==41
    assert set(devices)=={'xsamp.xref'}|{'xsamp.x'+stage+'.x'+name for stage in ('m','s')for name in ('dp','dn','lp','ln','cs','ch','t')}
    return devices,resistors

def pwl(points):
    assert all(a[0]<b[0]for a,b in zip(points,points[1:]))
    return 'PWL(\n+ '+'\n+ '.join(f'{t:.14g} {v:.14g}'for t,v in points)+')'

def data(bits,cm,amp):
    val=lambda b:cm+amp*(1 if b else-1)
    points=[(0,0),(.5e-9,val(bits[0]))]
    for i in range(1,256):
        if bits[i]!=bits[i-1]:points.extend([(START+i*UI,val(bits[i-1])),(START+i*UI+5e-12,val(bits[i]))])
    points.append((STOP,val(bits[-1])));return pwl(points)

def clock(scale,positive,stopped):
    low=(1.29-.15)*scale;high=(1.29+.15)*scale
    if not positive:low,high=high,low
    points=[(0,0),(.5e-9,low)];current=low
    if not stopped:
        for i in range(258):
            for at,new in [(START+(i+.5)*UI,high),(START+(i+1)*UI,low)]:
                if at+2.5e-12>=STOP:continue
                points.extend([(at-2.5e-12,current),(at+2.5e-12,new)]);current=new
    points.append((STOP,current));return pwl(points)

def main():
    p=argparse.ArgumentParser();p.add_argument('--case',choices=['nominal','hot_low','cold_high','swap_output','clock_stopped','wrong_edge'],required=True);args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/('cloud-cdr-halfcycle-retime-'+args.case);out.mkdir(exist_ok=False);reports.OUT=out
    c=pump.CORNERS[args.case if args.case in ('nominal','hot_low','cold_high')else'nominal'];scale=c['scale']
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=args.case,accepted=False,cdr_accepted=False,full_phy_accepted=False,physical_layout_matches=False,
        scope='Actual two-sampler half-cycle cascade:30HBT/28nativeR/2nativeMIM. First sampler rising-edge; second physically connected to first and falling-edge. External8GHz clock,10ohmsources,500uA per sampler,150fF on all four outputs.256original bits and clean native startup. No ideal internal bit regeneration. Not phase detector, closed-loop recovery or physical/x4PHY acceptance.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        assert sha(SOURCE)==SOURCE_SHA and sha(WRAPPER)==WRAPPER_SHA
        assert sha(ROOT/'scripts/cloud_cdr_xor.py')=='3ec870fa6a30d9f94038368d6b74c984c314c2d7248ecaab94c687867587fabe'
        r['readback_controls']=readback_controls()
        fetch(pump.BASE+'cloud-results-39029337682-1-pll-pump-current/pll-pump-current-39029337682-1.summary.json',primitive.SUMMARY,out/'models-pin.json')
        pin=json.loads((out/'models-pin.json').read_text());wanted=[n for n in pin['outputs']if n.startswith('source/model-sources/')]+['source-pin.json','source/runtime/patched-ngspice']
        old,proof=reports.restore_report('pll-pump-current',39029337682,primitive.SUMMARY,primitive.PARTS,out/'source',wanted);assert old==pin;r['models_source']=proof
        original=json.loads((out/'source/source-pin.json').read_text());assert sha(out/'source/source-pin.json')==pump.SUMMARY
        lib=out/'models';shutil.copytree(out/'source/source/model-sources',lib)
        assert all(sha(lib/p)==d for p,d in original['preparation']['model_sources'].items())
        engine=out/'source/source/runtime/patched-ngspice';engine.chmod(0o755);assert sha(engine)=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
        output=('qn','qp')if args.case=='swap_output'else('qp','qn')
        wrapper=WRAPPER.read_text()
        rows=[l.lower().split()for l in wrapper.splitlines()if l and not l.startswith('*')]
        assert rows[0]==['.subckt','nssoc_cdr_halfcycle_retime_v1','dp','dn','cp','cn','qp','qn','avdd','avss','sub','ira','irb']
        assert next(f for f in rows if f[0]=='xsa')==['xsa','dp','dn','aqp','aqn','cp','cn','avdd','avss','sub','ira','nssoc_rx_sampler_hbt']
        assert next(f for f in rows if f[0]=='xsb')==['xsb','udp','udn','qp','qn','cn','cp','avdd','avss','sub','irb','nssoc_rx_sampler_hbt']
        if args.case=='wrong_edge':
            old='XSB udp udn qp qn cn cp';assert wrapper.count(old)==1
            wrapper=wrapper.replace(old,'XSB udp udn qp qn cp cn')
        actual_wrapper=out/'actual-wrapper.spice';actual_wrapper.write_text(wrapper)
        devices={};resistors={}
        original_devices,original_resistors=bind(SOURCE.read_text(),('qp','qn'))
        for stage in ('a','b'):
            mapping=(dict(dp='dp',dn='dn',qp='xchain.aqp',qn='xchain.aqn',cp='cp',cn='cn',iref='ira')if stage=='a'else
                dict(dp='xchain.udp',dn='xchain.udn',qp=output[0],qn=output[1],cp='cp'if args.case=='wrong_edge'else'cn',cn='cn'if args.case=='wrong_edge'else'cp',iref='irb'))
            def mapped(n):return mapping.get(n,n.replace('xsamp.','xchain.xs'+stage+'.'))
            for name,d in original_devices.items():devices[name.replace('xsamp.','xchain.xs'+stage+'.')]=dict(nodes=[mapped(n)for n in d['nodes']],nx=d['nx'])
            for name,d in original_resistors.items():resistors[name.replace('xsamp.','xchain.xs'+stage+'.')]=dict(nodes=[mapped(n)for n in d['nodes']],parameters=d['parameters'])
        conversion=[f for f in rows if len(f)>4 and f[4]=='rppd'];caps=[f for f in rows if len(f)>3 and f[3]=='cap_cmim']
        assert len(conversion)==4 and len(caps)==2
        for f in conversion:resistors['xchain.'+f[0]]=dict(nodes=['0'if n in ('avss','sub')else'xchain.'+n for n in f[1:4]],parameters=f[5:])
        r['native_caps']={f[0]:dict(nodes=['xchain.'+n for n in f[1:3]],model=f[3],parameters=f[4:])for f in caps}
        assert len(devices)==30 and len(resistors)==28 and sum(x['nx']for x in devices.values())==82

        nodes={n for x in devices.values()for n in x['nodes']}|{n for x in resistors.values()for n in x['nodes']}|{n for x in r['native_caps'].values()for n in x['nodes']}|{'qp','qn','dp','dn','cp','cn','avdd','ira','irb'};nodes.discard('0')
        assert {'xchain.aqp','xchain.aqn','xchain.udp','xchain.udn'}<=nodes,'Required interstage voltage probes missing before simulation'
        vectors=['v('+n+')'for n in sorted(nodes)]+['@q.'+n+'.qnpn13g2[ic]'for n in devices]
        bits=primitive.prbs(0x7f);models=lib/'models/models'
        deck=['NSSOC clean native sampler characterization',f'.lib "{models}/cornerHBT.lib" hbt_typ',f'.lib "{models}/cornerRES.lib" {c["res"]}',f'.lib "{models}/cornerCAP.lib" {c["cap"]}',f'.include "{SOURCE}"',f'.include "{actual_wrapper}"',f'.temp {c["temperature"]}',
            '.options reltol=1e-4 abstol=1e-12 klu',f'VDD avdd 0 PWL(0 0 500p {2.5*scale:.12g})','IRA avdd ira PWL(0 0 500p .0005)','IRB avdd irb PWL(0 0 500p .0005)',
            'VDP dp0 0 '+data(bits,1.65*scale,.15*scale),'VDN dn0 0 '+data([1-b for b in bits],1.65*scale,.15*scale),
            'VCP cp0 0 '+clock(scale,True,args.case=='clock_stopped'),'VCN cn0 0 '+clock(scale,False,args.case=='clock_stopped'),
            'RDP dp0 dp 10','RDN dn0 dn 10','RCP cp0 cp 10','RCN cn0 cn 10',
            f'XCHAIN dp dn cp cn {output[0]} {output[1]} avdd 0 0 ira irb nssoc_cdr_halfcycle_retime_v1','CAQP xchain.aqp 0 150f','CAQN xchain.aqn 0 150f','CQP qp 0 150f','CQN qn 0 150f',
            '.control',f'pre_osdi {lib/"models/r3_cmc.osdi"}','set wr_singlescale','set wr_vecnames','set numdgt=16','save '+' '.join(vectors)]
        for name in devices:
            q='q.'+name+'.qnpn13g2';deck.extend([f'alter @{q}[off] = 1',f'echo NSSOC_NATIVE_FLAG_BEGIN {q}',f'show {q} : off','echo NSSOC_NATIVE_FLAG_END'])
        deck+=['op','wrdata op.dat '+' '.join(vectors),f'tran {STEP:.14g} {STOP:.14g} 0 {STEP:.14g}','wrdata wave.dat '+' '.join(vectors),'echo NSSOC_BACKEND_OPTIONS_BEGIN','option','echo NSSOC_BACKEND_OPTIONS_END','quit','.endc','.end']
        native=out/'native';native.mkdir();(native/'bench.cir').write_text('\n'.join(deck)+'\n');(native/'spinit').write_text('set num_threads=1\n')
        protected={str(f):sha(f)for f in [Path(__file__),SOURCE,WRAPPER,actual_wrapper,ROOT/'scripts/cloud_cdr_xor.py',ROOT/'scripts/cloud_vbic_tree32_backend.py',engine,native/'bench.cir',*lib.rglob('*')]if f.is_file()}
        r.update(devices=devices,resistors=resistors,vectors=vectors,source_bits=bits,source_bits_sha256=hashlib.sha256(bytes(bits)).hexdigest(),protected_inputs=protected);save()
        env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(native),OMP_NUM_THREADS='1')
        with(native/'native.log').open('w')as log:proc=subprocess.run([str(engine),'-n','-b','bench.cir'],cwd=native,env=env,stdout=log,stderr=subprocess.STDOUT)
        text=(native/'native.log').read_text();opts,notes,_=backend_readback(text,'klu');r.update(returncode=proc.returncode,native_options=opts,diagnostics=notes);save();assert proc.returncode==0 and not notes
        flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',text)
        assert [n for n,_ in flags]==['q.'+n+'.qnpn13g2'for n in devices]and all(re.findall(r'(?m)^\s*off\s+([01])\s*$',s)==['1']for _,s in flags)
        r['native_flags_verified']=len(flags)
        op=np.loadtxt(native/'op.dat',skiprows=1);assert op.size==len(vectors)+1 and np.isfinite(op).all()and abs(op).max()<1e-9;r['zero_source_op_maximum']=float(abs(op).max())
        with(native/'wave.dat').open()as f:header=f.readline().lower().split()
        assert header==['time',*vectors]
        wave=np.loadtxt(native/'wave.dat',skiprows=1);t=wave[:,0];assert wave.shape[1]==len(vectors)+1 and np.isfinite(wave).all()and t[0]==0 and abs(t[-1]-STOP)<1e-15 and np.all(np.diff(t)>0)and np.diff(t).max()<=STEP*1.00001
        d={n:wave[:,i+1]for i,n in enumerate(vectors)};active=t>=START
        def v(n):return np.zeros(len(t))if n=='0'else d['v('+n+')']
        delta=v('qp')-v('qn');signed=[];delay=[]
        for i,bit in enumerate(bits):
            edge=START+(i+1)*UI;sign=2*bit-1
            for phase in (.3,.6,.9):signed.append(float(np.interp(edge+phase*UI,t,delta))*sign)
            ids=np.flatnonzero((t>=edge)&(t<=edge+.95*UI));bad=ids[delta[ids]*sign<.1]
            delay.append(0. if not len(bad)else float(t[bad[-1]]-edge+STEP))
        checks={}
        for name,dev in devices.items():
            vc,vb,ve,_=map(v,dev['nodes']);ic=d['@q.'+name+'.qnpn13g2[ic]'];checks[name]=dict(minimum_active_vce_v=float((vc-ve)[active].min()),maximum_alltime_abs_vce_v=float(abs(vc-ve).max()),maximum_alltime_abs_vbe_v=float(abs(vb-ve).max()),maximum_alltime_abs_ic_per_emitter_a=float(abs(ic).max()/dev['nx']))
        safe=all(x['minimum_active_vce_v']>=.4 and x['maximum_alltime_abs_vce_v']<=1.6 and x['maximum_alltime_abs_vbe_v']<=1. and x['maximum_alltime_abs_ic_per_emitter_a']<.003 for x in checks.values())
        tails={name:float(d['@q.'+name+'.qnpn13g2[ic]'][active].min())for name in ('xchain.xsa.xm.xt','xchain.xsa.xs.xt','xchain.xsb.xm.xt','xchain.xsb.xs.xt')};safe=safe and min(tails.values())>=.0005
        first_margins=[];first_delays=[];dd=v('xchain.aqp')-v('xchain.aqn')
        for i,bit in enumerate(bits):
            edge=START+(i+.5)*UI;sign=2*bit-1
            for phase in (.3,.6,.9):first_margins.append(float(np.interp(edge+phase*UI,t,dd))*sign)
            ids=np.flatnonzero((t>=edge)&(t<=edge+.95*UI));bad=ids[dd[ids]*sign<.1]
            first_delays.append(0. if not len(bad)else float(t[bad[-1]]-edge+STEP))
        r['first_sampler_checks']=dict(samples=len(first_margins),minimum_signed_margin_v=min(first_margins),wrong_sign_samples=sum(x<=0 for x in first_margins),below_100mv_samples=sum(x<.1 for x in first_margins),maximum_clock_to_valid_s=max(first_delays),passed=min(first_margins)>=.1 and max(first_delays)<=.3*UI)
        r['native_cap_voltage_checks']={name:dict(maximum_alltime_abs_v=float(abs(v(d['nodes'][0])-v(d['nodes'][1])).max()),limit_v=1.6)for name,d in r['native_caps'].items()}
        safe=safe and all(x['maximum_alltime_abs_v']<=1.6 for x in r['native_cap_voltage_checks'].values())
        r['interface_observations']={name:dict(commonmode_v=[float(((v(p)+v(n))/2)[active].min()),float(((v(p)+v(n))/2)[active].max())],differential_v=[float((v(p)-v(n))[active].min()),float((v(p)-v(n))[active].max())])for name,p,n in [('first_sampler','xchain.aqp','xchain.aqn'),('retimer_input','xchain.udp','xchain.udn')]}
        data_ok=min(signed)>=.1 and max(delay)<=.3*UI and r['first_sampler_checks']['passed']
        r.update(samples=len(signed),minimum_signed_margin_v=min(signed),wrong_sign_samples=sum(x<=0 for x in signed),below_100mv_samples=sum(x<.1 for x in signed),maximum_clock_to_valid_s=max(delay),clock_to_valid_by_bit_s=delay,device_checks=checks,minimum_active_tail_current_a=tails,devices_passed=safe,data_passed=data_ok,
            observed_output_common_mode_v=[float(((v('qp')+v('qn'))/2)[active].min()),float(((v('qp')+v('qn'))/2)[active].max())],observed_output_differential_v=[float(delta[active].min()),float(delta[active].max())])
        assert len(signed)==768 and all(sha(Path(f))==h for f,h in protected.items());r['sources_unchanged']=True
        fault=args.case in ('swap_output','clock_stopped','wrong_edge');r['actual_fault_detected']=fault and not data_ok
        passed=r['actual_fault_detected']if fault else safe and data_ok
        r['status']='PASS_NATIVE_HALFCYCLE_RETIME_NOT_PHASE_DETECTOR_OR_CDR'if passed else'REJECTED_NATIVE_HALFCYCLE_RETIME'
        assert passed,'Original sampler data/device limits or added clean-start checks failed'
    except BaseException as error:
        if r['status']=='RUNNING':r['status']='FAIL_OR_ERROR'
        r['error']=repr(error);raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save();print(r['status'],flush=True)
if __name__=='__main__':main()
