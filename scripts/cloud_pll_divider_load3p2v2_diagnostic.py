#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual corrected v2 divider RC in both PLL stages: bounded102HBT diagnosis, not acquisition or parent-layout acceptance."""
import argparse,json,os,re,shutil,subprocess,time
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import run_cloud_pll865_snapshot as pll
from cloud_vbic_tree32_backend import backend_readback
from cloud_pll_divider_review import inspect_op
from cloud_pll_terminal_diagnosis import crossing_times
from route_cloud_newer_postcts import sha,fetch
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll-divider-load3p2v2-diagnostic';LIB=ROOT/'cloud-pll-snapshot'
SUMMARY='6f8d58ce61d36a2ba9d1a6685c489606fd690f47ec4c5c762ab8d6eb333d0470'
PARTS='214dd0fbc2ff51a0a41c389176adc9a00c8d51b8749320d843d4317bffaae8bc'
def hbts_of(parent):
    rows=[l.lower().split()for l in parent.splitlines()if l.lower().startswith('x_')]
    result={w[0]:dict(terminals=w[1:5],nx=float(next(p.split('=')[1]for p in w if p.startswith('nx='))))for w in rows if len(w)>5 and w[5]=='npn13g2'}
    assert len(result)==102
    return result

def rebind_flags(original,old_hbts,new_hbts,proof):
    mapping={n:n for n in old_hbts};divider_names=set()
    assert len(proof)==2 and {p['group']for p in proof}=={'xdiv1','xdiv2'}
    for group in proof:
        assert group['intrinsic_topology_equivalent_except_four_load_lengths']and len(group['normalized_load_changes'])==4
        m=group['device_bijection'];assert len(m)==len(set(m.values()))==91
        for old,new in m.items():
            if old in old_hbts:
                assert new in new_hbts and old_hbts[old]['nx']==new_hbts[new]['nx']
                mapping[old]=new;divider_names.add(old)
    assert len(divider_names)==68 and set(mapping)==set(old_hbts)and set(mapping.values())==set(new_hbts)
    pattern=r'q\.xloop\.(x_\w+)\.qnpn13g2'
    found=re.findall(pattern,original)
    assert set(found)==set(old_hbts)and all(found.count(n)==3 for n in old_hbts)
    # Simultaneous replacement prevents collisions between old and new IDs.
    rebound=re.sub(pattern,lambda m:'q.xloop.'+mapping[m[1]]+'.qnpn13g2',original)
    newfound=re.findall(pattern,rebound)
    assert set(newfound)==set(new_hbts)and all(newfound.count(n)==3 for n in new_hbts)
    assert len(re.findall(r'(?m)^alter .*\[off\] = 1$',rebound))==102
    return rebound,mapping

def main():
    spec=json.loads(os.environ['PARENT_REPORT'])
    assert set(spec)=={'run','head','summary','parts','model'}and spec['run']==38978829291 and spec['head']=='136f4665ab0ded356563444e15e0a35bd3cc252e'
    assert all(re.fullmatch('[0-9a-f]{64}',spec[k])for k in ['summary','parts','model'])
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,acquisition_accepted=False,new_bounded_diagnostic=True,original_completed_run_restarted=False,divider_matches_geometry=True,parent_geometry_updated=False,parent_interconnect_rc_revalidated=False,scope='Both corrected v2 native91/382R649C divider blocks replace old models, bound by parent intrinsic graph proof. All other parent records and parent interconnect RC retained; actual assembled parent geometry/RC still unvalidated. Original supplies/reset/reference/engine/PDK/.3125ps and50ns all102HBT terminal/current probes. OFF/readback102targets rebound by proved device bijection. No1us acquisition, full-device safety/PVT or PHY acceptance.')
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
        replacement,receipt=reports.restore_report('pll-divider-load3p2v2-parent',spec['run'],spec['summary'],spec['parts'],OUT/'new-parent',('parent845.spice','parent/parent845.spice'))
        assert replacement['source_head']==spec['head']and replacement['source_unchanged']
        assert replacement['status']=='PASS_BOTH_DIVIDER_RC_MODELS_IN_PARENT_WITH_INTRINSIC_GRAPH_AND_SIX_FAULTS_REQUIRES_PARENT_GEOMETRY_AND_ACQUISITION'
        assert len(replacement['controls'])==6 and all(c['rejected']for c in replacement['controls'])
        assert sha(OUT/'new-parent/parent845.spice')==replacement['model_sha256']==spec['model']
        assert (OUT/'new-parent/parent/parent845.spice').read_text()==parent
        candidate=(OUT/'new-parent/parent845.spice').read_text();old_hbts=hbts_of(parent);hbts=hbts_of(candidate)
        rebound,mapping=rebind_flags(original,old_hbts,hbts,replacement['intrinsic_graphs'])
        # Only verified native device IDs may change in the original full deck.
        changed_controls=[]
        first=next(n for n,v in mapping.items()if n!=v)
        for name,bad in [('missing_OFF',re.sub(r'^alter .*\[off\] = 1\n','',rebound,count=1,flags=re.M)),('wrong_OFF_value',rebound.replace('[off] = 1','[off] = 0',1)),('wrong_target',rebound.replace('q.xloop.'+mapping[first]+'.qnpn13g2','q.xloop.missing_native_device.qnpn13g2',1))]:
            assert bad!=rebound;(OUT/(name+'.cir')).write_text(bad)
            try:assert bad==rebind_flags(original,old_hbts,hbts,replacement['intrinsic_graphs'])[0],'Undeclared native startup target/control change'
            except AssertionError as error:changed_controls.append(dict(fault=name,rejected=True,reason=str(error)))
            else:raise AssertionError('Bad native flags accepted')
        (case/'parent865.spice').write_text(candidate)
        r.update(candidate_parent_sha256=sha(case/'parent865.spice'),parent_source=receipt,native_hbt_id_mapping=mapping,flag_binding_controls=changed_controls);save()
        assert original.count('.include "parent865.spice"')==1
        original=rebound
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
        assert sha(OUT/'new-parent/parent845.spice')==spec['model']
        r.update(status='COMPLETE_V2_DIVIDER_FRESH_WIRE_PARENT_50NS_ALL102HBT_DIAGNOSIS_NOT_FULL_ACQUISITION_OR_PARENT_LAYOUT_ACCEPTANCE',source_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
