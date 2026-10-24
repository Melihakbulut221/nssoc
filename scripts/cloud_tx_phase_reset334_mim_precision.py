#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh P/N334 native two-order MIM-aware RC and exact composition, no electrical acceptance."""
import argparse,copy,hashlib,json,os,re,shutil,subprocess,sys,traceback
from collections import Counter
from pathlib import Path
import build_pcie_local_vco_hybrid_v6 as compact
import cloud_pll_divider_load3p2v2_compose as original_controls
import cloud_tx_phase_divider_mim_precision as legacy
import compare_cloud_routed_endpoints as reports
import tx_native_cap_order as cap_order
import tx_phase_reset334_rc_sources as methods
import tx_phase_reset334_intrinsic_mim_source as intrinsic_source
import ensure_cloud_tested_source_release as publication
from run_cloud_tx_layout_repair import fetch,sha
from run_cloud_pll_filter_rc import unpack
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-phase-reset334-mim-precision'
GROUP='tx-phase-reset334-mim-precision'
METHOD=ROOT/'scripts/tx-phase-reset334-mim-precision-methods.json'
SOURCE=dict(run=40122940443,head='15f733863e43fb0ed3660829ffd24c2a1205139b',group='tx-phase-reset334-intrinsic-mim',
 summary='02671c9de96e779054cc37f7be26f0625351f0238b25dc210e78e94cf2e6db1d',
 parts='48f2d5352d98b27fbba2da42bfb670fb3cf2870dceb0ab53097f3fb9b6219373',asset=673049249)
FULL='docs/evidence/tx-phase-reset334-intrinsic-mim-full-result-20261024.json'
STATUS='PASS_BOTH_NATIVE334_EIGHT_MIM_TWO_ORDERS_22_RAW_CONTROLS_EACH_AND19_COMPOSITION_CONTROLS_REQUIRES_LOADED_RESET'
legacy.CELL=methods.CELL
def host():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
def pins():
    m=json.loads(METHOD.read_text())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    return m
def api(path):
    return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
def json_proof(value):
    # Frozen receipts are JSON: preserve every value and field while converting
    # source-only tuple containers to their exact JSON list representation.
    return json.loads(json.dumps(value,allow_nan=False))
def validate(prior):
    assert prior['source_head']==SOURCE['head']and prior['sources_unchanged']and prior['generated_sources_unchanged']and prior['validation_errors']==[]
    assert prior['status']=='PASS_BOTH_NATIVE334_INTRINSICS_EIGHT_MIM695_PLANES_11_MODEL_6_GEOMETRY_FAULTS_REQUIRES_TWO_ORDER_RC'
    assert set(prior['variants'])=={'p','n'}and len(prior['outputs'])==250
    for pol,v in prior['variants'].items():
        assert v['physical_GDS_sha256']==intrinsic_source.GDS[pol]
        assert v['intrinsic']==dict(devices=334,hbt=106,resistors=130,mim=8,finite_contacts=90,ports=intrinsic_source.PORTS)
        assert len(v['intrinsic_controls'])==11 and all(x['rejected']for x in v['intrinsic_controls'])
        g=v['mim_geometry']
        assert g['status']==intrinsic_source.MIM_STATUS and g['actual_mim_devices']==8 and g['physical_points']==695 and g['wire_components']==119
        assert all(g[k]for k in ('all_metal_via_drawings_unchanged','intrinsic_mask_union_exact','all_original_native_terminal_identities_unchanged','all695_native_and_physical_owners_verified'))
        assert len(g['controls'])==6 and all(x['rejected']for x in g['controls'])
        assert sorted(tuple(sorted((x['native_parameters']['w'],x['native_parameters']['l'])))for x in g['bottom_access_changes'])==[(2.,2.),(2.,2.2)]+[(24.,24.)]*6
        for kind,proof in v['derivations'].items():
            text,expected=intrinsic_source.sources(kind,pol);assert proof==json_proof(expected)
    assert all(prior[k]is False for k in ('wire_rc_extracted','qualified_pex','electrical_accepted','physical_reset_qualified','all31_clock_tree_accepted','PLL_connected','full_phy_accepted'))
