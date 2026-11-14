# SPDX-License-Identifier: Apache-2.0
"""What-if rerun of the preserved N1 actual650 bench with only divider values changed.

Every extracted wire R/C, device, source, load and solver option of run
41733225660 is reused unchanged. Only the instance parameters of the twelve
sampler-to-buffer divider resistors and six divider MIMs are rewritten, so
wiring parasitics stay those of the current layout. The frozen measure_wave
and its unchanged thresholds judge the result. A what-if is not a layout,
DRC, LVS or extraction of a new candidate.
"""
import json,re,subprocess,sys,time,copy,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import cdr_mos650_full650_loaded as loaded
RESISTORS=['XD0377','XD0378','XD0379','XD0380','XD0384','XD0385','XD0386','XD0387','XD0388','XD0389','XD0390','XD0391']
AC_MIM=['XD0423','XD0424','XD0427','XD0428'];SELECT_MIM=['XD0425','XD0426']
BUFFER_R=['XD0381','XD0382','XD0383','XD0392','XD0393','XD0394','XD0395','XD0396','XD0397','XD0398','XD0407','XD0408','XD0409','XD0410']
XOR_DATA=['XD0283','XD0284','XD0285','XD0286','XD0288','XD0290','XD0291','XD0294','XD0295','XD0296','XD0297','XD0298',
 'XD0301','XD0302','XD0303','XD0304','XD0306','XD0308','XD0309','XD0312','XD0313','XD0314','XD0315','XD0316']
BUFFER_BIAS=['ibda','ibdc','ibs0','ibs1']
# Pull-ups of the B-to-D divider that sets the D master-latch data-pair base level;
# the clock pair XD0211/XD0212 collectors sit one Vbe below it.
BD_UP=['XD0332','XD0333']
# Bench reference currents of the four sampler latches (A, B, C, D).
SAMPLER_BIAS=['ira','irb','irc','ird']
LOWZ4=dict(rppd_w='4u',ac_mim='7.2u',select_mim='9.6u')
C_SLAVE_DATA=['XD0255','XD0257']
C_SLAVE_ALL=['XD0253','XD0254','XD0255','XD0257']
VARIANTS={
 'bd10_lowz8_xor2_cdata3_sel15':dict(LOWZ4,bd_up_w='10u',slave_parallel='2',rppd_w='8u',xor_nx='2',c_devices=C_SLAVE_DATA,c_nx='3',buffer_select_bias='.0015'),
 'bd10_lowz8_xor2_cdata3':dict(LOWZ4,bd_up_w='10u',slave_parallel='2',rppd_w='8u',xor_nx='2',c_devices=C_SLAVE_DATA,c_nx='3'),
 'bd10_lowz8_xor2_cslave3':dict(LOWZ4,bd_up_w='10u',slave_parallel='2',rppd_w='8u',xor_nx='2',c_devices=C_SLAVE_ALL,c_nx='3'),
 'control':dict(),
  'bd10_lowz8_xor2_acload12':dict(LOWZ4,bd_up_w='10u',slave_parallel='2',rppd_w='8u',xor_nx='2',buffer_ac_w='12u'),
  'bd10_lowz8_xor2_acload16':dict(LOWZ4,bd_up_w='10u',slave_parallel='2',rppd_w='8u',xor_nx='2',buffer_ac_w='16u'),
 'bd10_lowz8_xor2_acbuf15':dict(LOWZ4,bd_up_w='10u',slave_parallel='2',rppd_w='8u',xor_nx='2',buffer_ac_w='12u',buffer_ac_bias='.0015'),
 'bd10_lowz8_xor2_acbuf20':dict(LOWZ4,bd_up_w='10u',slave_parallel='2',rppd_w='8u',xor_nx='2',buffer_ac_w='16u',buffer_ac_bias='.002'),
 'bd10_lowz8_xor2':dict(LOWZ4,bd_up_w='10u',slave_parallel='2',rppd_w='8u',xor_nx='2'),
 'bd10_lowz8_xor3':dict(LOWZ4,bd_up_w='10u',slave_parallel='2',rppd_w='8u',xor_nx='3'),
 'lowz4':LOWZ4,
 'compensated':dict(ac_mim='21.6u',select_mim='9.6u'),
 'fastbuf':dict(LOWZ4,buffer_w='16u',buffer_bias='.002'),
 'fastbuf_xor3':dict(LOWZ4,buffer_w='16u',buffer_bias='.002',xor_nx='3'),
 'lowz4_bd10':dict(LOWZ4,bd_up_w='10u'),
 'lowz4_bd12':dict(LOWZ4,bd_up_w='12u'),
 'bd10_smp075':dict(LOWZ4,bd_up_w='10u',sampler_bias='.00075'),
 'bd10_smp100':dict(LOWZ4,bd_up_w='10u',sampler_bias='.001'),
 'bd10_slave_parallel2':dict(LOWZ4,bd_up_w='10u',slave_parallel='2'),
 'bd10_slave_parallel2_lowz8':dict(LOWZ4,bd_up_w='10u',slave_parallel='2',rppd_w='8u'),
 'bd10_lowz8_acff4':dict(LOWZ4,bd_up_w='10u',slave_parallel='2',rppd_w='8u',ac_mim='14.4u'),
 'bd10_lowz8_selectff4':dict(LOWZ4,bd_up_w='10u',slave_parallel='2',rppd_w='8u',select_mim='19.2u')}
