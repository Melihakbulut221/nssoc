#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed saved-diagnosis resource admission; never omit selected observations."""
import hashlib,json,os,traceback
from pathlib import Path
import numpy as np
import tx_phase_reset334_saved_diagnosis as old
MAX_FRAMES=8192
MAX_CROSSINGS=262144
MAX_WINDOW_ASSOCIATIONS=65536
MAX_INTERVALS=8192
MAX_JSON_BYTES=1536*1024**2
MAX_OUTPUT_BYTES=2048*1024**2
MAX_RESULT_BYTES=8*1024**2
FAILURE_RESERVE_BYTES=16*1024**2

class ResourceLimit(AssertionError):
    def __init__(self,record):
        self.record=dict(record,complete_diagnosis=False,accepted=False,partial_result_accepted=False)
        super().__init__(json.dumps(self.record,sort_keys=True))

def bound(label,value,limit,counts=None):
    assert type(value)is int and type(limit)is int and value>=0 and limit>0
    if value>limit:raise ResourceLimit(dict(resource=label,observed=value,supported_limit=limit,counts=counts or {}))

def mem_available():
    rows=[line.split()[1:]for line in Path('/proc/meminfo').read_text().splitlines()if line.startswith('MemAvailable:')]
    assert len(rows)==1 and rows[0][1:]==['kB']
    return int(rows[0][0])*1024

def output_files(root):
    files={}
    for p in root.iterdir():
        assert p.is_file()and not p.is_symlink(),'Only flat regular diagnostic outputs are admitted'
        files[p.name]=p.stat().st_size
    return files

def write(path,value):
    """Stream complete JSON; preserve a clearly incomplete fragment if a limit/error occurs."""
    path=Path(path);assert path.parent.is_dir()and not path.is_symlink()
    tmp=path.with_name(path.name+'.writing');partial=path.with_name(path.name+'.incomplete')
    assert not tmp.exists()and not partial.exists()
    existing=sum(output_files(path.parent).values())
    result=path.name=='result.json';limit=MAX_RESULT_BYTES if result else MAX_JSON_BYTES
    aggregate=MAX_OUTPUT_BYTES-FAILURE_RESERVE_BYTES
    size=0;digest=hashlib.sha256()
    try:
        with tmp.open('xb')as stream:
            for text in json.JSONEncoder(indent=2,allow_nan=False).iterencode(value):
                raw=text.encode('utf-8')
                bound('single_JSON_bytes',size+len(raw),limit)
                bound('aggregate_diagnostic_bytes',existing+size+len(raw),aggregate)
                stream.write(raw);digest.update(raw);size+=len(raw)
            bound('single_JSON_bytes',size+1,limit)
            bound('aggregate_diagnostic_bytes',existing+size+1,aggregate)
            stream.write(b'\n');digest.update(b'\n');size+=1
        tmp.replace(path)
    except BaseException:
        if tmp.exists():tmp.replace(partial)
        raise
    return dict(bytes=size,sha256=digest.hexdigest(),streamed_complete_JSON=True)

def file_evidence(root):
    records={}
    for name,size in sorted(output_files(root).items()):
        p=root/name;h=hashlib.sha256()
        with p.open('rb')as stream:
            for block in iter(lambda:stream.read(1024**2),b''):h.update(block)
        records[name]=dict(bytes=size,sha256=h.hexdigest())
    return records