def prerequisite():
    r=api('actions/runs/'+str(SOURCE['run']));j=api('actions/jobs/120958376344')
    assert r['head_sha']==j['head_sha']==SOURCE['head']and r['run_attempt']==j['run_attempt']==1
    assert r['id']==j['run_id']==SOURCE['run']and r['status']==j['status']=='completed'and r['conclusion']==j['conclusion']=='success'
    assert r['path']=='.github/workflows/tx-phase-reset334-intrinsic-mim-cloud.yml'and r['head_branch']=='codex/tx-clock-phase-parent'
    tag='cloud-results-'+str(SOURCE['run'])+'-1-'+SOURCE['group']
    publication.validate_release(publication.api('releases/tags/'+tag),publication.api('git/ref/tags/'+tag),tag,SOURCE['head'])
    data=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(SOURCE['asset']),'-H','Accept: application/octet-stream','--allow-escape-sequences'])
    assert len(data)==98173 and hashlib.sha256(data).hexdigest()==SOURCE['summary']and data==(ROOT/FULL).read_bytes()
    prior=json.loads(data);validate(prior)
    return prior
def source_controls():
    host();pins();prior=prerequisite();proofs=[];roundtrips=[]
    for pol in ('p','n'):
        for kind in intrinsic_source.ORIGINAL:
            _,expected=intrinsic_source.sources(kind,pol)
            assert isinstance(expected['reversible_edits'][0],tuple)
            saved=prior['variants'][pol]['derivations'][kind]
            assert isinstance(saved['reversible_edits'][0],list)and saved==json_proof(expected)
            roundtrips.append(pol+'-'+kind)
    assert len(roundtrips)==6
    for label,fn in [('mim',methods.mim_source),('audit',methods.audit_source),('mutations',methods.mutations_source)]:
        text,proof=fn();proofs.append(dict(label=label,**proof))
    for order in (False,True):
        text,proof=methods.rc_source(Path('/fixture/p/precise'),order);proofs.append(dict(label='producer-'+str(order),**proof))
    for pol in ('p','n'):
        for nr,nc in ((123,456),(323,456),(3123,600),(91,7)):
            text,proof=methods.compose_source(pol,nr,nc)
            assert text.count('=='+str(nr+nc))==2
            assert 'dict(R='+str(nr)+',C='+str(nc)+')'in text
            assert 'wire_resistors='+str(nr)+',wire_capacitors='+str(nc)in text
            assert '==334'in text and '==695'in text and '==1010'in text and '==119'in text
            proofs.append(dict(label='compose-'+pol+'-'+str(nr)+'-'+str(nc),**proof))
    text,_=methods.audit_source()
    for token in ("rel_tol=3e-6,abs_tol=1e-4","graph.add_nodes_from(a)","owners['sub']=0","native_mim_intrinsic=mim_proof","intrinsic aliases","every_native_point_ground_capacitance_preserved=True"):assert token in text,token
    faults=[]
    for name,mutate in [
      ('source',lambda d:d.update(source_head='0'*40)),
      ('false-RC',lambda d:d.update(wire_rc_extracted=True)),
      ('false-electrical',lambda d:d.update(electrical_accepted=True)),
      ('missing-polarity',lambda d:d['variants'].pop('n')),
      ('device-count',lambda d:d['variants']['p']['intrinsic'].update(devices=333)),
      ('contact-count',lambda d:d['variants']['n']['intrinsic'].update(finite_contacts=89)),
      ('MIM-count',lambda d:d['variants']['p']['mim_geometry'].update(actual_mim_devices=7)),
      ('seed-width',lambda d:d['variants']['n']['mim_geometry']['bottom_access_changes'][-1]['native_parameters'].update(w=24.)),
      ('model-fault',lambda d:d['variants']['p']['intrinsic_controls'][0].update(rejected=False)),
      ('geometry-fault',lambda d:d['variants']['n']['mim_geometry']['controls'][0].update(rejected=False)),
      ('anchor-count',lambda d:d['variants']['p']['mim_geometry'].update(physical_points=694)),
      ('native-owner',lambda d:d['variants']['n']['mim_geometry'].update(all695_native_and_physical_owners_verified=False)),
      ('proof-generated-hash',lambda d:d['variants']['p']['derivations']['native'].update(generated_sha256='0'*64)),
      ('proof-original-hash',lambda d:d['variants']['n']['derivations']['intrinsic'].update(original_sha256='0'*64)),
      ('proof-edit-count',lambda d:d['variants']['p']['derivations']['mim']['reversible_edits'][0].__setitem__(2,2)),
      ('proof-edit-text',lambda d:d['variants']['n']['derivations']['native']['reversible_edits'][0].__setitem__(1,'PORTS=[]'))]:
        d=copy.deepcopy(prior);mutate(d)
        try:validate(d)
        except (AssertionError,KeyError):faults.append(name)
        else:raise AssertionError('Accepted prerequisite fault '+name)
    for name,text,changes in [('missing-source','','absent'),('identity-edit','x=1','x=1'),('empty-edit','x=1','')]:
        try:methods.derive(text,[(changes,'x=1'if name=='identity-edit'else'y=2')])
        except AssertionError:faults.append(name)
        else:raise AssertionError('Accepted derivation fault '+name)
    assert len(faults)==19 and len(proofs)==13
    cap=cap_order.controls();assert len(cap)==4;pub=publication.controls();assert len(pub['rejected'])==17;pins()
    return dict(status='PASS_RESET334_RC13_DERIVATIONS19_FAULTS_AND_ORIGINAL_CAP_ORDER_CONTROLS_NO_NATIVE',
      source_derivations=proofs,JSON_tuple_list_roundtrips=roundtrips,rejected=faults,cap_order_controls=cap,publication_controls=pub,native_executed=False,
      electrical_accepted=False,full_phy_accepted=False)
