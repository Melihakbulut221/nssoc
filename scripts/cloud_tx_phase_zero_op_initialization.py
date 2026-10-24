#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare original zero-source OP guesses; never execute a DUT transient."""
import argparse,hashlib,json,os,re,subprocess,tempfile,time
from pathlib import Path
import cloud_tx_phase_async_preset_intrinsic as native
import tx_phase_async_preset_diagnostic as bench
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-phase-zero-op-initialization'
METHOD=ROOT/'scripts/tx-phase-zero-op-initialization-methods.json'
def pins():
    d=json.loads(METHOD.read_text())
    for p,h in d['protected'].items():assert native.sha(ROOT/p)==h,p
    return d
def targets(contract):
    names=['q.'+n+'.qnpn13g2'for n in sorted(contract['hbt'])]
    assert len(names)==len(set(names))==106
    return names
def flag_block(contract,uniform_off):
    lines=[]
    for name in targets(contract):
        if uniform_off:lines.append('alter @'+name+'[off] = 1')
        lines+=['echo NSSOC_NATIVE_FLAG_BEGIN '+name,'show '+name+' : off','echo NSSOC_NATIVE_FLAG_END']
    return '\n'.join(lines)+'\n'
def op_only(original,contract,uniform_off):
    assert type(uniform_off)is bool
    rows=original.splitlines(keepends=True);tran=[r for r in rows if r.startswith('.tran ')]
    assert len(tran)==1 and original.count('run wave.raw\n')==1 and original.count('\nop\n')==1
    assert not any(r.startswith('alter ')for r in rows)
    body=original.replace(tran[0],'').replace('run wave.raw\n','')
    body=body.replace('\nop\n','\n'+flag_block(contract,uniform_off)+'op\n')
    assert not re.search(r'(?im)^\s*(?:\.tran\b|run\b|resume\b|tran\b|\.ic\b|\.nodeset\b)|\buic\b',body)
    expected=['alter @'+n+'[off] = 1'for n in targets(contract)]if uniform_off else[]
    assert [r for r in body.splitlines()if r.startswith('alter ')]==expected
    return body
def flags(log,contract,uniform_off):
    rows=re.findall(r'(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$',log)
    assert [n for n,b in rows]==targets(contract),'Missing, duplicate or reordered native HBT flag'
    value='1'if uniform_off else'0'
    assert all(re.findall(r'(?m)^\s*off\s+([01])\s*$',body)==[value]for n,body in rows)
    return dict(actual_HBT_targets=106,uniform_OFF_value=int(value),all_native_flags_read_back=True)
