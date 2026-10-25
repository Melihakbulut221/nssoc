#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reserved-only publication of the complete current-geometry MIM experiment."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
import cdr_v59_mim_admission as a
import cloud_cdr_v59_binding_rc as evidence
import migrate_outputs_to_cloud as publisher
import ensure_cloud_tested_source_release as release
from cloud_cdr500_resistor_v59_physical import precreated
from cloud_chunked_results import pack,verify_parts
ROOT=a.ROOT
GROUP='cdr-v59-mim-precision'
PASS='PASS_PD500_MIM_NATIVE_DOUBLE_TOTALS_TWO_ORDERS_22_CONTROLS_EACH_AND21_COMPOSITION_CONTROLS_REQUIRES_LOADED_WAVES'
BUNDLE=ROOT/'hw/soc/out/cloud-cdr-v59-mim-evidence'
TRANSPORT=ROOT/'hw/soc/out/cloud-cdr-v59-mim-publication'
def validate_pipeline(r,code):
    assert code==0 and r['status']==PASS and r['source_head']==os.environ['GITHUB_SHA']
    assert r['sources_unchanged']is True and r['both_native_orders_verified']is True
    assert r['native_rc_and_device_records_equal_in_both_orders']is True
    for k in ('qualified_pex','full_phy_accepted','closed_loop','loaded_simulation_passed'):assert r[k]is False
    assert set(r['variants'])=={'precise','precise_reversed'}
    for name,pair in r['variants'].items():
        c=pair['capture'];audit=pair['audit']
        assert c['native_order_variant']==name and c['sources_unchanged']and audit['sources_unchanged']
        assert c['capture']['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT'and c['capture']['returncode']==0
        assert c['native_binding']['actual_mim_devices']==7 and c['native_binding']['actual_mim_masks_exact']
        assert c['native_binding']['original_metal_and_vias_unchanged']
        assert c['native_binding']['all978points_match_original_native_clusters_and_physical_components']
        assert len(c['native_binding']['point_changes'])==7 and len(c['controls'])==5 and all(v['rejected']for v in c['controls'])
        assert c['intrinsic_capture_binding']['physical_components']==113 and c['intrinsic_capture_binding']['physical_points']==978
        assert len(c['intrinsic_capture_binding']['native_mim_devices'])==7
        assert audit['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
        assert len(audit['wire_controls']['cases'])==13 and len(audit['intrinsic_controls'])==9
        assert all(v['rejected']for v in audit['intrinsic_controls'])
    comp=r['composition'];assert len(comp['controls'])==21 and all(v['rejected']for v in comp['controls'])
    assert comp['contract']['counts']['devices']==500 and comp['contract']['intrinsic_mim_models_in_final_netlist']==7
    assert comp['contract']['all_raw_wire_tokens_preserved']is True
    assert comp['non_cascading_count_derivation']['reverse_reconstruction_exact']is True
    assert len(r['count_derivation_controls']['positive_collision_cases'])==len(r['count_derivation_controls']['rejected'])==4
    return True
def publish_existing(result):
    stem=GROUP+'-'+os.environ['GITHUB_RUN_ID']+'-'+os.environ['GITHUB_RUN_ATTEMPT']
    TRANSPORT.mkdir(parents=True,exist_ok=False)
    summary=TRANSPORT/(stem+'.summary.json');shutil.copyfile(BUNDLE/'result.json',summary)
    assert a.sha(summary)==a.sha(BUNDLE/'result.json')
    evidence.emit(summary,'CDR_V59_MIM_RESULT')
    pub=dict(status='RUNNING',summary_sha256=a.sha(summary),assets=[])
    a.write(TRANSPORT/'publication.json',pub)
    try:
        packed=pack(BUNDLE,stem,TRANSPORT,512*1024**2)
        pub['archive']=verify_parts(packed,TRANSPORT)
        manifest=TRANSPORT/(stem+'.parts.json')
        files=evidence.publication_files(TRANSPORT,summary,manifest,packed)
        full=BUNDLE/'stage/result.json'
        if full.is_file():
            target=TRANSPORT/(stem+'.stage-result.json');shutil.copyfile(full,target)
            assert a.sha(target)==a.sha(full);files.append(target)
        tag,_=release.context(GROUP,os.environ)
        old=publisher.release;publisher.release=evidence.only_reserved(GROUP,os.environ,release.api)
        try:
            for path in files:
                before=a.sha(path);pub['assets'].append(publisher.publish(path,tag))
                assert a.sha(path)==before
                a.write(TRANSPORT/'publication.json',pub)
        finally:publisher.release=old
        pub['status']='PASS_COMPLETE_CURRENT_MIM_EVIDENCE_PUBLISHED'
    except BaseException as error:
        pub.update(status='FAIL_PUBLICATION',error=repr(error));raise
    finally:a.write(TRANSPORT/'publication.json',pub)
    return pub
def main():
    p=argparse.ArgumentParser();p.add_argument('--preflight',action='store_true');p.add_argument('--publish-only',action='store_true');args=p.parse_args()
    a.authorize();reservation=precreated(GROUP,wait=True)
    assert not(args.preflight and args.publish_only)
    if args.preflight:print(json.dumps(reservation,indent=2));return
    if args.publish_only:
        BUNDLE.mkdir(parents=True,exist_ok=True)
        if not(BUNDLE/'result.json').exists():
            a.write(BUNDLE/'result.json',dict(status='FAIL_BEFORE_NATIVE_RESULT',source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1,native_stage_passed=False,accepted=False,qualified_pex=False,electrical_accepted=False,full_phy_accepted=False))
        publish_existing(json.loads((BUNDLE/'result.json').read_text()));return
    assert not BUNDLE.exists()and not TRANSPORT.exists()and not a.OUT.exists()and not a.saved.CAPSULE.exists()
    BUNDLE.mkdir(parents=True)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),run_attempt=1,
      reservation=reservation,native_stage_passed=False,accepted=False,qualified_pex=False,electrical_accepted=False,
      full_phy_accepted=False,simulation_executed=False,geometry_regenerated=False,
      original_publication_failure_preserved=True)
    a.write(BUNDLE/'result.json',r)
    try:
        command=[sys.executable,str(ROOT/'scripts/cloud_cdr_v59_mim_precision.py')]
        with (BUNDLE/'controller.log').open('wb')as stream:
            code=subprocess.call(command,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=stream,stderr=subprocess.STDOUT)
        r['command']=dict(argv=command,returncode=code,sha256=a.sha(BUNDLE/'controller.log'))
        if code:print((BUNDLE/'controller.log').read_text(errors='replace')[-20000:],flush=True)
        report=json.loads((a.OUT/'result.json').read_text());r['native_status']=report['status']
        r['stage_result_sha256']=a.sha(a.OUT/'result.json');validate_pipeline(report,code)
        r['saved_input_integrity']=a.verify_restored();a.methods()
        r.update(status='PASS_CURRENT_V59_MIM_TWO_ORDERS_COMPOSITION_REQUIRES_ELECTRICAL_VALIDATION',native_stage_passed=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error))
    finally:
        try:
            if a.saved.CAPSULE.exists():
                r['saved_input_integrity']=a.verify_restored()
                r['canonical_capsule_copy']=evidence.copy_tree(a.saved.CAPSULE,BUNDLE/'canonical-source-capsule')
            if a.OUT.exists():r['stage_copy']=evidence.copy_tree(a.OUT,BUNDLE/'stage')
        except BaseException as error:
            r.update(status='FAIL_INTEGRITY_OR_EVIDENCE_COPY',native_stage_passed=False,evidence_error=repr(error))
            # Keep every partial native output available to the workflow fallback.
        r['outputs']={str(q.relative_to(BUNDLE)):a.sha(q)for q in BUNDLE.rglob('*')if q.is_file()and q!=BUNDLE/'result.json'}
        a.write(BUNDLE/'result.json',r)
    assert r['native_stage_passed']is True,r.get('error',r['status'])
if __name__=='__main__':main()
