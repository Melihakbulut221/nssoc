#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One 7200 s same-process route attempt; every original progress gate remains."""
import argparse,ast,copy,hashlib,importlib.util,json,os,re,subprocess,sys,time,traceback
from pathlib import Path
import cloud_mainchip_route12_drt_continuation as frozen
import mainchip_userstack7200_admission as admission
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/mainchip-userstack7200-methods.json'
FROZEN='scripts/cloud_mainchip_route12_drt_continuation.py'
FROZEN_SHA='08b91df1a93d28c4acda1dbeae3b45e53af8393664ceaf71038808bdb0707eee'
GROUP='mainchip-route12-userstack7200'
OUT=ROOT/('cloud-'+GROUP)
PROGRAM=ROOT/'cloud-mainchip-userstack7200-program/controller.py'
NO_PROGRESS='No observable native DRT progress after cross-runner restore'
CURRENT={}
PROOFS=[]
def write(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n')
def methods():
    assert sha(ROOT/FROZEN)==FROZEN_SHA
    return admission.methods()
def adapted_source():
    text=(ROOT/FROZEN).read_text();assert hashlib.sha256(text.encode()).hexdigest()==FROZEN_SHA
    edits=[
      ('new-controller-import','import argparse,hashlib,json,os,re,shutil,subprocess,time\n',
       'import argparse,hashlib,json,os,re,shutil,subprocess,time\nimport cloud_mainchip_userstack7200_continue as diag\n'),
      ('separate-output',"out=ROOT/('cloud-mainchip-route12-drt-'+args.stage);out.mkdir(exist_ok=False);BASE.mkdir(exist_ok=False);reports.OUT=out",
       "out=diag.OUT;out.mkdir(exist_ok=False);BASE.mkdir(exist_ok=False);reports.OUT=out"),
      ('exact-diagnostic-admission','            pin=initial_receipt()\n','            pin=diag.admission.rejected_receipt()\n'),
      ('exact-capsule-restore',"            old,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],out/'initial',old_names)\n",
       "            old,proof=diag.admission.restore_failed_capsule(pin,out/'initial',old_names)\n"),
      ('honest-historical-rejection',"            assert old==pin['report']and old['sources_unchanged']and old['controller_sha256']in{LEGACY_CONTROLLER_SHA256,r['controller_sha256']}\n",
       "            assert old==pin['report']and old['controller_sha256']==diag.admission.CONTROLLER\n            assert 'sources_unchanged'not in old and 'active_drt_cross_runner_progress_proven'not in old\n"),
      ('current-inputs-before-restore',"            ident=run('create-restored',command(name,True)).stdout.strip();assert re.fullmatch('[a-f0-9]{64}',ident)\n",
       "            diag.current_inputs(BASE,case,r,runtime,names,global_report,global_names,full,methods)\n            ident=run('create-restored',command(name,True)).stdout.strip();assert re.fullmatch('[a-f0-9]{64}',ident)\n"),
      ('streaming-copy-proof','            compare="import pathlib,hashlib,sys;scan=lambda d:{str(p.relative_to(d)):hashlib.sha256(p.read_bytes()).hexdigest()for p in d.rglob(\'*\')if p.is_file()};assert scan(pathlib.Path(sys.argv[1]))==scan(pathlib.Path(sys.argv[2]))"\n',
       '            compare=diag.COPY_PROGRAM\n'),
      ('full-runtime-before-unobserved-budget',"            r['consumed_downloads_removed_after_verified_restore']=True;save()\n",
       "            r['consumed_downloads_removed_after_verified_restore']=True;save()\n            r['unobserved_runtime_binding']=diag.verify_runtime(name,inventory,case,out,r)\n            save()\n"),
      ('truthful-new-result-group',"group='mainchip-route12-drt-'+args.stage,","group=diag.GROUP,")]
    for label,old,new in edits:
        assert text.count(old)==1,(label,text.count(old));text=text.replace(old,new)
    before={n.name:ast.dump(n)for n in ast.parse((ROOT/FROZEN).read_text()).body if isinstance(n,ast.FunctionDef)}
    after={n.name:ast.dump(n)for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
    assert before.keys()==after.keys()and [n for n in before if before[n]!=after[n]]==['main']
    assert text.count("assert 600<=budget<=7200")==1
    assert text.count("assert len(raw)>len(prefix),'No observable native DRT progress after cross-runner restore'")==1
    return text,[label for label,old,new in edits]

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

def verify_runtime(name,inventory,case,out,r):
    rows=json.loads(subprocess.check_output(['docker','inspect',name],timeout=15));assert len(rows)==1
    c=rows[0];assert c['State']['Running']is True and c['Image']==r['image_id']
    assert c['Name']=='/nssoc-active-drt-cross' and c['HostConfig']['CpusetCpus']==r['cpuset']
    expect=dict(id=c['Id'],image=c['Image'],name=c['Name'],pid=c['State']['Pid'],started_at=c['State']['StartedAt'],
        cpuset=c['HostConfig']['CpusetCpus'],mode='EXACT_NO_GDB_7200_RUNTIME_BINDING',route_tcl=str(case/'route.tcl'))
    target=out/'no-gdb-runtime-expect.json';write(target,expect)
    p=subprocess.run(['sudo','--',sys.executable,str(ROOT/'scripts/mainchip_userstack7200_runtime.py'),
        '--expect',str(target),'--inventory',str(frozen.BASE/'input/runtime-inventory.json')],
        capture_output=True,text=True,timeout=420)
    (out/'no-gdb-runtime.stdout.log').write_text(p.stdout);(out/'no-gdb-runtime.stderr.log').write_text(p.stderr)
    if p.returncode:
        print(p.stdout[-8192:]+p.stderr[-8192:],flush=True)
        raise RuntimeError('Read-only runtime binding failed before route budget')
    result=json.loads(p.stdout);assert result['status']=='PASS_EXACT_RUNTIME_CLOSURE_WITHOUT_GDB'
    assert result['runtime_closure']==admission.capsule()['runtime_closure']
    assert result['gdb_attached']is False and result['target_detached']is True
    write(out/'no-gdb-runtime-result.json',result)
    return result
def qualify_success(report,run,head):
    assert report is not None and report['sources_unchanged']is True
    assert report['active_drt_cross_runner_progress_proven']is True
    assert report['continuation']['group']==GROUP and report['continuation']['run']==run
    assert report['continuation']['source_head']==head
    assert report['retained_timing_contract']['clock_periods_ns']==[20,4,8,8]
    assert report['retained_timing_contract']['derating_percent']==5
    assert report['unobserved_runtime_binding']['target_detached']is True
    assert report['unobserved_runtime_binding']['gdb_attached']is False
    assert report['unobserved_runtime_binding']['runtime_closure']==admission.capsule()['runtime_closure']
    if report['route_complete']:
        assert report['status']=='COMPLETE_NATIVE_DRT_REQUIRES_ALL_POSTROUTE_PHYSICAL_RC_STA_GATES'
        return dict(continuation_accepted=True,routing_complete=True,
            status='COMPLETE_NATIVE_DRT_REQUIRES_ORIGINAL_POSTROUTE_GATES')
    assert report['status']=='SAVED_CROSS_RUNNER_ACTIVE_DRT_PROGRESS_REQUIRES_FURTHER_CONTINUATION_AND_SIGNOFF'
    assert report['native_process_saved']is True and report['checkpoint_images']
    return dict(continuation_accepted=True,routing_complete=False,
        status='SAVED_SAME_PROCESS_ORIGINAL_LOG_PROGRESS_GATES_PASSED_NOT_ROUTE_COMPLETE')
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');a=p.parse_args()
    m=methods();program,edits=adapted_source()
    if a.controls:
        from check_mainchip_userstack7200_source import check
        print(json.dumps(check(),indent=2));return
    assert m['native_process_restore_authorized']is True,'Source-only until peer and root review plus controls'
    assert os.environ.get('NSSOC_DRT_SECONDS')=='7200'
    sys.modules['cloud_mainchip_userstack7200_continue']=sys.modules[__name__]
    PROGRAM.parent.mkdir(exist_ok=False);PROGRAM.write_text(program)
    spec=importlib.util.spec_from_file_location('mainchip_userstack7200_frozen_adapter',PROGRAM)
    inner=importlib.util.module_from_spec(spec);spec.loader.exec_module(inner)
    r=dict(status='RUNNING_SAME_PROCESS_ATTEMPT',source_head=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],
        group=GROUP,prior_diagnostic_run=admission.RUN,exact_adapter_edits=edits,
        generated_program_sha256=sha(PROGRAM),requested_budget_s=7200,gdb_attached=False,cold_restart=False,
        routing_complete=False,continuation_accepted=False,final_timing_complete=False,full_phy_accepted=False,
        historical_sources_unchanged_proven=False,old_scheduling_perturbation_retained=True)
    pending=None;after_error=None;report=None
    try:
        sys.argv=[str(PROGRAM),'--stage','cross']
        try:inner.main()
        except BaseException as error:pending=(error,error.__traceback__)
        finally:
            if CURRENT:
                try:r['current_inputs_after']=recheck_inputs()
                except BaseException as error:
                    after_error=error;r['current_input_recheck_error']=dict(error=repr(error),traceback=traceback.format_exc())
            else:r['current_inputs_after_unavailable']='Before-restore proof was never established'
        if(OUT/'result.json').is_file():
            (OUT/'result.json').rename(OUT/'inner-controller-result.json')
            report=json.loads((OUT/'inner-controller-result.json').read_bytes())
            r['inner_controller_result_sha256']=sha(OUT/'inner-controller-result.json')
            r['native_controller_outcome']=report['status'];r['native_route_returned']=bool(report['route_complete'])
            r['new_saved_process_images']=report.get('checkpoint_images',{})
        if pending:
            error,tb=pending
            r['native_inner_error']=dict(error=repr(error),traceback=''.join(traceback.format_exception(type(error),error,tb)))
            if type(error)is AssertionError and str(error)==NO_PROGRESS and report is not None:
                r['original_rejection']=verify_no_progress_site(error,inner.main,program,report)
                r['status']='REJECTED_ORIGINAL_NO_LOG_GATE_PROCESS_CHECKPOINT_PRESERVED'
            raise error.with_traceback(tb)
        if after_error:raise after_error
        r.update(qualify_success(report,int(os.environ['GITHUB_RUN_ID']),os.environ['GITHUB_SHA']))
        methods()
    except BaseException as error:
        if not r['status'].startswith('REJECTED_ORIGINAL_NO_LOG_GATE'):
            r['status']='FAIL_SAME_PROCESS_ROUTE_ATTEMPT'
        r['error']=repr(error);r['traceback']=traceback.format_exc()
        r['continuation_accepted']=False;r['routing_complete']=False
        raise
    finally:
        if OUT.exists():
            if(OUT/'result.json').exists()and not(OUT/'inner-controller-result.json').exists():
                (OUT/'result.json').rename(OUT/'inner-controller-result.json')
            r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
            write(OUT/'result.json',r);print(r['status'],flush=True)
if __name__=='__main__':main()
