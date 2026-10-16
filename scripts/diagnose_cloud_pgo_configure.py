#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reproduce the terminal PGO build failure using preserved profiles, in cloud."""
import hashlib,json,os,shutil,subprocess,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
from cloud_tree32_pgo import FLAGS,PROFILE_DIR
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pgo-configure-diagnosis'
ARCHIVE_SHA='7087cc08148b4d8bac5fed0e7e416ed7e4e9c332cd9616211448c5f344d10fd8'

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_run=38860616186,source_head=os.environ['GITHUB_SHA'],accepted=False,profile_build_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,log,cwd=ROOT):
        with (OUT/(log+'.log')).open('w') as stream: code=subprocess.call([str(x) for x in cmd],cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
        return code
    save()
    try:
        packed=OUT/'source.tar.gz'
        fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38860616186-1-tree32-pgo/tree32-pgo-38860616186-1.tar.gz.part0000',ARCHIVE_SHA,packed)
        assert packed.stat().st_size==131270752
        with tarfile.open(packed) as tar:
            members=tar.getmembers();assert len(members)==len({m.name for m in members})
            for m in members:
                p=Path(m.name);assert not p.is_absolute() and '..' not in p.parts and p.parts[0]=='cloud-tree32-pgo'
                assert m.isfile() or m.isdir()
            selected=[m for m in members if m.isfile() and (m.name.startswith('cloud-tree32-pgo/profiles/') or m.name in ['cloud-tree32-pgo/compiler.txt','cloud-tree32-pgo/training.json','cloud-tree32-pgo/prepared-state.json','cloud-tree32-pgo/configure.log'])]
            tar.extractall(ROOT,members=selected,filter='data')
        packed.unlink()
        training=json.loads((ROOT/'cloud-tree32-pgo/training.json').read_text())
        assert training['status']=='PASS_ACTUAL_FINE_TREE_TRAINING_NOT_COMPARISON_OR_PHY_ACCEPTANCE'
        for name,pin in training['profile_inventory'].items():
            p=Path(name);assert p.is_relative_to(PROFILE_DIR) and p.stat().st_size==pin['bytes'] and sha(p)==pin['sha256']
        r['training']=dict(status=training['status'],elapsed_s=training['elapsed_s'],capture=training['capture'],hot_profile_files=training['hot_profile_files'])
        r['profile_inventory']=training['profile_inventory'];r['compiler']=subprocess.check_output(['gcc','--version'],text=True)
        r['prior_compiler']=(ROOT/'cloud-tree32-pgo/compiler.txt').read_text();assert r['compiler']==r['prior_compiler']
        src=Path(os.environ['RUNNER_TEMP'])/'tree32-pgo-source';build=Path(os.environ['RUNNER_TEMP'])/'tree32-pgo-build'
        for cmd,name in [(['git','init',src],'git-init'),(['git','-C',src,'remote','add','origin','https://github.com/imr/ngspice.git'],'git-origin'),(['git','-C',src,'fetch','--depth','1','origin','a80f6e3e95d51534905b1f23410a951802666656'],'git-fetch'),(['git','-C',src,'checkout','--detach','FETCH_HEAD'],'git-checkout')]:assert run(cmd,name)==0
        from cloud_vbic_companion import patch
        r['patch']=patch(src/'src/spicelib/devices/vbic/vbicload.c')
        assert run(['./autogen.sh'],'autogen',src)==0
        build.mkdir()
        command=[src/'configure','--without-x','--with-readline=no','--disable-openmp','CFLAGS='+FLAGS,'LDFLAGS='+FLAGS]
        r['original_configure_returncode']=run(command,'original-configure',build)
        shutil.copyfile(build/'config.log',OUT/'original-config.log')
        config=(OUT/'original-config.log').read_text()
        lines=config.splitlines();indices=[i for i,l in enumerate(lines) if 'error:' in l or 'coverage-mismatch' in l and 'CFLAGS=' not in l]
        r['original_error_contexts']=['\n'.join(lines[max(0,i-3):i+5]) for i in indices if 'error:' in lines[i]]
        save()
        assert r['original_configure_returncode']!=0 and 'coverage-mismatch' in config, 'Original profile mismatch was not reproduced; inspect retained logs'
        suspects=[p for p in PROFILE_DIR.rglob('*.gcda') if p.name.endswith('#conftest.gcda')]
        assert suspects and all('tree32-pgo-build' in p.name for p in suspects)
        quarantine=OUT/'configure-only-profiles';quarantine.mkdir()
        r['quarantined_configure_profiles']=[]
        for p in suspects:
            assert not any(x in p.name.lower() for x in ('vbicload','spfactor','spsolve'))
            r['quarantined_configure_profiles'].append(dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size))
            shutil.move(p,quarantine/p.name)
        r['isolated_configure_returncode']=run(command,'isolated-configure',build)
        shutil.copyfile(build/'config.log',OUT/'isolated-config.log')
        assert r['isolated_configure_returncode']==0
        for name,pin in training['profile_inventory'].items():
            p=Path(name)
            if p in suspects: p=quarantine/p.name
            assert sha(p)==pin['sha256'] and p.stat().st_size==pin['bytes']
        r['status']='PASS_REPRODUCED_CONFIGURE_PROFILE_COLLISION_NOT_RUNTIME_ACCEPTANCE'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
