#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Resume genuine training profiles; isolate only Autoconf's conftest profile."""
import argparse,json,os,shutil,subprocess,tarfile
from pathlib import Path
import cloud_tree32_pgo as study
from run_cloud_tx_layout_repair import fetch,sha
ROOT=study.ROOT;OUT=study.OUT
ARCHIVE_SHA='7087cc08148b4d8bac5fed0e7e416ed7e4e9c332cd9616211448c5f344d10fd8'
CONFTEST_SHA='53f81018b1dab0cd21bace29a35a86e1db37fd7b67be0943a922403dedf26ff2'

def restore():
    assert not OUT.exists()
    packed=ROOT/'tree32-pgo-training-source.tar.gz'
    fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38860616186-1-tree32-pgo/tree32-pgo-38860616186-1.tar.gz.part0000',ARCHIVE_SHA,packed)
    assert packed.stat().st_size==131270752
    with tarfile.open(packed) as tar:
        members=tar.getmembers();assert len(members)==len({m.name for m in members})
        for m in members:
            p=Path(m.name);assert not p.is_absolute() and '..' not in p.parts and p.parts[0]=='cloud-tree32-pgo'
            assert m.isfile() or m.isdir()
        tar.extractall(ROOT,filter='data')
    packed.unlink()
    prior=json.loads((OUT/'result.json').read_text());assert prior==dict(status='FAIL_MISSING_PAIRED_REPORT',accepted=False)
    (OUT/'result.json').rename(OUT/'prior-failed-result.json')
    # Keep the archived native logs verbatim; the new build has separate names.
    for name in ('configure.log','build.log','config.log'):
        p=OUT/name
        if p.exists():p.rename(OUT/('prior-'+name))
    assert subprocess.check_output(['gcc','--version'],text=True)==(OUT/'compiler.txt').read_text()
    state=json.loads((OUT/'prepared-state.json').read_text())
    assert state['status']=='PASS_ACTUAL_FINE_TREE_TRAINING_NOT_COMPARISON_OR_PHY_ACCEPTANCE'
    study.verify_inventory(state['runtime_inventory']);study.verify_inventory(state['profile_inventory'])
    study.source.OUT=OUT
    original,contract,protected,receipt=study.source.restore_source(Path(state['runtime_paths']['packaged']))
    assert str(original)==state['source_directory'] and contract==state['contract'] and protected==state['protected_inputs']
    assert receipt['source_archive_sha256']==state['source_receipt']['source_archive_sha256']
    study.prepared()  # Rehash all original source/runtime/profile bytes before moving any file.
    candidates=[p for p in study.PROFILE_DIR.rglob('*.gcda') if p.name.endswith('#conftest.gcda')]
    assert len(candidates)==1
    p=candidates[0]
    expected=str(Path(os.environ['RUNNER_TEMP'])/'tree32-pgo-build').replace('/','#')+'#conftest.gcda'
    assert p.name==expected and sha(p)==CONFTEST_SHA and p.stat().st_size==128
    quarantine=OUT/'configure-only-profile';quarantine.mkdir()
    destination=quarantine/p.name;shutil.move(p,destination)
    r=dict(status='RESTORED_ORIGINAL_TRAINING_ONLY_CONFIGURE_PROFILE_QUARANTINED',source_run=38860616186,
        archive_sha256=ARCHIVE_SHA,source_head=os.environ['GITHUB_SHA'],prepared_state_sha256=sha(OUT/'prepared-state.json'),
        original_profile=str(p),quarantine=str(destination),quarantined_sha256=CONFTEST_SHA,
        all_simulator_profiles_unchanged=True,training_repeated=False,accepted=False)
    (OUT/'resume.json').write_text(json.dumps(r,indent=2)+'\n')

def return_profile():
    r=json.loads((OUT/'resume.json').read_text());p=Path(r['original_profile']);q=Path(r['quarantine'])
    assert p.is_relative_to(study.PROFILE_DIR) and q.is_relative_to(OUT/'configure-only-profile')
    assert not p.exists() and sha(q)==CONFTEST_SHA and sha(OUT/'prepared-state.json')==r['prepared_state_sha256']
    shutil.copyfile(q,p)
    study.prepared()  # Original immutable prepared state remains byte-for-byte identical.
    r.update(status='PASS_RESUMED_PROFILE_BYTES_IDENTICAL_AFTER_BUILD_NOT_NUMERICAL_ACCEPTANCE',
        all_original_profiles_restored=True)
    (OUT/'resume.json').write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    parser=argparse.ArgumentParser();parser.add_argument('--return-configure-profile',action='store_true');args=parser.parse_args()
    if args.return_configure_profile:return_profile()
    else:restore()
