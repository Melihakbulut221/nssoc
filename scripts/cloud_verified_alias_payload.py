#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Restore selected regular bytes from a pinned archive containing hardlink aliases.

No filesystem link is ever created. Every allowed alias must directly identify
an in-archive regular file with the same hash in the pinned complete inventory.
Existing stream extractor retains its default rejection of all nonregular files.
"""
import hashlib,io,json,os,tarfile,tempfile
from pathlib import Path
from cloud_chunked_results import verify_parts

def restore(manifest,parts,destination,expected,inventory):
    proof=verify_parts(manifest,parts)
    assert len(manifest['parts'])==1,'This checked seekable path supports exactly one verified part'
    prefix=manifest['source_directory'];assert Path(prefix).name==prefix and prefix not in ('','.','..')
    assert expected and all(inventory.get(n)==h for n,h in expected.items())
    def relative(name):
        p=Path(name);assert not p.is_absolute() and '..' not in p.parts and p.parts[0]==prefix and p.as_posix()==name
        return str(p.relative_to(prefix))
    assert not destination.exists();aliases={};found={}
    with tarfile.open(parts/manifest['parts'][0]['name'],'r:gz') as archive:
        entries=archive.getmembers();members={e.name:e for e in entries};assert len(entries)==len(members),'Duplicate archive entry'
        for entry in entries:
            name=relative(entry.name)
            if entry.islnk():
                target=relative(entry.linkname);referent=members.get(entry.linkname)
                assert referent is not None and referent.isfile(),'Hardlink must directly target a regular in-archive payload'
                assert name in inventory and target in inventory and inventory[name]==inventory[target],'Alias absent or different in pinned hash inventory'
                aliases[name]=dict(target=target,sha256=inventory[name])
            else:assert entry.isfile() or entry.isdir(),'Unsupported archive object'
        # Validate every selected path before creating any output directory.
        for name,digest in expected.items():
            relative(prefix+'/'+name);entry=members.get(prefix+'/'+name)
            assert entry and (entry.isfile() or entry.islnk()),'Missing selected payload'
        destination.mkdir(parents=True)
        for name,digest in expected.items():
            entry=members[prefix+'/'+name];payload=members[entry.linkname] if entry.islnk() else entry
            target=destination/name;target.parent.mkdir(parents=True,exist_ok=True)
            h=hashlib.sha256();total=0
            with archive.extractfile(payload) as source,target.open('xb') as output:
                while block:=source.read(1024**2):output.write(block);h.update(block);total+=len(block)
            assert h.hexdigest()==digest and total==payload.size,'Selected payload changed'
            found[name]=dict(sha256=h.hexdigest(),bytes=total,materialized_as_regular_file=True)
    return dict(archive=proof,selected_files=found,checked_hardlink_aliases=aliases,no_filesystem_links_created=True)

def controls():
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);payload=b'exact original native payload';digest=hashlib.sha256(payload).hexdigest()
        def fixture(label,kind=tarfile.LNKTYPE,target='evidence/payload',duplicate=False):
            path=root/(label+'.tar.gz.part0000')
            with tarfile.open(path,'w:gz') as a:
                item=tarfile.TarInfo('evidence/payload');item.size=len(payload);a.addfile(item,io.BytesIO(payload))
                link=tarfile.TarInfo('evidence/alias');link.type=kind;link.linkname=target;a.addfile(link)
                if duplicate:a.addfile(link)
            h=hashlib.sha256(path.read_bytes()).hexdigest();size=path.stat().st_size
            return dict(format='ordered-tar-gzip-parts-v1',stem=label,source_directory='evidence',bytes=size,sha256=h,parts=[dict(index=0,name=path.name,bytes=size,sha256=h)])
        inventory={'payload':digest,'alias':digest};m=fixture('positive')
        result=restore(m,root,root/'positive-out',{'alias':digest},inventory)
        assert (root/'positive-out/alias').read_bytes()==payload and not (root/'positive-out/alias').is_symlink()
        rejected=[]
        trials=[('symlink',fixture('symlink',kind=tarfile.SYMTYPE),inventory,{'alias':digest}),('escape',fixture('escape',target='../outside'),inventory,{'alias':digest}),('missing_target',fixture('missing_target',target='evidence/absent'),inventory,{'alias':digest}),('self_target',fixture('self_target',target='evidence/alias'),inventory,{'alias':digest}),('duplicate',fixture('duplicate',duplicate=True),inventory,{'alias':digest}),('inventory_mismatch',m,dict(inventory,alias='0'*64),{'alias':'0'*64}),('payload_hash',m,{'payload':'0'*64,'alias':'0'*64},{'alias':'0'*64})]
        for label,manifest,inv,selected in trials:
            try:restore(manifest,root,root/(label+'-out'),selected,inv)
            except (AssertionError,KeyError):rejected.append(label)
            else:raise AssertionError(label+' accepted')
    return dict(exact_alias_materialized_as_regular=True,negative_controls=rejected)
if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true';print(json.dumps(controls()))
