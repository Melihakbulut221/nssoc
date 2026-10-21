#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Inventory residual hosted storage after the already-qualified SDK cleanup."""
import json,os,shutil,subprocess
from pathlib import Path
from run_cloud_tx_layout_repair import sha
import cloud_pll845_preallocated_storage as allocation
import cloud_pll_storage_headroom as headroom
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-native-storage-residual'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 assert str(ROOT)=='/home/runner/work/nssoc/nssoc'
 assert not list(ROOT.glob('cloud-pll845-native-acquisition*'))
 OUT.mkdir(exist_ok=False)
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_activation=False,full_capacity_proven=False,
        full_phy_accepted=False,additional_cleanup_performed=False,commands=[])
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 def run(label,args):
  p=subprocess.run(args,capture_output=True,text=True,timeout=600)
  target=OUT/(label+'.log');target.write_text(p.stdout+p.stderr)
  r['commands'].append(dict(label=label,args=args,returncode=p.returncode,sha256=sha(target)));save()
  assert p.returncode==0,(label,p.stderr[-2000:])
  return p.stdout
 save()
 try:
  assert sha(ROOT/'scripts/cloud_pll_storage_headroom.py')=='2815e22ed2f81630f9a54ce81c848729883c2a604d79ac1f7b6ca51becc07aaa'
  assert sha(ROOT/'scripts/cloud_pll845_preallocated_storage.py')=='8750623b4f3cc77f168ed59a7a0c4b4a1baba8f9aed6cf2924af1e50f5249dda'
  headroom.main()
  shutil.copytree(headroom.OUT,OUT/'proven-headroom')
  prior=json.loads((headroom.OUT/'result.json').read_text())
  assert prior['protected_executables_unchanged']and not prior['native_activation']
  r['proven_cleanup']=dict(status=prior['status'],free_gain_bytes=prior['free_gain_bytes'],after=prior['after'])
  r['remaining_directories']={}
  for index,path in enumerate(['/','/usr','/usr/share','/usr/local','/usr/local/share','/var','/var/lib','/var/cache','/opt','/home/runner']):
   text=run('directory-'+str(index),['sudo','du','-xB1','--max-depth=1',path])
   rows=[]
   for line in text.splitlines():
    size,name=line.split('\t',1);rows.append(dict(path=name,bytes=int(size)))
   r['remaining_directories'][path]=sorted(rows,key=lambda x:x['bytes'],reverse=True);save()
  r['swap']=json.loads(run('swap',['swapon','--show','--bytes','--json']))
  r['root_files']=run('root-files',['sudo','find','/','-maxdepth','1','-type','f','-printf','%p %s bytes %b allocated512blocks\\n'])
  r['filesystems']=run('filesystems',['df','-B1','-T'])
  r['mount']=json.loads(run('mount',['findmnt','--json','-T',str(ROOT)]))
  v=os.statvfs(ROOT)
  r['statvfs']={k:getattr(v,k)for k in ('f_bsize','f_frsize','f_blocks','f_bfree','f_bavail')}
  r['disk']=dict(zip(('total','used','free'),shutil.disk_usage(ROOT)))
  image=allocation.choose_image(r['disk']['free']);minimum=130713600000
  r['unchanged_budget']=dict(possible_image_bytes=image,host_margin_bytes=allocation.HOST_ALLOCATION_MARGIN,
    native_reserve_bytes=allocation.NATIVE_CHECKPOINT_RESERVE,backing_reserve_bytes=allocation.HOST_CHECKPOINT_RESERVE,
    original_full_wave_uncompressed_lower_bound_bytes=minimum,
    minimum_extra_image_bytes_before_other_overheads=max(0,minimum+allocation.NATIVE_CHECKPOINT_RESERVE-image))
  assert all(Path(p).is_file()and sha(p)==h for p,h in prior['protected_executables'].items())
  assert not run('empty-docker',['docker','ps','-aq']).strip()
  r.update(status='MEASURED_RESIDUAL_HOSTED_STORAGE_AFTER_PROVEN_CLEANUP_NOT_NATIVE_CAPACITY_PROOF',
   protected_executables_unchanged=True,no_swap_disabling_no_new_cleanup_no_mount_or_format=True,
   scope='Directory totals overlap and must not be summed. This inventories remaining named candidates only; running native capsules and all allocation/gate contracts are unchanged.')
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
