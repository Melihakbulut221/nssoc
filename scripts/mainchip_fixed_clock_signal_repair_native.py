#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native fixed-clock signal-repair preparation/audits; routing is a separate supervised Tcl."""
import json,os,types
from pathlib import Path
import odb
import mainchip_original_clock_restoration as c
import mainchip_original_clock_restoration_native as n
import mainchip_original_clock_drc as d
import mainchip_fixed_clock_signal_repair as s

def save(path,value):
    from cloud_mainchip_original_clock_restoration import save as atomic
    atomic(path,value)

def snapshot(path,out,label):
    db,b=n.load(path)
    try:
        odb.write_def(b,str(out/(label+'.def')))
        names=sorted(x.getName()for x in b.getNets())
        assert len(names)==len(set(names))==143820
        identity={};encoded={}
        for name in names:
            net=b.findNet(name);row=n.identity(db,net)
            identity[name]=dict(name=name,sigtype=row['sigtype'],sha256=c.digest(c.canonical(row)))
            encoded[name]=n.encoded(net)
        # Preserve the qualified streaming placement/pin/connectivity projection.
        # Only dynamic wire state and used-via census are handled separately below.
        proxy=types.SimpleNamespace(identity=n.identity,
            encoded=lambda net:dict(metadata=str(net.getWireType()),special=net.isSpecial()),
            vias=lambda db,block,names:{})
        geometry=d.geometry_projection(db,b,proxy)
        geometry['scope']='All net identity and metadata/special status, all instance placement and master-pin boxes; encoded wires and union of used-via definitions audited separately.'
        return dict(identity=identity,encoded=encoded,geometry=geometry,via=n.vias(db,b,names),
                    raw_def_sha256=c.file_sha(out/(label+'.def')))
    finally:odb.dbDatabase.destroy(db)

def compare_vias(before,after,before_path,after_path):
    union=dict(before['via']);union.update(after['via'])
    for key in before['via'].keys()&after['via'].keys():assert before['via'][key]==after['via'][key]
    for path in (before_path,after_path):
        db,b=n.load(path)
        try:n.vias(db,b,[],union)
        finally:odb.dbDatabase.destroy(db)
    return dict(union_count=len(union),definitions_present_and_identical_in_both_databases=True,
                newly_generated_via_definitions_not_admitted=True)

def guide_proof(path):
    db,b=n.load(path)
    try:
        lo=db.getTech().findLayer('Metal2');hi=db.getTech().findLayer('TopMetal2')
        assert lo and hi and lo.getRoutingLevel()<hi.getRoutingLevel()
        rows=[];valid=0
        for net in sorted(b.getNets(),key=lambda x:x.getName()):
            for g in net.getGuides():
                assert not g.isCongested(),'Congested saved guide'
                assert g.getNet()is not None and g.getNet().getName()==net.getName()
                layer=g.getLayer();assert layer
                box=g.getBox()
                row=[net.getName(),layer.getName(),box.xMin(),box.yMin(),box.xMax(),box.yMax()]
                assert row[2]<row[4]and row[3]<row[5]
                rows.append(row)
                if lo.getRoutingLevel()<=layer.getRoutingLevel()<=hi.getRoutingLevel():valid+=1
        assert rows and valid>0,'No valid guides; native global-route fallback forbidden'
        return dict(guides=len(rows),in_range_guides=valid,sha256=c.digest(c.canonical(sorted(rows))),
                    source='Exact saved global guide loaded and observed through dbGuide before routing')
    finally:odb.dbDatabase.destroy(db)

def validate_guide_proof(value):
    assert type(value['guides'])is int and type(value['in_range_guides'])is int
    assert value['guides']>=value['in_range_guides']>0
    assert len(value['sha256'])==64
    return value

