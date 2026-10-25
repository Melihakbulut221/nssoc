#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only intrinsic241 reset waveform diagnostic; preserves failures and raw."""
import argparse,hashlib,json,os,re,shutil,subprocess,tarfile,time
from pathlib import Path
import numpy as np
import tx_phase_async_preset_diagnostic as bench
import cloud_tx_companion_replay as runtime
from cloud_tx_stream import read_streamed_wave
from run_cloud_tx_mux4 import native_diagnostics,verify_solver_options
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-phase-async-preset-intrinsic'
METHOD=ROOT/'scripts/tx-phase-async-preset-intrinsic-methods.json'
ENGINE_SHA='103134f6e3bf71771a7f9c94cc43fd5ea2f9d51490116718814aa344e9c51509'
def source_pins():
    d=json.loads(METHOD.read_text())
    for p,h in d['protected'].items():assert sha(ROOT/p)==h,p
    return d['protected']
def observer():
    data=subprocess.check_output(['gh','api',f'repos/Melihakbulut221/nssoc/releases/assets/{bench.OBSERVER_ASSET}','-H','Accept: application/octet-stream'])
    assert hashlib.sha256(data).hexdigest()==bench.OBSERVER_SHA
    return data,bench.boundary(data)
def restore():
    runtime.OUT=OUT
    engines,proof=runtime.restore_engines()
    engine=engines['patched'];assert sha(engine)==ENGINE_SHA
    spec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-input-20261013.json').read_text())
    r=spec['receipt'];packed=OUT/'models.tar.gz'
    fetch(r['url'],r['sha256'],packed);assert packed.stat().st_size==r['bytes']==109934
    dest=OUT/'models';dest.mkdir()
    with tarfile.open(packed)as ar:
        members=ar.getmembers();names=[m.name for m in members]
        assert len(names)==len(set(names))
        for m in members:
            p=Path(m.name);assert not p.is_absolute()and '..'not in p.parts and (m.isfile()or m.isdir())
        ar.extractall(dest,filter='data')
    manifest=json.loads((dest/'manifest.json').read_text())
    for name,record in manifest['files'].items():
        p=dest/name
        assert p.is_file()and p.stat().st_size==record['bytes']and sha(p)==record['sha256']
    required=[dest/'models'/('corner'+k+'.lib')for k in ('HBT','RES','CAP')]+[dest/'r3_cmc.osdi']
    assert all(p.is_file()for p in required)
    packed.unlink()
    return engine,dest,dict(engine_sha256=ENGINE_SHA,engine_provenance=proof,model_receipt=r,model_manifest=manifest)
