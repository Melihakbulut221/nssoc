# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure input/recipe/receipt and live-snapshot controls; no SoC execution."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import run_cloud_core_ack_qualification as q  # noqa: E402


@pytest.fixture(scope='module')
def c10(tmp_path_factory):
    lock=q.alu.validate_lock(json.loads((ROOT/q.alu.LOCK).read_text()))
    bundle=tmp_path_factory.mktemp('ack-c10')/'inputs'
    q.alu.restore(ROOT/lock['archive']['path'],bundle,lock)
    return bundle,lock


def test_only_ack_source_changes_and_all_original_81_inputs_retained(tmp_path,c10):
    bundle,lock=c10
    pins=q.protocol.source_contract();assert len(pins)==81
    for name,expected in pins.items():assert q.pin(bundle/'repo'/name)==expected
    prepared=tmp_path/'prepared';q.ack.prepare(bundle/'repo'/q.PIPE,prepared)
    assert q.ack.verify_prepared(prepared)['upstream_ack_latency_added_cycles']==1
    assert q.common.sha(prepared/'candidate.v')==q.CANDIDATE_SHA
    assert q.common.sha(bundle/lock['original_alu'])==q.alu.prefix.ORIGINAL_SHA
    assert not q.ack.verify_prepared(prepared)['candidate_adopted']


def test_exact_recipe_reversible_path_relocation_and_one_req_pipe(tmp_path,c10):
    bundle,lock=c10
    output=tmp_path/'synthesis';output.mkdir()
    origin=Path(lock['original_synthesis']).relative_to(lock['original_repo'])
    shutil.copytree(bundle/'repo'/origin/'boot-rom',output/'boot-rom')
    pipe=tmp_path/'candidate.v';pipe.write_bytes(q.ack.transform((bundle/'repo'/q.PIPE).read_bytes()))
    template=(bundle/'recipe/c10.ys').read_text()
    recipe=q.synthesis_recipe(template,bundle,output,pipe,lock)
    inputs=q.alu.validate_recipe_inputs(recipe,bundle,output,pipe)
    assert inputs[str(pipe)]['sha256']==q.CANDIDATE_SHA
    assert inputs[str(bundle/lock['original_alu'])]==lock['files'][lock['original_alu']]
    restored=recipe.replace(str(pipe),lock['original_repo']+'/'+q.PIPE)
    restored=restored.replace(str(output),lock['original_synthesis'])
    restored=restored.replace(str(bundle/'repo'),lock['original_repo']).replace(str(bundle/'pdk'),lock['original_pdk'])
    assert restored==template
    assert recipe.count(str(pipe))==1 and len(inputs)>70


@pytest.mark.parametrize('before,after',[
    ('CORE_REQ_REG 1','CORE_REQ_REG 0'),('CORE_WB_STAGE 1','CORE_WB_STAGE 0'),
    ('SOC_ETH_MBIST','NO_ETH_MBIST'),(' -D 20\n',' -D 20000\n'),
    ('soc_req_pipe.v','wrong_pipe.v'),('ibex_alu.v','different_alu.v')])
def test_any_original_synthesis_instruction_change_is_rejected(tmp_path,c10,before,after):
    bundle,lock=c10
    original=(bundle/'recipe/c10.ys').read_text();assert before in original
    with pytest.raises(ValueError,match='instructions changed'):
        q.synthesis_recipe(original.replace(before,after),bundle,tmp_path,tmp_path/'p.v',lock)


def test_original_checkout_prefix_in_destination_is_not_replaced_twice(c10):
    bundle,lock=c10
    nested=Path(lock['original_repo'])/'hw/soc/out/ack-only'
    recipe=q.synthesis_recipe((bundle/'recipe/c10.ys').read_text(),nested/'inputs',nested/'out',nested/'candidate.v',lock)
    assert recipe.count(str(nested/'candidate.v'))==1
    assert str(nested/'inputs/repo/hw/soc/rtl/soc_top.v') in recipe


