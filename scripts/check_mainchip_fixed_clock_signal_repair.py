#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted structural/native-API-shape and actual wrapper controls; no CAD or saved archive."""
import ast,copy,json,os,sys,tempfile,traceback,types
from pathlib import Path
from unittest.mock import patch
import mainchip_original_clock_restoration as c
import mainchip_fixed_clock_signal_repair as s
import cloud_mainchip_fixed_clock_signal_repair as driver
from check_mainchip_original_clock_restoration_driver import emit
# Explicit stub only for importing native glue and exercising its dbGuide API shape.
with patch.dict(sys.modules,{'odb':types.SimpleNamespace(dbDatabase=types.SimpleNamespace(destroy=lambda db:None))}):
    import mainchip_fixed_clock_signal_repair_native as native
OUT=c.ROOT/'cloud-mainchip-fixed-clock-signal-repair-controls'

def fixture():
    def record(name,use,kind,x):
        return ('- '+name+' ( u A ) ( v Z )\n  + USE '+use+'\n  + '+kind+' Metal2 ( '+str(x)+' 0 ) ( 20 * )\n ;\n').encode()
    records=[record('ck','CLOCK','FIXED',0),record('sig','SIGNAL','ROUTED',1),
             record('other','RESET','ROUTED',2),b'- unwired ( u B )\n  + USE SIGNAL\n ;\n']
    raw=b'VERSION 5.8 ;\nNETS 4 ;\n'+b''.join(records)+b'END NETS\nEND DESIGN\n'
    identity={name:dict(name=name,sigtype=kind,sha256=name)for name,kind in [('ck','CLOCK'),('sig','SIGNAL'),('other','RESET'),('unwired','SIGNAL')]}
    encoded={name:dict(wire_present=name!='unwired',metadata='FIXED'if name=='ck'else'ROUTED',
        paths=[]if name=='unwired'else['FIXED'if name=='ck'else'ROUTED'])for name in identity}
    baseline=dict(identity=identity,encoded=encoded,geometry=dict(sha256='geometry',counts={'instance':2}))
    return raw,baseline

def sequence(text):
    tree=ast.parse(text);run=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='run')
    rows=[]
    for node in ast.walk(run):
        if isinstance(node,ast.Call)and isinstance(node.func,ast.Name):
            if node.func.id=='phase'and node.args and isinstance(node.args[0],ast.Constant):rows.append((node.lineno,node.args[0].value))
            elif node.func.id=='command'and len(node.args)==2 and isinstance(node.args[1],ast.Constant):rows.append((node.lineno,node.args[1].value))
    rows=[v for _,v in sorted(rows)]
    expected=['bootstrap-exact-runtime','restore-complete-saved-inputs','actual-runtime-version','prepare',
        'load-exact-saved-guides','guide-audit','one-signal-routing-attempt','route-audit',
        'paired-original-class-return','unfix-audit','full-original-class-read-only-DRT','drc-audit']
    assert rows==expected
    return rows

def guide_fixture(empty=False,congested=False,valid=True):
    class Layer:
        def __init__(self,name,level):self.name,self.level=name,level
        def getName(self):return self.name
        def getRoutingLevel(self):return self.level
    lo,hi=Layer('Metal2',2),Layer('TopMetal2',7)
    box=types.SimpleNamespace(xMin=lambda:0,yMin=lambda:0,xMax=lambda:100,yMax=lambda:100)
    net=types.SimpleNamespace(getName=lambda:'sig')
    guide=types.SimpleNamespace(isCongested=lambda:congested,getNet=lambda:net,
        getLayer=lambda:lo if valid else Layer('TooHigh',9),getBox=lambda:box)
    net.getGuides=lambda:[]if empty else[guide]
    block=types.SimpleNamespace(getNets=lambda:[net])
    tech=types.SimpleNamespace(findLayer=lambda name:{'Metal2':lo,'TopMetal2':hi}[name])
    db=types.SimpleNamespace(getTech=lambda:tech)
    return db,block

