# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded saved-table reader; caller retains original safety/measurement gates."""
from contextlib import contextmanager
from pathlib import Path
import gzip,hashlib,shutil,tempfile
import numpy as np

CHUNK=1024**2
HEADER_LIMIT=4*1024**2
SSD_FLOOR=1024**3

def file_pin(path):
    path=Path(path)
    with path.open('rb')as stream:
        return dict(bytes=path.stat().st_size,sha256=hashlib.file_digest(stream,'sha256').hexdigest())

@contextmanager
def open_table(path, *, rows, columns, compressed_pin, raw_sha256, payload_sha256,
               raw_bytes, scratch_directory, scratch_limit):
    """Yield a read-only matrix mapped to an anonymous SSD temporary file.

    All bytes, labels, finite values, trailer and both digests are checked before
    yielding. A bounded payload is streamed once. No full raw/payload copies and
    no named temporary file survive either normal or exceptional context exit.
    """
    path=Path(path);directory=Path(scratch_directory).resolve()
    assert file_pin(path)==compressed_pin,'compressed input pin'
    assert isinstance(rows,int)and rows>0 and len(columns)>0 and len(set(columns))==len(columns),'shape'
    expected=rows*len(columns)*8
    assert expected<=scratch_limit,'scratch cap'
    assert directory.is_dir()and directory.stat().st_dev!=Path('/dev/shm').stat().st_dev,'SSD scratch filesystem'
    assert shutil.disk_usage(directory).free>=expected+SSD_FLOOR,'SSD entry floor'
    whole=hashlib.sha256();payload=hashlib.sha256();header=bytearray();matrix=None
    with tempfile.TemporaryFile(mode='w+b',dir=directory)as backing:
        assert backing.name is not None
        with gzip.open(path,'rb')as stream:
            while True:
                line=stream.readline(HEADER_LIMIT+1-len(header))
                assert line and len(header)+len(line)<=HEADER_LIMIT,'bounded native header'
                header.extend(line)
                if line==b'Binary:\n':break
            frozen_header=bytes(header)
            assert frozen_header.count(b'Variables:\n')==1,'variable declaration'
            lines=frozen_header.split(b'Variables:\n',1)[1].split(b'Binary:\n',1)[0].splitlines()
            parsed=[]
            for index,line in enumerate(lines):
                tokens=line.decode('ascii').split();assert len(tokens)==3 and int(tokens[0])==index,'column index'
                parsed.append(tokens[1])
            assert parsed==list(columns),'column labels'
            whole.update(frozen_header);remaining=expected
            while remaining:
                part=stream.read(min(CHUNK,remaining));assert part,'short payload'
                assert len(part)%8==0,'float alignment'
                assert np.isfinite(np.frombuffer(part,dtype='<f8')).all(),'nonfinite payload'
                whole.update(part);payload.update(part);backing.write(part);remaining-=len(part)
                assert backing.tell()<=scratch_limit,'scratch cap'
                assert shutil.disk_usage(directory).free>=SSD_FLOOR,'SSD continuous floor'
            trailer=stream.read(64)
            assert trailer==str(rows).encode('ascii'),'exact native trailer'
            assert stream.read(1)==b'','extra raw bytes'
            whole.update(trailer)
        assert len(frozen_header)+expected+len(trailer)==raw_bytes,'raw byte count'
        assert whole.hexdigest()==raw_sha256,'raw digest'
        assert payload.hexdigest()==payload_sha256,'payload digest'
        backing.flush();assert backing.tell()==expected
        assert shutil.disk_usage(directory).free>=SSD_FLOOR,'SSD terminal floor'
        matrix=np.memmap(backing,dtype='<f8',mode='r',shape=(rows,len(columns)))
        try:
            yield dict(matrix=matrix,header=frozen_header,columns=list(columns),rows=rows,
                       payload_bytes=expected,raw_sha256=whole.hexdigest(),payload_sha256=payload.hexdigest())
        finally:
            matrix._mmap.close()
    assert shutil.disk_usage(directory).free>=SSD_FLOOR,'SSD post-context floor'
