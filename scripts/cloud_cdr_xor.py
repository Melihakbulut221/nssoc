#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native 8GT/s CDR comparison-gate experiment, not recovered-clock acceptance."""
import argparse,json,os,re,shutil,subprocess
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import cloud_pll_pump_current as pump
from cloud_vbic_tree32_backend import backend_readback,readback_controls
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'cloud-pll-snapshot'
COMPONENT=ROOT/'hw/soc/analog/pcie/tx_mux54_passive_drive_v10.spice'
WRAPPER=ROOT/'hw/soc/analog/pcie/cdr_xor_hbt_v1.spice'
COMPONENT_SHA='56b50efbbc138e8af973c63809799574da4ffb9c79b9ff5b5732c44e7e234df8'
WRAPPER_SHA='342ba96abb65ce58de7c59fec4c9b2c06ecc06be069343ece22ef20c414c2675'
SUMMARY='d5eed10a190213d552fa410db5eece05cd2c39f0b8c5e8266ecee050c3ba4025'
PARTS='791cd593eac42eae8b9bf629b9ec90355b167a557910dcb5be4a441d30e01961'
OUTPUT_STEM='cloud-cdr-xor'
TOP='nssoc_cdr_xor_hbt_v1'
EXTRA_INPUTS=[]
UI=125e-12;START=2e-9;STOP=34e-9;STEP=.3125e-12

def prbs(seed):
    state=seed;bits=[]
    for _ in range(256):
        bits.append(state&1);state=((state<<1)|(((state>>6)^(state>>5))&1))&127
    assert len(set(bits))==2
    return bits

