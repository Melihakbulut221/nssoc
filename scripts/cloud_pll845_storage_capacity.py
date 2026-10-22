#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Measure distinct hosted disks after existing bounded cleanup; no native activation."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll845-storage-capacity'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 assert not list(ROOT.glob('cloud-pll845-native-acquisition*'))
 OUT.mkdir(exist_ok=False)
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_activation=False,full_capture_accepted=False,full_phy_accepted=False,commands={},filesystems={})
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 try:
  for name,cmd in [('blocks',['lsblk','--json','--bytes','--output','NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS']),('mounts',['findmnt','--json']),('space',['df','-B1','-T']),('swap',['swapon','--show','--bytes']),('remaining',['sudo','du','-xB1','--max-depth=1','/var','/usr/lib','/usr/local/lib','/usr/local/share','/opt','/home/runner'])]:
   p=subprocess.run(cmd,capture_output=True,text=True,timeout=600)
   (OUT/(name+'.log')).write_text(p.stdout+p.stderr)
   r['commands'][name]=dict(returncode=p.returncode,sha256=hashlib.sha256((p.stdout+p.stderr).encode()).hexdigest())
   assert p.returncode==0,(name,p.stderr[-1000:])
  for p in [ROOT,Path(os.environ['RUNNER_TEMP']),Path('/mnt'),Path('/tmp'),Path('/dev/shm')]:
   if not p.exists():continue
   u=shutil.disk_usage(p)
   r['filesystems'][str(p)]=dict(device=p.stat().st_dev,total_bytes=u.total,used_bytes=u.used,free_bytes=u.free,mount=json.loads(subprocess.check_output(['findmnt','--json','-T',str(p)],text=True))['filesystems'])
  head=ROOT/'cloud-pll-storage-headroom'
  assert head.is_dir()
  shutil.copytree(head,OUT/'existing-headroom-proof')
  h=json.loads((head/'result.json').read_text())
  assert h['protected_executables_unchanged'] and not h['native_activation']
  r['existing_headroom']={k:h[k] for k in ['before','after','free_gain_bytes','original_reserves_retained','full_capture_lower_bound','uncompressed_full_lower_bound_fits_before_other_overheads']}
  r.update(status='MEASURED_DISTINCT_HOSTED_DISKS_AND_EXISTING_RECLAIM_NOT_NATIVE_CAPACITY_PROOF',scope='Inventory only. Separate device ids do not establish usable additional persistent capacity or CRIU compatibility. No capsule downloaded, no native process resumed, no simulation bytes omitted.')
 finally:save()
if __name__=='__main__':main()
