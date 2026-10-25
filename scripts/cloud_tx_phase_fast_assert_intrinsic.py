#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh244-device fast-assert diagnostic; original phase/safety gates unchanged."""
import argparse,hashlib,json,os,re,subprocess,time
from pathlib import Path
import cloud_tx_phase_async_preset_intrinsic as original
import cloud_tx_phase_zero_op_initialization as initialization
import tx_phase_fast_assert_diagnostic as bench
from cloud_tx_stream import read_streamed_wave
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-phase-fast-assert-intrinsic'
METHOD=ROOT/'scripts/tx-phase-fast-assert-intrinsic-methods.json'
OP_RUN=40097348918
OP_HEAD='c9867dbbde16fc8cd35a660c33d59679d04505ba'
OP_ASSET=672315252
OP_SHA='d9e470d8c156904c5fbf0f80e9bbb0421a62cfa5c2dfa4986f47af9ef1540a55'
PARTS_ASSET=672315390
PARTS_SHA='8fc991c1733c3ac203efdd29daa72e8263f411dd80b961c52016e22643812e9b'
def pins():
    d=json.loads(METHOD.read_text())
    for p,h in d['protected'].items():assert original.sha(ROOT/p)==h,p
    original.source_pins();initialization.pins()
    return d
def api(path):
    return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
def asset(a,h):
    raw=subprocess.check_output(['gh','api',f'repos/Melihakbulut221/nssoc/releases/assets/{a}','-H','Accept: application/octet-stream'])
    assert hashlib.sha256(raw).hexdigest()==h
    return raw
def validate_op(d,run):
    assert run['id']==OP_RUN and run['head_sha']==OP_HEAD and run['status']=='completed'and run['conclusion']=='success'
    assert int(d['run_id'])==OP_RUN and d['source_head']==OP_HEAD
    assert d['status']=='PASS_DEFAULT_OP_FAILURE_AND_UNIFORM_OFF_ZERO_OP_COMPARISON_NOT_TRANSIENT_ACCEPTANCE'
    assert d['sources_unchanged']and d['all_expected_outcomes']
    assert d['runtime_and_models']['engine_sha256']==original.ENGINE_SHA
    for k in ('DUT_transient_executed','original_native_transient_accepted','reset_hardware_qualified','fast_assert244_accepted','PLL_connected','full_PHY_accepted'):assert d[k]is False
    assert set(d['cases'])=={s+'-'+k for s in ('p','n')for k in ('default-off0','uniform-off1')}
    for name,c in d['cases'].items():
        off=name.endswith('uniform-off1')
        assert c['complete']and c['returncode']==0 and c['expected_initialization_outcome_reproduced']
        assert c['source_sha256']==initialization.bench.SOURCE_SHA and c['uniform_off']is off
        assert c['flags']==dict(actual_HBT_targets=106,uniform_OFF_value=int(off),all_native_flags_read_back=True)
        assert c['zero_source_op']['columns']==355 and c['zero_source_op']['rows']==1 and c['zero_source_op']['all_saved_electrical_and_thermal_states_zero']
        assert c['solver']['status']=='PASS_NATIVE_SOLVER_OPTION_READBACK'and c['solver']['profile']==bench.PROFILE
        if off:assert c['diagnostics']==[]
        else:
            assert any('temperature limiting function received NaN'in x for x in c['diagnostics'])
            assert any('Starting dynamic gmin stepping'in x for x in c['diagnostics'])
    return dict(run=OP_RUN,source_head=OP_HEAD,summary_asset=OP_ASSET,summary_sha256=OP_SHA,parts_asset=PARTS_ASSET,parts_sha256=PARTS_SHA,
      scope='Original241 zero-source initial-junction comparison only; fresh244 transient must independently pass every diagnostic.')
def prerequisite():
    raw=asset(OP_ASSET,OP_SHA);parts=asset(PARTS_ASSET,PARTS_SHA)
    r=validate_op(json.loads(raw),api('actions/runs/'+str(OP_RUN)))
    p=json.loads(parts)
    assert p['bytes']==10526997 and p['sha256']=='a347bf0b8ef0a3e95aba2201dd9b35730fc52b57fd143ce026fa18764e77bd19'
    assert len(p['parts'])==1 and p['verification']['all_parts_and_combined_bytes_verified']
    return r,raw,parts
