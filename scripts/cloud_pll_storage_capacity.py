#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Measure hosted storage before choosing production full-capture migration."""
import hashlib,json,os,pathlib,shutil,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll-storage-capacity'
GIB=1024**3
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    assert os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert str(ROOT)=='/home/runner/work/nssoc/nssoc'
    OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING_CAPACITY_OBSERVATION',source_head=os.environ['GITHUB_SHA'],full_capacity_proven=False,acquisition_accepted=False,full_phy_accepted=False,commands=[])
    def run(label,args):
        p=subprocess.run(args,capture_output=True,text=True,timeout=240)
        data=p.stdout+p.stderr
        (OUT/(label+'.log')).write_text(data)
        r['commands'].append(dict(label=label,args=args,returncode=p.returncode,sha256=hashlib.sha256(data.encode()).hexdigest()))
        assert p.returncode==0,(label,p.returncode)
        return p.stdout
    try:
        r['workspace_disk']=dict(zip(('total','used','free'),shutil.disk_usage(ROOT)))
        r['mounts']=json.loads(run('mounts',['findmnt','--json','-o','TARGET,SOURCE,FSTYPE,SIZE,AVAIL,OPTIONS']))
        r['block_devices']=json.loads(run('block-devices',['lsblk','--json','--bytes','-o','NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS']))
        r['filesystem_bytes']=run('filesystem-bytes',['df','-B1','-T'])
        r['docker']=json.loads(run('docker-info',['docker','info','--format','{{json .}}']))
        assert not run('empty-docker',['docker','ps','-aq']).strip()
        paths=['/opt/hostedtoolcache','/usr/local/lib/android','/usr/share/dotnet','/opt/ghc','/usr/local/share','/usr/lib','/usr/share','/var/lib/docker','/mnt']
        r['directory_bytes']={}
        for i,p in enumerate(paths):
            if pathlib.Path(p).exists():
                r['directory_bytes'][p]=run('directory-'+str(i),['sudo','du','-sxB1',p]).strip()
        r['required_runtime']=dict(python=sys.executable,python_version=sys.version,node=shutil.which('node'),gh=shutil.which('gh'),docker=shutil.which('docker'))
        r['bounded_native_proof']=json.loads((ROOT/'docs/evidence/native-btrfs-complete-bounded-proof-20261021.json').read_text())
        assert r['bounded_native_proof']['run']==39544302605
        assert r['bounded_native_proof']['positive']['all_native_times_and_all34_probes_bit_exact']
        r['full_current_raw_bytes']=94755872699
        r['minimum_native_checkpoint_reserve_bytes']=12*GIB
        r['proposed_outside_backing_reserve_bytes']=4*GIB
        r['uncompressed_remaining_after_reserves_bytes']=r['workspace_disk']['free']-r['full_current_raw_bytes']-16*GIB
        r['status']='MEASURED_HOSTED_CAPACITY_NOT_FULL_RAW_COMPRESSION_OR_NATIVE_CONTINUATION_PROOF'
        r['scope']='Read-only observation after the established disposable SDK cleanup. No mount, repartition, native restart, raw truncation, solver or gate change. Bounded4ns compression cannot predict full94.76GB capacity.'
    finally:
        r['outputs']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in OUT.iterdir()if p.is_file()}
        (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
        print(json.dumps({k:r.get(k)for k in ('status','workspace_disk','uncompressed_remaining_after_reserves_bytes','directory_bytes')}))
if __name__=='__main__':main()
