#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Adapt source admission only; run the byte-exact existing postroute flow."""
import argparse,ast,hashlib,importlib.util,json,os,sys,traceback
from pathlib import Path
import mainchip_saved_postroute_admission as admission
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-mainchip-route12-postroute'
PROGRAM=ROOT/'cloud-mainchip-saved-postroute-program'
GEOMETRY='scripts/cloud_mainchip_route12_postroute_geometry.py'
POSTROUTE='scripts/cloud_mainchip_route12_postroute.py'
EDITS=[
('from check_mainchip_route12_completed_source import validate',
 'from mainchip_saved_postroute_admission import validate,verify_archive'),
("names=['work/detailed-route.odb','work/detailed-route.drc','work/native.log','work/boots.log','work/before-guide-read.odb','work/drt-done']",
 "names=['work/detailed-route.odb','work/detailed-route.drc','work/native.log','work/boots.log','work/before-guide-read.odb','work/drt-done','inner-controller-result.json','current-inputs-before.json','current-inputs-after.json','no-gdb-runtime-result.json']"),
("        controller='scripts/cloud_mainchip_route12_drt'+('_continuation'if 'continuation' in live['path']else'')+'.py'\n        assert source_hash(controller,selected['source_head'])==selected['controller_sha256']==sha(ROOT/controller)\n",
 "        r['completed_saved_source_binding']=verify_archive(selected,actual,OUT/'routed')\n        actual=actual['native_inner_report']\n")
]
def derive():
    m=admission.methods();old=(ROOT/GEOMETRY).read_text()
    assert hashlib.sha256(old.encode()).hexdigest()==m['protected'][GEOMETRY]
    new=old
    for a,b in EDITS:
        assert new.count(a)==1;new=new.replace(a,b)
    inverse=new
    for a,b in reversed(EDITS):
        assert inverse.count(b)==1;inverse=inverse.replace(b,a)
    assert inverse==old
    ast.parse(new)
    exact=(ROOT/POSTROUTE).read_bytes()
    assert hashlib.sha256(exact).hexdigest()==m['protected'][POSTROUTE]
    return new,exact,dict(geometry_old_sha256=hashlib.sha256(old.encode()).hexdigest(),
        geometry_derived_sha256=hashlib.sha256(new.encode()).hexdigest(),
        geometry_exact_reversible_edits=3,postroute_byte_exact_sha256=hashlib.sha256(exact).hexdigest(),
        topology_clock_antenna_RC_STA_algorithms_unchanged=True)
def source_controls():
    m=admission.methods();new,exact,proof=derive()
    assert type(m['native_execution_authorized'])is bool
    from check_final_native_antenna_counts import controls as antennas
    from cloud_mainchip_route12_postroute import controls as timing
    from check_mainchip_route12_completed_source import controls as old_completed
    import ensure_cloud_tested_source_release as release
    return dict(status='PASS_SAVED_POSTROUTE_SOURCE_ADMISSION_ORIGINAL_GATES_NOT_NATIVE',
        source_head=os.environ['GITHUB_SHA'],protected_files=len(m['protected']),
        derivation=proof,admission=admission.controls(),original_timing=timing(),
        original_antenna=antennas(),original_direct_admission=old_completed(),
        publication_release=release.controls(),native_execution=False,
        final_timing_complete=False,full_phy_accepted=False)
def main():
    assert os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');args=p.parse_args()
    if args.controls:
        r=source_controls();dest=ROOT/'cloud-mainchip-saved-postroute-controls';dest.mkdir(exist_ok=False)
        (dest/'result.json').write_text(json.dumps(r,indent=2)+'\n')
        print(json.dumps(r,indent=2),flush=True);return
    m=admission.methods();assert m['native_execution_authorized']is True
    assert json.loads(os.environ['NSSOC_COMPLETED_DRT'])==admission.SPEC
    program,exact,proof=derive();PROGRAM.mkdir(exist_ok=False)
    gpath=PROGRAM/'geometry.py';gpath.write_text(program)
    ppath=PROGRAM/'postroute.py';ppath.write_bytes(exact)
    def module(name,path):
        spec=importlib.util.spec_from_file_location(name,path)
        value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
    geometry=module('cloud_mainchip_route12_postroute_geometry',gpath)
    sys.modules['cloud_mainchip_route12_postroute_geometry']=geometry
    postroute=module('nssoc_exact_original_postroute',ppath)
    sys.argv=[str(ppath)]
    try:postroute.main()
    finally:
        if(OUT/'result.json').is_file():
            r=json.loads((OUT/'result.json').read_bytes())
            r['saved_source_adapter']=proof
            r['historical_sources_unchanged_proven']=False
            r['old_scheduling_perturbation_retained']=True
            r['original_physical_and_timing_thresholds_unchanged']=True
            r['final_timing_complete']=False;r['full_phy_accepted']=False
            (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
        admission.methods()
if __name__=='__main__':main()
