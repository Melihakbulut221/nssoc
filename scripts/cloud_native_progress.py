#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Observe an unfinished native raw file; never validate or adopt its waveform."""
import json,math,os,struct,subprocess,time
from pathlib import Path

def progress(path,expected_columns):
    result=dict(status='DIAGNOSTIC_INCOMPLETE_CAPTURE_ONLY',accepted=False,complete=False)
    path=Path(path)
    if not path.exists():return dict(result,state='raw_not_created')
    with path.open('rb') as stream:
        lines=[];used=0
        while True:
            line=stream.readline(1048576);used+=len(line)
            if used>1048576 or not line or not line.endswith(b'\n'):
                return dict(result,state='header_incomplete_or_oversized')
            lines.append(line)
            if line==b'Binary:\n':break
        header=b''.join(lines).decode('ascii');offset=stream.tell()
        def field(key):
            matches=[line.split(':',1)[1].strip() for line in header.splitlines() if line.startswith(key+':')]
            assert len(matches)==1,'Missing/duplicate raw field'
            return matches[0]
        assert field('Flags')=='real' and field('Plotname')=='Transient Analysis'
        width=int(field('No. Variables'));assert width==expected_columns and width>=2
        table=header.split('Variables:\n');assert len(table)==2
        rows=[line.split() for line in table[1].split('Binary:\n')[0].splitlines()]
        assert len(rows)==width and rows[0]==['0','time','time']
        assert all(len(row)==3 and row[0]==str(i) for i,row in enumerate(rows))
        size=os.fstat(stream.fileno()).st_size;payload=size-offset;assert payload>=0
        count,partial=divmod(payload,width*8)
        result.update(observed_file_bytes=size,columns=width,complete_binary_rows_observed=count,trailing_partial_row_bytes=partial,header_declared_rows=field('No. Points'))
        if count<2:return dict(result,state='fewer_than_two_written_rows')
        def timestamp(index):
            stream.seek(offset+index*width*8);raw=stream.read(8);assert len(raw)==8
            value=struct.unpack('<d',raw)[0];assert math.isfinite(value)
            return value
        start,previous,last=timestamp(0),timestamp(count-2),timestamp(count-1)
        assert start==0 and 0<=previous<last,'Nonadvancing or invalid sampled timestamps'
        return dict(result,state='observed_written_prefix',last_written_time_s=last,previous_written_time_s=previous,not_all_rows_examined=True)

def monitored_run(args,case,env,preexec_fn,timeout,expected_columns):
    case=Path(case);started=time.monotonic();deadline=started+timeout;next_report=started
    def record(proc,event):
        row=dict(event=event,elapsed_s=time.monotonic()-started,pid=proc.pid,accepted=False,complete=False)
        try:row['raw_progress']=progress(case/'wave.raw',expected_columns)
        except (OSError,AssertionError,ValueError,UnicodeError) as error:row['progress_error']=repr(error)
        with (case/'progress.jsonl').open('a') as stream:stream.write(json.dumps(row,allow_nan=False)+'\n')
        print('NSSOC_NATIVE_PROGRESS '+json.dumps(row,allow_nan=False),flush=True)
    with (case/'run.log').open('w') as log:
        proc=subprocess.Popen(args,cwd=case,env=env,preexec_fn=preexec_fn,stdout=log,stderr=subprocess.STDOUT)
        try:
            while True:
                now=time.monotonic();remaining=deadline-now
                if now>=next_report:record(proc,'poll');next_report=now+300
                if remaining<=0:
                    proc.kill();proc.wait();record(proc,'native_timeout')
                    raise subprocess.TimeoutExpired(args,timeout)
                try:code=proc.wait(timeout=min(60,remaining))
                except subprocess.TimeoutExpired:continue
                record(proc,'native_exit');return subprocess.CompletedProcess(args,code)
        except BaseException:
            if proc.poll() is None:proc.kill();proc.wait()
            raise