def controls():
    m=s.methods();assert m['source_controls_authorized']is True
    positives=[];refusals=[]
    def reject(label,fn,errors=(AssertionError,ValueError,KeyError)):
        try:fn()
        except errors:refusals.append(label)
        else:raise AssertionError('Accepted '+label)
    actual=json.loads(c.regular(c.ROOT/s.CLASSIFICATION).read_bytes())
    assert s.classification_admission()==s.classification_fields(actual)
    positives.append('actual_complete762_classification')
    for label,mutate in [
      ('prior_wrong_count',lambda b:b['classification'].update(marker_count=761)),
      ('prior_wrong_owner',lambda b:b['classification'].update(exclusive_group_counts={'clock-clock':762})),
      ('prior_wrong_selected',lambda b:b['classification'].update(selected_names_sha256='0'*64)),
      ('prior_wrong_TR',lambda b:b['classification'].update(TR_sha256='0'*64)),
      ('prior_feasibility_claim',lambda b:b['classification'].update(routing_feasibility_proven=True))]:
        bad=copy.deepcopy(actual);mutate(bad);reject(label,lambda bad=bad:s.classification_fields(bad))
    raw,before=fixture();owners=s.ownership(raw,['ck'],before['identity'],before['encoded'])
    assert owners['mutable']==['sig']
    changed=raw.replace(b'ROUTED Metal2 ( 1 0 )',b'ROUTED Metal2 ( 11 0 )')
    assert s.routing_delta(raw,changed,owners)['changed_signal_names']==['sig']
    assert s.routing_delta(raw,raw,owners)['changed_signal_count']==0
    positives+=['explicit_routed_SIGNAL_only','ordered_signal_delta_and_zero_delta']
    changes=[
      ('selected_geometry',lambda b:b.replace(b'FIXED Metal2 ( 0 0 )',b'FIXED Metal2 ( 10 0 )')),
      ('selected_class',lambda b:b.replace(b'FIXED Metal2',b'ROUTED Metal2')),
      ('non_signal_geometry',lambda b:b.replace(b'ROUTED Metal2 ( 2 0 )',b'ROUTED Metal2 ( 21 0 )')),
      ('new_unwired_signal',lambda b:b.replace(b'+ USE SIGNAL\n ;',b'+ USE SIGNAL\n  + ROUTED Metal2 ( 0 0 ) ( 1 0 )\n ;')),
      ('signal_connection',lambda b:b.replace(b'- sig ( u A )',b'- sig ( w A )')),
      ('signal_USE',lambda b:b.replace(b'- sig ( u A ) ( v Z )\n  + USE SIGNAL',b'- sig ( u A ) ( v Z )\n  + USE CLOCK')),
      ('signal_NDR',lambda b:b.replace(b'+ ROUTED Metal2 ( 1 0 )',b'+ NONDEFAULTRULE extra\n  + ROUTED Metal2 ( 1 0 )')),
      ('signal_new_class',lambda b:b.replace(b'ROUTED Metal2 ( 1 0 )',b'FIXED Metal2 ( 1 0 )')),
      ('signal_trailing_attribute',lambda b:b.replace(b'ROUTED Metal2 ( 1 0 ) ( 20 * )\n ;',b'ROUTED Metal2 ( 1 0 ) ( 20 * )\n + WEIGHT 10\n ;')),
      ('net_census',lambda b:b.replace(b'NETS 4',b'NETS 5')),
      ('non_NETS',lambda b:b.replace(b'VERSION 5.8',b'VERSION 5.7')),
      ('net_name',lambda b:b.replace(b'- sig ',b'- changed ')),
    ]
    for label,fn in changes:
        bad=fn(raw);assert bad!=raw;reject(label,lambda bad=bad:s.routing_delta(raw,bad,owners))
    good=copy.deepcopy(before);good['encoded']['sig']['paths']=['ROUTED','ROUTED']
    assert s.native_invariants(before,good,owners);positives.append('native_signal_path_count_change')
    for label,mutate in [
      ('native_placement',lambda b:b['geometry'].update(sha256='moved')),
      ('native_terminal',lambda b:b['identity']['sig'].update(sha256='rewired')),
      ('native_signal_FIXED',lambda b:b['encoded']['sig'].update(paths=['FIXED'])),
      ('native_signal_missing',lambda b:b['encoded']['sig'].update(wire_present=False,paths=[])),
      ('native_clock_path',lambda b:b['encoded']['ck'].update(paths=['FIXED','FIXED'])),
      ('native_non_SIGNAL_metadata',lambda b:b['encoded']['other'].update(metadata='FIXED')),
      ('native_unwired_created',lambda b:b['encoded']['unwired'].update(wire_present=True,paths=['ROUTED'])),
    ]:
        bad=copy.deepcopy(before);mutate(bad);reject(label,lambda bad=bad:s.native_invariants(before,bad,owners))
    with patch.object(native.n,'load',return_value=guide_fixture()):
        gp=native.guide_proof(Path('/synthetic.odb'));native.validate_guide_proof(gp)
    positives.append('actual_dbGuide_API_shape')
    for label,options in [('empty_guides',dict(empty=True)),('congested_guides',dict(congested=True)),('no_inrange_guides',dict(valid=False))]:
        with patch.object(native.n,'load',return_value=guide_fixture(**options)):
            reject(label,lambda:native.guide_proof(Path('/synthetic.odb')))
    # Only the hash is patched to admit this explicitly synthetic generated-Tcl fixture.
    original=(s.SETUP+'# The input has only stale data wires removed.\n'+s.LAYERS+'\n'+s.ARGUMENTS+'drt_run $i {*}$drt_args\n').encode()
    with patch.dict(s.GLOBAL_INPUTS,{s.GLOBAL_PREFIX+'fresh_fanout_native.tcl':c.digest(original)}):
        tcl=s.route_tcl(Path('/source.odb'),Path('/_env.tcl'),Path('/out'),original,lambda p:'{'+str(p)+'}')
    assert tcl.count('detailed_route {*}$drt_args')==1
    assert all(x not in tcl for x in ['-incremental','repair_antennas','repair_design','repair_timing','global_route','-single_step_dr'])
    assert 'read_db {/source.odb}'in tcl and s.SETUP in tcl and s.ARGUMENTS in tcl
    positives.append('actual_standard_route_program_original_arguments')
    reject('wrong_original_Tcl_hash',lambda:s.exact_setup(original))
    for label,old,new in [('wrong_seed','-or_seed 42','-or_seed 43'),('wrong_threads','set_thread_count','changed_thread_count'),
                          ('wrong_layers','Metal2-TopMetal2','Metal1-TopMetal2')]:
        bad=original.replace(old.encode(),new.encode());assert bad!=original
        with patch.dict(s.GLOBAL_INPUTS,{s.GLOBAL_PREFIX+'fresh_fanout_native.tcl':c.digest(bad)}):
            reject(label,lambda bad=bad:s.exact_setup(bad))
    log=b'NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_BEGIN\nwork\nNSSOC_FIXED_CLOCK_SIGNAL_REPAIR_RETURNED\n'
    assert s.route_log(log)['single_returned_attempt'];positives.append('single_completed_route_log')
    for label,bad in [('missing_return',log.split(b'NSSOC_FIXED_CLOCK_SIGNAL_REPAIR_RETURNED')[0]),
                      ('duplicate_route',log+log),('non_utf8_log',log+b'\xff')]:
        reject(label,lambda bad=bad:s.route_log(bad),(AssertionError,UnicodeError))
    result=dict(original1691_clock_gate_passed=True,native_invariants_passed=True,
        routing_delta=dict(other_records_byte_exact=True,non_NETS_bytes_exact=True),
        final_DRT=dict(marker_count=0,zero_reported_DRT_markers=True,all_categories_below_native_cap=True,
            serialized_markers=dict(marker_count=0,complete_native_category_census_equal=True)))
    assert s.continuation_gate(result)['eligible_for_separately_reviewed_RC_STA']
    nonzero=copy.deepcopy(result);nonzero['final_DRT'].update(marker_count=1,zero_reported_DRT_markers=False)
    nonzero['final_DRT']['serialized_markers']['marker_count']=1
    assert not s.continuation_gate(nonzero)['eligible_for_separately_reviewed_RC_STA']
    positives.append('zero_vs_visible_nonzero_DRT_gate')
    for label,mutate in [
      ('missing_DRT',lambda b:b.pop('final_DRT')),('saturated_DRT',lambda b:b['final_DRT'].update(all_categories_below_native_cap=False)),
      ('wrong_serialized_count',lambda b:b['final_DRT']['serialized_markers'].update(marker_count=1)),
      ('false_zero',lambda b:b['final_DRT'].update(zero_reported_DRT_markers=False)),
      ('clock_gate_false',lambda b:b.update(original1691_clock_gate_passed=False))]:
        bad=copy.deepcopy(result);mutate(bad);reject(label,lambda bad=bad:s.continuation_gate(bad))
    source=c.regular(ROOT/'scripts/cloud_mainchip_fixed_clock_signal_repair.py').read_text()
    order=sequence(source);positives.append('actual_cloud_phase_order')
    for label,a,b in [('skip_guide_audit',"phase('guide-audit')","phase('prepare')"),
                       ('skip_route_audit',"phase('route-audit')","phase('prepare')"),
                       ('skip_final_DRC',"'full-original-class-read-only-DRT'","'wrong-check'")]:
        bad=source.replace(a,b,1);assert bad!=source;reject(label,lambda bad=bad:sequence(bad))
    # Real restoration entry must always restore the shared extraction projection after failure.
    original_selected=driver.capture.SELECTED;injected=ValueError('injected capture transport failure');observed=[]
    def fail_capture(path):
        observed.append((path,driver.capture.SELECTED));raise injected
    with tempfile.TemporaryDirectory()as tmp,patch.object(driver,'TRANSPORT',Path(tmp)/'transport'),patch.object(s,'methods',return_value={'cloud_restore_authorized':True}),patch.object(driver.capture,'restore',side_effect=fail_capture):
        try:driver.restore_worker()
        except ValueError as e:assert e is injected
        else:raise AssertionError('Lost original transport error')
    assert len(observed)==1 and set(s.CLOCK_INPUTS)<=set(observed[0][1])and driver.capture.SELECTED==original_selected
    positives.append('actual_restore_projection_and_finally_on_error')
    import publish_mainchip_saved_postroute as pub
    old=pub.GROUP;seen=[]
    def fake(root,out):seen.append((root,out,pub.GROUP));return {'fixture':True}
    with patch.object(driver,'space',return_value={}),patch.object(pub,'publish_evidence',side_effect=fake):
        assert driver.publish()=={'fixture':True}
    assert seen==[(driver.OUT,driver.ROOT/('publication-'+driver.GROUP),driver.GROUP)]and pub.GROUP==old
    positives.append('actual_reserved_publisher_group_and_paths')
    error=ValueError('injected publisher failure')
    with patch.object(driver,'space',return_value={}),patch.object(pub,'publish_evidence',side_effect=error)as p:
        try:driver.publish()
        except ValueError as e:assert e is error;p.assert_called_once()
        else:raise AssertionError('Publisher error hidden')
    assert pub.GROUP==old;positives.append('actual_publisher_failure_preserved')
    import check_mainchip_clock_marker_classification as inherited
    inherited_result=inherited.controls()
    import check_mainchip_original_clock_restoration_driver as oldcheck
    markers=oldcheck.marker_controls()
    assert len(positives)==12 and len(refusals)==42,(len(positives),len(refusals))
    return dict(status='PASS_SIGNAL_REPAIR_SOURCE_CONTROLS_NOT_NATIVE',positives=positives,refusals=refusals,
        inherited_classification_archive_publication_wait=inherited_result,marker_API=markers,
        phase_sequence=order,synthetic_native_DB_API_fixture=True,synthetic_Tcl_hash_override_fixture=True,
        actual_native_archive_accessed=False,native_execution=False,accepted=False)

ROOT=c.ROOT
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);result=dict(status='RUNNING_SOURCE_CONTROLS',source_head=os.environ['GITHUB_SHA'])
    try:result.update(controls())
    except BaseException as e:
        result.update(status='FAIL_SOURCE_CONTROLS',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        path=OUT/'result.json';driver.save(path,result);emit(path)
if __name__=='__main__':main()
