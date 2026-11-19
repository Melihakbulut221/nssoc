#!/usr/bin/env python3
"""Bind the narrowly expanded route set to the rejected predecessor evidence."""
import json,hashlib,subprocess
from cloud_core_only_postgrt import archive
def verify_rejection(out):
 run=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/44556401044']))
 assert run['head_sha']=='686d42f911c06e6ade7f48f84c1fc6f83d591281' and run['run_attempt']==1
 assert run['status']=='completed' and run['conclusion']=='failure'
 z,m=archive(run,'core-only-loadsplit-route-44556401044')
 assert m['id']==14549202167 and m['digest']=='sha256:45267cc8bfce04694c3483f5be8afeeda2703ff9e6c77e98d3d99e0b344dfe41'
 r=json.loads(z.read('result.json'))
 assert r['source_head']==run['head_sha'] and not r['accepted'] and r['status']=='FAIL_OR_INCOMPLETE'
 assert set(n for n in z.namelist() if not n.endswith('/') and n!='result.json')==set(r['outputs'])
 for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 assert len(r['outputs'])==45
 assert r['routed_odb_sha256']=='8205dd3cf5d8fe085b84768dd8b5facb7e525246cc1c6c6b0ddff853c9899fa3'
 g=json.loads(z.read('geometry/physical-route-audit.json'))
 assert g['source_odb_sha256']==r['routed_odb_sha256'] and g['source_unchanged']
 assert g['inter_net_contact_pairs']==22 and g['contact_counts']=={'Metal2:nssoc_sta_n_62713:nssoc_sta_n_63701': 7, 'Metal2:nssoc_loadsplit_3_net:nssoc_sta_n_62607': 3, 'Metal2:net2514:nssoc_loadsplit_4_net': 3, 'Metal2:nssoc_sta_n_62661:nssoc_sta_n_62713': 3, 'Metal2:net4366:net4845': 3, 'Metal2:net5013:nssoc_sta_n_43169': 3}
 assert not g['signal_nets_with_disconnected_geometry'] and not g['unwired_multi_terminal_nets'] and not g['terminals_without_geometry']
 assert r['metrics']['route__drc_errors']==0 and r['metrics']['antenna__violating__nets']==0 and r['metrics']['antenna__violating__pins']==0
 assert r['detailed_identity']['instances']==106693 and r['detailed_identity']['exact_terminal_connections']
 p=r['detailed_preservation'];assert p['checked_unchanged_nets']==103086 and p['checked_clock_nets']==2113 and not p['changed_unselected_nets'] and not p['changed_clock_nets']
 (out/'rejected-predecessor-antenna.rpt').write_bytes(z.read('antenna.rpt'))
 (out/'rejected-predecessor-geometry.json').write_text(json.dumps(g,indent=2)+'\n')
 return dict(run=run['id'],head=run['head_sha'],artifact=m,verified_outputs=len(r['outputs']),contact_counts=g['contact_counts'],antenna_nets=0,production_admissible=False)
