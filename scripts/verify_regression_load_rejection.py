#!/usr/bin/env python3
"""Bind the narrowly expanded route set to the rejected predecessor evidence."""
import json,hashlib,subprocess
from cloud_core_only_postgrt import archive
def verify_rejection(out):
 run=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/44533830219']))
 assert run['head_sha']=='c5a7af65d4771c54314edc1d8d761cc6a7ad3b50' and run['run_attempt']==1
 assert run['status']=='completed' and run['conclusion']=='failure'
 z,m=archive(run,'core-only-regression-load-isolation-route-44533830219')
 assert m['id']==14535888831 and m['digest']=='sha256:a9a11bbbc74e1c58095f5eeeef7b73299e42d2b483760ed67564b8111f9a5dd5'
 r=json.loads(z.read('result.json'))
 assert r['source_head']==run['head_sha'] and not r['accepted'] and r['status']=='FAIL_OR_INCOMPLETE'
 assert set(n for n in z.namelist() if not n.endswith('/') and n!='result.json')==set(r['outputs'])
 for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 assert len(r['outputs'])==45
 assert r['routed_odb_sha256']=='284137acb3478477515652b8627036a1674eb91694fac3ce10257c46000c1bc7'
 g=json.loads(z.read('geometry/physical-route-audit.json'))
 assert g['source_odb_sha256']==r['routed_odb_sha256'] and g['source_unchanged']
 assert g['inter_net_contact_pairs']==17 and g['contact_counts']=={'Metal2:nssoc_sta_n_62797:nssoc_sta_n_64543':2,'Metal2:nssoc_regiso_5_net:nssoc_sta_n_62886':3,'Metal2:nssoc_sta_n_18115:nssoc_sta_n_60783':7,'Metal3:nssoc_sta_n_18115:nssoc_sta_n_60783':5}
 assert not g['signal_nets_with_disconnected_geometry'] and not g['unwired_multi_terminal_nets'] and not g['terminals_without_geometry']
 assert r['metrics']['route__drc_errors']==0 and r['metrics']['antenna__violating__nets']==1 and r['metrics']['antenna__violating__pins']==1
 assert r['detailed_identity']['instances']==106670 and r['detailed_identity']['exact_terminal_connections']
 p=r['detailed_preservation'];assert p['checked_unchanged_nets']==103083 and p['checked_clock_nets']==2113 and not p['changed_unselected_nets'] and not p['changed_clock_nets']
 (out/'rejected-predecessor-antenna.rpt').write_bytes(z.read('antenna.rpt'))
 (out/'rejected-predecessor-geometry.json').write_text(json.dumps(g,indent=2)+'\n')
 return dict(run=run['id'],head=run['head_sha'],artifact=m,verified_outputs=len(r['outputs']),contact_counts=g['contact_counts'],antenna_nets=1,production_admissible=False)
