# SPDX-License-Identifier: Apache-2.0
"""What-if rerun of the preserved N1 actual650 bench with only divider values changed.

Every extracted wire R/C, device, source, load and solver option of run
41733225660 is reused unchanged. Only the instance parameters of the twelve
sampler-to-buffer divider resistors and six divider MIMs are rewritten, so
wiring parasitics stay those of the current layout. The frozen measure_wave
and its unchanged thresholds judge the result. A what-if is not a layout,
DRC, LVS or extraction of a new candidate.
"""
import json,re,subprocess,sys,time
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
VARIANTS={
 'control':dict(),
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
    model.write_text(patched)
    (out/'patch.json').write_text(json.dumps(dict(variant=variant,values=VARIANTS[variant],changed=changed),indent=1))
    folder=native/'loaded-n1-nominal_late';assert not (folder/'wave.raw').exists()
    bench,bias=patch_bench((folder/'bench.cir').read_text(),variant);(folder/'bench.cir').write_text(bench)
    (out/'bench-patch.json').write_text(json.dumps(bias,indent=1))
    engine=native/'models/source/runtime/patched-ngspice';engine.chmod(0o755)
    began=time.monotonic()
    with open(out/'ngspice.stdout','wb')as so,open(out/'ngspice.stderr','wb')as se:
        rc=subprocess.run([str(engine),'-n','-b','bench.cir'],cwd=folder,stdout=so,stderr=se,timeout=17000).returncode
    elapsed=time.monotonic()-began
    t,d,info=loaded.read_streamed_wave(folder/'wave.raw',original['vectors'],loaded.STOP,loaded.STEP)
    r={}
    try:
        loaded.measure_wave(original['binding'],t,d,original['source_bits'],original['data_offset_s'],{},r,False,False);passed=True
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
        what_if_only=True,new_layout=False,electrical_acceptance=False)
    grid=(loaded.START+np.arange(258)[:,None]*loaded.UI+np.arange(16)[None,:]*loaded.UI/16).ravel()
    names=[n for n in original['vectors']if n.startswith('v(')]
    np.savez_compressed(out/'bit-phase-samples.npz',samples=np.array([np.interp(grid,t,d[n])for n in names],dtype=np.float32),names=np.array(names),grid=grid)
    (out/'result.json').write_text(json.dumps(keep,indent=1,sort_keys=True))
    # Multiplicity changes are a circuit screen, never an actual650 layout claim.
    if 'slave_parallel' in VARIANTS[variant]:
        keep['experiment_scope']='64 slave-tail MOS and 8 collector resistors use m=2; effective primitive multiplicity increases by 72. Existing interconnect RC is retained only as a what-if. No new extracted layout.'
        keep['source_topology_run']=43472881982
        keep['reference_variant']=('bd10_slave_parallel2_lowz8' if variant in ('bd10_lowz8_acff4','bd10_lowz8_selectff4','bd10_lowz8_xor2','bd10_lowz8_xor3') else 'bd10_slave_parallel2' if variant=='bd10_slave_parallel2_lowz8' else 'lowz4_bd10')
        (out/'result.json').write_text(json.dumps(keep,indent=1,sort_keys=True))
    print(json.dumps({k:keep[k]for k in('variant','returncode','passed','data_passed','devices_passed','phase_passed','phase_average_v','failing_hbt')},sort_keys=True))
if __name__=='__main__':main(*sys.argv[1:])
