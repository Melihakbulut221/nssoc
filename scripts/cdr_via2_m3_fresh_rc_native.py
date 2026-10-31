#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact-current phase adapter. Authority belongs only to the separately reviewed host.

No historical main, environment substitution, input acquisition or implicit retry.
The pure report validator also supports explicitly labelled synthetic source fixtures;
validate_complete always requires actual host admission and actual phase receipts.
"""
import argparse,copy,hashlib,json,os,subprocess,traceback
from pathlib import Path
import cdr_via2_m3_fresh_rc_admission as a
import cdr_via2_m3_fresh_rc_core as core
import cdr_via2_m3_fresh_rc_runtime as runtime

ROOT=Path(__file__).resolve().parents[1]
STATUS='PASS_CURRENT_VIA2_M3_FRESH_RC_NUMERICAL_QUALIFICATION_REQUIRES_LOADED_WAVES'
ACTUAL='ACTUAL_AUTHORIZED_NATIVE_PHASE'
SYNTHETIC='SOURCE_ONLY_SYNTHETIC_PHASE_FIXTURE'
VARIANTS=('precise','precise_reversed')
PHASES=('prepare','binding-export','binding-validate','wire-audit','mim-generate','mim-finish','mim-audit','compose')
LABELS=('prepare','binding-export','binding-validate','wire-audit','mim-generate-precise','mim-finish-precise','mim-audit-precise','mim-generate-precise_reversed','mim-finish-precise_reversed','mim-audit-precise_reversed','compose')
REPORT_DIR='native-phase-reports'
SOURCE_PATHS=('scripts/cdr_via2_m3_fresh_rc_native.py','scripts/cdr_via2_m3_fresh_rc_core.py','scripts/cdr-via2-m3-fresh-rc-core-catalog.json','scripts/cdr_via2_m3_fresh_rc_namespaces.py')
require=core.require;encode=core.encode

def read(path):return core.binding_namespace.decode(Path(path).read_bytes())
def pin(path):
    path=Path(path);require(path.is_file()and not path.is_symlink(),'regular phase file')
    return dict(bytes=path.stat().st_size,sha256=core.sha(path))
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    require(not path.is_symlink()and not any(p.is_symlink()for p in path.parents),'unlinked report path')
    with path.open('xb')as stream:stream.write(encode(value));stream.flush();os.fsync(stream.fileno())
def context_key(ctx):return {k:ctx[k]for k in ('source','run_id','attempt')}
def source_pins(root):return {name:pin(core.regular(root,name))for name in SOURCE_PATHS}
def label(phase,variant):
    require(phase in PHASES,'known phase')
    require((phase.startswith('mim-')and variant in VARIANTS)or(not phase.startswith('mim-')and variant is None),'exact phase variant')
    return phase+('-'+variant if variant else'')
def inventory(out):
    out=Path(out);require(not out.is_symlink(),'unlinked output')
    rows={}
    for path in out.rglob('*'):
        require(not path.is_symlink(),'no linked output member')
        if path.is_file():
            relative=path.relative_to(out).as_posix()
            if not relative.startswith(REPORT_DIR+'/'):rows[relative]=pin(path)
        else:require(path.is_dir(),'regular output tree')
    return rows

def numerical_inventory(out):
    rows={};out=Path(out)
    for name in ('binding','wire-stage','mim'):
        target=out/name
        if target.exists():
            for path,p in inventory(target).items():rows[name+'/'+path]=p
    for name in ('preparation.json','count-order-controls.json','prepare-phase.json','precision-result.json'):
        if(out/name).exists():rows[name]=pin(core.regular(out,name))
    return rows

def required_outputs(name):
    fixed={'prepare':['preparation.json','count-order-controls.json','prepare-phase.json'],'binding-export':['binding/native-devices.json','binding/native-contact-oracle.json'],'binding-validate':['binding/binding.json','binding/pd500-compact.spice','binding/binding-core-observations.json','binding/result.json','binding/current-binding-descriptor.json'],'wire-audit':['wire-stage/result.json','wire-stage/wire/audit.json','wire-stage/wire/core-observations.json'],'compose':['precision-result.json','mim/composition/composition.json','mim/composition/pd500-mim-wire.spice','mim/composition/compose.py','mim/composition/verified-wire-projection.spice']}
    if name in fixed:return fixed[name]
    for variant in VARIANTS:
        base='mim/'+variant+'/'
        if name=='mim-generate-'+variant:return [base+n for n in ('generate-phase.json','native-binding.json','method-derivation.json','wire/anchors08.json','wire/native05/wires.gds','wire/run-rc01.py')]
        if name=='mim-finish-'+variant:return [base+'result.json']
        if name=='mim-audit-'+variant:return [base+'audit-stage/result.json',base+'intrinsic-audit-controls.json']
    raise ValueError('unknown receipt output contract')

def verify_receipt(out,name,ctx,pins,scope=ACTUAL):
    require(name in LABELS,'known receipt');row=read(core.regular(out,REPORT_DIR+'/'+name+'.json'))
    require(row['schema']=='cdr-via2-m3-fresh-rc-phase-v1'and row['label']==name and row['status']=='PASS_PHASE','complete successful phase receipt')
    require(row['context']==context_key(ctx)and row['source_pins']==pins and row['execution_scope']==scope,'current phase source/context/scope')
    require(type(row['outputs'])is dict and row['outputs'],'phase produced durable evidence')
    require(set(required_outputs(name))<=set(row['outputs']),'required phase reports missing from receipt')
    require(type(row['inputs'])is dict,'complete numerical input inventory')
    for path,expected in {**row['inputs'],**row['outputs']}.items():require(pin(core.regular(out,path))==expected,'phase input/output changed '+path)
    return row

def lifecycle(out,name,ctx,pins,scope,call,before_guard,after_guard):
    """Preserve first failure, including failed pre/post guards, without hiding save failure."""
    require(name in LABELS and scope in (ACTUAL,SYNTHETIC),'explicit lifecycle scope')
    destination=Path(out)/REPORT_DIR/(name+'.json')
    require(not destination.exists()and not destination.is_symlink(),'phase may not be repeated or overwritten')
    record=dict(schema='cdr-via2-m3-fresh-rc-phase-v1',label=name,context=context_key(ctx),source_pins=pins,execution_scope=scope,status='RUNNING',outputs={})
    primary=None;before={};observe=numerical_inventory if scope==ACTUAL else inventory
    try:
        before_guard();before=observe(out);record['inputs']=before;record['result']=call();after_guard()
        after=observe(out)
        for path,expected in before.items():require(path in after and after[path]==expected,'previous phase/input bytes changed '+path)
        record['outputs']={path:p for path,p in after.items()if path not in before}
        require(record['outputs'],'phase produced no new durable output')
        if scope==ACTUAL:require(set(required_outputs(name))<=set(record['outputs']),'actual phase required report outputs')
        record['status']='PASS_PHASE'
    except BaseException as error:
        primary=error;record.update(status='FAIL_PHASE',error=repr(error),traceback=traceback.format_exc())
        try:record['observed_after_failure']=observe(out)
        except BaseException as observe_error:record['observation_error']=repr(observe_error)
    try:write(destination,record)
    except BaseException as save_error:
        print('UNSAVED_FRESH_RC_PHASE '+encode(dict(record,save_error=repr(save_error))).decode(),flush=True)
        if primary is None:primary=save_error
    if primary is not None:raise primary
    return record

def binding_report(result,ctx):
    report=copy.deepcopy(result['r']);report['binding']=copy.deepcopy(result['binding'])
    report.update(source_head=ctx['source'],status=core.binding_namespace.BINDING_PASS,sources_unchanged=True,native_simulation_passed=False,qualified_pex=False,wire_rc_included=False,full_phy_accepted=False,closed_loop=False)
    return report

def save_binding(out,result,ctx):
    report=binding_report(result,ctx);summary=Path(out)/'binding/result.json';write(summary,report)
    descriptor=dict(run=ctx['run_id'],source_head=ctx['source'],summary_sha256=pin(summary)['sha256'],report=report)
    write(Path(out)/'binding/current-binding-descriptor.json',descriptor)
    packet,dp,identity=current_packet(out,ctx);core.current_binding(ROOT,packet,context_key(ctx),dp)[0].stage_report('binding')
    return dict(identity=identity,descriptor_pin=dp)

def current_packet(out,ctx):
    out=Path(out);descriptor=core.regular(out,'binding/current-binding-descriptor.json');summary=core.regular(out,'binding/result.json')
    dp=pin(descriptor)
    def packet():return dict(descriptor=descriptor.read_bytes(),summary=summary.read_bytes())
    bound=core.binding_namespace.CurrentBinding(packet,context_key(ctx),dp);bound.stage_report('binding')
    d=read(descriptor);return packet,dp,dict(run=d['run'],source=d['source_head'],summary_sha256=d['summary_sha256'])

def verify_runtime_cache(out):
    base=Path(out)/'runtime-inputs';r=read(core.regular(base,'result.json'));cfg,records=runtime.records()
    require(r['status']=='PASS_AUTHENTICATED_RUNTIME_INPUTS_ONLY_NO_EXTRACTION'and r['all_original_model_pins_verified']is True,'authenticated actual runtime acquisition')
    for name in ('frozen_layout','models','magic'):
        expected=r[name]['complete_extracted_members'];actual=inventory(base/name)
        require(actual==expected,'complete authenticated cache bytes '+name)
        runtime.verify_manifest(base/name,actual)
    precise={name:pin(core.regular(base/'precise',name))for name in cfg['precise']['selected']}
    expected={name:records['precise-summary.json']['outputs'][name]if name!='result.json'else next(p['sha256']for n,p in cfg['records'].items()if n.endswith('/precise-summary.json'))for name in cfg['precise']['selected']}
    require(set(inventory(base/'precise'))==set(precise)and all(precise[n]['sha256']==expected[n]for n in precise),'exact selected precise cache')
    require(read(base/'precise/result.json')==records['precise-summary.json'],'precise runtime report bytes/provenance')
    from build_cdr500_cleaned_native_models import MODEL_PINS
    require(read(base/'model-pins.json')==MODEL_PINS,'all model pin declaration')
    for name,digest in MODEL_PINS.items():require(core.sha(core.regular(ROOT/'pdk',name))==digest,'current model bytes '+name)
    for name,p in r['frozen_layout']['manifest']['files'].items():require(pin(core.regular(ROOT,name))==p,'all restored frozen runtime bytes '+name)
    return cfg,records,r

def copy_cache(out,destination,name):
    _,_,r=verify_runtime_cache(out);source=Path(out)/'runtime-inputs'/name
    members=r['magic']['complete_extracted_members']if name=='magic'else inventory(source)
    return runtime.copy_owned(source,Path(destination),members)

def extraction_result(out,relative):
    value=read(core.regular(out,relative))
    require(value['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT'and value['returncode']==0,'successful exact native extraction')
    return value

def rejected(rows,count,key='rejected'):
    require(type(rows)is list and len(rows)==count,'complete control count')
    require(all(row[key]is True for row in rows),'every fault rejected')

def raw_gates(audit,controls,mim=False):
    require(audit['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY','strict full raw audit')
    require(audit['original_devices']==500 and audit['geometry_probes']==978 and audit['public_ports']==25 and audit['physical_wire_components']==113,'actual observed native census')
    require(all(audit[k]is True for k in ('complete_collapsed_capacitance_conserved','geometry_conductor_ownership_exact','native_export_r_edge_value_multiset_exact','every_native_mutual_attachment_and_value_preserved','every_native_point_ground_capacitance_preserved','no_intrinsic_alias_edges_inserted_in_resistance_graph')),'complete conductor/branch/capacitance coverage')
    require(audit['full_pex_qualified']is False,'raw audit is not qualified PEX')
    for key in ('actual_exported_resistors','actual_exported_capacitors'):require(type(audit[key])is int and audit[key]>0,'positive measured R/C counts')
    require(len(controls['cases'])==13 and all(row['rejected_by']for row in controls['cases']),'all thirteen raw corruption refusals')
    if mim:require(audit['native_mim_intrinsic']['devices']==7,'all seven intrinsic MIM devices')

def operate(phase,variant,out,ctx):
    out=Path(out);current=Path(a.producer.CURRENT_ROOT)
    if phase=='prepare':
        verify_runtime_cache(out);r=core.prepare_current_view(ROOT,current,out)
        r['runtime_copy']=copy_cache(out,out/'wire-stage/magic-cloud','magic')
        write(out/'count-order-controls.json',core.composition_and_order_controls(ROOT))
        write(out/'prepare-phase.json',r);return r
    if phase=='binding-export':
        core.binding_native_export(ROOT,out/'binding')
        return dict(native_devices=pin(out/'binding/native-devices.json'),contact_oracle=pin(out/'binding/native-contact-oracle.json'))
    if phase=='binding-validate':
        result=core.binding_validate(ROOT,out/'binding');require(result['binding']['native_ports']==read(ROOT/core.CONFIG)['canonical_view']['port_order'],'actual semantic port order')
        return save_binding(out,result,ctx)
    if phase=='wire-audit':
        extraction=extraction_result(out,'wire-stage/wire/rc03/result.json');preparation=read(out/'preparation.json')
        result=core.wire_audit(ROOT,out/'wire-stage/wire',preparation['wire_methods']);raw_gates(result['audit'],result['controls'])
        result.update(method_adaptations=preparation['wire_methods'],extraction=extraction,context=context_key(ctx),sources_unchanged=True)
        write(out/'wire-stage/result.json',result);return result
    packet,dp,identity=current_packet(out,ctx);bound=core.current_binding(ROOT,packet,context_key(ctx),dp)[0].stage_report('binding')
    if phase=='mim-generate':
        target=out/'mim'/variant
        preparation=core.prepare_mim_variant(ROOT,current,out,variant,dict(binding=bound['binding'],identity=identity),read(out/'wire-stage/result.json'))
        copies=dict(magic=copy_cache(out,target/'source/magic-cloud','magic'),precise=copy_cache(out,target/'producer','precise'))
        cfg,records,_=verify_runtime_cache(out);core.prepare_capture_runtime(ROOT,target,records['precise-summary.json'])
        command=['ldd',str(target/'producer/precise-source/magic/tclmagic.so')]
        deps=subprocess.run(command,capture_output=True,timeout=60,check=False)
        for suffix,data in (('stdout',deps.stdout),('stderr',deps.stderr)):
            with(target/('precise-ldd.'+suffix)).open('xb')as stream:stream.write(data)
        write(target/'precise-ldd.json',dict(argv=command,returncode=deps.returncode,stdout=pin(target/'precise-ldd.stdout'),stderr=pin(target/'precise-ldd.stderr')))
        require(deps.returncode==0 and b'not found'not in deps.stdout+deps.stderr,'complete precise runtime dependency resolution')
        core.capture_generate(ROOT,target);core.derive_capture_methods(ROOT,target,variant)
        r=dict(preparation=preparation,copies=copies,native_binding=read(target/'native-binding.json'),method=read(target/'method-derivation.json'),model_binding_source=identity,context=context_key(ctx))
        write(target/'generate-phase.json',r);return r
    if phase=='mim-finish':
        target=out/'mim'/variant;capture=extraction_result(out,'mim/'+variant+'/wire/rc03/result.json')
        result=core.capture_finish(ROOT,target,capture,bound['binding'])
        result.update(status='PASS_PD500_MIM_AWARE_NATIVE_CAPTURE_AND_INTRINSIC_BINDING_REQUIRES_RAW_RC_AUDIT',native_order_variant=variant,model_binding_source=identity,source_head=ctx['source'],context=context_key(ctx),sources_unchanged=True,native_extraction_executed=True,qualified_pex=False,full_phy_accepted=False,closed_loop=False,capture=capture)
        write(target/'result.json',result);return result
    if phase=='mim-audit':
        target=out/'mim'/variant;result=core.mim_audit(ROOT,target,read(target/'result.json'),packet,context_key(ctx),dp)
        result.update(context=context_key(ctx),sources_unchanged=True,qualified_pex=False,full_phy_accepted=False)
        write(target/'audit-stage/result.json',result);return result
    require(phase=='compose','all phase branches explicit')
    variants={v:dict(capture=read(out/'mim'/v/'result.json'),audit=read(out/'mim'/v/'audit-stage/result.json'))for v in VARIANTS}
    result=core.compare_and_compose(ROOT,out/'mim',packet,context_key(ctx),dp,variants)
    result.update(context=context_key(ctx),sources_unchanged=True,both_native_orders_verified=True,native_rc_and_device_records_equal_in_both_orders=True,qualified_pex=False,full_phy_accepted=False,loaded_simulation_passed=False)
    write(out/'precision-result.json',result);return result

def validate_complete_files(out,ctx,pins,ports,scope):
    """Pure byte/report validator. The actual caller pins scope and runs host guards."""
    out=Path(out);require(scope in (ACTUAL,SYNTHETIC),'explicit qualification scope')
    receipts={name:verify_receipt(out,name,ctx,pins,scope)for name in LABELS}
    require({p.name for p in(out/REPORT_DIR).iterdir()}=={name+'.json'for name in LABELS},'all and only eleven terminal phase receipts')
    packet,dp,identity=current_packet(out,ctx);binding=core.binding_namespace.CurrentBinding(packet,context_key(ctx),dp).stage_report('binding')
    require(binding['binding']==read(out/'binding/binding.json')and binding['binding']['native_ports']==ports,'actual current binding and port order')
    auxiliary=read(out/'count-order-controls.json')
    require(auxiliary['count_derivation']['status']=='PASS_NONCASCADING_MEASURED_COUNT_DERIVATION'and len(auxiliary['count_derivation']['positive_collision_cases'])==len(auxiliary['count_derivation']['rejected'])==4,'original measured-count controls')
    require(auxiliary['order_controls']==auxiliary['reverse_controls']['rejected']==['missing','value','endpoint','node']and auxiliary['reverse_controls']['reversal_roundtrip']is True,'original order/reversal controls')
    wire=read(out/'wire-stage/result.json');raw_gates(wire['audit'],wire['controls']);extraction_result(out,'wire-stage/wire/rc03/result.json')
    precise=read(out/'precision-result.json');require(precise['context']==context_key(ctx)and precise['sources_unchanged']is precise['both_native_orders_verified']is precise['native_rc_and_device_records_equal_in_both_orders']is True,'complete current precision result')
    require(precise['qualified_pex']is precise['full_phy_accepted']is precise['loaded_simulation_passed']is False,'precision scope retained')
    require(set(precise['variants'])==set(VARIANTS),'both complete independent order results')
    counts=[]
    for variant in VARIANTS:
        capture=read(out/'mim'/variant/'result.json');audit=read(out/'mim'/variant/'audit-stage/result.json')
        require(precise['variants'][variant]==dict(capture=capture,audit=audit),'complete original order reports preserved')
        require(capture['native_order_variant']==variant and capture['model_binding_source']==identity,'current capture binding/run/order')
        require(capture['context']==audit['context']==context_key(ctx)and capture['sources_unchanged']is audit['sources_unchanged']is True,'current order source context')
        require(capture['status']=='PASS_PD500_MIM_AWARE_NATIVE_CAPTURE_AND_INTRINSIC_BINDING_REQUIRES_RAW_RC_AUDIT','completed capture status')
        rejected(capture['controls'],5);raw_gates(audit['audit'],audit['wire_controls'],True);rejected(audit['intrinsic_controls'],9)
        measured=capture['intrinsic_capture_binding'];require(measured['R']==audit['audit']['actual_exported_resistors']and measured['C']==audit['audit']['actual_exported_capacitors']and len(measured['native_mim_devices'])==7,'same measured complete R/C/seven native MIM')
        require(audit['intrinsic_binding_source']==dict(run=identity['run'],summary_sha256=identity['summary_sha256']),'current intrinsic binding')
        extraction_result(out,'mim/'+variant+'/wire/rc03/result.json');counts.append(dict(devices=500,R=measured['R'],C=measured['C']))
    require(counts[0]==counts[1],'both measured R/C counts')
    for name,keys in [('native_order_equivalence',('original_order_restored','symmetric_endpoint_value_multiset_exact','non_coupling_records_unchanged')),('reversal',('reversed_enumeration','symmetric_endpoint_value_multiset_exact','non_coupling_records_unchanged'))]:require(all(precise[name][key]is True for key in keys),'actual full native order equivalence '+name)
    composition=precise['composition'];require(composition['status']=='PASS_PD500_FRESH_MIM_COMPOSITION_AND21_CONTROLS_REQUIRES_LOADED_WAVES','complete composition status');rejected(composition['controls'],21)
    contract=read(out/'mim/composition/composition.json');require(composition['contract']==contract and contract['counts']==counts[0],'actual composition contract and measured R/C')
    require(contract['interface']==ports+['wire_cref']and contract['intrinsic_mim_models_in_final_netlist']==7,'actual semantic interface and seven MIM')
    require(contract['all_raw_wire_tokens_preserved']is contract['explicit_mim_device_estimate_double_count_removed']is True and contract['qualified_pex']is False,'all branches/one-copy intrinsic scope')
    require(composition['binding_summary_sha256']==identity['summary_sha256'],'composition uses current binding')
    return dict(status=STATUS if scope==ACTUAL else'PASS_SYNTHETIC_PHASE_REPORT_VALIDATION_ONLY',execution_scope=scope,context=context_key(ctx),fresh_RC_pipeline_complete=scope==ACTUAL,source_pins=pins,binding=identity,counts=counts[0],phase_receipts={name:pin(out/REPORT_DIR/(name+'.json'))for name in LABELS},qualified_pex=False,electrical_accepted=False,full_phy_accepted=False,loaded_simulation_passed=False)

def authorized(out,ctx):
    require(ctx==a.context(os.environ),'actual current phase environment')
    require(Path(out)==a.OUT and not Path(out).is_symlink(),'exact fresh output root')
    c,p=a.source_guard(ctx);a.native_preflight(Path(out)/'preflight.json',ctx,c,p)
    return c,p

def validate_complete(out,ctx):
    authorized(out,ctx);verify_runtime_cache(out);core.current_view_proof(ROOT,Path(a.producer.CURRENT_ROOT))
    result=validate_complete_files(out,ctx,source_pins(ROOT),read(ROOT/core.CONFIG)['canonical_view']['port_order'],ACTUAL)
    authorized(out,ctx);return result

def run_phase(phase,variant,out,ctx):
    name=label(phase,variant);require(Path(out)==a.OUT and not Path(out).is_symlink(),'exact native phase output')
    pins=source_pins(ROOT);index=LABELS.index(name)
    def guard():
        authorized(out,ctx)
        for previous in LABELS[:index]:verify_receipt(out,previous,ctx,pins,ACTUAL)
        verify_runtime_cache(out)
    return lifecycle(out,name,ctx,pins,ACTUAL,lambda:operate(phase,variant,out,ctx),guard,guard)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=PHASES,required=True);parser.add_argument('--variant',choices=VARIANTS);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    run_phase(args.phase,args.variant,args.out,a.context(os.environ))

if __name__=='__main__':main()
