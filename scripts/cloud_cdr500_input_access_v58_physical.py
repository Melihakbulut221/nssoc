#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh native physical/wire qualification of the reviewed CDR500 access delta."""
import argparse, ast, importlib.util, json, os, shutil, subprocess, sys, tarfile, traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch, sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-cdr500-input-access-v58-physical'
OLD='nssoc_cdr_pd500_active_input_v57'
TOP='nssoc_cdr_pd500_input_access_v58'
APP_SHA='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'

def derive(text, edits):
    original=text;changes=[]
    for a,b in edits:
        count=text.count(a);assert count>0 and b not in text,(a,count)
        text=text.replace(a,b);changes.append(dict(before=a,after=b,count=count))
    reversed_text=text
    for v in reversed(changes):
        assert reversed_text.count(v['after'])==v['count']
        reversed_text=reversed_text.replace(v['after'],v['before'])
    assert reversed_text==original
    ast.parse(text)
    return text,changes

def native(which):
    sys.path.insert(0,str(OUT/'methods'))
    module=__import__('cdr_v58_'+which)
    module.OUT=OUT;module.ROOT=ROOT
    getattr(module,'native'if which=='planes'else'recover')()

def main():
    p=argparse.ArgumentParser();p.add_argument('--native',choices=('planes','recover'));p.add_argument('--serialization-diagnostic',action='store_true');args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.native:native(args.native);return
    assert os.environ['GITHUB_RUN_ATTEMPT']=='1'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,qualified_pex=False,wire_rc_extracted=False,loaded_simulation_started=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(command,name):
        log=OUT/(name+'.log')
        with log.open('w')as stream:rc=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(name=name,returncode=rc,log_sha256=sha(log)));save()
        if rc:print(log.read_text(errors='replace')[-20000:],flush=True)
        assert rc==0,(name,rc)
    save()
    try:
        method=json.loads((ROOT/'scripts/cdr500-input-access-v58-methods.json').read_text())
        required=dict(method['protected'])
        required.update(json.loads((ROOT/'scripts/cdr500-input-access-v58-physical-methods.json').read_text())['protected'])
        assert all(sha(ROOT/n)==v for n,v in required.items())
        protected={str(ROOT/n):v for n,v in required.items()}
        pin=json.loads((ROOT/'docs/evidence/cdr500-floating-wire-cleanup-pass-20261024.json').read_text())
        selected=[n for n in pin['report']['outputs']if n.startswith('parent/')or n in ('wire/native05/wires.l2n','wire/native05/result.json','wire/probe01.py','wire/locate01.py','wire/anchors01.py','wire/dedup01.py')]
        prior,proof=reports.restore_report('cdr500-floating-wire-cleanup',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',selected)
        assert prior==pin['report']and prior['sources_unchanged']
        assert prior['status']=='PASS_PD500_FLOATING_ROOT_CLEANUP_FULL_PHYSICAL_AND_UNCHANGED_STRICT_WIRES_REQUIRES_FRESH_RC'
        r['cleaned_physical_source']=proof
        assert sha(OUT/'source/parent/layout'/(OLD+'.gds'))=='e6ab61471595cd3635c8e2ef3922a09d6b128db0a5338fd6106f3a8e4aefc2f3'
        dpin=json.loads((ROOT/'docs/evidence/cdr500-input-path-diagnosis-pass-20261024.json').read_text())
        (OUT/'diagnosis').mkdir()
        diagnostic=OUT/'diagnosis/result.json'
        diagnostic_url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-40085495203-1-cdr500-input-path-diagnosis/cdr500-input-path-diagnosis-40085495203-1.summary.json'
        fetch(diagnostic_url,dpin['summary_sha256'],diagnostic)
        observed=json.loads(diagnostic.read_text())
        assert sha(diagnostic)==dpin['summary_sha256']and observed['source_head']==dpin['source_head']
        assert observed['status']==dpin['status']and observed['sources_unchanged']
        r['owned_path_source']=dict(run=dpin['run'],source_head=dpin['source_head'],summary_sha256=sha(diagnostic),summary_url=diagnostic_url,source_archive_previously_verified=dpin['small_archive_fully_verified_in_memory'])
        survey=OUT/'diagnosis/native-sampler-survey.json'
        survey_url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-40093754159-1-cdr500-input-access-v58-corridors/cdr500-input-access-v58-corridors-40093754159-1.summary.json'
        survey_sha='2e41ff33706aea82769eaa9d9afacec1f373916c2dbd3866f63b2233bd3c4e54'
        fetch(survey_url,survey_sha,survey)
        measured=json.loads(survey.read_text())
        assert measured['source_head']=='6dfc9392b6327a73a6ef265c492bf3eccefd4d98'and measured['sources_unchanged']
        assert measured['status']=='PASS_READ_ONLY_NATIVE_ALL_PRIMITIVES_CORRIDOR_DIAGNOSIS_NOT_PHYSICAL_RC_OR_ELECTRICAL_ACCEPTANCE'
        assert not measured['accepted']and not measured['geometry_survey']['candidate_gds_written']
        protected[str(survey)]=survey_sha
        r['native_geometry_selection_source']=dict(run=40093754159,source_head=measured['source_head'],summary_sha256=survey_sha,summary_url=survey_url,physical_accepted=False)
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==APP_SHA
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink()
        runtime=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
        assert all(sha(Path(n))==h for n,h in protected.items())
        parent=OUT/'parent';parent.mkdir();shutil.copytree(OUT/'source/parent/inputs',parent/'inputs');shutil.copyfile(OUT/'source/parent/children.json',parent/'children.json')
        run([app,'python',ROOT/'scripts/generate_cdr500_input_access_v58.py','--physical',OUT/'source','--diagnosis',diagnostic,'--survey',survey,'--pdk',ROOT/'pdk','--out',parent/'layout'],'generation')
        if args.serialization_diagnostic:
            r.update(status='REPORT_ONLY_GENERATION_COMPLETED_ORIGINAL_GATES_PASSED_NO_PHYSICAL_STARTED',sources_unchanged=all(sha(Path(n))==v for n,v in protected.items()))
            assert r['sources_unchanged']
            return
        layout=parent/'layout';delta=json.loads((layout/'result.json').read_text())
        assert len(delta['controls'])==9 and delta['added_via_instances']==24
        assert len(delta['native_survey_selection_controls'])==8 and delta['added_route_rectangles']==20
        assert delta['original_sampler_via1_via2_material_preserved']and delta['native_survey_sha256']==survey_sha
        assert len(delta['high_endpoint_cut_controls'])==3 and delta['original_high_endpoint_two_cut_sets_preserved']==8
        assert delta['original_children_drawings_and_placements_preserved']and delta['original_public_labels_and_boundary_preserved']and delta['serialized_metal_and_via_delta_exact']
        assert delta['all_intrinsic_device_bias_and_stimulus_sources_unchanged']and not delta['reduced_resistance_claim']
        (OUT/'candidate-delta.json').write_text(json.dumps(delta,indent=2)+'\n');r['candidate_delta']=delta;save()
        names={}
        for old,new in [(OLD+'.lef',TOP+'.lef'),('schematic.cir','schematic.cir')]:
            original=(OUT/'source/parent/layout'/old).read_text();assert TOP not in original and original.count(OLD)>0
            changed=original.replace(OLD,TOP);assert changed.replace(TOP,OLD)==original
            (layout/new).write_text(changed);names[old]=dict(old_sha256=sha(OUT/'source/parent/layout'/old),new_sha256=sha(layout/new),only_parent_name_replaced=True,replacements=original.count(OLD))
        meta=json.loads((OUT/'source/parent/layout/result.json').read_text())
        meta['status']='GENERATED_PD500_REAL_INPUT_ACCESS_V58_REQUIRES_NATIVE_VALIDATION'
        meta['input_access_v58']=delta
        meta['inputs']=dict(delta['input_sha256'])
        meta['inputs'].update({str(OUT/'source/parent/layout'/n):sha(OUT/'source/parent/layout'/n)for n in (OLD+'.lef','schematic.cir','result.json')})
        meta['outputs']={p.name:sha(p)for p in layout.iterdir()if p.is_file()and p.name!='result.json'}
        (layout/'result.json').write_text(json.dumps(meta,indent=2)+'\n');r['boundary_name_adaptations']=names
        methods=OUT/'methods';methods.mkdir();adapt={}
        sources={
          'check_physical.py':('hw/soc/flow/check_pcie_cdr_sampler_active_input_v57_parent.py',[(OLD,TOP)]),
          'cdr_v58_geometry.py':('scripts/check_cdr_sampler_active_input_v57_parent_geometry.py',[(OLD,TOP)]),
          'cdr_v58_planes.py':('scripts/cloud_cdr_sampler_active_input_v57_planes.py',[(OLD,TOP),('from check_cdr_sampler_active_input_v57_parent_geometry import check','from cdr_v58_geometry import check')]),
          'cdr_v58_recover.py':('scripts/cloud_cdr_sampler_active_input_v57_wire_inputs.py',[(OLD,TOP)]),
        }
        for name,(source,edits)in sources.items():
            text,changes=derive((ROOT/source).read_text(),edits)
            (methods/name).write_text(text);adapt[name]=dict(source=source,original_sha256=sha(ROOT/source),generated_sha256=sha(methods/name),reversible_changes=changes)
        # Wrong/no-op derivations must reject; no extraction/census gate changes.
        faults=[]
        for a,b in [('absent','new'),('same','same')]:
            try:derive('same',[(a,b)])
            except AssertionError:faults.append([a,b])
            else:raise AssertionError('Accepted unsafe source derivation')
        assert len(faults)==2
        r['method_adaptations']=adapt;r['source_derivation_controls']=faults;save()
        run([sys.executable,methods/'check_physical.py','--layout',layout,'--out',parent/'physical','--app',app],'physical')
        physical=json.loads((parent/'physical/result.json').read_text());r['physical']=physical
        assert physical['status']=='PASS_NATIVE_PDK_CDR_PD500_DRC_LVS_AND_FAULT_CONTROLS'
        assert physical['steps']['drc']['measurement']['category_count']==560 and physical['steps']['drc']['measurement']['markers']==0
        assert len(physical['steps'])==15 and all(v['status']=='REJECTED_EXPECTED_FAULT'for n,v in physical['steps'].items()if n not in ('drc','lvs','lvs_flat'))
        for mode in ('lvs','lvs_flat'):
            audit=physical['steps'][mode]['audit']
            assert audit['status']=='PASS within comparison scope'and audit['circuit_status_counts']=={'Match':1}and not audit['extraction_diagnostics']
            assert audit['circuits'][0]['layout_devices_recursive']==audit['circuits'][0]['schematic_devices_recursive']==500
        save()
        run([app,'python',Path(__file__),'--native','planes'],'fresh-native-planes')
        r['native_planes']=json.loads((OUT/'native-planes.json').read_text())
        assert r['native_planes']['status']=='PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS'
        assert len(r['native_planes']['controls'])==19 and len(r['native_planes']['parent_geometry']['controls'])==5
        wire=OUT/'wire';wire.mkdir();wire_methods={}
        for name in ('probe01.py','locate01.py','anchors01.py','dedup01.py'):
            original=(OUT/'source/wire'/name).read_text();assert sha(OUT/'source/wire'/name)==prior['unchanged_wire_method_sha256'][name]
            if name=='dedup01.py':text=original;changes=[]
            else:text,changes=derive(original,[(OLD,TOP)])
            if name=='probe01.py':
                assert 'if not ts:assert not area and not ps and n.cluster_id not in owners' in text
            (wire/name).write_text(text);wire_methods[name]=dict(original_sha256=sha(OUT/'source/wire'/name),generated_sha256=sha(wire/name),changes=changes)
        r['strict_wire_method_adaptations']=wire_methods;save()
        run([app,'python',Path(__file__),'--native','recover'],'source-annotation-recovery')
        for name in wire_methods:run([app,'python',wire/name],name)
        r['strict_wire_graph']=json.loads((wire/'native05/result.json').read_text())
        r['device_locations']=json.loads((wire/'device-locations01.json').read_text())
        r['anchors']=json.loads((wire/'anchors08.json').read_text())
        assert r['strict_wire_graph']['native_device_count']==500 and r['strict_wire_graph']['native_terminal_count']==1446
        assert r['strict_wire_graph']['wire_component_count']==113
        assert r['anchors']['logical_anchor_count']==978 and r['anchors']['public_ports']==25
        assert r['anchors']['dispositions']==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=953,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=493)
        assert all(sha(wire/n)==v['generated_sha256']for n,v in wire_methods.items())
        assert all(sha(methods/n)==v['generated_sha256']for n,v in adapt.items())
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in selected)
        assert all(sha(Path(n))==v for n,v in protected.items())and all(sha(ROOT/n)==v['sha256']for n,v in runtime['files'].items())
        r.update(status='PASS_PD500_V58_OWNED_ACCESS_FULL_PHYSICAL_AND_STRICT_WIRES_REQUIRES_FRESH_MIM_RC',sources_unchanged=True)
    except BaseException as e:
        r.update(status='FAIL_NATIVE_PHYSICAL_OR_STRICT_WIRES',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        for name,path in [('layout',OUT/'parent/layout/result.json'),('physical',OUT/'parent/physical/result.json'),('candidate_delta',OUT/'candidate-delta.json'),('serialization_witness',OUT/'parent/serialized-delta-witness.json')]:
            if path.exists():r[name]=json.loads(path.read_text())
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