def patch(text,variant):
    v=VARIANTS[variant];lines=text.split('\n');changed={}
    def edit(name,key,value):
        hits=[i for i,l in enumerate(lines)if l.split(maxsplit=1)[:1]==[name]]
        if not hits:
            # An exported MIM card may keep its native name; bind by its own terminal node.
            node=('w_t'+name[3:]+'_mim_top').lower()
            hits=[i for i,l in enumerate(lines)if node in l.lower().split()and 'cap_cmim'in l.lower()]
        assert len(hits)==1,(name,len(hits))
        old=lines[hits[0]];new,count=re.subn(r'(\s'+key+r'=)\S+',r'\g<1>'+value,old)
        assert count==1,(name,key,old);lines[hits[0]]=new;changed.setdefault(name,[old]).append(new)
    for n in RESISTORS:
        if 'rppd_w'in v:edit(n,'w',v['rppd_w'])
    for names,key in ((AC_MIM,'ac_mim'),(SELECT_MIM,'select_mim')):
        for n in names:
            if key in v:edit(n,'w',v[key]);edit(n,'l',v[key])
    for n in BUFFER_R:
        if 'buffer_w'in v:edit(n,'w',v['buffer_w'])
    for n in ['XD0382','XD0383','XD0393','XD0394']:
        if 'buffer_ac_w' in v:edit(n,'w',v['buffer_ac_w'])
    for n in BD_UP:
        if 'bd_up_w'in v:edit(n,'w',v['bd_up_w'])
    for n in XOR_DATA:
        if 'xor_nx'in v:edit(n,'nx',v['xor_nx'])
    if 'slave_parallel' in v:
        # Authenticated native topology: four slave latch sink banks, not masters.
        banks=[list(range(83,87))+list(range(91,95))+list(range(104,112)),
               list(range(50,54))+list(range(58,62))+list(range(71,79)),
               list(range(128,132))+list(range(136,140))+list(range(149,157)),
               list(range(17,21))+list(range(25,29))+list(range(38,46))]
        sinks=[f'XD{i:04d}_s0' for bank in banks for i in bank]
        loads=[f'XD{i:04d}' for i in (325,326,341,344,352,355,362,364)]
        assert len(sinks)==len(set(sinks))==64 and len(loads)==8
        for n in sinks+loads:
            original=[line for line in lines if line.split(maxsplit=1)[:1]==[n]]
            assert len(original)==1 and re.search(r'\sm=1(?:\s|$)',original[0]),(n,original)
            edit(n,'m',v['slave_parallel'])
    for n in v.get('c_devices',[]):edit(n,'nx',v['c_nx'])
    return '\n'.join(lines),changed
