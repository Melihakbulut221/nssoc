#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read every native OP column, including simulator-internal nodes and currents."""
import copy,hashlib,re
import numpy as np
def read(raw,required):
    marker=b'Binary:\n';offset=raw.find(marker,0,1048576)
    assert offset>=0,'Missing native binary header'
    offset+=len(marker);h=raw[:offset].decode('ascii')
    def field(key):
        values=[l.split(':',1)[1].strip()for l in h.splitlines()if l.startswith(key+':')]
        assert len(values)==1,('Missing/duplicate field',key)
        return values[0]
    assert field('Flags')=='real'and field('Plotname').lower()=='operating point'
    assert int(field('No. Points'))==1
    assert h.count('Variables:\n')==1
    table=[l.split()for l in h.split('Variables:\n',1)[1].split('Binary:\n',1)[0].splitlines()]
    width=int(field('No. Variables'))
    assert width==len(table)and all(len(x)==3 for x in table)
    assert [x[0]for x in table]==list(map(str,range(width)))
    names=[x[1]for x in table]
    assert len(names)==len(set(names))and len(required)==len(set(required))
    assert set(required)<=set(names),'Missing required native terminal voltage'
    assert all(re.fullmatch(r'v\([^()]+\)',n)for n in required)
    for _,name,kind in table:
        assert kind in ('voltage','current')
        prefix='v('if kind=='voltage'else'i('
        assert name.startswith(prefix)and name.endswith(')')and not any(c.isspace()for c in name),(name,kind)
        inner=name[2:-1];assert inner
        depth=0
        for c in inner:
            if c=='(':depth+=1
            elif c==')':depth-=1
            assert depth>=0,('Unbalanced native name',name)
        assert depth==0,('Unbalanced native name',name)
        if name in required:assert kind=='voltage'
    assert len(raw)-offset==width*8,'Truncated/extra native OP payload'
    values=np.frombuffer(raw[offset:],dtype='<f8')
    assert np.isfinite(values).all(),'Nonfinite native OP value'
    maxima={}
    counts={}
    for kind,limit in (('voltage',1e-9),('current',1e-12)):
        ids=[i for i,x in enumerate(table)if x[2]==kind];counts[kind]=len(ids)
        assert ids
        maximum=float(np.max(np.abs(values[ids])));maxima[kind]=maximum
        assert maximum<limit,('Nonzero zero-source OP',kind,maximum,limit)
    return dict(status='PASS_ALL_REQUIRED_TERMINALS_AND_EVERY_NATIVE_ZERO_SOURCE_OP_COLUMN',
       required_terminal_voltages=len(required),native_columns=width,counts=counts,max_abs=maxima,
       additional_native_columns=width-len(required),every_column_finite_and_checked=True,
       voltage_limit_v=1e-9,current_limit_a=1e-12,raw_sha256=hashlib.sha256(raw).hexdigest(),
       biased_operation_or_lock_accepted=False)
def controls(raw,required):
    read(raw,required)
    offset=raw.index(b'Binary:\n')+len(b'Binary:\n');h=raw[:offset].decode('ascii')
    table=[l.split()for l in h.split('Variables:\n',1)[1].split('Binary:\n',1)[0].splitlines()]
    names=[x[1]for x in table];values=np.frombuffer(raw[offset:],dtype='<f8').copy()
    cases=[]
    def payload(name,idx,value):
        a=values.copy();a[idx]=value;cases.append((name,raw[:offset]+a.tobytes()))
    payload('nonzero_required_voltage',names.index(required[0]),1e-3)
    payload('nonzero_extra_voltage',next(i for i,x in enumerate(table)if x[2]=='voltage'and x[1]not in required),1e-3)
    payload('nonzero_native_current',next(i for i,x in enumerate(table)if x[2]=='current'),1e-6)
    payload('nonfinite_extra_node',next(i for i,x in enumerate(table)if x[1]not in required),float('nan'))
    cases+=[('truncated_payload',raw[:-1]),('extra_payload',raw+b'x'),
     ('missing_required_identity',h.replace(required[0],'v(FAULT_MISSING_TERMINAL)',1).encode()+raw[offset:]),
     ('duplicate_identity',h.replace(names[1],names[0],1).encode()+raw[offset:]),
     ('wrong_point_count',h.replace('No. Points: 1','No. Points: 2',1).encode()+raw[offset:]),
     ('wrong_unit',h.replace('voltage','current',1).encode()+raw[offset:])]
    nested=next(n for n in names if '('in n[2:-1])
    cases.append(('unbalanced_native_internal_name',h.replace(nested,nested[:-1],1).encode()+raw[offset:]))
    cases.append(('extra_closing_native_internal_name',h.replace(nested,nested+')',1).encode()+raw[offset:]))
    result=[]
    for name,data in cases:
        assert data!=raw
        try:read(data,required)
        except (AssertionError,ValueError):result.append(dict(name=name,rejected=True))
        else:raise AssertionError('Accepted '+name)
    assert len(result)==12
    return result
