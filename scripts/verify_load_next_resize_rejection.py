#!/usr/bin/env python3
"""Bind the narrowly expanded route set to the rejected predecessor evidence."""
import json,hashlib,subprocess
from cloud_core_only_postgrt import archive
def verify_rejection(out):
 run=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/44507049713']))
 assert run['head_sha']=='b754ac1dfec7a00a74586c857a5a0041e0eee14f' and run['run_attempt']==1
 assert run['status']=='completed' and run['conclusion']=='failure'
 z,m=archive(run,'core-only-load-next-resize-route-44507049713')
 assert m['id']==14524137030 and m['digest']=='sha256:b8487902a4f95fe13a022a1dc33bc93a348ee0b6e1f32218d4af24fba45798fd'
 r=json.loads(z.read('result.json'))
 assert r['source_head']==run['head_sha'] and not r['accepted'] and r['status']=='FAIL_OR_INCOMPLETE'
 assert set(n for n in z.namelist() if not n.endswith('/') and n!='result.json')==set(r['outputs'])
 for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 assert len(r['outputs'])==45
 assert r['routed_odb_sha256']=='a7b345166a4fea983978e150fc0a09c1e7e0f4f8045c8ed09f331b48adac52d0'
 g=json.loads(z.read('geometry/physical-route-audit.json'))
 assert g['source_odb_sha256']==r['routed_odb_sha256'] and g['source_unchanged']
 assert g['inter_net_contact_pairs']==32 and g['contact_counts']=={'Metal2:net2135:nssoc_sta_n_63198': 7, 'Metal2:net2135:nssoc_sta_n_62749': 3, 'Metal2:net2194:net2774': 3, 'Metal2:net5510:nssoc_sta_n_18115': 2, 'Metal2:net5513:nssoc_sta_n_28565': 3, 'Metal3:net2135:nssoc_sta_n_63198': 9, 'Metal4:net2135:nssoc_sta_n_63198': 5}
 assert not g['signal_nets_with_disconnected_geometry'] and not g['unwired_multi_terminal_nets'] and not g['terminals_without_geometry']
 assert r['metrics']['route__drc_errors']==0 and r['metrics']['antenna__violating__nets']==1 and r['metrics']['antenna__violating__pins']==2
 assert r['detailed_identity']['instances']==106656 and r['detailed_identity']['exact_terminal_connections']
 p=r['detailed_preservation'];assert p['checked_unchanged_nets']==103080 and p['checked_clock_nets']==2113 and not p['changed_unselected_nets'] and not p['changed_clock_nets']
 (out/'rejected-predecessor-antenna.rpt').write_bytes(z.read('antenna.rpt'))
 (out/'rejected-predecessor-geometry.json').write_text(json.dumps(g,indent=2)+'\n')
 return dict(run=run['id'],head=run['head_sha'],artifact=m,verified_outputs=len(r['outputs']),contact_counts=g['contact_counts'],antenna_nets=1,production_admissible=False)
