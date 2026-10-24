#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inspect immutable failed DRC marker coordinates in the cloud."""
import hashlib,io,json,os,subprocess,tarfile,xml.etree.ElementTree as ET
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
R='repos/Melihakbulut221/nssoc/'
def sha(b):return hashlib.sha256(b).hexdigest()
def api(p,binary=False):
 c=['gh','api',R+p]
 if binary:c+=['-H','Accept: application/octet-stream']
 b=subprocess.check_output(c)
 return b if binary else json.loads(b)
def asset(n,h):
 b=api('releases/assets/'+str(n),True);assert sha(b)==h;return b
summary=asset(670590754,'9d343fdc0f5d113c745fa360db012590d30f7b59310d819340b82071829d6f98')
parts=asset(670590821,'353180029d1f8c4682cfa4f04115c55e5c0e9d303a66db5d4a5436604ca2d1d0')
r=json.loads(summary);m=json.loads(parts)
assert r['source_head']=='97528f74aca37fd1876bef6cf1a5683911a2c371'
assert r['physical']['steps']['drc']['measurement']['categories']=={"'TM1.a'":120}
rel=api('releases/tags/cloud-results-40033603461-1-cdr-active-levelshift-v50-physical')
by={a['name']:a for a in rel['assets']};chunks=[]
for i,p in enumerate(m['parts']):
 assert p['index']==i
 b=asset(by[p['name']]['id'],p['sha256']);assert len(b)==p['bytes'];chunks.append(b)
packed=b''.join(chunks);assert len(packed)==m['bytes'] and sha(packed)==m['sha256']
with tarfile.open(fileobj=io.BytesIO(packed),mode='r:gz')as tar:
 matches=[x for x in tar.getmembers()if x.name.endswith('/physical/drc/drc.lyrdb')]
 assert len(matches)==1
 xml=tar.extractfile(matches[0]).read()
assert sha(xml)==r['physical']['steps']['drc']['measurement']['report_sha256']
root=ET.fromstring(xml)
items=[dict(category=x.findtext('category'),cell=x.findtext('cell'),values=[v.text for v in x.findall('./values/value')])for x in root.findall('./items/item')]
assert len(items)==120
out=Path('cloud-cdr-v50-drc-marker-inspection');out.mkdir()
report=dict(status='PASS_INSPECTION_OF_120_REAL_TM1_WIDTH_FAILURES_NOT_A_FIX',source_head=os.environ['GITHUB_SHA'],source_run=40033603461,source_summary_sha256=sha(summary),source_parts_sha256=sha(parts),native_report_sha256=sha(xml),items=items,full_phy_accepted=False)
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],items=items[:16]),indent=2))
