#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh phase55 native MIM-aware double-total RC in both orders; no electrical claim."""
import argparse,ast,copy,difflib,hashlib,importlib.util,json,os,re,shutil,subprocess,sys,traceback
from collections import Counter
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
import build_pcie_local_vco_hybrid_v6 as compact
import cloud_pll_divider_load3p2v2_compose as original_controls
import compare_cloud_routed_endpoints as reports
import tx_native_cap_order as cap_order
from run_cloud_tx_layout_repair import fetch,sha
from run_cloud_pll_filter_rc import unpack
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-phase-divider-mim-precision'
SOURCE=dict(run=40084804265,head='9eefcbb7ac28942ca5dc40dcef35e0bfbf7dd61e',group='tx-phase-divider-intrinsic-mim')
PRECISE='1a44bd5c70af3800213419c2e3b2213285523a74fcc4b92bc9cf7314d93a592c'
CELL='phase_divider55_wires'
INTRINSIC='nssoc_tx_phase_divider55_intrinsic_v1'
MODEL='nssoc_tx_phase_divider55_native_wire_v1'
def derive(text,edits):
    original=text;records=[]
    for before,after in edits:
        assert before and before!=after
        matches=list(re.finditer(re.escape(before),text));count=len(matches);assert count>0,(before,count)
        positions=[m.start()+i*(len(after)-len(before))for i,m in enumerate(matches)]
        text=text.replace(before,after);records.append(dict(before=before,after=after,count=count,positions=positions))
    reverse=text
    for row in reversed(records):
        for start in reversed(row['positions']):
            assert reverse[start:start+len(row['after'])]==row['after'],row
            reverse=reverse[:start]+row['before']+reverse[start+len(row['after']):]
    assert reverse==original
    ast.parse(text)
    return text,dict(original_sha256=hashlib.sha256(original.encode()).hexdigest(),generated_sha256=hashlib.sha256(text.encode()).hexdigest(),edits=records,reversible=True)
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
def protected():
    pins=json.loads((ROOT/'scripts/tx-phase-divider-mim-precision-methods.json').read_text())['protected']
    for path,digest in pins.items():assert sha(ROOT/path)==digest,path
    return pins
def audit_source():
    edits=[
        ("PRIOR=B.parent/'pcie-magic-resis-terminals-v1-20261004/audit_pilot.py'","PRIOR=B.parent/'raw-parser.py'"),
        ('import networkx as nx','import networkx as nx\nsys.path.insert(0,str(Path.cwd()/"scripts"))\nfrom audit_tx_phase55_mim_intrinsic import validate_mim'),
        ('divider_load3p2_wires',CELL),
        ('==205','==126'),('=205','=126'),('=198','=117'),('=85','=51'),('==283','==168'),
        ("['38']","['25']"),("['37']","['24']"),('==37','==24'),('range(1,38)','range(1,25)'),
        ("require(not after['devices'] and not before['devices'] and not before['resistors'],'Device insertion into wire-only graph')","require(not before['resistors'],'Unexpected baseline resistor insertion')"),
        ("require(native_r==export_r,'Native/export resistor topology/value differs')","require(native_r==export_r,'Native/export resistor topology/value differs')\n mim_proof=validate_mim(rows,rep,before,after,original,owners,anchors,json.loads((B.parent/'source/native.json').read_text()))"),
        ('original_devices=91,public_ports=7,physical_wire_components=37','native_mim_intrinsic=mim_proof,original_devices=55,public_ports=9,physical_wire_components=24'),
        ('connected_wire_components=37','connected_wire_components=24'),('collapsed_matrix_entries=38**2','collapsed_matrix_entries=25**2')]
    return derive((ROOT/'scripts/pll_divider_load3p2_audit_rc02.py').read_text(),edits)
def mutations_source():
    return derive((ROOT/'scripts/pll_divider_load3p2_mutations01.py').read_text(),[
        ('divider_load3p2_wires',CELL),("NO_SPREADING_R',84)","NO_SPREADING_R',50)")])
