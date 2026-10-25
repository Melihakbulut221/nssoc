#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Admit only the exact v59 cd_shunt physical+font+wire capsule; no CAD here."""
import copy,hashlib,json,os,re,shutil,tarfile,tempfile
from collections import Counter
from decimal import Decimal
from pathlib import Path,PurePosixPath
import cloud_cdr_v59_font_recovery as font
import cloud_cdr_v59_annotation_diagnostic as original
import ensure_cloud_tested_source_release as release
from cloud_verified_parts import JoinedParts
from cloud_chunked_results import verify_parts
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/cdr-v59-binding-rc-methods.json'
PIN=ROOT/'docs/evidence/cdr-v59-font-recovery-native-result-20261025.json'
PARTS=ROOT/'docs/evidence/cdr-v59-font-recovery-native-parts-20261025.json'
RUN=40188489346
HEAD='0af252ad92d21799295406ddadde0121bdd5b2fe'
GROUP='cdr-v59-font-recovery'
SUMMARY_SHA='da0ea575f0950c765714f831786ca325cab597dad2df1ed6d65785b1688595f0'
PARTS_SHA='7e6347398f7b9c6d170d4c6c3dcb05b5d02e421b1e8bc1d41e5cf54514a659eb'
ARCHIVE_SHA='f131a19548c21e225b70fd030e0a1965413cff98641b596cd59a9dec4d0348ff'
CAPSULE=ROOT/'hw/soc/out/cloud-cdr-v59-font-recovery'
ANALYSIS=CAPSULE/'analysis-capsule'
CANONICAL_ROOT=Path('/home/runner/work/nssoc/nssoc')
TARGETS=(184,185,222,223)
CENSUS=dict(npn13G2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221)
ASSETS=json.loads(r'''[{"id":674854287,"name":"cdr-v59-font-recovery-40188489346-1.anchors.json","size":1650472,"digest":"sha256:2cf0762a1fe8be50e749266bdaa09c4d10de4a17e8151986bf3356949972a4b2"},{"id":674854339,"name":"cdr-v59-font-recovery-40188489346-1.derived-helper.py","size":13336,"digest":"sha256:6c445c96df3ad83c47b25c977a9fad4b06daad38187cbeb594b6e75c56d7fc24"},{"id":674854213,"name":"cdr-v59-font-recovery-40188489346-1.device-locations.json","size":686516,"digest":"sha256:79ebadf8a36a2be02be680e6d276abbd67c9ddf0bd784a069fa27b96d034e066"},{"id":674853882,"name":"cdr-v59-font-recovery-40188489346-1.font-roundtrip.json","size":72138,"digest":"sha256:6e24a47410af82c015be4cc1a5648241f604d98a2572b25fa8bc4f19e1435b0f"},{"id":674853786,"name":"cdr-v59-font-recovery-40188489346-1.materialization.json","size":104274,"digest":"sha256:0f48663e3010c49c1f1d6eb98fba64f8e8573649ac736a997edc6bd280205e20"},{"id":674853635,"name":"cdr-v59-font-recovery-40188489346-1.parts.json","size":850,"digest":"sha256:7e6347398f7b9c6d170d4c6c3dcb05b5d02e421b1e8bc1d41e5cf54514a659eb"},{"id":674854044,"name":"cdr-v59-font-recovery-40188489346-1.source-pins.json","size":38506,"digest":"sha256:7e79d77f79fdda53b20e9dd3acb92e2e00ca18e56837e578e0d947bdbee1a941"},{"id":674853973,"name":"cdr-v59-font-recovery-40188489346-1.static-source.gds","size":2910,"digest":"sha256:3a9b62c8597335b253671bb135dfcacf2778a71e5a1d62eb59c0ab72345c354f"},{"id":674854136,"name":"cdr-v59-font-recovery-40188489346-1.strict-wire-graph.json","size":290684,"digest":"sha256:2141727fa6bfdc46ed2ab79176180752de8c7612f8b8ed9423ab629fb80500af"},{"id":674853577,"name":"cdr-v59-font-recovery-40188489346-1.summary.json","size":362103,"digest":"sha256:da0ea575f0950c765714f831786ca325cab597dad2df1ed6d65785b1688595f0"},{"id":674853707,"name":"cdr-v59-font-recovery-40188489346-1.tar.gz.part0000","size":24921266,"digest":"sha256:f131a19548c21e225b70fd030e0a1965413cff98641b596cd59a9dec4d0348ff"}]''')
ANCHOR_INPUTS=json.loads(r'''{"/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-v59-font-recovery/analysis-capsule/parent/layout/nssoc_cdr_pd500_resistor_v59.gds":"fb2a773c4d3a3ffab6acfe7718a55fa5db0c2621a6c75377940c95a7989b70b5","/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-v59-font-recovery/analysis-capsule/parent/physical/lvs_flat/result.lvsdb":"e1d74b26b218e92170ed07527db12a0850fbd0a2f039de9283d8a934669b6558","/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-v59-font-recovery/analysis-capsule/wire/anchors01.py":"d7e42e16f91787003a981c9047cff8b91c1810fcdf05b346d0b1e308f730bc38","/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-v59-font-recovery/analysis-capsule/wire/device-locations01.json":"79ebadf8a36a2be02be680e6d276abbd67c9ddf0bd784a069fa27b96d034e066","/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-v59-font-recovery/analysis-capsule/wire/native05/result.json":"2141727fa6bfdc46ed2ab79176180752de8c7612f8b8ed9423ab629fb80500af","/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-v59-font-recovery/analysis-capsule/wire/native05/wires.l2n":"807d3003a1abb98725941cbfab8d48e125bb586e45e6c2147395604ba510c2ee","/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-v59-font-recovery/analysis-capsule/parent/layout/result.json":"4b36c9731972d2bb1f1035ae780fdb2c5692bb32a767dc8369dc1f1fa84cde5b","/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-v59-font-recovery/analysis-capsule/wire/anchors03.json":"7bcb08ab9c8b5ebeaba7b386e1e797af3178c60fdf9d4ef7e8d5b242ec5e801f","/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-v59-font-recovery/analysis-capsule/wire/dedup01.py":"58ec392e70a89e2b4b6175fbef01413e3417b1d5fb1389aabd6fa7b95b743544"}''')