def patch_bench(text,variant):
    v=VARIANTS[variant];changed={}
    if 'sampler_bias'in v:
        for b in SAMPLER_BIAS:
            old=f'I_{b} avdd {b} PWL(0 0 500p .0005)';assert text.count(old)==1,(b,text.count(old))
            new=f'I_{b} avdd {b} PWL(0 0 500p {v["sampler_bias"]})';text=text.replace(old,new);changed[b]=[old,new]
    if 'buffer_bias'in v:
        for b in BUFFER_BIAS:
            old=f'I_{b} avdd {b} PWL(0 0 500p .001)';assert text.count(old)==1,(b,text.count(old))
            new=f'I_{b} avdd {b} PWL(0 0 500p {v["buffer_bias"]})';text=text.replace(old,new);changed[b]=[old,new]
    if 'buffer_ac_bias' in v:
        for b in ['ibda','ibdc']:
            old=f'I_{b} avdd {b} PWL(0 0 500p .001)';assert text.count(old)==1
            new=f'I_{b} avdd {b} PWL(0 0 500p {v["buffer_ac_bias"]})';text=text.replace(old,new);changed[b]=[old,new]
    if 'buffer_select_bias' in v:
        for b in ['ibs0','ibs1']:
            old=f'I_{b} avdd {b} PWL(0 0 500p .001)';assert text.count(old)==1
            new=f'I_{b} avdd {b} PWL(0 0 500p {v["buffer_select_bias"]})';text=text.replace(old,new);changed[b]=[old,new]
    return text,changed