def final_result(path,result):
    """Persist a complete terminal failure envelope if normal result encoding/admission fails."""
    path=Path(path);assert path.name=='result.json'
    try:
        proof=write(path,result)
        return dict(proof,terminal_failure_envelope=False)
    except BaseException as error:
        failure=dict(type=type(error).__name__,error=repr(error),traceback=traceback.format_exc())
    # Normal writes reserve space even for result.json and count old/new coexistence.
    # Keep both the last complete result and every incomplete fragment byte-exact.
    previous=path.with_name('result.previous.json')
    assert not previous.exists()
    if path.exists():path.replace(previous)
    files=file_evidence(path.parent)
    original={k:result.get(k)for k in ('error','traceback')}
    assert all(v is None or type(v)is str for v in original.values())
    envelope=dict(status='FAIL_INCOMPLETE_CURRENT_AVSS18_SAVED_CAPTURE_DIAGNOSIS',
      run_id=result['run_id'],source_head=result['source_head'],accepted=False,
      complete_diagnosis=False,partial_result_accepted=False,new_simulation=False,
      native_process_resumed=False,full_PHY_accepted=False,
      original_electrical_rejection_preserved=True,original_status=result.get('status'),
      original_failure=original,result_write_failure=failure,
      outputs={name:row['sha256']for name,row in files.items()},preserved_evidence=files,
      previous_complete_and_partial_bytes_preserved=True,observations_not_truncated_for_acceptance=True)
    assert type(envelope['run_id'])is int and type(envelope['source_head'])is str
    data=(json.dumps(envelope,indent=2,allow_nan=False)+'\n').encode()
    # A bounded emergency record uses only the pre-reserved space. Authored limit/
    # encoder failures are small; filesystem I/O failures are never reported as success.
    bound('terminal_failure_envelope_bytes',len(data),1024**2)
    bound('terminal_total_bytes',sum(row['bytes']for row in files.values())+len(data),MAX_OUTPUT_BYTES)
    tmp=path.with_name('result.failure-writing')
    assert not tmp.exists()and not path.exists()
    with tmp.open('xb')as stream:stream.write(data)
    tmp.replace(path)
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
      streamed_complete_JSON=False,terminal_failure_envelope=True)