def methods():
    m=json.loads((ROOT/METHOD).read_text())
    assert m['scope']=='FRESH_V59_CD_SHUNT_BINDING_AND_RAW_WIRE_RC_NO_NEW_GEOMETRY_OR_SIMULATION'
    for n,h in m['protected'].items():assert sha(ROOT/n)==h,n
    font.methods()
    assert sha(PIN)==SUMMARY_SHA and sha(PARTS)==PARTS_SHA
    assert m['future_mim']['state']=='UNBOUND_PENDING_FRESH_V59_BINDING_AND_RAW_RC'
    assert m['future_mim']['binding_run']is None and m['future_mim']['raw_rc_run']is None
    return m

def authorize(stage):
    assert stage in ('binding','rc')
    m=methods()
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
    assert m[stage+'_authorized']is True
    assert ROOT==CANONICAL_ROOT,'Exact native anchor root differs'
    return m

def validate_run(r,j):
    assert r['id']==RUN and r['head_sha']==HEAD and r['run_attempt']==1
    assert r['path']=='.github/workflows/cdr-v59-font-recovery-cloud.yml'
    assert r['event']=='workflow_dispatch'and r['status']=='completed'and r['conclusion']=='success'
    expected={121154246625:'controls',121154331539:'saved-font-and-strict-wires'}
    assert j['total_count']==len(j['jobs'])==2 and {v['id']for v in j['jobs']}==set(expected)
    for v in j['jobs']:
        assert v['run_id']==RUN and v['head_sha']==HEAD and v['name']==expected[v['id']]
        assert v['status']=='completed'and v['conclusion']=='success'
    return True

def validate_assets(a):
    keys=('id','name','size','digest')
    assert len(a)==11 and len({v['name']for v in a})==11
    assert sorted([{k:v[k]for k in keys}for v in a],key=lambda v:v['name'])==sorted(ASSETS,key=lambda v:v['name'])
    return True

def validate_manifest(m):
    stem=GROUP+'-'+str(RUN)+'-1'
    assert m['format']=='ordered-tar-gzip-parts-v1'and m['stem']==stem
    assert m['source_directory']=='cloud-cdr-v59-font-recovery'
    assert m['bytes']==24921266 and m['sha256']==ARCHIVE_SHA
    assert m['parts']==[dict(index=0,name=stem+'.tar.gz.part0000',bytes=24921266,sha256=ARCHIVE_SHA)]
    return True

