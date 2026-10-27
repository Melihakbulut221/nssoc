#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native two-signal ownership, class-overlay and strict original-class audits."""
import json,os,types
from pathlib import Path
import odb
import mainchip_original_clock_restoration as c
import mainchip_original_clock_restoration_native as n
import mainchip_original_clock_drc as d
import mainchip_fixed_clock_signal_repair as old
import mainchip_fixed_clock_signal_repair_native as prior
import mainchip_two_signal_repair as s
import mainchip_two_signal_ownership_native as ownership_native
from cloud_mainchip_original_clock_restoration import save

def snapshot(path,out,label):
    db,b=n.load(path)
    try:
        odb.write_def(b,str(out/(label+'.def')))
        names=sorted(x.getName()for x in b.getNets());assert len(names)==len(set(names))==143820
        identity={};encoded={}
        for name in names:
            net=b.findNet(name);row=n.identity(db,net)
            identity[name]=dict(name=name,sigtype=row['sigtype'],sha256=c.digest(c.canonical(row)))
            encoded[name]=n.encoded(net)
        # Only the temporary metadata/path class overlay is excluded here.
        # Complete per-net metadata/path states are compared independently below.
        proxy=types.SimpleNamespace(identity=n.identity,encoded=lambda net:dict(special=net.isSpecial()),
                                    vias=lambda db,block,names:{})
        geometry=d.geometry_projection(db,b,proxy)
        geometry['scope']='Qualified placement/pins/connections/NDR and special status; all metadata/path classes and used-via definitions compared separately.'
        geometry['immutable_obstacles_and_special_material']=ownership_native.immutable_material(db,b)
        return dict(identity=identity,encoded=encoded,geometry=geometry,
            via=prior.via_projection(n.vias(db,b,names)),raw_def_sha256=c.file_sha(out/(label+'.def')))
    finally:odb.dbDatabase.destroy(db)

def structural_equal(left,right):
    assert left['identity']==right['identity'],'Native terminal identity changed'
    assert left['geometry']==right['geometry'],'Native placement/pin/NDR/special geometry changed'
    assert left['via']==right['via'],'Metadata-only step changed used via definitions'

def metadata_base(source,destination,target,expected,baseline,out,label,remove_category=False):
    assert set(target)==set(baseline['encoded'])
    db,b=n.load(source)
    try:
        before={x.getName():n.encoded(x)for x in b.getNets()}
        assert before==baseline['encoded']
        if remove_category:
            category=b.findMarkerCategory(d.CATEGORY)
            assert category is not None,'Expected saved three-marker category absent'
            odb.dbMarkerCategory.destroy(category)
            assert b.findMarkerCategory(d.CATEGORY)is None
        for name,kind in target.items():
            net=b.findNet(name);assert net
            if str(net.getWireType())!=kind:net.setWireType(kind)
        actual={x.getName():n.encoded(x)for x in b.getNets()}
        c.validate_metadata_transition(actual,before,target)
        odb.write_db(db,str(destination))
    finally:odb.dbDatabase.destroy(db)
    got=snapshot(destination,out,label)
    assert c.regular(out/(label+'.def')).read_bytes()==expected
    structural_equal(baseline,got)
    c.validate_metadata_transition(got['encoded'],baseline['encoded'],target)
    return got

def input_paths():
    clock,global_root=prior.source_paths()
    failed=Path(os.environ['NSSOC_TWO_SIGNAL_FAILED_SOURCE'])
    source=c.regular(failed/s.INPUT)
    assert c.file_sha(source)==s.INPUT_SHA and source.stat().st_size==s.INPUT_BYTES
    assert c.file_sha(failed/'work/expected-original-class.def')==s.DEF_SHA
    assert c.file_sha(failed/'work/initial-drc-markers.json')==s.MARKER_SHA
    assert c.file_sha(failed/'work/initial-drc.rpt')==s.TR_SHA
    return clock,global_root,failed,source