def copy_checked(src,dest):
    shutil.copytree(src,dest)
    hashes={str(p.relative_to(src)):sha(p)for p in src.rglob('*')if p.is_file()}
    assert all(sha(dest/p)==h for p,h in hashes.items())
    return hashes
def compose(P,pol,prior,audit):
    source=P/'source';B=P/'precise';destination=P/'composition';destination.mkdir()
    intrinsic=legacy.load(ROOT/'scripts'/('tx_phase_reset334_'+pol+'_intrinsic_generated.py'),'tx_phase_reset334_'+pol+'_intrinsic_generated')
    native=json.loads((source/'native.json').read_text());planes=json.loads((B/'anchors03.json').read_text())
    rows=compact.statements((B/'rc01/wires.spice').read_text());extracted=[row for row in rows[1:-1]if row[0].startswith('X')]
    assert len(extracted)==8 and audit['native_mim_intrinsic']['devices']==8
    projected=[row for row in rows if not row[0].startswith('X')]
    assert Counter(map(tuple,projected[1:-1]))==Counter(tuple(row)for row in rows[1:-1]if row[0].startswith(('R','C')))
    wire='\n'.join(' '.join(row)for row in projected)+'\n';(destination/'verified-wire-projection.spice').write_text(wire)
    nr=audit['actual_exported_resistors'];nc=audit['actual_exported_capacitors'];assert min(nr,nc)>0
    generated,method=methods.compose_source(pol,nr,nc);path=destination/'compose.py';path.write_text(generated)
    model=legacy.load(path,'reset334_'+pol+'_composition');original_controls.compose=model
    tech=json.loads((source/'pdk/libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())['techParams']
    compact_text=(source/'intrinsic.spice').read_text();intrinsic.verify(compact_text,native['modes']['lvs_flat']['devices'],tech,methods.names(pol)[0])
    output,expected,wires,mapping,bindings=model.prepare(compact_text,wire,native,planes,tech)
    verify=lambda s:model.verify(s,expected,wires,mapping,native,planes)
    positive=verify(output);d=destination/'controls';d.mkdir()
    controls=original_controls.controls(output,verify,d,True)
    outputrows=compact.statements(output);mim=next(row for row in outputrows if 'cap_cmim'in row)
    for label,extra in [('duplicate_bound_mim',[mim[0]+'_DUPLICATE',*mim[1:]]),('retained_extractor_mim',extracted[0])]:
        mutant='\n'.join(' '.join(row)for row in [*outputrows[:-1],extra,outputrows[-1]])+'\n'
        assert mutant!=output;(d/(label+'.spice')).write_text(mutant)
        try:verify(mutant)
        except (AssertionError,ValueError)as e:controls.append(dict(fault=label,rejected=True,reason=str(e)))
        else:raise AssertionError('Accepted '+label)
    assert len(controls)==19 and all(x['rejected']for x in controls)
    assert sum('cap_cmim'in row for row in compact.statements(output))==8
    assert positive==dict(devices=334,wire_resistors=nr,wire_capacitors=nc,terminals=1010,wire_components=119,body_nodes=1,ports=intrinsic.PORTS+['wire_cref'])
    (destination/'reset334-wire.spice').write_text(output)
    contract=dict(status='PASS_NATIVE334_EIGHT_MIM_ONCE_ALL_RC_AND19_COMPOSITION_FAULTS_REQUIRES_LOADED_RESET',
      positive=positive,controls=controls,method=method,projected_native_mim_cards=extracted,
      verified_native_mim_proof=audit['native_mim_intrinsic'],wire_node_map=mapping,bindings=bindings,
      all_raw_wire_tokens_preserved=True,intrinsic_mim_models_exactly_once=True,model_sha256=sha(destination/'reset334-wire.spice'),
      electrical_accepted=False,physical_reset_qualified=False,all31_clock_tree_accepted=False,PLL_connected=False,full_phy_accepted=False,qualified_pex=False)
    (destination/'composition.json').write_text(json.dumps(contract,indent=2)+'\n')
    return contract
def main():
    host();locked=pins();prior=prerequisite()
    tag,head=publication.context(GROUP,os.environ)
    pub=publication.validate_release(publication.api('releases/tags/'+tag),publication.api('git/ref/tags/'+tag),tag,head)
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],release_prerequisite=pub,
      accepted=False,qualified_pex=False,electrical_accepted=False,physical_reset_qualified=False,
      all31_clock_tree_accepted=False,PLL_connected=False,full_phy_accepted=False,polarities={})
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(cmd,label,folder):
        path=folder/(label+'.log')
        with path.open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        result.setdefault('commands',[]).append(dict(label=str(path.relative_to(OUT)),returncode=code,sha256=sha(path)));save()
        if code:print(path.read_text(errors='replace')[-18000:],flush=True)
        assert code==0,(label,code)
    save()
    try:
        full=OUT/'qualified-intrinsic'
        restored,proof=reports.restore_report(SOURCE['group'],SOURCE['run'],SOURCE['summary'],SOURCE['parts'],full,list(prior['outputs']))
        assert restored==prior and sha(full/'result.json')==SOURCE['summary'];validate(restored);result['source']=proof;save()
        runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text());rt=OUT/'magic-cloud';rt.mkdir();packed=OUT/'runtime.tar.gz'
        fetch(runtime['receipt']['url'],runtime['receipt']['sha256'],packed);assert packed.stat().st_size==runtime['receipt']['bytes'];unpack(packed,rt)
        manifest=json.loads((rt/'manifest.json').read_text());assert all(sha(rt/n)==v['sha256']for n,v in manifest['files'].items());result['runtime']=runtime
        qualified,qproof=reports.restore_report('tx-raw64-totalcap-precision',39486998309,'bdcbddedf70af7e4bc9a1d6b3ec4ac334a619e2fe208244b83a6e8b74cc09a38','3b0dc36952ae38ac4ce1c1ea8e27cac8e4917ca7543a81a916a207b49adaa9e2',OUT/'producer',['precise-source/magic/tclmagic.so'])
        assert qualified['status']=='PASS_REBUILT_NATIVE8074_RC_DOUBLE_TOTALS_AND13_CONTROLS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE'
        for key in ('sources_unchanged','baseline_reproduced_original_rc_and_failure','no_rc_records_changed','no_geometry_technology_or_threshold_change','both_native_input_orders_verified'):assert qualified[key]
        assert qualified['source_changes']['changed_only']=='resis/resis.h'
        assert len(qualified['controls']['cases'])==len(qualified['historical_controls']['cases'])==13
        lib=OUT/'producer/precise-source/magic/tclmagic.so';assert sha(lib)==qualified['rebuilt_runtimes']['precise']['sha256']==methods.PRECISE
        precision=OUT/'precision-runtime';shutil.copytree(rt/'runtime',precision);target=precision/'lib/magic/tcl/tclmagic.so';shutil.copyfile(lib,target);assert sha(target)==methods.PRECISE
        for path in (rt/'runtime').rglob('*'):
            if path.is_file()and path.relative_to(rt/'runtime')!=Path('lib/magic/tcl/tclmagic.so'):assert sha(path)==sha(precision/path.relative_to(rt/'runtime'))
        deps=subprocess.run(['ldd',str(lib)],capture_output=True,text=True);assert deps.returncode==0 and 'not found'not in deps.stdout+deps.stderr
        result['precision_producer']=qproof;result['producer_sha256']=methods.PRECISE;result['producer_dependencies']=deps.stdout+deps.stderr
        pilot=json.loads((ROOT/'docs/evidence/cdr-mim-explicit-model-pilot-pass-20261018.json').read_text())['report']['private_ngspice_tech']
        original=rt/'tech';private=OUT/'ngspice-mim-tech';shutil.copytree(original,private);path=private/'ihp-sg13g2-extract.tech';assert sha(path)==pilot['original_sha256'];text=path.read_text()
        for line in pilot['removed_cdl_device_estimate_lines']:assert text.count(line)==1;text=text.replace(line,'')
        path.write_text(text);assert sha(path)==pilot['private_sha256']
        assert all(sha(private/p.name)==sha(p)for p in original.iterdir()if p.is_file()and p.name!='ihp-sg13g2-extract.tech');result['private_tech']=pilot
        raw=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())['raw_parser'];fetch(raw['url'],raw['sha256'],OUT/'raw-parser.py')
        mim,proof=methods.mim_source();mp=ROOT/'scripts/audit_tx_reset334_mim_generated.py';assert not mp.exists();mp.write_text(mim);(OUT/mp.name).write_bytes(mp.read_bytes());generated={mp:sha(mp)};result['MIM_derivation']=proof
        errors=[]
        for pol in ('p','n'):
            P=OUT/pol;P.mkdir();v=dict(status='RUNNING',orders={});result['polarities'][pol]=v;save()
            try:
                source=P/'source';copied=copy_checked(full/pol,source);pdk=copy_checked(full/'pdk',source/'pdk')
                runtime_copy=copy_checked(precision,P/'precision-runtime');tech_copy=copy_checked(private,P/'ngspice-mim-tech')
                shutil.copyfile(OUT/'raw-parser.py',P/'raw-parser.py');assert sha(P/'raw-parser.py')==raw['sha256']
                for kind in intrinsic_source.ORIGINAL:
                    name='tx_phase_reset334_'+pol+'_'+kind+'_generated.py';path=ROOT/'scripts'/name;assert not path.exists()
                    data=(source/name).read_text();expected,derivation=intrinsic_source.sources(kind,pol)
                    assert data==expected and json_proof(derivation)==prior['variants'][pol]['derivations'][kind]
                    path.write_text(data);generated[path]=sha(path)
                anchor=json.loads((source/'mim/anchors.json').read_text());assert len(anchor['anchors'])==695 and len(anchor['rows'])==1010
                original_prefix='/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-tx-phase-reset334-intrinsic-mim/'
                repo_prefix='/home/runner/work/nssoc/nssoc/';source_inputs={}
                for name,digest in anchor['inputs'].items():
                    if name.startswith(original_prefix):target=full/name[len(original_prefix):]
                    else:assert name.startswith(repo_prefix);target=ROOT/name[len(repo_prefix):]
                    assert sha(target)==digest,(name,target);source_inputs[str(target)]=digest
                run([sys.executable,ROOT/'scripts/tx_reverse_native_cap_order.py','--controls'],'reverse-order-controls',P)
                for order in ('precise','precise_reversed'):
                    B=P/order;B.mkdir();shutil.copyfile(source/'mim/wires.gds',B/'wires.gds')
                    anchors=copy.deepcopy(anchor);anchors['inputs']={**source_inputs,str(B/'wires.gds'):sha(B/'wires.gds'),str(source/'mim/anchors.json'):sha(source/'mim/anchors.json')}
                    anchors['dispositions']=dict(Counter(row['disposition']for row in anchors['rows']))
                    assert anchors['dispositions']==dict(ACTUAL_CONTACT_REFERENCE_WITH_UNMODELED_POLY_DIFFUSION_R=684,RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R=326)
                    assert anchors['rows']==anchor['rows']and anchors['anchors']==anchor['anchors']
                    (B/'anchors03.json').write_text(json.dumps(anchors,indent=2)+'\n')
                    methodproof={}
                    for name,(text,pr)in [('run-rc01.py',methods.rc_source(B,order=='precise_reversed')),('audit-rc02.py',methods.audit_source()),('mutations01.py',methods.mutations_source())]:
                        (B/name).write_text(text);assert sha(B/name)==pr['generated_sha256'];methodproof[name]=pr
                    run([sys.executable,B/'run-rc01.py'],order+'-native',P)
                    native=json.loads((B/'rc01/result.json').read_text());assert native['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT'and native['returncode']==0
                    run([sys.executable,B/'audit-rc02.py',B/'rc01',B/'anchors03.json',B/'audit.json'],order+'-raw-audit',P)
                    audit=json.loads((B/'audit.json').read_text());v['orders'][order]=dict(native=native,audit=audit,methods=methodproof);save()
                    assert audit['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'and audit['native_mim_intrinsic']['devices']==8 and audit['geometry_probes']==695
                    run([sys.executable,B/'mutations01.py'],order+'-raw-controls',P)
                    controls=json.loads((B/'native-mutations01.json').read_text());assert controls['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'and len(controls['cases'])==13
                    module=legacy.load(B/'audit-rc02.py','reset334_'+pol+'_'+order);faults=legacy.raw_mim_controls(B,module,anchors)
                    for name,pr in methodproof.items():assert sha(B/name)==pr['generated_sha256']
                    v['orders'][order].update(wire_controls=controls,mim_controls=faults);save()
                first=P/'precise/rc01';second=P/'precise_reversed/rc01';cell=methods.CELL
                assert legacy.records(first/'wires.spice')==legacy.records(second/'wires.spice'),'Two-order native R/C/device records differ'
                _,equivalence=cap_order.reorder((second/(cell+'.ext')).read_text(),(first/(cell+'.ext')).read_text())
                for token in ('device','parameters','node','port','equiv','substrate'):
                    assert [x for x in cap_order.rows((first/(cell+'.ext')).read_text())if x[0]==token]==[x for x in cap_order.rows((second/(cell+'.ext')).read_text())if x[0]==token],token
                reversal=json.loads((second/(cell+'.order-proof.json')).read_text());assert reversal['reversed_enumeration']and reversal['symmetric_endpoint_value_multiset_exact']and reversal['non_coupling_records_unchanged']
                v['native_order_equivalence']=equivalence;v['reversal']=reversal
                v['composition']=compose(P,pol,prior['variants'][pol],v['orders']['precise']['audit'])
                for folder,checks in [(source,copied),(source/'pdk',pdk),(P/'precision-runtime',runtime_copy),(P/'ngspice-mim-tech',tech_copy)]:
                    assert all(sha(folder/n)==h for n,h in checks.items())
                assert sha(P/'raw-parser.py')==raw['sha256']
                v.update(status='PASS_NATIVE334_EIGHT_MIM_TWO_ORDERS_AND19_COMPOSITION_FAULTS_REQUIRES_LOADED_RESET',sources_unchanged=True)
            except BaseException as e:
                v.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());errors.append(dict(polarity=pol,error=repr(e)));save()
        result['validation_errors']=errors
        assert all(sha(full/n)==h for n,h in prior['outputs'].items())
        assert all(sha(rt/n)==v['sha256']for n,v in manifest['files'].items())
        assert all(sha(p)==h for p,h in generated.items())and sha(OUT/'raw-parser.py')==raw['sha256'];pins()
        assert not errors,errors
        result.update(status=STATUS,sources_unchanged=True,both_polarities_and_orders_verified=True,native_RC_and_device_records_equal_in_both_orders=True)
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');args=p.parse_args()
    if args.controls:print(json.dumps(source_controls(),indent=2))
    else:main()
