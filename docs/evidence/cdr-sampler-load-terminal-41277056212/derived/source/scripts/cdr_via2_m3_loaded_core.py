#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explicit current-RC loaded numerical library; standalone native execution is disabled."""
import ast,copy,hashlib,json,os,re,textwrap,traceback
from collections import Counter
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
CATALOG='scripts/cdr-via2-m3-loaded-core-catalog.json'
CATALOG_SHA='1878794473cdba6b5eaf35b983b02f219f8eecd45067976391a8ab22c574b082'
INPUTS='scripts/cdr-via2-m3-loaded-core-inputs.json'
INPUTS_SHA='e41b27534d66a4a57cc12a73f1b40c0131e8e3ea3f56f42fc5d5d95cf060cfe1'
WORKER='scripts/cloud_cdr_current_eight_drain_loaded.py'
PREPARED_STATUS='PASS_CURRENT_VIA2_M3_LOADED_PREPARATION_NO_TRANSIENT'
EXECUTABLE_BLOCKS={'scenario','prerequisites','binding','deck','measurement'}

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(path):
    with Path(path).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def file_pin(path):
    path=Path(path);require(path.is_file()and not path.is_symlink(),'regular input file')
    return dict(bytes=path.stat().st_size,sha256=sha(path))

def source_path(root,name):
    root=Path(root).absolute();path=root/name
    require(not Path(name).is_absolute()and '..'not in Path(name).parts,'relative source path')
    require(path.resolve()==path.absolute()and path.is_file(),'unaliased regular source path')
    return path

def pinned_json(path,pin):
    require(file_pin(path)=={k:pin[k]for k in ('bytes','sha256')},'exact file bytes: '+str(path))
    return json.loads(Path(path).read_bytes())

def stable_ast(tree):
    # Python 3.13+ omits optional empty fields by default; keep the older full form.
    try:return ast.dump(tree,annotate_fields=True,include_attributes=False,show_empty=True)
    except TypeError:return ast.dump(tree,annotate_fields=True,include_attributes=False)

def digest_bytes(raw):return hashlib.sha256(raw).hexdigest()

def catalog(root=ROOT):
    path=source_path(root,CATALOG);require(sha(path)==CATALOG_SHA,'frozen catalog bytes')
    value=json.loads(path.read_bytes());require(value['original_source']=='84b8b591e10be32716947c8d6b079fd7a21ce18d','frozen original worker identity')
    for name,pin in value['files'].items():require(file_pin(source_path(root,name))==pin,'frozen complete source: '+name)
    return value

def extract(record,root=ROOT,dedented=False):
    c=catalog(root);path=source_path(root,record['file']);lines=path.read_text().splitlines(True)
    raw=''.join(lines[record['start']-1:record['end']]).encode()
    require(len(raw)==record['bytes']and digest_bytes(raw)==record['sha256'],'exact frozen definition/block bytes')
    text=textwrap.dedent(raw.decode())if dedented else raw.decode()
    if dedented:require(digest_bytes(text.encode())==record['dedented_sha256'],'exact dedented frozen block')
    tree=ast.parse(text,filename=str(path))
    require(digest_bytes(stable_ast(tree).encode())==record['ast_sha256'],'exact frozen AST')
    return text,tree

def select_definition(tree,name,kind):
    require(name!='main','historical main excluded')
    if kind=='Assign':
        require(tree.body and all(isinstance(n,ast.Assign)and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)for n in tree.body),'assignment-only physical line')
        names=[n.targets[0].id for n in tree.body]
    else:
        require(kind=='FunctionDef'and len(tree.body)==1 and isinstance(tree.body[0],ast.FunctionDef),'single function definition')
        names=[tree.body[0].name]
    require(len(names)==len(set(names))and names.count(name)==1,'unique exact named definition')
    return ast.Module(body=[tree.body[names.index(name)]],type_ignores=[])

def definition(namespace,file,name,root=ROOT):
    record=catalog(root)['definitions'][file+':'+name];text,tree=extract(record,root)
    require(record['name']==name,'catalog definition name')
    selected=select_definition(tree,name,record['kind'])
    exec(compile(selected,str(source_path(root,file))+':'+name,'exec'),namespace)
    return namespace[name]

def block(name,namespace,root=ROOT):
    require(name in EXECUTABLE_BLOCKS,'historical runtime/acquisition/main are not executable blocks')
    record=catalog(root)['blocks'][name];text,tree=extract(record,root,True)
    exec(compile(tree,str(source_path(root,record['file']))+':'+name,'exec'),namespace)
    return namespace

