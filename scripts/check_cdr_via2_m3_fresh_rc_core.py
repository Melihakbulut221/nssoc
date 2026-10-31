#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted full-census synthetic numerical controls, never native CAD evidence."""
import ast,copy,json,os,shutil,subprocess,sys,tempfile,traceback
from pathlib import Path
import cdr_via2_m3_fresh_rc_core as c
import cdr_via2_m3_fresh_rc_fixtures as f
ROOT=Path(__file__).resolve().parents[1]
BRANCH='codex/cdr-via2-m3-fresh-rc-core'
MANIFEST='scripts/cdr-via2-m3-fresh-rc-core-pins.json'
RECORDS=[]

def source_guard():
    e=os.environ
    c.require(e.get('GITHUB_ACTIONS')=='true'and e.get('RUNNER_ENVIRONMENT')=='github-hosted'and e.get('GITHUB_JOB')=='source-controls','hosted source-only job')
    c.require(e.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'and e.get('GITHUB_EVENT_NAME')=='workflow_dispatch'and e.get('GITHUB_REF')=='refs/heads/'+BRANCH,'exact manual source branch')
    c.require(e.get('GITHUB_RUN_ATTEMPT')=='1'and e.get('APPROVED_SOURCE')==e.get('GITHUB_SHA'),'exact approved source/no rerun')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();c.require(head==e['GITHUB_SHA'],'actual checkout')
    raw=c.regular(ROOT,MANIFEST).read_bytes();c.require(raw==subprocess.check_output(['git','show',head+':'+MANIFEST],cwd=ROOT),'immutable manifest')
    manifest=json.loads(raw);c.require(manifest['native_authority']is False,'source-only manifest')
    for path,pin in manifest['files'].items():
        data=c.regular(ROOT,path).read_bytes();c.require(dict(bytes=len(data),sha256=c.hashlib.sha256(data).hexdigest())==pin,'protected source '+path)
    cfg=json.loads(c.regular(ROOT,c.CONFIG).read_text());c.require(all(cfg[k]is False for k in ('native_execution_authorized','rc_execution_authorized','wave_execution_authorized')),'native disabled config')
    return dict(source=head,run_id=int(e['GITHUB_RUN_ID']),attempt=1)

def record(name,**detail):
    c.require(name not in {r['name']for r in RECORDS},'unique control');RECORDS.append(dict(name=name,passed=True,**detail));print('PASS '+name,flush=True)

def reject(name,call):
    try:call()
    except (ValueError,AssertionError,KeyError,TypeError,FileNotFoundError,SyntaxError)as error:record(name,expected_refusal=True,error=repr(error))
    else:raise AssertionError('Accepted '+name)

def definition_controls():
    definitions=0
    for key,item in c.catalog(ROOT)['sources'].items():
        c.source(ROOT,key)
        if item['definitions']:
            _,nodes=c.checked_nodes(ROOT,key,list(item['definitions']));definitions+=len(nodes)
    for name in c.catalog(ROOT)['blocks']:c.block_nodes(ROOT,name)
    c.require(definitions==30 and len(c.catalog(ROOT)['blocks'])==9,'complete immutable definition/block catalog')
    record('complete_16_sources_30_definitions_9_exact_main_blocks',definitions=definitions,blocks=9)
    reject('unapproved_historical_main',lambda:c.functions(ROOT,'binding',['main'],{}))
    reject('standalone_native_entry_closed',c.authorize_native)
    reject('namespace_native_entry_closed',c.binding_namespace.authorize_native)
    reject('definition_global_collision',lambda:c.functions(ROOT,'intrinsic',['require'],dict(require=lambda *_:None)))

def packet(context,binding_result):
    report=copy.deepcopy(binding_result['r']);report['binding']=copy.deepcopy(binding_result['binding'])
    report.update(source_head=context['source'],status=c.binding_namespace.BINDING_PASS,sources_unchanged=True,explicit_synthetic_fixture=True,native_simulation_passed=False,qualified_pex=False,wire_rc_included=False,full_phy_accepted=False,closed_loop=False)
    summary=c.binding_namespace.encode(report)
    descriptor=dict(run=context['run_id'],source_head=context['source'],summary_sha256=c.binding_namespace.pin(summary)['sha256'],report=report)
    data=dict(summary=summary,descriptor=c.binding_namespace.encode(descriptor))
    return data,c.binding_namespace.pin(data['descriptor']),descriptor

def full_numerical_controls(context,tmp):
    auxiliary=c.composition_and_order_controls(ROOT)
    record('original_noncascading_count_and_both_order_control_sets',**auxiliary)
    b=tmp/'binding';fixture=f.synthetic_inputs(b,tmp/'technology')
    result=c.binding_validate(ROOT,b,tmp/'technology');binding=result['binding'];proof=result['r']
    c.require(binding['native_ports']==f.PORTS,'actual SPICE port order rather than reversed fixture plan')
    c.require(len(binding['devices'])==500 and len(proof['controls'])==14 and len(proof['native_contact_comparisons'])==221,'full synthetic binding')
    record('full_500_binding_actual_schema_and_25_port_order',faults=proof['controls'],target_controls=proof['target_length_controls'],contact_controls=proof['contact_model_controls'],synthetic_contact_comparisons=len(proof['native_contact_comparisons']),native_pdk_executed=False)
    data,dpin,descriptor=packet(context,result);provider,intrinsic=c.current_binding(ROOT,lambda:data,context,dpin)
    c.require(provider.stage_report('binding')['binding']==binding,'complete real-schema current provider')
    record('actual_frozen_build_to_current_binding_provider',devices=500,explicit_synthetic_fixture=True)
    wp=tmp/'wire-stage';w=wp/'wire';w.mkdir(parents=True);counts=f.raw_fixture(w,fixture,binding,False)
    methods=c.derive_wire_methods(ROOT,wp);raw=c.wire_audit(ROOT,w,methods)
    c.require(counts['R']==raw['audit']['actual_exported_resistors']and counts['C']==raw['audit']['actual_exported_capacitors'],'actual synthetic R/C counts')
    record('complete_wire_fixture_13_unchanged_raw_corruptions',counts=counts,controls=raw['controls'])
    mim=tmp/'mim';variants={}
    order=c.functions(ROOT,'cap_order',['rows','capkey','reorder','controls'],c.common(ROOT))
    reverse=c.functions(ROOT,'reverse',['reverse'],dict(c.common(ROOT),reorder=order.reorder)).reverse
    for variant in ('precise','precise_reversed'):
        out=mim/variant;wire=out/'wire';wire.mkdir(parents=True)
        counts=f.raw_fixture(wire,fixture,binding,True)
        (out/'source/wire').mkdir(parents=True)
        for name in ('audit-rc48.py','mutations48.py'):shutil.copyfile(w/name,out/'source/wire'/name)
        f.save(out/'model-binding/binding.json',binding);f.save(out/'source/wire/native05/result.json',fixture['geometry'])
        if variant=='precise_reversed':
            path=wire/'rc03/pump_wires.ext';before=path.read_text();after,reversal=reverse(before);c.require(after!=before,'actual independent enumeration reversal')
            path.write_text(after);f.save(path.with_suffix('.order-proof.json'),reversal)
        capture=c.capture_finish(ROOT,out,dict(status='NATIVE_COMPLETE_AWAITING_RC_AUDIT',returncode=0,explicit_synthetic_fixture=True),binding)
        capture.update(native_order_variant=variant,model_binding_source=dict(run=context['run_id'],summary_sha256=descriptor['summary_sha256']),sources_unchanged=True,explicit_synthetic_fixture=True,native_extraction_executed=False)
        audit=c.mim_audit(ROOT,out,capture,lambda:data,context,dpin)
        c.require(len(capture['controls'])==5 and len(audit['wire_controls']['cases'])==13 and len(audit['intrinsic_controls'])==9,'complete per-order control census')
        variants[variant]=dict(capture=capture,audit=audit)
        record(variant+'_7_mim_5_capture_13_raw_9_intrinsic_corruptions',counts=counts,capture_controls=capture['controls'],raw_controls=audit['wire_controls'],intrinsic_controls=audit['intrinsic_controls'])
    composed=c.compare_and_compose(ROOT,mim,lambda:data,context,dpin,variants)
    record('both_native_order_numerical_records_and_21_composition_corruptions',composition=composed['composition'],order_equivalence=composed['native_order_equivalence'],reversal=composed['reversal'],native_extraction_executed=False)
    reject('missing_second_order',lambda:c.compare_and_compose(ROOT,tmp/'never-created',lambda:data,context,dpin,dict(precise=variants['precise'])))
    stale=copy.deepcopy(context);stale['run_id']+=1
    reject('stale_current_binding',lambda:c.current_binding(ROOT,lambda:data,stale,dpin)[0].stage_report('binding'))
    negative=copy.deepcopy(variants);negative['precise']['audit']['intrinsic_controls']=negative['precise']['audit']['intrinsic_controls'][:-1]
    reject('missing_intrinsic_control',lambda:c.compare_and_compose(ROOT,tmp/'never-created',lambda:data,context,dpin,negative))
    return dict(binding=proof,wire=raw,variants=variants,composition=composed)

def copy_and_command_controls(tmp):
    source=tmp/'copy-source';source.mkdir();(source/'one.txt').write_bytes(b'one\n');(source/'nested').mkdir();(source/'nested/two.json').write_bytes(b'{"fixture":true}\n')
    pins={p.relative_to(source).as_posix():dict(bytes=p.stat().st_size,sha256=c.sha(p))for p in source.rglob('*')if p.is_file()}
    observed=c.copy_exact_tree(source,tmp/'copy-destination',pins);c.require(observed==pins,'complete independent copy fixture')
    record('exclusive_full_input_copy_preserves_all_bytes',files=len(pins))
    reject('copy_existing_destination',lambda:c.copy_exact_tree(source,tmp/'copy-destination',pins))
    reject('copy_nested_source_destination',lambda:c.copy_exact_tree(source,source/'child',pins))
    reject('copy_changed_source',lambda:c.copy_exact_tree(source,tmp/'copy-bad-sha',{**pins,'one.txt':dict(bytes=4,sha256='0'*64)}))
    reject('copy_missing_manifest_member',lambda:c.copy_exact_tree(source,tmp/'copy-incomplete',{'one.txt':pins['one.txt']}))
    linked=tmp/'linked-source';linked.symlink_to(source,target_is_directory=True)
    reject('copy_linked_root',lambda:c.copy_exact_tree(linked,tmp/'copy-linked',pins))
    (source/'link').symlink_to(source/'one.txt')
    reject('copy_linked_member',lambda:c.copy_exact_tree(source,tmp/'copy-linked-member',pins));(source/'link').unlink()
    base=tmp/'command-repo';out=base/'hw/soc/out/cloud-cdr-via2-m3-fresh-rc';entry=base/'scripts/cdr_via2_m3_fresh_rc_native.py'
    plan=c.command_plan(base,out,'/fixture/verified.AppImage','/usr/bin/python3',entry)
    c.require(len(plan['commands'])==13 and plan['native_authority']is False,'complete nonexecuting command contract')
    c.require(plan['commands'][0]['argv']==['/fixture/verified.AppImage','python',str(entry),'--phase','binding-export','--out',str(out)],'independent native-export argv')
    c.require([x['label']for x in plan['commands']]==['binding-export','binding-validate','wire-extract','wire-audit','mim-generate-precise','mim-extract-precise','mim-finish-precise','mim-audit-precise','mim-generate-precise_reversed','mim-extract-precise_reversed','mim-finish-precise_reversed','mim-audit-precise_reversed','compose'],'complete independent phase order')
    c.require(all('--native-export'not in x['argv']and '--generate'not in x['argv']for x in plan['commands']),'no historical CLI recursion')
    record('explicit_13_command_contract_without_execution',plan=plan)
    reject('wrong_owned_output',lambda:c.command_plan(base,tmp/'wrong','/fixture/app','/usr/bin/python3',entry))
    reject('historical_entry_rejected',lambda:c.command_plan(base,out,'/fixture/app','/usr/bin/python3',base/'scripts/cloud_cdr_current_eight_drain_fresh_binding.py'))
    reject('relative_runtime_rejected',lambda:c.command_plan(base,out,'relative','/usr/bin/python3',entry))
    early=tmp/'early-wire';early.mkdir()
    reject('raw_audit_early_failure',lambda:c.wire_audit(ROOT,early,{}))
    c.require(json.loads((early/'core-observations.json').read_text())=={},'actual early scalar failure preserved')
    record('early_raw_failure_observation_persisted')

def main():
    out=ROOT/'rc-core-source-controls';out.mkdir(exist_ok=False);result=dict(status='RUNNING',scope='SYNTHETIC_SOURCE_NUMERICAL_CONTROLS_ONLY',native_acquired=False,native_executed=False,physical_accepted=False,qualified_pex=False,full_phy_accepted=False,records=RECORDS)
    try:
        result['context']=source_guard();result['python_runtime']=dict(version=sys.version,implementation=sys.implementation.name,ast_empty_fields=c.stable_ast_dump(ast.parse('def f(): pass').body[0]));definition_controls()
        with tempfile.TemporaryDirectory(prefix='nssoc-source-fixture-')as temporary:
            copy_and_command_controls(Path(temporary));result['full_numerical_fixture']=full_numerical_controls(result['context'],Path(temporary))
        result.update(status='PASS_COMPLETE_SYNTHETIC_NUMERICAL_SOURCE_CONTROLS_ONLY',passed=len(RECORDS),failed=0)
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR',error=repr(error),traceback=traceback.format_exc(),passed=len(RECORDS),failed=1);raise
    finally:(out/'result.json').write_bytes(c.encode(result))

if __name__=='__main__':main()
