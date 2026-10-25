#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh334 exact compact devices and eight actual MIM masks for both preset geometries."""
import argparse,copy,hashlib,importlib.util,json,os,re,subprocess,sys,tempfile,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as compact
import cloud_pll_divider_load3p2v2_compose as original_controls
from cloud_tx_driver_localpins_intrinsic import PDK
from run_cloud_tx_layout_repair import sha,fetch
import tx_phase_reset334_intrinsic_mim_source as source
import ensure_cloud_tested_source_release as publication
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-phase-reset334-intrinsic-mim'
GROUP='tx-phase-reset334-intrinsic-mim'
METHOD=ROOT/'scripts/tx-phase-reset334-intrinsic-mim-methods.json'
APP_SHA='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
SOURCE=dict(run=40120130880,head='2e1f26e9c4fdf37d63433a0c859c2d305db3486b',group='tx-phase-reset244-physical',
 summary='5591fe784df1cc1294302ac38a13a8db4b6285f37335fa7c2fbe2d477c7fa913',
 parts='a6be15e92a1721ddd794ab75cce227e962f6ada294d5a54b0e58cc4778ec187b',summary_asset=672983363)
STATUS='PASS_BOTH_NATIVE334_INTRINSICS_EIGHT_MIM695_PLANES_11_MODEL_6_GEOMETRY_FAULTS_REQUIRES_TWO_ORDER_RC'
def host():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'
def pins():
    m=json.loads(METHOD.read_text())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    return m
def api(path):
    return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
def validate_run(run,job):
    assert run['id']==SOURCE['run']and run['head_sha']==SOURCE['head']and run['run_attempt']==1
    assert run['path']=='.github/workflows/tx-phase-reset244-physical-cloud.yml'and run['head_branch']=='codex/tx-clock-phase-parent'
    assert run['status']=='completed'and run['conclusion']=='success'
    assert job['id']==120949804811 and job['run_id']==SOURCE['run']and job['head_sha']==SOURCE['head']
    assert job['run_attempt']==1 and job['status']=='completed'and job['conclusion']=='success'
def validate(prior):
    assert prior['source_head']==SOURCE['head']and prior['sources_unchanged']and prior['validation_errors']==[]
    assert prior['status']=='PASS_BOTH_FRESH334_PHYSICAL_AND1010_TERMINAL_GATES_REQUIRES_MIM_RC_AND_LOADED_RESET'
    assert set(prior['variants'])=={'p','n'}and len(prior['outputs'])==198
    for pol,v in prior['variants'].items():
        assert v['status']=='PASS_FRESH334_DRC_DEEP_FLAT_LVS9_FAULTS_AND1010_NATIVE_TERMINALS7_FAULTS_REQUIRES_FRESH_RC_AND_LOADED_RESET'and v['sources_unchanged']
        assert v['generation']['preset_polarity']==pol
        assert v['generation']['output_sha256'][source.top(pol)+'.gds']==source.GDS[pol]
        assert prior['outputs'][pol+'/layout/'+source.top(pol)+'.gds']==source.GDS[pol]
        assert v['generation']['primitive_counts']==dict(hbt=106,rppd=130,cmim=8,physical_ptap=90)
        d=v['steps']['drc']['measurement'];assert d['status']=='PASS'and d['markers']==0 and d['category_count']==560
        for mode in ('deep_lvs','flat_lvs'):
            d=v['steps'][mode];a=d['audit']
            assert d['expected_verdict_observed']and d['ports']['passed']and d['ports']['actual_count']==d['ports']['expected_count']==11
            assert a['status']=='PASS within comparison scope'and not a['reasons']and not a['extraction_diagnostics']
            assert a['circuits'][0]['layout_devices_recursive']==a['circuits'][0]['schematic_devices_recursive']==334
        faults={k:v for k,v in v['steps'].items()if k not in ('drc','deep_lvs','flat_lvs')}
        assert len(faults)==9 and all(x['expected_verdict_observed']and not x['positive']for x in faults.values())
        w=v['wires'];g=w['graph'];a=w['anchors']
        assert w['sources_unchanged']and w['physical_GDS_sha256']==source.GDS[pol]
        assert g['native_device_count']==334 and g['native_terminal_count']==1010
        assert g['native_electrical_net_count']==120 and g['wire_component_count']==119
        assert g['no_wire_geometry_change']and g['no_component_union_by_native_label']
        assert a['counts']==dict(devices=334,terminals=1010,metal_terminals=684,body_terminals=326,public_ports=11,unique_reference_planes=695,wire_components=119)
        assert len(a['negative_controls'])==7 and all(x['rejected']for x in a['negative_controls'])
        assert v['generation']['exactly243_other_compact_devices_unchanged']
        assert v['generation']['sole_device_dimension_delta']==dict(name='PHASE__XRUN__XAND_SKEW',old_L_um=32,new_L_um=20,W_um=1)
    assert all(prior[k]is False for k in ('qualified_pex','electrical_accepted','physical_reset_qualified','all31_clock_tree_accepted','PLL_connected','full_phy_accepted'))
