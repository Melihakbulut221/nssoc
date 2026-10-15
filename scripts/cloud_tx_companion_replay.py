#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Paired pristine/patched native engine on the unchanged frozen coupled tree."""
import argparse,copy,hashlib,json,os,re,resource,shutil,subprocess,tarfile,time
from pathlib import Path
from cloud_tx_step_factorial import restore,replace_analysis,charge_deck,wave_difference,STEPS,STOP,PROFILE
from cloud_tx_stream import read_streamed_wave
from run_cloud_tx_mux4 import verify_solver_options,native_diagnostics
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-vbic-coupled-replay'
RUNTIME_BASE='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38793936101-1-vbic-companion/'
REFERENCE_BASE='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38789786404-1-tree-step-factorial/'

def restore_engines():
    packed=OUT/'runtimes.tar.gz';fetch(RUNTIME_BASE+'vbic-companion-38793936101-1.tar.gz','71a7334475d5d9c18dc01e47661e2ff356a516586e6cc0f1ad1f0e4ae916694b',packed)
    assert packed.stat().st_size==23540070
    engine_dir=OUT/'runtime';engine_dir.mkdir();reports={};paths={}
    with tarfile.open(packed) as archive:
        for name in ('packaged','pristine','patched'):
            raw=archive.extractfile('cloud-vbic-companion/'+name+'.json').read();report=json.loads(raw)
            assert report['variant']==name;reports[name]=report
            data=archive.extractfile('cloud-vbic-companion/runtime/'+name+'-ngspice').read()
            assert data[:4]==b'\x7fELF' and hashlib.sha256(data).hexdigest()==report['executable_sha256']
            path=engine_dir/(name+'-ngspice');path.write_bytes(data);path.chmod(0o755);paths[name]=path
            (engine_dir/(name+'.json')).write_bytes(raw)
        patch=json.loads(archive.extractfile('cloud-vbic-companion/patch.json').read())
        assert patch['original_sha256']=='ae2fca22ca7178bce26f31b4e433307945cafa9d8661d55007eed8fc096ff866'
        assert patch['patched_sha256']=='aafdf5b06a6965c995a70321dc6edaab34ad1f0698dd42e8e15adca22088cb25'
        assert patch['one_expression_only'] and not patch['physical_model_parameters_changed']
        (engine_dir/'companion.patch').write_bytes(archive.extractfile('cloud-vbic-companion/companion.patch').read())
    assert sha(paths['packaged'])=='eaca52dad06845779fed4f50420a6a0cf4a32776e6a572432275f350002b87b8'
    assert all(row['complete'] and row['current_dc_invariance_1na'] for row in reports['patched']['cases'].values())
    for name in ('packaged','pristine'):
        assert all(row['complete'] and row['current_dc_invariance_1na'] for row in reports[name]['cases'].values() if row['qco']==0)
        assert all(not row['complete'] and row['diagnostics'] for row in reports[name]['cases'].values() if row['qco']>0)
    packed.unlink();return paths,dict(patch=patch,synthetic_reports=reports)


def references(vectors):
    summary_path=OUT/'reference-summary.json';fetch(REFERENCE_BASE+'tx-step-factorial-38789786404-1.summary.json','d5983fd5a49ad2ba603631712505de80cb725a231dfbbadd1fc1b6b142ac3154',summary_path)
    summary=json.loads(summary_path.read_text());packed=OUT/'reference.tar.gz'
    fetch(REFERENCE_BASE+'tx-step-factorial-38789786404-1.tar.gz','90394c65cbb5afe8f58f45f9b6d2e6ae7420c1e902ff6a62868f483c17b71d19',packed)
    assert packed.stat().st_size==104696029
    result={}
    with tarfile.open(packed) as archive:
        for step in STEPS:
            label=f'tstep0.125-tmax{step*1e12:g}';name=label+'/wave.raw'
            raw=archive.extractfile('cloud-tx-step-factorial/'+name).read();assert hashlib.sha256(raw).hexdigest()==summary['outputs'][name]
            path=OUT/'reference'/label/'wave.raw';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            t,v,receipt=read_streamed_wave(path,vectors,STOP,step);assert receipt==summary['cases'][label]['capture']
            result[step]=(t,v)
    packed.unlink();return result


