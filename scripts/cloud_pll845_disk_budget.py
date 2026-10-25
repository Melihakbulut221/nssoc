#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud host storage only; native process, probes and acceptance gates are unchanged."""
import contextlib,gzip,hashlib,io,json,math
from pathlib import Path
GIB=1024**3
LEGACY='185b78aa506cf5fbd84d171ac58ddc5bf3c7e415f91139dbbb1fbe320c05f4f3'
CONTROLLER='scripts/cloud_pll845_native_acquisition.py'
SELF='scripts/cloud_pll845_disk_budget.py'
def digest(data):return hashlib.sha256(data).hexdigest()

def verify_resume_methods(report,current,root):
    manifest=json.loads((root/'scripts/pll845-host-storage-deltas.json').read_text())
    text=(root/CONTROLLER).read_text()
    assert digest(text.encode())==manifest['candidate_sha256']==current[CONTROLLER]
    assert digest((root/SELF).read_bytes())==manifest['helper_sha256']==current[SELF]
    for edit in reversed(manifest['edits']):
        assert text.count(edit['after'])==edit['count']
        text=text.replace(edit['after'],edit['before'])
    assert digest(text.encode())==manifest['baseline_sha256']==LEGACY
    old=report['method_hashes']
    if report['controller_sha256']==current[CONTROLLER]:
        assert old==current,'Changed method in current-revision continuation'
        return dict(mode='exact-current-methods',native_methods_unchanged=True)
    assert report['controller_sha256']==LEGACY,'Unrecognized controller migration'
    expected=dict(current);expected.pop(SELF);expected[CONTROLLER]=LEGACY
    assert old==expected,'Changed native/parser/physical method during storage migration'
    return dict(mode='explicit-reversible-host-storage-only-delta',baseline_sha256=LEGACY,
        candidate_sha256=current[CONTROLLER],helper_sha256=current[SELF],native_methods_unchanged=True)

class PartsReader(io.RawIOBase):
    def __init__(self,paths):
        self.paths=iter(paths);self.stream=None
    def readable(self):return True
    def readinto(self,buffer):
        view=memoryview(buffer);used=0
        while used<len(view):
            if self.stream is None:
                path=next(self.paths,None)
                if path is None:break
                self.stream=path.open('rb')
            n=self.stream.readinto(view[used:])
            if n:used+=n
            else:self.stream.close();self.stream=None
        return used
    def close(self):
        if self.stream:self.stream.close();self.stream=None
        super().close()

@contextlib.contextmanager
def joined_parts(manifest,directory):
    # Caller verifies every part and the complete ordered digest before extraction.
    raw=PartsReader([directory/p['name']for p in manifest['parts']])
    with io.BufferedReader(raw,buffer_size=4*1024**2)as stream:
        yield stream

def reserve_bytes(payload_bytes,entries):
    assert payload_bytes>=0 and entries>=0
    # One streaming gzip archive is written by cloud_chunked_results.pack.
    # Include tar/PAX headers and block rounding, 1% compression expansion
    # headroom, and 8 GiB for checkpoint images, growth until the next poll,
    # runner activity and logs. No optimistic measured compression ratio.
    tar_bound=payload_bytes+(entries+1)*8192+10240
    return max(12*GIB,(tar_bound*101+99)//100+8*GIB)

def disk_plan(root):
    paths=list(root.rglob('*'));total=sum(p.stat().st_size for p in paths if p.is_file())
    return dict(source_tree_bytes=total,source_tree_entries=len(paths),
        archive_copies=1,archive_reserve_bytes=reserve_bytes(total,len(paths)),
        expansion_headroom_percent=1,checkpoint_and_poll_margin_bytes=8*GIB)

def controls():
    import tempfile
    with tempfile.TemporaryDirectory()as tmp:
        root=Path(tmp);payload=bytes(range(256))*4096
        packed=gzip.compress(payload);paths=[]
        for i in range(0,len(packed),127):
            p=root/str(i);p.write_bytes(packed[i:i+127]);paths.append(p)
        with io.BufferedReader(PartsReader(paths))as src:
            assert gzip.GzipFile(fileobj=src).read()==payload
        assert sum(p.stat().st_size for p in paths)==len(packed)
        paths[-1].write_bytes(paths[-1].read_bytes()[:-1])
        try:
            with io.BufferedReader(PartsReader(paths))as src:gzip.GzipFile(fileobj=src).read()
        except (EOFError,OSError):pass
        else:raise AssertionError('Truncated compressed stream accepted')
        observed_free=71302311936
        assert reserve_bytes(36213374907,20000)<observed_free<2*36213374907
        assert reserve_bytes(45*GIB,20000)<60*GIB
        assert reserve_bytes(60*GIB,20000)>60*GIB
        assert reserve_bytes(0,0)>=12*GIB
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'scripts/pll845-host-storage-deltas.json').read_text())
    import copy
    current={CONTROLLER:manifest['candidate_sha256'],SELF:manifest['helper_sha256'],
        'unchanged-native-parser':'a'*64}
    legacy=dict(current);legacy.pop(SELF);legacy[CONTROLLER]=LEGACY
    prior=dict(controller_sha256=LEGACY,method_hashes=legacy)
    assert verify_resume_methods(prior,current,root)['native_methods_unchanged']
    same=dict(controller_sha256=current[CONTROLLER],method_hashes=current)
    assert verify_resume_methods(same,current,root)['mode']=='exact-current-methods'
    rejected=[]
    for name in ('unknown-controller','changed-parser','missing-parser','extra-method','current-changed-parser'):
        bad=copy.deepcopy(same if name=='current-changed-parser'else prior)
        if name=='unknown-controller':bad['controller_sha256']='0'*64
        elif name in ('changed-parser','current-changed-parser'):bad['method_hashes']['unchanged-native-parser']='b'*64
        elif name=='missing-parser':del bad['method_hashes']['unchanged-native-parser']
        else:bad['method_hashes']['unexpected']='c'*64
        try:verify_resume_methods(bad,current,root)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Changed continuation method accepted')
    assert len(rejected)==5
    return dict(joined_parts_exact_roundtrip=True,truncated_stream_rejected=True,
        exact_current_and_legacy_method_controls=True,changed_methods_rejected=rejected,
        observed_duplicate_reserve_trap_reproduced=True,conservative_one_archive_budget=True)
if __name__=='__main__':print(json.dumps(controls()))