def prerequisite():
    run=api('actions/runs/'+str(SOURCE['run']));job=api('actions/jobs/120949804811');validate_run(run,job)
    tag='cloud-results-'+str(SOURCE['run'])+'-1-'+SOURCE['group']
    publication.validate_release(publication.api('releases/tags/'+tag),publication.api('git/ref/tags/'+tag),tag,SOURCE['head'])
    raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(SOURCE['summary_asset']),'-H','Accept: application/octet-stream','--allow-escape-sequences'])
    assert len(raw)==5644409 and hashlib.sha256(raw).hexdigest()==SOURCE['summary']
    prior=json.loads(raw);validate(prior)
    return prior,dict(run=SOURCE['run'],head=SOURCE['head'],job=job['id'],summary_sha256=SOURCE['summary'])
def controls():
    host();m=pins();prior,pre=prerequisite();derived=source.controls();faults=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,KeyError):faults.append(name)
        else:raise AssertionError('Accepted physical prerequisite corruption '+name)
    mutations=[
      ('source',lambda d:d.update(source_head='0'*40)),
      ('status',lambda d:d.update(status='PASS')),
      ('sources',lambda d:d.update(sources_unchanged=False)),
      ('errors',lambda d:d.update(validation_errors=['bad'])),
      ('missing-polarity',lambda d:d['variants'].pop('n')),
      ('GDS',lambda d:d['variants']['p']['generation']['output_sha256'].update({source.top('p')+'.gds':'0'*64})),
      ('DRC-markers',lambda d:d['variants']['p']['steps']['drc']['measurement'].update(markers=1)),
      ('DRC-category',lambda d:d['variants']['n']['steps']['drc']['measurement'].update(category_count=559)),
      ('LVS-devices',lambda d:d['variants']['p']['steps']['flat_lvs']['audit']['circuits'][0].update(layout_devices_recursive=333)),
      ('LVS-ports',lambda d:d['variants']['n']['steps']['deep_lvs']['ports'].update(actual_count=10)),
      ('native-terminals',lambda d:d['variants']['p']['wires']['graph'].update(native_terminal_count=1009)),
      ('body-terminals',lambda d:d['variants']['n']['wires']['anchors']['counts'].update(body_terminals=325)),
      ('physical-fault',lambda d:d['variants']['p']['steps']['wrong_offset_length'].update(expected_verdict_observed=False)),
      ('anchor-fault',lambda d:d['variants']['n']['wires']['anchors']['negative_controls'][0].update(rejected=False)),
      ('offset-length',lambda d:d['variants']['p']['generation']['sole_device_dimension_delta'].update(new_L_um=32)),
      ('false-electrical',lambda d:d.update(electrical_accepted=True))]
    for name,mutation in mutations:
        d=copy.deepcopy(prior);mutation(d);reject(name,lambda d=d:validate(d))
    assert len(faults)==16 and len(derived['rejected'])==9
    p=publication.controls();assert len(p['rejected'])==17;pins()
    return dict(status='PASS_RESET334_MIM_SOURCE9_PHYSICAL16_PUBLICATION17_CONTROLS_NO_NATIVE',
      prerequisite=pre,derivations=derived,physical_faults=faults,publication_controls=p,
      native_execution=False,wire_rc_extracted=False,electrical_accepted=False,full_phy_accepted=False)