def protocol_fixture(tmp_path,monkeypatch):
    """Synthetic receipt fixture for parser rejection, never native evidence."""
    root=tmp_path/'fixture';prepared=root/'core-ack-prepared';result=root/'core-ack-result'
    (prepared/'ack').mkdir(parents=True);result.mkdir()
    original=(ROOT/q.PIPE).read_bytes()
    (prepared/'ack/candidate.v').write_bytes(q.ack.transform(original))
    (prepared/'preparation.json').write_text('{}\n')
    monkeypatch.setattr(q.protocol,'verify_prepared',lambda _:dict(source_methods={}))
    row=dict(github_source_commit='a'*40,status='PASS_FINITE_ACTUAL_CORE_PROTOCOL_CASES_ONLY',
        preparation=q.pin(prepared/'preparation.json'),methods={},compilations={},cases={},
        actual_core_protocol_proved=False,whole_soc_verified=False,sequential_equivalence_proved=False,
        candidate_adopted=False,timing_accepted=False)
    for name in ('original','candidate',*q.protocol.REJECTIONS):
        out=result/name;out.mkdir();(out/'compile.log').write_text('')
        row['compilations'][name]=dict(execution=dict(returncode=0),log=q.pin(out/'compile.log'))
        for reset in (range(4) if name=='candidate' else (0,)):
            key=name+'-reset'+str(reset);out=result/key;out.mkdir()
            case=dict(variant=name,reset_phase=reset,passed=True)
            if name in q.protocol.REJECTIONS:
                (out/'native.log').write_text('FATAL: '+q.protocol.REJECTIONS[name]+'\n')
                code=1
            else:
                counts=dict(reset_phase=reset,cycles=900,accepted=20,delivered=20,cancelled=0,
                    responses=20,cancelled_responses=0,held=5,stalls=9,pmp_first=2,pmp_second=2,
                    split_second=8,bus_errors=4,stopped_clock=6,traps=8,irq=1)
                (out/'native.log').write_text('PASS_ACTUAL_CORE_DIRECTED_PROTOCOL '+' '.join(f'{n}={v}' for n,v in counts.items())+'\n')
                words=[0]*2048;words[(0x3fe0-0x2000)//4]=8;words[(0x3fe4-0x2000)//4]=1
                words[(0x3ff0-0x2000)//4]=0x600dc0de
                (out/'signature.hex').write_text('\n'.join(f'{x:08x}' for x in words)+'\n')
                signature=q.protocol.read_signature(out/'signature.hex');code=0
                case.update(counters=counts,signature_sha256=signature)
                row['matching_architectural_signature']=signature
            case['execution']=dict(returncode=code,log=q.pin(out/'native.log'));row['cases'][key]=case
    producer=dict(source_commit='a'*40,signature_sha256=row['matching_architectural_signature'])
    (result/'firmware.bin').write_bytes(bytes.fromhex('13000000'))
    header=bytearray(52);header[:6]=b'\x7fELF\x01\x01'
    struct.pack_into('<H',header,18,243);struct.pack_into('<I',header,24,0x80)
    (result/'firmware.elf').write_bytes(header)
    (result/'firmware.hex').write_text(q.protocol.firmware_hex(result/'firmware.bin',result/'firmware.elf'))
    producer['firmware']=q.pin(result/'firmware.bin')
    (result/'firmware-toolchain-probe').mkdir()
    raw=bytes.fromhex('73250030731005307300501073002030')
    (result/'firmware-toolchain-probe/probe.bin').write_bytes(raw)
    row['firmware_toolchain_probe']=q.protocol.verify_firmware_probe(raw)
    row['firmware_toolchain_probe'].update(compile=dict(returncode=0),objcopy=dict(returncode=0))
    def update():
        row['outputs']={str(p.relative_to(result)):q.pin(p) for p in result.rglob('*')
                        if p.is_file() and p!=result/'result.json'}
        q.common.save(result/'result.json',row);producer['result']=q.pin(result/'result.json')
    update()
    return root,result,row,producer,update


def test_all_nine_raw_case_receipts_and_six_compile_logs_required(tmp_path,monkeypatch):
    root,_,row,producer,_=protocol_fixture(tmp_path,monkeypatch)
    assert q.verify_protocol_tree(root,producer)==row


@pytest.mark.parametrize('mutation',['no_compile_gate','width','counter','signature','negative','missing_case','acceptance','candidate','firmware','opcode'])
def test_repinning_semantically_wrong_protocol_evidence_does_not_pass(tmp_path,monkeypatch,mutation):
    root,result,row,producer,update=protocol_fixture(tmp_path,monkeypatch)
    if mutation=='no_compile_gate':row.pop('compilations')
    elif mutation=='width':
        p=result/'candidate/compile.log'
        p.write_text('tb.v:43: warning: Port 56 (rf_ecc_err_o) of ibex_top expects 3 bits, got 1.\n')
        row['compilations']['candidate']['log']=q.pin(p)
    elif mutation=='counter':row['cases']['candidate-reset0']['counters']['traps']=7
    elif mutation=='signature':row['cases']['candidate-reset0']['signature_sha256']='0'*64
    elif mutation=='negative':row['cases']['corrupt_payload-reset0']['execution']['returncode']=0
    elif mutation=='missing_case':row['cases'].pop('candidate-reset2')
    elif mutation=='acceptance':row['candidate_adopted']=True
    elif mutation=='candidate':(root/'core-ack-prepared/ack/candidate.v').write_text('changed')
    elif mutation=='firmware':(result/'firmware.hex').write_text('00000013\n')
    else:(result/'firmware-toolchain-probe/probe.bin').write_bytes(b'\0'*16)
    update()
    with pytest.raises(ValueError):q.verify_protocol_tree(root,producer)


def test_missing_corrected_native_result_blocks_before_any_runtime(tmp_path,monkeypatch):
    monkeypatch.setenv('GITHUB_ACTIONS','true');monkeypatch.setenv('GITHUB_SHA','a'*40)
    monkeypatch.setattr(q,'PROTOCOL_PRODUCER',None)
    with pytest.raises(ValueError,match='producer pin pending'):q.initialize(tmp_path/'out',tmp_path/'work')
    assert not (tmp_path/'out').exists() and not (tmp_path/'work').exists()


@pytest.mark.parametrize('entry',['synthesis','boot'])
def test_no_native_work_outside_reviewed_cloud(tmp_path,monkeypatch,entry):
    monkeypatch.delenv('GITHUB_ACTIONS',raising=False)
    with pytest.raises(ValueError,match='cloud-only'):
        if entry=='synthesis':q.synthesize_and_map(tmp_path/'out',tmp_path/'work')
        else:q.boot_prepare(tmp_path/'out',tmp_path/'work','candidate','independent',tmp_path/'map')
    assert not (tmp_path/'out').exists()


def test_nested_result_receipts_are_in_inventory_and_links_are_rejected(tmp_path):
    (tmp_path/'nested').mkdir();(tmp_path/'nested/result.json').write_text('{}')
    (tmp_path/'result.json').write_text('{}')
    assert set(q.own_inventory(tmp_path))=={'nested/result.json'}
    (tmp_path/'linked').symlink_to(tmp_path/'nested/result.json')
    with pytest.raises(ValueError,match='Linked'):q.own_inventory(tmp_path)


def test_compact_snapshot_is_immutable_and_does_not_signal_or_accept(tmp_path,monkeypatch):
    live=tmp_path/'live';live.mkdir();(live/'progress').mkdir()
    (live/'result.json').write_text('{"status":"RUNNING"}\n')
    (live/'boot.log').write_text('first-prefix\n')
    (live/'progress/cycle-0010000.json').write_text('{"cycle":10000}\n')
    monkeypatch.setattr(q,'observation',lambda _:dict(terminal=False,status='RUNNING'))
    snapshot=tmp_path/'snapshot';q.capture(live,snapshot)
    before=copy.deepcopy(q.own_inventory(snapshot))
    (live/'boot.log').write_text('first-prefix\nnewer-native-progress\n')
    assert q.own_inventory(snapshot)==before
    receipt=json.loads((snapshot/'snapshot.json').read_text())
    assert receipt['worker_was_not_signaled'] and not receipt['candidate_adopted']
    assert receipt['status']=='IMMUTABLE_PARTIAL_OBSERVATION_NOT_ACCEPTANCE'
    assert receipt['files']['boot.log']['sha256']==hashlib.sha256(b'first-prefix\n').hexdigest()
    with pytest.raises(ValueError):q.capture(live,live/'nested')


def test_observer_never_turns_running_into_native_timeout(tmp_path,monkeypatch):
    monkeypatch.setattr(q,'observation',lambda _:dict(terminal=False,status='RUNNING'))
    out=tmp_path/'github-output'
    row=q.wait(tmp_path,seconds=0,github_output=out)
    assert row['terminal'] is False and row['worker_was_not_signaled'] is True
    assert out.read_text()=='terminal=false\n'
    with pytest.raises(ValueError):q.wait(tmp_path,seconds=float('nan'))


def test_detached_tiny_receipt_worker_has_real_pid_birth_and_sanitized_env(tmp_path,monkeypatch):
    # This launches only a tiny Python receipt control, never a core or EDA tool.
    monkeypatch.setenv('GH_TOKEN','test-token-must-not-reach-child')
    command=[sys.executable,'-c',
        'import os,time; assert "GH_TOKEN" not in os.environ; time.sleep(.1); print("TINY_RECEIPT_CONTROL")']
    child=q.launch_worker(tmp_path,command)
    launch=json.loads((tmp_path/'launch.json').read_text())
    assert launch['pid']==child.pid and launch['identity']['pid']==child.pid
    assert launch['identity']['command']==command and launch['identity']['birth'].isdigit()
    assert child.wait(timeout=5)==0
    assert (tmp_path/'worker.log').read_text()=='TINY_RECEIPT_CONTROL\n'


def test_archived_protocol_keeps_original_provenance_and_checks_available_live_identity():
    captured=q.protocol_provenance()
    q.check_live_provenance(captured['run'],captured['artifact'],captured)
    expired=copy.deepcopy(captured['artifact']);expired['expired']=True
    q.check_live_provenance(None,expired,captured)
    q.check_live_provenance(None,None,captured)
    wrong=copy.deepcopy(expired);wrong['digest']='sha256:'+'0'*64
    with pytest.raises(ValueError,match='identity differs'):q.check_live_provenance(None,wrong,captured)
    wrong=copy.deepcopy(captured['run']);wrong['conclusion']='failure'
    with pytest.raises(ValueError):q.check_live_provenance(wrong,None,captured)
    assert q.PROTOCOL_PRODUCER['url'].endswith('closure-core-ack-full-width-37012329552-20261002.zip')


@pytest.mark.parametrize('mode',['pass','wrong_command','failed_process','missing_mbist'])
def test_actual_boot_run_control_flow_with_stub_process_only(tmp_path,monkeypatch,mode):
    # Exercise the real preflight ordering, stream capture, post-pins and final
    # failure handling. The child is a Python test double; no SoC is simulated.
    monkeypatch.setenv('GITHUB_ACTIONS','true');monkeypatch.setenv('GITHUB_SHA','a'*40)
    monkeypatch.setattr(q,'verify_outputs',lambda *_:None)
    output=tmp_path/'out';output.mkdir();(output/'firmware').mkdir()
    source=tmp_path/'source.v';source.write_text('synthetic source fixture')
    executable=tmp_path/'simulation.vvp';executable.write_text('synthetic compiled fixture')
    runtime=tmp_path/'vvp';runtime.write_text('synthetic runtime identity fixture')
    flash=output/'firmware/flash0.hex';flash.write_text('fixture')
    command=[str(runtime),'-i',str(executable),'+flash0='+str(flash)]
    if mode=='wrong_command':command[1]='--unreviewed-option'
    row=dict(status='COMPILED_READY_FOR_ACK_FOUR_STATE_BOOT',github_source_commit='a'*40,
        actual_core_prerequisite=dict(producer=q.PROTOCOL_PRODUCER),cycle_bound=q.qualified.CYCLES,
        sources={str(source):q.pin(source)},compiled_simulation_path=str(executable),
        compiled_simulation=q.pin(executable),runtime=dict(tools=dict(vvp=q.pin(runtime))),
        boot_command=command,**{n:False for n in q.GATES})
    q.common.save(output/'result.json',row)
    launched=[]
    class StubChild:
        stdout=['LOGICROM_GL progress cycles=10000\n',
                *([] if mode=='missing_mbist' else ['QUALIFICATION_MBIST PASS cycles=983048\n']),
                'LOGICROM_GL PASS checks=28\n']
        def wait(self):return 1 if mode=='failed_process' else 0
    def popen(arguments,**kwargs):
        launched.append(arguments)
        assert arguments==command and 'GH_TOKEN' not in kwargs['env']
        return StubChild()
    monkeypatch.setattr(q.subprocess,'Popen',popen)
    if mode=='pass':q.boot_run(output)
    else:
        with pytest.raises(ValueError):q.boot_run(output)
    final=json.loads((output/'result.json').read_text())
    assert final['status']==(q.BOOT_STATUS if mode=='pass' else 'FAILED_PRESERVED')
    assert all(final[n] is False for n in q.GATES)
    assert len(launched)==(0 if mode=='wrong_command' else 1)
    if launched:
        progress=json.loads((output/'progress/cycle-0010000.json').read_text())
        assert progress['cycle']==10000 and progress['compiled_simulation']==q.pin(executable)
        assert final['boot_execution']['returncode']==(1 if mode=='failed_process' else 0)
