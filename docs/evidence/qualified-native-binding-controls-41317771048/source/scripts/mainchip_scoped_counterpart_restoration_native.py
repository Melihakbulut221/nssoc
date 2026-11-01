"""Run original native restoration and physical audits with one scoped class adapter."""
import gc,json,os,shutil,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,'/work/tail-source/scripts')
import mainchip_bulk_postdrt_antenna_native as native
import mainchip_targeted_counterpart_routing_native as targeted
import mainchip_targeted_counterpart_routing as scope_core
import mainchip_container_floorplan_import as container
import mainchip_saved_diode_routing_native as saved
import mainchip_scoped_counterpart_restoration as fix
import mainchip_qualified_pin_native_binding as qualified
WORK=Path('/work/out/work/bulk-postdrt-antenna')
DATA=Path('/work/out/bulk-postdrt-antenna')
def read(name):return json.loads((DATA/name).read_bytes())
def verify():
    native.p.source_guard()
    assert native.fp(Path('/work/current-input.odb'))==native.p.INPUT
    pins=json.loads(Path('/work/scoped-source-pins.json').read_bytes())
    for name,pin in pins.items():assert fix.pin(Path('/work/tail-source',name).read_bytes())==pin,('new source',name)
    assert native.fp(WORK/'routed-fixed.odb')==dict(bytes=214409779,sha256='b87a2d43fe33dd8ca99f0faa2bdf38337ae30d6c5b72a337472919ac57f64e63')
    assert fix.pin((WORK/'fixed.def').read_bytes())==dict(bytes=185488886,sha256='9f28be4140f481886d501b26370ffcd431ceb8a436de1aff0946ee39573456d5')
def scoped_restore(raw,classes):
    reference=(WORK/'fixed.def').read_bytes()
    expected,proof=fix.plan(reference,raw,classes,read('insertion-plan.json'),read('targeted-routing-scope.json'))
    assert proof['total_nets']==143820
    native.save(DATA/'scoped-class-restoration-plan.json',proof)
    return expected
def restore():
    # Both clones have private globals; the frozen modules and functions remain untouched.
    clock_proxy=SimpleNamespace(**vars(native.c))
    clock_proxy.restore_classes=scoped_restore
    proxy=SimpleNamespace(**vars(native))
    proxy.restore_plan=container.clone(native.restore_plan,c=clock_proxy)
    container.call_native(proxy,'restore_plan',WORK,DATA)
    proof=read('class-restoration-plan.json')
    assert proof['failure_cleanup']is False and proof['used_pre_route_fallback']is False
    assert proof['source_pin']==native.fp(WORK/'routed-fixed.odb')
def power():
    target=WORK/'insertion-connected.odb'
    assert not target.exists()
    before=native.fp(WORK/'candidate.odb')
    shutil.copyfile(WORK/'candidate.odb',target)
    assert native.fp(target)==before
    saved.power_contact_audit()
    assert native.fp(target)==before and native.fp(WORK/'candidate.odb')==before
    result=read('new-diode-direct-pg-contacts.json')
    assert result['complete']is True and len(result['contacts'])==2702
    native.save(DATA/'scoped-candidate-pg-audit.json',dict(candidate=before,contacts=2702,complete=True,**fix.FLAGS))
def canonical_snapshot(path,out,protected=None):
    actual=native.snapshot(path,out,protected)
    result,proof=fix.canonical_master_snapshot(actual)
    assert proof['masters']==58
    native.save(DATA/('master-representation-'+out.stem+'.json'),proof)
    return result
def main():
    assert not any(k in os.environ for k in ('GH_TOKEN','GITHUB_TOKEN'))
    verify()
    phase=os.environ['NSSOC_BULK_PHASE']
    assert phase in ('restore-plan','restored-audit','power-contact-audit','final-audit')
    plan=read('insertion-plan.json');scope=read('targeted-routing-scope.json')
    scope_core.validate_scope(scope,plan)
    if phase in ('restore-plan','power-contact-audit'):
        native.p.run_phase(phase,restore if phase=='restore-plan'else power,verify,
            lambda name,value:native.save(DATA/name,value))
    else:
        physical=qualified.bind(native,scope_core,container.clone,plan,scope,Path("/work/tail-source"))
        original_phase=container.clone(targeted.bind_phase(plan,scope),snapshot=canonical_snapshot,connectivity=physical)
        container.clone(native.main,phase=original_phase)()
    verify()
if __name__=='__main__':main()
