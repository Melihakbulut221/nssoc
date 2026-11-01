#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Frozen 32:1 physical-macro tree: source/runtime controls and backend timing.

This measures complete native startup/early data captures, NOT full-wave or
whole-tree physical acceptance. Original intermacro wires are still ideal.
"""
import argparse,hashlib,json,os,re,resource,shutil,subprocess,tarfile,time
from pathlib import Path
import numpy as np
import cloud_tx_companion_replay as runtime
from cloud_tx_stream import streaming_deck,read_streamed_wave
from cloud_tx_step_factorial import wave_difference
from run_cloud_tx_mux4 import native_diagnostics
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-vbic-tree32-backend'
HEAD='31d4d70464ed0c395ca9c4564e81e101fee849da'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38496981217-1-tree-32-physical_wire-nominal-none/'
STEM='tx-tree-physical-32-physical_wire-nominal-none-38496981217-1'
SUMMARY_SHA='f3bf13ca9bd612d5401bba9c708f8803be576851b677560ebb7da26c102a8aa0'
ARCHIVE_SHA='3755d4c6e3b67fca7bd763d40cde84a76fbf22d6983628a944fc15066f361bce'
COMPACT_SHA='d0ea24db033fa1f5964b5cae3f12ed2831af3fbd241074638a7d38073534c6f4'

def restore_source(packaged):
    summary_path=OUT/'original-summary.json';fetch(BASE+STEM+'.summary.json',SUMMARY_SHA,summary_path)
    summary=json.loads(summary_path.read_text())
    assert summary['streams']==32 and summary['condition']=='nominal' and summary['fault']=='none'
    assert not summary['component_screen_passed'] and summary['review']['all_engineering_gates_passed']
    assert summary['diagnostics']==['Warning - approaching max data size: current size = 4775.711 MB, limit = 4977.488 MB']
    source=ROOT/'cloud-tx-mux4';assert not source.exists()
    packed=OUT/'source.tar.gz';fetch(BASE+STEM+'.tar.gz',ARCHIVE_SHA,packed);assert packed.stat().st_size==2133372821
    seen=set();verified_outputs={};skipped={}
    with tarfile.open(packed,'r|gz') as archive:
        for entry in archive:
            name=Path(entry.name)
            assert not name.is_absolute() and '..' not in name.parts and name.parts[0]=='cloud-tx-mux4'
            assert entry.name not in seen and (entry.isdir() or entry.isfile());seen.add(entry.name)
            if entry.isdir():continue
            relative=str(name.relative_to('cloud-tx-mux4'));target=ROOT/name
            if relative=='native/wave.dat.gz':
                digest=hashlib.file_digest(archive.extractfile(entry),'sha256').hexdigest()
                assert digest==summary['outputs'][relative];skipped[relative]=dict(sha256=digest,bytes=entry.size,reason='Original failed full capture remains in permanent source archive; verified streaming, not copied into new diagnostic output.')
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with archive.extractfile(entry) as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
                digest=sha(target)
            if relative in summary['outputs']:
                assert digest==summary['outputs'][relative];verified_outputs[relative]=digest
    packed.unlink();assert verified_outputs==summary['outputs'] and sha(source/'result.json')==SUMMARY_SHA
    subprocess.run(['git','fetch','--depth=1','origin',HEAD],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    protected={};restored=[]
    for path,digest in summary['inputs'].items():
        path=Path(path)
        if path.is_relative_to(source) or path.suffix in ('.spice','.inc','.lib','.osdi'):
            assert path.is_relative_to(ROOT)
            if not path.exists() or sha(path)!=digest:
                assert not path.is_relative_to(source), 'Archived input changed'
                relative=str(path.relative_to(ROOT));data=subprocess.check_output(['git','show',HEAD+':'+relative],cwd=ROOT)
                assert hashlib.sha256(data).hexdigest()==digest
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);restored.append(relative)
            assert sha(path)==digest;protected[str(path)]=digest
    assert [v for k,v in summary['inputs'].items() if k.endswith('/ngspice')]==[sha(packaged)]
    contract=json.loads((source/'native/contract.json').read_text())
    assert contract['streams']==32 and contract['fault']=='none' and contract['condition']['step_ps']==.5
    assert hashlib.sha256(bytes(contract['bits'])).hexdigest()==summary['review']['signals']['source_bits_sha256']
    assert len(contract['vectors'])==len(set(contract['vectors']))
    return source,contract,protected,dict(source_run=38496981217,source_head=HEAD,source_summary_sha256=SUMMARY_SHA,source_archive_sha256=ARCHIVE_SHA,verified_original_outputs=verified_outputs,original_large_wave_verified=skipped,restored_original_repository_inputs=restored,original_failure_retained=summary['diagnostics'])

def make_deck(original,contract,stop,backend):
    assert stop in (1.2e-9,4e-9) and backend in ('sparse','klu')
    deck=streaming_deck(original,contract)
    rows=re.findall(r'(?m)^\.tran ([^\n]+)$',deck)
    assert len(rows)==1 and list(map(float,rows[0].split()))==[.5e-12,34e-9,0.,.5e-12]
    before='.tran '+rows[0];after=f'.tran 5e-13 {stop:.14g} 0 5e-13'
    changed=deck.replace(before,after);assert changed.replace(after,before)==deck
    if backend=='klu':
        assert not re.search(r'(?im)^\.options? .*\bklu\b',changed)
        changed=changed.replace('.control\n','.options klu\n.control\n')
    assert changed.count('quit\n.endc')==1
    changed=changed.replace('quit\n.endc','echo NSSOC_BACKEND_OPTIONS_BEGIN\noption\necho NSSOC_BACKEND_OPTIONS_END\nrusage > native-resources.txt\nquit\n.endc')
    return changed

def option_values(text,backend):
    assert ('KLU' in text) if backend=='klu' else ('Sparse 1.3' in text)
    numeric={}
    for label,pattern in {'reltol':r'reltol(?:\s+\(current\))?','abstol':r'abstol(?:\s+\(current\))?','vntol':r'vntol(?:\s+\(voltage\))?','trtol':'trtol','maxord':r'(?:maxord|maxorder)','itl4':r'itl4(?:\s+\(transient iterations\))?'}.items():
        values=re.findall(r'(?mi)^\s*'+pattern+r'\s*=\s*(\S+)\s*$',text);assert len(values)==1,(label,values);numeric[label]=float(values[0])
    assert numeric['reltol']==1e-4 and numeric['abstol']==1e-12
    method=re.findall(r'(?mi)^\s*(?:method|integration method)\s*=\s*(\S+)\s*$',text);assert len(method)==1
    return dict(backend=backend,numeric=numeric,method=method[0],native_readback_sha256=hashlib.sha256(text.encode()).hexdigest())

def options(path,backend):
    return option_values(path.read_text(),backend)

def backend_readback(log,backend):
    blocks=re.findall(r'(?ms)^NSSOC_BACKEND_OPTIONS_BEGIN\s*\n(.*?)^NSSOC_BACKEND_OPTIONS_END\s*$',log)
    assert len(blocks)==1 and log.count('NSSOC_BACKEND_OPTIONS_BEGIN')==log.count('NSSOC_BACKEND_OPTIONS_END')==1,'Missing/duplicate native readback scope'
    block=blocks[0];parsed=option_values(block,backend)
    benign={'Truncation error correction, charge based, is selected:','diaggmin (stepping) = 0'}
    inside=False;scoped=[]
    for line in log.splitlines():
        if line.strip()=='NSSOC_BACKEND_OPTIONS_BEGIN':inside=True
        elif line.strip()=='NSSOC_BACKEND_OPTIONS_END':inside=False
        if inside and line.strip() in benign:continue
        scoped.append(line)
    return parsed,native_diagnostics('\n'.join(scoped)),block

def readback_controls():
    block='Sparse 1.3\nreltol (current) = 0.0001\nabstol (current) = 1e-12\nvntol (voltage) = 1e-6\ntrtol = 7\nmaxorder = 2\nitl4 (transient iterations) = 10\nIntegration method = trapezoidal\nTruncation error correction, charge based, is selected:\ndiaggmin (stepping) = 0\n'
    good='NSSOC_BACKEND_OPTIONS_BEGIN\n'+block+'NSSOC_BACKEND_OPTIONS_END\n'
    assert not backend_readback(good,'sparse')[1]
    assert not backend_readback(good.replace('Sparse 1.3','KLU'),'klu')[1]
    rejected=[]
    for name,bad in [('outside_label','diaggmin (stepping) = 0\n'+good),('inside_warning',good.replace('Sparse 1.3','Sparse 1.3\nWarning: genuine failure')),('changed_tolerance',good.replace('0.0001','0.01')),('duplicate',good+good),('missing_marker',good.replace('NSSOC_BACKEND_OPTIONS_END','')),('wrong_backend',good.replace('Sparse 1.3','KLU')),('missing_numeric',good.replace('trtol = 7\n',''))]:
        try:failed=bool(backend_readback(bad,'sparse')[1])
        except AssertionError:failed=True
        assert failed,name;rejected.append(name)
    return dict(positive=2,negative=rejected,only_verified_option_labels_exempted=True)


def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],controller_sha256=sha(Path(__file__)),cases={},
        scope='Source-pinned32:1 tree with actual per-macro RC and original ideal intermacro wires; startup provenance and4ns backend cost comparison only. No full34ns, all-corner, actual whole-tree routing, PLL/CDR, four-lane or PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        result['readback_controls']=readback_controls()
        runtime.OUT=OUT;paths,provenance=runtime.restore_engines();result['runtime_provenance']=provenance
        gate=OUT/'compact-gate.json';fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38796689216-1-vbic-full-window/vbic-full-window-38796689216-1.summary.json',COMPACT_SHA,gate)
        compact=json.loads(gate.read_text());assert compact['compact_numerical_component_screen_passed'] and compact['protected_inputs_unchanged']
        assert compact['cases']['patched-0.125']['executable_sha256']==sha(paths['patched'])
        source,contract,protected,receipt=restore_source(paths['packaged']);result.update(source_receipt=receipt,protected_inputs=protected,hbt_count=len(contract['hbt']),mos_count=len(contract['mos']),native_vector_count=len(contract['vectors']));save()
        original=(source/'native/bench.cir').read_text();captures={}
        for variant,backend,stop in [('packaged','sparse',1.2e-9),('pristine','sparse',1.2e-9),('patched','sparse',4e-9),('patched','klu',4e-9)]:
            if variant=='patched':assert result.get('pristine_reproduces_packaged_to_1nv')
            name=variant+'-'+backend;directory=OUT/name;directory.mkdir()
            (directory/'bench.cir').write_text(make_deck(original,contract,stop,backend));shutil.copyfile(source/'native/spinit',directory/'spinit')
            row=dict(variant=variant,backend=backend,stop_s=stop,tstep_s=.5e-12,tmax_s=.5e-12,executable_sha256=sha(paths[variant]),complete=False);result['cases'][name]=row;save()
            try:
                env={k:v for k,v in os.environ.items() if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(directory),OMP_NUM_THREADS='1',RAYON_NUM_THREADS='1')
                def limits():
                    resource.setrlimit(resource.RLIMIT_AS,(12*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0));os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
                started=time.monotonic()
                with (directory/'run.log').open('w') as log:proc=subprocess.run([str(paths[variant]),'-n','-b','bench.cir'],cwd=directory,env=env,preexec_fn=limits,stdout=log,stderr=subprocess.STDOUT,timeout=8400)
                row.update(elapsed_s=time.monotonic()-started,returncode=proc.returncode)
                text=(directory/'run.log').read_text(errors='replace')
                row['native_options'],row['diagnostics'],option_block=backend_readback(text,backend)
                (directory/'native-options.txt').write_text(option_block)
                assert proc.returncode==0 and not row['diagnostics'],'Native process/diagnostic failure'
                flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',text)
                assert [a for a,b in flags]==['q.'+n+'.qnpn13g2' for n in contract['hbt']]
                assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',b)==['1'] for a,b in flags)
                op=np.loadtxt(directory/'op.dat',skiprows=1);assert op.size==len(contract['vectors'])+1 and np.isfinite(op).all() and abs(op).max()<=1e-10
                row['native_options']=options(directory/'native-options.txt',backend)
                t,v,cap=read_streamed_wave(directory/'wave.raw',contract['vectors'],stop,.5e-12);captures[name]=(t,v);row.update(complete=True,capture=cap)
                if variant=='pristine':
                    compared=wave_difference(captures['packaged-sparse'],captures[name],contract['vectors'],end=stop)
                    result['pristine_packaged_comparison']=compared;result['pristine_reproduces_packaged_to_1nv']=compared['worst_voltage_difference_v']<=1e-9
            except Exception as error:row['error']=repr(error)
            save();print(json.dumps(dict(case=name,complete=row['complete'],elapsed_s=row.get('elapsed_s'),error=row.get('error'))),flush=True)
        if all(n in captures for n in ('patched-sparse','patched-klu')):
            a=result['cases']['patched-sparse'];b=result['cases']['patched-klu']
            assert a['native_options']['numeric']==b['native_options']['numeric'] and a['native_options']['method']==b['native_options']['method']
            compared=wave_difference(captures['patched-sparse'],captures['patched-klu'],contract['vectors'],end=4e-9)
            result['patched_backend_comparison']=compared;result['backend_voltage_agreement_to_1nv']=compared['worst_voltage_difference_v']<=1e-9
            result['sparse_over_klu_elapsed_ratio']=a['elapsed_s']/b['elapsed_s']
        assert all(sha(Path(p))==d for p,d in protected.items());result['protected_inputs_unchanged']=True
        result['all_native_cases_complete']=all(c['complete'] for c in result['cases'].values())
        result['status']='COMPLETE_TREE32_BACKEND_DIAGNOSIS_NOT_FULL_WAVE_OR_PHY_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls-only',action='store_true');a=p.parse_args()
    if a.controls_only:print(json.dumps(readback_controls()))
    else:main()
