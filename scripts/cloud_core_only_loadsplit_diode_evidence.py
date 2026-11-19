#!/usr/bin/env python3
"""Bind the 44-diode map to real archived preparation and baseline export evidence."""
import os,json,hashlib,copy
from pathlib import Path
from cloud_core_only_postgrt import completed,archive
from rebind_loadsplit_antenna_inventory import EXPECTED,rebind_inventory,verify_moved_export
from check_antenna_netlist_export import check_added_antennas

def verified(run,head,name,aid,digest):
    rr=completed(run,head)
    z,m=archive(rr,name)
    assert m['id']==aid and m['digest']=='sha256:'+digest
    r=json.loads(z.read('result.json'))
    assert r['source_head']==head and r['sources_unchanged'] and r['accepted'] is False
    assert set(n for n in z.namelist() if not n.endswith('/') and n!='result.json')==set(r['outputs'])
    for n,h in r['outputs'].items():
        assert hashlib.sha256(z.read(n)).hexdigest()==h,n
    return z,r,m

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=Path('hw/soc/out/loadsplit-diode-evidence');out.mkdir(parents=True,exist_ok=False)
    report=dict(source_head=os.environ['GITHUB_SHA'],status='VERIFYING',accepted=False,final_timing_complete=False)
    try:
        z,b,bm=verified(44550131521,'1aa4f5288de36c472ea5ce9548bffa0c703ee623','core-only-regression-antenna-extraction-44550131521',14542543395,'7eb3ec71a5435393eb626b14d2a3c190a21a935e169730413fd5662d11ca44f1')
        assert b['status']=='NOMINAL_RC_AND_NATIVE_SPEF_STA_EXECUTED_REQUIRES_COVERAGE_AND_SIGNOFF'
        bind=b['fresh_view_binding']
        assert bind['odb_sha256']=='bd28f784aa3cad49b72197de70c394727ab0e72608610febd4c4e16dfc4a28bc'
        assert bind['netlist_sha256']==b['outputs']['routed.v']=='1e49dbd06ce9478c5c4cdd44ac891f1f9698dfea76bd63a3f564f8bb79023be6'
        baseline=z.read('routed.v').decode();inventory=b['cumulative_antenna_inventory'];assert len(inventory)==1410
        before=copy.deepcopy(inventory)
        baseline_check=check_added_antennas(baseline,inventory)
        assert baseline_check['new_diodes_exported']==1410
        assert not baseline_check['missing_diodes'] and not baseline_check['duplicate_diodes'] and not baseline_check['signal_connection_mismatches']
        del z
        z,p,pm=verified(44555127293,'bb26e933787c729110c6fa16167bfa44a393e2dc','core-only-loadsplit-prep-44555127293',14544652590,'2d0eebbd815fa2411933ddddadc8c5a8eeeed8c15793d7424f6ea74be5d65daf')
        assert p['status']=='TWENTY_ONE_LOAD_SPLIT_BUFFERS_PREPARED_REQUIRES_ROUTING_ANTENNA_AND_FRESH_RC'
        assert p['source_admission']['odb_sha256']==bind['odb_sha256']
        assert p['outputs']['candidate-partially-routed.odb']=='3c55f2e88aff518b5483e10760b2d75042856d2b77616526bc731cb2083fd7c3'
        assert p['outputs']['diode-reconnection-audit.json']=='0a351518d262c04f39a2c7e869d0ce6c246755d9b2d34990e2cda321f3451632'
        audit=json.loads(z.read('diode-reconnection-audit.json'))
        updated,moved=rebind_inventory(inventory,audit)
        assert inventory==before and len(updated)==1410 and len(moved)==44
        changed={name for name in inventory if inventory[name]!=updated[name]}
        assert changed==set(EXPECTED)
        try:verify_moved_export(baseline,moved)
        except AssertionError:stale_rejected=True
        else:raise AssertionError('Old baseline export accepted as load-split export')
        report.update(status='ACTUAL_PREPARATION_AND_BASELINE_DIODE_MAP_VERIFIED_REQUIRES_NEW_ROUTED_EXPORT',baseline_artifact=bm,preparation_artifact=pm,baseline_export=baseline_check,moved_diodes=len(moved),inventory_count=len(updated),all_moved_diodes_present_in_inventory=True,input_unchanged=True,stale_baseline_export_rejected=stale_rejected,changed_cells=sorted(changed),source_odb_sha256=bind['odb_sha256'],candidate_odb_sha256=p['outputs']['candidate-partially-routed.odb'])
        (out/'rebound-inventory.json').write_text(json.dumps(updated,indent=2)+'\n')
        (out/'moved-diodes.json').write_text(json.dumps(moved,indent=2)+'\n')
        print(json.dumps({k:report[k] for k in ['status','moved_diodes','inventory_count','input_unchanged','stale_baseline_export_rejected']},indent=2))
    except BaseException as e:
        report.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
    finally:
        report['outputs']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='result.json'}
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
