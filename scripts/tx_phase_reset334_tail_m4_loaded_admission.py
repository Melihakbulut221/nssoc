#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticate all3181 current M4 RC files and the exact native3165 view; no CAD or simulation."""
import hashlib,json,subprocess
from pathlib import Path
import cloud_chunked_results as chunks
import tx_phase_reset244_avss18_baseline as frozen
import tx_phase_reset334_tail_m4_rc_admission as physical
import ensure_cloud_tested_source_release as publication
ROOT=Path(__file__).resolve().parents[1]
SOURCE={'run': 40389279496, 'job': 121806403483, 'head': '7cce8a3f959fe2c71452c757296d3951f857bedf', 'release': 424685864, 'group': 'tx-phase-reset334-tail-m4-rc', 'summary': '06db4d7a1bd50396e449c11e5c08660c619db7c5655003f731e23e6e610310cb'}
ASSETS={'summary': {'id': 679269684, 'name': 'tx-phase-reset334-tail-m4-rc-40389279496-1.summary.json', 'size': 3091157, 'sha256': '06db4d7a1bd50396e449c11e5c08660c619db7c5655003f731e23e6e610310cb'}, 'native': {'id': 679270543, 'name': 'native-RC-result.json', 'size': 2485576, 'sha256': '0da5676f4b4b9cabaf4119a8cb94492e5f0d8d6f5686ae0633d51a51562ff240'}, 'parts': {'id': 679269844, 'name': 'tx-phase-reset334-tail-m4-rc-40389279496-1.parts.json', 'size': 874, 'sha256': 'a8aa64ca1aa1e4af91e1a1082439bb3a5ac80454f985bffc81564fa2e1d70bad'}, 'archive': {'id': 679270999, 'name': 'tx-phase-reset334-tail-m4-rc-40389279496-1.tar.gz.part0000', 'size': 125252895, 'sha256': '1973a6c4f6e5707d035d88e5dc5c48ddf7ec3b988b3f787df0f49a384e8dd8d0'}}
SUMMARY='docs/evidence/tx-phase-reset334-tail-M4-RC-native-pass-20261026-summary.json'
NATIVE='docs/evidence/tx-phase-reset334-tail-M4-RC-native-pass-20261026-native-result.json'
ROOT_NAME='cloud-tx-phase-reset334-tail-m4-rc'
TAG='cloud-results-'+str(SOURCE['run'])+'-1-'+SOURCE['group']
MODELS={'p': '474987ee48116c9ca825f526fa6eb36c66244307994c414c3dac7854afb63306', 'n': '75f73b6868707cdcc4386e7a41d2ee877344af7702cf412aa5e5d04edb5dda09'}
sha=frozen.sha

def digest(b):return hashlib.sha256(b).hexdigest()

def native_snapshot():
    raw=(ROOT/NATIVE).read_bytes()
    assert len(raw)==ASSETS['native']['size']and digest(raw)==ASSETS['native']['sha256']
    r=json.loads(raw);validate(r);return raw,r

def snapshot():
    raw=(ROOT/SUMMARY).read_bytes()
    assert len(raw)==ASSETS['summary']['size']and digest(raw)==SOURCE['summary']
    r=json.loads(raw);_,native=native_snapshot();validate_outer(r,native);return raw,r

