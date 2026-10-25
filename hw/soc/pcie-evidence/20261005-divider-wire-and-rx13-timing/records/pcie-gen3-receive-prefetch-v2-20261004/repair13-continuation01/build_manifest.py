# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Freeze exact future continuation inputs and current existing route identity."""
from pathlib import Path
import datetime,hashlib,json
C=Path(__file__).resolve().parent;B=C.parent;R=B.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
old=json.loads((B/'repair12-continuation01/manifest.json').read_text());m=json.loads(json.dumps(old).replace('repair12','repair13').replace('repair-12','repair-13').replace('RX12','RX13'))
active=json.loads((B/'repair13-source/active-drt.json').read_text());m['route_owner']=active['owner'];m['route_native']=active['native'];m['route_inputs']=active['inputs'];m['boot_id']=active['boot_id'];m['utc']=datetime.datetime.now(datetime.UTC).isoformat()
paths=[Path(p) for p in m['inputs']]+[B/'repair13-source/source-only-peer-root.json',B/'repair13-source/proof-source-only-peer-root.json',B/'repair13-source/route-rc-source-only-peer-root.json',C/'lifecycle-controls.json',C/'check_lifecycle_boundaries.py']
m['inputs']={str(p):pin(p) for p in paths}
assert m['inputs']=={p:pin(p) for p in m['inputs']}
for p,h in m['route_inputs'].items():assert pin(p)==h
for identity in [m['route_owner'],m['route_native']]:
 f=(Path('/proc')/str(identity['pid'])/'stat').read_text().rsplit(') ',1)[1].split();assert f[19]==identity['start_ticks'] and f[0]!='Z'
p=C/'manifest.json';assert not p.exists();p.write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(dict(path=str(p),**pin(p),inputs=len(m['inputs']))))