def wave(bits,cm,amplitude):
    level=lambda b:cm+amplitude*(1 if b else -1)
    points=[(0,0),(.5e-9,level(bits[0]))]
    for i in range(1,256):
        if bits[i]!=bits[i-1]:
            edge=START+i*UI;points.extend([(edge,level(bits[i-1])),(edge+5e-12,level(bits[i]))])
    points.append((STOP,level(bits[-1])))
    return 'PWL(\n+ '+'\n+ '.join(f'{t:.14g} {v:.14g}'for t,v in points)+')'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--case',choices=['nominal','hot_low','cold_high','swap_output'],required=True);args=ap.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/(OUTPUT_STEM+'-'+args.case);out.mkdir(exist_ok=False);reports.OUT=out
    corner='nominal'if args.case=='swap_output'else args.case;c=pump.CORNERS[corner];scale=c['scale']
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=args.case,accepted=False,
        full_phy_accepted=False,cdr_accepted=False,layout_accepted=False,
        scope='Original54-device mux connected as XOR, external ideal current bias and driven differential inputs through10ohm sources,50fF per output. 256symbols/8GT/s. Schematic primitive only; no physical input level conversion, samplers, recovered clock, complete PVT, noise/jitter/BER, interconnect or chip integration.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        assert sha(COMPONENT)==COMPONENT_SHA and sha(WRAPPER)==WRAPPER_SHA
        r['readback_controls']=readback_controls()
        fetch(pump.BASE+'cloud-results-39029337682-1-pll-pump-current/pll-pump-current-39029337682-1.summary.json',SUMMARY,out/'models-pin.json')
        pin=json.loads((out/'models-pin.json').read_text())
        wanted=[n for n in pin['outputs']if n.startswith('source/model-sources/')]
        wanted+=['source-pin.json','source/runtime/patched-ngspice']
        old,proof=reports.restore_report('pll-pump-current',39029337682,SUMMARY,PARTS,out/'source',wanted)
        assert old==pin;r['models_source']=proof
        original=json.loads((out/'source/source-pin.json').read_text())
        assert sha(out/'source/source-pin.json')==pump.SUMMARY
        assert not LIB.exists();shutil.copytree(out/'source/source/model-sources',LIB)
        assert all(sha(LIB/p)==d for p,d in original['preparation']['model_sources'].items())
        engine=out/'source/source/runtime/patched-ngspice';engine.chmod(0o755)
        assert sha(engine)=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
        rows=[l.lower().split()for l in COMPONENT.read_text().splitlines()if l and not l.startswith('*')]
        public=next(f[2:]for f in rows if f[0]=='.subckt')
        assert public==['sub','ap','an','bp','bn','iref','sp','sn','on','op','avss','avdd']
        output=('qn','qp')if args.case=='swap_output'else('qp','qn')
        mapping=dict(zip(public,['0','dp','dn','dn','dp','iref','ep','en',*output,'0','avdd']))
        def node(n):return mapping[n]if n in mapping else'xgate.xcore.'+n
        devices={};nodes=set()
        for f in rows:
            if 'npn13g2'in f:
                at=f.index('npn13g2');assert at==5
                params=dict(x.split('=')for x in f[at+1:]);nx=int(params['nx']);assert 1<=nx<=10
                path='xgate.xcore.'+f[0]
                devices[path]=dict(nodes=[node(n)for n in f[1:5]],nx=nx)
                nodes.update(devices[path]['nodes'])
        assert len(devices)==19
        nodes.update(['qp','qn','dp','dn','ep','en','avdd','iref']);nodes.discard('0')
        voltages=['v('+n+')'for n in sorted(nodes)]
        currents=['@q.'+n+'.qnpn13g2[ic]'for n in devices]
        vectors=voltages+currents
        a,b=prbs(0x7f),prbs(0x5d);expected=np.array([x^y for x,y in zip(a,b)])
        assert set(zip(a,b))=={(0,0),(0,1),(1,0),(1,1)}
        models=LIB/'models/models'
        deck=['NSSOC actual54device CDR XOR primitive experiment',
            f'.lib "{models}/cornerHBT.lib" hbt_typ',f'.lib "{models}/cornerRES.lib" {c["res"]}',
            f'.include "{COMPONENT}"',f'.include "{WRAPPER}"',f'.temp {c["temperature"]}',
            '.options reltol=1e-4 abstol=1e-12 klu',f'VDD avdd 0 PWL(0 0 500p {2.5*scale:.12g})',
            'IREF avdd iref PWL(0 0 500p .0005)',
            'VDP dp0 0 '+wave(a,2.0*scale,.15*scale),
            'VDN dn0 0 '+wave([1-x for x in a],2.0*scale,.15*scale),
            'VEP ep0 0 '+wave(b,1.3*scale,.15*scale),
            'VEN en0 0 '+wave([1-x for x in b],1.3*scale,.15*scale),
            'RDP dp0 dp 10','RDN dn0 dn 10','REP ep0 ep 10','REN en0 en 10',
            f'XGATE dp dn ep en {output[0]} {output[1]} avdd 0 0 iref {TOP}',
            'CQP qp 0 50f','CQN qn 0 50f','.control',f'pre_osdi {LIB/"models/r3_cmc.osdi"}',
            'set wr_singlescale','set wr_vecnames','set numdgt=16','save '+' '.join(vectors)]
        for n in devices:
            path='q.'+n+'.qnpn13g2'
            deck += [f'alter @{path}[off] = 1',f'echo NSSOC_NATIVE_FLAG_BEGIN {path}',f'show {path} : off','echo NSSOC_NATIVE_FLAG_END']
        deck+=['op','wrdata op.dat '+' '.join(vectors),f'tran {STEP:.14g} {STOP:.14g} 0 {STEP:.14g}',
            'wrdata wave.dat '+' '.join(vectors),'echo NSSOC_BACKEND_OPTIONS_BEGIN','option',
            'echo NSSOC_BACKEND_OPTIONS_END','quit','.endc','.end']
        native=out/'native';native.mkdir();(native/'bench.cir').write_text('\n'.join(deck)+'\n')
        (native/'spinit').write_text('set num_threads=1\n')
        protected={str(p):sha(p)for p in [Path(__file__),*EXTRA_INPUTS,COMPONENT,WRAPPER,engine,native/'bench.cir',*LIB.rglob('*')]if p.is_file()}
        r.update(physical_device_count=54,hbt_count=19,source_bits=[a,b],expected_xor=expected.tolist(),
            vectors=vectors,devices=devices,protected_inputs=protected);save()
        env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')}
        env.update(SPICE_SCRIPTS=str(native),OMP_NUM_THREADS='1')
        with(native/'native.log').open('w')as log:
            proc=subprocess.run([str(engine),'-n','-b','bench.cir'],cwd=native,env=env,stdout=log,stderr=subprocess.STDOUT)
        text=(native/'native.log').read_text();opts,notes,_=backend_readback(text,'klu')
        r.update(returncode=proc.returncode,native_options=opts,diagnostics=notes);save()
        assert proc.returncode==0 and not notes
        flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',text)
        assert [n for n,_ in flags]==['q.'+n+'.qnpn13g2'for n in devices]
        assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',s)==['1']for _,s in flags)
        op=np.loadtxt(native/'op.dat',skiprows=1);assert op.size==len(vectors)+1 and np.isfinite(op).all()and np.abs(op).max()<1e-9
        r['zero_source_op_maximum']=float(np.abs(op).max())
        header=(native/'wave.dat').open().readline().lower().split()
        assert header==['time',*vectors],header
        wave_data=np.loadtxt(native/'wave.dat',skiprows=1);t=wave_data[:,0]
        assert wave_data.shape[1]==len(vectors)+1 and np.isfinite(wave_data).all()
        assert t[0]==0 and abs(t[-1]-STOP)<1e-15 and np.all(np.diff(t)>0)and np.diff(t).max()<=STEP*1.00001
        d={n:wave_data[:,i+1]for i,n in enumerate(vectors)};active=t>=START
        def v(n):return np.zeros(len(t))if n=='0'else d['v('+n+')']
        signed=[];delta=v('qp')-v('qn');sign=2*expected-1
        for phase in (.3,.5,.7):signed.extend((np.interp(START+(np.arange(256)+phase)*UI,t,delta)*sign).tolist())
        safety={}
        for n,info in devices.items():
            vc,vb,ve,body=map(v,info['nodes']);ic=d['@q.'+n+'.qnpn13g2[ic]']
            safety[n]=dict(minimum_active_vce_v=float((vc-ve)[active].min()),
                maximum_alltime_vce_v=float((vc-ve).max()),maximum_alltime_abs_ic_a=float(np.abs(ic).max()),nx=info['nx'])
        signal_pass=min(signed)>=.1
        safe=all(v['minimum_active_vce_v']>=.4 and v['maximum_alltime_vce_v']<=1.6 and v['maximum_alltime_abs_ic_a']<.003*v['nx']for v in safety.values())
        observed_fault=args.case=='swap_output'and sum(x<0 for x in signed)>0
        r.update(samples=768,wrong_sign_samples=sum(x<0 for x in signed),below_100mv_samples=sum(x<.1 for x in signed),
            minimum_signed_margin_v=min(signed),device_checks=safety,data_passed=signal_pass,devices_passed=safe,
            actual_output_swap_detected=observed_fault,native_flags_verified=19)
        assert all(sha(Path(p))==h for p,h in protected.items());r['sources_unchanged']=True
        passed=safe and (observed_fault if args.case=='swap_output'else signal_pass)
        r['status']='PASS_NATIVE_XOR_PRIMITIVE_ONLY_NOT_CDR_OR_LAYOUT'if passed else'REJECTED_NATIVE_XOR_PRIMITIVE'
        assert passed,'Original XOR/device criteria failed; raw evidence retained'
    except BaseException as error:
        if r['status']=='RUNNING':r['status']='FAIL_OR_ERROR'
        r['error']=repr(error);raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
