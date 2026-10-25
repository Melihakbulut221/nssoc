#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native XOR reference/tail repair with unchanged data/select/load topology; not full PD closure."""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import cloud_cdr_xor as primitive
import cloud_pll_pump_current as pump
from cloud_cdr_sampler_hybrid_tail import data,UI,START,STOP,STEP
from cloud_vbic_tree32_backend import backend_readback,readback_controls
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hw/soc/analog/pcie/cdr_xor_core_hybrid_tail_v2.spice'
SOURCE_SHA='47dbcf055d732456f9b5c199e8deedd0a2fc402546c5c464ab315862bd70b660'
WRAPPER=ROOT/'hw/soc/analog/pcie/cdr_xor_hybrid_tail_v2.spice'
WRAPPER_SHA='39d055605d72b6aa586b058c5492e17ae5bffe2dffc0942c07258dcb7137cddc'

def source_check(text):
    import cloud_cdr_xor_hybrid_tail_v1 as baseline
    prior=ROOT/'hw/soc/analog/pcie/cdr_xor_core_hybrid_tail_v1.spice'
    assert sha(prior)=='acd8a6e20db2d973c870d9245fb359d55ff0351ff843198e3c278e3d9bb135d1'
    baseline.source_check(prior.read_text())
    clean=lambda s:'\n'.join(l for l in s.splitlines()if l and not l.startswith('*'))+'\n'
    expected=clean(prior.read_text());assert expected.count('nx=3 ')==12
    expected=expected.replace('nssoc_cdr_xor_core_hybrid_tail_v1','nssoc_cdr_xor_core_hybrid_tail_v2').replace('nx=3 ','nx=4 ')
    assert clean(text)==expected,'Unexpected change outside twelve data HBT finger counts'
    prior_wrap=ROOT/'hw/soc/analog/pcie/cdr_xor_hybrid_tail_v1.spice'
    assert sha(prior_wrap)=='3a8098d153edcfc4b4a82e0852122665628338b0717b94fe76bb86097127e656'
    assert clean(WRAPPER.read_text())==clean(prior_wrap.read_text()).replace('hybrid_tail_v1','hybrid_tail_v2')
    return dict(status='PASS_ONLY_TWELVE_DATA_HBT_NX3_TO_NX4_CHANGES',unchanged_selectors_mos_reference_tails_loads_body_network=True)

def bind(text,outputs):
    rows=[s.lower().split()for s in text.splitlines()if s and not s.startswith('*')]
    ports=['sub','ap','an','bp','bn','iref','sp','sn','on','op','avss','avdd']
    assert rows[0]==['.subckt','nssoc_cdr_xor_core_hybrid_tail_v2',*ports]
    assert rows[-1]==['.ends','nssoc_cdr_xor_core_hybrid_tail_v2']and len(rows)==56
    mapping=dict(zip(ports,['0','dp','dn','dn','dp','iref','ep','en',*outputs,'0','avdd'],strict=True))
    def node(n):return mapping.get(n,'xgate.xcore.'+n)
    hbts={};mos={};resistors={};taps={};seen=set()
    for f in rows[1:-1]:
        name='xgate.xcore.'+f[0];assert f[0].startswith('x')and name not in seen;seen.add(name)
        if len(f)>5 and f[5]=='npn13g2':
            p=dict(v.split('=')for v in f[6:]);nx=int(p['nx']);assert p==dict(nx=str(nx),we='0.07u',le='0.9u')and nx in (4,6)
            hbts[name]=dict(nodes=[node(n)for n in f[1:5]],nx=nx)
        elif len(f)>5 and f[5]=='sg13_lv_nmos':
            p=dict(v.split('=')for v in f[6:]);assert f[0]in ('xd0009','xd0049','xd0053')and p==dict(w='8u'if f[0]=='xd0009'else'64u',l='.3u',ng='1')
            mos[name]=dict(nodes=[node(n)for n in f[1:5]],parameters=p)
        elif len(f)>4 and f[4]=='rppd':resistors[name]=dict(nodes=[node(n)for n in f[1:4]],parameters=f[5:])
        else:
            assert f[3]=='ptap1';taps[name]=dict(nodes=[node(n)for n in f[1:3]],parameters=f[4:])
    assert len(hbts)==16 and sum(x['nx']for x in hbts.values())==72 and len(resistors)==8 and len(taps)==27
    assert set(mos)=={'xgate.xcore.xd0009','xgate.xcore.xd0049','xgate.xcore.xd0053'}
    return hbts,mos,resistors,taps