def module_namespace(root,file,values):
    return dict(__name__='frozen_loaded_'+Path(file).stem,__file__=str(source_path(root,file)),**values)

def numerical_namespace(root=ROOT,numpy=None):
    """Load only byte-bound definitions into independent explicit namespaces."""
    if numpy is None:
        import numpy as numpy
    catalog(root)
    parser_file='scripts/build_pcie_local_vco_hybrid_v6.py'
    parser=module_namespace(root,parser_file,dict(re=re,Decimal=Decimal))
    for name in ('require','statements','number'):definition(parser,parser_file,name,root)
    mux_file='scripts/run_cloud_tx_mux4.py';mux=module_namespace(root,mux_file,dict(re=re))
    for name in ('NEWTON_PROFILES','solver_options','verify_solver_options','native_diagnostics','native_save_commands'):definition(mux,mux_file,name,root)
    backend_file='scripts/cloud_vbic_tree32_backend.py';backend=module_namespace(root,backend_file,dict(re=re,hashlib=hashlib,native_diagnostics=mux['native_diagnostics']))
    for name in ('option_values','options','backend_readback','readback_controls'):definition(backend,backend_file,name,root)
    legacy_file='scripts/cloud_cdr_pd_vi.py';legacy=module_namespace(root,legacy_file,{})
    for name in ('UI','START','STOP','STEP','pwl','clock','shifted_data'):definition(legacy,legacy_file,name,root)
    stream_file='scripts/cloud_tx_stream.py';stream=module_namespace(root,stream_file,dict(np=numpy,Path=Path,hashlib=hashlib))
    for name in ('digest','streaming_deck','read_streamed_wave'):definition(stream,stream_file,name,root)
    primitive_file='scripts/cloud_cdr_xor.py';primitive=module_namespace(root,primitive_file,{})
    definition(primitive,primitive_file,'prbs',root)
    pump_file='scripts/cloud_pll_pump_current.py';pump=module_namespace(root,pump_file,{})
    definition(pump,pump_file,'CORNERS',root)
    ns=module_namespace(root,WORKER,dict(copy=copy,hashlib=hashlib,json=json,os=os,re=re,Counter=Counter,Decimal=Decimal,Path=Path,np=numpy,ROOT=Path(root).absolute(),sha=sha,
      parser=SimpleNamespace(**parser),legacy=SimpleNamespace(**legacy),stream=SimpleNamespace(**stream),primitive=SimpleNamespace(**primitive),pump=SimpleNamespace(**pump),
      native_save_commands=mux['native_save_commands'],backend_readback=backend['backend_readback'],readback_controls=backend['readback_controls'],
      UI=legacy['UI'],START=legacy['START'],STOP=legacy['STOP'],STEP=legacy['STEP']))
    for name in ('MODEL','CASES','BIASES','bind_native','binding_controls'):definition(ns,WORKER,name,root)
    require(ns['UI']==125e-12 and ns['START']==2e-9 and ns['STOP']==ns['START']+258*ns['UI']and ns['STEP']==.3125e-12,'unchanged numerical time contract')
    require('main'not in ns and 'current_inputs'not in ns and 'reports'not in ns and 'fetch'not in ns,'no historical orchestration namespace')
    return ns

