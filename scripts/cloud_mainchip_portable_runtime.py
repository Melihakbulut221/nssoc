#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Recover exact loaded OpenROAD runtime and prove isolated saved-DB readback.

This is a prerequisite to process checkpointing, not a routing or timing pass.
All native work is restricted to hosted GitHub Actions runners.
"""
import argparse,hashlib,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-mainchip-portable-runtime'
APP_SHA='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
TUNABLES='glibc.cpu.hwcaps=-AVX512F,-AVX512CD,-AVX512BW,-AVX512DQ,-AVX512ER,-AVX512PF,-AVX512VL,-RTM'
PREFIX='run/1-openroad-detailedrouting/'
NIX=re.compile(rb'/nix/store/[a-z0-9]{32}-[A-Za-z0-9+._?=-]+')
def native_inventory():
    """Runs inside the pinned AppImage namespace, while the real ELF is alive."""
    base=OUT/'runtime-root';base.mkdir(exist_ok=False)
    command=[shutil.which('openroad'),'-exit','-no_init',str(OUT/'inventory.tcl')]
    assert command[0]
    ready=OUT/'inventory-ready';log=OUT/'native-inventory.log'
    env=dict(os.environ);env['GLIBC_TUNABLES']=TUNABLES
    with log.open('w')as stream:
        child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+180
            while not ready.exists():
                assert child.poll()is None,('native exited',child.returncode)
                assert time.monotonic()<deadline,'Native DB inventory readiness timeout'
                time.sleep(.25)
            proc=Path('/proc')/str(child.pid)
            exe=Path(os.readlink(proc/'exe'))
            assert exe.is_file() and exe.stat().st_size>1000000,'Did not reach actual native OpenROAD ELF'
            maps=(proc/'maps').read_text()
            entries={}
            for line in maps.splitlines():
                fields=line.split(maxsplit=5)
                if len(fields)==6 and fields[5].startswith('/nix/store/'):
                    assert not fields[5].endswith(' (deleted)')
                    p=Path(fields[5]);assert p.is_file();entries[str(p)]=sha(p)
            assert str(exe)in entries,'Actual ELF absent from memory mappings'
            rawenv=(proc/'environ').read_bytes().split(b'\0')
            allowed={'LD_LIBRARY_PATH','TCL_LIBRARY','TK_LIBRARY','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH','QT_QPA_PLATFORM','PYTHONPATH','PYTHONHOME'}
            actual_env={}
            for row in rawenv:
                if not row or b'='not in row:continue
                key,value=row.split(b'=',1);key=key.decode()
                if key in allowed:actual_env[key]=value.decode()
            # Starting from the actual ELF and mapped libraries avoids copying
            # the devshell wrapper (which references the entire CAD toolset).
            pending=set()
            missing=set();seen=set();manifest={};links={}
            def reference(raw):
                for match in NIX.findall(raw):
                    name=match.decode()
                    if Path(name).is_dir():
                        if name not in seen:pending.add(name)
                    else:missing.add(name)
            reference(str(exe).encode())
            for name in entries:reference(name.encode())
            for value in actual_env.values():reference(value.encode())
            shell=Path(shutil.which('sh')).resolve();assert shell.is_file()
            reference(str(shell).encode())
            while pending:
                source=Path(sorted(pending)[0]);pending.remove(str(source));seen.add(str(source))
                assert source.is_dir()and str(source).startswith('/nix/store/')
                target=base/str(source).lstrip('/')
                for folder,dirs,names in os.walk(source,followlinks=False):
                    folder=Path(folder);dest=base/str(folder).lstrip('/');dest.mkdir(parents=True,exist_ok=True)
                    for name in [*dirs,*names]:
                        p=folder/name;q=dest/name
                        if p.is_symlink():
                            value=os.readlink(p);reference(value.encode())
                            resolved=p.resolve(strict=False);reference(str(resolved).encode())
                            if not q.is_symlink():q.symlink_to(value)
                            links[str(p)]=value
                        elif p.is_file():
                            assert shutil.disk_usage(base).free>5*1024**3,'Insufficient cloud disk for exact runtime closure'
                            digest=hashlib.sha256();overlap=b''
                            with p.open('rb')as src,q.open('wb')as dst:
                                while True:
                                    block=src.read(1024**2)
                                    if not block:break
                                    digest.update(block);dst.write(block);reference(overlap+block);overlap=block[-1024:]
                            shutil.copystat(p,q);manifest[str(p)]=dict(sha256=digest.hexdigest(),bytes=p.stat().st_size)
                        elif not p.is_dir():raise AssertionError(('Unexpected runtime special file',str(p)))
            assert str(exe)in manifest and manifest[str(exe)]['sha256']==entries[str(exe)]
            for name,digest in entries.items():
                assert sha(base/name.lstrip('/'))==digest,('Mapped library was not reproduced',name)
            (base/'bin').mkdir(exist_ok=True);(base/'bin/sh').symlink_to(str(shell))
            (base/'tmp').mkdir(exist_ok=True);(base/'tmp').chmod(0o1777)
            (base/'etc').mkdir(exist_ok=True)
            (base/'etc/passwd').write_text('root:x:0:0:root:/tmp:/bin/sh\n')
            (base/'etc/group').write_text('root:x:0:\n')
            (base/'Dockerfile').write_text('FROM scratch\nCOPY . /\n')
            state=dict(status='CAPTURED_REAL_ELF_AND_RUNTIME_CLOSURE_REQUIRES_CONTAINER_READBACK',actual_elf=str(exe),actual_elf_sha256=sha(exe),actual_elf_bytes=exe.stat().st_size,
                mapped_libraries=entries,environment=actual_env,stores=sorted(seen),absent_reference_strings=sorted(missing),
                files=manifest,symlinks=links,shell=str(shell),runtime_file_count=len(manifest),runtime_bytes=sum(v['bytes']for v in manifest.values()),glibc_tunables=TUNABLES)
            (OUT/'runtime-inventory.json').write_text(json.dumps(state,indent=2)+'\n')
            (OUT/'native-process-maps.txt').write_text(maps)
        finally:
            if child.poll()is None:child.terminate()
            try:child.wait(timeout=15)
            except subprocess.TimeoutExpired:child.kill();child.wait()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--native-inventory',action='store_true');args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if args.native_inventory:native_inventory();return
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],route_complete=False,final_timing_complete=False,process_checkpoint_proven=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(label,command,timeout=900,env=None):
        with (OUT/(label+'.log')).open('w')as stream:
            p=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout)
        r.setdefault('commands',[]).append(dict(label=label,returncode=p.returncode,log_sha256=sha(OUT/(label+'.log'))));save()
        if p.returncode:print((OUT/(label+'.log')).read_text(errors='replace')[-12000:],flush=True)
        assert p.returncode==0,(label,p.returncode)
    save()
    try:
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==APP_SHA;r['runtime_sha256']=APP_SHA
        pin=json.loads((ROOT/'docs/evidence/mainchip-native-route-interruption-20261020.json').read_text())
        names=[PREFIX+x for x in ('fresh-fanout-global.odb','fresh-fanout.guide','fresh_fanout_native.tcl','clean_orphan_guides_drt.tcl','fixed_clock_native.tcl','propagated_native.tcl','_env.tcl','config.json','state_in.json')]
        assert all(n in pin['outputs']for n in names)
        prior,proof=reports.restore_report(pin['group'],pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',names)
        assert prior['status']=='INTERRUPTED_NATIVE_STAGE_RETAINED_NOT_ACCEPTED'
        r['source']=proof
        odb=OUT/'source'/PREFIX/'fresh-fanout-global.odb'
        # One shared verifier for host/container; exact same database and output.
        tcl='read_db {'+str(odb)+'}\nset b [ord::get_db_block]\nset n [llength [$b getInsts]]\nif {$n != 152762} {error "Saved global instance census differs"}\nputs "NSSOC_INSTANCES $n"\nputs "NSSOC_NETS [llength [$b getNets]]"\n'
        (OUT/'inventory.tcl').write_text(tcl+'set f [open {'+str(OUT/'inventory-ready')+'} w]\nputs $f ready\nclose $f\nafter 1800000\nexit\n')
        run('build-runtime-closure',[str(app),'python',str(Path(__file__).resolve()),'--native-inventory'],timeout=2400)
        inventory=json.loads((OUT/'runtime-inventory.json').read_text())
        r['actual_elf']={k:inventory[k]for k in ('actual_elf','actual_elf_sha256','actual_elf_bytes','runtime_file_count','runtime_bytes')}
        r['closure_inventory_sha256']=sha(OUT/'runtime-inventory.json')
        r['runtime_environment']=inventory['environment'];save()
        (OUT/'host.tcl').write_text(tcl+'write_db {'+str(OUT/'host.odb')+'}\nexit\n')
        (OUT/'container.tcl').write_text(tcl+'write_db {'+str(OUT/'container.odb')+'}\nexit\n')
        safe_env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN','LD_PRELOAD','GLIBC_TUNABLES')}
        safe_env['GLIBC_TUNABLES']=TUNABLES
        run('host-readback',[str(app),'openroad','-exit','-no_init',str(OUT/'host.tcl')],env=safe_env)
        image='nssoc-mainchip-runtime'
        run('build-exact-container',['docker','build','--network','none','-t',image,str(OUT/'runtime-root')],timeout=1800)
        info=json.loads(subprocess.check_output(['docker','image','inspect',image]))[0]
        r['image_id']=info['Id'];save()
        envargs=[]
        for key,value in sorted(inventory['environment'].items()):envargs.extend(['-e',key+'='+value])
        run('container-readback',['docker','run','--rm','--network','none','--security-opt','seccomp=unconfined',
            '--mount','type=bind,src='+str(OUT)+',dst='+str(OUT),'-w',str(OUT),'-e','GLIBC_TUNABLES='+TUNABLES,
            *envargs,'--entrypoint',inventory['actual_elf'],info['Id'],'-exit','-no_init',str(OUT/'container.tcl')])
        host=sha(OUT/'host.odb');container=sha(OUT/'container.odb')
        assert host==container,('Isolated native DB serialization differs',host,container)
        r['isolated_db_equivalence']=dict(host_odb_sha256=host,container_odb_sha256=container,byte_identical=True,
            original_global_odb_sha256=sha(odb),instances=152762,actual_native_elf_used=True)
        run('save-exact-image',['docker','save','-o',str(OUT/'native-image.tar'),info['Id']],timeout=900)
        r['image_archive']=dict(sha256=sha(OUT/'native-image.tar'),bytes=(OUT/'native-image.tar').stat().st_size)
        # The image archive is durable and complete. Avoid publishing a second
        # copy of the identical extracted filesystem inside the result archive.
        assert r['image_archive']['bytes']>0 and r['image_id'].startswith('sha256:')
        shutil.rmtree(OUT/'runtime-root')
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in names)
        r.update(status='PASS_EXACT_REAL_OPENROAD_CONTAINER_AND_SAVED_DB_REQUIRES_PROCESS_CHECKPOINT',
            sources_unchanged=True,process_checkpoint_proven=False,
            next_action='Use this exact native image and actual source Tcl for bounded OpenROAD process checkpoint/restore on separate cloud runners, then resume full DRT with all original gates. No route or final STA acceptance yet.')
    except BaseException as error:
        import traceback
        r.update(status='FAIL_OR_ERROR',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'and 'runtime-root'not in p.relative_to(OUT).parts}
        save()
if __name__=='__main__':main()
