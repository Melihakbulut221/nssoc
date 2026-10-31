#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source closure test: unchanged checker import to first native boundary only."""
import argparse,ast,ctypes,hashlib,importlib.util,json,os,re,socket,subprocess,sys,types,urllib.request
import xml.etree.ElementTree
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC='scripts/cdr-via2-m3-physical-source-closure.json'
MANIFEST='scripts/cdr-via2-m3-physical-closure-pins.json'
OUT=ROOT/'hw/soc/out/cdr-via2-m3-physical-source-closure-controls'
def require(value,message):
    if not value:raise AssertionError(message)
def encode(value):return(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def fingerprint(path):
    with path.open('rb')as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return dict(bytes=path.stat().st_size,sha256=digest)
def regular(path):
    path=Path(path)
    require(path.is_absolute()and path.is_file()and not path.is_symlink(),'Regular existing file required: '+str(path))
    require(path.resolve()==path,'Symlink component not allowed: '+str(path))
    return path
def context():
    e=os.environ
    require(e.get('GITHUB_ACTIONS')=='true'and e.get('RUNNER_ENVIRONMENT')=='github-hosted'and e.get('RUNNER_OS')=='Linux','Hosted Linux only')
    require(e.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'and e.get('GITHUB_EVENT_NAME')=='workflow_dispatch','Manual exact repository')
    branch='codex/cdr-via2-m3-physical-source-closure'
    require(e.get('GITHUB_REF')=='refs/heads/'+branch,'Exact isolated source-only branch')
    require(e.get('GITHUB_WORKFLOW_REF')=='Melihakbulut221/nssoc/.github/workflows/cloud-evidence-summary.yml@refs/heads/'+branch,'Exact registered workflow')
    require(e.get('GITHUB_JOB')=='source-controls'and e.get('GITHUB_RUN_ATTEMPT')=='1','Source-only job; no retries')
    require(re.fullmatch('[0-9a-f]{40}',e.get('GITHUB_SHA',''))and re.fullmatch('[1-9][0-9]*',e.get('GITHUB_RUN_ID','')),'Exact source and run')
    require(e.get('APPROVED_SOURCE')==e['GITHUB_SHA'],'Explicit exact source')
    require(Path.cwd()==ROOT,'Actual checkout cwd, never fixture ROOT spoofing')
    return dict(source=e['GITHUB_SHA'],run_id=int(e['GITHUB_RUN_ID']),attempt=1,branch=branch)
def source_guard(ctx):
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==ctx['source'],'Actual Git HEAD')
    raw=regular(ROOT/MANIFEST).read_bytes()
    require(raw==subprocess.check_output(['git','show',ctx['source']+':'+MANIFEST],cwd=ROOT),'Immutable manifest bytes')
    manifest=json.loads(raw)
    require(manifest['schema']=='cdr-via2-m3-physical-closure-pins-v1'and manifest['native_execution_authorized']is False,'Source-only manifest')
    for name,pin in manifest['files'].items():
        require(fingerprint(regular(ROOT/name))==dict(bytes=pin['bytes'],sha256=pin['sha256']),'Protected source closure changed: '+name)
    spec=json.loads(regular(ROOT/SPEC).read_bytes())
    require(spec['authorization']==dict(source_controls=True,native_candidate_acquisition=False,geometry_generation=False,physical_execution=False,fresh_rc=False,electrical_simulation=False),'No native authorization')
    for name,pin in {**spec['static_repository_files'],**spec['analog_import_sources']}.items():
        require(manifest['files'][name]['sha256']==pin['sha256']and manifest['files'][name]['bytes']==pin['bytes'],'Complete closure manifest')
    return spec,manifest

def prepare_decks():
    ctx=context();spec,manifest=source_guard(ctx)
    sys.path.insert(0,str(ROOT/'hw/soc/flow'))
    from prepare_ihp_drc import prepare,validate_lock,verify
    records={}
    for kind,contract in spec['runtime_decks'].items():
        lock=json.loads(regular(ROOT/contract['lock']).read_bytes());validate_lock(lock)
        require(lock['repository']==contract['repository']and lock['commit']==contract['commit']and len(lock['files'])==contract['count'],'Exact immutable deck closure')
        destination=ROOT/('hw/soc/tools/ihp-'+kind+'-5e6d592')
        prepare(lock,destination)
        for row in lock['files']:
            path=regular(destination/row['path']);verify(path.read_bytes(),row)
            records[str(path.relative_to(ROOT))]=fingerprint(path)
    require(len(records)==98,'Full45DRC53LVS source census')
    OUT.mkdir(parents=True,exist_ok=False)
    (OUT/'deck-source-preparation.json').write_bytes(encode(dict(status='PREPARED_PINNED_SOURCE_DECKS_NOT_NATIVE_EXECUTION',**ctx,files=records,native_acquisition=False,tool_executed=False)))
    source_guard(ctx)
    print(json.dumps(dict(status='PREPARED_PINNED_98_SOURCE_FILES',**ctx),sort_keys=True))

def controls():
    ctx=context();spec,manifest=source_guard(ctx);environment=dict(os.environ)
    app=regular(Path(os.environ['CLOUD_APPIMAGE']).resolve())
    require(fingerprint(app)['sha256']==spec['appimage']['sha256'],'Real pinned immutable AppImage; never execute it')
    deck_receipt=json.loads(regular(OUT/'deck-source-preparation.json').read_bytes())
    require(deck_receipt['source']==ctx['source']and deck_receipt['run_id']==ctx['run_id']and len(deck_receipt['files'])==98,'Same-source full source-deck preparation')
    for name,pin in deck_receipt['files'].items():require(fingerprint(regular(ROOT/name))==pin,'Real deck source byte mismatch')
    outer=OUT/'fixture';require(not outer.exists(),'New isolated owned fixture');outer.mkdir()
    checker=outer/'unchanged_check_physical.py'
    original=regular(ROOT/spec['checker']['path']).read_text()
    require(hashlib.sha256(original.encode()).hexdigest()==spec['checker']['sha256'],'Original full checker bytes')
    transformed=original
    for row in spec['checker']['changes']:
        require(transformed.count(row['before'])==row['count']and row['after']not in transformed,'Exact original four substitutions')
        transformed=transformed.replace(row['before'],row['after'])
    reverse=transformed
    for row in reversed(spec['checker']['changes']):
        require(reverse.count(row['after'])==row['count'],'Exact four-substitution reversal census')
        reverse=reverse.replace(row['after'],row['before'])
    require(reverse==original,'Byte-identical four-substitution reversal')
    checker.write_text(transformed)
    require(fingerprint(checker)==spec['checker']['generated'],'Exact generated checker from real failed producer')
    ast.parse(transformed)
    require(len(spec['manual_reachable_closure']['imported_python'])==9 and len(spec['manual_reachable_closure']['read_hashed_without_import'])==3,'Complete12Python closure')
    allowed={ROOT/n for n in manifest['files']}|{ROOT/MANIFEST}|{ROOT/n for n in deck_receipt['files']}|{app}
    state=dict(active=False,reads=set(),bytecode_probes=set(),blocked=[],deny_read=None,read_fault_hits=[],owned=outer)
    native_roots={Path(sys.base_prefix).resolve(),Path(sys.prefix).resolve()}
    def owned(path):return path==outer or path.is_relative_to(outer)
    def audit(event,args):
        if not state['active']:return
        if event.startswith(('socket.','os.exec','os.spawn','os.posix_spawn'))or event in('subprocess.Popen','os.system','os.fork','os.forkpty','urllib.Request','ctypes.dlopen'):
            state['blocked'].append(event);raise AssertionError('CLOSURE_BARRIER_EXTERNAL_EFFECT '+event)
        if event in('os.mkdir','os.remove','os.rmdir','os.chmod','os.truncate','os.symlink','os.link','os.rename','os.chdir'):
            paths=args[:2]if event in('os.rename','os.link','os.symlink')else args[:1]
            require(event!='os.chdir','Real checkout cwd immutable')
            for value in paths:
                if isinstance(value,(str,bytes,os.PathLike)):
                    path=Path(os.fsdecode(value)).absolute()
                    require(owned(path),'Filesystem mutation outside owned fixture')
        if event!='open'or not isinstance(args[0],(str,bytes,os.PathLike)):return
        path=Path(os.fsdecode(args[0])).absolute();mode=args[1];flags=args[2]
        writing=isinstance(mode,str)and any(c in mode for c in('w','a','x','+'))or isinstance(flags,int)and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing:
            require(owned(path),'Write outside owned fixture');return
        if path==state['deny_read']:
            state['read_fault_hits'].append(str(path));raise FileNotFoundError('EXPLICIT_MISSING_SOURCE_FIXTURE '+str(path))
        if owned(path):return
        if path.is_relative_to(ROOT):
            if path.suffix=='.pyc'and not path.exists():state['bytecode_probes'].add(str(path.relative_to(ROOT)));return
            require(path in allowed,'Unpinned repository read: '+str(path));state['reads'].add(str(path.relative_to(ROOT)))
        else:require(path==app or any(path.is_relative_to(p)for p in native_roots),'Unexpected external file read: '+str(path))
    sys.addaudithook(audit)
    barrier=[];state['active']=True
    try:
        for name,call in(('socket',lambda:socket.socket()),('subprocess',lambda:subprocess.Popen([sys.executable,'-c','raise SystemExit(91)'])),('os.system',lambda:os.system('exit 91')),('urllib',lambda:urllib.request.urlopen('https://example.invalid/')),('ctypes',lambda:ctypes.CDLL(None))):
            try:call()
            except AssertionError as error:
                require(str(error).startswith('CLOSURE_BARRIER_EXTERNAL_EFFECT'),'Unexpected external barrier rejection');barrier.append(name)
            else:raise AssertionError('Native/network/process escaped barrier: '+name)
        try:(ROOT/'forbidden-source-closure-write').write_text('must never exist')
        except AssertionError as error:require(str(error)=='Write outside owned fixture','Expected write barrier');barrier.append('repository-write')
        else:raise AssertionError('Repository write escaped fixture')
    finally:state['active']=False
    def import_checker(label):
        module_spec=importlib.util.spec_from_file_location('explicit_physical_closure_fixture_'+label,checker)
        module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module);return module
    # Import-time build() is real; all seven original SPICE bytes stay only on this runner.
    before=len(state['blocked']);state['active']=True
    try:module=import_checker('positive')
    finally:state['active']=False
    require(len(state['blocked'])==before and len(module.PORTS)==25 and sum(module.EXPECTED_CENSUS.values())==500,'Actual import identity; no physical execution')
    import_refusals=[]
    for name in spec['analog_import_sources']:
        state.update(active=True,deny_read=ROOT/name);caught=None;before=len(state['read_fault_hits'])
        try:import_checker('missing_'+str(len(import_refusals)))
        except BaseException as error:caught=error
        finally:state.update(active=False,deny_read=None)
        require(isinstance(caught,FileNotFoundError)and str(caught).startswith('EXPLICIT_MISSING_SOURCE_FIXTURE ')and len(state['read_fault_hits'])==before+1,'Missing import source not refused before native boundary')
        import_refusals.append(dict(path=name,exception=type(caught).__name__,native_boundary_reached=False))
    # A deliberately non-GDS synthetic input exercises unchanged run() admission only.
    layout=outer/'synthetic-layout';layout.mkdir()
    (layout/(module.TOP+'.gds')).write_bytes(b'EXPLICIT NON-GDS SOURCE CLOSURE FIXTURE\n')
    (layout/'schematic.cir').write_bytes(b'EXPLICIT NON-SPICE SOURCE CLOSURE FIXTURE\n')
    generated=dict(inputs={str(ROOT/n):pin['sha256']for n,pin in spec['analog_import_sources'].items()},outputs={p.name:fingerprint(p)['sha256']for p in layout.iterdir()})
    (layout/'result.json').write_bytes(encode(generated))
    calls=[]
    class NativeBoundary(BaseException):pass
    boundary=NativeBoundary('EXPLICIT_STOP_BEFORE_FIRST_NATIVE_DRC_EXECUTION')
    def stop(command,directory,label):
        expected=[app,'klayout','-b','-zz','-r',ROOT/'hw/soc/tools/ihp-drc-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/drc/ihp-sg13g2.drc']
        options=['input='+str(layout/(module.TOP+'.gds')),'topcell='+module.TOP,'log='+str(directory/'deck.log'),'run_mode=deep','report='+str(directory/'drc.lyrdb'),'threads=2','no_recommended=False','precheck_drc=False']
        for option in options:expected+=['-rd',option]
        require(command==expected and directory.name=='drc'and label=='run','Exact original first-native command boundary')
        require(dict(os.environ)==environment,'Production GitHub environment mutated')
        calls.append(dict(command=list(map(str,command)),directory=str(directory.relative_to(outer)),label=label,native_executed=False))
        raise boundary
    scope={**module.run.__globals__,'execute':stop}
    entry=types.FunctionType(module.run.__code__,scope,module.run.__name__,module.run.__defaults__,module.run.__closure__)
    require(entry.__code__ is module.run.__code__ and module.execute is not stop,'Unchanged code object; production module not patched')
    runtime_refusals=[]
    # Every static Python/lock/analog/deck path that run() reads must refuse missing bytes.
    # All98 deck and21 repository pins are positively read; bounded independent missing categories follow.
    direct=set(spec['manual_reachable_closure']['read_hashed_without_import'])|{'hw/soc/flow/check_ihp_drc.py','hw/soc/flow/prepare_ihp_drc.py','hw/soc/flow/check_pcie_rx_cell.py','hw/soc/flow/check_pcie_analog_bank.py','scripts/cdr_retimed_localbus_v12_parent_plan.py','hw/soc/pnr/ihp-drc.lock.json','hw/soc/pnr/ihp-lvs.lock.json'}|set(spec['analog_import_sources'])|set(deck_receipt['files'])
    denied=['scripts/generate_cdr_retimed_localbus_v12_parent.py','hw/soc/pnr/ihp-drc.lock.json']
    for kind in('drc','lvs'):
        lock=json.loads((ROOT/spec['runtime_decks'][kind]['lock']).read_bytes())
        denied.append('hw/soc/tools/ihp-'+kind+'-5e6d592/'+lock['entrypoint'])
    for index,name in enumerate(denied):
        output=outer/('missing-runtime-'+str(index));before_calls=len(calls);caught=None
        state.update(active=True,deny_read=ROOT/name)
        try:entry(layout,output,app)
        except BaseException as error:caught=error
        finally:state.update(active=False,deny_read=None)
        require(isinstance(caught,FileNotFoundError)and str(caught).startswith('EXPLICIT_MISSING_SOURCE_FIXTURE ')and len(calls)==before_calls and not output.exists(),'Missing runtime source reached native boundary: '+name)
        runtime_refusals.append(dict(path=name,exception=type(caught).__name__,native_boundary_reached=False))
    positive=outer/'positive';caught=None;before_blocks=len(state['blocked'])
    state['active']=True
    try:entry(layout,positive,app)
    except BaseException as error:caught=error
    finally:state['active']=False
    require(caught is boundary and len(calls)==1 and len(state['blocked'])==before_blocks,'Must reach exactly first native boundary without effects')
    record=json.loads(regular(positive/'result.json').read_bytes())
    require(record['status']=='RUNNING'and record['steps']=={}and record['serial_phy_complete']is False and record['main_chip_integrated']is False and record['qualified_pex']is False,'Unexecuted RUNNING fixture only, never physical success')
    require(set(record['inputs'])>={str(ROOT/n)for n in direct},'All declared run-time pinned reads observed')
    expected_reads=set(spec['static_repository_files'])-{'hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py'}|set(spec['analog_import_sources'])|set(deck_receipt['files'])
    require(expected_reads<=state['reads'],'Incomplete observed source/import closure')
    require(dict(os.environ)==environment and Path.cwd()==ROOT,'Environment or cwd spoofed')
    source_guard(ctx)
    result=dict(status='PASS_UNCHANGED_PHYSICAL_CHECKER_IMPORT_TO_FIRST_NATIVE_BOUNDARY_ONLY',**ctx,
      checker=spec['checker']['generated'],four_transform_reversal_exact=True,unchanged_run_code_object=True,
      import_source_refusals=import_refusals,runtime_source_refusals=runtime_refusals,external_barriers=barrier,
      observed_repository_reads=sorted(state['reads']),absent_bytecode_probes=sorted(state['bytecode_probes']),blocked_events=state['blocked'],
      calls=calls,first_native_command_not_executed=True,real_pinned_appimage_verified=True,real_pinned_deck_files=98,
      imported_python_files=9,hash_only_python_files=3,original_analog_import_files=7,
      synthetic_layout_only=True,fixture_only_globals=['execute'],production_module_modified=False,github_environment_spoofed=False,
      native_candidate_acquired=False,geometry_generated=False,drc_executed=False,lvs_executed=False,physical_accepted=False,
      fresh_rc_executed=False,electrical_accepted=False,production_admission_qualified=False)
    (OUT/'result.json').write_bytes(encode(result));print(json.dumps(result,sort_keys=True))
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-decks',action='store_true');args=parser.parse_args()
    if args.prepare_decks:prepare_decks()
    else:controls()
