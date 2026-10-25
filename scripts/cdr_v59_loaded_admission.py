#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact current v59 composition admission for the unchanged ten loaded cases."""
import json,os
from collections import Counter
from pathlib import Path
import cdr_v59_binding_rc_source as saved
import ensure_cloud_tested_source_release as release
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/cdr-v59-loaded-methods.json'
PIN='scripts/cdr-v59-loaded-prerequisites.json'
MODEL='nssoc_cdr_pd500_resistor_mim_wire_v59'
SUMMARY='docs/evidence/cdr-v59-mim-runtime-native-pass-summary-20261025.json'
STAGE='docs/evidence/cdr-v59-mim-runtime-native-pass-stage-20261025.json'
PARTS='docs/evidence/cdr-v59-mim-runtime-native-pass-parts-20261025.json'
def methods():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'
    m=json.loads((ROOT/METHOD).read_bytes())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    assert m['geometry_regeneration_authorized']is False
    assert m['native_extraction_authorized']is False
    assert type(m['preparation_authorized'])is bool and type(m['simulation_authorized'])is bool
    assert m['native_execution_authorized']is m['simulation_authorized']
    return m
def descriptor():return json.loads((ROOT/PIN).read_bytes())
def snapshots():
    methods();p=descriptor()
    out={}
    for key,path in [('summary',SUMMARY),('stage',STAGE),('parts',PARTS)]:
        spec=p['snapshots'][key];f=ROOT/path
        assert str(f.relative_to(ROOT))==spec['path']and f.stat().st_size==spec['bytes']and sha(f)==spec['sha256']
        out[key]=json.loads(f.read_bytes())
    validate_reports(out['summary'],out['stage'])
    return out
def validate_reports(r,s):
    p=descriptor();head=p['run']['head_sha']
    assert r['source_head']==s['source_head']==head
    assert r['status']=='PASS_CURRENT_V59_MIM_TWO_ORDERS_COMPOSITION_REQUIRES_ELECTRICAL_VALIDATION'
    assert r['native_stage_passed']is True and r['command']['returncode']==0
    assert r['stage_result_sha256']==p['snapshots']['stage']['sha256']
    assert r['outputs']['stage/result.json']==r['stage_result_sha256']
    assert all(r[k]is False for k in ('accepted','qualified_pex','electrical_accepted','full_phy_accepted','simulation_executed','geometry_regenerated'))
    assert r['original_publication_failure_preserved']is True
    assert s['status']=='PASS_PD500_MIM_NATIVE_DOUBLE_TOTALS_TWO_ORDERS_22_CONTROLS_EACH_AND21_COMPOSITION_CONTROLS_REQUIRES_LOADED_WAVES'
    assert s['sources_unchanged']is s['both_native_orders_verified']is s['native_rc_and_device_records_equal_in_both_orders']is True
    assert s['qualified_pex']is s['full_phy_accepted']is s['closed_loop']is s['loaded_simulation_passed']is False
    assert set(s['variants'])=={'precise','precise_reversed'}
    for v in s['variants'].values():
        assert len(v['audit']['wire_controls']['cases'])==13 and len(v['audit']['intrinsic_controls'])==9
    assert len(s['composition']['controls'])==21
    c=s['composition']['contract']
    assert c['counts']==dict(devices=500,R=24574,C=15694)
    assert len(c['device_records'])==500 and len(c['interface'])==len(set(c['interface']))==26
    assert Counter(d['model']for d in c['device_records'])==dict(npn13g2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221)
    targets={d['native_id']:d for d in c['device_records']if d['native_id']in (184,185,222,223)}
    assert set(targets)=={184,185,222,223}
    for d in targets.values():
        assert d['model']=='rppd'and d['parameters']==dict(w='4u',l='5u',ps='0u',b='0',m='1',sw_et='1')
    assert c['intrinsic_mim_models_in_final_netlist']==7
    assert c['explicit_mim_device_estimate_double_count_removed']is c['all_raw_wire_tokens_preserved']is True
    assert c['qualified_pex']is c['mim_device_wire_capacitance_separation_qualified']is False
    assert r['saved_input_integrity']==s['current_input_integrity']==dict(all1127_saved_files_unchanged=True,
      original706_unchanged=True,full_binding763_and_rc1136_bundle_hashes_verified=True,canonical_anchor_paths_unchanged=True)
    assert len(r['canonical_capsule_copy'])==1127 and len(r['stage_copy'])==4420
    assert len(r['outputs'])==5548 and len(s['outputs'])==4419
    for name,h in s['outputs'].items():
        assert r['outputs']['stage/'+name]==h
        assert r['stage_copy'][name]['sha256']==h
    return True
