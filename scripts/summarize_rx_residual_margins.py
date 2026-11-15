# SPDX-License-Identifier: Apache-2.0
"""Summarize authenticated all-corner residual input margins; no CAD mutation."""
import subprocess,json,io,zipfile,hashlib,re,os,math
from pathlib import Path
assert os.environ['GITHUB_ACTIONS']=='true'
p='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',p+s]))
run=api('actions/runs/43725515099')
assert run['conclusion']=='success' and run['run_attempt']==1 and run['head_sha']=='adfa6e152dcf8560ed6cc5839682376c8a9d0633'
a=api('actions/artifacts/14166341678');digest='cb5383123492ae6fc8baf6aefe55a86445d06f8deb6d53ea88acedf07021de37'
assert a['workflow_run']['id']==run['id'] and a['digest']=='sha256:'+digest and not a['expired']
b=subprocess.check_output(['gh','api',p+'actions/artifacts/14166341678/zip'],timeout=600)
assert hashlib.sha256(b).hexdigest()==digest
z=zipfile.ZipFile(io.BytesIO(b));r=json.loads(z.read('result.json'))
assert r['sources_unchanged'] and r['returncode']==0 and r['source_odb_sha256']=='441ff0490eb3239ba9011e1b5e08e99f7f8304a600e30ec38dc4806d10525e3e'
idx={t['name']:i for i,t in enumerate(r['targets'])};rows=[]
for path in r['paths']:
 if path['mode']!='min' or path['slack_ns']>=0:continue
 row=dict(path=path,margins=[])
 for pin,master in path['pins']:
  vals={};reports={}
  for mode in ['max','min']:
   values=[]
   for c in ['1-nssoc-ackbranchslow','2-nssoc-ackbranchtypical','3-nssoc-ackbranchfast']:
    n=f'run/{c}/branch-{idx[pin]}-{mode}.rpt';data=z.read(n)
    assert hashlib.sha256(data).hexdigest()==r['outputs'][n]
    text=data.decode();assert 'NSSOC_TARGET '+pin in text
    v=list(map(float,re.findall(r'([-+\d.eE]+)\s+slack \(',text)))
    assert v and all(math.isfinite(x)for x in v)
    values.extend(v);reports[n]=dict(sha256=r['outputs'][n],slacks_ns=v)
   vals[mode]=min(values)
  row['margins'].append(dict(pin=pin,master=master,worst_setup_ns=vals['max'],worst_hold_ns=vals['min'],reports=reports))
 rows.append(row)
assert len(rows)==7
out=Path('residual-margin-summary');out.mkdir()
result=dict(status='PASS_AUTHENTICATED_BRANCH_MARGIN_SUMMARY',accepted=False,full_phy_accepted=False,source_run=run['id'],source_head=run['head_sha'],artifact_id=a['id'],artifact_sha256=digest,source_odb_sha256=r['source_odb_sha256'],paths=rows)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
for row in rows:
 print(row['path']['end'],[(x['pin'],x['worst_setup_ns'],x['worst_hold_ns'])for x in row['margins']])
