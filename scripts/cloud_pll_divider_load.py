#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Explicit output-latch gain hypotheses with baseline wires; never physical acceptance."""
import argparse,json,os,re,shutil,subprocess,time
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import run_cloud_pll865_snapshot as pll
from cloud_vbic_tree32_backend import backend_readback
from cloud_pll_divider_review import inspect_op
from cloud_pll_terminal_diagnosis import crossing_times
from route_cloud_newer_postcts import sha,fetch
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll-divider-load';LIB=ROOT/'cloud-pll-snapshot'
SUMMARY='6f8d58ce61d36a2ba9d1a6685c489606fd690f47ec4c5c762ab8d6eb333d0470'
PARTS='214dd0fbc2ff51a0a41c389176adc9a00c8d51b8749320d843d4317bffaae8bc'
def candidate_parent(original,length):
    assert length in ('3.2','4.2')
    edits=[];result=original
    for group in ('xdiv1','xdiv2'):
        for number in range(45,49):
            name='X_'+group+'_xd'+str(number).zfill(4)
            rows=[l for l in original.splitlines()if l.startswith(name+' ')];assert len(rows)==1
            old=rows[0];assert old.endswith('rppd w=8.0u l=2.12u ps=0.0u b=0 m=1 sw_et=1')
            new=old.replace('l=2.12u','l='+length+'u');assert original.count(old)==1
            result=result.replace(old,new);edits.append(dict(device=name,before=old,after=new))
    assert len(edits)==8
    return result,edits

def require_candidate(original,candidate,length):
    expected,edits=candidate_parent(original,length)
    assert candidate==expected,'Undeclared device, wire or source change'
    return edits

