#!/usr/bin/env python3
"""Bind the narrowly expanded route set to the rejected predecessor evidence."""
import json,hashlib,subprocess
from cloud_core_only_postgrt import archive
def verify_rejection(out):
 run=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/44485580230']))
 assert run['head_sha']=='4848d0affb0ef20f2bbe3a2c865f749d1cc3ec64' and run['run_attempt']==1
 assert run['status']=='completed' and run['conclusion']=='failure'
 z,m=archive(run,'core-only-spacing-load-isolation-route-44485580230')
 assert m['id']==14511783320 and m['digest']=='sha256:2f8d185a83040cdcb943220c0ef7dfd99ecabaf28161e95dfacdab56605fc77b'
 r=json.loads(z.read('result.json'))
 assert r['source_head']==run['head_sha'] and not r['accepted'] and r['status']=='FAIL_OR_INCOMPLETE'
 assert set(n for n in z.namelist() if not n.endswith('/') and n!='result.json')==set(r['outputs'])
 for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 assert len(r['outputs'])==45
 assert r['routed_odb_sha256']=='36de40df4a47f8bc1e15c78a515efe75c07d96ec567059b9b02608c5353ff26e'
 g=json.loads(z.read('geometry/physical-route-audit.json'))
 assert g['source_odb_sha256']==r['routed_odb_sha256'] and g['source_unchanged']
 assert g['inter_net_contact_pairs']==3 and g['contact_counts']=={'Metal2:net5592:nssoc_sta_n_63283':3}
 assert not g['signal_nets_with_disconnected_geometry'] and not g['unwired_multi_terminal_nets'] and not g['terminals_without_geometry']
 assert r['metrics']['route__drc_errors']==0 and r['metrics']['antenna__violating__nets']==1 and r['metrics']['antenna__violating__pins']==1
 assert r['detailed_identity']['instances']==106654 and r['detailed_identity']['exact_terminal_connections']
 p=r['detailed_preservation'];assert p['checked_unchanged_nets']==103082 and p['checked_clock_nets']==2113 and not p['changed_unselected_nets'] and not p['changed_clock_nets']
 (out/'rejected-predecessor-antenna.rpt').write_bytes(z.read('antenna.rpt'))
 (out/'rejected-predecessor-geometry.json').write_text(json.dumps(g,indent=2)+'\n')
 return dict(run=run['id'],head=run['head_sha'],artifact=m,verified_outputs=len(r['outputs']),contact_counts=g['contact_counts'],antenna_nets=1,production_admissible=False)
