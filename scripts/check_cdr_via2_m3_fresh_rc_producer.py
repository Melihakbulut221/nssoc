#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only producer fixtures; no native payload or extraction is used."""
import copy,json,tempfile,types
from pathlib import Path
import cdr_via2_m3_fresh_rc_producer as p

def controls(root,config):
    positive=[];refused=[]
    def good(name,fn):
        result=fn();positive.append(name);return result
    def bad(name,fn):
        try:fn()
        except (RuntimeError,ValueError,KeyError,UnicodeError,TypeError,FileNotFoundError):refused.append(name)
        else:raise RuntimeError('refusal did not trigger: '+name)
    actual=good('complete actual proof and current metadata',lambda:p.metadata(root,config))
    good('all actual original live metadata',lambda:p.validate_live(config,actual,*[actual[k]for k in('run','jobs','release','tag')]))
    for label,edit in(
        ('wrong producer SHA',lambda d:d['run'].__setitem__('head_sha','0'*40)),
        ('rerun attempt',lambda d:d['run'].__setitem__('run_attempt',2)),
        ('wrong workflow',lambda d:d['run'].__setitem__('workflow_id',1)),
        ('nonterminal producer',lambda d:d['run'].__setitem__('status','in_progress')),
        ('failed producer',lambda d:d['run'].__setitem__('conclusion','failure')),
        ('missing job',lambda d:d['jobs']['jobs'].pop()),
        ('wrong job identity',lambda d:d['jobs']['jobs'][0].__setitem__('id',1)),
        ('changed source job',lambda d:d['jobs']['jobs'][0].__setitem__('head_sha','0'*40)),
        ('changed terminal step',lambda d:d['jobs']['jobs'][0]['steps'][0].__setitem__('conclusion','failure')),
        ('wrong release',lambda d:d['release'].__setitem__('id',1)),
        ('changed release target',lambda d:d['release'].__setitem__('target_commitish','0'*40)),
        ('draft release',lambda d:d['release'].__setitem__('draft',True)),
        ('release no longer prerelease',lambda d:d['release'].__setitem__('prerelease',False)),
        ('missing asset',lambda d:d['release']['assets'].pop()),
        ('duplicate asset',lambda d:d['release']['assets'].append(copy.deepcopy(d['release']['assets'][0]))),
        ('changed asset digest',lambda d:d['release']['assets'][0].__setitem__('digest','sha256:'+'0'*64)),
        ('changed asset identity',lambda d:d['release']['assets'][0].__setitem__('id',1)),
        ('changed asset bytes',lambda d:d['release']['assets'][0].__setitem__('size',1)),
        ('wrong tag source',lambda d:d['tag']['object'].__setitem__('sha','0'*40)),
        ('annotated tag',lambda d:d['tag']['object'].__setitem__('type','tag'))):
        changed=copy.deepcopy(actual);edit(changed)
        bad(label,lambda d=changed:p.validate_live(config,actual,*[d[k]for k in('run','jobs','release','tag')]))
    for label,edit in(
        ('wrong complete proof hash',lambda c:c['proof']['receipt'].__setitem__('sha256','0'*64)),
        ('missing complete member',lambda c:c['complete_members'].pop(next(iter(c['complete_members'])))),
        ('wrong archive root',lambda c:c.__setitem__('archive_root','historical-stem')),
        ('wrong archive hash',lambda c:c.__setitem__('archive_sha256','0'*64)),
        ('missing current member',lambda c:c['current_files'].pop(next(iter(c['current_files'])))),
        ('old port indices',lambda c:c.__setitem__('native_port_order',actual['qualification']['native_identity']['old_native_port_order'])),
        ('wrong candidate identity',lambda c:c['candidate_gds'].__setitem__('sha256','0'*64))):
        changed=copy.deepcopy(config);edit(changed);bad(label,lambda c=changed:p.metadata(root,c))
    for text in ('/absolute','a/../b','a//b','./a','a'+chr(92)+'b'):
        bad('unsafe relative '+text,lambda s=text:p.relative(s))
    for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',bytes([255])):bad('invalid strict JSON '+repr(raw),lambda b=raw:p.decode(b))
    with tempfile.TemporaryDirectory(prefix='explicit-synthetic-rc-producer-')as name:
        scratch=Path(name).resolve();record=scratch/'sample.json';record.write_bytes(b'{"ok":true}')
        pin=p.fingerprint(record.read_bytes());good('exact real synthetic bytes',lambda:p.exact_record(scratch,'sample.json',pin))
        bad('changed byte pin',lambda:p.exact_record(scratch,'sample.json',dict(pin,bytes=1)))
        bad('changed canonical object pin',lambda:p.exact_record(scratch,'sample.json',dict(pin,canonical_object_sha256='0'*64)))
        (scratch/'link.json').symlink_to(record);bad('symlink record',lambda:p.exact_record(scratch,'link.json',pin))
        restore=scratch/'restore';restore.mkdir();view=restore/p.CURRENT_PREFIX
        graph=dict(wire_component_count=113,native_net_count=238,native_electrical_net_count=114,native_terminal_count=1446,native_device_count=500,wire_rc_extracted=False)
        anchors=dict(logical_anchor_count=978,physical_anchor_count=978,public_ports=25,point_quantization_used_to_merge=False,wire_rc_extracted=False)
        payload={p.CURRENT_PREFIX+n:b'explicit synthetic placeholder; not native data'for n in config['current_files']}
        payload[p.CURRENT_PREFIX+'wire/native05/result.json']=json.dumps(graph).encode()
        payload[p.CURRENT_PREFIX+'wire/anchors08.json']=json.dumps(anchors).encode()
        sq=copy.deepcopy(actual['qualification']);sq['current_files']={n:p.fingerprint(payload[p.CURRENT_PREFIX+n])for n in config['current_files']}
        payload['native/view/canonical-view-qualification.json']=json.dumps(sq).encode()
        for i in range(p.MEMBERS-len(payload)):payload['synthetic-inputs/'+str(i)+'.txt']=b'synthetic only'
        for n,b in payload.items():
            dest=restore/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
        members={n:p.fingerprint(b)for n,b in payload.items()};sp=copy.deepcopy(config);sp['complete_members']=members
        full=dict(every_member_authenticated=True,full_member_count=p.MEMBERS,full_members=members,selected=members)
        original=dict(qualification=sq)
        # Same production code object in an explicitly synthetic isolated namespace.
        # No process environment or production module globals are modified.
        namespace=dict(vars(p));namespace['CURRENT_ROOT']=str(view)
        synthetic=types.FunctionType(p.validate_restored.__code__,namespace,'synthetic_validate_restored')
        if synthetic.__code__ is not p.validate_restored.__code__:raise RuntimeError('fixture changed code object')
        good('complete synthetic665 restore and current78',lambda:synthetic(restore,sp,full,original))
        bad('real absolute input root refuses synthetic location',lambda:p.validate_restored(restore,sp,full,original))
        bad('incomplete archive authentication',lambda:synthetic(restore,sp,dict(full,every_member_authenticated=False),original))
        bad('wrong archive member count',lambda:synthetic(restore,sp,dict(full,full_member_count=664),original))
        extra=restore/'extra.json';extra.write_bytes(b'{}');bad('extra restored member',lambda:synthetic(restore,sp,full,original));extra.unlink()
        sample=restore/next(iter(payload));saved=sample.read_bytes();sample.write_bytes(b'changed');bad('changed restored bytes',lambda:synthetic(restore,sp,full,original));sample.write_bytes(saved)
        sample.unlink();sample.symlink_to(record);bad('restored symlink',lambda:synthetic(restore,sp,full,original));sample.unlink();sample.write_bytes(saved)
        smaller=dict(full);smaller['selected']=dict(members);smaller['selected'].pop(next(iter(smaller['selected'])));bad('omitted selected member',lambda:synthetic(restore,sp,smaller,original))
        good('all synthetic bytes restored after refusals',lambda:synthetic(restore,sp,full,original))
    return dict(status='PASS_SOURCE_PRODUCER_METADATA_AND_EXPLICIT_SYNTHETIC_RESTORE_ONLY',positive_controls=positive,refusal_controls=refused,native_acquisition=False,RC_executed=False,electrical_accepted=False)

if __name__=='__main__':
    raise SystemExit('Call controls only after the reviewed host source guard on GitHub; standalone execution disabled')
