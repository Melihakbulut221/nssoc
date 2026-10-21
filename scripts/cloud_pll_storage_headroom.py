#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Measure extra disposable hosted capacity without restoring any native capsule."""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
import cloud_pll845_preallocated_storage as allocation
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll-storage-headroom'
FIXED=[
 '/usr/local/lib/android','/usr/share/dotnet','/opt/ghc',
 '/usr/share/swift','/usr/local/swift','/opt/swift',
 '/usr/lib/jvm','/opt/microsoft/powershell','/usr/local/share/powershell',
 '/opt/google/chrome','/opt/microsoft/msedge','/usr/local/share/chromium',
 '/usr/local/share/boost','/usr/local/share/vcpkg',
 '/home/runner/.rustup','/home/runner/.cargo','/home/runner/.cache',
 '/root/.rustup','/root/.cargo','/root/.cache',
 '/usr/local/julia','/opt/az']
def sha(path):
    with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def entry_exists(path):
    # /root cache entries are intentionally inspected with the same privilege
    # used for their bounded disposable-runner cleanup.
    code='import os,sys;sys.exit(0 if os.path.lexists(sys.argv[1]) else 1)'
    check=subprocess.run(['sudo','python3','-c',code,str(path)],capture_output=True,text=True)
    assert check.returncode in (0,1),check.stderr
    return check.returncode==0
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert str(ROOT)=='/home/runner/work/nssoc/nssoc'and not os.path.ismount(ROOT)
    assert not list(ROOT.glob('cloud-pll845-native-acquisition*'))
    OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_activation=False,full_capacity_proven=False,acquisition_accepted=False,full_phy_accepted=False,commands=[],removed=[])
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(name,args):
        p=subprocess.run(args,capture_output=True,text=True,timeout=600)
        text=p.stdout+p.stderr;(OUT/(name+'.log')).write_text(text)
        r['commands'].append(dict(name=name,args=args,returncode=p.returncode,log_sha256=sha(OUT/(name+'.log'))));save()
        assert p.returncode==0,(name,text[-2000:])
        return p.stdout
    save()
    try:
        assert not run('empty-docker',['docker','ps','-aq']).strip()
        protected={}
        for name in ('python3','bash','curl','gh','docker','gcc','make','tar','gzip','ldd','node'):
            path=shutil.which(name)
            if path:
                resolved=Path(path).resolve();protected[str(resolved)]=sha(resolved)
        protected[str(Path(sys.executable).resolve())]=sha(Path(sys.executable).resolve())
        r['protected_executables']=protected
        r['before']=dict(zip(('total','used','free'),shutil.disk_usage(ROOT)))
        r['filesystem']=run('filesystem-before',['df','-B1','-T',str(ROOT)])
        r['top_level_bytes']=run('top-level-bytes',['sudo','du','-xB1','--max-depth=1','/opt','/usr/local','/home/runner','/usr/share'])
        candidates=[Path(p)for p in FIXED]
        cache=Path('/opt/hostedtoolcache')
        if cache.is_dir():
            for p in cache.iterdir():
                if p.name=='Python'and p.is_dir():
                    candidates.extend(p.iterdir())
                else:candidates.append(p)
        # Only named unused LLVM SDK roots, never general /usr/lib.
        candidates.extend(p for p in Path('/usr/lib').glob('llvm-*')if p.name.removeprefix('llvm-').isdigit())
        seen=set()
        for p in candidates:
            assert p.is_absolute()and str(p)not in ('/','/usr','/opt','/home/runner',str(ROOT))
            if not entry_exists(p):continue
            if str(p)in seen:continue
            seen.add(str(p))
            if any(Path(q).is_relative_to(p)for q in protected):
                r.setdefault('retained_protected',[]).append(str(p));continue
            assert not ROOT.is_relative_to(p)and not p.is_relative_to(ROOT)
            before=shutil.disk_usage(ROOT).free
            measured=run('size-'+str(len(r['removed'])),['sudo','du','-sxB1',str(p)]).strip()
            run('remove-'+str(len(r['removed'])),['sudo','rm','-rf','--',str(p)])
            assert not entry_exists(p)
            r['removed'].append(dict(path=str(p),measured_bytes=measured,free_gain_bytes=shutil.disk_usage(ROOT).free-before));save()
        run('apt-cache-clean',['sudo','apt-get','clean'])
        run('unused-docker-images',['docker','image','prune','-af'])
        assert all(Path(p).is_file()and sha(p)==digest for p,digest in protected.items())
        for label,args in [('python',[sys.executable,'--version']),('gh',['gh','--version']),('docker',['docker','info','--format','{{json .}}']),('compiler',['gcc','--version']),('make',['make','--version']),('curl',['curl','--version'])]:
            run('post-'+label,args)
        assert not run('empty-docker-after',['docker','ps','-aq']).strip()
        r['after']=dict(zip(('total','used','free'),shutil.disk_usage(ROOT)))
        r['free_gain_bytes']=r['after']['free']-r['before']['free']
        r['original_allocation_controls']=allocation.controls()
        image=allocation.choose_image(r['after']['free'])
        r['original_reserves_retained']=dict(possible_image_bytes=image,host_margin_bytes=allocation.HOST_ALLOCATION_MARGIN,native_reserve_bytes=allocation.NATIVE_CHECKPOINT_RESERVE,host_checkpoint_reserve_bytes=allocation.HOST_CHECKPOINT_RESERVE)
        # Lower bound, not a capacity claim:1us/.3125ps plus startup rows.
        minimum_rows=3200000
        r['full_capture_lower_bound']=dict(columns=5106,minimum_rows=minimum_rows,uncompressed_payload_bytes=minimum_rows*5106*8,header_and_startup_and_runtime_and_filesystem_overhead_excluded=True)
        r['uncompressed_payload_space_after_native_reserve_bytes']=image-allocation.NATIVE_CHECKPOINT_RESERVE
        r['uncompressed_full_lower_bound_fits_before_other_overheads']=r['uncompressed_payload_space_after_native_reserve_bytes']>=r['full_capture_lower_bound']['uncompressed_payload_bytes']
        r.update(status='MEASURED_EXTRA_DISPOSABLE_HOSTED_CAPACITY_PROTECTED_EXECUTABLES_UNCHANGED_NOT_NATIVE_PROOF',protected_executables_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
