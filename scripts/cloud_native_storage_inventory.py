#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read-only hosted storage inventory for the full native PLL capture."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-native-storage-inventory'
def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],read_only_inventory=True,
        native_activation=False,full_capacity_proven=False,full_phy_accepted=False,commands=[],paths={})
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        for label,cmd in [('filesystems',['df','-B1','-T']),
          ('block-devices',['lsblk','--bytes','--json','--output','NAME,PATH,TYPE,SIZE,FSTYPE,MOUNTPOINTS,RO,MODEL']),
          ('mounts',['findmnt','--json']),('swap',['swapon','--show','--bytes'])]:
            p=subprocess.run(cmd,capture_output=True,text=True,timeout=60)
            target=OUT/(label+'.log');target.write_text(p.stdout+p.stderr)
            r['commands'].append(dict(label=label,command=cmd,returncode=p.returncode,sha256=sha(target)))
            assert p.returncode==0,(label,p.stderr)
            if label=='block-devices':r['block_devices']=json.loads(p.stdout)
        for name in [str(ROOT),os.environ['RUNNER_TEMP'],'/','/mnt','/mnt/resource','/tmp','/home/runner']:
            p=Path(name)
            if not p.exists():r['paths'][name]=dict(exists=False);continue
            stat=p.stat();usage=shutil.disk_usage(p)
            r['paths'][name]=dict(exists=True,device_id=stat.st_dev,mountpoint=os.path.ismount(p),
                total_bytes=usage.total,used_bytes=usage.used,free_bytes=usage.free)
        for name in ('partitions','mounts','swaps'):
            (OUT/('proc-'+name+'.txt')).write_bytes((Path('/proc')/name).read_bytes())
        root_device=ROOT.stat().st_dev
        r['different_device_paths']=[name for name,row in r['paths'].items()if row.get('exists')and row['device_id']!=root_device]
        r['uncompressed_full_wave_lower_bound_bytes']=130713600000
        r.update(status='COMPLETE_READ_ONLY_HOSTED_STORAGE_INVENTORY_NOT_CAPACITY_PROOF',
            no_cleanup_format_mount_or_native_process_started=True,
            next_action='Assess any independent existing storage before changing checkpoint allocation. Do not sum paths sharing device_id or count unallocated/block/raw capacity as usable; prove any proposed layout on a disposable hosted runner first.')
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
