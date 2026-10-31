#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only exact-runtime metadata and explicitly synthetic archive controls."""
import copy,io,os,tarfile,tempfile
from pathlib import Path
import cdr_via2_m3_fresh_rc_runtime as r

def controls(root):
    positive=[];refused=[]
    def good(label,fn):value=fn();positive.append(label);return value
    def bad(label,fn):
        try:fn()
        except (AssertionError,RuntimeError,ValueError,KeyError,TypeError,FileNotFoundError,tarfile.TarError):refused.append(label)
        else:raise AssertionError('refusal did not trigger '+label)
    c,d=good('all original direct metadata bytes and precise qualification',lambda:r.records(root))
    args=[d['precise-'+n+'.json']for n in('run','jobs','release','tag-ref')]
    good('actual historical source tag target distinction',lambda:r.validate_precise_live(c,d,*args))
    for label,edit in (
        ('runtime producer source changed',lambda v:v[0].__setitem__('head_sha','0'*40)),
        ('runtime producer pending',lambda v:v[0].__setitem__('status','in_progress')),
        ('runtime producer failed',lambda v:v[0].__setitem__('conclusion','failure')),
        ('runtime producer rerun',lambda v:v[0].__setitem__('run_attempt',2)),
        ('runtime workflow changed',lambda v:v[0].__setitem__('workflow_id',1)),
        ('runtime job missing',lambda v:v[1]['jobs'].clear()),
        ('runtime job source changed',lambda v:v[1]['jobs'][0].__setitem__('head_sha','0'*40)),
        ('runtime job failed',lambda v:v[1]['jobs'][0].__setitem__('conclusion','failure')),
        ('runtime job step changed',lambda v:v[1]['jobs'][0]['steps'][0].__setitem__('conclusion','failure')),
        ('historical branch target silently replaced with source',lambda v:v[2].__setitem__('target_commitish',c['precise']['source'])),
        ('historical tag silently replaced with source',lambda v:v[3]['object'].__setitem__('sha',c['precise']['source'])),
        ('historical tag changed to annotated',lambda v:v[3]['object'].__setitem__('type','tag')),
        ('runtime release changed',lambda v:v[2].__setitem__('id',1)),
        ('runtime asset missing',lambda v:v[2]['assets'].pop()),
        ('runtime asset duplicated',lambda v:v[2]['assets'].append(copy.deepcopy(v[2]['assets'][0]))),
        ('runtime asset identity changed',lambda v:v[2]['assets'][0].__setitem__('id',1)),
        ('runtime asset bytes changed',lambda v:v[2]['assets'][0].__setitem__('size',1)),
        ('runtime asset digest changed',lambda v:v[2]['assets'][0].__setitem__('digest','sha256:'+'0'*64)),
        ('runtime asset incomplete',lambda v:v[2]['assets'][0].__setitem__('state','new'))):
        value=copy.deepcopy(args);edit(value);bad(label,lambda v=value:r.validate_precise_live(c,d,*v))
    with tempfile.TemporaryDirectory(prefix='explicit-synthetic-rc-runtime-')as name:
        base=Path(name)
        payload=b'explicit synthetic executable; no native runtime'
        pins={'bin/tool':r.q.fingerprint(payload)}
        manifest=r.encode(dict(files=pins,scope='explicit synthetic fixture'))
        def archive(path,rows):
            with tarfile.open(path,'w:gz',format=tarfile.GNU_FORMAT)as tar:
                for name,data,kind in rows:
                    item=tarfile.TarInfo(name);item.mode=0o755 if name.endswith('tool')else 0o644
                    if kind=='dir':item.type=tarfile.DIRTYPE;tar.addfile(item)
                    elif kind=='link':item.type=tarfile.SYMTYPE;item.linkname='outside';tar.addfile(item)
                    elif kind=='sparse':item.type=tarfile.GNUTYPE_SPARSE;tar.addfile(item)
                    elif kind=='special':item.type=tarfile.FIFOTYPE;tar.addfile(item)
                    elif kind=='oversized':item.size=3*1024**3;tar.addfile(item)
                    else:item.size=len(data);tar.addfile(item,io.BytesIO(data))
        rows=[('.',b'','dir'),('./bin/',b'','dir'),('./bin/tool',payload,'file'),('./manifest.json',manifest,'file')]
        packed=base/'ok.tar.gz';archive(packed,rows);destination=base/'runtime'
        observed=good('real normalized directory and executable archive extraction',lambda:r.safe_unpack(packed,destination))
        good('complete original synthetic manifest byte verification',lambda:r.verify_manifest(destination,observed))
        if(destination/'bin/tool').stat().st_mode&0o777!=0o755:raise AssertionError('actual executable mode lost')
        positive.append('actual extracted executable mode755')
        good('all-byte and executable-mode owned copy',lambda:r.copy_owned(destination,base/'copy',observed))
        if(base/'copy/bin/tool').stat().st_mode&0o777!=0o755:raise AssertionError('copied executable mode lost')
        bad('runtime copy cannot overwrite',lambda:r.copy_owned(destination,base/'copy',observed))
        bad('runtime extraction cannot overwrite',lambda:r.safe_unpack(packed,destination))
        changed=dict(observed);changed['bin/tool']=dict(changed['bin/tool'],sha256='0'*64)
        bad('changed observed runtime fingerprint',lambda:r.verify_manifest(destination,changed))
        (destination/'bin/tool').write_bytes(b'changed');bad('changed actual runtime file',lambda:r.verify_manifest(destination,observed));(destination/'bin/tool').write_bytes(payload)
        saved=(destination/'manifest.json').read_bytes();(destination/'manifest.json').write_bytes(r.encode(dict(files={'missing':r.q.fingerprint(b'x')})))
        bad('manifest member missing',lambda:r.verify_manifest(destination,observed));(destination/'manifest.json').write_bytes(saved)
        for index,(label,extra)in enumerate((
            ('duplicate normalized runtime path',[('bin/tool',payload,'file')]),
            ('runtime traversal',[('../escape',b'x','file')]),
            ('runtime absolute path',[('/escape',b'x','file')]),
            ('runtime symlink',[('link',b'','link')]),
            ('runtime sparse file',[('sparse',b'','sparse')]),
            ('runtime FIFO',[('fifo',b'','special')]),
            ('runtime huge member',[('huge',b'','oversized')]))):
            trial=base/('bad'+str(index)+'.tar.gz');archive(trial,rows+extra)
            bad(label,lambda p=trial,i=index:r.safe_unpack(p,base/('bad'+str(i))))
        (destination/'link').symlink_to(destination/'bin/tool');bad('runtime copy symlink refused',lambda:r.copy_owned(destination,base/'bad-copy',{'link':pins['bin/tool']}))
    return dict(status='PASS_RUNTIME_SOURCE_AND_SYNTHETIC_ARCHIVE_CONTROLS_ONLY',positive_controls=positive,refusal_controls=refused,native_payload_acquired=False,RC_executed=False)

if __name__=='__main__':raise SystemExit('Hosted integrated source controls only; no standalone native authority')