def validate_outer(r,native):
    validate(native)
    assert (r['source_head'],r['run_id'],r['run_attempt'])==(SOURCE['head'],SOURCE['run'],1)
    assert r['status']==native['status'] and r['native_result']==native
    assert r['native_result_present']is True and r['native_result_raw_path']=='native-RC-result.json'
    assert r['native_result_sha256']==ASSETS['native']['sha256']and r['native_result_bytes']==ASSETS['native']['size']
    for key in ('native_extraction_completed','both_orders_qualified','fresh_current_four_OP_and_original_loaded_waveforms_required','protected_sources_unchanged','original_electrical_rejection_preserved'):assert r[key]is True,key
    for key in ('electrical_accepted','full_phy_accepted','simulation_executed','geometry_generation_executed','continuation_executed','zero_op_executed','old_R_rescaled'):assert r[key]is False,key
    s=r['supervisor']
    assert s['returncode']==0 and s['supervision_failure']is None and s['memory_read_error']is None
    assert s['process_group_cleanup']['remaining_live']==[]
    assert s['minimum_available_kib']==2097152 and s['maximum_group_rss_kib']==10485760
    assert len(r['outputs'])==3180 and 'result.json'not in r['outputs']
    native_view={p[len('native/'):]:h for p,h in r['outputs'].items()if p.startswith('native/')}
    expected=dict(native['outputs']);expected['result.json']=ASSETS['native']['sha256']
    assert len(expected)==3165 and native_view==expected
    assert r['outputs']['native-RC-result.json']==ASSETS['native']['sha256']
    for name,stage in (('fresh-intrinsic-result.json','intrinsic'),('fresh-two-order-result.json','precision')):
        assert r['outputs'][name]==native['outputs'][name]==native['stages'][stage]['source_sha256']
    physical_raw,physical_outer=physical.physical();native_raw,physical_native=physical.native_physical()
    assert native['original_physical_source']==physical.SOURCE
    full_physical=physical.expected_files(physical_outer)
    assert len(full_physical)==631
    assert all(r['outputs']['native/intrinsic/physical/'+p]==h for p,h in full_physical.items())
    assert r['outputs']['native/intrinsic/physical/native/result.json']==digest(native_raw)
    assert r['outputs']['native/intrinsic/physical/result.json']==digest(physical_raw)
    return True

def validate(r):
    assert r['source_head']==SOURCE['head']and r['run_id']==SOURCE['run']and r['run_attempt']==1
    assert r['status']=='PASS_FRESH_TAIL_M4_334_EIGHT_MIM_BOTH_NATIVE_RC_ORDERS_REQUIRES_LOADED'
    assert len(r['outputs'])==3164 and set(r['polarities'])=={'p','n'}
    assert r['protected_sources_unchanged']and r['original_electrical_rejection_preserved']
    assert r['fresh_native_RC_extracted']and r['both_polarities_and_orders_verified']
    assert r['original_13_wire_9_MIM_faults_each_order_and19_composition_faults_preserved']
    for k in ('accepted','qualified_pex','electrical_accepted','physical_reset_qualified','all31_clock_tree_accepted','PLL_connected','full_phy_accepted','simulation_executed','geometry_generation_executed','old_R_rescaled'):assert r[k]is False
    for pol,p in r['polarities'].items():
        assert p['sources_unchanged']and set(p['orders'])=={'precise','precise_reversed'}
        assert p['native_order_equivalence']['symmetric_endpoint_value_multiset_exact']
        assert p['native_order_equivalence']['non_coupling_records_unchanged']and p['native_order_equivalence']['original_order_restored']
        c=p['composition'];assert c['model_sha256']==MODELS[pol]==r['outputs']['precision/'+pol+'/composition/reset334-wire.spice']
        assert c['positive']==dict(devices=334,wire_resistors=1347,wire_capacitors=2545,terminals=1010,wire_components=119,body_nodes=1,ports=['CLKP','CLKN','MP','MN','QP','QN','ARM_P','ARM_N','DIV_AVDD','AVSS','SUB','wire_cref'])
        assert len(c['controls'])==19 and all(f['rejected']for f in c['controls'])
        assert c['all_raw_wire_tokens_preserved']and c['intrinsic_mim_models_exactly_once']
        assert len(c['bindings'])==334 and len({x['native_id']for x in c['bindings']})==334
        for name,o in p['orders'].items():
            a=o['audit'];assert o['native']['returncode']==0 and not o['native']['elapsed_timeout']
            assert len(o['wire_controls']['cases'])==13 and all(f['rejected_by']for f in o['wire_controls']['cases'])
            assert len(o['mim_controls'])==9 and all(f['rejected']for f in o['mim_controls'])
            assert [a[k]for k in ('original_devices','physical_wire_components','geometry_probes','metal_device_terminals','unmodeled_body_well_terminals','actual_exported_resistors','actual_exported_capacitors')]==[334,119,695,684,326,1347,2545]
            assert a['disconnected_probes']==[]
            for k in ('native_export_r_edge_value_multiset_exact','geometry_conductor_ownership_exact','every_native_point_ground_capacitance_preserved','every_native_mutual_attachment_and_value_preserved','complete_collapsed_capacitance_conserved','per_conductor_intrinsic_ground_c_conserved','no_intrinsic_alias_edges_inserted_in_resistance_graph'):assert a[k]
    return True