def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--load-length',choices=['3.2','4.2'],required=True);args=parser.parse_args();OUT=ROOT/('cloud-pll-divider-load-'+args.load_length.replace('.','p'))
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,acquisition_accepted=False,new_bounded_diagnostic=True,original_completed_run_restarted=False,candidate_matches_geometry=False,wire_parasitics_are_parent_estimates=True,load_length_um=args.load_length,scope='Eight output-latch collector load resistors XD45..48 in xdiv1/xdiv2 change only L2.12um to3.2um or4.2um, W8um fixed, to test regeneration gain after measured tiny divider output swing. All baseline wire RC are frozen estimates, NOT candidate physical extraction. Original supplies/reset/reference/OFF102/engine/PDK/.3125ps and50ns all102HBT probes retained. No acquisition/safety/physical/PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38910378266-1-pll-native-acquisition-continuation/pll-native-acquisition-continuation-38910378266-1.summary.json'
        fetch(url,SUMMARY,OUT/'terminal.json');prior=json.loads((OUT/'terminal.json').read_text())
        assert prior['native_exitcode']==0 and not prior['independent_acquisition']['passed'] and len(prior['independent_acquisition']['feedback_edges_s'])==0
        selected=tuple(n for n in prior['outputs']if n.startswith(('model-sources/','runtime/')))+('case/circuit.cir','case/actual-acquisition.cir','case/parent865.spice','case/spinit')
        old,proof=reports.restore_report('pll-native-acquisition-continuation',38910378266,SUMMARY,PARTS,OUT/'source',selected);assert old==prior;r['source']=proof
        assert not LIB.exists();shutil.copytree(OUT/'source/model-sources',LIB)
        assert all(sha(LIB/p)==d for p,d in old['preparation']['model_sources'].items())
        case=OUT/'diagnostic';shutil.copytree(OUT/'source/case',case);original=(case/'circuit.cir').read_text();parent=(case/'parent865.spice').read_text()
        assert sha(case/'parent865.spice')=='8147a7cbae9d1a43b362733a3b52c218c5d04ef519cedf9abf35cd17ff27911e'
        candidate,edits=candidate_parent(parent,args.load_length);assert require_candidate(parent,candidate,args.load_length)==edits
        (case/'parent865.spice').write_text(candidate)
        bad_hbt=candidate.replace('nx=4 we=0.07u le=0.9u','nx=3 we=0.07u le=0.9u',1)
        wire=next(l for l in candidate.splitlines()if l.startswith('R_'))
        wrong_wire=candidate.replace(wire,wire.rsplit(' ',1)[0]+' 123.0',1)
        faults={'wrong_hbt':bad_hbt,'wire_changed':wrong_wire,'missing_load':candidate.replace(edits[0]['after']+'\n','',1)}
        controls=[]
        for name,bad in faults.items():
            assert bad!=candidate;(OUT/(name+'.spice')).write_text(bad)
            try:require_candidate(parent,bad,args.load_length)
            except AssertionError:controls.append(dict(fault=name,rejected=True))
            else:raise AssertionError('Unlisted native model change accepted')
        r.update(candidate_parent_sha256=sha(case/'parent865.spice'),declared_changes=edits,candidate_controls=controls);save()
        assert original.count('.include "parent865.spice"')==1
        rows=[l.lower().split()for l in parent.splitlines()if l.lower().startswith('x_')]
        hbts={w[0]:dict(terminals=w[1:5],nx=float(next(p.split('=')[1]for p in w if p.startswith('nx='))))for w in rows if len(w)>5 and w[5]=='npn13g2'};assert len(hbts)==102
        base=old['preparation']['vectors'];assert len(base)==34
        required={'v(xloop.'+n+')'for d in hbts.values()for n in d['terminals']}|{'@q.xloop.'+n+'.qnpn13g2[ic]'for n in hbts}
        vectors=list(dict.fromkeys(base+sorted(required)));assert len(vectors)<600
        source_save='save '+' '.join(base);assert original.splitlines().count(source_save)==1
        full='.tran 3.125e-13 1e-06 0 3.125e-13';short='.tran 3.125e-13 5e-08 0 3.125e-13';assert original.count(full)==1
        deck=original.replace(source_save,'save '+' '.join(vectors)).replace(full,short)
        assert deck.replace('save '+' '.join(vectors),source_save).replace(short,full)==original
        (case/'circuit.cir').write_text(deck)
        wrapper=(case/'actual-acquisition.cir').read_text();assert wrapper.count('write op.raw all')==1
        wrapper=wrapper.replace('write op.raw all','write op.raw '+' '.join(base));(case/'actual-acquisition.cir').write_text(wrapper)
        # Published input models and original capture remain untouched. Only
        # this separate diagnostic deck changes duration and recorded probes.
        engine=OUT/'source/runtime/patched-ngspice';assert sha(engine)=='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509';engine.chmod(0o755)
        protected={str(p):sha(p)for p in [engine,*case.iterdir(),*LIB.rglob('*')]if p.is_file()};r.update(hbt_devices=hbts,probe_count=len(vectors),protected_inputs=protected);save()
        env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN','LD_PRELOAD','PYTHONPATH','PYTHONHOME')}
        env.update(SPICE_SCRIPTS=str(case),OMP_NUM_THREADS='1',GLIBC_TUNABLES='glibc.cpu.hwcaps=-AVX512F,-AVX512CD,-AVX512BW,-AVX512DQ,-AVX512ER,-AVX512PF,-AVX512VL,-RTM')
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});start=time.monotonic()
        with (OUT/'native.log').open('w')as f:code=subprocess.call([str(engine),'-n','-b','actual-acquisition.cir'],cwd=case,env=env,stdout=f,stderr=subprocess.STDOUT)
        text=(OUT/'native.log').read_text(errors='replace');r.update(returncode=code,elapsed_s=time.monotonic()-start);save();assert code==0
        options,diagnostics,_=backend_readback(text,'klu');r.update(native_options=options,diagnostics=diagnostics);save();assert not diagnostics
        assert all(options[k]==old['native_options'][k]for k in ('backend','numeric','method'))
        flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',text)
        assert len(flags)==102 and {n for n,b in flags}=={'q.xloop.'+n+'.qnpn13g2'for n in hbts}
        assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',body)==['1']for _,body in flags)
        r['zero_source_op']=inspect_op((case/'op.raw').read_bytes(),base,vectors);assert r['zero_source_op']['diagnostic_zero_op_verified']
        raw=(case/'actual-acquisition.raw').read_bytes();names,values,meta=pll.decode_prefix(raw)
        assert meta['header_matches_observed'] and meta['payload_has_only_complete_rows'] and np.isfinite(values).all()
        observed={n:values[:,i]for i,n in enumerate(names)};assert len(names)==len(vectors)+1 and len(observed)==len(names)
        data={'time':observed['time']};used={'time'}
        for name in vectors:
            allowed={name}if name.startswith('v(')else{name,'i('+name+')'};found=allowed&set(observed);assert len(found)==1
            actual=found.pop();assert actual not in used;used.add(actual);data[name]=observed[actual]
        assert used==set(observed);t=data['time'];assert t[0]==0 and abs(t[-1]-50e-9)<1e-15 and np.all(np.diff(t)>0) and np.diff(t).max()<=3.125e-13*1.00001
        r['capture']=dict(**meta,raw_sha256=sha(case/'actual-acquisition.raw'),start_s=float(t[0]),end_s=float(t[-1]),rows=len(t))
        measurements={}
        for name,d in hbts.items():
            c,b,e,sub=[data['v(xloop.'+n+')']for n in d['terminals']]
            ic=data['@q.xloop.'+name+'.qnpn13g2[ic]']/d['nx'];signals={'vce_v':c-e,'vbe_v':b-e,'vbc_v':b-c,'ic_per_emitter_a':ic,'collector_v':c,'base_v':b,'emitter_v':e,'substrate_v':sub};windows=[]
            for lo,hi in [(0.,50e-9),(5e-9,10e-9),(10e-9,20e-9),(40e-9,50e-9)]:
                mask=(t>=lo)&(t<=hi);assert mask.sum()>10
                windows.append(dict(interval_s=[lo,hi],signals={k:dict(minimum=float(v[mask].min()),maximum=float(v[mask].max()),mean=float(v[mask].mean()))for k,v in signals.items()}))
            measurements[name]=dict(nx=d['nx'],windows=windows)
        r['hbt_measurements']=measurements;r['terminal_signal_ranges']={n:[float(data[n][t>=40e-9].min()),float(data[n][t>=40e-9].max())]for n in base}
        waves={'vco_diff':data['v(clkp)']-data['v(clkn)'],'divider1_diff':data['v(qp)']-data['v(qn)'],'divider2_diff':data['v(xloop.qp2)']-data['v(xloop.qn2)'],'receiver_clk':data['v(xloop.clk)'],'feedback':data['v(fb)']}
        diagnostic={}
        for name,wave in waves.items():
            threshold=0. if name.endswith('_diff')else .6 if name=='receiver_clk'else 1.25
            edge=crossing_times(t,wave,threshold);edge=edge[(edge>=40e-9)&(edge<50e-9)];sel=wave[t>=40e-9]
            diagnostic[name]=dict(threshold_v=threshold,minimum_v=float(sel.min()),maximum_v=float(sel.max()),rising_edges=len(edge),mean_edge_frequency_hz=float((len(edge)-1)/(edge[-1]-edge[0]))if len(edge)>1 else None,minimum_edge_interval_s=float(np.diff(edge).min())if len(edge)>1 else None,maximum_edge_interval_s=float(np.diff(edge).max())if len(edge)>1 else None)
        r['last10ns_diagnostics']=diagnostic
        assert all(sha(Path(p))==d for p,d in protected.items()) and all(sha(OUT/'source'/p)==old['outputs'][p]for p in selected)
        r.update(status='COMPLETE_DIVIDER_LOAD_HYPOTHESIS_WITH_BASELINE_WIRES_REQUIRES_PHYSICAL_REEXTRACTION',source_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
