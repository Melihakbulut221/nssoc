# SPDX-License-Identifier: Apache-2.0
"""Read existing authenticated native reports; never rerun or modify placement."""
import os,subprocess,json,hashlib,zipfile,re,traceback,collections
from pathlib import Path
P='repos/Melihakbulut221/nssoc/'
OUT=Path('reset-critical-audit');OUT.mkdir()
r=dict(status='RUNNING',accepted=False,full_phy_accepted=False)
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
try:
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 run=api('actions/runs/43715930015');assert run['head_sha']=='797c06051cde73076629381ed79fe8d0c5e6452f' and run['conclusion']=='success' and run['run_attempt']==1
 meta=api('actions/artifacts/14162873930');digest='e97aedd4ac08772ae08e9648dd0915f2e09cf78b90c59d6961d04e26a7003964'
 assert meta['workflow_run']['id']==run['id'] and meta['workflow_run']['head_sha']==run['head_sha'] and meta['digest']=='sha256:'+digest and not meta['expired']
 archive=Path('reset-existing-derived.zip')
 with archive.open('xb')as f:subprocess.run(['gh','api',P+'actions/artifacts/14162873930/zip'],stdout=f,check=True,timeout=600)
 with archive.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==digest
 with zipfile.ZipFile(archive)as z:
  source=json.loads(z.read('result.json'));assert source['candidate_odb_sha256']=='0451f211acbac6b2b29a14b9b19d4b5beb1eb23c96cbb10d4a76c9f4fdf15cb7' and source['sources_unchanged'] and source['returncode']==0
  file='run/2-nssoc-sizedslow/max.rpt';raw=z.read(file);h=hashlib.sha256(raw).hexdigest();assert h==source['outputs'][file]
  blocks=raw.decode().split('Startpoint:')[1:];rows=[];counts=collections.Counter()
  for part in blocks:
   if 'slack (VIOLATED)'not in part:continue
   lines=part.splitlines();start=lines[0].strip().split(' (',1)[0];end=re.search(r'(?m)^Endpoint: (.+)',part)[1].strip().split(' (',1)[0]
   indexes=[i for i,l in enumerate(lines)if start+'/Q ('in l or start+'/QN ('in l or start+'/Q_N ('in l]
   if len(indexes)!=1:continue
   i=indexes[0];launch_net=next((l.strip().rsplit(' (net)',1)[0]for l in lines[i+1:]if ' (net)'in l),'')
   counts[launch_net]+=1;chain=[]
   for line in lines[i+1:]:
    if 'data arrival time'in line:break
    m=re.search(r'([^ ]+)/(A|X) \(sg13g2_buf_(1|2|4|8|16)\)',line)
    if m:
     if m[2]=='X':chain.append(dict(instance=m[1],master='sg13g2_buf_'+m[3],report_row=line.strip()))
    elif '(sg13g2_'in line:break
   slack=float(re.search(r'([-+0-9.eE]+)\s+slack \(VIOLATED\)',part)[1])
   rows.append(dict(start=start,end=end,launch_net=launch_net,slack_ns=slack,initial_buffer_chain=chain))
  r.update(status='EXISTING_NATIVE_SETUP_PATH_AUDIT_COMPLETE_NOT_REPAIR',source_run=run['id'],source_head=run['head_sha'],source_odb_sha256=source['candidate_odb_sha256'],report_sha256=h,reported_violating_paths=len(rows),launch_net_counts=dict(counts),worst_paths=rows[:20],worst_path_text='Startpoint:'+blocks[0],reset_paths=[x for x in rows if x['launch_net'].endswith('.rst_ni')][:100],sources_unchanged=True)
except BaseException:r.update(status='FAIL_OR_ERROR',traceback=traceback.format_exc());raise
finally:(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