def current_configuration(root=ROOT):
    path=source_path(root,INPUTS);require(sha(path)==INPUTS_SHA,'current input descriptor bytes')
    c=json.loads(path.read_bytes())
    require(c['native_execution_authorized']is False and c['wave_execution_authorized']is False,'core descriptor grants no execution authority')
    require(c['allowed_cases']==['nominal_late'],'single matching declared scenario')
    records={name:pinned_json(source_path(root,pin['path']),pin)for name,pin in c['records'].items()}
    transport=c['transport_prerequisite'];records['transport_prerequisite']=pinned_json(source_path(root,transport['path']),transport)
    q=records['readback/actual/fresh-rc-qualification.json'];p=c['producer']
    require(q['status']=='PASS_CURRENT_VIA2_M3_FRESH_RC_NUMERICAL_QUALIFICATION_REQUIRES_LOADED_WAVES'and q['fresh_RC_pipeline_complete']is True,'actual complete current RC qualification')
    require(q['context']==dict(source=p['source'],run_id=p['run'],attempt=p['attempt'])and q['execution_scope']=='ACTUAL_AUTHORIZED_NATIVE_PHASE','actual RC producer identity')
    require(all(q[k]is False for k in ('electrical_accepted','qualified_pex','full_phy_accepted','loaded_simulation_passed')),'RC does not imply loaded acceptance')
    contract=records['readback/actual/mim/composition/composition.json'];planes=records['readback/actual/binding/inputs/native-planes.json'];projection=records['derived-loaded-vector-projection.json']
    require(contract['counts']==q['counts']=={k:c['observed'][k]for k in ('devices','R','C')},'actual current census')
    require(contract['interface']==c['observed']['interface']and len(contract['interface'])==26,'actual current interface order')
    require(len(contract['device_records'])==500 and sum(len(d['terminals'])for d in contract['device_records'])==1446,'all current device terminals')
    require(planes['status']=='PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS'and len(planes['anchors'])==160 and len({a['logical_net']for a in planes['anchors']})==51,'full current native planes')
    require(projection['native_model_card_validation_executed']is False and projection['loaded_simulation_executed']is False,'derived selection is not native card or wave validation')
    require(projection['counts']==c['observed']['selected_vectors']and len(projection['vectors'])==projection['counts']['total'],'actual measured selection census')
    require(projection['source']==p['source']and projection['run_id']==p['run'],'current vector projection identity')
    receipt=records['receipt.json'];require(receipt['source']==p['source']and receipt['run_id']==p['run']and receipt['release_id']==p['release']and receipt['conclusion']=='success','full producer receipt identity')
    for name,pin in c['records'].items():
        if name=='receipt.json':continue
        expected=receipt['files'][name];require(all(expected[k]==pin[k]for k in ('bytes','sha256')),'receipt exact record '+name)
    return c,records

def context_key(context):
    require(set(context)=={'source','run_id','attempt'}and re.fullmatch('[0-9a-f]{40}',context['source'])is not None,'explicit current execution context')
    require(type(context['run_id'])is int and context['run_id']>0 and context['attempt']==1,'current run/first attempt')
    return copy.deepcopy(context)