def rc_source(B,reversed_order):
    edits=[
        ("W=B/'native01/wires.gds'","W=B/'wires.gds'"),
        ("RT=B/'magic-cloud/runtime/lib';T=B/'magic-cloud/tech'","RT=B.parent/'precision-runtime/lib';T=B.parent/'ngspice-mim-tech'"),
        ('e8f2d96121e704acee41e7a58c23feead887527e3bfc4f51da4d97aa8183970e',PRECISE),
        ('divider_load3p2_wires',CELL)]
    if reversed_order:
        marker="'extract all',"
        command='exec /usr/bin/python3 {'+str(ROOT/'scripts/tx_reverse_native_cap_order.py')+'} {'+str(B/'rc01'/f'{CELL}.ext')+'}'
        edits.append((marker,marker+repr(command)+','))
    return derive((ROOT/'scripts/pll_divider_load3p2_run_rc01.py').read_text(),edits)
def compose_source(nr,nc):
    edits=[
        ('import pll_divider_load3p2_intrinsic as intrinsic','import tx_phase55_intrinsic_generated as intrinsic'),
        ('nssoc_divider_load3p2_native91_wire_v1',MODEL),
        ('nssoc_divider_load3p2_native91_intrinsic_v1',INTRINSIC),
        ('divider_load3p2_wires',CELL),
        ('Full native91 divider composition','Full native55 phase-divider composition'),
        ('==91','==55'),('==205','==126'),('==7','==9'),('==283','==168'),('==37','==24'),('wire_components=37','wire_components=24'),
        ('dict(devices=91,wire_resistors=382,wire_capacitors=649','dict(devices=55,wire_resistors='+str(nr)+',wire_capacitors='+str(nc)),
        ('dict(R=382,C=649)','dict(R='+str(nr)+',C='+str(nc)+')'),
        ('==1031','=='+str(nr+nc)),
        ('Actual raw91 divider devices and382R649C metal/via model','Actual raw55 phase-divider devices and'+str(nr)+'R'+str(nc)+'C metal/via model')]
    return derive((ROOT/'scripts/pll_divider_load3p2_compose_model.py').read_text(),edits)
def source_controls():
    protected();a,proof=audit_source();mutations_source();rc_source(Path('/fixture'),False);rc_source(Path('/fixture'),True)
    for nr,nc in ((123,456),(323,456),(3123,600),(91,7)):
        generated,_=compose_source(nr,nc)
        assert generated.count('=='+str(nr+nc))==2
        assert 'dict(R='+str(nr)+',C='+str(nc)+')'in generated
        assert 'wire_resistors='+str(nr)+',wire_capacitors='+str(nc)in generated
    assert "rel_tol=3e-6,abs_tol=1e-4" in a
    assert "graph.add_nodes_from(a)"in a and "owners['sub']=0"in a
    assert "native_mim_intrinsic=mim_proof"in a
    assert "intrinsic aliases" in a and "every_native_point_ground_capacitance_preserved=True"in a
    bad=[('', [('absent','new')]),('x=1\n',[('x=1','x=1')]),('x=1\ny=2\n',[('','bad')])]
    for text,edits in bad:
        try:derive(text,edits)
        except AssertionError:pass
        else:raise AssertionError('Unsafe source derivation accepted')
    return dict(source_derivations=8,corruptions_rejected=len(bad),original_conservation_gates_retained=True,cap_order_controls=cap_order.controls())