def plan(t,values,c,replay,prior_names,targets,interval_fn,pairmap=None):
    """Enumerate exactly the unchanged frame selectors before allocating full state frames."""
    assert len(t)>=2 and len(set(prior_names))==len(prior_names)
    rows=set();crossings=0;window_count=0;interval_count=0
    active=np.flatnonzero(t>=old.START);assert len(active)
    original_pairmap=old.pairs(c)
    if pairmap is None:pairmap=original_pairmap
    else:
        assert type(pairmap)is dict and all(pairmap.get(k)==v for k,v in original_pairmap.items())
        assert len(pairmap)==len(original_pairmap)+12
        assert all(len(p)==2 and p[0]!=p[1]and all('v('+n+')'in c['vectors']for n in p)for p in pairmap.values())
    windows=[(e['fall_s']-old.UI,e['fall_s']+2*old.UI,e['fall_s'])
      for s in c['instances']for e in s['oracle']['first_falls']]
    def sample(at):rows.update(old.bracket(t,float(at))['rows'])
    for p,n in pairmap.values():
        y=values['v('+p+')']-values['v('+n+')']
        rows.update([int(np.argmin(y)),int(np.argmax(y)),int(active[np.argmin(y[active])]),int(active[np.argmax(y[active])])])
        for level in (-.1,0.,.1):
            count=int(np.count_nonzero(((y[:-1]<=level)&(y[1:]>level))|((y[:-1]>=level)&(y[1:]<level))))
            crossings+=count;bound('native_crossings',crossings,MAX_CROSSINGS)
            events=old.crossing_rows(t,y,level);assert len(events)==count
            for lo,hi,origin in windows:
                chosen=old.window_events(events,lo,hi,origin)
                window_count+=len(chosen);bound('first_fall_window_associations',window_count,MAX_WINDOW_ASSOCIATIONS)
                for event in chosen:rows.update(event['rows'])
    failed={n for n,r in replay['measurement']['hbt_safety'].items()if not r['passed']}
    assert failed==set(targets)
    for name in failed:
        spec=c['hbt'][name]
        cv,bv,ev,_=[np.zeros_like(t)if node=='0'else values['v('+node+')']for node in spec['terminals']]
        ce,be,ic=cv-ev,bv-ev,values['@q.'+name+'.qnpn13g2[ic]']/spec['nx']
        rows.update([int(active[np.argmin(ce[active])]),int(np.argmax(abs(ce))),
          int(np.argmax(abs(be))),int(np.argmax(abs(ic)))])
    for i in range(256):sample(old.START+(i+.5)*old.UI)
    for spec in c['instances']:
        for event in spec['oracle']['first_falls']:
            arm,fall=event['arm_s'],event['fall_s']
            for at in (arm,arm+c['timing']['clock_ramp_s'],fall,fall+old.UI/2,fall+old.UI,fall+2*old.UI):sample(at)
    for key in ('reset_assert_s','reset_release_s'):
        for dt in (0.,c['timing']['clock_ramp_s'],old.UI):sample(c['timing'][key]+dt)
    for name in prior_names:
        spec=c['hbt'][name];y=values['v('+spec['terminals'][0]+')']-values['v('+spec['terminals'][2]+')']
        rows.add(int(active[np.argmin(y[active])]))
        if name in targets:
            found=interval_fn(t,y);interval_count+=len(found)
            bound('tail_violation_intervals',interval_count,MAX_INTERVALS)
            for interval in found:
                for label in ('first','last','before','after'):
                    if interval[label]is not None:rows.add(interval[label]['row'])
    bound('complete_native_state_frames',len(rows),MAX_FRAMES)
    counts=dict(frames=len(rows),crossings=crossings,first_fall_window_associations=window_count,
      tail_violation_intervals=interval_count,raw_rows=len(t))
    # Deliberately conservative planning allowance, not a measured Python RSS guarantee.
    estimate=len(t)*(len(c['vectors'])+1)*8+len(rows)*1024**2+crossings*2048+window_count*4096+interval_count*2048+256*1024**2
    return dict(counts=counts,required_frame_rows=sorted(rows),estimated_required_available_bytes=estimate,
      memory_estimate_is_not_measured_peak_RSS=True,finite_input_bounds=dict(frames=len(t),
        crossings=len(pairmap)*3*(len(t)-1),intervals=len(targets)*((len(t)+1)//2)),
      supported=dict(frames=MAX_FRAMES,crossings=MAX_CROSSINGS,window_associations=MAX_WINDOW_ASSOCIATIONS,
        intervals=MAX_INTERVALS,single_JSON_bytes=MAX_JSON_BYTES,aggregate_output_bytes=MAX_OUTPUT_BYTES),
      exact_fixed_selectors_preserved=True,subsampling_or_truncation=False)

def admit_memory(plan,available):
    assert type(available)is int and available>0
    bound('estimated_available_memory',plan['estimated_required_available_bytes'],available,plan['counts'])
    return dict(available_bytes=available,planning_estimate_bytes=plan['estimated_required_available_bytes'],
      measured_peak_RSS=False)

def validate_frames(plan,frames,t):
    assert sorted(int(k)for k in frames)==plan['required_frame_rows'],'Resource plan/native frames differ'
    for key,row in frames.items():
        index=int(key);assert row['row']==index and row['time_s']==float(t[index]),'Resource frame/time binding changed'
    return True

def input_budget(native_sizes,op_inventory_bytes,op_archive_bytes):
    limits={'wave.raw':4331024984,'contract.json':1024**2,'bench.cir':1024**2,
      'native.log':1024**2,'op.raw':2*1024**2}
    assert set(native_sizes)==set(limits)
    assert native_sizes['wave.raw']==limits['wave.raw']
    assert op_inventory_bytes==672685609 and op_archive_bytes==262840889
    for name,size in native_sizes.items():bound('restored_'+name,size,limits[name])
    # Native parts + five retained files + OP part/inventory + small transport metadata.
    retained_bound=4051609570+sum(limits.values())+op_archive_bytes+op_inventory_bytes+3*1024**2
    # pack() streams gzip straight into parts, without a second complete archive copy.
    publication_bound=MAX_OUTPUT_BYTES*2+MAX_RESULT_BYTES+16*1024**2
    peak_bound=retained_bound+publication_bound
    assert peak_bound<16*1024**3
    return dict(native_retained_bytes=native_sizes,native_retained_limits=limits,
      native_archive_bytes=4051609570,OP_archive_bytes=op_archive_bytes,OP_extracted_bytes=op_inventory_bytes,
      input_supported_disk_bound_bytes=retained_bound,publication_additional_disk_bound_bytes=publication_bound,
      combined_supported_disk_bound_bytes=peak_bound,required_free_disk_bytes=16*1024**3,
      all_native_paths_under_RUNNER_TEMP=True,raw_or_input_archives_in_publication=False,
      gzip_and_filesystem_allowance_bytes=16*1024**2)
