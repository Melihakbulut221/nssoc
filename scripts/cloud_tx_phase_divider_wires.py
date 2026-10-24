#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fresh native graph and physical terminal planes for the real phase-output cell."""
import hashlib,json,os,shutil,subprocess,sys,tarfile,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-phase-divider-wires'
TOP='nssoc_tx_phase_divider55_v1'
PHYSICAL_RUN=40079962143
PHYSICAL_HEAD='60b6cc9bf263a3fc2e08aa434bff4292a6df1143'
PHYSICAL_STATUS='PASS_NATIVE55_PHASE_OUTPUTS_DRC_DEEP_FLAT_LVS_AND_FIVE_FAULTS_REQUIRES_LOADED_PHASE_AND_FRESH_RC'
REPO='repos/Melihakbulut221/nssoc/'
def api(p):return json.loads(subprocess.check_output(['gh','api',REPO+p]))
def derive(original,edits):
    result=original
    for old,new,count in edits:
        assert result.count(old)==count,(old,result.count(old),count)
        result=result.replace(old,new)
    reverse=result
    for old,new,count in reversed(edits):
        assert reverse.count(new)==count,(new,reverse.count(new),count)
        reverse=reverse.replace(new,old)
    assert reverse==original,'Derivation changed a native ownership or anchor algorithm'
    return result

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ['GITHUB_REPOSITORY']=='Melihakbulut221/nssoc'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,
      phase_electrically_verified=False,deterministic_startup_verified=False,wire_rc_extracted=False,qualified_pex=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        methods=json.loads((ROOT/'scripts/tx-phase-divider-wires-methods.json').read_text())
        assert all(sha(ROOT/p)==h for p,h in methods.items())
        live=api('actions/runs/'+str(PHYSICAL_RUN))
        assert live['head_sha']==PHYSICAL_HEAD and live['run_attempt']==1
        assert live['head_branch']=='codex/tx-clock-phase-parent'and live['path']=='.github/workflows/tx-phase-divider-physical-cloud.yml'
        assert live['status']=='completed'and live['conclusion']=='success','Physical prerequisite must finish successfully before extraction'
        jobs=api('actions/runs/'+str(PHYSICAL_RUN)+'/jobs')['jobs']
        assert len(jobs)==1 and jobs[0]['name']=='native'and jobs[0]['conclusion']=='success'
        group='tx-phase-divider-physical';release=api('releases/tags/cloud-results-'+str(PHYSICAL_RUN)+'-1-'+group)
        pins={}
        for suffix,key in [('.summary.json','summary'),('.parts.json','parts')]:
            assets=[a for a in release['assets']if a['name']==group+'-'+str(PHYSICAL_RUN)+'-1'+suffix];assert len(assets)==1
            a=assets[0];assert a['size']<4*1024**2
            data=subprocess.check_output(['gh','api',REPO+'releases/assets/'+str(a['id']),'-H','Accept: application/octet-stream'])
            h=hashlib.sha256(data).hexdigest();assert a['digest']=='sha256:'+h
            pins[key]=h;(OUT/('physical'+suffix)).write_bytes(data)
        selected=('layout/'+TOP+'.gds','layout/result.json','layout/schematic.cir','flat_lvs/result.lvsdb','flat_lvs/audit.json','flat_lvs/extracted.cir','deep_lvs/audit.json','geometry-audit.json')
        source=OUT/'source';prior,proof=reports.restore_report(group,PHYSICAL_RUN,pins['summary'],pins['parts'],source,selected)
        assert prior['source_head']==PHYSICAL_HEAD and prior['status']==PHYSICAL_STATUS and prior['sources_unchanged']
        assert all(prior['steps'][n]['expected_verdict_observed']for n in ['drc','deep_lvs','flat_lvs','master_access_open','master_slave_short','wrong_feedback','wrong_seed','offgrid'])
        assert prior['steps']['drc']['measurement']['category_count']==560 and prior['steps']['drc']['measurement']['markers']==0
        assert prior['geometry_audit']['devices']==55 and prior['geometry_audit']['ports']==9
        gds=source/'layout'/(TOP+'.gds');gds_sha=sha(gds);assert gds_sha==prior['outputs']['layout/'+TOP+'.gds']
        r.update(physical_source=proof,physical_gds_sha256=gds_sha);save()
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());packed=OUT/'fixture.tar.gz'
        fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed);assert packed.stat().st_size==spec['receipt']['bytes']
        with tarfile.open(packed)as t:t.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        pcells=[ROOT/n for n in manifest['files']if n.endswith('/ihp/npn13G2_code.py')];assert len(pcells)==1
        assert sha(pcells[0])=='634cda63717ab4122f15e0fef5f3e8475e90e67e043823f5b8ed208e695f1729'
        shutil.copyfile(pcells[0],OUT/'npn13G2_code.py')
        def execute(script,label,*args):
            log=OUT/(label+'.log')
            with log.open('w')as f:p=subprocess.run([str(app),'python',str(script),*map(str,args)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
            r.setdefault('executions',{})[label]=dict(returncode=p.returncode,log_sha256=sha(log));save()
            if p.returncode:print(log.read_text(errors='replace')[-16000:],flush=True)
            assert p.returncode==0,label+' rejected'
        original=(ROOT/'scripts/tx_driver_localpins_wire_native.py').read_text()
        edits=[
          ('nssoc_tx_input_driver_v7_physical_localpins_v1',TOP,1),
          ("P=B/'inputs/tx-input-driver-localpins/cloud-tx-input-driver-localpins'","P=B/'source'",1),
          ("P/'base/layout.gds'","P/'layout/"+TOP+".gds'",1),
          ("P/'check-raw_flat_lvs/","P/'flat_lvs/",2),
          ('6f7a7cf92c1dc25a259acdbff779c7cce841128991abb780e13478aa84b4eb62',gds_sha,1),
          ('c.pin_count()==6','c.pin_count()==9',1),
          ('dict(sg13_hv_nmos=40,sg13_lv_nmos=22,sg13_lv_pmos=22,ptap1=10,ntap1=2,rppd=4)','dict(npn13G2=19,rppd=20,cap_cmim=4,ptap1=12)',1),
          ("'full_driver_wires'","'phase_divider55_wires'",1),
          ("'DRIVERWIRES'","'PHASEDIVIDERWIRES'",1),
          ('PASS_FULL_DRIVER_METAL_VIA_GRAPH_BOUND_TO_ALL100_NATIVE_DEVICES_NO_RC','PASS_PHASE55_METAL_VIA_GRAPH_BOUND_TO_ALL55_NATIVE_DEVICES_NO_RC',1)]
        script=OUT/'wire-native.py';script.write_text(derive(original,edits));generated={script:sha(script)}
        r['graph_derivation']=dict(original_sha256=methods['scripts/tx_driver_localpins_wire_native.py'],generated_sha256=sha(script),exact_edits=edits,algorithm_unchanged=True)
        execute(script,'wire-graph')
        graph=json.loads((OUT/'native01/result.json').read_text())
        assert graph['native_device_count']==55 and graph['native_terminal_count']==168
        assert set(graph['native_ports'])=={'CLKP','CLKN','QP','QN','MP','MN','DIV_AVDD','AVSS','SUB'}
        assert graph['no_wire_geometry_change']and graph['no_component_union_by_native_label']
        components=graph['wire_component_count'];assert components==len(graph['wire_components'])>0
        assert graph['native_electrical_net_count']==len({t['native_cluster']for t in graph['native_net_coverage']if t['device_terminals']})
        r['native_measured_counts']={k:graph[k]for k in ['native_device_count','native_terminal_count','wire_component_count','native_net_count','native_electrical_net_count']};save()
        original=(ROOT/'scripts/pll_divider_load3p2_anchors_native.py').read_text()
        edits=[
          ('All91 divider devices:283 terminal planes','All55 phase-divider devices:168 terminal planes',1),
          ('nssoc_clock_div4_load3p2_v1_layout',TOP,1),
          ("db=source/'raw_flat/result.lvsdb'","db=physical_source/'flat_lvs/result.lvsdb'",1),
          ('assert len(devices)==91','assert len(devices)==55',1),
          ('Counter(npn13G2=34,rppd=33,cap_cmim=6,ptap1=18)','Counter(npn13G2=19,rppd=20,cap_cmim=4,ptap1=12)',1),
          ('assert len(owner)==37','assert len(owner)=='+str(components),1),
          ("assert len(rows)==283 and sum('reference_label'in r for r in rows)==198 and len(public)==7","assert len(rows)==168 and sum('reference_label'in r for r in rows)==117 and len(public)==9",1),
          ("assert len(observed)==283 and len({(r['device'],r['terminal']) for r in observed})==283","assert len(observed)==168 and len({(r['device'],r['terminal']) for r in observed})==168",1),
          ('PASS_ALL283_DIVIDER_TERMINALS_BOUND_WITH198_METAL85_BODY_AND_SEVEN_FAULTS_NOT_RC_ACCEPTANCE','PASS_ALL168_PHASE_TERMINALS_BOUND_WITH117_METAL51_BODY_AND_SEVEN_FAULTS_NOT_RC_ACCEPTANCE',1),
          ('devices=91,terminals=283,metal_terminals=198,body_terminals=85,public_ports=7','devices=55,terminals=168,metal_terminals=117,body_terminals=51,public_ports=9',1),
          ('wire_components=37','wire_components='+str(components),1),
          ('OUT=Path(sys.argv[1]);generate()',"OUT=Path(sys.argv[1]);generate(OUT,OUT/'source')",1)]
        script=OUT/'anchors-native.py';script.write_text(derive(original,edits));generated[script]=sha(script)
        r['anchor_derivation']=dict(original_sha256=methods['scripts/pll_divider_load3p2_anchors_native.py'],generated_sha256=sha(script),exact_edits=edits,physical_selection_and_all_seven_faults_unchanged=True)
        execute(script,'all-terminal-anchors',OUT)
        anchors=json.loads((OUT/'anchors.json').read_text());assert len(anchors['negative_controls'])==7 and all(f['rejected']for f in anchors['negative_controls'])
        assert anchors['counts']['terminals']==168 and anchors['counts']['body_terminals']==51 and anchors['counts']['public_ports']==9
        assert anchors['counts']['wire_components']==components and len(anchors['rows'])==168
        assert all(sha(p)==h for p,h in generated.items())and all(sha(ROOT/p)==h for p,h in methods.items())
        assert all(sha(source/p)==prior['outputs'][p]for p in selected)
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        r.update(status='PASS_NATIVE55_PHASE_WIRES_ALL168_TERMINALS_AND_SEVEN_FAULTS_REQUIRES_FRESH_RC_AND_LOADED_PHASE',
          sources_unchanged=True,generated_sources_unchanged=True,graph=graph,anchors=anchors)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
