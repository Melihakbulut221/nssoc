#!/usr/bin/env python3
import subprocess,json,hashlib,zipfile,io,os,time
from pathlib import Path
from check_antenna_netlist_export import check_added_antennas
OUT=Path('hw/soc/out/antenna-export-indexed');OUT.mkdir(parents=True,exist_ok=False)
def archive(run,head,aid,digest):
 base='repos/Melihakbulut221/nssoc/'
 r=json.loads(subprocess.check_output(['gh','api',base+'actions/runs/'+str(run)]));assert r['head_sha']==head and r['status']=='completed'and r['run_attempt']==1
 m=json.loads(subprocess.check_output(['gh','api',base+'actions/artifacts/'+str(aid)]));assert m['workflow_run']['id']==run and m['digest']=='sha256:'+digest
 raw=subprocess.check_output(['gh','api',base+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(raw).hexdigest()==digest
 return zipfile.ZipFile(io.BytesIO(raw))
z=archive(44384960280,'04c6c90beae74d1d50d3a5822cd36e9f89750125',14464719424,'463772cf27cf10a37480bceccf484bcc135de88adfab3376dcc49af6da9f536b');src=json.loads(z.read('result.json'))
for n,h in src['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h
assert src['returncode']==0 and src['netlist_sha256']=='012c7ed722b8ea78d78a22b2130ff323f5e27fb7ec773d99acd09d98ad69f337'
y=archive(44382891924,'508bb46d0366363d7e79a001ab8a68b230f4fd96',14464567635,'d5864cb7b9575155444b2ca063010f889c9203ab7bf1a8867b86dba19254c4b3');prefix='core-only-posteco-antenna-reaudit/';ir=json.loads(y.read(prefix+'result.json'))
for n,h in ir['outputs'].items():assert hashlib.sha256(y.read(prefix+n)).hexdigest()==h
cells=json.loads(y.read(prefix+'insertion-audit.json'))['new_cells'];started=time.monotonic();r=check_added_antennas(z.read('candidate.v').decode(),cells);r['elapsed_seconds']=time.monotonic()-started
r.update(source_head=os.environ['GITHUB_SHA'],accepted=False,netlist_sha256=src['netlist_sha256'],inventory_odb_sha256=ir['output_odb_sha256'],export_artifact=14464719424,inventory_artifact=14464567635)
(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
assert r['new_diodes_expected']==r['new_diodes_exported']==800 and not r['missing_diodes']and not r['duplicate_diodes']and not r['signal_connection_mismatches']
print(json.dumps(r,indent=2))
