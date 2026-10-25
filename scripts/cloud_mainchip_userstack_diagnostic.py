#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Observe the exact rejected DRT process; never admit it as normal continuation."""
import argparse,ast,copy,hashlib,importlib.util,json,os,re,subprocess,sys,tempfile,time,traceback
from pathlib import Path
import cloud_mainchip_route12_drt_continuation as frozen
import mainchip_latest_userstack_bridge as admission
from run_cloud_tx_layout_repair import sha
import mainchip_userstack_native_probe as native_probe
from mainchip_userstack_native_prerequisite import verify as fixture_prerequisite
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/mainchip-userstack-native-methods.json'
FROZEN='scripts/cloud_mainchip_route12_drt_continuation.py'
FROZEN_SHA='08b91df1a93d28c4acda1dbeae3b45e53af8393664ceaf71038808bdb0707eee'
OUT=ROOT/'cloud-mainchip-route12-userstack'
PROGRAM=ROOT/'cloud-mainchip-userstack-program/controller.py'
NO_PROGRESS="No observable native DRT progress after cross-runner restore"
PROBE=None
CURRENT={}
PROOFS=[]
COPY_PROGRAM="""import hashlib,json,pathlib,sys
def scan(root):
    result={}
    for p in sorted(root.rglob('*')):
        assert not p.is_symlink()
        if p.is_dir():continue
        assert p.is_file()
        h=hashlib.sha256()
        with p.open('rb')as stream:
            for block in iter(lambda:stream.read(1048576),b''):h.update(block)
        result[str(p.relative_to(root))]=h.hexdigest()
    return result
a=scan(pathlib.Path(sys.argv[1]));b=scan(pathlib.Path(sys.argv[2]))
assert a and a==b
print(json.dumps(dict(files=len(a),source_and_destination_equal=True,streaming_bytes=1048576)))
"""
def write(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n')
def methods():
    assert sha(ROOT/FROZEN)==FROZEN_SHA
    m=json.loads((ROOT/METHOD).read_text())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    assert m['normal_continuation_accepted']is False and m['route_segment_s']==600
    assert m['observer_envelope_s']==500 and m['sample_count']==20 and m['interval_s']==5
    return m
def adapted_source():
    text=(ROOT/FROZEN).read_text();assert hashlib.sha256(text.encode()).hexdigest()==FROZEN_SHA
    edits=[
      ('observer-import','import argparse,hashlib,json,os,re,shutil,subprocess,time\n',
       'import argparse,hashlib,json,os,re,shutil,subprocess,time\nimport cloud_mainchip_userstack_diagnostic as diag\n'),
      ('separate-output',"out=ROOT/('cloud-mainchip-route12-drt-'+args.stage);out.mkdir(exist_ok=False);BASE.mkdir(exist_ok=False);reports.OUT=out",
       "out=diag.OUT;out.mkdir(exist_ok=False);BASE.mkdir(exist_ok=False);reports.OUT=out"),
      ('exact-rejected-admission','            pin=initial_receipt()\n','            pin=diag.admission.rejected_receipt()\n'),
      ('exact-recovered-image-restore',"            old,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],out/'initial',old_names)\n",
       "            old,proof=diag.admission.restore_failed_capsule(pin,out/'initial',old_names)\n"),
      ('honest-historical-failure',"            assert old==pin['report']and old['sources_unchanged']and old['controller_sha256']in{LEGACY_CONTROLLER_SHA256,r['controller_sha256']}\n",
       "            assert old==pin['report']and old['controller_sha256']==diag.FROZEN_SHA\n            assert 'sources_unchanged'not in old and 'active_drt_cross_runner_progress_proven'not in old\n"),
      ('current-inputs-before-restore',"            ident=run('create-restored',command(name,True)).stdout.strip();assert re.fullmatch('[a-f0-9]{64}',ident)\n",
       "            diag.current_inputs(BASE,case,r,runtime,names,global_report,global_names,full,methods)\n            ident=run('create-restored',command(name,True)).stdout.strip();assert re.fullmatch('[a-f0-9]{64}',ident)\n"),
      ('streaming-copy-proof','            compare="import pathlib,hashlib,sys;scan=lambda d:{str(p.relative_to(d)):hashlib.sha256(p.read_bytes()).hexdigest()for p in d.rglob(\'*\')if p.is_file()};assert scan(pathlib.Path(sys.argv[1]))==scan(pathlib.Path(sys.argv[2]))"\n',
       '            compare=diag.COPY_PROGRAM\n'),
      ('begin-bound-observer',"            r['consumed_downloads_removed_after_verified_restore']=True;save()\n",
       "            r['consumed_downloads_removed_after_verified_restore']=True;save()\n            diag.start_probe(name,inventory,case,out,r)\n"),
      ('stop-observer-before-checkpoint',"        st=state(name);r['segment_elapsed_s']=time.monotonic()-start\n",
       "        diag.finish_probe(r,out)\n        st=state(name);r['segment_elapsed_s']=time.monotonic()-start\n"),
      ('checkpoint-if-observer-rejected',"        while time.monotonic()-start<budget and state(name)['Running']:\n",
       "        while time.monotonic()-start<budget and state(name)['Running']:\n            if diag.probe_rejected():\n                r['early_checkpoint_reason']='Read-only observer rejected; preserve process before diagnostic failure';save();break\n")]
    for label,old,new in edits:
        assert text.count(old)==1,(label,text.count(old))
        text=text.replace(old,new)
    before={n.name:ast.dump(n)for n in ast.parse((ROOT/FROZEN).read_text()).body if isinstance(n,ast.FunctionDef)}
    after={n.name:ast.dump(n)for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
    assert before.keys()==after.keys()
    assert [name for name in before if before[name]!=after[name]]==['main']
    return text,[label for label,old,new in edits]
def current_inputs(base,case,r,runtime,names,global_report,global_names,full,original_methods):
    global CURRENT
    assert not CURRENT
    pairs={}
    def add(label,path,want):
        assert label not in pairs and re.fullmatch('[0-9a-f]{64}',want)
        if any(row['path']==str(path)for row in pairs.values()):
            assert all(row['expected_sha256']==want for row in pairs.values()if row['path']==str(path));return
        pairs[label]=dict(path=str(path),expected_sha256=want,actual_sha256=sha(path))
        assert pairs[label]['actual_sha256']==want,label
    for n in names:add('runtime/'+n,base/'input'/n,runtime['outputs'][n])
    add('flow-config',base/'flow-config/trial-config.json',full['outputs']['trial-config.json'])
    for n in global_names:add('global/'+n,base/'global'/n,global_report['outputs'][n])
    for n,want in original_methods.items():add('original-method/'+n,ROOT/n,want)
    add('frozen-controller',ROOT/FROZEN,FROZEN_SHA)
    generated,_=adapted_source()
    add('generated-diagnostic',PROGRAM,hashlib.sha256(generated.encode()).hexdigest())
    add('exact-saved-native-tcl',case/'route.tcl',r['route_script']['sha256'])
    add('exact-saved-global-odb',case/'before-guide-read.odb',global_report['global_odb_sha256'])
    for n,want in admission.REQUIRED_INPUTS.items():add('authenticated-current/'+n,ROOT/n,want)
    CURRENT=pairs
    proof=admission.verify_current_inputs(lambda:copy.deepcopy(CURRENT),'before_restore')
    PROOFS.append(proof);write(OUT/'current-inputs-before.json',proof)
def recheck_inputs():
    assert CURRENT
    pairs=copy.deepcopy(CURRENT)
    for label,row in pairs.items():
        row['actual_sha256']=sha(Path(row['path']))
        assert row['actual_sha256']==row['expected_sha256'],label
    proof=admission.verify_current_inputs(lambda:pairs,'after_restore',PROOFS[0])
    PROOFS.append(proof);write(OUT/'current-inputs-after.json',proof)
    return proof
def start_probe(name,inventory,case,out,r):
    return native_probe.start_probe(name,inventory,case,out,r)
def probe_rejected():return native_probe.probe_rejected()
def finish_probe(r,out):return native_probe.finish_probe(r,out)
def validate_observations():return native_probe.validate_observations()
def verify_no_progress_site(error,function,program,report):
    assert type(error)is AssertionError and str(error)==NO_PROGRESS
    tree=ast.parse(program)
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='main')
    sites=[n for n in ast.walk(main)if isinstance(n,ast.Assert)
        and isinstance(n.msg,ast.Constant)and n.msg.value==NO_PROGRESS]
    assert len(sites)==1
    site=sites[0]
    assert ast.dump(site.test)==ast.dump(ast.parse('len(raw)>len(prefix)',mode='eval').body)
    assert function.__code__.co_filename==str(PROGRAM) and function.__code__.co_name=='main'
    assert function.__code__.co_firstlineno==main.lineno
    tb=error.__traceback__;assert tb is not None
    while tb.tb_next is not None:tb=tb.tb_next
    assert tb.tb_frame.f_code is function.__code__ and tb.tb_lineno==site.lineno,'Wrong assertion code or site'
    assert report['status']=='FAIL_OR_ERROR' and report['error']==repr(error)
    assert report['native_process_saved']is True and report['native_log']['single_entrypoint']is True
    witness='File "'+str(PROGRAM)+'", line '+str(site.lineno)+', in main'
    assert witness in report['traceback']
    assert report['traceback'].rstrip().endswith('AssertionError: '+NO_PROGRESS)
    return dict(code_object_bound=True,source_assertion_line=site.lineno,
        original_no_log_progress_rejection_reproduced=True,normal_continuation_accepted=False)
def run_inner_and_verify(inner,r,program):
    pending=None;after_errors=[]
    try:
        inner.main()
    except BaseException as error:
        pending=(error,error.__traceback__)
    finally:
        # Both cleanup and the after-proof are attempted even after an unexpected
        # restore/observer/native error. Neither may erase the original failure.
        try:finish_probe(r,OUT)
        except BaseException as error:after_errors.append(dict(stage='observer-finish',error=repr(error),traceback=traceback.format_exc()))
        if CURRENT:
            try:r['current_inputs_after']=recheck_inputs()
            except BaseException as error:after_errors.append(dict(stage='current-inputs-after',error=repr(error),traceback=traceback.format_exc()))
        else:r['current_inputs_after_unavailable']='The before-input proof was never established'
    if after_errors:r['after_errors']=after_errors
    if pending:
        error,tb=pending
        r['native_inner_error']=dict(error=repr(error),traceback=''.join(traceback.format_exception(type(error),error,tb)))
        if type(error)is not AssertionError or str(error)!=NO_PROGRESS:raise error.with_traceback(tb)
        report=json.loads((OUT/'result.json').read_text())
        r['expected_rejection']=verify_no_progress_site(error,inner.main,program,report)
    if after_errors:raise AssertionError('After-diagnostic verification failed; original error retained')
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
    a=argparse.ArgumentParser();a.add_argument('--controls',action='store_true');args=a.parse_args()
    m=methods();program,edits=adapted_source()
    if args.controls:
        # Native execution is never performed by controls.
        from check_mainchip_userstack_native_source import check
        result=check()
        print(json.dumps(result,indent=2));return
    assert m['native_process_restore_authorized']is True and m['native_attachment_authorized']is True,'Source-only until review and controls'
    qualification=fixture_prerequisite()
    assert os.environ.get('NSSOC_DRT_SECONDS')=='600'
    sys.modules['cloud_mainchip_userstack_diagnostic']=sys.modules[__name__]
    PROGRAM.parent.mkdir(exist_ok=False);PROGRAM.write_text(program)
    spec=importlib.util.spec_from_file_location('mainchip_observed_frozen_adapter',PROGRAM)
    inner=importlib.util.module_from_spec(spec);spec.loader.exec_module(inner)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],
        exact_adapter_edits=edits,generated_program_sha256=sha(PROGRAM),
        routing_complete=False,continuation_accepted=False,final_timing_complete=False,full_phy_accepted=False,
        historical_sources_unchanged_proven=False,scheduling_perturbed=True,harmless_fixture_prerequisite=qualification)
    try:
        sys.argv=[str(PROGRAM),'--stage','cross']
        run_inner_and_verify(inner,r,program)
        r['observations']=validate_observations()
        original=OUT/'result.json';saved=OUT/'inner-controller-result.json';original.rename(saved)
        r['inner_controller_result_sha256']=sha(saved)
        report=json.loads(saved.read_text())
        r['native_controller_outcome']=report['status']
        r['native_route_returned']=bool(report['route_complete'])
        r['new_saved_process_images']=report.get('checkpoint_images',{})
        methods()
        r['status']='PASS_EXACT_SAVED_USERSTACK_DIAGNOSIS_NOT_ROUTING_OR_CONTINUATION'
    except BaseException as error:
        r.update(status='FAIL_OBSERVED_PROCESS_DIAGNOSIS',error=repr(error),traceback=traceback.format_exc())
        raise
    finally:
        if OUT.exists():
            if(OUT/'result.json').exists()and not(OUT/'inner-controller-result.json').exists():
                (OUT/'result.json').rename(OUT/'inner-controller-result.json')
            r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
            write(OUT/'result.json',r)
            print(r['status'],flush=True)
if __name__=='__main__':main()
