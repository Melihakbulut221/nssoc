#!/usr/bin/env python3
"""Bind the narrowly expanded route set to the rejected predecessor evidence."""
import json,hashlib,subprocess
from cloud_core_only_postgrt import archive
def verify_rejection(out):
 run=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/44519671827']))
 assert run['head_sha']=='614a0a8ccab89228478e255e92df9db1a323b66e' and run['run_attempt']==1
 assert run['status']=='completed' and run['conclusion']=='failure'
 z,m=archive(run,'core-only-load-resize-antenna-route-44519671827')
 assert m['id']==14528307995 and m['digest']=='sha256:b724b253cb6f0b2731a90ad9d2596aaea9c0336ba1c492d53ffa7c290afbdc4b'
 r=json.loads(z.read('result.json'))
 assert r['source_head']==run['head_sha'] and not r['accepted'] and r['status']=='FAIL_OR_INCOMPLETE'
 assert set(n for n in z.namelist() if not n.endswith('/') and n!='result.json')==set(r['outputs'])
 for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 assert len(r['outputs'])==50
 assert r['routed_odb_sha256']=='4ea3593748463388944db28db453184655a2b9cb81c8a81972a2566358e004fb'
 g=json.loads(z.read('geometry/physical-route-audit.json'))
 assert g['source_odb_sha256']==r['routed_odb_sha256'] and g['source_unchanged']
 assert g['inter_net_contact_pairs']==8 and g['contact_counts']=={'Metal2:net912:nssoc_sta_n_60783':1,'Metal2:nssoc_sta_n_54415:nssoc_sta_n_60783':7}
 assert not g['signal_nets_with_disconnected_geometry'] and not g['unwired_multi_terminal_nets'] and not g['terminals_without_geometry']
 assert r['metrics']['route__drc_errors']==0 and r['metrics']['antenna__violating__nets']==0 and r['metrics']['antenna__violating__pins']==0
 assert r['detailed_identity']['instances']==106664 and r['detailed_identity']['exact_terminal_connections']
 p=r['detailed_preservation'];assert p['checked_unchanged_nets']==103087 and p['checked_clock_nets']==2113 and not p['changed_unselected_nets'] and not p['changed_clock_nets']
 (out/'rejected-predecessor-antenna.rpt').write_bytes(z.read('antenna.rpt'))
 (out/'rejected-predecessor-geometry.json').write_text(json.dumps(g,indent=2)+'\n')
 return dict(run=run['id'],head=run['head_sha'],artifact=m,verified_outputs=len(r['outputs']),contact_counts=g['contact_counts'],antenna_nets=0,production_admissible=False)
