#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact native phase55 compact binding and real four-MIM geometry prerequisite."""
import ast,hashlib,importlib.util,json,os,re,subprocess,sys,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as compact
import cloud_pll_divider_load3p2v2_compose as original_controls
from cloud_tx_driver_localpins_intrinsic import PDK
from run_cloud_tx_layout_repair import sha,fetch
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-phase-divider-intrinsic-mim'
TOP='nssoc_tx_phase_divider55_v1';INTRINSIC='nssoc_tx_phase_divider55_intrinsic_v1'
SOURCE=dict(run=40082784240,head='db46f332c4438e21bf55dae4ec9cc4a85b8afd32',group='tx-phase-divider-wires',
 summary='f1c445c151a34323fbc9366e4ddbbb29f3d0d26d97612536a1cf1c556100faf8',
 parts='cfa3093662f5a1804f588a32f7709f88622408d34f060f0ab30f6913f7f3e86a')
GDS='c9f55e2220c2278edbbe83d54d6da1ffcbf25b88de32b7335cde1e416e6e795b'
def derive(text,edits):
    original=text
    for before,after,count in edits:
        assert text.count(before)==count,(before,text.count(before));text=text.replace(before,after)
    reverse=text
    for before,after,count in reversed(edits):
        assert reverse.count(after)==count,(after,reverse.count(after));reverse=reverse.replace(after,before)
    assert reverse==original
    ast.parse(text);return text
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ['GITHUB_REPOSITORY']=='Melihakbulut221/nssoc'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,wire_rc_extracted=False,
      electrical_accepted=False,deterministic_startup_verified=False,full_clock_tree_implemented=False,full_phy_accepted=False,qualified_pex=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def execute(cmd,label):
        with (OUT/(label+'.log')).open('w')as f:p=subprocess.run(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        r.setdefault('executions',{})[label]=dict(returncode=p.returncode,log_sha256=sha(OUT/(label+'.log')));save()
        if p.returncode:print((OUT/(label+'.log')).read_text(errors='replace')[-20000:],flush=True)
        assert p.returncode==0,label
    save()
    try:
        pins=json.loads((ROOT/'scripts/tx-phase-divider-intrinsic-mim-methods.json').read_text())
        assert all(sha(ROOT/p)==h for p,h in pins.items())
        live=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/'+str(SOURCE['run'])]))
        assert live['status']=='completed'and live['conclusion']=='success'and live['run_attempt']==1 and live['head_sha']==SOURCE['head']
        assert live['head_branch']=='codex/tx-clock-phase-parent'and live['path']=='.github/workflows/tx-phase-divider-wires-cloud.yml'
        base=f"https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-{SOURCE['run']}-1-{SOURCE['group']}/{SOURCE['group']}-{SOURCE['run']}-1"
        fetch(base+'.summary.json',SOURCE['summary'],OUT/'wire-summary.json');prior=json.loads((OUT/'wire-summary.json').read_text())
        source=OUT/'source';record,proof=reports.restore_report(SOURCE['group'],SOURCE['run'],SOURCE['summary'],SOURCE['parts'],source,list(prior['outputs']))
        assert record==prior and prior['source_head']==SOURCE['head']and prior['sources_unchanged']and prior['generated_sources_unchanged']
        assert prior['status']=='PASS_NATIVE55_PHASE_WIRES_ALL168_TERMINALS_AND_SEVEN_FAULTS_REQUIRES_FRESH_RC_AND_LOADED_PHASE'
        assert prior['physical_gds_sha256']==GDS
        assert prior['native_measured_counts']==dict(native_device_count=55,native_terminal_count=168,wire_component_count=24,native_net_count=44,native_electrical_net_count=25)
        assert prior['anchors']['counts']==dict(devices=55,terminals=168,metal_terminals=117,body_terminals=51,public_ports=9,unique_reference_planes=126,wire_components=24)
        assert len(prior['anchors']['negative_controls'])==7 and all(x['rejected']for x in prior['anchors']['negative_controls'])
        r['wire_source']=proof;r['original_anchor_controls']=prior['anchors']['negative_controls'];save()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        native_edits=[
          ("PORTS=['CLKP','CLKN','QP','QN','DIV_AVDD','AVSS','SUB']","PORTS=['CLKP','CLKN','MP','MN','QP','QN','DIV_AVDD','AVSS','SUB']",1),
          ("nssoc_clock_div4_load3p2_v1_layout",TOP,1),
          ('ee95597fc6307f2476d49d9ac5560ed6b06d4dcda956f7716e0d7ea5611731f6',GDS,1),
          ("root=source/'source/wire';gds=root/'source/layout'/(TOP+'.gds');database=root/'raw_flat/result.lvsdb'","root=source/'source';gds=root/'layout'/(TOP+'.gds');database=root/'flat_lvs/result.lvsdb'",1),
          ("source/'anchors03.json'","source/'anchors.json'",1),
          ("root/'source/layout/result.json'","root/'layout/result.json'",1),
          ("root/'native01/result.json'","source/'native01/result.json'",1),
          ('c.pin_count()==7','c.pin_count()==9',1),
          ('==91','==55',1),
          ('Counter(npn13G2=34,rppd=33,cap_cmim=6,ptap1=18)','Counter(npn13G2=19,rppd=20,cap_cmim=4,ptap1=12)',1),
          ('len(names)==38 and len(set(names.values()))==38','len(names)==25 and len(set(names.values()))==25',1),
          ('==283','==168',2),
          ('EXPORTED_NATIVE_DIVIDER91_AND283_TERMINALS_NOT_ELECTRICAL_ACCEPTANCE','EXPORTED_NATIVE_PHASE55_AND168_TERMINALS_NOT_ELECTRICAL_ACCEPTANCE',1)]
        old=ROOT/'scripts/pll_divider_load3p2_native.py';new=ROOT/'scripts/tx_phase55_native_generated.py';assert not new.exists()
        new.write_text(derive(old.read_text(),native_edits));(OUT/new.name).write_bytes(new.read_bytes())
        r['native_derivation']=dict(original_sha256=sha(old),generated_sha256=sha(new),edits=native_edits,reversible=True);save()
        execute([app,'python',new,source,OUT],'native-export')
        native=json.loads((OUT/'native.json').read_text());rows=native['modes']['lvs_flat']['devices'];assert len(rows)==55 and native['gds_sha256']==GDS
        edits=[
          ('from pll_divider_load3p2_native import ORDER,PORTS','from tx_phase55_native_generated import ORDER,PORTS',1),
          ('91-device','55-device',1),('==91','==55',1),
          ('dict(devices=91,hbt=34,resistors=33,mim=6,finite_contacts=18,ports=PORTS)','dict(devices=55,hbt=19,resistors=20,mim=4,finite_contacts=12,ports=PORTS)',1)]
        old=ROOT/'scripts/pll_divider_load3p2_intrinsic.py';new=ROOT/'scripts/tx_phase55_intrinsic_generated.py';assert not new.exists()
        new.write_text(derive(old.read_text(),edits));(OUT/new.name).write_bytes(new.read_bytes())
        r['intrinsic_derivation']=dict(original_sha256=sha(old),generated_sha256=sha(new),edits=edits,reversible=True)
        spec=importlib.util.spec_from_file_location('tx_phase55_intrinsic_generated',new);intrinsic=importlib.util.module_from_spec(spec);spec.loader.exec_module(intrinsic)
        models=OUT/'pdk';model_pins={p:h for p,h in compact.MODEL_PINS.items()if p.endswith(('resistors_mod.lib','sg13g2_hbt_mod.lib','capacitors_mod.lib','sg13g2_tech.json','utility_functions.py'))}
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
        text,binding=intrinsic.build(rows,tech,INTRINSIC);(OUT/'phase55-intrinsic.spice').write_text(text)
        r['intrinsic']=intrinsic.verify(text,rows,tech,INTRINSIC);r['intrinsic_bindings']=binding
        controls=OUT/'intrinsic-controls';controls.mkdir()
        r['intrinsic_controls']=original_controls.controls(text,lambda s:intrinsic.verify(s,rows,tech,INTRINSIC),controls,False)
        assert len(r['intrinsic_controls'])==11 and all(x['rejected']for x in r['intrinsic_controls'])
        (OUT/'binding.json').write_text(json.dumps(dict(native=native,intrinsic_bindings=binding,ports=intrinsic.PORTS),indent=2)+'\n');save()
        execute([app,'python',ROOT/'scripts/tx_phase55_mim_native.py',source,OUT],'native-mim-geometry')
        r['mim_geometry']=json.loads((OUT/'mim/result.json').read_text())
        assert r['mim_geometry']['status']=='PASS_ACTUAL_FOUR_MIM_DRAWINGS_AND_ALL126_NATIVE_PLANES_WITH_SIX_FAULTS_REQUIRES_RC'
        assert all(sha(source/p)==h for p,h in prior['outputs'].items())
        assert all(sha(models/p)==h for p,h in model_pins.items())and all(sha(ROOT/p)==h for p,h in pins.items())
        for key,name in [('native_derivation','tx_phase55_native_generated.py'),('intrinsic_derivation','tx_phase55_intrinsic_generated.py')]:
            assert sha(ROOT/'scripts'/name)==sha(OUT/name)==r[key]['generated_sha256']
        r.update(status='PASS_NATIVE55_INTRINSIC_AND_FOUR_MIM126_PLANES_11_MODEL_6_GEOMETRY_FAULTS_REQUIRES_TWO_ORDER_RC',
          sources_unchanged=True,native_sha256=sha(OUT/'native.json'),intrinsic_sha256=sha(OUT/'phase55-intrinsic.spice'),
          binding_sha256=sha(OUT/'binding.json'),models=dict(commit=PDK,hashes=model_pins))
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
