#!/usr/bin/env python3
"""Bind the 720-diode map to real archived preparation and baseline export evidence."""
import os,json,hashlib,copy
from pathlib import Path
from cloud_core_only_postgrt import completed,archive
from rebind_signal_fanout_antenna_inventory import EXPECTED,OUTSIDE_CUMULATIVE,rebind_inventory,verify_moved_export
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
    out=Path('hw/soc/out/signal-fanout-diode-evidence');out.mkdir(parents=True,exist_ok=False)
    report=dict(source_head=os.environ['GITHUB_SHA'],status='VERIFYING',accepted=False,final_timing_complete=False)
    try:
        z,b,bm=verified(44567580014,'2b14595809d4575f10b383dda6e5be77ca8b4da2','core-only-loadsplit-clean-extraction-44567580014',14554237236,'77286a8405133cc945d5b8100925d6d13ebe18227737f3e3d67eb4366d5cf868')
        assert b['status']=='NOMINAL_RC_AND_NATIVE_SPEF_STA_EXECUTED_REQUIRES_COVERAGE_AND_SIGNOFF'
        bind=b['fresh_view_binding']
        assert bind['odb_sha256']=='12a48d839091ba5c4fea76a193fea75fcc5f2f38621b1df809cb3df5bd51e458'
        assert bind['netlist_sha256']==b['outputs']['routed.v']=='ab0c1367a61b3226396ee082768469ea2eddddf5772455cf1ecb38bff50ff1ca'
        baseline=z.read('routed.v').decode();inventory=b['cumulative_antenna_inventory'];assert len(inventory)==1410
        before=copy.deepcopy(inventory)
        baseline_check=check_added_antennas(baseline,inventory)
        assert baseline_check['new_diodes_exported']==1410
        assert not baseline_check['missing_diodes'] and not baseline_check['duplicate_diodes'] and not baseline_check['signal_connection_mismatches']
        del z
        z,p,pm=verified(44572321564,'d2890354ff2ba58a2c1f64a23c0d19bd039d5d2c','core-only-signal-fanout-prep-44572321564',14555371112,'70cd6cd78803faf97e50979f0c04a738616121c1a9a9b7338408f18de949bbaf')
        assert p['status']=='SIGNAL_FANOUT_BUFFERS_PREPARED_REQUIRES_ROUTING_ANTENNA_AND_FRESH_RC'
        assert p['source_admission']['odb_sha256']==bind['odb_sha256']
        assert p['outputs']['candidate-partially-routed.odb']=='2338707a927b80c95dbb087a332ea42f32e9c514c737bc25ae344d4e4da7a40c'
        assert p['outputs']['diode-reconnection-audit.json']=='ff26d38a52385594019eb1dffe44906cb99bc12d86d158cfc4786ba2d798a954'
        audit=json.loads(z.read('diode-reconnection-audit.json'))
        updated,moved=rebind_inventory(inventory,audit,baseline)
        assert inventory==before and len(updated)==1410 and len(moved)==720
        changed={name for name in inventory if inventory[name]!=updated[name]}
        assert changed==set(EXPECTED)-set(OUTSIDE_CUMULATIVE) and len(changed)==698
        try:verify_moved_export(baseline,moved)
        except AssertionError:stale_rejected=True
        else:raise AssertionError('Old baseline export accepted as signal-fanout export')
        report.update(status='ACTUAL_PREPARATION_AND_BASELINE_DIODE_MAP_VERIFIED_REQUIRES_NEW_ROUTED_EXPORT',baseline_artifact=bm,preparation_artifact=pm,baseline_export=baseline_check,moved_diodes=len(moved),inventory_count=len(updated),moved_diodes_in_cumulative=698,moved_diodes_outside_cumulative=22,all_moved_diodes_verified_in_baseline=True,input_unchanged=True,stale_baseline_export_rejected=stale_rejected,changed_cells=sorted(changed),source_odb_sha256=bind['odb_sha256'],candidate_odb_sha256=p['outputs']['candidate-partially-routed.odb'])
        (out/'rebound-inventory.json').write_text(json.dumps(updated,indent=2)+'\n')
        (out/'moved-diodes.json').write_text(json.dumps(moved,indent=2)+'\n')
        print(json.dumps({k:report[k] for k in ['status','moved_diodes','inventory_count','input_unchanged','stale_baseline_export_rejected']},indent=2))
    except BaseException as e:
        report.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
    finally:
        report['outputs']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file() and p.name!='result.json'}
        (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