def controls():
    locked=pins();_,bound=native.observer()
    text=(ROOT/bench.builder.OUTPUT).read_text()
    original,c=bench.prepare(text,bound,'p',True,'candidate.spice','/models','/r3.osdi')
    wrong=[]
    def fails(name,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError):wrong.append(name)
        else:raise AssertionError('Accepted '+name)
    for value in (False,True):
        body=op_only(original,c,value)
        assert body.count('\nop\n')==1 and body.count('write op.raw all')==1
        assert sum(r.startswith('alter ')for r in body.splitlines())==(106 if value else 0)
        log=''.join('NSSOC_NATIVE_FLAG_BEGIN '+n+'\n  off '+str(int(value))+'\nNSSOC_NATIVE_FLAG_END\n'for n in targets(c))
        assert flags(log,c,value)['all_native_flags_read_back']
        for label,bad in [('missing',log.split('NSSOC_NATIVE_FLAG_END\n',1)[1]),
          ('wrong_value',log.replace('off '+str(int(value)),'off '+str(int(not value)),1)),
          ('wrong_target',log.replace(targets(c)[0],'q.missing',1)),
          ('duplicate',log+log.split('NSSOC_NATIVE_FLAG_END\n',1)[0]+'NSSOC_NATIVE_FLAG_END\n')]:
            fails(str(value)+'_'+label,lambda:flags(bad,c,value))
    fails('added_transient',lambda:op_only(original.replace('op\n','tran .3p 1n\nop\n',1),c,True))
    fails('added_IC',lambda:op_only(original.replace('.temp 27','.ic V(mp)=1\n.temp 27'),c,True))
    fails('preexisting_parameter_alter',lambda:op_only(original.replace('\nop\n','\nalter @q.device[nx] = 2\nop\n'),c,True))
    assert len(wrong)==11 and pins()==locked
    print(json.dumps(dict(status='PASS_UNIFORM106_OFF_OP_ONLY_SOURCE_CONTROLS_NO_NATIVE',negative_controls=wrong,
      original_hbt=106,default_and_uniform_flag_coverage=True,native_execution=False,DUT_transient_executed=False,full_PHY_accepted=False),indent=2))
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    locked=pins();oldpins=native.source_pins();OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING_ZERO_OP_INITIALIZATION_COMPARISON',run_id=os.environ['GITHUB_RUN_ID'],source_head=os.environ['GITHUB_SHA'],
      scope='Original immutable241-device source, same PDK/runtime, zero external sources; compare default OFF=0 and uniform all106HBT OFF=1 initial junction guesses. No .tran/run/IC/UIC, no selected differential phase, no new fast-assert circuit. Passing OP does not erase original transient diagnostics.',
      cases={},DUT_transient_executed=False,original_native_transient_accepted=False,reset_hardware_qualified=False,
      fast_assert244_accepted=False,PLL_connected=False,full_PHY_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        _,bound=native.observer();text=(ROOT/bench.builder.OUTPUT).read_text();assert bench.digest(text)==bench.SOURCE_SHA
        native.OUT=OUT;engine,models,proof=native.restore();r['runtime_and_models']=proof;save()
        for sign in ('p','n'):
            for off in (False,True):
                label=sign+'-'+('uniform-off1'if off else'default-off0');case=OUT/label;case.mkdir()
                source=case/'candidate.spice';source.write_text(text)
                original,c=bench.prepare(text,bound,sign,True,source,models/'models',models/'r3_cmc.osdi')
                body=op_only(original,c,off);(case/'bench.cir').write_text(body);(case/'contract.json').write_text(json.dumps(c,indent=2)+'\n')
                (case/'spinit').write_text('set num_threads=1\n')
                row=dict(variant=sign,uniform_off=off,source_sha256=native.sha(source),deck_sha256=native.sha(case/'bench.cir'),complete=False)
                r['cases'][label]=row;save()
                try:
                    env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN','LD_PRELOAD','PYTHONPATH','PYTHONHOME')}
                    env.update(SPICE_SCRIPTS=str(case),OMP_NUM_THREADS='1',GLIBC_TUNABLES='glibc.cpu.hwcaps=-AVX512F,-AVX512CD,-AVX512BW,-AVX512DQ,-AVX512ER,-AVX512PF,-AVX512VL,-RTM')
                    start=time.monotonic()
                    with (case/'native.log').open('w')as log:
                        process=subprocess.run([str(engine),'-n','-b','bench.cir'],cwd=case,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
                    log=(case/'native.log').read_text();row.update(returncode=process.returncode,elapsed_s=time.monotonic()-start,log_sha256=native.sha(case/'native.log'),log_tail=log[-16384:])
                    assert process.returncode==0
                    row['solver']=native.verify_solver_options(log,bench.PROFILE)
                    row['flags']=flags(log,c,off)
                    row['diagnostics']=native.native_diagnostics(log,bench.PROFILE)
                    row['zero_source_op']=native.zero_op(case/'op.raw',c['vectors'])
                    assert not (case/'wave.raw').exists()
                    if off:assert not row['diagnostics'],'Uniform OFF did not resolve original numerical OP issue'
                    else:
                        assert any('temperature limiting function received NaN'in l for l in row['diagnostics'])
                        assert any('Starting dynamic gmin stepping'in l for l in row['diagnostics'])
                    row.update(complete=True,expected_initialization_outcome_reproduced=True)
                except BaseException as exc:row.update(error=repr(exc),expected_initialization_outcome_reproduced=False)
                assert native.sha(source)==bench.SOURCE_SHA and native.sha(case/'bench.cir')==row['deck_sha256']
                save();print(json.dumps(dict(case=label,complete=row['complete'],error=row.get('error'))),flush=True)
        assert pins()==locked and native.source_pins()==oldpins and native.sha(engine)==native.ENGINE_SHA
        r['sources_unchanged']=True
        good=len(r['cases'])==4 and all(v['complete']for v in r['cases'].values())
        r.update(status='PASS_DEFAULT_OP_FAILURE_AND_UNIFORM_OFF_ZERO_OP_COMPARISON_NOT_TRANSIENT_ACCEPTANCE'if good else'REJECTED_ZERO_OP_COMPARISON',all_expected_outcomes=good)
    except BaseException as exc:r.update(status='FAIL_OR_ERROR',error=repr(exc));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):native.sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
    assert r['all_expected_outcomes']
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--native-op',action='store_true');a=p.parse_args()
    assert a.controls!=a.native_op
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    controls()if a.controls else main()