def guide_census(path,owners,out,immutable_material):
    """Save every observed router row before any routing-admission assertion."""
    observed=dict(status='INCOMPLETE_ROUTER_API_OBSERVATION',accepted=False,
        source_odb_sha256=c.file_sha(path),rows={},special_observations={},
        duplicate_names=[],current_net=None,enumerated_count=0,enumeration_complete=False,
        immutable_special_material=immutable_material,
        material_protection='Already compared by structural_equal before this call; unchanged postroute invariants remain mandatory.')
    report=None;failure=None;answer=None;db=None
    try:
        db,b=n.load(path)
        for net in b.getNets():
            name=net.getName();observed['current_net']=name;observed['enumerated_count']+=1
            guides=list(net.getGuides());iterms=list(net.getITerms());bterms=list(net.getBTerms())
            row=dict(n.encoded(net),guides=len(guides),terminals=len(iterms)+len(bterms),
                special=net.isSpecial(),sigtype=str(net.getSigType()))
            if name in observed['rows']:
                observed['duplicate_names'].append(dict(name=name,row=row))
            else:observed['rows'][name]=row
            if row['special']is True:
                details=[]
                for ordinal,guide in enumerate(guides):
                    owner=guide.getNet();layer=guide.getLayer();box=guide.getBox()
                    details.append(dict(ordinal=ordinal,owner=None if owner is None else owner.getName(),
                        layer=None if layer is None else layer.getName(),
                        box=[box.xMin(),box.yMin(),box.xMax(),box.yMax()],congested=guide.isCongested()))
                observed['special_observations'][name]=dict(identity=n.identity(db,net),guides=details)
        observed.update(current_net=None,enumeration_complete=True)
        report=s.router_census_observation(observed['rows'],owners)
        native_refusals=[]
        if observed['duplicate_names']:native_refusals.append(dict(name=None,reason='duplicate_native_net_name'))
        for name,details in observed['special_observations'].items():
            row=observed['rows'][name];identity=details['identity']
            if not (identity['name']==name and identity['sigtype']==row['sigtype']
                and len(identity['terminals'])+len(identity['bterms'])==row['terminals']):
                native_refusals.append(dict(name=name,reason='special_terminal_identity_join'))
            if len(details['guides'])!=row['guides']or any(
                guide['owner']!=name or guide['layer']is None or guide['congested']
                or not (guide['box'][0]<guide['box'][2]and guide['box'][1]<guide['box'][3])
                for guide in details['guides']):
                native_refusals.append(dict(name=name,reason='special_guide_identity_or_geometry'))
        report['native_observation_refusals']=native_refusals
        # Both complete raw observations and all compact refusal classes survive rejection.
        save(out/'router-census-observed.json',observed)
        save(out/'router-census-report.json',report)
        assert not native_refusals,('Native router census observation refused',native_refusals)
        answer=s.router_census(observed['rows'],owners)
        observed['status']='COMPLETE_ROUTER_CENSUS_GATE_NOT_ROUTING_ACCEPTANCE'
    except BaseException as exc:
        failure=exc
        observed.update(status='FAIL_ROUTER_CENSUS_NO_ROUTING',error=repr(exc))
    finally:
        try:
            if db is not None:odb.dbDatabase.destroy(db)
        except BaseException as exc:
            observed['database_cleanup_error']=repr(exc)
            observed['status']='FAIL_ROUTER_CENSUS_NO_ROUTING'
            if failure is None:failure=exc
        if report is None:
            report=s.router_census_observation(observed['rows'],owners)
            report['native_observation_refusals']=[]
        report.update(observation_status=observed['status'],
            enumeration_complete=observed['enumeration_complete'],
            current_net=observed['current_net'],enumerated_count=observed['enumerated_count'],accepted=False)
        if failure is not None:report['error']=repr(failure)
        save(out/'router-census-observed.json',observed)
        save(out/'router-census-report.json',report)
    if failure is not None:raise failure
    answer['saved_census']={p:c.file_sha(out/p)for p in (
        'router-census-observed.json','router-census-report.json')}
    return answer

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    m=s.methods()
    assert m['native_execution_authorized']is True and m['native_routing_authorized']is True
    clock,global_root,failed,source=input_paths()
    out=Path(os.environ['NSSOC_TWO_SIGNAL_OUT'])
    assert out.is_absolute()and out.is_dir()
    for p in [out,*out.parents]:assert not p.is_symlink()
    donor=clock/'source/geometry/routed/work/before-guide-read.odb'
    mode=os.environ['NSSOC_TWO_SIGNAL_PHASE']
    assert mode in ('ownership','prepare-fixed','fixed-audit','route-audit','unfix-audit','drc-audit')
    result=dict(status='RUNNING',phase=mode,accepted=False,original_run_failure_preserved=True,
                timing_accepted=False,full_phy_accepted=False)
    try:
        if mode=='ownership':
            baseline=snapshot(source,out,'baseline-original')
            original=c.regular(out/'baseline-original.def').read_bytes()
            assert c.digest(original)==s.DEF_SHA
            db,b=n.load(source)
            try:
                names=sorted(n.selected(b));assert len(names)==1691
                expected_geometry=s.readback()['saved_unfix_audit']['native_geometry']
                assert d.geometry_projection(db,b,n)==expected_geometry
                category=b.findMarkerCategory(d.CATEGORY);assert category is not None
                category.writeJSON(str(out/'source-markers.json'))
                assert c.file_sha(out/'source-markers.json')==s.MARKER_SHA
                measurement=d.measure_report(category,failed/'work/initial-drc.rpt',
                    out/'source-markers.rpt',out/'source-markers.json')
                assert measurement['marker_count']==3 and measurement['report_sha256']==s.TR_SHA
                ownership=ownership_native.collect(db,b)
            finally:odb.dbDatabase.destroy(db)
            owners,fixed,classes=s.ownership(original,names,baseline)
            save(out/'ownership.json',ownership);save(out/'owners.json',owners)
            save(out/'baseline-native.json',baseline);save(out/'original-classes.json',classes)
            (out/'expected-fixed.def').write_bytes(fixed)
            result['original_gate']=n.original_gate(donor,source,out,'original-gate-before-two-net-repair')
            result.update(status='COMPLETE_READ_ONLY_OWNERSHIP_NOT_ROUTING_ACCEPTANCE',
                native_ownership=ownership,initial_original_class_DRT=measurement,
                input_sha256=s.INPUT_SHA,eligible_for_one_two_net_attempt=ownership['eligible_for_one_two_net_attempt'])
        else:
            baseline=json.loads(c.regular(out/'baseline-native.json').read_bytes())
            owners=json.loads(c.regular(out/'owners.json').read_bytes())
            classes=json.loads(c.regular(out/'original-classes.json').read_bytes())
            original=c.regular(out/'baseline-original.def').read_bytes()
            fixed=c.regular(out/'expected-fixed.def').read_bytes()
            assert c.digest(original)==s.DEF_SHA
            actual_owners,actual_fixed,actual_classes=s.ownership(original,owners['selected'],baseline)
            assert (actual_owners,actual_fixed,actual_classes)==(owners,fixed,classes)
            s.require_actionable(json.loads(c.regular(out/'ownership.json').read_bytes()))
            if mode=='prepare-fixed':
                records=c.parse_def(fixed)['records']
                wired={k:v for k,v in classes.items()if v is not None}
                patch,_=c.patch_def(original,{k:records[k]for k in wired})
                (out/'fixed-patch.def').write_bytes(patch)
                target={k:('FIXED'if k in wired else e['metadata'])for k,e in baseline['encoded'].items()}
                metadata_base(source,out/'fixed-base.odb',target,fixed,baseline,out,'fixed-metadata',remove_category=True)
                (out/'fixed.tcl').write_text(n.import_tcl(out/'fixed-base.odb',out/'fixed-patch.def',out,'fixed'))
                result.update(status='PREPARED_ALL_NONTARGET_FIXED_ENCODING',protected_wired=len(wired),
                    protected_unwired=len(classes)-len(wired),mutable=list(s.TARGETS),
                    old_marker_category_removed_after_complete_read_only_evidence=True)
            elif mode=='fixed-audit':
                got=snapshot(out/'fixed.odb',out,'fixed-audit')
                assert c.regular(out/'fixed-audit.def').read_bytes()==fixed
                structural_equal(baseline,got)
                c.validate_encoded({k:got['encoded'][k]for k in classes},
                    {k:'FIXED'if v is not None else None for k,v in classes.items()})
                assert all(got['encoded'][k]==baseline['encoded'][k]for k in s.TARGETS)
                assert c.restore_classes(fixed,classes)==original
                result['router_census']=guide_census(out/'fixed.odb',owners,out,
                    got['geometry']['immutable_obstacles_and_special_material'])
                result['guide_proof']=prior.validate_guide_proof(prior.guide_proof(out/'fixed.odb'))
                save(out/'fixed-native.json',got)
                settings=old.timing_contract(json.loads(c.regular(global_root/(old.GLOBAL_PREFIX+'config.json')).read_bytes()),
                    json.loads(c.regular(global_root/'trial-config.json').read_bytes()))
                text=old.route_tcl(out/'fixed.odb',global_root/(old.GLOBAL_PREFIX+'_env.tcl'),out,
                    c.regular(global_root/(old.GLOBAL_PREFIX+'fresh_fanout_native.tcl')).read_bytes(),n.tcl_path)
                (out/'repair.tcl').write_text(text)
                result.update(status='PASS_ACTUAL_ALL_NONTARGET_FIXED_BEFORE_ONE_ATTEMPT',
                    repair_tcl_sha256=c.file_sha(out/'repair.tcl'),fixed_odb_sha256=c.file_sha(out/'fixed.odb'),
                    timing_contract=settings)
            elif mode=='route-audit':
                pre=json.loads(c.regular(out/'fixed-audit-result.json').read_bytes())
                assert pre['status']=='PASS_ACTUAL_ALL_NONTARGET_FIXED_BEFORE_ONE_ATTEMPT'
                assert c.file_sha(out/'repair.tcl')==pre['repair_tcl_sha256']
                assert c.file_sha(out/'fixed.odb')==pre['fixed_odb_sha256']
                before=json.loads(c.regular(out/'fixed-native.json').read_bytes())
                routed=out/'routed-fixed.odb';got=snapshot(routed,out,'routed-audit')
                raw=c.regular(out/'routed-audit.def').read_bytes()
                assert raw==c.regular(out/'routed-fixed.def').read_bytes()
                result['routing_delta']=s.routing_delta(fixed,raw,owners)
                old.native_invariants(before,got,owners)
                result['via_proof']=prior.compare_vias(before,got,out/'fixed.odb',routed)
                c.validate_encoded({k:got['encoded'][k]for k in classes},
                    {k:'FIXED'if v is not None else None for k,v in classes.items()})
                expected=s.restore_expectation(raw,classes)
                records=c.parse_def(expected)['records']
                patch,_=c.patch_def(raw,{k:records[k]for k,v in classes.items()if v is not None})
                (out/'original-class-patch.def').write_bytes(patch)
                (out/'expected-original-class.def').write_bytes(expected)
                target={k:e['metadata']for k,e in baseline['encoded'].items()}
                metadata_base(routed,out/'unfix-base.odb',target,raw,got,out,'unfixed-metadata')
                (out/'unfix.tcl').write_text(n.import_tcl(out/'unfix-base.odb',out/'original-class-patch.def',out,'repaired'))
                result.update(status='PASS_ONLY_TWO_SIGNAL_DELTA_ALL_OTHERS_FIXED',native_invariants_passed=True)
            elif mode=='unfix-audit':
                candidate=out/'repaired.odb';got=snapshot(candidate,out,'repaired-audit')
                expected=c.regular(out/'expected-original-class.def').read_bytes()
                assert c.regular(out/'repaired-audit.def').read_bytes()==expected
                result['routing_delta']=s.routing_delta(original,expected,owners)
                old.native_invariants(baseline,got,owners)
                result['via_proof']=prior.compare_vias(baseline,got,source,candidate)
                save(out/'unfixed-native.json',got)
                result['original_gate']=n.original_gate(donor,candidate,out,'original-gate-after-two-net-repair')
                db,b=n.load(candidate)
                try:
                    assert b.findMarkerCategory(d.CATEGORY)is None
                    native_geometry=d.geometry_projection(db,b,n)
                finally:odb.dbDatabase.destroy(db)
                (out/'final-drc.tcl').write_text(d.tcl(candidate,out,n.tcl_path))
                result.update(status='PASS_ORIGINAL_CLASS_TWO_SIGNAL_REPAIR_REQUIRES_DRC',
                    original1691_clock_gate_passed=True,native_invariants_passed=True,
                    candidate_sha256=c.file_sha(candidate),native_geometry=native_geometry,
                    expected_def_sha256=c.digest(expected),drc_tcl_sha256=c.file_sha(out/'final-drc.tcl'))
            else:
                previous=json.loads(c.regular(out/'unfix-audit-result.json').read_bytes())
                assert previous['status']=='PASS_ORIGINAL_CLASS_TWO_SIGNAL_REPAIR_REQUIRES_DRC'
                assert c.file_sha(out/'repaired.odb')==previous['candidate_sha256']
                assert c.file_sha(out/'final-drc.tcl')==previous['drc_tcl_sha256']
                expected=c.regular(out/'expected-original-class.def').read_bytes()
                assert c.digest(expected)==previous['expected_def_sha256']
                for p in ('drc-before.def','drc-after.def'):
                    assert c.regular(out/p).read_bytes()==expected
                measured=out/'drc-observed.odb';got=snapshot(measured,out,'measured-audit')
                assert c.regular(out/'measured-audit.def').read_bytes()==expected
                assert got==json.loads(c.regular(out/'unfixed-native.json').read_bytes()),'Read-only DRT changed complete native structural/class/material projection'
                db,b=n.load(measured)
                try:
                    assert d.geometry_projection(db,b,n)==previous['native_geometry']
                    category=b.findMarkerCategory(d.CATEGORY);assert category is not None
                    category.writeJSON(str(out/'initial-drc-markers.json'))
                    measurement=d.measure_report(category,out/'initial-drc.rpt',out/'initial-drc-reread.rpt',out/'initial-drc-markers.json')
                finally:odb.dbDatabase.destroy(db)
                result['original_gate']=n.original_gate(donor,measured,out,'original-gate-after-final-two-net-drc')
                result.update(status='COMPLETE_TWO_SIGNAL_ATTEMPT_ORIGINAL_CLASS_DRC_NOT_ACCEPTANCE',
                    original1691_clock_gate_passed=True,native_invariants_passed=True,
                    routing_delta=previous['routing_delta'],final_DRT=measurement)
                result['next_stage']=s.require_complete(result)
        input_paths()
    except BaseException as exc:
        result.update(status='FAIL_OR_BLOCKED_TWO_SIGNAL_NATIVE_PHASE',error=repr(exc));raise
    finally:save(out/(mode+'-result.json'),result)
if __name__=='__main__':main()
