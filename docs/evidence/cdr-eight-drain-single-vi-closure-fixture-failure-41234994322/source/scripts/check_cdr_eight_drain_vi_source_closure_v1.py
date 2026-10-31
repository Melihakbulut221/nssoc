#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted frozen-main source closure fixture; never native or admission qualification."""
import ast,contextlib,hashlib,importlib,json,os,socket,subprocess,sys,types,urllib.request
from pathlib import Path
from unittest.mock import patch
import cdr_eight_drain_vi_bias_off_admission_v1 as a
ROOT=a.ROOT
SPEC='scripts/cdr-eight-drain-vi-source-closure-v1.json'
WORKER='scripts/cloud_cdr_eight_drain_vi_bias_off_worker_v1.py'
TRANSPORT='docs/evidence/cdr-via-rich-stream-transport-pass-20261019.json'
def encoded(x):return(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def require(v,message):
    if not v:raise AssertionError(message)
def controls(method):
    actual=a.context();require(os.environ['GITHUB_JOB']=='source-controls','Source-control fixture only')
    environment=dict(os.environ)
    spec=json.loads(a.regular(ROOT,SPEC).read_bytes())
    require(spec['schema']=='single-vi-frozen-worker-source-closure-v1','Exact closure specification')
    require(a.sha(a.regular(ROOT,WORKER))==spec['worker']['sha256']==method['protected_sha256'][WORKER],'Frozen numerical worker unchanged')
    for path,sha in spec['frozen_runtime_source_sha256'].items():
        require(a.sha(a.regular(ROOT,path))==sha==method['protected_sha256'][path],'Frozen runtime source closure changed: '+path)
    for path,pin in spec['required_static_source'].items():
        file=a.regular(ROOT,path)
        require(file.stat().st_size==pin['bytes']and a.sha(file)==pin['sha256']==method['protected_sha256'][path],'Missing static read closure pin')
    text=a.regular(ROOT,WORKER).read_text();tree=ast.parse(text)
    parents={child:parent for parent in ast.walk(tree)for child in ast.iter_child_nodes(parent)}
    def isroot(n):return isinstance(n,ast.Name)and n.id=='ROOT'or isinstance(n,ast.BinOp)and isinstance(n.op,ast.Div)and isroot(n.left)
    expressions=[]
    for n in ast.walk(tree):
        if not(isinstance(n,ast.BinOp)and isroot(n)):continue
        p=parents.get(n)
        if isinstance(p,ast.BinOp)and isinstance(p.op,ast.Div)and p.left is n:continue
        expressions.append(dict(line=n.lineno,scope='main',expression=ast.get_source_segment(text,n)))
    require(expressions==spec['worker_root_expressions']and len(expressions)==11,'Complete worker ROOT expression census')
    require(spec['manual_scope']['unresolved_reachable_ROOT_paths']==[],'Unresolved reachable ROOT read')
    outer=ROOT/'hw/soc/out/cdr-eight-drain-single-vi-source-controls/closure'
    require(not outer.exists()and not outer.is_symlink(),'New owned fixture output');outer.mkdir(parents=True)
    state=dict(active=False,owned=None,blocked=[],reads=set(),bytecode_probes=set())
    def audit(event,args):
        if not state['active']:return
        if event.startswith(('socket.','os.exec','os.spawn','os.posix_spawn'))or event in('subprocess.Popen','os.system','os.fork','os.forkpty','urllib.Request','ctypes.dlopen'):
            state['blocked'].append(event);raise AssertionError('SOURCE_FIXTURE_BLOCKED_EXTERNAL_EFFECT '+event)
        if event!='open'or not isinstance(args[0],(str,bytes,os.PathLike)):return
        path=Path(os.fsdecode(args[0])).absolute();mode=args[1];flags=args[2]
        writing=isinstance(mode,str)and any(c in mode for c in('w','a','x','+'))or isinstance(flags,int)and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing:
            require(path.is_relative_to(state['owned']),'Write outside owned cloud fixture')
        elif path.is_relative_to(ROOT):
            if path.is_relative_to(outer):return
            name=str(path.relative_to(ROOT))
            if name.endswith('.pyc')and not path.exists():state['bytecode_probes'].add(name);return
            require(name in method['protected_sha256']or name==a.METHOD,'Unpinned repository read: '+name)
            state['reads'].add(name)
    sys.addaudithook(audit)
    # Real forbidden APIs are stopped before socket/process creation, not mocked.
    state.update(active=True,owned=outer)
    barrier=[]
    try:
        for name,call in(('socket',lambda:socket.socket()),('subprocess',lambda:subprocess.Popen([sys.executable,'-c','raise SystemExit(91)'])),
          ('os.system',lambda:os.system('exit 91')),('urllib',lambda:urllib.request.urlopen('https://example.invalid/'))):
            try:call()
            except AssertionError as error:
                require(str(error).startswith('SOURCE_FIXTURE_BLOCKED_EXTERNAL_EFFECT'),'Unexpected barrier failure');barrier.append(name)
            else:raise AssertionError('External effect escaped fixture barrier: '+name)
        before=len(state['blocked'])
        worker=importlib.import_module('cloud_cdr_eight_drain_vi_bias_off_worker_v1')
        require(len(state['blocked'])==before,'Imported worker attempted external effect')
    finally:state['active']=False
    production_rejections=[]
    for case,prepare in(('nominal_early',True),('vi_bias_off',False)):
        try:a.authorize_case(case,prepare)
        except AssertionError as error:production_rejections.append(dict(case=case,prepare_only=prepare,error=str(error)))
        else:raise AssertionError('Production gate unexpectedly admitted source-control job')
    cases=[]
    class AcquisitionBoundary(BaseException):pass
    for label,case,prepare,missing in(('preparation','nominal_early',True,False),('vi','vi_bias_off',False,False),('missing-static-source','nominal_early',True,True)):
        owned=outer/label;owned.mkdir();calls=[];boundary=AcquisitionBoundary('EXPLICIT_SOURCE_FIXTURE_STOP_BEFORE_NATIVE_RESTORE')
        class FixtureRoot:
            def __truediv__(self,name):
                name=str(name)
                if name=='cloud-cdr-current-eight-drain-loaded-'+case:return owned/'worker'
                if missing and name==TRANSPORT:return owned/'intentionally-missing-static-source.json'
                return ROOT/name
        def fixture_authorize(case_arg,prepare_arg):
            require(dict(os.environ)==environment,'Environment identity spoofed')
            require((case_arg,prepare_arg)==(case,prepare)and type(prepare_arg)is bool,'Explicit fixture scope')
            calls.append('synthetic_source_fixture_entry')
        def stop(out,prepare_arg):
            require(out==owned/'worker'and prepare_arg is prepare,'Exact acquisition boundary')
            calls.append('native_restore_not_entered');raise boundary
        class FixtureAdmission:
            def __getattr__(self,name):
                if name=='authorize_case':return fixture_authorize
                if name=='restore':return stop
                return getattr(a,name)
        scope={**worker.main.__globals__,'ROOT':FixtureRoot(),'current_inputs':FixtureAdmission()}
        entry=types.FunctionType(worker.main.__code__,scope,worker.main.__name__,worker.main.__defaults__,worker.main.__closure__)
        require(entry.__code__ is worker.main.__code__ and worker.current_inputs is a,'Frozen production entry/module changed')
        argv=['EXPLICIT_SOURCE_CLOSURE_FIXTURE','--case',case]+(['--prepare-only']if prepare else[])
        before_blocks=len(state['blocked']);caught=None
        state.update(active=True,owned=owned)
        try:
            with patch.object(sys,'argv',argv),patch.object(worker.reports,'OUT',worker.reports.OUT):entry()
        except BaseException as error:caught=error
        finally:state['active']=False
        require(dict(os.environ)==environment and len(state['blocked'])==before_blocks,'Fixture environment/external-effect violation')
        if missing:
            require(isinstance(caught,FileNotFoundError)and calls==['synthetic_source_fixture_entry'],'Missing static source did not fail before acquisition')
            require(not(owned/'worker').exists(),'Incomplete pinned source passed pre-output integrity')
            row=dict(case=case,preparation_only=prepare,expected_missing_static_source_refused=True,error=str(caught),calls=calls)
        else:
            require(caught is boundary and calls==['synthetic_source_fixture_entry','native_restore_not_entered'],'Did not reach the exact no-acquisition boundary')
            raw=a.regular(owned/'worker','result.json').read_bytes();result=json.loads(raw)
            require(result['status']=='FAIL_OR_ERROR'and result['source_head']==actual['source']and result['case']==case,'Expected synthetic boundary result only')
            require(result['transport_control_source']==dict(run=39167905272,summary_sha256='6dedebb34be2a5ae446fcd6add23613f091016a776a921f4625ecc74a7f841d3',parts_sha256='1fc3d3de6d243717ee88c1f330aff125b1714e7428bc52aa88f9b438158c62b3'),'Real transport JSON not consumed')
            require(result['terminal_finalization_complete']is True and result['terminal_inventory_complete']is True and not result['terminal_errors'],'Unchanged real terminal finalizer failed')
            require(result['active_primary_exception_before_terminal']['type']=='AcquisitionBoundary','Synthetic acquisition boundary identity lost')
            require(not(owned/'worker/current-mim-bundle').exists()and not(owned/'worker/source').exists(),'Native payload directory unexpectedly created')
            row=dict(case=case,preparation_only=prepare,calls=calls,worker_main_code_identity=True,
              result_path=str((owned/'worker/result.json').relative_to(outer)),result_bytes=len(raw),result_sha256=hashlib.sha256(raw).hexdigest(),
              real_readback_controls=result['readback_controls'],real_transport_source=result['transport_control_source'],terminal_finalizer_complete=True)
        cases.append(row)
    require(TRANSPORT in state['reads'],'Actual static transport file was not read')
    report=dict(status='PASS_FROZEN_MAIN_STATIC_CLOSURE_FIXTURE_NOT_PRODUCTION_ADMISSION',source=actual['source'],run_id=actual['run_id'],
      method_sha256=a.sha(ROOT/a.METHOD),worker_sha256=spec['worker']['sha256'],production_gate_refusals=production_rejections,
      cases=cases,network_process_barrier_controls=barrier,blocked_events=state['blocked'],
      actual_repository_reads=sorted(state['reads']),absent_bytecode_probes=sorted(state['bytecode_probes']),
      frozen_runtime_sources=len(spec['frozen_runtime_source_sha256']),ROOT_expressions=11,
      fixture_globals_only=True,production_module_changed=False,github_environment_spoofed=False,
      native_acquisition=False,native_simulator_executed=False,production_admission_qualified=False,electrical_accepted=False)
    (outer/'receipt.json').write_bytes(encoded(report));return report