def validate_summary(r,prior=None):
    if prior is not None:assert prior==r
    assert r['status']=='PASS_EXACT_SAVED_FONT_ROUNDTRIP_AND_STRICT_WIRES_REQUIRES_MIM_RC'
    assert r['source_head']==HEAD and r['run_id']==RUN
    for k in ('accepted','geometry_regenerated','physical_checks_rerun','qualified_pex',
      'wire_rc_extracted','electrical_accepted','full_phy_accepted','original_physical_and_planes_rerun'):assert r[k]is False,k
    for k in ('annotation_binding_accepted','strict_wires_executed','original_font_rejection_preserved',
      'all345_restored_files_unchanged','restored_failure_report_unchanged','all339_analysis_originals_unchanged',
      'runtime_unchanged','font_recovery_sources_unchanged'):assert r[k]is True,k
    assert len(r['outputs'])==705 and all(re.fullmatch('[0-9a-f]{64}',h)for h in r['outputs'].values())
    old=json.loads((ROOT/original.REPORT).read_text());original.validate_report(old)
    assert r['original_physical_summary_sha256']==original.SUMMARY_SHA
    assert r['original_physical_status']==old['physical']['status']
    for n,h in old['outputs'].items():assert r['outputs']['analysis-capsule/'+n]==h,n
    assert r['outputs']['analysis-capsule/result.json']==original.SUMMARY_SHA
    assert r['preserved_candidate_gds_sha256']==original.PINNED_OUTPUTS['parent/layout/nssoc_cdr_pd500_resistor_v59.gds']
    assert r['preserved_candidate_reference_sha256']==original.PINNED_OUTPUTS['parent/layout/schematic.cir']
    c=r['font_roundtrip'];n=r['annotation_materialization']
    assert c==json.loads((ROOT/'docs/evidence/cdr-v59-font-recovery-native-font-20261025.json').read_text())
    assert n==json.loads((ROOT/'docs/evidence/cdr-v59-font-recovery-native-materialization-20261025.json').read_text())
    assert c['status']=='PASS_ONLY_EXACT_OBSERVED_FONT2_TO_NoFont_TRANSITION_ALL_OTHER_FIELDS_EXACT'
    assert c['original_failure']['line']==40 and c['original_failure']['original_rejection_preserved']
    assert c['original_failure']['exact_code_object_bound']and c['original_failure']['actual_first_native_and_saved_cell_objects_bound']
    assert len(c['native_controls']['rejected'])==c['native_controls']['positive_exact_saved_copies']==28
    assert len(c['serialized'])==2
    assert all(x['actual_font_fields']['native_font']==2 and x['actual_font_fields']['serialized_font']==-1 for x in c['serialized'])
    assert n['status']=='PASS_STATIC_NATIVE_SIDECAR_AND_UNCHANGED_EXACT_ANNOTATION_RECOVERY_REQUIRES_STRICT_WIRES'
    assert len(n['native_controls']['rejected'])==10 and n['all_original_source_pin_sets_preserved']
    assert n['original_recovery_source_unchanged']and not n['signature_fallback_used']
    assert [(x['label'],x['returncode'])for x in r['commands']]==[
      ('font-native-source-and-exact-recovery',0),('probe01.py',0),('locate01.py',0),('anchors01.py',0),('dedup01.py',0)]
    assert r['strict_wire_graph']==dict(native_device_count=500,native_terminal_count=1446,wire_component_count=113)
    assert r['anchors']==dict(logical_anchor_count=978,public_ports=25,dispositions=dict(
      ACTUAL_TERMINAL_METAL_POINT_REFERENCE=953,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=493))
    assert set(r['complete_reports'])=={'wire/source-pins.json','wire/native05/result.json','wire/device-locations01.json','wire/anchors08.json'}
    for name,v in r['complete_reports'].items():
        assert v['path']=='analysis-capsule/'+name and v['sha256']==r['outputs'][v['path']]and v['bytes']>0
    return r

def expected_files(r):
    validate_summary(r)
    return {**r['outputs'],'result.json':SUMMARY_SHA}

def safe_name(value):
    p=PurePosixPath(value)
    assert value and chr(92)not in value and not p.is_absolute() and '..'not in p.parts
    assert p.as_posix()==value and value not in ('.','..')
    return p

