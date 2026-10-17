#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Audit the preserved pre-reroute Ethernet candidate against actual pin geometry."""
import json,os,re,shutil,subprocess,sys
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-ethernet-preserved-route'
SUMMARY='43a8be4e7899e3e22d318230abfe2c6479655d3c237937e72fcaebe5fd6b80f7'
PARTS='2c2803ceded84f3c119d4051ee208f8e09623db3386691733cb098ec039dee8b'
CANDIDATE='49a805c66e904b534dd846bcca58070feaeac77dfe1427f7937e89427b0085e8'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],source_run=38978702458,final_timing_complete=False,full_serial_phy_complete=False,scope='Pre-reroute one-master candidate with every old signal dbWire retained. Native complete cell/net/PG/NDR/port census, exact wire equality, selected placed pins and LEF obstruction equality, independent all-signal connectivity/contacts. No timing/qualifiedRC/internal-cellGDS/LVS/PGcut/spacing or signoff claim.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,label,env):
        with (OUT/(label+'.log')).open('w')as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env)
        text=(OUT/(label+'.log')).read_text(errors='replace');print(label,text[-4000:],flush=True)
        assert p.returncode==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(label,p.returncode)
        return text
    save()
    try:
        selected=('candidate.odb','parent/routed.odb','geometry-proof.json')
        source,proof=reports.restore_report('ethernet-hold-eco',38978702458,SUMMARY,PARTS,OUT/'source',selected)
        assert source['source_head']=='deed6d20f745d4a5a18d420cc7184ca09d322893'and source['source_unchanged']and source['sized_cells']==1 and source['added_cells']==0
        assert source['outputs']['candidate.odb']==sha(OUT/'source/candidate.odb')==CANDIDATE
        assert source['logic']['status']=='PASS within scope'and source['inversion_control']=='REJECTED'
        # Shared read-only exporters use this basename. This copy contains the
        # preserved candidate bytes, never the rejected full reroute's ODB.
        shutil.copy2(OUT/'source/candidate.odb',OUT/'source/routed.odb');assert sha(OUT/'source/routed.odb')==CANDIDATE
        assert json.loads((OUT/'source/geometry-proof.json').read_text())==source['geometry']
        r.update(restoration=proof,candidate_odb_sha256=CANDIDATE,parent_odb_sha256=sha(OUT/'source/parent/routed.odb'),inherited_logic_proof=source['logic'],inherited_inversion_control=source['inversion_control'],full_reroute_accepted=False)
        methods=['audit_ethernet_preserved_route_native.py','audit_ethernet_delay_candidate_native.py','export_cloud_routed_shapes.py','check_cloud_routed_shapes.py','check_cloud_signal_contacts.py']
        r['method_hashes']={p:sha(ROOT/'scripts'/p)for p in methods};save()
        env=dict(os.environ,NSSOC_ETHERNET_CHILD_SHA=CANDIDATE,NSSOC_NINE_REVIEW_OUT=str(OUT),NSSOC_ROUTE_AUDIT_OUT=str(OUT),NSSOC_GEOMETRY_ADDED_BUFFERS='240')
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/audit_ethernet_preserved_route_native.py')],'native-preserved-route',env)
        r['native_census']=json.loads((OUT/'native-nine-audit.json').read_text());r['wire_census']=json.loads((OUT/'unchanged-wire-native.json').read_text());save()
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/export_cloud_routed_shapes.py')],'export',env)
        r['export']=json.loads((OUT/'export.json').read_text());assert r['export']['instances']==114031 and r['export']['nets']==114103 and r['export']['exported_nets']==113796
        run([sys.executable,str(ROOT/'scripts/check_cloud_routed_shapes.py'),'--directory',str(OUT)],'continuity',env)
        r['continuity']=json.loads((OUT/'continuity.json').read_text());save()
        run([sys.executable,str(ROOT/'scripts/check_cloud_signal_contacts.py'),'--directory',str(OUT)],'contacts',env)
        r['contacts']=json.loads((OUT/'signal-contacts.json').read_text())
        assert r['continuity']['checked']==r['contacts']['net_count']==113796
        assert r['continuity']['total_shapes']==r['contacts']['shape_count']==r['export']['shapes']
        tcl=OUT/'placement-antenna.tcl';tcl.write_text(f'read_db {{{OUT/"source/routed.odb"}}}\nset_thread_count 2\ncheck_placement -verbose\nset n [check_antennas -verbose -report_file {{{OUT/"antenna.rpt"}}}]\nputs "NSSOC_ANTENNA_RETURN $n"\n')
        text=run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(tcl)],'placement-antenna',env);r['antenna_report_lines']=[l for l in text.splitlines()if 'violation'in l.lower()]
        assert all(sha(OUT/'source'/p)==v['sha256']for p,v in proof['restore']['selected_files'].items())
        assert all(sha(ROOT/'scripts'/p)==v for p,v in r['method_hashes'].items())and sha(OUT/'source/routed.odb')==CANDIDATE
        r.update(status='COMPLETE_PRESERVED_ROUTE_NATIVE_GEOMETRY_SCREEN_REQUIRES_FRESH_RC_AND_ALL_ENDPOINTS',source_unchanged=True)
    except BaseException as error:
        r.update(status='FAIL_OR_ERROR',error=repr(error))
        for name,key in [('native-nine-audit.json','native_census'),('unchanged-wire-native.json','wire_census'),('continuity.json','continuity'),('signal-contacts.json','contacts')]:
            if (OUT/name).exists():r[key]=json.loads((OUT/name).read_text())
        raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
