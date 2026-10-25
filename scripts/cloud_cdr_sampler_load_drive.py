#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fourfold native drive with explicit1pF stress; no physical integration claim."""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import cloud_cdr_xor as primitive
import cloud_pll_pump_current as pump
from cloud_vbic_tree32_backend import backend_readback,readback_controls
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hw/soc/analog/pcie/rx_sampler_load_drive_v2.spice'
SOURCE_SHA='973930e61f732a729c751c9a7048e41f6eb81720aac23e620efa0a120b192f70'
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
    assert current is None and set(sub)=={'nssoc_cml_latch_load_drive_v2','nssoc_rx_sampler_load_drive_v2'}
    devices={};resistors={};mos={}
    def visit(top,path,ports,stack):
        assert top not in stack
        unit=sub[top];mapping=dict(zip(unit['ports'],ports,strict=True));seen=set()
        def node(n):return mapping.get(n,path+'.'+n)
        for f in unit['rows']:
            assert f[0].startswith('x')and f[0]not in seen;seen.add(f[0]);name=path+'.'+f[0]
            if len(f)>5 and f[5]=='npn13g2':
                assert name not in devices;params=dict(x.split('=')for x in f[6:]);assert params.keys()=={'nx'}
                devices[name]=dict(nodes=[node(n)for n in f[1:5]],nx=int(params['nx']))
            elif len(f)>5 and f[5]=='sg13_lv_nmos':
                params=dict(x.split('=')for x in f[6:]);assert set(params)=={'w','l','ng'}
                assert params==dict(w='8u'if name=='xsamp.xref'else'128u',l='.3u',ng='1')
                mos[name]=dict(nodes=[node(n)for n in f[1:5]],parameters=params)
            elif len(f)>4 and f[4]=='rppd':resistors[name]=dict(nodes=[node(n)for n in f[1:4]],parameters=f[5:])
            else:
                assert f[-1]in sub;visit(f[-1],name,[node(n)for n in f[1:-1]],stack+[top])
    visit('nssoc_rx_sampler_load_drive_v2','xsamp',['dp','dn',*output,'cp','cn','avdd','0','0','iref'],[])
    assert len(devices)==12 and len(resistors)==12 and len(mos)==3
    assert sum(x['nx']for x in devices.values())==128
    assert set(devices)=={'xsamp.x'+stage+'.x'+name for stage in ('m','s')for name in ('dp','dn','lp','ln','cs','ch')}
    assert set(mos)=={'xsamp.xref','xsamp.xm.xt','xsamp.xs.xt'}
    return devices,resistors,mos

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
    p=argparse.ArgumentParser();p.add_argument('--case',choices=['nominal','hot_low','cold_high','swap_output','clock_stopped'],required=True);args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/('cloud-cdr-sampler-load-drive-'+args.case);out.mkdir(exist_ok=False);reports.OUT=out
    c=pump.CORNERS[args.case if args.case in ('nominal','hot_low','cold_high')else'nominal'];scale=c['scale']
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=args.case,accepted=False,cdr_accepted=False,full_phy_accepted=False,physical_layout_matches=False,
        scope='Candidate12HBT/3nativeLVNMOS/12nativeR CML master/slave sampler with external8GHz clock,10ohm data/clock sources,1.65V data commonmode,500uA idealbias and1pF/output stress. Fourfold HBT Nx/tail width/collector resistor width relative to original hybrid sampler. This lumped stress is not the distributed extracted parent load. Clean zero-sourceOP/OFF readback,256sourcebits,full34.25ns native trajectory. No RX/XOR loading, recovered clock, physical parasitics or fullCDR/PHY acceptance.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        assert sha(SOURCE)==SOURCE_SHA
        from check_cdr_sampler_load_drive_source import check
        r['source_delta_guard']=check()
        assert sha(ROOT/'scripts/cloud_cdr_xor.py')=='3ec870fa6a30d9f94038368d6b74c984c314c2d7248ecaab94c687867587fabe'
        r['readback_controls']=readback_controls()
        fetch(pump.BASE+'cloud-results-39029337682-1-pll-pump-current/pll-pump-current-39029337682-1.summary.json',primitive.SUMMARY,out/'models-pin.json')
        pin=json.loads((out/'models-pin.json').read_text());wanted=[n for n in pin['outputs']if n.startswith('source/model-sources/')]+['source-pin.json','source/runtime/patched-ngspice']
        old,proof=reports.restore_report('pll-pump-current',39029337682,primitive.SUMMARY,primitive.PARTS,out/'source',wanted);assert old==pin;r['models_source']=proof
        original=json.loads((out/'source/source-pin.json').read_text());assert sha(out/'source/source-pin.json')==pump.SUMMARY
        lib=out/'models';shutil.copytree(out/'source/source/model-sources',lib)
        assert all(sha(lib/p)==d for p,d in original['preparation']['model_sources'].items())
        engine=out/'source/source/runtime/patched-ngspice';engine.chmod(0o755);assert sha(engine)=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
        output=('qn','qp')if args.case=='swap_output'else('qp','qn');devices,resistors,mos=bind(SOURCE.read_text(),output)
        nodes={n for x in [*devices.values(),*mos.values()]for n in x['nodes']}|{'qp','qn','dp','dn','cp','cn','avdd','iref'};nodes.discard('0')
        vectors=['v('+n+')'for n in sorted(nodes)]+['@q.'+n+'.qnpn13g2[ic]'for n in devices]+['@n.'+n+'.nsg13_lv_nmos[ids]'for n in mos]
        bits=primitive.prbs(0x7f);models=lib/'models/models'
        mos_osdi={}
        for name in ('psp103.osdi','psp103_nqs.osdi'):
            matches=list(lib.rglob(name));assert len(matches)==1,(name,matches)
            mos_osdi[name]=matches[0]
        r['mos_runtime']={str(p.relative_to(lib)):sha(p)for p in mos_osdi.values()}
        deck=['NSSOC clean native sampler characterization',f'.lib "{models}/cornerHBT.lib" hbt_typ',f'.lib "{models}/cornerRES.lib" {c["res"]}',f'.lib "{models}/cornerMOSlv.lib" {c["mos"]}',f'.include "{SOURCE}"',f'.temp {c["temperature"]}',
            '.options reltol=1e-4 abstol=1e-12 klu',f'VDD avdd 0 PWL(0 0 500p {2.5*scale:.12g})','IREF avdd iref PWL(0 0 500p .0005)',
            'VDP dp0 0 '+data(bits,1.65*scale,.15*scale),'VDN dn0 0 '+data([1-b for b in bits],1.65*scale,.15*scale),
            'VCP cp0 0 '+clock(scale,True,args.case=='clock_stopped'),'VCN cn0 0 '+clock(scale,False,args.case=='clock_stopped'),
            'RDP dp0 dp 10','RDN dn0 dn 10','RCP cp0 cp 10','RCN cn0 cn 10',
            f'XSAMP dp dn {output[0]} {output[1]} cp cn avdd 0 0 iref nssoc_rx_sampler_load_drive_v2','CQP qp 0 1p','CQN qn 0 1p',
            '.control',f'pre_osdi {lib/"models/r3_cmc.osdi"}',*[f'pre_osdi {p}'for p in mos_osdi.values()],'set wr_singlescale','set wr_vecnames','set numdgt=16','save '+' '.join(vectors)]
        for name in devices:
            q='q.'+name+'.qnpn13g2';deck.extend([f'alter @{q}[off] = 1',f'echo NSSOC_NATIVE_FLAG_BEGIN {q}',f'show {q} : off','echo NSSOC_NATIVE_FLAG_END'])
        deck+=['op','wrdata op.dat '+' '.join(vectors),f'tran {STEP:.14g} {STOP:.14g} 0 {STEP:.14g}','wrdata wave.dat '+' '.join(vectors),'echo NSSOC_BACKEND_OPTIONS_BEGIN','option','echo NSSOC_BACKEND_OPTIONS_END','quit','.endc','.end']
        native=out/'native';native.mkdir();(native/'bench.cir').write_text('\n'.join(deck)+'\n');(native/'spinit').write_text('set num_threads=1\n')
        protected={str(f):sha(f)for f in [Path(__file__),SOURCE,ROOT/'scripts/cloud_cdr_xor.py',ROOT/'scripts/cloud_vbic_tree32_backend.py',engine,native/'bench.cir',*lib.rglob('*')]if f.is_file()}
        r.update(devices=devices,resistors=resistors,mos_devices=mos,vectors=vectors,source_bits=bits,source_bits_sha256=hashlib.sha256(bytes(bits)).hexdigest(),protected_inputs=protected);save()
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
            edge=START+(i+.5)*UI;sign=2*bit-1
            for phase in (.3,.6,.9):signed.append(float(np.interp(edge+phase*UI,t,delta))*sign)
            ids=np.flatnonzero((t>=edge)&(t<=edge+.95*UI));bad=ids[delta[ids]*sign<.1]
            delay.append(0. if not len(bad)else float(t[bad[-1]]-edge+STEP))
        checks={}
        for name,dev in devices.items():
            vc,vb,ve,_=map(v,dev['nodes']);ic=d['@q.'+name+'.qnpn13g2[ic]'];checks[name]=dict(minimum_active_vce_v=float((vc-ve)[active].min()),maximum_alltime_abs_vce_v=float(abs(vc-ve).max()),maximum_alltime_abs_vbe_v=float(abs(vb-ve).max()),maximum_alltime_abs_ic_per_emitter_a=float(abs(ic).max()/dev['nx']))
        safe=all(x['minimum_active_vce_v']>=.4 and x['maximum_alltime_abs_vce_v']<=1.6 and x['maximum_alltime_abs_vbe_v']<=1. and x['maximum_alltime_abs_ic_per_emitter_a']<.003 for x in checks.values())
        mos_checks={}
        for name,dev in mos.items():
            vd,vg,vs,vb=map(v,dev['nodes']);ids=d['@n.'+name+'.nsg13_lv_nmos[ids]']
            peaks={label:float(abs(value).max())for label,value in [('vds',vd-vs),('vgs',vg-vs),('vgd',vg-vd),('vdb',vd-vb),('vsb',vs-vb)]}
            mos_checks[name]=dict(peaks_v=peaks,limit_v=1.32,minimum_active_vds_v=float((vd-vs)[active].min()),minimum_active_drain_current_a=float(ids[active].min()),maximum_alltime_abs_drain_current_a=float(abs(ids).max()),passed=max(peaks.values())<=1.32 and float((vd-vs)[active].min())>=0)
        tails={name:mos_checks[name]['minimum_active_drain_current_a']for name in ('xsamp.xm.xt','xsamp.xs.xt')}
        safe=safe and all(x['passed']for x in mos_checks.values())and min(tails.values())>=.0005
        r['mos_checks']=mos_checks
        data_ok=min(signed)>=.1 and max(delay)<=.3*UI
        r.update(samples=len(signed),minimum_signed_margin_v=min(signed),wrong_sign_samples=sum(x<=0 for x in signed),below_100mv_samples=sum(x<.1 for x in signed),maximum_clock_to_valid_s=max(delay),clock_to_valid_by_bit_s=delay,device_checks=checks,minimum_active_tail_current_a=tails,devices_passed=safe,data_passed=data_ok,
            observed_output_common_mode_v=[float(((v('qp')+v('qn'))/2)[active].min()),float(((v('qp')+v('qn'))/2)[active].max())],observed_output_differential_v=[float(delta[active].min()),float(delta[active].max())])
        assert len(signed)==768 and all(sha(Path(f))==h for f,h in protected.items());r['sources_unchanged']=True
        fault=args.case in ('swap_output','clock_stopped');r['actual_fault_detected']=fault and not data_ok
        passed=r['actual_fault_detected']if fault else safe and data_ok
        r['status']='PASS_NATIVE_LOAD_DRIVE_STRESS_NOT_CDR_OR_PHYSICAL_ACCEPTANCE'if passed else'REJECTED_NATIVE_LOAD_DRIVE_STRESS'
        assert passed,'Original sampler data/device limits or added clean-start checks failed'
    except BaseException as error:
        if r['status']=='RUNNING':r['status']='FAIL_OR_ERROR'
        r['error']=repr(error);raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save();print(r['status'],flush=True)
if __name__=='__main__':main()