def zero_op(path,vectors):
    raw=path.read_bytes();mark=raw.find(b'Binary:\n',0,1048576);assert mark>=0
    offset=mark+8;head=raw[:offset].decode('ascii')
    def field(k):
        matches=[l.split(':',1)[1].strip()for l in head.splitlines()if l.startswith(k+':')]
        assert len(matches)==1
        return matches[0]
    assert field('Flags')=='real'and field('Plotname').lower()=='operating point'and field('No. Points')=='1'
    rows=[r.split()for r in head.split('Variables:\n',1)[1].split('Binary:\n',1)[0].splitlines()]
    assert len(rows)==int(field('No. Variables'))and all(len(r)==3 for r in rows)
    assert [r[0]for r in rows]==list(map(str,range(len(rows))))
    aliases={}
    for name in vectors:
        for n in ([name,'i('+name+')']if name.startswith('@')else[name]):aliases[n]=name
    observed=[aliases[r[1]]for r in rows]
    assert set(observed)==set(vectors)
    # ngspice write may repeat its first saved variable as the OP scale only.
    duplicates=len(observed)==len(vectors)+1 and observed[0]==observed[1]
    assert (len(observed)==len(vectors)and len(set(observed))==len(observed))or(duplicates and len(set(observed[1:]))==len(vectors))
    assert len(raw)-offset==8*len(rows)
    values=np.frombuffer(raw[offset:],dtype='<f8');assert np.isfinite(values).all()
    if duplicates:assert raw[offset:offset+8]==raw[offset+8:offset+16]
    for r,name,value in zip(rows,observed,values,strict=True):
        kind='voltage'if name.startswith('v(')else'current'
        assert r[2]==kind and abs(value)<=(1e-9 if kind=='voltage'else 1e-12)
    return dict(all_saved_electrical_and_thermal_states_zero=True,rows=1,columns=len(rows),explicit_scale_duplicate=duplicates,sha256=sha(path))
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    protected=source_pins();OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING_INTRINSIC_RESET_DIAGNOSTIC',run_id=os.environ['GITHUB_RUN_ID'],source_head=os.environ['GITHUB_SHA'],
      scope='Fresh fixture-driven34ns intrinsic241 transient for four preset/initial-clock cases. Native106HBT/127R/8MIM. All raw columns/steps preserved. Original tight solver/4GHz/125ps UI and unchanged HBT limits. External clock/ARM scalar fixtures come from completed PLL observation; not its actual waveform. No old55 layout/RC reused, no real reset distribution, no31-cell loaded tree, noPLL or PHY acceptance.',
      native_cases={},protected=protected,reset_hardware_qualified=False,layout_RC_included=False,PLL_connected=False,full_PHY_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        raw,bound=observer();(OUT/'pll-observer.summary.json').write_bytes(raw);r['boundary']=bound;save()
        engine,models,proof=restore();r['runtime_and_models']=proof;save()
        text=(ROOT/bench.builder.OUTPUT).read_text()
        assert bench.digest(text)==bench.SOURCE_SHA
        for sign in ('p','n'):
            for initial in (True,False):
                label=sign+'-'+('initial-high'if initial else'initial-low')
                case=OUT/label;case.mkdir();row=dict(complete=False,diagnostic_screen_passed=False);r['native_cases'][label]=row
                try:
                    source=case/'candidate.spice';source.write_text(text)
                    deck,contract=bench.prepare(text,bound,sign,initial,source,models/'models',models/'r3_cmc.osdi')
                    (case/'bench.cir').write_text(deck);(case/'contract.json').write_text(json.dumps(contract,indent=2)+'\n')
                    (case/'spinit').write_text('set num_threads=1\n')
                    row.update(deck_sha256=sha(case/'bench.cir'),source_sha256=sha(source),contract_sha256=sha(case/'contract.json'),hbt_count=106,primitive_count=241,vector_count=len(contract['vectors']))
                    save();start=time.monotonic()
                    env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN','LD_PRELOAD','PYTHONPATH','PYTHONHOME')}
                    env.update(SPICE_SCRIPTS=str(case),OMP_NUM_THREADS='1',GLIBC_TUNABLES='glibc.cpu.hwcaps=-AVX512F,-AVX512CD,-AVX512BW,-AVX512DQ,-AVX512ER,-AVX512PF,-AVX512VL,-RTM')
                    with (case/'native.log').open('w')as log:
                        proc=subprocess.Popen([str(engine),'-n','-b','bench.cir'],cwd=case,env=env,stdout=log,stderr=subprocess.STDOUT)
                        row['native_pid']=proc.pid;row['started_epoch']=time.time();save()
                        while proc.poll()is None:
                            try:proc.wait(timeout=30)
                            except subprocess.TimeoutExpired:
                                row['elapsed_s']=time.monotonic()-start
                                row['raw_bytes']=(case/'wave.raw').stat().st_size if (case/'wave.raw').exists()else 0
                                save();print(json.dumps(dict(case=label,elapsed_s=row['elapsed_s'],raw_bytes=row['raw_bytes'])),flush=True)
                    row.update(returncode=proc.returncode,elapsed_s=time.monotonic()-start);row.pop('native_pid',None)
                    log=(case/'native.log').read_text(errors='replace')
                    row['native_log_tail']=log[-16384:];row['native_log_sha256']=sha(case/'native.log')
                    row['solver']=verify_solver_options(log,bench.PROFILE)
                    row['diagnostics']=native_diagnostics(log,bench.PROFILE)
                    assert proc.returncode==0 and not row['diagnostics'],'Native diagnostics/process failure'
                    row['zero_source_op']=zero_op(case/'op.raw',contract['vectors'])
                    t,values,capture=read_streamed_wave(case/'wave.raw',contract['vectors'],bench.STOP,bench.STEP)
                    row['capture']=capture;row['measurement']=bench.review(t,values,contract)
                    row.update(complete=True,diagnostic_screen_passed=row['measurement']['diagnostic_screen_passed'])
                    assert sha(case/'bench.cir')==row['deck_sha256']and sha(source)==bench.SOURCE_SHA
                except BaseException as exc:
                    row['error']=repr(exc)
                save();print(json.dumps(dict(case=label,complete=row['complete'],diagnostic_screen_passed=row['diagnostic_screen_passed'],error=row.get('error'))),flush=True)
        assert source_pins()==protected and sha(engine)==ENGINE_SHA
        r['all_four_complete']=all(x['complete']for x in r['native_cases'].values())and len(r['native_cases'])==4
        r['all_four_diagnostic_screens_passed']=r['all_four_complete']and all(x['diagnostic_screen_passed']for x in r['native_cases'].values())
        r['sources_unchanged']=True
        r['status']='PASS_FOUR_INTRINSIC_RESET_DIAGNOSTIC_SCREENS_NOT_LAYOUT_OR_FULLPHY'if r['all_four_diagnostic_screens_passed']else'REJECTED_INTRINSIC_RESET_DIAGNOSTIC_PRESERVE_ALL_FAILURES'
    except BaseException as exc:r.update(status='FAIL_OR_ERROR',error=repr(exc));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
    assert r['all_four_diagnostic_screens_passed'],'Real intrinsic diagnostic gates remain open; all evidence retained'
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--native',action='store_true')
    args=parser.parse_args();assert args.native
    main()
