#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native four-sampler/two-comparator retimed phase detector, no recovered clock."""
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

PD=ROOT/'hw/soc/analog/pcie/cdr_retimed_pd_vi_v1.spice'
PD_SHA='5d2f451b0c5d428e7e96bb1b06929e7960a384777ac6b4e6a197c8334b5fcf41'
VI=ROOT/'hw/soc/analog/pcie/cdr_vi_hbt_v1.spice'
VI_SHA='9f13b4eeca782f34feb3a858937de871f61b2e7ab5a06ffc43ecfdfb5f5268ef'

def shifted_data(bits,cm,amp,offset):
    value=lambda b:cm+amp*(2*b-1)
    points=[(0,0),(.5e-9,value(bits[0]))]
    for i in range(1,256):
        if bits[i]!=bits[i-1]:points.extend([(START+i*UI+offset,value(bits[i-1])),(START+i*UI+offset+5e-12,value(bits[i]))])
    points.append((STOP,value(bits[-1])));return pwl(points)

def hbt_size(fields,physical):
    params=dict(f.split('=')for f in fields);assert len(params)==len(fields),'Duplicate native HBT parameter'
    assert set(params)==({'nx','we','le'}if physical else{'nx'}),'Unexpected native HBT parameter set'
    if physical:assert params['we']=='0.07u'and params['le']=='0.9u','Changed extracted HBT emitter geometry'
    nx=int(params['nx']);assert nx>0 and str(nx)==params['nx']
    return nx

def hbt_parameter_controls():
    assert hbt_size(['nx=2'],False)==2
    assert hbt_size(['nx=6','we=0.07u','le=0.9u'],True)==6
    rejected=[]
    for label,fields,physical in [('wrong_width',['nx=6','we=0.08u','le=0.9u'],True),('wrong_length',['nx=6','we=0.07u','le=1.0u'],True),('missing_area',['we=0.07u','le=0.9u'],True),('unknown_parameter',['nx=2','m=2'],False),('duplicate',['nx=2','nx=3'],False)]:
        try:hbt_size(fields,physical)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Malformed native HBT accepted: '+label)
    return dict(positive=2,rejected=rejected)

def bind_pd(texts,ports):
    cells={};current=None
    for text in texts:
        for line in text.lower().splitlines():
            f=line.split()
            if not f or f[0].startswith('*'):continue
            if f[0]=='.subckt':
                assert current is None and f[1]not in cells;current=f[1];cells[current]=dict(ports=f[2:],rows=[])
            elif f[0]=='.ends':assert current==f[1];current=None
            else:assert current is not None;cells[current]['rows'].append(f)
        assert current is None
    devices={};resistors={};caps={};contacts={};wire_counts=dict(R=0,C=0)
    def visit(cell,path,terminals,stack):
        assert cell not in stack
        unit=cells[cell];mapping=dict(zip(unit['ports'],terminals,strict=True));seen=set()
        def node(n):return '0'if n=='0'else mapping.get(n,path+'.'+n)
        for f in unit['rows']:
            assert f[0]not in seen;seen.add(f[0]);name=path+'.'+f[0]
            if f[0][0]in ('r','c'):
                assert len(f)==4;wire_counts[f[0][0].upper()]+=1;continue
            assert f[0].startswith('x')
            if len(f)>5 and f[5]=='npn13g2':
                nx=hbt_size(f[6:],cell=='nssoc_cdr_xor54_wire_v4')
                devices[name]=dict(nodes=[node(n)for n in f[1:5]],nx=nx)
            elif len(f)>4 and f[4]=='rppd':resistors[name]=dict(nodes=[node(n)for n in f[1:4]],parameters=f[5:])
            elif len(f)>3 and f[3]=='cap_cmim':caps[name]=dict(nodes=[node(n)for n in f[1:3]],parameters=f[4:])
            elif len(f)>3 and f[3]=='ptap1':contacts[name]=dict(nodes=[node(n)for n in f[1:3]],parameters=f[4:])
            else:assert f[-1]in cells;visit(f[-1],name,[node(n)for n in f[1:-1]],stack+[cell])
    visit('nssoc_cdr_retimed_pd_vi_v1','xpd',ports,[])
    assert len(devices)==122 and len(resistors)==102 and len(caps)==11 and len(contacts)==54
    assert wire_counts==dict(R=8040,C=5282)
    return devices,resistors,caps,contacts,wire_counts