def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
def main():
    host();m=pins();prior,pre=prerequisite()
    tag,head=publication.context(GROUP,os.environ)
    pub=publication.validate_release(publication.api('releases/tags/'+tag),publication.api('git/ref/tags/'+tag),tag,head)
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],physical_prerequisite=pre,release_prerequisite=pub,
      accepted=False,wire_rc_extracted=False,qualified_pex=False,electrical_accepted=False,physical_reset_qualified=False,
      all31_clock_tree_accepted=False,PLL_connected=False,full_phy_accepted=False,variants={})
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def execute(cmd,label,out):
        path=out/(label+'.log')
        with path.open('w')as log:p=subprocess.run(list(map(str,cmd)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r.setdefault('executions',{})[out.name+'/'+label]=dict(returncode=p.returncode,log_sha256=sha(path));save()
        if p.returncode:print(path.read_text(errors='replace')[-20000:],flush=True)
        assert p.returncode==0,label
    save()
    try:
        physical=OUT/'physical'
        record,proof=reports.restore_report(SOURCE['group'],SOURCE['run'],SOURCE['summary'],SOURCE['parts'],physical,list(prior['outputs']))
        assert record==prior;validate(record);assert sha(physical/'result.json')==SOURCE['summary'];r['restore']=proof;save()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==APP_SHA
        models=OUT/'pdk';model_pins={p:h for p,h in compact.MODEL_PINS.items()if p.endswith(('resistors_mod.lib','sg13g2_hbt_mod.lib','capacitors_mod.lib','sg13g2_tech.json','utility_functions.py'))}
        assert PDK=='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
        for p,h in model_pins.items():
            target=models/p;target.parent.mkdir(parents=True,exist_ok=True);fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/'+PDK+'/ihp-sg13g2/'+p,h,target)
        hbt=(models/'libs.tech/ngspice/models/sg13g2_hbt_mod.lib').read_text(encoding='latin-1')
        res=(models/'libs.tech/ngspice/models/resistors_mod.lib').read_text();caps=(models/'libs.tech/ngspice/models/capacitors_mod.lib').read_text()
        assert len(re.findall(r'^\.subckt\s+npn13G2\s+c\s+b\s+e\s+bn\s*$',hbt,re.M|re.I))==1
        assert len(re.findall(r'^\.subckt\s+rppd\s+1\s+2\s+bn\s*$',res,re.M|re.I))==1
        assert len(re.findall(r'^\.subckt\s+cap_cmim\s+PLUS\s+MINUS\s*$',caps,re.M|re.I))==1
        tap=re.search(r'^\.subckt\s+ptap1\s+1\s+2\s*\n(.*?)^\.ends\s+ptap1',res,re.M|re.S|re.I);assert tap
        assert [s.strip()for s in re.findall(r'^R\S+\s+1\s+2\s+R=R\s*$',tap[1],re.M)]==['R1 1 2 R=R']
        tech=json.loads((models/'libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())['techParams']
        generated={};errors=[]
        for pol in ('p','n'):
            out=OUT/pol;out.mkdir();v=dict(status='RUNNING',polarity=pol,physical_GDS_sha256=source.GDS[pol],derivations={});r['variants'][pol]=v;save()
            try:
                paths={}
                for kind in source.ORIGINAL:
                    name='tx_phase_reset334_'+pol+'_'+kind+'_generated'
                    path=ROOT/'scripts'/(name+'.py');assert not path.exists()
                    text,derivation=source.sources(kind,pol);path.write_text(text);(out/path.name).write_bytes(path.read_bytes())
                    paths[kind]=path;generated[path]=sha(path);v['derivations'][kind]=derivation
                execute([app,'python',paths['native'],physical/pol,out],'native-export',out)
                native=json.loads((out/'native.json').read_text());rows=native['modes']['lvs_flat']['devices']
                assert len(rows)==334 and native['gds_sha256']==source.GDS[pol]
                intrinsic=load_module(paths['intrinsic'],paths['intrinsic'].stem)
                name='nssoc_tx_phase_reset334_'+pol+'_intrinsic_v1'
                text,binding=intrinsic.build(rows,tech,name);(out/'intrinsic.spice').write_text(text)
                v['intrinsic']=intrinsic.verify(text,rows,tech,name)
                assert v['intrinsic']==dict(devices=334,hbt=106,resistors=130,mim=8,finite_contacts=90,ports=source.PORTS)
                control_dir=out/'intrinsic-controls';control_dir.mkdir()
                v['intrinsic_controls']=original_controls.controls(text,lambda s:intrinsic.verify(s,rows,tech,name),control_dir,False)
                assert len(v['intrinsic_controls'])==11 and all(x['rejected']for x in v['intrinsic_controls'])
                (out/'binding.json').write_text(json.dumps(dict(native=native,intrinsic_bindings=binding,ports=intrinsic.PORTS),indent=2)+'\n');save()
                execute([app,'python',paths['mim'],physical/pol,out],'native-mim-geometry',out)
                geom=json.loads((out/'mim/result.json').read_text());v['mim_geometry']=geom
                assert geom['status']==source.MIM_STATUS and geom['actual_mim_devices']==8 and geom['physical_points']==695
                assert geom['all695_native_and_physical_owners_verified']and len(geom['controls'])==6 and all(x['rejected']for x in geom['controls'])
                # Check six actual large capacitors plus both unequal physical seed dimensions.
                sizes=sorted(tuple(sorted((x['native_parameters']['w'],x['native_parameters']['l'])))for x in geom['bottom_access_changes'])
                assert sizes==[(2.,2.),(2.,2.2)]+[(24.,24.)]*6
                v.update(status='PASS_NATIVE334_INTRINSIC_AND_EIGHT_MIM695_PLANES_REQUIRES_TWO_ORDER_RC',
                  native_sha256=sha(out/'native.json'),intrinsic_sha256=sha(out/'intrinsic.spice'),binding_sha256=sha(out/'binding.json'),
                  wire_rc_extracted=False,electrical_accepted=False,full_phy_accepted=False)
            except BaseException as e:
                v.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());errors.append(dict(polarity=pol,error=repr(e)));save()
        r['validation_errors']=errors
        assert all(sha(physical/p)==h for p,h in prior['outputs'].items())
        assert all(sha(models/p)==h for p,h in model_pins.items())
        assert all(sha(p)==h for p,h in generated.items());pins()
        assert not errors,errors
        r.update(status=STATUS,sources_unchanged=True,generated_sources_unchanged=True,models=dict(commit=PDK,hashes=model_pins))
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--controls',action='store_true');args=parser.parse_args()
    if args.controls:print(json.dumps(controls(),indent=2))
    else:main()
