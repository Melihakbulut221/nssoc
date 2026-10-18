#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Full physical CDR model, 3 ns all-vector transport equivalence, not acceptance."""
import json,os,re,subprocess
from pathlib import Path
import numpy as np
import cloud_tx_stream as stream
from run_cloud_tx_mux4 import native_save_commands
from cloud_vbic_tree32_backend import backend_readback,readback_controls
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-cdr-via-rich-stream-control'
SAVE_HELPER_SHA='bb7f5c5ef736dd54c5ed560424d97d248894f4aa6fa6119f1e95c5f5c3df4b52'
STREAM_SHA='2894eede2e5e087c23cadee9cec9dbdca359315a786cec0cabfe7f8da37449cb'
ENGINE_SHA='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False,loaded_screen_passed=False,scope='Same full484-device13186R10127C model; all1107 vectors and native samples over3ns compared between original ASCII in-memory and binary streamed transport. Shortened interval only for transport validation; full34.25ns loaded acceptance remains separately required.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        assert sha(Path(stream.__file__))==STREAM_SHA;r['readback_controls']=readback_controls()
        pin=json.loads((ROOT/'docs/evidence/cdr-via-rich-v7-loaded-memory-rejection-20261018.json').read_text());source=ROOT/'cloud-cdr-via-rich-v7-mim-loaded-nominal_early'
        selected=[p for p in pin['report']['outputs']if p.startswith('models/')]+['native/bench.cir','native/spinit','native/native.log','composed/pd484-mim-wire.spice','source/source/runtime/patched-ngspice']
        original,proof=reports.restore_report('cdr-via-rich-v7-mim-loaded-nominal_early',pin['run'],pin['summary_sha256'],pin['parts_sha256'],source,selected)
        assert original==pin['report']and original['status']=='FAIL_OR_ERROR'and original['returncode']==0
        assert original['diagnostics']and all('approaching max data size'in s for s in original['diagnostics']);r['failed_source']=proof
        vectors=original['vectors'];assert len(vectors)==1107
        deck=(source/'native/bench.cir').read_text();rows=re.findall(r'(?m)^tran ([^\n]+)$',deck);assert len(rows)==1
        step,stop,start,tmax=map(float,rows[0].split());assert step==tmax==.3125e-12 and stop==34.25e-9 and start==0
        before='tran '+rows[0];after=f'tran {step:.14g} 3e-9 0 {tmax:.14g}'
        short=deck.replace(before,after);assert short.replace(after,before)==deck
        r['interval_adaptation']=dict(before=before,after=after,original_source_and_saved_vectors_unchanged=True)
        assert sha(ROOT/'scripts/run_cloud_tx_mux4.py')==SAVE_HELPER_SHA
        overflow=[line for line in (source/'native/native.log').read_text().splitlines()if 'save'in line.lower()and 'too many'in line.lower()]
        assert overflow,'Original native log must establish actual save-command rejection'
        saves=native_save_commands(vectors);assert len(saves)==9 and all(len(line.split())-1<=128 for line in saves)
        assert [v for line in saves for v in line.split()[1:]]==vectors
        original_save='save '+' '.join(vectors);assert short.count(original_save)==1
        short=short.replace(original_save,'\n'.join(saves))
        r['save_command_repair']=dict(original_native_errors=overflow,original_arguments=len(vectors),commands=saves,commands_count=len(saves),all_vectors_in_original_order=True,helper_sha256=SAVE_HELPER_SHA)
        prior_pin=json.loads((ROOT/'docs/evidence/cdr-via-rich-stream-width-rejection-20261019.json').read_text())
        old_capture,old_proof=reports.restore_report('cdr-via-rich-stream-control',prior_pin['run'],prior_pin['summary_sha256'],prior_pin['parts_sha256'],OUT/'old-unbounded-save',['legacy/wave.dat'])
        assert old_capture==prior_pin['report'];r['old_unbounded_save_source']=old_proof
        engine=source/'source/source/runtime/patched-ngspice';assert sha(engine)==ENGINE_SHA;engine.chmod(0o755)
        protected={str(source/p):original['outputs'][p]for p in selected};captures={}
        for mode,body in [('legacy',short),('streamed',stream.streaming_deck(short,dict(vectors=vectors)))]:
            dest=OUT/mode;dest.mkdir();(dest/'bench.cir').write_text(body);(dest/'spinit').write_bytes((source/'native/spinit').read_bytes())
            env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(dest),OMP_NUM_THREADS='1')
            with(dest/'native.log').open('w')as f:p=subprocess.run([str(engine),'-n','-b','bench.cir'],cwd=dest,env=env,stdout=f,stderr=subprocess.STDOUT)
            log=(dest/'native.log').read_text()
            r.setdefault('native_processes',{})[mode]=dict(returncode=p.returncode,log_sha256=sha(dest/'native.log'));save()
            if p.returncode or 'NSSOC_BACKEND_OPTIONS_BEGIN'not in log:print(log[-12000:],flush=True)
            options,notes,_=backend_readback(log,'klu')
            assert not any('too many arg'in line.lower()for line in log.splitlines()),'Native command rejected'
            captures[mode]=dict(returncode=p.returncode,native_options=options,diagnostics=notes,deck_sha256=sha(dest/'bench.cir'));r['captures']=captures;save()
            assert p.returncode==0 and not notes
            flags=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',log)
            assert len(flags)==116 and all(re.findall(r'(?m)^\s*off\s+([01])\s*$',s)==['1']for _,s in flags)
            assert [n for n,_ in flags]==['q.'+n+'.qnpn13g2'for n in original['devices']]
            op=np.loadtxt(dest/'op.dat',skiprows=1);assert op.size==1108 and np.isfinite(op).all()and abs(op).max()<1e-9
            captures[mode]['zero_source_op_maximum']=float(abs(op).max())
        assert captures['legacy']['native_options']['numeric']==captures['streamed']['native_options']['numeric']and captures['legacy']['native_options']['method']==captures['streamed']['native_options']['method']
        with(OUT/'legacy/wave.dat').open()as f:assert f.readline().lower().split()==['time',*vectors]
        legacy=np.loadtxt(OUT/'legacy/wave.dat',skiprows=1)
        t,values,capture=stream.read_streamed_wave(OUT/'streamed/wave.raw',vectors,3e-9,step)
        r['transport_comparison']=stream.compare_complete(legacy,t,values,vectors);r['stream_capture']=capture
        old_samples=np.loadtxt(OUT/'old-unbounded-save/legacy/wave.dat',skiprows=1)
        voltage_ids=[i for i,n in enumerate(vectors,1)if n.startswith('v(')]
        r['unchanged_voltage_samples']=stream.compare_complete(old_samples[:,[0,*voltage_ids]],t,{n:values[n]for n in vectors if n.startswith('v(')},[n for n in vectors if n.startswith('v(')])
        r['current_history_diagnosis']={n:dict(old_distinct_values=int(len(np.unique(old_samples[:,i]))),new_distinct_values=int(len(np.unique(values[n]))),old_min=float(old_samples[:,i].min()),old_max=float(old_samples[:,i].max()),new_min=float(values[n].min()),new_max=float(values[n].max()))for i,n in enumerate(vectors,1)if n.startswith('@')}
        assert len(r['current_history_diagnosis'])==162
        assert all(x['new_distinct_values']>1 for x in r['current_history_diagnosis'].values()),'Every actual device current must be present as a native transient history'
        assert sha(OUT/'old-unbounded-save/legacy/wave.dat')==old_capture['outputs']['legacy/wave.dat']
        r['transport_controls']=[];saved=float(legacy[1,1]);legacy[1,1]+=.01
        try:stream.compare_complete(legacy,t,values,vectors)
        except AssertionError:r['transport_controls'].append(dict(case='actual_saved_value_changed',rejected=True))
        else:raise AssertionError('Accepted changed native sample')
        finally:legacy[1,1]=saved
        try:stream.read_streamed_wave(OUT/'streamed/wave.raw',vectors[:-1],3e-9,step)
        except AssertionError:r['transport_controls'].append(dict(case='missing_expected_vector',rejected=True))
        else:raise AssertionError('Accepted omitted vector')
        assert all(sha(Path(p))==h for p,h in protected.items())and sha(Path(stream.__file__))==STREAM_SHA and sha(ROOT/'scripts/run_cloud_tx_mux4.py')==SAVE_HELPER_SHA
        r['sources_unchanged']=True;r['status']='PASS_FULL_CDR_MODEL_ALL_VECTOR_3NS_STREAM_TRANSPORT_REQUIRES_FULL_LOADED_SCREEN'
    except BaseException as e:r.update(status='FAIL_STREAM_TRANSPORT_CONTROL',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
