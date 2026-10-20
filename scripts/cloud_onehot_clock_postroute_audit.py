#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only audit of already routed/extracted clock-repair artifacts; no routing."""
import hashlib,json,math,os,subprocess,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-onehot-clock-postroute-audit'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
        full_phy_accepted=False,final_timing_complete=False,qualified_pex=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/onehot-clock-route-complete-postcheck-failure-20261020.json').read_text())
        assert pin['run']==39373842033 and pin['summary_sha256']=='fe4da272657ae98da5a7ffc510c7e067afd550b22a3eabcadac7e78e4e3e86a7'
        assert pin['parts_sha256']=='1f7be7c3559dfeecb59ad74fce0e48ab2253754c45a6472742df3f3668381d4a'
        names=[n for n in pin['outputs']if n in (
            'run/1-openroad-detailedrouting/soc_top.odb','run/1-openroad-detailedrouting/soc_top.nl.v',
            'run/1-openroad-detailedrouting/state_out.json','run/2-openroad-checkantennas/state_out.json',
            'run/2-openroad-checkantennas/reports/antenna.rpt',
            'run/3-odb-reportdisconnectedpins/state_out.json',
            'run/4-nssoc-onehotroutercx/native-spef-integrity.json',
            'run/5-nssoc-onehotroutedsta/native-sta-script-proof.json',
            'run/5-nssoc-onehotroutedsta/state_out.json')or
            (n.startswith('run/5-nssoc-onehotroutedsta/')and n.endswith(('.rpt','sta.log','filter_unannotated_metrics.json')))]
        original,proof=reports.restore_report('onehot-clock-restore-route',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'routed',names)
        assert original['status']=='FAIL_OR_ERROR_NO_SOURCE_RESTART'
        assert original['source_head']==pin['source_head']=='840f9681704b89b471814ee0108dc60f3429f219'
        assert original['returncode']==0 and original['detailed_route_complete']
        assert original['error']=="AssertionError('Actual routed candidate geometry or topology changed')"
        assert original['routed_odb_sha256']=='bde963927da325e3f66c1c62d6f78f5db4c60b1344670ebabd04d3339c1a5850'
        r['completed_native_source']=proof;r['original_rejection']=dict(status=original['status'],error=original['error'])
        cp=json.loads((ROOT/'docs/evidence/onehot-clock-restore-pass-20261020.json').read_text())
        base,bproof=reports.restore_report(cp['group'],cp['run'],cp['summary_sha256'],cp['parts_sha256'],OUT/'before',['candidate.odb','transfer-proof.json'])
        assert base==cp['report']and base['sources_unchanged']
        assert base['candidate_odb_sha256']=='c13a87d9127193482c96708e2f7bbdce8d83636fe4800876d9dbc14e89c6b23e'
        r['exact_before_source']=bproof
        a=OUT/'before/candidate.odb';b=OUT/'routed/run/1-openroad-detailedrouting/soc_top.odb'
        assert sha(a)==base['candidate_odb_sha256']and sha(b)==original['routed_odb_sha256']
        old=ROOT/'scripts/check_onehot_coverage_data_routed_topology.py'
        new=ROOT/'scripts/check_onehot_clock_postroute_topology.py'
        delta=json.loads((ROOT/'scripts/onehot-clock-postroute-topology-delta.json').read_text())
        assert sha(old)==delta['baseline_sha256']
        text=old.read_text()
        for edit in delta['edits']:
            assert text.count(edit['before'])==edit['count'];text=text.replace(edit['before'],edit['after'])
        assert new.read_text()==text and sha(new)==delta['candidate_sha256']
        app=Path(os.environ['CLOUD_APPIMAGE'])
        assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        fixed=ROOT/'scripts/check_onehot_fixed_clock_route.py'
        protected={str(p):sha(p)for p in [Path(__file__),old,new,fixed,a,b,*[OUT/'routed'/n for n in names]]}
        # Record metrics independently of the final topology gate, so a rejected
        # topology never hides the actual completed native timing evidence.
        sta=OUT/'routed/run/5-nssoc-onehotroutedsta'
        state=json.loads((sta/'state_out.json').read_text())
        r['measurements']={}
        for corner in ('nom_slow_1p08V_125C','nom_typ_1p20V_25C','nom_fast_1p32V_m40C'):
            folder=sta/corner
            assert not(folder/'unpropagated.rpt').read_text().strip()
            assert 'NSSOC_ROUTED_ORIGINAL_CLOCKS_PROPAGATED'in (folder/'sta.log').read_text()
            keys=['timing__setup__ws','timing__hold__ws','timing__setup_vio__count','timing__hold_vio__count','design__max_cap_violation__count','design__max_slew_violation__count','design__max_fanout_violation__count']
            m={k:state['metrics'][k+'__corner:'+corner]for k in keys}
            assert all(math.isfinite(float(v))for v in m.values())
            r['measurements'][corner]=m
        for label,file in [('spef_integrity','run/4-nssoc-onehotroutercx/native-spef-integrity.json'),('sta_script_proof','run/5-nssoc-onehotroutedsta/native-sta-script-proof.json')]:
            r[label]=json.loads((OUT/'routed'/file).read_text())
        from check_final_native_antenna_counts import validate
        ar=OUT/'routed/run/2-openroad-checkantennas'
        r['antenna']=validate((ar/'reports/antenna.rpt').read_text(),json.loads((ar/'state_out.json').read_text())['metrics'])
        assert r['antenna']==original['final_antenna']
        physical=json.loads((OUT/'routed/run/3-odb-reportdisconnectedpins/state_out.json').read_text())['metrics']
        r['routing_drc_errors']=physical['route__drc_errors'];r['critical_disconnected_pins']=physical['design__critical_disconnected_pin__count']
        save()
        env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')}
        env.update(NSSOC_TOPOLOGY_BEFORE=str(a),NSSOC_TOPOLOGY_AFTER=str(b))
        for label,method,var in [('topology',new,'NSSOC_TOPOLOGY_OUT'),('fixed_clock',fixed,'NSSOC_CLOCK_ROUTE_PROOF_OUT')]:
            output=OUT/(label+'.json')
            with(OUT/(label+'.log')).open('w')as f:
                rc=subprocess.call([str(app),'openroad','-exit','-python',str(method)],cwd=ROOT,env={**env,var:str(output)},stdout=f,stderr=subprocess.STDOUT)
            r[label+'_returncode']=rc
            if output.is_file():r[label]=json.loads(output.read_text())
            save()
            if rc:print((OUT/(label+'.log')).read_text()[-12000:],flush=True)
            assert rc==0,('Actual saved native geometry/topology audit failed',label)
        assert len(r['topology']['rejected'])==4
        assert r['topology']['proof']['original_masters_geometry_all_pins_nets_ndrs_ports_preserved']
        assert r['fixed_clock']['original_physical_route_preserved']
        assert all(sha(Path(p))==v for p,v in protected.items())
        assert all(sha(OUT/'routed'/n)==original['outputs'][n]for n in names)
        r.update(status='COMPLETE_SAVED_CLOCK_ROUTE_TOPOLOGY_AND_ORIGINAL_THREE_CORNER_READOUT_NOT_SIGNOFF',
            sources_unchanged=True,protected_inputs=protected,
            scope='Read only exact saved ODBs and original routed STA reports. Same complete cell/pin/net/geometry conservation and four faults; source-specific SHA pins replace an obsolete previous-stage constant. Remaining antenna and timing violations are not waived; no rerouting or metric modification.')
    except BaseException as e:r.update(status='FAIL_OR_ERROR_SAVED_ARTIFACTS_RETAINED',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