def raw_mim_controls(B,module,anchors):
    P=B/'rc01';names=('wires.spice','baseline.spice',CELL+'.ext',CELL+'.res.ext')
    texts={n:(P/n).read_text()for n in names};source_rows=texts['wires.spice'].splitlines()
    idx=next(i for i,x in enumerate(source_rows)if x.startswith('X'));x=source_rows[idx].split();cases=[]
    def spice_case(name,change):
        lines=source_rows.copy();fields=x.copy();change(fields)
        if fields:lines[idx]=' '.join(fields)
        else:del lines[idx]
        cases.append((name,'wires.spice','\n'.join(lines)+'\n'))
    spice_case('missing_export_mim',lambda f:f.clear())
    spice_case('wrong_export_model',lambda f:f.__setitem__(3,'cap_rfcmim'))
    spice_case('wrong_export_width',lambda f:f.__setitem__(next(i for i,t in enumerate(f)if t.startswith('w=')),'w=999u'))
    spice_case('swapped_export_plates',lambda f:f.__setitem__(slice(1,3),list(reversed(f[1:3]))))
    for name,filename,transform in [
        ('missing_source_device',CELL+'.ext',lambda t:re.sub(r'^device .*\n','',t,count=1,flags=re.M)),
        ('wrong_source_dimension',CELL+'.ext',lambda t:re.sub(r'^(device .*? w=)\S+',r'\g<1>999999',t,count=1,flags=re.M)),
        ('missing_replacement_device',CELL+'.res.ext',lambda t:re.sub(r'^device .*\n','',t,count=1,flags=re.M)),
        ('shifted_replacement_location',CELL+'.res.ext',lambda t:re.sub(r'^(device csubckt cap_cmim )\d+',r'\g<1>1',t,count=1,flags=re.M)),
        ('wrong_parameter_declaration',CELL+'.ext',lambda t:t.replace('parameters cap_cmim w=w l=l','parameters cap_cmim w=l l=w',1))]:
        cases.append((name,filename,transform(texts[filename])))
    original_read=Path.read_text;results=[]
    for name,filename,changed in cases:
        assert changed!=texts[filename]
        def read(path,*a,**kw):return changed if path==P/filename else original_read(path,*a,**kw)
        with patch.object(Path,'read_text',read):
            try:module.audit(P,anchors)
            except ValueError as e:reason=str(e)
            else:raise AssertionError('Accepted '+name)
        assert 'MIM'in reason,(name,reason)
        results.append(dict(name=name,rejected=True,reason=reason,sha256=hashlib.sha256(changed.encode()).hexdigest(),diff=''.join(difflib.unified_diff(texts[filename].splitlines(True),changed.splitlines(True)))))
    assert len(results)==9
    return results
def records(path):
    result=Counter()
    for row in compact.statements(path.read_text())[1:-1]:
        assert row[0].startswith(('R','C','X'))
        key=tuple(row)if row[0][0]in ('R','X')else ('C',*sorted(row[1:3]),Decimal(row[3]))
        result[key]+=1
    return result