def main(root,variant,out):
    root=Path(root).resolve();native=root/'native';out=Path(out);out.mkdir(parents=True)
    original=json.loads((root/'derived/loaded-n1-nominal_late.json').read_bytes())
    model=native/'composition-n1/model.cir';text=model.read_text()
    patched,changed=patch(text,variant)
    if variant in ('bd10_lowz8_xor2','bd10_lowz8_xor3'):
        baseline,_=patch(text,'bd10_slave_parallel2_lowz8')
        a,b=baseline.splitlines(),patched.splitlines();assert len(a)==len(b)
        differences=[(x,y) for x,y in zip(a,b) if x!=y]
        assert len(differences)==len(XOR_DATA)==24
        assert {x.split()[0] for x,y in differences}==set(XOR_DATA)
        for old,new in differences:
            assert 'npn13g2' in old and re.search(r'\snx=4(?:\s|$)',old)
            expected,count=re.subn(r'(\snx=)4(?=\s|$)',r'\g<1>'+VARIANTS[variant]['xor_nx'],old)
            assert count==1 and new==expected
        (out/'isolated-load-change.json').write_text(json.dumps({'reference_variant':'bd10_slave_parallel2_lowz8','changed_devices':XOR_DATA,'only_nx_changed':True,'old_nx':4,'new_nx':int(VARIANTS[variant]['xor_nx']),'wiring_rc_unchanged_whatif_only':True},indent=2))
    if 'buffer_ac_w' in VARIANTS[variant]:
        import zipfile,io
        topo_blob=Path('buffer-topology.zip').read_bytes()
        assert hashlib.sha256(topo_blob).hexdigest()=='e4b96b9ed5ea0cfc3dd44269c1b1e19be755857fa5c483aced0d4ae19e6e04e9'
        topo=json.loads(zipfile.ZipFile(io.BytesIO(topo_blob)).read('divider-topology.json'))
        assert topo['status']=='DIVIDER_TOPOLOGY_CLASSIFIED'
        expected={'w_t273_c':'xd0383','w_t275_c':'xd0382','w_t278_c':'xd0394','w_t280_c':'xd0393'}
        for node,rname in expected.items():
            rs=[d for d in topo['buffer_terminal_neighborhoods'][node]['connected_devices'] if d['model']=='rppd']
            assert len(rs)==1 and rs[0]['device']==rname and rs[0]['parameters']['w']=='8u' and rs[0]['parameters']['l']=='1.8u'
        baseline,_=patch(text,'bd10_lowz8_xor2')
        left,right=baseline.splitlines(),patched.splitlines();assert len(left)==len(right)
        diffs=[(x,y) for x,y in zip(left,right) if x!=y]
        assert len(diffs)==4 and {x.split()[0].lower() for x,y in diffs}==set(expected.values())
        for old,new in diffs:
            revised,count=re.subn(r'(\sw=)8u(?=\s|$)',lambda m:m[1]+VARIANTS[variant]['buffer_ac_w'],old)
            assert count==1 and revised==new
        proof={'baseline':'bd10_lowz8_xor2','only_four_ac_collector_widths_changed':True,'collector_devices':list(expected.values()),'old_width':'8u','new_width':VARIANTS[variant]['buffer_ac_w'],'only_bias_sources_changed':(['ibda','ibdc'] if 'buffer_ac_bias' in VARIANTS[variant] else []),'old_bias_a':.001,'new_bias_a':float(VARIANTS[variant].get('buffer_ac_bias','.001')),'topology_artifact':14092472835,'settling_diagnostic_run':43562679420,'current_density_limit_unchanged_a_per_emitter':.003,'nominal_current_times_resistance_preserved_heuristic_only':('buffer_ac_bias' in VARIANTS[variant]),'what_if_only':True,'new_layout':False}
        (out/'isolated-ac-buffer-change.json').write_text(json.dumps(proof,indent=2))
    if 'c_devices' in VARIANTS[variant]:
        import zipfile,io
        blob=Path('sampler-phase.zip').read_bytes()
        assert hashlib.sha256(blob).hexdigest()=='87e4c31c3a91c3df65895773196fde014965e0ec93ed9e25e80f0a2fde019298'
        evidence=json.loads(zipfile.ZipFile(io.BytesIO(blob)).read('sampler-c-phase.json'))
        assert evidence['original_gate_reproduction'] and not evidence['accepted']
        rows=evidence['sampler_c_backtrace']['groups'][0]['devices']
        for native_id in VARIANTS[variant]['c_devices']:
            found=[d for d in rows if d['name']=='xpd.'+native_id.lower()]
            assert len(found)==1 and found[0]['nx']==4 and found[0]['collector_backtrace_depth']==0
        baseline,_=patch(text,'bd10_lowz8_xor2')
        def verify_isolated(candidate):
            left,right=baseline.splitlines(),candidate.splitlines();assert len(left)==len(right)
            diffs=[(x,y) for x,y in zip(left,right) if x!=y]
            assert len(diffs)==len(VARIANTS[variant]['c_devices'])
            assert {x.split()[0] for x,y in diffs}==set(VARIANTS[variant]['c_devices'])
            for old,new in diffs:
                expected,n=re.subn(r'(\snx=)4(?=\s|$)',lambda m:m[1]+'3',old)
                assert n==1 and expected==new and 'npn13g2' in old
            return diffs
        differences=verify_isolated(patched)
        # Negative controls prove that an omitted edit or wrong nx is rejected.
        for damaged in [baseline,patched.replace(differences[0][1],differences[0][0],1),patched.replace(differences[0][1],differences[0][1].replace('nx=3','nx=2'),1)]:
            try:verify_isolated(damaged)
            except AssertionError:pass
            else:raise AssertionError('Isolated change verifier accepted mutation')
        (out/'isolated-c-sampler-change.json').write_text(json.dumps({'reference':'bd10_lowz8_xor2','only_changed_native_ids':VARIANTS[variant]['c_devices'],'old_nx':4,'new_nx':3,'negative_controls_rejected':3,'evidence_run':43584493730,'evidence_artifact':14110140623,'new_layout':False,'unchanged_extracted_wire_rc_whatif_only':True},indent=2))
    # Current per emitter must use the actual candidate nx, not the archived binding.
    bound=copy.deepcopy(original['binding'])
    binding_changes={}
    if 'xor_nx' in VARIANTS[variant]:
        devices=bound['groups']['npn13g2']
        for native_id in XOR_DATA:
            marker='w_t'+native_id[3:]+'_b'
            hits=[name for name,dev in devices.items() if dev['nodes'][1].lower().rsplit('.',1)[-1]==marker]
            assert len(hits)==1,(native_id,'ambiguous or missing bound HBT',hits)
            name=hits[0];assert devices[name]['nx']==4,(name,devices[name]['nx'])
            devices[name]['nx']=int(VARIANTS[variant]['xor_nx'])
            binding_changes[name]={'native_id':native_id,'old_nx':4,'new_nx':devices[name]['nx']}
        assert len(binding_changes)==24
        restored=copy.deepcopy(bound)
        for name in binding_changes:restored['groups']['npn13g2'][name]['nx']=4
        assert restored==original['binding'],'Unrelated waveform binding changed'
    if 'c_devices' in VARIANTS[variant]:
        for native_id in VARIANTS[variant]['c_devices']:
            marker='w_t'+native_id[3:]+'_b'
            hits=[name for name,dev in bound['groups']['npn13g2'].items() if dev['nodes'][1].lower().rsplit('.',1)[-1]==marker]
            assert len(hits)==1
            name=hits[0];assert name not in binding_changes and bound['groups']['npn13g2'][name]['nx']==4
            bound['groups']['npn13g2'][name]['nx']=3
            binding_changes[name]={'native_id':native_id,'old_nx':4,'new_nx':3}
        assert len(binding_changes)==24+len(VARIANTS[variant]['c_devices'])
        restored=copy.deepcopy(bound)
        for name in binding_changes:restored['groups']['npn13g2'][name]['nx']=4
        assert restored==original['binding']
        bench_before=(native/'loaded-n1-nominal_late/bench.cir').read_text()
        bench_after,bias_changes=patch_bench(bench_before,variant)
        if 'buffer_select_bias' in VARIANTS[variant]:
            assert set(bias_changes)=={'ibs0','ibs1'}
            restored_bench=bench_after
            for old_line,new_line in bias_changes.values():
                assert restored_bench.count(new_line)==1
                restored_bench=restored_bench.replace(new_line,old_line,1)
            assert restored_bench==bench_before,'Unrelated bench data/clock/load/solver changed'
            baseline_cdata,_=patch(text,'bd10_lowz8_xor2_cdata3')
            assert patched==baseline_cdata,'Only select bias may differ from measured cdata3 model'
            (out/'isolated-select-bias-change.json').write_text(json.dumps({'reference_variant':'bd10_lowz8_xor2_cdata3','reference_run':43584735530,'connectivity_evidence_run':43595197025,'changed_bias_sources':bias_changes,'all_model_records_byte_identical_to_reference_variant':True,'all_other_bench_lines_byte_identical':True,'frozen_gate_thresholds_unchanged':True,'original_wire_rc_retained':True,'new_layout':False,'old_current_a':.001,'new_current_a':.0015},indent=2))
        else:
            assert bench_after==bench_before and bias_changes=={},'Bench sources must remain byte-identical' 
    (out/'candidate-current-density-binding.json').write_text(json.dumps({'changes':binding_changes,'original_binding_sha256':hashlib.sha256(json.dumps(original['binding'],sort_keys=True).encode()).hexdigest(),'candidate_binding_sha256':hashlib.sha256(json.dumps(bound,sort_keys=True).encode()).hexdigest(),'current_limit_a_per_emitter':.003,'original_metadata_unchanged':True},indent=2))
    model.write_text(patched)
    (out/'patch.json').write_text(json.dumps(dict(variant=variant,values=VARIANTS[variant],changed=changed),indent=1))
    folder=native/'loaded-n1-nominal_late';assert not (folder/'wave.raw').exists()
    original_bench_text=(folder/'bench.cir').read_text()
    bench,bias=patch_bench(original_bench_text,variant);(folder/'bench.cir').write_text(bench)
    (out/'bench-patch.json').write_text(json.dumps(bias,indent=1))
    if 'buffer_ac_bias' in VARIANTS[variant]:
        assert set(bias)=={'ibda','ibdc'} and all('PWL(0 0 500p .001)' in pair[0] for pair in bias.values())

    if variant in ('bd10_lowz8_xor2_acload12','bd10_lowz8_xor2_acload16'):
        assert not bias and bench==original_bench_text
        (out/'unchanged-bias-proof.json').write_text(json.dumps({'all_bench_sources_unchanged':True,'reference_variant':'bd10_lowz8_xor2','bench_sha256':hashlib.sha256(bench.encode()).hexdigest(),'only_model_delta':'four A/C collector widths; topology verified above','unchanged_gate_limits':True},indent=2))

    engine=native/'models/source/runtime/patched-ngspice';engine.chmod(0o755)
    began=time.monotonic()
    with open(out/'ngspice.stdout','wb')as so,open(out/'ngspice.stderr','wb')as se:
        rc=subprocess.run([str(engine),'-n','-b','bench.cir'],cwd=folder,stdout=so,stderr=se,timeout=17000).returncode
    elapsed=time.monotonic()-began
    t,d,info=loaded.read_streamed_wave(folder/'wave.raw',original['vectors'],loaded.STOP,loaded.STEP)
    r={}
    try:
        loaded.measure_wave(bound,t,d,original['source_bits'],original['data_offset_s'],{},r,False,False);passed=True
    except AssertionError as e:passed=False;r['assertion']=str(e)
    keep={k:r[k]for k in ('status','data_passed','devices_passed','phase_passed','phase_average_v','vi','sampler_checks','comparisons','minimum_active_stage_tail_current_a','interface_observations')if k in r}
    for g in ('sampler_checks','comparisons'):
        for x in keep.get(g,{}).values():x.pop('clock_to_valid_by_bit_s',None)
    hbt=[n for n,x in r.get('device_checks',{}).items()if x['minimum_active_vce_v']<.4 or x['maximum_alltime_abs_vce_v']>1.6 or x['maximum_alltime_abs_vbe_v']>1 or x['maximum_alltime_abs_ic_per_emitter_a']>=.003]
    waveform_passed=passed
    passed=waveform_passed and rc==0
    keep.update(variant=variant,returncode=rc,elapsed_seconds=elapsed,passed=passed,
        waveform_passed=waveform_passed,simulator_passed=(rc==0),failing_hbt=hbt,
        failing_mos=[n for n,x in r.get('mos_checks',{}).items()if not x['passed']],raw=dict(points=info['header_rows'],sha256=info['raw_sha256']),
        what_if_only=True,new_layout=False,electrical_acceptance=False,current_density_binding_changes=binding_changes)
    grid=(loaded.START+np.arange(258)[:,None]*loaded.UI+np.arange(16)[None,:]*loaded.UI/16).ravel()
    names=[n for n in original['vectors']if n.startswith('v(')]
    np.savez_compressed(out/'bit-phase-samples.npz',samples=np.array([np.interp(grid,t,d[n])for n in names],dtype=np.float32),names=np.array(names),grid=grid)
    (out/'result.json').write_text(json.dumps(keep,indent=1,sort_keys=True))
    # Multiplicity changes are a circuit screen, never an actual650 layout claim.
    if 'slave_parallel' in VARIANTS[variant]:
        keep['experiment_scope']='64 slave-tail MOS and 8 collector resistors use m=2; effective primitive multiplicity increases by 72. Existing interconnect RC is retained only as a what-if. No new extracted layout.'
        keep['source_topology_run']=43472881982
        keep['reference_variant']=('bd10_slave_parallel2_lowz8' if variant in ('bd10_lowz8_acff4','bd10_lowz8_selectff4','bd10_lowz8_xor2','bd10_lowz8_xor3') else 'bd10_slave_parallel2' if variant=='bd10_slave_parallel2_lowz8' else 'lowz4_bd10')
        if 'buffer_ac_w' in VARIANTS[variant]:
            keep['reference_variant']='bd10_lowz8_xor2'
            keep['experiment_scope']+=' Relative to failed xor2 baseline four A/C buffer collector widths change. Bias changes only with explicit buffer_ac_bias; acload12/16 preserve all original bench sources. No layout or extracted-RC update; device and data gates unchanged.'
        (out/'result.json').write_text(json.dumps(keep,indent=1,sort_keys=True))
    if 'c_devices' in VARIANTS[variant]:
        keep['reference_variant']='bd10_lowz8_xor2'
        keep['experiment_scope']='Only C slave data pair nx=4->3, plus feedback pair in cslave3 variant, relative to xor2 baseline. Original sources, solver, data/device gates and old wiring RC retained. Circuit what-if only; no new layout, extracted RC, closed-loop PHY or manufacturing acceptance.'
        (out/'result.json').write_text(json.dumps(keep,indent=1,sort_keys=True))
    if 'buffer_select_bias' in VARIANTS[variant]:
        keep['reference_variant']='bd10_lowz8_xor2_cdata3'
        keep['experiment_scope']='Only ibs0 and ibs1 bias sources 1mA->1.5mA relative to measured cdata3. Native model identical, all other bench lines identical. Frozen device/data/phase/current limits unchanged. Nominal externally clocked circuit what-if, not extracted new layout or complete PHY.'
        (out/'result.json').write_text(json.dumps(keep,indent=1,sort_keys=True))
    print(json.dumps({k:keep[k]for k in('variant','returncode','passed','data_passed','devices_passed','phase_passed','phase_average_v','failing_hbt')},sort_keys=True))
if __name__=='__main__':main(*sys.argv[1:])