def exact_extract(manifest,parts,destination,expected):
    # Verify every ordered part and the combined archive BEFORE extraction.
    proof=verify_parts(manifest,parts);prefix=manifest['source_directory'];safe_name(prefix)
    assert '/'not in prefix and expected and all(re.fullmatch('[0-9a-f]{64}',h)for h in expected.values())
    for n in expected:safe_name(n)
    assert not destination.exists();destination.mkdir(parents=True)
    seen=set();found={}
    with JoinedParts([parts/p['name']for p in manifest['parts']])as joined:
        with tarfile.open(fileobj=joined,mode='r|gz')as archive:
            for entry in archive:
                name=entry.name.rstrip('/')if entry.isdir()else entry.name
                safe_name(name)
                assert entry.name in (name,name+'/')if entry.isdir()else entry.name==name
                assert name not in seen and (entry.isfile()or entry.isdir()),'Duplicate/nonregular native member'
                seen.add(name)
                if entry.isdir():
                    assert name==prefix or name.startswith(prefix+'/'),'Wrong archive directory root';continue
                assert name.startswith(prefix+'/')
                relative=name[len(prefix)+1:]
                assert relative in expected,'Unexpected native member'
                target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
                digest=hashlib.sha256();count=0
                with archive.extractfile(entry)as src,target.open('xb')as out:
                    while b:=src.read(4*1024**2):out.write(b);digest.update(b);count+=len(b)
                assert count==entry.size and digest.hexdigest()==expected[relative],relative
                found[relative]=dict(bytes=count,sha256=digest.hexdigest())
    assert set(found)==set(expected),'Missing native member'
    return dict(archive=proof,regular_members=len(found),complete_member_hashes=found,full_inventory_verified=True)

def verify_files(root,expected):
    assert root.is_dir()and not root.is_symlink()
    for n,h in expected.items():
        safe_name(n);p=root/n
        assert p.is_file()and not p.is_symlink()and sha(p)==h,n
        assert all(not a.is_symlink()for a in p.parents if a!=root.parent),n
    return dict(files=len(expected),all_hashes_unchanged=True)

def verify_saved_inputs(pin):
    return verify_files(CAPSULE,expected_files(pin))

def validate_targets(devices):
    rows={x['native_id']:x for x in devices}
    assert len(rows)==len(devices)==500 and set(rows)==set(range(1,501))
    for ident in TARGETS:
        d=rows[ident];assert d['model']=='rppd'
        assert {k:Decimal(str(v))for k,v in d['parameters'].items()}=={
          'w':Decimal(4),'l':Decimal(5),'ps':Decimal(0),'b':Decimal(0),'m':Decimal(1)}
    return True

def validate_geometry(pin):
    verify_saved_inputs(pin)
    graph=json.loads((ANALYSIS/'wire/native05/result.json').read_text())
    locations=json.loads((ANALYSIS/'wire/device-locations01.json').read_text())
    anchors=json.loads((ANALYSIS/'wire/anchors08.json').read_text())
    assert graph['status']=='PASS_GEOMETRIC_PUMP_WIRE_COMPONENT_BINDING_NO_RC'
    assert graph['native_devices']==CENSUS and graph['native_device_count']==500
    assert graph['native_terminal_count']==1446 and graph['wire_component_count']==113
    assert graph['native_net_count']==238 and graph['native_electrical_net_count']==114
    assert not any(x['metal_area_dbu2']and not x['device_terminals']for x in graph['native_net_coverage'])
    assert locations['status']=='PASS_ALL_500_DEVICES_HAVE_UNIQUE_PHYSICAL_PCELL_ENCLOSURE'
    assert locations['native_terminal_count']==1446 and Counter(d['model']for d in locations['devices'])==CENSUS
    validate_targets(locations['devices'])
    assert anchors['status']=='PASS_EXACT_PHYSICAL_POINTS_FOR_ALL_LOGICAL_REFERENCES'
    assert anchors['logical_anchor_count']==anchors['physical_anchor_count']==978 and anchors['public_ports']==25
    assert anchors['dispositions']==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=953,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=493)
    assert anchors['inputs']==ANCHOR_INPUTS
    expected=expected_files(pin)
    for report in (graph,locations,anchors):
        for name,value in report['inputs'].items():
            p=Path(name);assert p.is_absolute()and p.is_relative_to(CAPSULE)
            rel=str(p.relative_to(CAPSULE));h=value['sha256']if isinstance(value,dict)else value
            assert expected[rel]==h and sha(p)==h
            if isinstance(value,dict):assert p.stat().st_size==value['bytes']
    return graph,locations,anchors