def actual_context(context):
    context=context_key(context)
    require(os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_SHA')==context['source']and os.environ.get('GITHUB_RUN_ID')==str(context['run_id'])and os.environ.get('GITHUB_RUN_ATTEMPT')=='1','real hosted execution identity; no environment substitution')
    return context

def verify_current_inputs(paths,root=ROOT):
    c,records=current_configuration(root);require(set(paths)=={'model','composition','planes'},'explicit native input paths')
    for role in paths:
        path=Path(paths[role]).absolute();require(path.resolve()==path,'unaliased native input path')
        require(file_pin(path)=={k:c[role][k]for k in ('bytes','sha256')},'actual current '+role+' bytes')
    contract=json.loads(Path(paths['composition']).read_bytes());planes=json.loads(Path(paths['planes']).read_bytes())
    require(contract==records['readback/actual/mim/composition/composition.json']and planes==records['readback/actual/binding/inputs/native-planes.json'],'native restored/derived exact join')
    return c,records,contract,planes

def verify_runtime(runtime,root=ROOT):
    c,_=current_configuration(root)
    require(set(runtime)=={'lib','engine','source_pin','models_summary'},'explicit restored runtime paths')
    paths={k:Path(v).absolute()for k,v in runtime.items()}
    require(all(p.resolve()==p for p in paths.values()),'unaliased runtime paths')
    require(sha(paths['engine'])==c['runtime']['engine_sha256']and sha(paths['source_pin'])==c['runtime']['model_pin_sha256']and sha(paths['models_summary'])==c['runtime']['original_models_summary_sha256'],'unchanged real engine/model manifests')
    original=json.loads(paths['source_pin'].read_bytes());pins=original['preparation']['model_sources'];lib=paths['lib']
    require(lib.is_dir()and all(not p.is_symlink()for p in lib.rglob('*')),'regular owned model library')
    files={str(p.relative_to(lib)):p for p in lib.rglob('*')if p.is_file()}
    require(set(files)==set(pins),'complete exact original model library')
    require(all(sha(files[name])==digest for name,digest in pins.items()),'all unchanged model-source bytes')
    require(os.access(paths['engine'],os.X_OK),'executable frozen engine')
    return dict(paths={k:str(v)for k,v in paths.items()},engine=file_pin(paths['engine']),source_pin=file_pin(paths['source_pin']),models_summary=file_pin(paths['models_summary']),model_files={n:file_pin(p)for n,p in files.items()})

def write_exclusive(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    require(path.parent.resolve()==path.parent.absolute(),'unaliased output parent')
    raw=(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    with path.open('xb')as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return file_pin(path)

def snapshot_writer(out,report):
    directory=Path(out)/'numerical-observations';directory.mkdir(exist_ok=True)
    require(directory.resolve()==directory.absolute(),'unaliased numerical observations')
    def save():
        serial=0
        while (directory/('%06d.json'%serial)).exists():serial+=1
        return write_exclusive(directory/('%06d.json'%serial),report)
    return save

def preserve_phase_failure(report,error):
    if report.get('status')in ('RUNNING','RUNNING_ACTUAL_WHOLE_WIRE_TRANSIENT'):report['status']='FAIL_OR_ERROR'
    report['error']=repr(error);report['traceback']=''.join(traceback.format_exception(type(error),error,error.__traceback__))

def finish_report(path,report,primary):
    try:write_exclusive(path,report)
    except BaseException as error:
        try:print(json.dumps(dict(unsaved_loaded_report=report,secondary_save_error=repr(error)),sort_keys=True,allow_nan=False),flush=True)
        except BaseException:pass
        if primary is None:raise

def verify_projection(namespace,projection):
    bound=namespace['bound'];vectors=namespace['vectors'];r=namespace['r']
    require(vectors==projection['vectors'],'complete actual selected vector order')
    require(bound['aliases']=={name:row['loaded_node']for name,row in projection['aliases'].items()},'all actual collector aliases')
    require(r['vector_census']==dict(total=projection['counts']['total'],voltage_nodes=projection['counts']['voltage_nodes'],hbt_collector_currents=projection['counts']['hbt_currents'],mos_drain_currents=projection['counts']['mos_currents'],save_commands=len(namespace['native_save_commands'](vectors))),'current selected vector census')

def prepare_case(out,paths,runtime,context,case='nominal_late',root=ROOT):
    """Prepare actual pinned model and full frozen deck; never invokes a simulator."""
    context=actual_context(context);require(case=='nominal_late','only matching nominal_late')
    c,records,contract,planes=verify_current_inputs(paths,root);runtime_proof=verify_runtime(runtime,root)
    out=Path(out).absolute();require(out.resolve()==out,'unaliased new case workspace');out.mkdir(exist_ok=False)
    ns=numerical_namespace(root);ns.update(args=SimpleNamespace(case=case),out=out)
    block('scenario',ns,root);report=ns['r'];save=snapshot_writer(out,report);ns['save']=save
    primary=None
    try:
        report.update(current_context=context,current_producer=copy.deepcopy(c['producer']),native_card_validation_executed=False,transient_executed=False)
        save();block('prerequisites',ns,root)
        pinpath=out/'current-inputs.json';pp=out/'current-runtime.json'
        current_proof=dict(context=context,producer=c['producer'],files={k:dict(path=str(Path(v).absolute()),**file_pin(v))for k,v in paths.items()},descriptor=file_pin(source_path(root,INPUTS)))
        write_exclusive(pinpath,current_proof);write_exclusive(pp,runtime_proof)
        ns.update(model=Path(paths['model']).absolute(),contract=contract,planes=planes,proof=current_proof,pinpath=pinpath,pp=pp,lib=Path(runtime['lib']).absolute(),engine=Path(runtime['engine']).absolute())
        report['native_plane_source']=dict(path=str(Path(paths['planes']).absolute()),**file_pin(paths['planes']))
        report['models_source']=runtime_proof
        block('binding',ns,root);report['native_card_validation_executed']=True
        require(report['binding_controls']['equivalent_unit_spellings']==2 and len(report['binding_controls']['rejected'])==13,'all original actual binding controls')
        block('deck',ns,root);verify_projection(ns,records['derived-loaded-vector-projection.json'])
        extra=[Path(__file__).resolve(),source_path(root,CATALOG),source_path(root,INPUTS),Path(paths['composition']),Path(paths['planes']),Path(runtime['source_pin']),Path(runtime['models_summary']),pinpath,pp]
        extra += [source_path(root,name)for name in catalog(root)['files']]
        extra.append(source_path(root,c['transport_prerequisite']['path']))
        report['protected_inputs'].update({str(p):sha(p)for p in extra})
        require(all(sha(Path(p))==digest for p,digest in report['protected_inputs'].items()),'complete prepared source/model integrity')
        report.update(status=PREPARED_STATUS,sources_unchanged=True,transient_executed=False)
        prepared=dict(schema='nssoc-current-via2-m3-loaded-prepared-v1',context=context,case=case,paths={k:str(Path(v).absolute())for k,v in paths.items()},runtime={k:str(Path(v).absolute())for k,v in runtime.items()},report=report)
        write_exclusive(out/'prepared-state.json',prepared)
        plan=dict(argv=[str(ns['engine']),'-n','-b','bench.cir'],cwd=str(ns['native']),remove_environment_keys=['LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN'],environment=dict(SPICE_SCRIPTS=str(ns['native']),OMP_NUM_THREADS='1'),stdout=str(ns['native']/'native.log'),stderr='STDOUT',engine=file_pin(ns['engine']),prepared_state=file_pin(out/'prepared-state.json'),case=case,context=context)
        write_exclusive(out/'transient-command.json',plan)
        return dict(status=PREPARED_STATUS,context=context,plan=plan,report=copy.deepcopy(report))
    except BaseException as error:
        primary=error;preserve_phase_failure(report,error);raise
    finally:finish_report(out/'preparation-result.json',report,primary)

def measure_case(out,context,returncode,prepared_pin,root=ROOT):
    """Run complete frozen measurement body on runner-owned actual outputs.

    Host admission must separately bind actual supervised command/return code and
    preserve the full owned workspace. This library grants no execution authority.
    """
    context=actual_context(context);require(type(returncode)is int,'actual simulator return code')
    out=Path(out).absolute();require(out.resolve()==out and out.is_dir(),'existing unaliased case workspace')
    plan=json.loads((out/'transient-command.json').read_bytes());prepared=pinned_json(out/'prepared-state.json',prepared_pin)
    require(plan['prepared_state']==prepared_pin,'host-retained preparation pin')
    require(prepared['context']==plan['context']==context and prepared['case']==plan['case']=='nominal_late','exact prepared source/run/scenario')
    c,records,contract,planes=verify_current_inputs(prepared['paths'],root);verify_runtime(prepared['runtime'],root)
    expected_plan=dict(argv=[prepared['runtime']['engine'],'-n','-b','bench.cir'],cwd=str(out/'native'),remove_environment_keys=['LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN'],environment=dict(SPICE_SCRIPTS=str(out/'native'),OMP_NUM_THREADS='1'),stdout=str(out/'native'/'native.log'),stderr='STDOUT',engine=file_pin(prepared['runtime']['engine']),prepared_state=prepared_pin,case='nominal_late',context=context)
    require(plan==expected_plan,'exact actual transient command contract')
    report=prepared['report'];require(report['status']==PREPARED_STATUS and report['transient_executed']is False,'actual prepared-only input')
    primary=None;report['status']='RUNNING'
    try:
        require(all(sha(Path(p))==digest for p,digest in report['protected_inputs'].items()),'unchanged pre-transient inputs')
        ns=numerical_namespace(root);ns.update(args=SimpleNamespace(case='nominal_late'),out=out)
        block('scenario',ns,root)
        require(ns['offset']==report['data_offset_s']and ns['corner']==report['corner']and ns['bits']==report['source_bits'],'unchanged frozen scenario')
        bound=ns['bind_native'](Path(prepared['paths']['model']).read_text(),contract,planes)
        require(bound==report['binding']and bound['groups']['npn13g2']==report['devices']and bound['groups']['sg13_lv_nmos']==report['mos_devices']and bound['groups']['cap_cmim']==report['native_caps'],'complete actual rebound group identity')
        report['transient_executed']=True;report['status']='RUNNING_ACTUAL_WHOLE_WIRE_TRANSIENT'
        ns.update(r=report,save=snapshot_writer(out,report),native=out/'native',proc=SimpleNamespace(returncode=returncode),bound=bound,devices=bound['groups']['npn13g2'],mos=bound['groups']['sg13_lv_nmos'],caps=bound['groups']['cap_cmim'],vectors=report['vectors'],protected=report['protected_inputs'])
        verify_projection(ns,records['derived-loaded-vector-projection.json'])
        block('measurement',ns,root)
        return copy.deepcopy(report)
    except BaseException as error:
        primary=error;preserve_phase_failure(report,error);raise
    finally:finish_report(out/'measurement-result.json',report,primary)

def main():raise SystemExit('Native/wave execution is disabled in this standalone source-only core; use a separately reviewed current-source host.')
if __name__=='__main__':main()