def source_paths():
    clock=Path(os.environ['NSSOC_SIGNAL_CLOCK_SOURCE'])
    global_root=Path(os.environ['NSSOC_SIGNAL_GLOBAL_SOURCE'])
    for name,h in s.CLOCK_INPUTS.items():assert c.file_sha(clock/name)==h,('clock input',name)
    for name,h in s.GLOBAL_INPUTS.items():assert c.file_sha(global_root/name)==h,('global input',name)
    return clock,global_root

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    method=s.methods()
    assert method['native_execution_authorized']is True and method['native_routing_authorized']is True
    clock,global_root=source_paths();out=Path(os.environ['NSSOC_SIGNAL_OUT'])
    assert out.is_absolute()and out.is_dir()
    for p in [out,*out.parents]:assert not p.is_symlink()
    mode=os.environ['NSSOC_SIGNAL_PHASE']
    assert mode in ('prepare','guide-audit','route-audit','unfix-audit','drc-audit')
    fixed=clock/'work/fixed.odb';restored=clock/'work/restored.odb'
    donor=clock/'source/geometry/routed/work/before-guide-read.odb'
    result=dict(status='RUNNING',phase=mode,accepted=False,timing_accepted=False,full_phy_accepted=False)
    try:
        plan=json.loads(c.regular(clock/'work/audit-restored-result.json').read_bytes())['plan']
        names=plan['all_clock_names']
        assert len(names)==len(set(names))==1691 and c.digest(c.canonical(names))==s.SELECTED_SHA
        original=c.regular(clock/'work/restored.def').read_bytes()
        fixed_raw=c.regular(clock/'work/fixed.def').read_bytes()
        overlay,classes=c.fixed_overlay(original,names)
        assert overlay==fixed_raw
        if mode=='prepare':
            baseline=snapshot(fixed,out,'baseline-fixed')
            assert baseline['raw_def_sha256']==s.FIXED_DEF
            owners=s.ownership(fixed_raw,names,baseline['identity'],baseline['encoded'])
            c.validate_encoded({k:baseline['encoded'][k]for k in names},
                {k:'FIXED'if v is not None else None for k,v in classes.items()})
            result['original_gate_before']=n.original_gate(donor,restored,out,'original-gate-before-repair')
            save(out/'baseline-native.json',baseline);save(out/'ownership.json',owners)
            save(out/'original-classes.json',classes)
            guide=global_root/(s.GLOBAL_PREFIX+'fresh-fanout.guide')
            (out/'load-guides.tcl').write_text('read_db '+n.tcl_path(fixed)+'\nread_guides '+n.tcl_path(guide)+
                '\nwrite_def '+n.tcl_path(out/'guide-loaded.def')+'\nwrite_db '+n.tcl_path(out/'guide-loaded.odb')+'\n')
            settings=s.timing_contract(json.loads(c.regular(global_root/(s.GLOBAL_PREFIX+'config.json')).read_bytes()),
                json.loads(c.regular(global_root/'trial-config.json').read_bytes()))
            text=s.route_tcl(out/'guide-loaded.odb',global_root/(s.GLOBAL_PREFIX+'_env.tcl'),out,
                c.regular(global_root/(s.GLOBAL_PREFIX+'fresh_fanout_native.tcl')).read_bytes(),n.tcl_path)
            (out/'repair.tcl').write_text(text)
            result.update(status='PREPARED_FIXED_CLOCK_SIGNAL_REPAIR',selected=1691,
                mutable_signals=len(owners['mutable']),timing_contract=settings,repair_tcl_sha256=c.file_sha(out/'repair.tcl'))
        else:
            baseline=json.loads(c.regular(out/'baseline-native.json').read_bytes())
            owners=json.loads(c.regular(out/'ownership.json').read_bytes())
            assert owners['selected']==names and owners['net_count']==143820
            if mode=='guide-audit':
                got=snapshot(out/'guide-loaded.odb',out,'guide-audit')
                assert c.regular(out/'guide-audit.def').read_bytes()==fixed_raw
                assert got==baseline,'Guide load changed native geometry, metadata, wire or via projection'
                result['guide_proof']=validate_guide_proof(guide_proof(out/'guide-loaded.odb'))
                result.update(status='PASS_EXACT_GUIDE_LOAD_BEFORE_ROUTING',
                    guide_loaded_odb_sha256=c.file_sha(out/'guide-loaded.odb'))
            elif mode=='route-audit':
                pre=json.loads(c.regular(out/'guide-audit-result.json').read_bytes())
                assert pre['status']=='PASS_EXACT_GUIDE_LOAD_BEFORE_ROUTING'
                assert c.file_sha(out/'guide-loaded.odb')==pre['guide_loaded_odb_sha256']
                validate_guide_proof(pre['guide_proof'])
                prep=json.loads(c.regular(out/'prepare-result.json').read_bytes())
                assert c.file_sha(out/'repair.tcl')==prep['repair_tcl_sha256']
                routed=out/'routed-fixed.odb';got=snapshot(routed,out,'routed-audit')
                raw=c.regular(out/'routed-audit.def').read_bytes()
                assert raw==c.regular(out/'routed-fixed.def').read_bytes()
                result['routing_delta']=s.routing_delta(fixed_raw,raw,owners)
                s.native_invariants(baseline,got,owners)
                result['via_proof']=compare_vias(baseline,got,fixed,routed)
                c.validate_encoded({k:got['encoded'][k]for k in names},
                    {k:'FIXED'if v is not None else None for k,v in classes.items()})
                expected=c.restore_classes(raw,classes)
                expected_records=c.parse_def(expected)['records']
                patch,_=c.patch_def(raw,{k:expected_records[k]for k,v in classes.items()if v is not None})
                (out/'original-class-patch.def').write_bytes(patch)
                (out/'expected-original-class.def').write_bytes(expected)
                # Metadata and encoded route classes are independent. Restore metadata first.
                baseview=n.view(routed,out/'metadata-base-view.def',names)
                originalview=n.view(restored,out/'source-original-view.def',names,baseview['vias'])
                target={k:originalview['encoded'][k]['metadata']for k in names}
                n.metadata_base(routed,out/'unfix-base.odb',target,raw,baseview,out,'metadata-unfixed')
                (out/'unfix.tcl').write_text(n.import_tcl(out/'unfix-base.odb',out/'original-class-patch.def',out,'repaired'))
                save(out/'routed-native.json',got)
                result.update(status='PASS_SIGNAL_ONLY_DELTA_WITH_CLOCKS_ENCODED_FIXED',native_invariants_passed=True)
            elif mode=='unfix-audit':
                candidate=out/'repaired.odb';got=snapshot(candidate,out,'repaired-audit')
                expected=c.regular(out/'expected-original-class.def').read_bytes()
                assert c.regular(out/'repaired-audit.def').read_bytes()==expected
                # Compare routing changes in the original-class domain, not the temporary overlay.
                old=snapshot(restored,out,'original-native')
                result['routing_delta']=s.routing_delta(original,expected,owners)
                s.native_invariants(old,got,owners)
                result['via_proof']=compare_vias(old,got,restored,candidate)
                result['original_gate']=n.original_gate(donor,candidate,out,'original-gate-after-repair')
                db,b=n.load(candidate)
                try:
                    assert b.findMarkerCategory(d.CATEGORY)is None,'Existing final-check category'
                    geometry=d.geometry_projection(db,b,n)
                finally:odb.dbDatabase.destroy(db)
                (out/'final-drc.tcl').write_text(d.tcl(candidate,out,n.tcl_path))
                result.update(status='PASS_ORIGINAL_CLASS_SIGNAL_REPAIR_REQUIRES_COMPLETE_DRC',
                    original1691_clock_gate_passed=True,native_invariants_passed=True,
                    candidate_sha256=c.file_sha(candidate),native_geometry=geometry,
                    expected_def_sha256=c.digest(expected),drc_tcl_sha256=c.file_sha(out/'final-drc.tcl'))
            else:
                prior=json.loads(c.regular(out/'unfix-audit-result.json').read_bytes())
                assert prior['status']=='PASS_ORIGINAL_CLASS_SIGNAL_REPAIR_REQUIRES_COMPLETE_DRC'
                candidate=out/'repaired.odb';measured=out/'drc-observed.odb'
                assert c.file_sha(candidate)==prior['candidate_sha256']
                assert c.file_sha(out/'final-drc.tcl')==prior['drc_tcl_sha256']
                expected=c.regular(out/'expected-original-class.def').read_bytes()
                assert c.digest(expected)==prior['expected_def_sha256']
                for p in ('drc-before.def','drc-after.def'):
                    assert c.regular(out/p).read_bytes()==expected
                got=snapshot(measured,out,'measured-audit')
                assert c.regular(out/'measured-audit.def').read_bytes()==expected
                db,b=n.load(measured)
                try:
                    assert d.geometry_projection(db,b,n)==prior['native_geometry'],'Read-only DRT changed nonmarker native geometry'
                    category=b.findMarkerCategory(d.CATEGORY)
                    assert category is not None,'Missing final original-class DRT category'
                    category.writeJSON(str(out/'initial-drc-markers.json'))
                    measurement=d.measure_report(category,out/'initial-drc.rpt',out/'initial-drc-reread.rpt',out/'initial-drc-markers.json')
                finally:odb.dbDatabase.destroy(db)
                result['original_gate']=n.original_gate(donor,measured,out,'original-gate-after-final-drc')
                result.update(status='COMPLETE_SIGNAL_REPAIR_AND_ORIGINAL_CLASS_DRC_NOT_TIMING_OR_PHY_ACCEPTANCE',
                    original1691_clock_gate_passed=True,native_invariants_passed=True,
                    routing_delta=prior['routing_delta'],final_DRT=measurement)
                result['next_stage']=s.continuation_gate(result)
        source_paths()
    except BaseException as e:
        result.update(status='FAIL_SIGNAL_REPAIR_NATIVE_PHASE',error=repr(e));raise
    finally:save(out/(mode+'-result.json'),result)

if __name__=='__main__':main()