def initialized_deck(original_deck,contract):
    assert original_deck.count('\nop\n')==1 and not re.search(r'(?im)^\s*alter\b',original_deck)
    block=initialization.flag_block(contract,True)
    result=original_deck.replace('\nop\n','\n'+block+'op\n')
    assert result.count(block)==1 and result.replace(block,'')==original_deck
    assert [r for r in result.splitlines()if r.startswith('alter ')]==['alter @'+n+'[off] = 1'for n in initialization.targets(contract)]
    assert not re.search(r'(?im)^\s*(?:\.ic\b|\.nodeset\b)|\buic\b',result)
    assert result.count('\nrun wave.raw\n')==1 and len([l for l in result.splitlines()if l.startswith('.tran ')])==1
    return result
def gate(row):
    checks=dict(native_returncode_zero=row.get('returncode')==0,
      no_native_diagnostics=row.get('diagnostics')==[],
      solver_readback=row.get('solver',{}).get('status')=='PASS_NATIVE_SOLVER_OPTION_READBACK',
      all106_flags=row.get('flags')==dict(actual_HBT_targets=106,uniform_OFF_value=1,all_native_flags_read_back=True),
      full_zero_OP=row.get('zero_source_op',{}).get('all_saved_electrical_and_thermal_states_zero')is True and row.get('zero_source_op',{}).get('columns')in(358,359),
      complete_original_capture=row.get('capture',{}).get('complete_unmodified_rows')is True,
      original_phase_and_safety=row.get('measurement',{}).get('diagnostic_screen_passed')is True,
      no_validation_errors=row.get('errors')==[])
    return dict(checks=checks,passed=all(checks.values()))
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    locked=pins();OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING_FAST_ASSERT244_INTRINSIC_DIAGNOSTIC',run_id=os.environ['GITHUB_RUN_ID'],source_head=os.environ['GITHUB_SHA'],
      scope='Fresh244-device fixture-driven4x34ns test, original125ps fixed phase/safety/solver limits. Three physical-rppd ARM fan-in candidate; uniform all106 OFF junction initialization qualified separately at original zero-source OP. No IC/UIC/internal ideal driver, no fitted phase, no old55RC. Complete new waveforms and all failures preserved.',
      native_cases={},protected=locked['protected'],original241_transient_accepted=False,layout_RC_included=False,
      reset_hardware_qualified=False,all31_clock_tree_accepted=False,PLL_connected=False,full_PHY_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        receipt,opraw,parts=prerequisite();r['zero_op_prerequisite']=receipt
        (OUT/'zero-op.summary.json').write_bytes(opraw);(OUT/'zero-op.parts.json').write_bytes(parts)
        raw,bound=original.observer();(OUT/'pll-observer.summary.json').write_bytes(raw);r['boundary']=bound
        original.OUT=OUT;engine,models,proof=original.restore();r['runtime_and_models']=proof
        text=(ROOT/bench.builder.OUTPUT).read_text();assert bench.digest(text)==bench.SOURCE_SHA;save()
        for sign in ('p','n'):
            for high in (True,False):
                label=sign+'-'+('initial-high'if high else'initial-low');case=OUT/label;case.mkdir()
                row=dict(complete=False,diagnostic_screen_passed=False,errors=[]);r['native_cases'][label]=row
                try:
                    source=case/'candidate.spice';source.write_text(text)
                    base,c=bench.prepare(text,bound,sign,high,source,models/'models',models/'r3_cmc.osdi')
                    deck=initialized_deck(base,c)
                    c.update(base_prepared_deck_sha256=c['deck_sha256'],deck_sha256=bench.digest(deck),
                      initialization=dict(uniform_all106_native_OFF=1,selected_differential_phase=False,IC_or_UIC=False,prerequisite=receipt))
                    (case/'bench.cir').write_text(deck);(case/'contract.json').write_text(json.dumps(c,indent=2)+'\n')
                    (case/'spinit').write_text('set num_threads=1\n')
                    row.update(deck_sha256=original.sha(case/'bench.cir'),source_sha256=original.sha(source),
                      contract_sha256=original.sha(case/'contract.json'),hbt_count=106,primitive_count=244,vector_count=len(c['vectors']))
                    assert row['vector_count']==358
                    env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN','LD_PRELOAD','PYTHONPATH','PYTHONHOME')}
                    env.update(SPICE_SCRIPTS=str(case),OMP_NUM_THREADS='1',GLIBC_TUNABLES='glibc.cpu.hwcaps=-AVX512F,-AVX512CD,-AVX512BW,-AVX512DQ,-AVX512ER,-AVX512PF,-AVX512VL,-RTM')
                    start=time.monotonic();save()
                    with (case/'native.log').open('w')as log:
                        process=subprocess.Popen([str(engine),'-n','-b','bench.cir'],cwd=case,env=env,stdout=log,stderr=subprocess.STDOUT)
                        row.update(native_pid=process.pid,started_epoch=time.time());save()
                        while process.poll()is None:
                            try:process.wait(timeout=30)
                            except subprocess.TimeoutExpired:
                                row.update(elapsed_s=time.monotonic()-start,raw_bytes=(case/'wave.raw').stat().st_size if(case/'wave.raw').exists()else 0)
                                save();print(json.dumps(dict(case=label,elapsed_s=row['elapsed_s'],raw_bytes=row['raw_bytes'])),flush=True)
                    row.update(returncode=process.returncode,elapsed_s=time.monotonic()-start);row.pop('native_pid',None)
                    log=(case/'native.log').read_text(errors='replace')
                    row.update(native_log_sha256=original.sha(case/'native.log'),native_log_tail=log[-16384:])
                    # Independent screens preserve useful raw diagnosis on any failure,
                    # but gate() requires every original acceptance condition.
                    for name,fn in [
                      ('solver',lambda:original.verify_solver_options(log,bench.PROFILE)),
                      ('diagnostics',lambda:original.native_diagnostics(log,bench.PROFILE)),
                      ('flags',lambda:initialization.flags(log,c,True)),
                      ('zero_source_op',lambda:original.zero_op(case/'op.raw',c['vectors']))]:
                        try:row[name]=fn()
                        except BaseException as exc:row['errors'].append(dict(stage=name,error=repr(exc)))
                    try:
                        t,values,capture=read_streamed_wave(case/'wave.raw',c['vectors'],bench.STOP,bench.STEP)
                        row['capture']=capture;row['measurement']=bench.review(t,values,c)
                    except BaseException as exc:row['errors'].append(dict(stage='complete_raw_and_original_observer',error=repr(exc)))
                    assert original.sha(case/'bench.cir')==row['deck_sha256']and original.sha(source)==bench.SOURCE_SHA
                    row['complete']=True
                except BaseException as exc:row['errors'].append(dict(stage='native_or_source',error=repr(exc)))
                row['acceptance_gate']=gate(row);row['diagnostic_screen_passed']=row['complete']and row['acceptance_gate']['passed']
                save();print(json.dumps(dict(case=label,complete=row['complete'],passed=row['diagnostic_screen_passed'],gates=row['acceptance_gate'])),flush=True)
        assert pins()==locked and original.sha(engine)==original.ENGINE_SHA
        for name,v in proof['model_manifest']['files'].items():
            p=models/name;assert p.is_file()and p.stat().st_size==v['bytes']and original.sha(p)==v['sha256']
        r['sources_and_models_unchanged']=True
        good=len(r['native_cases'])==4 and all(v['diagnostic_screen_passed']for v in r['native_cases'].values())
        r.update(all_four_diagnostic_screens_passed=good,
          status='PASS_FOUR_FAST_ASSERT244_INTRINSIC_DIAGNOSTICS_NOT_LAYOUT_OR_FULLPHY'if good else'REJECTED_FAST_ASSERT244_PRESERVE_COMPLETE_FAILURE_EVIDENCE')
    except BaseException as exc:r.update(status='FAIL_OR_ERROR',error=repr(exc));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):original.sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
    assert r['all_four_diagnostic_screens_passed'],'Fresh244 numerical/phase/safety gate rejected; complete evidence retained'
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--native',action='store_true');a=p.parse_args();assert a.native;main()