def main():
    p=argparse.ArgumentParser();p.add_argument('--case',choices=['nominal','hot_low','cold_high','swap_output','bias_off'],required=True);a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/('cloud-cdr-xor-hybrid-tail-v2-'+a.case);out.mkdir(exist_ok=False);reports.OUT=out
    c=pump.CORNERS[a.case if a.case in ('nominal','hot_low','cold_high')else'nominal'];scale=c['scale']
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],case=a.case,accepted=False,full_phy_accepted=False,physical_layout_matches=False,qualified_pex=False,
        scope='Native16HBT/3LVNMOS/8rppd/27finite-body-contact XOR schematic screening. V1 three HBT reference/tails replaced, then V2 twelve data HBTs Nx3 to Nx4; selectors/MOS/load/body topology unchanged. Original500uA reference,2V data and1.3V selector common modes,300mV differential swings,10ohm input sources,50fF/output,256bits/34.25ns. Original three sampling phases plus settling and stricter VBE bounds. Ideal boundaries are NOT extracted parent captures or loads. No layout/RC, full process matrix, closed loop or fullPHY acceptance.')
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        assert sha(SOURCE)==SOURCE_SHA and sha(WRAPPER)==WRAPPER_SHA;r['source_delta_guard']=source_check(SOURCE.read_text())
        faults=[]
        for label,bad in [('changed_data',SOURCE.read_text().replace('nx=4','nx=5',1)),('changed_load',SOURCE.read_text().replace('l=8.0u','l=7.0u',1)),('wrong_tail',SOURCE.read_text().replace('w=64u','w=8u',1))]:
            try:source_check(bad)
            except AssertionError:faults.append(label)
            else:raise AssertionError('Accepted source mutation '+label)
        assert len(faults)==3;r['source_mutations']=faults;r['readback_controls']=readback_controls()
        fetch(pump.BASE+'cloud-results-39029337682-1-pll-pump-current/pll-pump-current-39029337682-1.summary.json',primitive.SUMMARY,out/'models-pin.json')
        pin=json.loads((out/'models-pin.json').read_text());wanted=[n for n in pin['outputs']if n.startswith('source/model-sources/')]+['source-pin.json','source/runtime/patched-ngspice']
        old,proof=reports.restore_report('pll-pump-current',39029337682,primitive.SUMMARY,primitive.PARTS,out/'source',wanted);assert old==pin;r['models_source']=proof
        original=json.loads((out/'source/source-pin.json').read_text());assert sha(out/'source/source-pin.json')==pump.SUMMARY
        lib=out/'models';shutil.copytree(out/'source/source/model-sources',lib)
        assert all(sha(lib/n)==v for n,v in original['preparation']['model_sources'].items())
        engine=out/'source/source/runtime/patched-ngspice';engine.chmod(0o755);assert sha(engine)=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
        outputs=('qn','qp')if a.case=='swap_output'else('qp','qn');hbts,mos,resistors,taps=bind(SOURCE.read_text(),outputs)
        nodes={n for d in [*hbts.values(),*mos.values(),*resistors.values(),*taps.values()]for n in d['nodes']}|{'qp','qn','dp','dn','ep','en','avdd','iref'};nodes.discard('0')
        vectors=['v('+n+')'for n in sorted(nodes)]+['@q.'+n+'.qnpn13g2[ic]'for n in hbts]+['@n.'+n+'.nsg13_lv_nmos[ids]'for n in mos]
        bits=primitive.prbs(0x7f);select_bits=primitive.prbs(0x5d);expected_bits=[a^b for a,b in zip(bits,select_bits,strict=True)];assert set(zip(bits,select_bits))=={(0,0),(0,1),(1,0),(1,1)};models=lib/'models/models';osdis=[]
        for name in ('psp103.osdi','psp103_nqs.osdi'):
            found=list(lib.rglob(name));assert len(found)==1;osdis.append(found[0])
        current=0 if a.case=='bias_off'else .0005
        deck=['NSSOC native hybrid XOR component characterization',f'.lib "{models}/cornerHBT.lib" hbt_typ',f'.lib "{models}/cornerRES.lib" {c["res"]}',f'.lib "{models}/cornerMOSlv.lib" {c["mos"]}',f'.include "{SOURCE}"',f'.include "{WRAPPER}"',f'.temp {c["temperature"]}',
            '.options reltol=1e-4 abstol=1e-12 klu',f'VDD avdd 0 PWL(0 0 500p {2.5*scale:.12g})',f'IREF avdd iref PWL(0 0 500p {current:.12g})',
            'VDP dp0 0 '+data(bits,2.0*scale,.15*scale),'VDN dn0 0 '+data([1-b for b in bits],2.0*scale,.15*scale),
            'VEP ep0 0 '+data(select_bits,1.3*scale,.15*scale),'VEN en0 0 '+data([1-b for b in select_bits],1.3*scale,.15*scale),'RDP dp0 dp 10','RDN dn0 dn 10','REP ep0 ep 10','REN en0 en 10',
            f'XGATE dp dn ep en {outputs[0]} {outputs[1]} avdd 0 0 iref nssoc_cdr_xor_hybrid_tail_v2','CQP qp 0 50f','CQN qn 0 50f','.control',f'pre_osdi {lib/"models/r3_cmc.osdi"}',*[f'pre_osdi {p}'for p in osdis],'set wr_singlescale','set wr_vecnames','set numdgt=16','save '+' '.join(vectors)]
        for name in hbts:
            q='q.'+name+'.qnpn13g2';deck.extend([f'alter @{q}[off] = 1',f'echo NSSOC_NATIVE_FLAG_BEGIN {q}',f'show {q} : off','echo NSSOC_NATIVE_FLAG_END'])
        deck+=['op','wrdata op.dat '+' '.join(vectors),f'tran {STEP:.14g} {STOP:.14g} 0 {STEP:.14g}','wrdata wave.dat '+' '.join(vectors),'echo NSSOC_BACKEND_OPTIONS_BEGIN','option','echo NSSOC_BACKEND_OPTIONS_END','quit','.endc','.end']
        native=out/'native';native.mkdir();(native/'bench.cir').write_text('\n'.join(deck)+'\n');(native/'spinit').write_text('set num_threads=1\n')
        protected={str(f):sha(f)for f in [Path(__file__),SOURCE,WRAPPER,ROOT/'scripts/cloud_cdr_xor_hybrid_tail_v1.py',ROOT/'hw/soc/analog/pcie/cdr_xor_core_hybrid_tail_v1.spice',ROOT/'hw/soc/analog/pcie/cdr_xor_hybrid_tail_v1.spice',ROOT/'hw/soc/analog/pcie/cdr_xor_core_shunt_v4.spice',ROOT/'hw/soc/analog/pcie/cdr_xor_hbt_shunt_v4.spice',ROOT/'scripts/cloud_cdr_sampler_hybrid_tail.py',ROOT/'scripts/cloud_cdr_xor.py',ROOT/'scripts/cloud_vbic_tree32_backend.py',engine,native/'bench.cir',*lib.rglob('*')]if f.is_file()}
        r.update(devices=hbts,mos_devices=mos,resistors=resistors,finite_body_contacts=taps,vectors=vectors,source_bits=bits,selector_bits=select_bits,expected_xor=expected_bits,source_bits_sha256=hashlib.sha256(bytes(bits+select_bits)).hexdigest(),protected_inputs=protected);save()
        env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(native),OMP_NUM_THREADS='1')
        with(native/'native.log').open('w')as log:proc=subprocess.run([str(engine),'-n','-b','bench.cir'],cwd=native,env=env,stdout=log,stderr=subprocess.STDOUT)
        text=(native/'native.log').read_text();opts,notes,_=backend_readback(text,'klu');r.update(returncode=proc.returncode,native_options=opts,diagnostics=notes);save();assert proc.returncode==0 and not notes
        flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',text)
        assert [n for n,_ in flags]==['q.'+n+'.qnpn13g2'for n in hbts]and all(re.findall(r'(?m)^\s*off\s+([01])\s*$',s)==['1']for _,s in flags)
        r['native_flags_verified']=len(flags)
        op=np.loadtxt(native/'op.dat',skiprows=1);assert op.size==len(vectors)+1 and np.isfinite(op).all()and abs(op).max()<1e-9;r['zero_source_op_maximum']=float(abs(op).max())
        with(native/'wave.dat').open()as f:header=f.readline().lower().split()
        assert header==['time',*vectors]
        wave=np.loadtxt(native/'wave.dat',skiprows=1);t=wave[:,0];assert wave.shape[1]==len(vectors)+1 and np.isfinite(wave).all()and t[0]==0 and abs(t[-1]-STOP)<1e-15 and np.all(np.diff(t)>0)and np.diff(t).max()<=STEP*1.00001
        d={n:wave[:,i+1]for i,n in enumerate(vectors)};active=t>=START
        def v(n):return np.zeros(len(t))if n=='0'else d['v('+n+')']
        delta=v('qp')-v('qn');signed=[];delay=[]
        for i,bit in enumerate(expected_bits):
            edge=START+i*UI;sign=2*bit-1
            for phase in (.3,.5,.7):signed.append(float(np.interp(edge+phase*UI,t,delta))*sign)
            ids=np.flatnonzero((t>=edge)&(t<=edge+.95*UI));bad=ids[delta[ids]*sign<.1]
            delay.append(0. if not len(bad)else float(t[bad[-1]]-edge+STEP))
        checks={}
        for name,dev in hbts.items():
            vc,vb,ve,_=map(v,dev['nodes']);ic=d['@q.'+name+'.qnpn13g2[ic]'];checks[name]=dict(minimum_active_vce_v=float((vc-ve)[active].min()),maximum_alltime_abs_vce_v=float(abs(vc-ve).max()),maximum_alltime_abs_vbe_v=float(abs(vb-ve).max()),maximum_alltime_abs_ic_per_emitter_a=float(abs(ic).max()/dev['nx']))
        safe=all(x['minimum_active_vce_v']>=.4 and x['maximum_alltime_abs_vce_v']<=1.6 and x['maximum_alltime_abs_vbe_v']<=1 and x['maximum_alltime_abs_ic_per_emitter_a']<.003 for x in checks.values())
        mc={}
        for name,dev in mos.items():
            vd,vg,vs,vb=map(v,dev['nodes']);ids=d['@n.'+name+'.nsg13_lv_nmos[ids]'];peaks={k:float(abs(q).max())for k,q in [('vds',vd-vs),('vgs',vg-vs),('vgd',vg-vd),('vdb',vd-vb),('vsb',vs-vb)]}
            mc[name]=dict(peaks_v=peaks,limit_v=1.32,minimum_active_vds_v=float((vd-vs)[active].min()),minimum_active_drain_current_a=float(ids[active].min()),maximum_alltime_abs_drain_current_a=float(abs(ids).max()),passed=max(peaks.values())<=1.32 and float((vd-vs)[active].min())>=0)
        tails={n:mc[n]['minimum_active_drain_current_a']for n in ('xgate.xcore.xd0049','xgate.xcore.xd0053')};tail=min(tails.values());safe=safe and all(x['passed']for x in mc.values())and tail>=.0005
        data_ok=min(signed)>=.1 and max(delay)<=.3*UI
        r.update(samples=len(signed),minimum_signed_margin_v=min(signed),wrong_sign_samples=sum(x<=0 for x in signed),below_100mv_samples=sum(x<.1 for x in signed),maximum_input_to_valid_s=max(delay),input_to_valid_by_bit_s=delay,device_checks=checks,mos_checks=mc,minimum_active_tail_current_a=tail,tail_currents_a=tails,devices_passed=safe,data_passed=data_ok,
            observed_output_common_mode_v=[float(((v('qp')+v('qn'))/2)[active].min()),float(((v('qp')+v('qn'))/2)[active].max())],observed_output_differential_v=[float(delta[active].min()),float(delta[active].max())])
        assert len(signed)==768 and all(sha(Path(f))==z for f,z in protected.items());r['sources_unchanged']=True
        fault=a.case in ('swap_output','bias_off');r['actual_fault_detected']=(a.case=='swap_output'and sum(x<=0 for x in signed)==768 and safe)or(a.case=='bias_off'and tail<.0005 and min(signed)<.1)
        passed=r['actual_fault_detected']if fault else safe and data_ok
        r['status']='PASS_NATIVE_XOR_HYBRID_COMPONENT_ONLY_NOT_PARENT_OR_LAYOUT'if passed else'REJECTED_NATIVE_XOR_HYBRID_COMPONENT'
        assert passed,'Component data/device screen failed; full native failures retained'
    except BaseException as error:
        if r['status']=='RUNNING':r['status']='FAIL_OR_ERROR'
        r['error']=repr(error);raise
    finally:
        r['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save();print(r['status'],flush=True)
if __name__=='__main__':main()