def validate_remote(run,jobs,info,ref):
    p=descriptor()
    for k,v in p['run'].items():assert run[k]==v,('run',k)
    expected={j['id']:j for j in p['jobs']}
    assert jobs['total_count']==len(jobs['jobs'])==len(expected)
    for row in jobs['jobs']:
        assert row['id']in expected and row['run_id']==p['run']['id']and row['head_sha']==p['run']['head_sha']
        for k,v in expected[row['id']].items():assert row[k]==v,('job',k)
    assert info['id']==p['release']['id']
    proof=release.validate_release(info,ref,p['release']['tag_name'],p['run']['head_sha'])
    fields=('id','name','size','digest','state')
    actual=sorted([{k:a[k]for k in fields}for a in info['assets']],key=lambda a:a['id'])
    assert actual==sorted(p['assets'],key=lambda a:a['id'])
    return proof
def expected_files():
    r=snapshots()['summary']
    return {**r['outputs'],'result.json':descriptor()['snapshots']['summary']['sha256']}
def verify_restored(out):
    return saved.verify_files(Path(out)/'current-mim-bundle',expected_files())
def restore(out,prepare_only):
    m=methods();assert os.environ.get('GITHUB_RUN_ATTEMPT')=='1'
    assert type(prepare_only)is bool
    assert m['preparation_authorized'if prepare_only else'simulation_authorized']is True
    out=Path(out);assert out.is_dir()and not out.is_symlink()
    p=descriptor();snap=snapshots();runid=p['run']['id'];tag=p['release']['tag_name']
    run=release.api('actions/runs/'+str(runid))
    jobs=release.api('actions/runs/'+str(runid)+'/attempts/1/jobs?per_page=100')
    info=release.api('releases/tags/'+tag);ref=release.api('git/ref/tags/'+tag)
    remote=validate_remote(run,jobs,info,ref)
    transport=out/'current-mim-transport';transport.mkdir(exist_ok=False)
    actual={a['id']:a for a in info['assets']}
    for a in p['assets']:
        dest=transport/a['name'];fetch(actual[a['id']]['browser_download_url'],a['digest'].removeprefix('sha256:'),dest)
        assert dest.stat().st_size==a['size']and sha(dest)==a['digest'].removeprefix('sha256:')
    stem=p['stem']
    for key,suffix in [('summary','.summary.json'),('stage','.stage-result.json'),('parts','.parts.json')]:
        assert (transport/(stem+suffix)).read_bytes()==(ROOT/p['snapshots'][key]['path']).read_bytes()
    bundle=out/'current-mim-bundle'
    archive=saved.exact_extract(snap['parts'],transport,bundle,expected_files())
    assert archive['regular_members']==5549
    assert (bundle/'stage/result.json').read_bytes()==(ROOT/STAGE).read_bytes()
    stage=snap['stage'];prior=stage
    model=bundle/'stage/composition/pd500-mim-wire.spice'
    contract=json.loads((bundle/'stage/composition/composition.json').read_bytes())
    assert contract==stage['composition']['contract']
    plane_path=bundle/'stage/precise/source/native-planes.json'
    planes=json.loads(plane_path.read_bytes())
    assert planes['status']=='PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS'and len(planes['anchors'])==160
    assert len({a['logical_net']for a in planes['anchors']})==51
    binding=json.loads((bundle/'stage/precise/model-binding/binding.json').read_bytes())
    binding_report=json.loads((bundle/'stage/inputs/binding-bundle/stage/result.json').read_bytes())
    assert binding==binding_report['binding'];saved.validate_bound_targets(binding)
    layouts=[v for k,v in planes['inputs'].items()if k.endswith('/layout/result.json')]
    assert layouts==[sha(bundle/'stage/precise/source/parent/layout/result.json')]
    assert all(sha(bundle/('stage/'+name))==h for name,h in stage['outputs'].items())
    verify_restored(out)
    proof=dict(run=runid,source_head=p['run']['head_sha'],reservation=remote,full_archive=archive,
      summary_sha256=p['snapshots']['summary']['sha256'],stage_sha256=p['snapshots']['stage']['sha256'],
      original_publication_failure_preserved=True,geometry_regenerated=False,simulation_preaccepted=False)
    plane_proof=dict(current_mim_source=proof['stage_sha256'],native_planes_sha256=sha(plane_path),
      fresh_layout_sha256=layouts[0],native_binding_sha256=sha(bundle/'stage/precise/model-binding/binding.json'))
    return prior,proof,model,contract,planes,plane_proof