def restore_saved(pin,stage):
    validate_summary(pin);methods()
    assert ROOT==CANONICAL_ROOT and not CAPSULE.exists()
    run=release.api('actions/runs/'+str(RUN))
    jobs=release.api('actions/runs/'+str(RUN)+'/attempts/1/jobs?per_page=100');validate_run(run,jobs)
    tag='cloud-results-'+str(RUN)+'-1-'+GROUP
    rel=release.api('releases/tags/'+tag);validate_assets(rel['assets'])
    reservation=release.validate_release(rel,release.api('git/ref/tags/'+tag),tag,HEAD)
    # Original physical job remains an authenticated failure with passed physical gates.
    oldrun=release.api('actions/runs/'+str(original.RUN))
    oldjobs=release.api('actions/runs/'+str(original.RUN)+'/attempts/1/jobs?per_page=100')
    original.validate_run(oldrun,oldjobs)
    transport=stage/'source-transport';transport.mkdir(exist_ok=False)
    stem=GROUP+'-'+str(RUN)+'-1'
    base='https://github.com/Melihakbulut221/nssoc/releases/download/'+tag+'/'
    fetch(base+stem+'.summary.json',SUMMARY_SHA,transport/'summary.json')
    assert json.loads((transport/'summary.json').read_text())==pin
    fetch(base+stem+'.parts.json',PARTS_SHA,transport/'parts.json')
    manifest=json.loads((transport/'parts.json').read_text());validate_manifest(manifest)
    for part in manifest['parts']:fetch(base+part['name'],part['sha256'],transport/part['name'])
    proof=exact_extract(manifest,transport,CAPSULE,expected_files(pin))
    for part in manifest['parts']:(transport/part['name']).unlink()
    graph,locations,anchors=validate_geometry(pin)
    return dict(group=GROUP,run=RUN,attempt=1,head=HEAD,summary_sha256=SUMMARY_SHA,
      parts_sha256=PARTS_SHA,release=reservation,restore=proof,original_failed_run=original.RUN,
      original_failed_status_preserved=True,absolute_anchor_inputs_unchanged=True)

def copy_selected(root,destination,names,expected):
    assert len(names)==len(set(names))and all(n in expected for n in names)
    assert not destination.exists();destination.mkdir(parents=True)
    for n in names:
        safe_name(n);src=root/n;assert src.is_file()and not src.is_symlink()and sha(src)==expected[n]
        dst=destination/n;dst.parent.mkdir(parents=True,exist_ok=True)
        with dst.open('xb')as out,src.open('rb')as inp:shutil.copyfileobj(inp,out,4*1024**2)
        assert sha(dst)==expected[n]
    return {n:expected[n]for n in names}

def restore_for_binding(pin,names,stage):
    proof=restore_saved(pin,stage)
    expected={n[len('analysis-capsule/'):]:h for n,h in pin['outputs'].items()if n.startswith('analysis-capsule/')}
    copied=copy_selected(ANALYSIS,stage/'inputs',names,expected)
    return dict(outputs=copied,explicit_rooted_projection_of=SUMMARY_SHA),proof

def restore_for_rc(pin,stage):
    proof=restore_saved(pin,stage)
    expected={n[len('analysis-capsule/'):]:h for n,h in pin['outputs'].items()if n.startswith('analysis-capsule/')}
    graph,locations,anchors=validate_geometry(pin)
    return dict(outputs=expected,strict_wire_graph=graph,anchors=anchors,explicit_rooted_projection_of=SUMMARY_SHA),proof

def validate_bound_targets(binding):
    rows={d['native_id']:d for d in binding['devices']}
    assert len(rows)==len(binding['devices'])==500 and set(rows)==set(range(1,501))
    for ident in TARGETS:
        d=rows[ident];assert d['native_model']==d['model']=='rppd'
        assert {k:Decimal(v)for k,v in d['native_parameters'].items()}==dict(w=Decimal(4),l=Decimal(5),ps=Decimal(0),b=Decimal(0),m=Decimal(1))
        # Original converter already checks the complete model against canonical native SPICE.
        import build_cdr500_cleaned_native_models as models
        assert models.number(d['parameters']['l'])==Decimal('5e-6')and models.number(d['parameters']['w'])==Decimal('4e-6')
    return True

def binding_target_controls(binding):
    validate_bound_targets(binding);rejected=[]
    for ident in TARGETS:
        bad=copy.deepcopy(binding);d=next(d for d in bad['devices']if d['native_id']==ident);d['native_parameters']['l']='7.4'
        try:validate_bound_targets(bad)
        except AssertionError:rejected.append('old_L7_4_device_'+str(ident))
        else:raise AssertionError('Accepted old target length')
    for name,key,value in [('width','w','5'),('compact_length','l','7.4u')]:
        bad=copy.deepcopy(binding);d=next(d for d in bad['devices']if d['native_id']==184)
        d['native_parameters'if name=='width'else'parameters'][key]=value
        try:validate_bound_targets(bad)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Accepted '+name)
    assert len(rejected)==6
    return dict(actual_fresh_binding=True,rejected=rejected)
