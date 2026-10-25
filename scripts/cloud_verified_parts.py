#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Restore selected native evidence only after complete ordered-part verification."""
import copy,hashlib,io,json,tarfile,tempfile
from pathlib import Path
from cloud_chunked_results import verify_parts,pack

class JoinedParts(io.RawIOBase):
    def __init__(self,paths):
        super().__init__();self.paths=iter(paths);self.current=None
    def readable(self):return True
    def readinto(self,buffer):
        while True:
            if self.current is None:
                path=next(self.paths,None)
                if path is None:return 0
                self.current=path.open('rb')
            count=self.current.readinto(buffer)
            if count:return count
            self.current.close();self.current=None
    def close(self):
        if self.current is not None:self.current.close();self.current=None
        super().close()

def extract_verified(manifest,parts,destination,expected):
    proof=verify_parts(manifest,parts)
    prefix=manifest['source_directory'];assert Path(prefix).name==prefix and prefix not in ('','.','..')
    assert expected and all(Path(n).as_posix()==n and not Path(n).is_absolute() and '..' not in Path(n).parts for n in expected)
    assert not destination.exists();destination.mkdir(parents=True)
    seen=set();found={}
    with JoinedParts([parts/p['name'] for p in manifest['parts']]) as joined:
        with tarfile.open(fileobj=joined,mode='r|gz') as archive:
            for entry in archive:
                name=Path(entry.name)
                assert not name.is_absolute() and '..' not in name.parts and name.parts[0]==prefix
                assert entry.name not in seen and (entry.isfile() or entry.isdir()),'Duplicate or non-regular archive entry'
                seen.add(entry.name)
                relative=str(name.relative_to(prefix))
                if relative not in expected:continue
                assert entry.isfile()
                target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
                digest=hashlib.sha256();total=0
                with archive.extractfile(entry) as source,target.open('xb') as output:
                    while data:=source.read(4*1024**2):output.write(data);digest.update(data);total+=len(data)
                assert digest.hexdigest()==expected[relative] and total==entry.size,'Changed selected native evidence'
                found[relative]=dict(sha256=digest.hexdigest(),bytes=total)
    assert set(found)==set(expected),'Missing selected native evidence'
    return dict(archive=proof,selected_files=found,full_archive_verified_before_extraction=True)

def controls():
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);source=root/'evidence';source.mkdir();payload=bytes(range(256))*32
        (source/'wave.raw').write_bytes(payload);(source/'unused.txt').write_text('unchanged auxiliary file')
        manifest=pack(source,'fixture',root,127);expected={'wave.raw':hashlib.sha256(payload).hexdigest()}
        proof=extract_verified(manifest,root,root/'restored',expected)
        assert (root/'restored/wave.raw').read_bytes()==payload and not (root/'restored/unused.txt').exists()
        rejected=[]
        trials=[('missing',manifest,{'absent':expected['wave.raw']}),('wrong_selected_hash',manifest,{'wave.raw':'0'*64})]
        bad=copy.deepcopy(manifest);bad['parts']=bad['parts'][::-1];trials.append(('order',bad,expected))
        bad=copy.deepcopy(manifest);bad['sha256']='0'*64;trials.append(('whole_hash',bad,expected))
        trials.append(('selection_escape',manifest,{'../escape':expected['wave.raw']}))
        for label,m,e in trials:
            try:extract_verified(m,root,root/label,e)
            except (AssertionError,FileNotFoundError):rejected.append(label)
            else:raise AssertionError(label+' accepted')
        for label,name,kind in [('symlink','evidence/link',tarfile.SYMTYPE),('traversal','evidence/../escape',tarfile.REGTYPE),('wrong_root','other/file',tarfile.REGTYPE)]:
            name_part=label+'.tar.gz.part0000';path=root/name_part
            with tarfile.open(path,'w:gz') as archive:
                item=tarfile.TarInfo(name);item.type=kind;item.linkname='../../escape' if kind==tarfile.SYMTYPE else '';archive.addfile(item)
            digest=hashlib.sha256(path.read_bytes()).hexdigest();size=path.stat().st_size
            m=dict(format='ordered-tar-gzip-parts-v1',stem=label,source_directory='evidence',bytes=size,sha256=digest,parts=[dict(index=0,name=name_part,bytes=size,sha256=digest)])
            try:extract_verified(m,root,root/(label+'-out'),expected)
            except AssertionError:rejected.append(label)
            else:raise AssertionError(label+' accepted')
    return dict(exact_native_payload_roundtrip=True,negative_controls=rejected)

if __name__=='__main__':
    import os
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    print(json.dumps(controls()))
