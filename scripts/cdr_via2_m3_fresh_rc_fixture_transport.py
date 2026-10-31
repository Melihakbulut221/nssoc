#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Lossless source-fixture log transport; never used for native input acquisition."""
import base64,hashlib,zlib
from pathlib import PurePosixPath
SCHEMA='fresh-rc-source-fixture-zlib-v1'

def require(value,message):
    if not value:raise ValueError(message)

def digest(raw):return hashlib.sha256(raw).hexdigest()

def path_name(path):
    require(type(path)is str and path.startswith('fresh-rc-controls/phase-fixtures/'),'explicit source fixture path')
    p=PurePosixPath(path)
    require(not p.is_absolute()and str(p)==path and all(x not in ('','..','.')and not x.startswith('.')for x in p.parts),'canonical fixture path')
    return path

def encode(path,raw):
    path=path_name(path);require(type(raw)is bytes,'exact source fixture bytes');raw.decode('utf-8',errors='strict')
    packed=zlib.compress(raw,6);parts=[packed[i:i+24000]for i in range(0,len(packed),24000)]
    index=dict(schema=SCHEMA,encoding='zlib+base64',path=path,bytes=len(raw),sha256=digest(raw),compressed_bytes=len(packed),compressed_sha256=digest(packed),chunks=len(parts))
    chunks=[dict(path=path,index=i,base64=base64.b64encode(b).decode('ascii'))for i,b in enumerate(parts)]
    return index,chunks

def decode(index,chunks):
    path=path_name(index['path']);require(index['schema']==SCHEMA and index['encoding']=='zlib+base64','exact fixture encoding')
    require(all(type(index[k])is int and index[k]>=0 for k in ('bytes','compressed_bytes','chunks'))and index['chunks']>0,'nonnegative declared lengths')
    require(type(chunks)is list and len(chunks)==index['chunks'],'complete chunk census')
    parts=[]
    for i,row in enumerate(chunks):
        require(row['path']==path and type(row['index'])is int and row['index']==i,'exact ordered chunk identity')
        parts.append(base64.b64decode(row['base64'],validate=True))
    packed=b''.join(parts);require(len(packed)==index['compressed_bytes']and digest(packed)==index['compressed_sha256'],'complete compressed bytes')
    inflater=zlib.decompressobj();raw=inflater.decompress(packed,index['bytes']+1)
    require(inflater.eof and not inflater.unused_data and not inflater.unconsumed_tail,'one complete zlib stream')
    require(len(raw)==index['bytes']and digest(raw)==index['sha256'],'complete original fixture bytes')
    raw.decode('utf-8',errors='strict');return raw
