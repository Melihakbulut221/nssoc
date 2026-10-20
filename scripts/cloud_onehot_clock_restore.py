#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Prepare one measured historical clock route in the latest actual routed chip."""
import json,os,shutil,subprocess
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from bootstrap_flow import verify
from route_cloud_newer_postcts import sha
from cloud_onehot_clock_geometry import PINS,ODB
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-onehot-clock-restore'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,
       scope='Physical single-clock-route candidate only. Requires DRC, inter-net short and connectivity checks, fresh RC, full original three-corner STA before acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    def run(cmd,label,mode=None,fault=None,expected=None):
        env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')}
        if mode:env['NSSOC_CLOCK_RESTORE_MODE']=mode
        if fault:env['NSSOC_CLOCK_RESTORE_FAULT']=fault
        path=OUT/(label+'.log')
        with path.open('w')as f:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=code));save()
        if expected:
            assert code!=0 and expected in path.read_text(),(label,'Expected native fault was not rejected')
        else:
            if code:print(path.read_text()[-10000:],flush=True)
            assert code==0,(label,code)
        return code
    try:
        protected={};sources={}
        for tag,pin in PINS.items():
            names=[ODB]
            if tag=='after':names+=['run/2-openroad-detailedrouting/soc_top.nl.v','run/2-openroad-detailedrouting/state_out.json','trial-config.json']
            source,proof=reports.restore_report(pin['group'],pin['run'],pin['summary'],pin['parts'],OUT/tag,names)
            assert source['sources_unchanged']and source['returncode']==0 and source['detailed_route_complete']
            assert source['native_routing_drc_errors']==0 and source['critical_disconnected_pins']==0
            assert sha(OUT/tag/ODB)==pin['odb_sha256']==source['routed_odb_sha256']
            for name in names:
                assert sha(OUT/tag/name)==source['outputs'][name]
                protected[str(OUT/tag/name)]=sha(OUT/tag/name)
            sources[tag]=dict(**pin,restore_proof=proof)
            if tag=='after':r['original_measurements']=source['measurements']
        (OUT/'sources.json').write_text(json.dumps(sources,indent=2)+'\n')
        r['sources']=sources;save()
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        exe=shutil.which('openroad');assert exe
        helper=ROOT/'scripts/prepare_onehot_clock_restore.py'
        for p in (Path(__file__),helper,ROOT/'scripts/cloud_onehot_clock_geometry.py',OUT/'sources.json'):protected[str(p)]=sha(p)
        run([exe,'-exit','-python',helper],'prepare-native-clock-transfer')
        plan=json.loads((OUT/'transfer-plan.json').read_text())
        assert plan['net']=='clknet_3_5_0_pcie_clk_i'
        assert plan['patch_sha256']==sha(OUT/'clock-patch.def')and plan['import_base_sha256']==sha(OUT/'import-base.odb')
        tcl=OUT/'import.tcl'
        tcl.write_text('read_db {'+str(OUT/'import-base.odb')+'}\nread_def -incremental {'+str(OUT/'clock-patch.def')+'}\nwrite_db {'+str(OUT/'candidate.odb')+'}\nwrite_verilog {'+str(OUT/'candidate.v')+'}\n')
        baseline=OUT/'export-baseline.tcl'
        baseline.write_text('read_db {'+str(OUT/'after'/ODB)+'}\nwrite_verilog {'+str(OUT/'baseline-export.v')+'}\n')
        run([exe,'-exit',baseline],'export-unchanged-baseline-netlist')
        run([exe,'-exit',tcl],'native-incremental-clock-def-import')
        run([exe,'-exit','-python',helper],'native-route-transfer-proof','audit')
        r['proof']=json.loads((OUT/'transfer-proof.json').read_text())
        assert r['proof']['original_clock_route_restored_exactly']and r['proof']['all_unrelated_def_content_unchanged']
        # Actual placement and wire-type corruptions must be rejected while
        # leaving the original positive ODB and positive DEF untouched.
        positive={str(OUT/p):sha(OUT/p)for p in ('candidate.odb','candidate.def','candidate.v','transfer-proof.json')}
        run([exe,'-exit','-python',helper],'reject-unrelated-cell-motion','audit','unrelated_location','Unrelated DEF geometry, cells or connectivity changed')
        run([exe,'-exit','-python',helper],'reject-unfixed-clock-route','audit','wire_type','Clock route is not physically fixed')
        assert all(sha(Path(p))==v for p,v in positive.items())
        # Compare native exports of the unchanged source ODB and candidate ODB:
        # the physical-only clock wire change must not rewrite logic or ports.
        assert sha(OUT/'candidate.v')==sha(OUT/'baseline-export.v'),'Native physical transfer changed exported netlist'
        cfg=json.loads((OUT/'after/trial-config.json').read_text())
        assert cfg['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
        assert cfg['CLOCK_PERIOD']==20 and cfg['TIME_DERATING_CONSTRAINT']==5
        assert cfg['SETUP_VIOLATION_CORNERS']==cfg['HOLD_VIOLATION_CORNERS']==['*']
        state=json.loads((OUT/'after/run/2-openroad-detailedrouting/state_out.json').read_text())
        state.update(odb=str(OUT/'candidate.odb'),nl=str(OUT/'candidate.v'),spef=None,metrics={});state['def']=str(OUT/'candidate.def')
        (OUT/'candidate-state.json').write_text(json.dumps(state,indent=2)+'\n')
        (OUT/'trial-config.json').write_text(json.dumps(cfg,indent=2)+'\n')
        assert all(sha(Path(p))==v for p,v in protected.items())
        r.update(status='PASS_NATIVE_CLOCK_ROUTE_TRANSFER_REQUIRES_PHYSICAL_LEGALIZATION_RC_AND_STA',sources_unchanged=True,
            controls=dict(unrelated_cell_motion_rejected=True,unfixed_clock_route_rejected=True),
            netlist_literal_identity=True,candidate_odb_sha256=sha(OUT/'candidate.odb'),candidate_netlist_sha256=sha(OUT/'candidate.v'),
            candidate_state='candidate-state.json',native_openroad_sha256=sha(Path(exe)))
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