def main():
    choices=['nominal_early','nominal_late','hot_early','hot_late','cold_early','cold_late','constant_zero','constant_one','swap_comparisons','wrong_edge','clock_stopped','vi_swap','vi_bias_off']
    parser=argparse.ArgumentParser();parser.add_argument('--case',choices=choices,required=True);args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/('cloud-cdr-pd-vi-'+args.case);out.mkdir(exist_ok=False);reports.OUT=out
    corner='hot_low'if args.case.startswith('hot_')else'cold_high'if args.case.startswith('cold_')else'nominal'
    c=pump.CORNERS[corner];scale=c['scale'];offset=(-.15 if args.case.endswith('_early')else.15)*UI
    bits=([0]*256 if args.case=='constant_zero'else[1]*256 if args.case=='constant_one'else primitive.prbs(0x7f))
    constant=args.case.startswith('constant_');fault=args.case in ('swap_comparisons','wrong_edge','clock_stopped','vi_swap','vi_bias_off')
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=args.case,accepted=False,full_phy_accepted=False,cdr_accepted=False,physical_layout_matches=False,
        scope='Four real samplers, four native buffers, two fresh-wire XORs and directly connected8HBT V/I stage:122HBT/102rppd/11MIM/54bodycontacts,8040wireR/5282wireC. Original bits and explicit early/late data transition oracle. External8GHz clock,10ohmsources,500uA sampler/XOR references,1mA buffer references,250uA converter references,150fF each sampler output,50fF each XOR output. HBTtyp models with nominal/hot/cold supply/resistor/cap conditions. Native converter directly loads XOR outputs and drives a40um-square differential MIM capacitor. No ideal internal bit regeneration, recovered clock, full loop or whole-PHY acceptance.',data_offset_s=offset,corner=corner)
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        assert sha(SOURCE)==SOURCE_SHA and sha(WRAPPER)==WRAPPER_SHA and sha(PD)==PD_SHA and sha(VI)==VI_SHA
        assert sha(ROOT/'scripts/cloud_cdr_xor.py')=='3ec870fa6a30d9f94038368d6b74c984c314c2d7248ecaab94c687867587fabe'
        r['readback_controls']=readback_controls()
        r['hbt_parameter_controls']=hbt_parameter_controls()
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
        text=PD.read_text()
        if args.case=='wrong_edge':
            old='XSD dup dun dqp dqn cp cn';assert text.count(old)==1;text=text.replace(old,'XSD dup dun dqp dqn cn cp')
        if args.case=='vi_swap':
            old='XVI xp xn yp yn vip vin';assert text.count(old)==1;text=text.replace(old,'XVI yp yn xp xn vip vin')
        actual=out/'actual-pd.spice';actual.write_text(text)
        outputs=['yp','yn','xp','xn']if args.case=='swap_comparisons'else['xp','xn','yp','yn']
        biases=['ira','irb','irc','ird','irx','iry','ibda','ibdc','ibs0','ibs1']
        ports=['dp','dn','cp','cn',*outputs,'avdd','0','0',*biases,'0','vip','vin','irvx','irvy']
        devices,resistors,caps,contacts,wire_counts=bind_pd([SOURCE.read_text(),WRAPPER.read_text(),model.read_text(),VI.read_text(),text],ports)
        nodes={n for group in (devices,resistors,caps,contacts)for dev in group.values()for n in dev['nodes']}|{'dp','dn','cp','cn','xp','xn','yp','yn','avdd',*biases};nodes.discard('0')
        assert {f'xpd.{tag}q{leg}'for tag in 'abcd'for leg in 'pn'}<=nodes
        vectors=['v('+n+')'for n in sorted(nodes)]+['@q.'+n+'.qnpn13g2[ic]'for n in devices]
        models=lib/'models/models'
        deck=['NSSOC actual retimed phase detector',f'.lib "{models}/cornerHBT.lib" hbt_typ',f'.lib "{models}/cornerRES.lib" {c["res"]}',f'.lib "{models}/cornerCAP.lib" {c["cap"]}',f'.include "{SOURCE}"',f'.include "{model}"',f'.include "{WRAPPER}"',f'.include "{actual}"',f'.include "{VI}"',f'.temp {c["temperature"]}',
            '.options reltol=1e-4 abstol=1e-12 klu',f'VDD avdd 0 PWL(0 0 500p {2.5*scale:.12g})']
        deck += [f'I_{bias} avdd {bias} PWL(0 0 500p '+('.001)'if bias.startswith('ib')else'.0005)')for bias in biases]
        deck += [f'I_{bias} avdd {bias} PWL(0 0 500p '+('0)'if args.case=='vi_bias_off'else'.00025)')for bias in ('irvx','irvy')]
        deck += ['VDP dp0 0 '+shifted_data(bits,1.65*scale,.15*scale,offset),'VDN dn0 0 '+shifted_data([1-b for b in bits],1.65*scale,.15*scale,offset),
            'VCP cp0 0 '+clock(scale,True,args.case=='clock_stopped'),'VCN cn0 0 '+clock(scale,False,args.case=='clock_stopped'),
            'RDP dp0 dp 10','RDN dn0 dn 10','RCP cp0 cp 10','RCN cn0 cn 10','XPD '+' '.join(ports)+' nssoc_cdr_retimed_pd_vi_v1']
        deck += [f'C_{tag}{leg} xpd.{tag}q{leg} 0 150f'for tag in 'abcd'for leg in 'pn']
        deck += [f'C_{node} {node} 0 50f'for node in ('xp','xn','yp','yn')]
        deck += ['.control',f'pre_osdi {lib/"models/r3_cmc.osdi"}','set wr_singlescale','set wr_vecnames','set numdgt=16','save '+' '.join(vectors)]
        for name in devices:
            q='q.'+name+'.qnpn13g2';deck += [f'alter @{q}[off] = 1',f'echo NSSOC_NATIVE_FLAG_BEGIN {q}',f'show {q} : off','echo NSSOC_NATIVE_FLAG_END']
        deck += ['op','wrdata op.dat '+' '.join(vectors),f'tran {STEP:.14g} {STOP:.14g} 0 {STEP:.14g}','wrdata wave.dat '+' '.join(vectors),'echo NSSOC_BACKEND_OPTIONS_BEGIN','option','echo NSSOC_BACKEND_OPTIONS_END','quit','.endc','.end']
        native=out/'native';native.mkdir();(native/'bench.cir').write_text('\n'.join(deck)+'\n');(native/'spinit').write_text('set num_threads=1\n')
        protected={str(f):sha(f)for f in [Path(__file__),SOURCE,WRAPPER,PD,VI,actual,model,pinpath,ROOT/'scripts/cloud_cdr_xor.py',ROOT/'scripts/cloud_vbic_tree32_backend.py',engine,native/'bench.cir',*lib.rglob('*')]if f.is_file()}
        r.update(devices=devices,resistors=resistors,native_caps=caps,contacts=contacts,wire_counts=wire_counts,vectors=vectors,source_bits=bits,source_bits_sha256=hashlib.sha256(bytes(bits)).hexdigest(),protected_inputs=protected);save()
        env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(native),OMP_NUM_THREADS='1')
        with(native/'native.log').open('w')as log:proc=subprocess.run([str(engine),'-n','-b','bench.cir'],cwd=native,env=env,stdout=log,stderr=subprocess.STDOUT)
        log=(native/'native.log').read_text();opts,notes,_=backend_readback(log,'klu');r.update(returncode=proc.returncode,native_options=opts,diagnostics=notes);save();assert proc.returncode==0 and not notes
        flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',log)
        assert [n for n,_ in flags]==['q.'+n+'.qnpn13g2'for n in devices]and all(re.findall(r'(?m)^\s*off\s+([01])\s*$',s)==['1']for _,s in flags)
        r['native_flags_verified']=len(flags)
        op=np.loadtxt(native/'op.dat',skiprows=1);assert op.size==len(vectors)+1 and np.isfinite(op).all()and abs(op).max()<1e-9;r['zero_source_op_maximum']=float(abs(op).max())
        with(native/'wave.dat').open()as f:header=f.readline().lower().split()
        assert header==['time',*vectors]
        wave=np.loadtxt(native/'wave.dat',skiprows=1);t=wave[:,0];assert wave.shape[1]==len(vectors)+1 and np.isfinite(wave).all()and t[0]==0 and abs(t[-1]-STOP)<1e-15 and np.all(np.diff(t)>0)and np.diff(t).max()<=STEP*1.00001
        d={n:wave[:,i+1]for i,n in enumerate(vectors)};active=t>=START
        def v(n):return np.zeros(len(t))if n=='0'else d['v('+n+')']
        def measure(p,n,expected,edges,phases,limit):
            delta=v(p)-v(n);signed=[];delays=[]
            for bit,edge in zip(expected,edges,strict=True):
                sign=2*bit-1
                for phase in phases:signed.append(float(np.interp(edge+phase*UI,t,delta))*sign)
                ids=np.flatnonzero((t>=edge)&(t<=edge+.95*UI));bad=ids[delta[ids]*sign<.1]
                delays.append(0. if not len(bad)else float(t[bad[-1]]-edge+STEP))
            return dict(samples=len(signed),minimum_signed_margin_v=min(signed),wrong_sign_samples=sum(x<=0 for x in signed),below_100mv_samples=sum(x<.1 for x in signed),maximum_clock_to_valid_s=max(delays),clock_to_valid_by_bit_s=delays,passed=min(signed)>=.1 and max(delays)<=limit*UI)
        indices=range(1,256);current=[bits[i]for i in indices];previous=[bits[i-1]for i in indices];edge_bits=current if offset<0 else previous
        rising=[START+(i+.5)*UI for i in indices];falling=[START+i*UI for i in indices]
        expected=dict(a=current,b=edge_bits,c=previous,d=edge_bits)
        sampler_checks={tag:measure('xpd.'+tag+'qp','xpd.'+tag+'qn',expected[tag],falling if tag=='b'else rising,(.3,.6,.9),.3)for tag in 'abcd'}
        xbits=[a^b for a,b in zip(current,edge_bits,strict=True)];ybits=[a^b for a,b in zip(previous,edge_bits,strict=True)]
        comparisons=dict(x=measure('xp','xn',xbits,rising,(.6,.75,.9),.6),y=measure('yp','yn',ybits,rising,(.6,.75,.9),.6))
        delta=(v('xp')-v('xn'))-(v('yp')-v('yn'));window=(t>=START+8*UI)&(t<=START+255*UI)
        area=float(np.trapezoid(delta[window],t[window]));average=area/float(t[window][-1]-t[window][0]);direction=1 if offset>0 else-1
        phase_ok=abs(average)<=.01 if constant else direction*average>=.03
        checks={}
        for name,dev in devices.items():
            vc,vb,ve,_=map(v,dev['nodes']);ic=d['@q.'+name+'.qnpn13g2[ic]'];checks[name]=dict(minimum_active_vce_v=float((vc-ve)[active].min()),maximum_alltime_abs_vce_v=float(abs(vc-ve).max()),maximum_alltime_abs_vbe_v=float(abs(vb-ve).max()),maximum_alltime_abs_ic_per_emitter_a=float(abs(ic).max()/dev['nx']))
        safe=all(x['minimum_active_vce_v']>=.4 and x['maximum_alltime_abs_vce_v']<=1.6 and x['maximum_alltime_abs_vbe_v']<=1 and x['maximum_alltime_abs_ic_per_emitter_a']<.003 for x in checks.values())
        tail_names=[f'xpd.xs{tag}.x{stage}.xt'for tag in 'abcd'for stage in ('m','s')]+['xpd.'+tag+'.xt'for tag in ('xda','xdc','xs0','xs1')]
        tails={n:float(d['@q.'+n+'.qnpn13g2[ic]'][active].min())for n in tail_names};safe=safe and min(tails.values())>=.0005
        cap_checks={name:dict(maximum_alltime_abs_v=float(abs(v(dev['nodes'][0])-v(dev['nodes'][1])).max()),limit_v=1.6)for name,dev in caps.items()};safe=safe and all(x['maximum_alltime_abs_v']<=1.6 for x in cap_checks.values())
        data_ok=all(x['passed']for x in sampler_checks.values())and all(x['passed']for x in comparisons.values())and phase_ok
        r.update(expected_samples=expected,expected_comparisons=dict(x=xbits,y=ybits),sampler_checks=sampler_checks,comparisons=comparisons,phase_average_v=average,phase_passed=phase_ok,phase_gate=dict(minimum_signed_v=.03,constant_maximum_abs_v=.01,window_s=[START+8*UI,START+255*UI]),device_checks=checks,minimum_active_tail_current_a=tails,native_cap_voltage_checks=cap_checks,devices_passed=safe,data_passed=data_ok)
        # Direct native collector currents, with physical input-to-output
        # polarity. No Boolean reconstruction from ideal phase decisions.
        def ic(name):return d['@q.xpd.xvi.'+name+'.qnpn13g2[ic]']
        current=(ic('xxp')+ic('xyn'))-(ic('xxn')+ic('xyp'))
        output_delta=v('vip')-v('vin')
        def mean(values):return float(np.trapezoid(values[window],t[window])/(t[window][-1]-t[window][0]))
        mean_current=mean(current);mean_output=mean(output_delta)
        vi_phase_ok=(abs(mean_current)<=5e-6 and abs(mean_output)<=.002)if constant else(direction*mean_current>=50e-6 and direction*mean_output>=.005)
        vi_tails={tag:float(ic(tag)[active].min())for tag in ('xtx','xty')}
        vi_bias_ok=min(vi_tails.values())>=.0001
        vi_ok=vi_phase_ok and vi_bias_ok
        r['vi']=dict(mean_signed_current_a=mean_current,mean_output_difference_v=mean_output,minimum_active_tail_current_a=vi_tails,phase_passed=vi_phase_ok,bias_passed=vi_bias_ok,passed=vi_ok,phase_limits=dict(minimum_signed_current_a=50e-6,minimum_signed_voltage_v=.005,constant_maximum_abs_current_a=5e-6,constant_maximum_abs_voltage_v=.002),output_commonmode_v=[float(((v('vip')+v('vin'))/2)[active].min()),float(((v('vip')+v('vin'))/2)[active].max())],native_mim_geometry_um=[40,40],real_input_loading=True,actual_filter_connection=True,closed_loop=False)
        r['interface_observations']={name:dict(commonmode_v=[float(((v(p)+v(n))/2)[active].min()),float(((v(p)+v(n))/2)[active].max())],differential_v=[float((v(p)-v(n))[active].min()),float((v(p)-v(n))[active].max())])for name,p,n in [('data_a','xpd.adp','xpd.adn'),('data_c','xpd.cdp','xpd.cdn'),('select0','xpd.s0p','xpd.s0n'),('select1','xpd.s1p','xpd.s1n')]}
        assert all(sha(Path(f))==digest for f,digest in protected.items());r['sources_unchanged']=True;r['actual_fault_detected']=fault and not(data_ok and vi_ok)
        passed=r['actual_fault_detected']if fault else safe and data_ok and vi_ok
        r['status']='PASS_NATIVE_PD_VI_SCREEN_NOT_CLOSED_LOOP_OR_PHYSICAL_ACCEPTANCE'if passed else'REJECTED_NATIVE_PD_VI'
        assert passed,'Actual retimed sample identity, loaded comparison, phase-to-current, filter polarity or device gate failed'
    except BaseException as error:
        if r['status']=='RUNNING':r['status']='FAIL_OR_ERROR'
        r['error']=repr(error);raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save();print(r['status'],flush=True)
if __name__=='__main__':main()
