#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actually connected two-sampler/native-R/fresh-wire-XOR comparison."""
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
WRAPPER=ROOT/'hw/soc/analog/pcie/cdr_sampled_compare_buffered_v4.spice'
WRAPPER_SHA='8b9ade6650c8d5153f3d872660b04d8cac1970220a6fc5fc233ec05489bb2d7c'
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
    p=argparse.ArgumentParser();p.add_argument('--case',choices=['nominal','hot_low','cold_high','swap_output','clock_stopped'],required=True);args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/('cloud-cdr-feedforward-compare-'+args.case);out.mkdir(exist_ok=False);reports.OUT=out
    c=pump.CORNERS[args.case if args.case in ('nominal','hot_low','cold_high')else'nominal'];scale=c['scale']
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=args.case,accepted=False,cdr_accepted=False,full_phy_accepted=False,physical_layout_matches=False,
        scope='Connected2native samplers+8native level-conversion resistors+2native4HBT buffers+actual54device XOR withfresh4020R/2641C. All57HBTs measured;135native devices including4native MIM capacitors including27bodycontacts. External8GHz clock/10ohmsources/500uA sampler/XOR references and1mA perbuffer reference;150fF per sampleroutput retained plus actual connected load;50fF per XORoutput. No ideal internalgain/currentdriver;4native3.6um-square MIM feedforward capacitors across input series resistors. Sampler/converter routing RC and complete multiedgePD/CDR/x4PHY remain open.')
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
        pinpath=ROOT/'docs/evidence/cdr-v4-composition-pass-20261017.json';compin=json.loads(pinpath.read_text())
        composed,comproof=reports.restore_report('cdr-v4-composition',compin['run'],compin['summary_sha256'],compin['parts_sha256'],out/'xor-source',list(compin['outputs']))
        assert composed['sources_unchanged']and composed['status']==compin['status']and composed['composition']['counts']==dict(devices=54,R=4020,C=2641)
        assert composed['native_binding']==compin['native_binding']and composed['controls']==compin['controls']and len(composed['controls']['controls'])==6
        model=out/'xor-source/xor54-wire.spice';assert sha(model)=='b201876a3b0988f746822213f51c120e09f9837c0f26ddb1a7a591bd57dfdc23'
        r['xor_source']=comproof
        output=('qn','qp')if args.case=='swap_output'else('qp','qn');devices={};resistors={}
        original_devices,original_resistors=bind(SOURCE.read_text(),('qp','qn'))
        for letter in ('a','b'):
            mapping=dict(dp=letter+'dp',dn=letter+'dn',qp='xcmp.'+letter+'qp',qn='xcmp.'+letter+'qn',cp='cp',cn='cn',avdd='avdd',iref='ir'+letter)
            def mapped(n):return mapping.get(n,n.replace('xsamp.','xcmp.xs'+letter+'.'))
            for name,d in original_devices.items():devices[name.replace('xsamp.','xcmp.xs'+letter+'.')]=dict(nodes=[mapped(n)for n in d['nodes']],nx=d['nx'])
            for name,d in original_resistors.items():resistors[name.replace('xsamp.','xcmp.xs'+letter+'.')]=dict(nodes=[mapped(n)for n in d['nodes']],parameters=d['parameters'])
        rows=[l.lower().split()for l in model.read_text().splitlines()if l and not l.startswith('*')]
        assert rows[0]==['.subckt','nssoc_cdr_xor54_wire_v4','qp','qn','avdd','sub','dp','dn','ep','en','iref','avss','wire_cref']
        mapping=dict(qp=output[0],qn=output[1],avdd='avdd',sub='0',dp='xcmp.xp',dn='xcmp.xn',ep='xcmp.yp',en='xcmp.yn',iref='irx',avss='0',wire_cref='0')
        def mapped(n):return mapping.get(n,'xcmp.xxor.'+n)
        for f in rows:
            if 'npn13g2'in f:
                assert f[5]=='npn13g2';params=dict(x.split('=')for x in f[6:]);devices['xcmp.xxor.'+f[0]]=dict(nodes=[mapped(n)for n in f[1:5]],nx=int(params['nx']))
            elif len(f)>4 and f[4]=='rppd':resistors['xcmp.xxor.'+f[0]]=dict(nodes=[mapped(n)for n in f[1:4]],parameters=f[5:])
        wrapper_rows=[l.lower().split()for l in WRAPPER.read_text().splitlines()if l and not l.startswith('*')]
        sections={};section=None
        for f in wrapper_rows:
            if f[0]=='.subckt':assert section is None and f[1]not in sections;section=f[1];sections[section]=dict(ports=f[2:],rows=[])
            elif f[0]=='.ends':assert f[1]==section;section=None
            else:assert section is not None;sections[section]['rows'].append(f)
        assert section is None and set(sections)=={'nssoc_cdr_sampled_compare_buffered_v4','nssoc_cdr_data_buffer_v4','nssoc_cdr_select_buffer_v4'}
        top_rows=sections['nssoc_cdr_sampled_compare_buffered_v4']['rows']
        conversion=[f for f in top_rows if len(f)>4 and f[4]=='rppd'];assert len(conversion)==8
        def check_caps(candidate_rows):
            actual=[f for f in candidate_rows if len(f)>3 and f[3]=='cap_cmim']
            expected=[['xcfap','aqp','udp','cap_cmim','w=3.6u','l=3.6u'],['xcfan','aqn','udn','cap_cmim','w=3.6u','l=3.6u'],['xcfbp','bqp','usp','cap_cmim','w=3.6u','l=3.6u'],['xcfbn','bqn','usn','cap_cmim','w=3.6u','l=3.6u']]
            assert actual==expected,'Native compensation geometry/terminal mismatch'
            return actual
        cap_rows=check_caps(top_rows);cap_controls=[]
        for label in ('missing_cap','wrong_terminal','wrong_geometry'):
            bad=[list(f)for f in top_rows]
            at=next(i for i,f in enumerate(bad)if f[0]=='xcfap')
            if label=='missing_cap':bad.pop(at)
            elif label=='wrong_terminal':bad[at][2]='usn'
            else:bad[at][-1]='l=99u'
            try:check_caps(bad)
            except AssertionError:cap_controls.append(label)
            else:raise AssertionError('Actual MIM corruption accepted')
        r['native_mim_caps']={f[0]:dict(nodes=['xcmp.'+n for n in f[1:3]],model=f[3],parameters=f[4:])for f in cap_rows}
        r['native_mim_controls']=cap_controls;assert len(cap_controls)==3
        for tag,name,inputs,outputs,bias in [('xbd','nssoc_cdr_data_buffer_v4',['udp','udn'],['xp','xn'],'ird'),('xbs','nssoc_cdr_select_buffer_v4',['usp','usn'],['yp','yn'],'irs')]:
            actual=next(f for f in top_rows if f[0]==tag);assert actual==[tag,*inputs,*outputs,'avdd','avss','sub',bias,name]
            unit=sections[name];m=dict(zip(unit['ports'],['xcmp.'+n for n in inputs+outputs]+['avdd','0','0',bias],strict=True))
            def mapped(n):return m.get(n,'xcmp.'+tag+'.'+n)
            added=[0,0]
            for f in unit['rows']:
                path='xcmp.'+tag+'.'+f[0]
                if len(f)>5 and f[5]=='npn13g2':
                    params=dict(x.split('=')for x in f[6:]);assert params.keys()=={'nx'};devices[path]=dict(nodes=[mapped(n)for n in f[1:5]],nx=int(params['nx']));added[0]+=1
                else:assert f[4]=='rppd';resistors[path]=dict(nodes=[mapped(n)for n in f[1:4]],parameters=f[5:]);added[1]+=1
            assert added==[4,3 if tag=='xbd'else 4]
        for f in conversion:resistors['xcmp.'+f[0]]=dict(nodes=['0'if n in ('sub','avss')else'xcmp.'+n for n in f[1:4]],parameters=f[5:])
        assert len(devices)==57 and len(resistors)==47 and sum('ptap1'in f for f in rows)==27
        assert sum(f[0].startswith('r')for f in rows)==4020 and sum(f[0].startswith('c')for f in rows)==2641
        nodes={n for x in devices.values()for n in x['nodes']}|{'qp','qn','adp','adn','bdp','bdn','cp','cn','avdd','ira','irb','irx','xcmp.aqp','xcmp.aqn','xcmp.bqp','xcmp.bqn','xcmp.xp','xcmp.xn','xcmp.yp','xcmp.yn'};nodes.discard('0')
        vectors=['v('+n+')'for n in sorted(nodes)]+['@q.'+n+'.qnpn13g2[ic]'for n in devices]
        a,b=primitive.prbs(0x7f),primitive.prbs(0x5d);bits=[x^y for x,y in zip(a,b,strict=True)];assert set(zip(a,b))=={(0,0),(0,1),(1,0),(1,1)};models=lib/'models/models'
        deck=['NSSOC native connected sampled comparison',f'.lib "{models}/cornerHBT.lib" hbt_typ',f'.lib "{models}/cornerRES.lib" {c["res"]}',f'.lib "{models}/cornerCAP.lib" {c["cap"]}',f'.include "{SOURCE}"',f'.include "{model}"',f'.include "{WRAPPER}"',f'.temp {c["temperature"]}',
            '.options reltol=1e-4 abstol=1e-12 klu',f'VDD avdd 0 PWL(0 0 500p {2.5*scale:.12g})','IRA avdd ira PWL(0 0 500p .0005)','IRB avdd irb PWL(0 0 500p .0005)','IRX avdd irx PWL(0 0 500p .0005)','IRD avdd ird PWL(0 0 500p .001)','IRS avdd irs PWL(0 0 500p .001)',
            'VADP adp0 0 '+data(a,1.65*scale,.15*scale),'VADN adn0 0 '+data([1-x for x in a],1.65*scale,.15*scale),'VBDP bdp0 0 '+data(b,1.65*scale,.15*scale),'VBDN bdn0 0 '+data([1-x for x in b],1.65*scale,.15*scale),
            'VCP cp0 0 '+clock(scale,True,args.case=='clock_stopped'),'VCN cn0 0 '+clock(scale,False,args.case=='clock_stopped'),
            'RADP adp0 adp 10','RADN adn0 adn 10','RBDP bdp0 bdp 10','RBDN bdn0 bdn 10','RCP cp0 cp 10','RCN cn0 cn 10',
            f'XCMP adp adn bdp bdn cp cn {output[0]} {output[1]} avdd 0 0 ira irb irx ird irs 0 nssoc_cdr_sampled_compare_buffered_v4','CAQP xcmp.aqp 0 150f','CAQN xcmp.aqn 0 150f','CBQP xcmp.bqp 0 150f','CBQN xcmp.bqn 0 150f','CQP qp 0 50f','CQN qn 0 50f',
            '.control',f'pre_osdi {lib/"models/r3_cmc.osdi"}','set wr_singlescale','set wr_vecnames','set numdgt=16','save '+' '.join(vectors)]
        for name in devices:
            q='q.'+name+'.qnpn13g2';deck.extend([f'alter @{q}[off] = 1',f'echo NSSOC_NATIVE_FLAG_BEGIN {q}',f'show {q} : off','echo NSSOC_NATIVE_FLAG_END'])
        deck+=['op','wrdata op.dat '+' '.join(vectors),f'tran {STEP:.14g} {STOP:.14g} 0 {STEP:.14g}','wrdata wave.dat '+' '.join(vectors),'echo NSSOC_BACKEND_OPTIONS_BEGIN','option','echo NSSOC_BACKEND_OPTIONS_END','quit','.endc','.end']
        native=out/'native';native.mkdir();(native/'bench.cir').write_text('\n'.join(deck)+'\n');(native/'spinit').write_text('set num_threads=1\n')
        protected={str(f):sha(f)for f in [Path(__file__),SOURCE,WRAPPER,model,pinpath,ROOT/'scripts/cloud_cdr_xor.py',ROOT/'scripts/cloud_vbic_tree32_backend.py',engine,native/'bench.cir',*lib.rglob('*')]if f.is_file()}
        r.update(devices=devices,resistors=resistors,vectors=vectors,source_bits=[a,b],expected_xor=bits,source_bits_sha256=[hashlib.sha256(bytes(x)).hexdigest()for x in (a,b)],expected_xor_sha256=hashlib.sha256(bytes(bits)).hexdigest(),protected_inputs=protected);save()
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
            for phase in (.6,.75,.9):signed.append(float(np.interp(edge+phase*UI,t,delta))*sign)
            ids=np.flatnonzero((t>=edge)&(t<=edge+.95*UI));bad=ids[delta[ids]*sign<.1]
            delay.append(0. if not len(bad)else float(t[bad[-1]]-edge+STEP))
        checks={}
        for name,dev in devices.items():
            vc,vb,ve,_=map(v,dev['nodes']);ic=d['@q.'+name+'.qnpn13g2[ic]'];checks[name]=dict(minimum_active_vce_v=float((vc-ve)[active].min()),maximum_alltime_abs_vce_v=float(abs(vc-ve).max()),maximum_alltime_abs_vbe_v=float(abs(vb-ve).max()),maximum_alltime_abs_ic_per_emitter_a=float(abs(ic).max()/dev['nx']))
        safe=all(x['minimum_active_vce_v']>=.4 and x['maximum_alltime_abs_vce_v']<=1.6 and x['maximum_alltime_abs_vbe_v']<=1. and x['maximum_alltime_abs_ic_per_emitter_a']<.003 for x in checks.values())
        r['native_mim_voltage_checks']={name:dict(maximum_alltime_abs_v=float(abs(v(dev['nodes'][0])-v(dev['nodes'][1])).max()),limit_v=1.6)for name,dev in r['native_mim_caps'].items()}
        safe=safe and all(x['maximum_alltime_abs_v']<=x['limit_v']for x in r['native_mim_voltage_checks'].values())
        tails={name:float(d['@q.'+name+'.qnpn13g2[ic]'][active].min())for name in ('xcmp.xsa.xm.xt','xcmp.xsa.xs.xt','xcmp.xsb.xm.xt','xcmp.xsb.xs.xt','xcmp.xbd.xt','xcmp.xbs.xt')};safe=safe and min(tails.values())>=.0005
        sampler_checks={}
        for letter,source_bits in [('a',a),('b',b)]:
            dd=v('xcmp.'+letter+'qp')-v('xcmp.'+letter+'qn');margins=[];delays=[]
            for i,bit in enumerate(source_bits):
                edge=START+(i+.5)*UI;sign=2*bit-1
                for phase in (.3,.6,.9):margins.append(float(np.interp(edge+phase*UI,t,dd))*sign)
                ids=np.flatnonzero((t>=edge)&(t<=edge+.95*UI));bad=ids[dd[ids]*sign<.1]
                delays.append(0. if not len(bad)else float(t[bad[-1]]-edge+STEP))
            sampler_checks[letter]=dict(samples=len(margins),minimum_signed_margin_v=min(margins),wrong_sign_samples=sum(x<=0 for x in margins),below_100mv_samples=sum(x<.1 for x in margins),maximum_clock_to_valid_s=max(delays),passed=min(margins)>=.1 and max(delays)<=.3*UI)
        r['loaded_sampler_checks']=sampler_checks
        r['buffer_stage_observations']={}
        for label,pn,nn,source_bits in [('data','xcmp.xp','xcmp.xn',a),('select','xcmp.yp','xcmp.yn',b)]:
            dd=v(pn)-v(nn);stage_delays=[];stage_margins=[]
            for i,bit in enumerate(source_bits):
                edge=START+(i+.5)*UI;sign=2*bit-1
                ids=np.flatnonzero((t>=edge)&(t<=edge+.95*UI));bad=ids[dd[ids]*sign<.1]
                stage_delays.append(0. if not len(bad)else float(t[bad[-1]]-edge+STEP))
                for phase in (.3,.6,.9):stage_margins.append(float(np.interp(edge+phase*UI,t,dd))*sign)
            r['buffer_stage_observations'][label]=dict(maximum_clock_to_100mv_s=max(stage_delays),minimum_signed_sample_v=min(stage_margins),below100mv_samples=sum(x<.1 for x in stage_margins),clock_to_100mv_by_bit_s=stage_delays)
        r['native_interface_observations']={name:dict(commonmode_v=[float(((v(p)+v(n))/2)[active].min()),float(((v(p)+v(n))/2)[active].max())],differential_v=[float((v(p)-v(n))[active].min()),float((v(p)-v(n))[active].max())])for name,p,n in [('sample_a','xcmp.aqp','xcmp.aqn'),('sample_b','xcmp.bqp','xcmp.bqn'),('xor_data','xcmp.xp','xcmp.xn'),('xor_select','xcmp.yp','xcmp.yn'),('data_buffer_input','xcmp.udp','xcmp.udn'),('select_buffer_input','xcmp.usp','xcmp.usn')]}
        data_ok=min(signed)>=.1 and max(delay)<=.6*UI and all(x['passed']for x in sampler_checks.values())
        r.update(samples=len(signed),minimum_signed_margin_v=min(signed),wrong_sign_samples=sum(x<=0 for x in signed),below_100mv_samples=sum(x<.1 for x in signed),maximum_clock_to_valid_s=max(delay),clock_to_valid_by_bit_s=delay,device_checks=checks,minimum_active_tail_current_a=tails,devices_passed=safe,data_passed=data_ok,
            observed_output_common_mode_v=[float(((v('qp')+v('qn'))/2)[active].min()),float(((v('qp')+v('qn'))/2)[active].max())],observed_output_differential_v=[float(delta[active].min()),float(delta[active].max())])
        assert len(signed)==768 and all(sha(Path(f))==h for f,h in protected.items());r['sources_unchanged']=True
        fault=args.case in ('swap_output','clock_stopped');r['actual_fault_detected']=fault and not data_ok
        passed=r['actual_fault_detected']if fault else safe and data_ok
        r['status']='PASS_NATIVE_CONNECTED_SAMPLED_COMPARISON_NOT_PHASE_DETECTOR_OR_CDR'if passed else'REJECTED_NATIVE_CONNECTED_SAMPLED_COMPARISON'
        assert passed,'Actual connected sampler/XOR data/device limits failed; preserve loaded trajectories'
    except BaseException as error:
        if r['status']=='RUNNING':r['status']='FAIL_OR_ERROR'
        r['error']=repr(error);raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save();print(r['status'],flush=True)
if __name__=='__main__':main()
