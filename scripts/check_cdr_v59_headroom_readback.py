#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source fixtures; no native capture download or simulator."""
import copy,hashlib,io,json,tarfile,tempfile
from pathlib import Path
import numpy as np
import cdr_v59_headroom_readback_admission as a
import cdr_v59_headroom_rows as c
import cdr_v58_saved_rows as rows
def controls():
    m=a.methods();positive=[];negative=[]
    def reject(label,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError,TypeError):negative.append(label)
        else:raise AssertionError('Accepted '+label)
    actual={}
    for case in ('nominal_early','nominal_late'):
        pin,outer,native,parts,receipt=a.reference(case,m)
        actual[case]=(pin,outer,native,parts,receipt)
        positive.append('actual_pinned_reports_'+case)
        assert a.identity(receipt['run'],receipt['job'],receipt['release'],receipt['tag'],pin)
        positive.append('actual_pinned_identity_'+case)
    pin,outer,native,parts,receipt=actual['nominal_early']
    native_sha=m['protected'][pin['prefix']+'.native-result.json']
    for label,change in [
        ('wrong_source',lambda o,n,p:n.update(source_head='0'*40)),
        ('waived_native_status',lambda o,n,p:n.update(status='PASS')),
        ('wrong_engine_exit',lambda o,n,p:n.update(returncode=1)),
        ('missing_OFF',lambda o,n,p:n.update(native_flags_verified=123)),
        ('nonzero_OP',lambda o,n,p:n.update(zero_source_op_maximum=1e-5)),
        ('original_integrity',lambda o,n,p:n['current_saved_input_integrity'].update(files=5548)),
        ('accepted_flag',lambda o,n,p:n.update(accepted=True)),
        ('wave_digest',lambda o,n,p:n['raw_capture'].update(raw_sha256='0'*64)),
        ('wrong_native_result',lambda o,n,p:o['outputs'].update({'native-controller-result.json':'0'*64})),
        ('extra_vector',lambda o,n,p:n['vectors'].append(n['vectors'][0])),
        ('part_order',lambda o,n,p:p['parts'].reverse()),
        ('wrong_outer_case',lambda o,n,p:o.update(case='nominal_late'))]:
        oo,nn,pp=copy.deepcopy((outer,native,parts));change(oo,nn,pp)
        reject(label,lambda:a.validate_reports('nominal_early',pin,oo,nn,pp,native_sha))
    for label,which,key,value in [
        ('run_head',0,'head_sha','0'*40),('run_attempt',0,'run_attempt',2),
        ('job_id',1,'id',0),('job_nonterminal',1,'status','in_progress'),
        ('job_success',1,'conclusion','success'),('release_draft',2,'draft',True),
        ('release_not_prerelease',2,'prerelease',False),('release_wrong_target',2,'target_commitish','0'*40)]:
        args=copy.deepcopy([receipt[k]for k in ('run','job','release','tag')]);args[which][key]=value
        reject(label,lambda:a.identity(*args,pin))
    for name in ('/escape','root/../escape','root/a\\b','other/a','root//a','root/a:bad'):
        reject('member_'+repr(name),lambda:a.relative(name,'root'))
    assert a.relative('root/hidden/.x','root')=='hidden/.x';positive.append('canonical_hidden_member')
    stage=json.loads((a.ROOT/'docs/evidence/cdr-v59-mim-runtime-native-pass-stage-20261025.json').read_bytes())
    contract=stage['composition']['contract'];bound=native['binding']
    records,branches,selected=c.topology(contract,bound);positive.append('actual_current500_topology')
    for label,edit in [
        ('target_base_role',lambda r:r[61]['terminals'][1].update(native_net='cp')),
        ('upper_emitter_cluster',lambda r:r[54]['terminals'][2].update(native_cluster=999)),
        ('tail_width',lambda r:r[3]['parameters'].update(w='32u')),
        ('bleeder_length',lambda r:r[179]['parameters'].update(l='19.2u'))]:
        altered=copy.deepcopy(contract);by={r['native_id']:r for r in altered['device_records']};edit(by)
        reject(label,lambda:c.topology(altered,bound))
    tt=np.array([0.,1.,2.,3.,4.,5.,6.]);sig=np.array([.5,.25,.125,.5,.3,.2,.5])
    spans=c.intervals(tt,sig,1.,.4)
    assert [(p['first'],p['last'],p['worst'],p['before'],p['after'])for p in spans]==[(1,2,2,0,3),(4,5,5,3,6)]
    assert sum(p['native_rows']for p in spans)==4;positive.append('all_noncontiguous_native_violation_rows')
    assert c.intervals(tt,np.ones(7),1.,.4)==[];positive.append('explicit_no_violation_intervals')
    assert spans[0]['left_censored_at_analysis_start']is True
    assert spans[0]['entry_threshold_bracket_inside_analysis']is False
    assert spans[0]['before_v']==.5 and spans[0]['first_v']==.25 and spans[0]['last_v']==.125 and spans[0]['after_v']==.5
    assert spans[0]['first_analysis_row']==1 and spans[0]['first_analysis_row_s']==1.
    assert spans[1]['left_censored_at_analysis_start']is False and spans[1]['right_censored_at_capture_end']is False
    assert spans[1]['entry_threshold_bracket_inside_analysis']is True and spans[1]['exit_threshold_bracket_inside_capture']is True
    positive.append('START_censor_not_mislabeled_threshold_bracket')
    both=c.intervals(tt,np.full(7,.25),1.5,.4)[0]
    assert (both['first'],both['last'],both['before'],both['after'])==(2,6,1,None)
    assert both['left_censored_at_analysis_start']is True and both['right_censored_at_capture_end']is True
    assert both['first_s']==2. and both['analysis_start_s']==1.5 and both['before_s']==1.
    assert both['before_v']==both['first_v']==both['last_v']==both['capture_end_v']==.25
    assert both['after_s']is None and both['after_v']is None
    assert not both['entry_threshold_bracket_inside_analysis']and not both['exit_threshold_bracket_inside_capture']
    positive.append('both_censored_between_samples_and_capture_end')
    right=c.intervals(tt,np.array([.5,.5,.5,.3,.2,.1,.25]),1.,.4)[0]
    assert right['left_censored_at_analysis_start']is False and right['right_censored_at_capture_end']is True
    assert right['before_s']==2. and right['before_v']==.5 and right['first_v']==.3 and right['last_v']==.25
    at_zero=c.intervals(tt,np.full(7,.25),0.,.4)[0]
    assert at_zero['before']is None and at_zero['before_s']is None and at_zero['before_v']is None and at_zero['left_censored_at_analysis_start']is True
    assert c.intervals(tt,np.full(7,.25),7.,.4)==[]
    positive.append('right_only_capture_start_and_empty_window_boundaries')
    b=c.budget(.875,1.25,.625,1.5,1.125,2.)
    assert b['VCE_v']==.25 and b['supply_to_upper_C_v']==.5 and b['upper_VCE_v']==.375 and b['upper_E_to_target_C_access_v']==.25
    assert b['reconstruction_v']==.25 and b['required_VCE_recovery_to_original_0p4_v']==.4-.25
    positive.append('same_row_headroom_identity')
    reject('nonfinite_budget',lambda:c.budget(float('nan'),1.,0.,2.,1.,2.5))
    names=c.names_for(records,selected,bound);d={n:np.arange(7,dtype=float)/16 for n in names}
    for i in selected:
        cv=c.current_vector(records[i])
        if cv:d[cv]=np.arange(7,dtype=float)*(i+1)/1024
    values=c.current_sum(d,records,[61,62])
    assert np.array_equal(values,d[c.current_vector(records[61])]+d[c.current_vector(records[62])])
    reject('duplicate_parallel_current',lambda:c.current_sum(d,records,[61,61]))
    reject('invented_resistor_current',lambda:c.current_sum(d,records,[179]))
    positive.append('instantaneous_parallel_sum')
    f=c.frame(tt,d,3,records,branches,selected,bound)
    assert f['row']==3 and f['time_s']==3. and len(f['headroom_paths'])==8
    for path in f['headroom_paths']:
        assert path['currents']['cn_Ic_a']==sum(d[c.current_vector(records[i])][3]for i in next(x for x in branches if x['name']==path['branch'])['cn'])
        assert path['bleed_current_a']is None and path['complete_KCL']is False
    positive.append('actual_topology_same_row_frame')
    with tempfile.TemporaryDirectory()as td:
        p=Path(td);diagnosis=dict(selected_native_ids=selected,frame_rows=[1,3,5])
        meta=c.write_frames(p/'frames.jsonl',tt,d,diagnosis,native,contract)
        frames=[json.loads(line)for line in (p/'frames.jsonl').read_text().splitlines()]
        assert meta['rows']==3 and [x['row']for x in frames]==[1,3,5]
        cache=rows.cache(p/'cache.bin',tt,d,names);assert cache['rows']==7
        raw=bytearray((p/'cache.bin').read_bytes());raw[-1]^=1;(p/'cache.bin').write_bytes(raw)
        reject('changed_native_cache_byte',lambda:rows.verify_cache(p/'cache.bin',tt,d,cache))
    positive.append('actual_JSONL_and_bit_exact_cache')
    reject('local_archive_readback',lambda:a.cloud_guard({**m,'readback_authorized':False}))
    # These archives are synthetic bytes created only in hosted source controls.
    # The actual extractor hashes even unselected members before discarding them.
    with tempfile.TemporaryDirectory()as td:
        base=Path(td);data={p:('fixture:'+p).encode()for p in a.SELECT}
        data.update({'result.json':b'{}','hidden/.empty':b'','unselected.bin':b'complete'})
        expected={p:hashlib.sha256(b).hexdigest()for p,b in data.items()if p!='result.json'}
        def archive_case(label):
            folder=base/label;folder.mkdir();payload=io.BytesIO()
            entries=list(data.items())
            if label=='missing_selected':entries=[x for x in entries if x[0]!='native/wave.raw']
            if label=='missing_unselected':entries=[x for x in entries if x[0]!='unselected.bin']
            if label=='unexpected':entries.append(('unknown',b'x'))
            if label=='duplicate':entries.append(entries[0])
            if label=='path_escape':entries.append(('../escape',b'x'))
            with tarfile.open(fileobj=payload,mode='w:gz')as tar:
                for p,b in entries:
                    nm=('other/'if label=='wrong_root'else'fixture/')+p
                    item=tarfile.TarInfo(nm);item.size=len(b)
                    if label=='unselected_bytes'and p=='unselected.bin':b=b'changed!';item.size=len(b)
                    if label=='changed_selected'and p=='native/wave.raw':b=b'changed';item.size=len(b)
                    if p=='native/wave.raw'and label in ('symlink','hardlink','fifo'):
                        item.type={'symlink':tarfile.SYMTYPE,'hardlink':tarfile.LNKTYPE,'fifo':tarfile.FIFOTYPE}[label];item.linkname='elsewhere';item.size=0
                    tar.addfile(item,io.BytesIO(b)if item.isfile()else None)
            raw=payload.getvalue();parts=[]
            for i,start in enumerate(range(0,len(raw),127)):
                b=raw[start:start+127];n='fixture.tar.gz.part'+str(i).zfill(4);(folder/n).write_bytes(b)
                parts.append(dict(index=i,name=n,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
            manifest=dict(format='ordered-tar-gzip-parts-v1',stem='fixture',source_directory='fixture',parts=parts,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            if label=='corrupt_part':
                p=folder/parts[0]['name'];b=bytearray(p.read_bytes());b[-1]^=1;p.write_bytes(b)
            return manifest,folder
        manifest,folder=archive_case('positive')
        proof=a.extract(manifest,folder,folder/'saved',dict(outputs=expected),hashlib.sha256(b'{}').hexdigest())
        assert proof['all_member_hashes_verified']==len(data)and len(proof['selected'])==len(a.SELECT)+1
        assert (folder/'saved/native/wave.raw').read_bytes()==data['native/wave.raw']
        positive.append('real_complete_multipart_extractor')
        for label in ('missing_selected','missing_unselected','unselected_bytes','changed_selected','unexpected','duplicate','symlink','hardlink','fifo','path_escape','wrong_root','corrupt_part'):
            manifest,folder=archive_case(label)
            reject('archive_'+label,lambda:a.extract(manifest,folder,folder/'saved',dict(outputs=expected),hashlib.sha256(b'{}').hexdigest()))
    assert len(positive)==16 and len(negative)==47,(positive,negative)
    return dict(status='PASS_SOURCE_FIXTURES_NOT_CAPTURE_ANALYSIS',positive=positive,rejected=negative,
        positives=len(positive),refusals=len(negative),actual_capture_read=False,simulation=False)
if __name__=='__main__':print(json.dumps(controls(),indent=2))