def main(full_window=False,mode='compact',compact_summary_sha256=None):
    assert mode in ('compact','wire') and (mode=='compact' or full_window)
    global OUT
    if full_window:OUT=ROOT/('cloud-vbic-full-window' if mode=='compact' else 'cloud-vbic-full-wire')
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],cases={},
        original_circuit_changed=False,original_engineering_gates_changed=False,
        full_window=full_window,mode=mode,
        scope='Same frozen62HBT64MOS coupled compact tree startup prefix, same all native vectors, sources, PDK and original strict solver profile. Pristine source binary must reproduce packaged reference before patched cases. Engine experiment only: no full34ns/PVT/physical/fullPHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    if full_window:result['scope']='Full original34ns coupled tree; unchanged physical sources, models, bits, solver and engineering gates. Patched engine experimental; not fullPHY acceptance.'
    save()
    try:
        paths,provenance=restore_engines();result['runtime_provenance']=provenance;save()
        if mode=='wire':
            assert compact_summary_sha256 and re.fullmatch(r'[0-9a-f]{64}',compact_summary_sha256)
            compact_path=OUT/'compact-gate.json'
            fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38796689216-1-vbic-full-window/vbic-full-window-38796689216-1.summary.json',compact_summary_sha256,compact_path)
            compact=json.loads(compact_path.read_text())
            assert compact['source_head']=='d14078e2aefda63d06d03fbea9b128fe8b66d71a'
            assert compact['full_window'] and compact['protected_inputs_unchanged'] and compact['pristine_reproduces_packaged_reference'] and compact['all_simulations_complete']
            assert compact['compact_numerical_component_screen_passed'] and compact['comparisons']['patched-0.125-to-0.0625']['passed']
            for label in ('patched-0.125','patched-0.0625'):
                assert compact['cases'][label]['executable_sha256']==sha(paths['patched'])
                assert compact['cases'][label]['engineering_review']['all_engineering_gates_passed'] and not compact['cases'][label].get('error')
            result['compact_prerequisite']={'run':38796689216,'sha256':compact_summary_sha256,'passed':True}
        os.environ['CLOUD_NGSPICE']=str(paths['packaged'])
        spec=json.loads((ROOT/'docs/evidence/pcie-tree4-assembly-input-20261015.json').read_text())
        rows=[c for study in spec['placement_variants']['compact_edge_supply']['loaded_studies'] if study['run']==38763917040 for c in study['cases'] if c['mode']==mode and c['condition']=='hot_low_eighth_step' and c['fault']=='none']
        assert len(rows)==1;source,original_summary,contract,protected=restore(rows[0],OUT,mode)
        result['source_receipt']=rows[0];result['verified_circuit_inputs']=protected
        original=(source/'native/bench.cir').read_text();captures={}
        pristine_steps=STEPS if mode=='compact' else STEPS[:1]
        if mode=='compact':old=references(contract['vectors'])
        else:
            from run_cloud_tx_mux4 import STOP as source_stop
            rt,rv,rr=read_streamed_wave(source/'native/wave.raw',contract['vectors'],source_stop,STEPS[0])
            assert rr==original_summary['review']['capture_transport']
            old={STEPS[0]:(rt,rv)}
            result['original_wire_capture']=rr
        if full_window:
            from analyze_cloud_assembled_wave import step_metrics,step_controls
            from run_cloud_tx_mux4 import review,STOP as full_stop
            result['numerical_controls']=step_controls()

        for variant,steps in [('pristine',pristine_steps),('patched',STEPS if full_window else (*STEPS,.03125e-12))]:
            if variant=='patched':assert result.get('pristine_reproduces_packaged_reference'), 'Pristine provenance control must pass before patch experiment'
            for step in steps:
                label=variant+'-'+str(step*1e12);case=OUT/label;case.mkdir()
                stop=full_stop if full_window and variant=='patched' else STOP
                deck=replace_analysis(original,STEPS[0],step)
                if full_window and variant=='patched':
                    prefix_line=f'.tran {STEPS[0]:.14g} {STOP:.14g} 0 {step:.14g}'
                    full_line=f'.tran {STEPS[0]:.14g} {full_stop:.14g} 0 {step:.14g}'
                    assert deck.count(prefix_line)==1
                    deck=deck.replace(prefix_line,full_line)
                    original_line=re.findall(r'(?m)^\.tran [^\n]+$',original)
                    assert len(original_line)==1 and deck.replace(full_line,original_line[0])==original
                deck=charge_deck(deck,None)
                (case/'bench.cir').write_text(deck);shutil.copyfile(source/'native/spinit',case/'spinit')
                row=dict(variant=variant,step_s=step,stop_s=stop,executable_sha256=sha(paths[variant]),complete=False,accepted=False);result['cases'][label]=row;save()
                try:
                    env={k:v for k,v in os.environ.items() if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')}
                    env.update(SPICE_SCRIPTS=str(case),OMP_NUM_THREADS='1',RAYON_NUM_THREADS='1')
                    def limits():
                        resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
                    start=time.monotonic()
                    with (case/'run.log').open('w') as log:
                        proc=subprocess.run([str(paths[variant]),'-n','-b','bench.cir'],cwd=case,env=env,preexec_fn=limits,stdout=log,stderr=subprocess.STDOUT,timeout=(8400 if full_window and mode=='wire' else 1800))
                    text=(case/'run.log').read_text(errors='replace');row.update(returncode=proc.returncode,elapsed_s=time.monotonic()-start)
                    row['solver_options']=verify_solver_options(text,PROFILE);row['diagnostics']=native_diagnostics(text,PROFILE)
                    assert proc.returncode==0 and not row['diagnostics'],'Native diagnostic/process failure'
                    flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',text)
                    assert [x[0] for x in flags]==['q.'+n+'.qnpn13g2' for n in contract['hbt']]
                    assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',body)==['1'] for _,body in flags)
                    import numpy as np
                    op=np.loadtxt(case/'op.dat',skiprows=1);assert op.size==len(contract['vectors'])+1 and np.isfinite(op).all() and abs(op).max()<=1e-10
                    t,v,receipt=read_streamed_wave(case/'wave.raw',contract['vectors'],stop,step)
                    captures[(variant,step)]=(t,v);row.update(complete=True,capture=receipt)
                    if full_window and variant=='patched':
                        case_contract=copy.deepcopy(contract);case_contract['condition']['step_ps']=step*1e12
                        (case/'contract.json').write_text(json.dumps(case_contract,indent=2)+'\n')
                        row['engineering_review']=review(case,case_contract)
                    if variant=='pristine':
                        comparison=wave_difference((t,v),old[step],contract['vectors']);row['packaged_reference_comparison']=comparison
                        row['packaged_voltage_reproduced_to_1nv']=comparison['worst_voltage_difference_v']<=1e-9
                except Exception as error:row['error']=repr(error)
                save();print(json.dumps(dict(case=label,complete=row['complete'],error=row.get('error'))),flush=True)
            if variant=='pristine':
                result['pristine_reproduces_packaged_reference']=all(result['cases']['pristine-'+str(step*1e12)].get('packaged_voltage_reproduced_to_1nv',False) for step in pristine_steps);save()
        result['comparisons']={};result['unavailable_comparisons']=[]
        for variant,steps in [('pristine',pristine_steps),('patched',STEPS if full_window else (*STEPS,.03125e-12))]:
            for a,b in zip(steps,steps[1:]):
                name=f'{variant}-{a*1e12:g}-to-{b*1e12:g}'
                if (variant,a) in captures and (variant,b) in captures:
                    result['comparisons'][name]=(step_metrics(captures[(variant,a)],captures[(variant,b)],contract) if full_window and variant=='patched' else wave_difference(captures[(variant,a)],captures[(variant,b)],contract['vectors']))
                else:result['unavailable_comparisons'].append(name)
        assert all(sha(Path(path))==digest for path,digest in protected.items())
        result['all_simulations_complete']=all(c['complete'] for c in result['cases'].values())
        result['protected_inputs_unchanged']=True
        result['status']='COMPLETE_PAIRED_RUNTIME_COUPLED_STARTUP_DIAGNOSIS_NOT_ACCEPTANCE'
        if full_window:
            result['numerical_component_screen_passed']=(result['all_simulations_complete'] and not result['unavailable_comparisons'] and all(row.get('engineering_review',{}).get('all_engineering_gates_passed',False) for row in result['cases'].values() if row['variant']=='patched') and result['comparisons'].get('patched-0.125-to-0.0625',{}).get('passed',False))
            result['status']='COMPLETE_FULL_WINDOW_'+mode.upper()+'_ENGINE_EXPERIMENT_NOT_PHY_ACCEPTANCE'
            if mode=='compact':result['compact_numerical_component_screen_passed']=result['numerical_component_screen_passed']
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--full-window',action='store_true')
    parser.add_argument('--mode',choices=['compact','wire'],default='compact');parser.add_argument('--compact-summary-sha256')
    args=parser.parse_args();main(args.full_window,args.mode,args.compact_summary_sha256)
