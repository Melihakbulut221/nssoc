#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Full physical CDR model, 3 ns all-vector transport equivalence, not acceptance."""
import json,os,re,subprocess
from pathlib import Path
import numpy as np
import cloud_tx_stream as stream
from cloud_vbic_tree32_backend import backend_readback,readback_controls
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-cdr-via-rich-stream-control'
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
        selected=[p for p in pin['report']['outputs']if p.startswith('models/')]+['native/bench.cir','native/spinit','composed/pd484-mim-wire.spice','source/source/runtime/patched-ngspice']
        original,proof=reports.restore_report('cdr-via-rich-v7-mim-loaded-nominal_early',pin['run'],pin['summary_sha256'],pin['parts_sha256'],source,selected)
        assert original==pin['report']and original['status']=='FAIL_OR_ERROR'and original['returncode']==0
        assert original['diagnostics']and all('approaching max data size'in s for s in original['diagnostics']);r['failed_source']=proof
        vectors=original['vectors'];assert len(vectors)==1107
        deck=(source/'native/bench.cir').read_text();rows=re.findall(r'(?m)^tran ([^\n]+)$',deck);assert len(rows)==1
        step,stop,start,tmax=map(float,rows[0].split());assert step==tmax==.3125e-12 and stop==34.25e-9 and start==0
        before='tran '+rows[0];after=f'tran {step:.14g} 3e-9 0 {tmax:.14g}'
        short=deck.replace(before,after);assert short.replace(after,before)==deck
        r['interval_adaptation']=dict(before=before,after=after,original_source_and_saved_vectors_unchanged=True)
        engine=source/'source/source/runtime/patched-ngspice';assert sha(engine)==ENGINE_SHA;engine.chmod(0o755)
        protected={str(source/p):original['outputs'][p]for p in selected};captures={}
        for mode,body in [('legacy',short),('streamed',stream.streaming_deck(short,dict(vectors=vectors)))]:
            dest=OUT/mode;dest.mkdir();(dest/'bench.cir').write_text(body);(dest/'spinit').write_bytes((source/'native/spinit').read_bytes())
            env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')};env.update(SPICE_SCRIPTS=str(dest),OMP_NUM_THREADS='1')
            with(dest/'native.log').open('w')as f:p=subprocess.run([str(engine),'-n','-b','bench.cir'],cwd=dest,env=env,stdout=f,stderr=subprocess.STDOUT)
            log=(dest/'native.log').read_text();options,notes,_=backend_readback(log,'klu')
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
        r['transport_controls']=[];saved=float(legacy[1,1]);legacy[1,1]+=.01
        try:stream.compare_complete(legacy,t,values,vectors)
        except AssertionError:r['transport_controls'].append(dict(case='actual_saved_value_changed',rejected=True))
        else:raise AssertionError('Accepted changed native sample')
        finally:legacy[1,1]=saved
        try:stream.read_streamed_wave(OUT/'streamed/wave.raw',vectors[:-1],3e-9,step)
        except AssertionError:r['transport_controls'].append(dict(case='missing_expected_vector',rejected=True))
        else:raise AssertionError('Accepted omitted vector')
        assert all(sha(Path(p))==h for p,h in protected.items())and sha(Path(stream.__file__))==STREAM_SHA
        r['sources_unchanged']=True;r['status']='PASS_FULL_CDR_MODEL_ALL_VECTOR_3NS_STREAM_TRANSPORT_REQUIRES_FULL_LOADED_SCREEN'
    except BaseException as e:r.update(status='FAIL_STREAM_TRANSPORT_CONTROL',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
