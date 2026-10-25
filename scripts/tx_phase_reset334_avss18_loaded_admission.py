#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticate the complete current AVSS18 RC capsule; no CAD or simulation."""
import hashlib,json,subprocess
from pathlib import Path
import cloud_chunked_results as chunks
import tx_phase_reset244_avss18_baseline as frozen
import tx_phase_reset334_avss18_rc_admission as physical
import ensure_cloud_tested_source_release as publication
ROOT=Path(__file__).resolve().parents[1]
SOURCE={'run': 40217002155, 'job': 121240388714, 'head': '881493acb2670dae88b821c45a697f3215df5aeb', 'release': 423554242, 'group': 'tx-phase-reset334-avss18-rc', 'summary': '00ec7ddda92e1545bf6495a6e75287e85ba956a25fd0ced4f9754bbc4c79e067'}
ASSETS={'summary': {'id': 675684027, 'name': 'tx-phase-reset334-avss18-rc-40217002155-1.summary.json', 'size': 2408543, 'sha256': '00ec7ddda92e1545bf6495a6e75287e85ba956a25fd0ced4f9754bbc4c79e067'}, 'parts': {'id': 675684139, 'name': 'tx-phase-reset334-avss18-rc-40217002155-1.parts.json', 'size': 868, 'sha256': '3c5e1d2587387c2ffd134f7f6e0edad7ba3e4db65e8cc1b11ade0f60d3ed4a2c'}, 'archive': {'id': 675684628, 'name': 'tx-phase-reset334-avss18-rc-40217002155-1.tar.gz.part0000', 'size': 70182061, 'sha256': 'cef352f2e67fb8bd01413fc91c31b66895961ccc4101311a9e2fd94adff3b7ed'}}
SUMMARY='docs/evidence/tx-phase-reset334-avss18-rc-native-full-result-20261025.json'
ROOT_NAME='cloud-tx-phase-reset334-avss18-rc'
TAG='cloud-results-'+str(SOURCE['run'])+'-1-'+SOURCE['group']
MODELS={'p': 'bfe98e32e29aacd8defbb46eed28a62286bcc1513db0af1b6f8e1d514e1c8aa4', 'n': '1e5a2f72577c1923d06afa4e74f879ca2f8bd086581c1400188ff5ac7d95c975'}
sha=frozen.sha

def digest(b):return hashlib.sha256(b).hexdigest()

def snapshot():
    raw=(ROOT/SUMMARY).read_bytes()
    assert len(raw)==ASSETS['summary']['size']and digest(raw)==SOURCE['summary']
    r=json.loads(raw);validate(r);return raw,r

def validate(r):
    assert r['source_head']==SOURCE['head']and r['run_id']==SOURCE['run']and r['run_attempt']==1
    assert r['status']=='PASS_FRESH_AVSS18_334_EIGHT_MIM_BOTH_NATIVE_RC_ORDERS_REQUIRES_LOADED'
    assert len(r['outputs'])==2716 and set(r['polarities'])=={'p','n'}
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
    assert run['path']=='.github/workflows/tx-phase-reset334-avss18-rc-cloud.yml'
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
    validate(r);expected=dict(r['outputs']);assert 'result.json'not in expected
    expected['result.json']=SOURCE['summary'];assert len(expected)==2717
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
    p_raw,p=physical.physical()
    assert(destination/'intrinsic/physical/result.json').read_bytes()==p_raw
    for pol in ('p','n'):
        base=destination/'precision'/pol
        assert json.loads((base/'composition/composition.json').read_bytes())==r['polarities'][pol]['composition']
        assert sha(base/'composition/reset334-wire.spice')==MODELS[pol]
        assert json.loads((destination/'intrinsic/physical'/pol/'layout/result.json').read_bytes())==p['variants'][pol]['generation']
    return r,p,dict(metadata=metadata,transport=parts,inventory=inventory,all2717_files_authenticated=True,original_electrical_rejection_preserved=True)