def validate_metadata(run,job,info,ref):
    assert run['id']==SOURCE['run']and run['head_sha']==SOURCE['head']and run['run_attempt']==1
    assert run['status']=='completed'and run['conclusion']=='success'
    assert run['path']=='.github/workflows/tx-phase-reset334-tail-m4-rc-cloud.yml'
    assert run['head_branch']=='codex/phase318-saved-capture-diagnosis'
    assert job['id']==SOURCE['job']and job['run_id']==SOURCE['run']and job['head_sha']==SOURCE['head']
    assert job['run_attempt']==1 and job['status']=='completed'and job['conclusion']=='success'
    assert info['id']==SOURCE['release'];publication.validate_release(info,ref,TAG,SOURCE['head'])
    for a in ASSETS.values():
        matches=[x for x in info['assets']if x['name']==a['name']];assert len(matches)==1
        x=matches[0];assert x['id']==a['id']and x['size']==a['size']and x['state']=='uploaded'and x['digest']=='sha256:'+a['sha256']
    return True

def prerequisite():
    raw,r=snapshot()
    run=frozen.api('actions/runs/'+str(SOURCE['run']));job=frozen.api('actions/jobs/'+str(SOURCE['job']))
    info=frozen.api('releases/'+str(SOURCE['release']));ref=frozen.api('git/ref/tags/'+TAG)
    validate_metadata(run,job,info,ref)
    assert frozen.raw_asset(ASSETS['summary'])==raw
    return r,dict(run=run,job=job,release=info,tag=ref)

def expected_files(r):
    _,native=native_snapshot();validate_outer(r,native)
    expected=dict(r['outputs']);assert 'result.json'not in expected
    expected['result.json']=SOURCE['summary'];assert len(expected)==3181
    return expected

def restore(destination):
    raw,r=snapshot();_,metadata=prerequisite()
    transport=destination.parent/'current-RC-transport';transport.mkdir(exist_ok=False)
    (transport/'summary.json').write_bytes(raw)
    b=frozen.raw_asset(ASSETS['parts']);(transport/'parts.json').write_bytes(b);m=json.loads(b);a=ASSETS['archive']
    assert m['format']=='ordered-tar-gzip-parts-v1'and m['source_directory']==ROOT_NAME
    assert m['stem']==SOURCE['group']+'-'+str(SOURCE['run'])+'-1'
    assert m['bytes']==a['size']and m['sha256']==a['sha256']
    assert m['parts']==[dict(index=0,name=a['name'],bytes=a['size'],sha256=a['sha256'])]
    part=transport/a['name']
    with part.open('xb')as output:
        subprocess.run(['gh','api','--allow-escape-sequences','-H','Accept: application/octet-stream','repos/'+frozen.REPO+'/releases/assets/'+str(a['id'])],stdout=output,check=True)
    parts=chunks.verify_parts(m,transport)
    inventory=frozen.audit_archive(part,expected_files(r),destination,ROOT_NAME)
    assert(destination/'result.json').read_bytes()==raw
    native_raw,native=native_snapshot();native_root=destination/'native'
    assert(native_root/'result.json').read_bytes()==native_raw
    assert(destination/'native-RC-result.json').read_bytes()==native_raw
    p_raw,p_outer=physical.physical();p_native_raw,p_native=physical.native_physical()
    assert(native_root/'intrinsic/physical/result.json').read_bytes()==p_raw
    assert(native_root/'intrinsic/physical/native/result.json').read_bytes()==p_native_raw
    for pol in ('p','n'):
        base=native_root/'precision'/pol
        assert json.loads((base/'composition/composition.json').read_bytes())==native['polarities'][pol]['composition']
        assert sha(base/'composition/reset334-wire.spice')==MODELS[pol]
        assert json.loads((native_root/'intrinsic/physical/native'/pol/'layout/result.json').read_bytes())==p_native['variants'][pol]['generation']
    return native,p_native,dict(metadata=metadata,transport=parts,inventory=inventory,
      outer_summary_sha256=SOURCE['summary'],native_summary_sha256=digest(native_raw),
      complete_files=3181,native_view_files=3165,all3181_files_authenticated=True,
      consumed_native_view='native',full_current_physical_files=631,
      original_electrical_rejection_preserved=True)