def compose(prior,audit):
    source=OUT/'source';B=OUT/'precise';destination=OUT/'composition';destination.mkdir()
    # Restore exact generated methods, including native port order, without modifying them.
    for name,key in [('tx_phase55_native_generated.py','native_derivation'),('tx_phase55_intrinsic_generated.py','intrinsic_derivation')]:
        original=source/name;assert sha(original)==prior[key]['generated_sha256']
        target=ROOT/'scripts'/name;assert not target.exists();shutil.copyfile(original,target)
        assert sha(target)==sha(original)
    intrinsic=load(ROOT/'scripts/tx_phase55_intrinsic_generated.py','tx_phase55_intrinsic_generated')
    native=json.loads((source/'native.json').read_text());planes=json.loads((B/'anchors03.json').read_text())
    text=(B/'rc01/wires.spice').read_text();rows=compact.statements(text)
    extracted=[row for row in rows[1:-1]if row[0].startswith('X')]
    assert len(extracted)==4 and audit['native_mim_intrinsic']['devices']==4
    # Only explicitly checked native MIM cards are projected; all raw R/C tokens survive.
    projected=[row for row in rows if not row[0].startswith('X')]
    assert Counter(map(tuple,projected[1:-1]))==Counter(tuple(row)for row in rows[1:-1]if row[0].startswith(('R','C')))
    wire='\n'.join(' '.join(row)for row in projected)+'\n';(destination/'verified-wire-projection.spice').write_text(wire)
    nr=audit['actual_exported_resistors'];nc=audit['actual_exported_capacitors'];assert min(nr,nc)>0
    generated,method=compose_source(nr,nc);path=destination/'compose.py';path.write_text(generated)
    model=load(path,'phase55_composition');original_controls.compose=model
    tech=json.loads((source/'pdk/libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())['techParams']
    compact_text=(source/'phase55-intrinsic.spice').read_text();intrinsic.verify(compact_text,native['modes']['lvs_flat']['devices'],tech,INTRINSIC)
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
    assert len(controls)==19 and all(c['rejected']for c in controls)
    assert sum('cap_cmim'in row for row in compact.statements(output))==4
    assert positive==dict(devices=55,wire_resistors=nr,wire_capacitors=nc,terminals=168,wire_components=24,body_nodes=1,ports=intrinsic.PORTS+['wire_cref'])
    (destination/'phase55-wire.spice').write_text(output)
    contract=dict(status='PASS_NATIVE55_FOUR_MIM_ONCE_AND_ALL_RC_COMPOSITION_WITH19_CONTROLS_REQUIRES_LOADED_PHASE',positive=positive,controls=controls,method=method,
      projected_native_mim_cards=extracted,verified_native_mim_proof=audit['native_mim_intrinsic'],wire_node_map=mapping,bindings=bindings,
      all_raw_wire_tokens_preserved=True,intrinsic_mim_models_exactly_once=True,model_sha256=sha(destination/'phase55-wire.spice'),
      electrical_accepted=False,deterministic_startup_verified=False,full_clock_tree_implemented=False,full_phy_accepted=False,qualified_pex=False)
    (destination/'composition.json').write_text(json.dumps(contract,indent=2)+'\n')
    return contract
def main():
    p=argparse.ArgumentParser();p.add_argument('--controls',action='store_true');p.add_argument('--summary');p.add_argument('--parts');args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.controls:print(json.dumps(source_controls(),indent=2));return
    assert os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'and os.environ['GITHUB_REPOSITORY']=='Melihakbulut221/nssoc'
    assert os.environ['GITHUB_RUN_ATTEMPT']=='1'
    assert all(re.fullmatch('[0-9a-f]{64}',x or '')for x in (args.summary,args.parts))
    pins=protected();OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,electrical_accepted=False,deterministic_startup_verified=False,
      full_clock_tree_implemented=False,full_phy_accepted=False,qualified_pex=False,variants={})
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,label):
        path=OUT/(label+'.log')
        with path.open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=code,sha256=sha(path)));save()
        if code:print(path.read_text(errors='replace')[-18000:],flush=True)
        assert code==0,(label,code)
    save()
    try:
        job=json.loads(subprocess.check_output(['gh','api',f"repos/Melihakbulut221/nssoc/actions/runs/{SOURCE['run']}"]))
        assert job['status']=='completed'and job['conclusion']=='success'and job['run_attempt']==1
        assert job['head_sha']==SOURCE['head']and job['head_branch']=='codex/tx-clock-phase-parent'
        assert job['path']=='.github/workflows/tx-phase-divider-intrinsic-mim-cloud.yml'
        base=f"https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-{SOURCE['run']}-1-{SOURCE['group']}/{SOURCE['group']}-{SOURCE['run']}-1"
        fetch(base+'.summary.json',args.summary,OUT/'source-summary.json');frozen=json.loads((OUT/'source-summary.json').read_text())
        prior,proof=reports.restore_report(SOURCE['group'],SOURCE['run'],args.summary,args.parts,OUT/'source',list(frozen['outputs']))
        assert prior==frozen and prior['source_head']==SOURCE['head']and prior['sources_unchanged']
        assert prior['status']=='PASS_NATIVE55_INTRINSIC_AND_FOUR_MIM126_PLANES_11_MODEL_6_GEOMETRY_FAULTS_REQUIRES_TWO_ORDER_RC'
        assert len(prior['intrinsic_controls'])==11 and all(x['rejected']for x in prior['intrinsic_controls'])
        assert prior['intrinsic']==dict(devices=55,hbt=19,resistors=20,mim=4,finite_contacts=12,ports=['CLKP','CLKN','MP','MN','QP','QN','DIV_AVDD','AVSS','SUB'])
        assert prior['mim_geometry']['status']=='PASS_ACTUAL_FOUR_MIM_DRAWINGS_AND_ALL126_NATIVE_PLANES_WITH_SIX_FAULTS_REQUIRES_RC'
        r['source']=proof;r['source_head_verified']=SOURCE['head'];r['source_controls']=source_controls();save()
        source=OUT/'source'
        assert sha(source/'native.json')==prior['native_sha256']and sha(source/'phase55-intrinsic.spice')==prior['intrinsic_sha256']and sha(source/'binding.json')==prior['binding_sha256']
        runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text());rt=OUT/'magic-cloud';rt.mkdir();packed=OUT/'runtime.tar.gz'
        fetch(runtime['receipt']['url'],runtime['receipt']['sha256'],packed);assert packed.stat().st_size==runtime['receipt']['bytes'];unpack(packed,rt)
        manifest=json.loads((rt/'manifest.json').read_text());assert all(sha(rt/n)==v['sha256']for n,v in manifest['files'].items());r['runtime']=runtime
        qualified,qproof=reports.restore_report('tx-raw64-totalcap-precision',39486998309,'bdcbddedf70af7e4bc9a1d6b3ec4ac334a619e2fe208244b83a6e8b74cc09a38','3b0dc36952ae38ac4ce1c1ea8e27cac8e4917ca7543a81a916a207b49adaa9e2',OUT/'producer',['precise-source/magic/tclmagic.so'])
        assert qualified['status']=='PASS_REBUILT_NATIVE8074_RC_DOUBLE_TOTALS_AND13_CONTROLS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE'
        for key in ('sources_unchanged','baseline_reproduced_original_rc_and_failure','no_rc_records_changed','no_geometry_technology_or_threshold_change','both_native_input_orders_verified'):assert qualified[key]
        assert qualified['source_changes']['changed_only']=='resis/resis.h'
        assert len(qualified['controls']['cases'])==len(qualified['historical_controls']['cases'])==13
        lib=OUT/'producer/precise-source/magic/tclmagic.so';assert sha(lib)==qualified['rebuilt_runtimes']['precise']['sha256']==PRECISE
        destination=OUT/'precision-runtime';shutil.copytree(rt/'runtime',destination);target=destination/'lib/magic/tcl/tclmagic.so';shutil.copyfile(lib,target);assert sha(target)==PRECISE
        for path in (rt/'runtime').rglob('*'):
            if path.is_file()and path.relative_to(rt/'runtime')!=Path('lib/magic/tcl/tclmagic.so'):assert sha(path)==sha(destination/path.relative_to(rt/'runtime'))
        deps=subprocess.run(['ldd',str(lib)],capture_output=True,text=True);assert deps.returncode==0 and 'not found'not in deps.stdout+deps.stderr
        r['precision_producer']=qproof;r['producer_sha256']=PRECISE;r['producer_dependencies']=deps.stdout+deps.stderr
        pilot=json.loads((ROOT/'docs/evidence/cdr-mim-explicit-model-pilot-pass-20261018.json').read_text())['report']['private_ngspice_tech']
        original=rt/'tech';private=OUT/'ngspice-mim-tech';shutil.copytree(original,private);path=private/'ihp-sg13g2-extract.tech';assert sha(path)==pilot['original_sha256'];text=path.read_text()
        for line in pilot['removed_cdl_device_estimate_lines']:assert text.count(line)==1;text=text.replace(line,'')
        path.write_text(text);assert sha(path)==pilot['private_sha256']
        assert all(sha(private/p.name)==sha(p)for p in original.iterdir()if p.is_file()and p.name!='ihp-sg13g2-extract.tech');r['private_tech']=pilot
        raw=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())['raw_parser'];fetch(raw['url'],raw['sha256'],OUT/'raw-parser.py')
        original_anchor=json.loads((source/'mim/anchors.json').read_text());assert len(original_anchor['anchors'])==126 and len(original_anchor['rows'])==168
        source_inputs={}
        old_prefix='/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-tx-phase-divider-intrinsic-mim/'
        repo_prefix='/home/runner/work/nssoc/nssoc/'
        for name,digest in original_anchor['inputs'].items():
            if name.startswith(old_prefix):target=source/name[len(old_prefix):]
            else:assert name.startswith(repo_prefix);target=ROOT/name[len(repo_prefix):]
            assert sha(target)==digest,(name,target);source_inputs[str(target)]=digest
        run([sys.executable,ROOT/'scripts/tx_reverse_native_cap_order.py','--controls'],'reverse-order-controls')
        for variant in ('precise','precise_reversed'):
            B=OUT/variant;B.mkdir();shutil.copyfile(source/'mim/wires.gds',B/'wires.gds')
            anchors=copy.deepcopy(original_anchor);anchors['inputs']={**source_inputs,str(B/'wires.gds'):sha(B/'wires.gds'),str(source/'mim/anchors.json'):sha(source/'mim/anchors.json')}
            anchors['dispositions']=dict(Counter(row['disposition']for row in anchors['rows']))
            assert anchors['dispositions']==dict(ACTUAL_CONTACT_REFERENCE_WITH_UNMODELED_POLY_DIFFUSION_R=117,RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R=51)
            assert anchors['rows']==original_anchor['rows']and anchors['anchors']==original_anchor['anchors']
            (B/'anchors03.json').write_text(json.dumps(anchors,indent=2)+'\n')
            methods={}
            for name,(text,proof)in [('run-rc01.py',rc_source(B,variant=='precise_reversed')),('audit-rc02.py',audit_source()),('mutations01.py',mutations_source())]:
                (B/name).write_text(text);assert sha(B/name)==proof['generated_sha256'];methods[name]=proof
            run([sys.executable,B/'run-rc01.py'],variant+'-native')
            native=json.loads((B/'rc01/result.json').read_text());assert native['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT'and native['returncode']==0
            run([sys.executable,B/'audit-rc02.py',B/'rc01',B/'anchors03.json',B/'audit.json'],variant+'-raw-audit')
            audit=json.loads((B/'audit.json').read_text());r['variants'][variant]=dict(native=native,audit=audit,methods=methods);save()
            assert audit['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY',audit.get('error')
            assert audit['native_mim_intrinsic']['devices']==4 and audit['geometry_probes']==126
            run([sys.executable,B/'mutations01.py'],variant+'-raw-controls')
            controls=json.loads((B/'native-mutations01.json').read_text());assert controls['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'and len(controls['cases'])==13
            module=load(B/'audit-rc02.py','phase_mim_strict_'+variant);mim=raw_mim_controls(B,module,anchors)
            for name,proof in methods.items():assert sha(B/name)==proof['generated_sha256']
            r['variants'][variant].update(wire_controls=controls,mim_controls=mim);save()
        first=OUT/'precise/rc01';second=OUT/'precise_reversed/rc01'
        assert records(first/'wires.spice')==records(second/'wires.spice'),'Two-order native R/C/device records differ'
        _,equivalence=cap_order.reorder((second/(CELL+'.ext')).read_text(),(first/(CELL+'.ext')).read_text())
        for token in ('device','parameters','node','port','equiv','substrate'):
            assert [x for x in cap_order.rows((first/(CELL+'.ext')).read_text())if x[0]==token]==[x for x in cap_order.rows((second/(CELL+'.ext')).read_text())if x[0]==token],token
        reversal=json.loads((second/(CELL+'.order-proof.json')).read_text());assert reversal['reversed_enumeration']and reversal['symmetric_endpoint_value_multiset_exact']and reversal['non_coupling_records_unchanged']
        r['native_order_equivalence']=equivalence;r['reversal']=reversal
        r['composition']=compose(prior,r['variants']['precise']['audit']);save()
        assert all(sha(source/n)==digest for n,digest in prior['outputs'].items())
        assert all(sha(rt/n)==v['sha256']for n,v in manifest['files'].items())and sha(OUT/'raw-parser.py')==raw['sha256']
        protected();r.update(status='PASS_NATIVE55_FOUR_MIM_TWO_PRECISE_ORDERS_22_CONTROLS_EACH_AND19_COMPOSITION_CONTROLS_REQUIRES_LOADED_PHASE',
          sources_unchanged=True,both_native_orders_verified=True,native_rc_and_device_records_equal_in_both_orders=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
