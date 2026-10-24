#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Restore only an equivalent native coupling-record order for regression.

Never edits any capacitance value or native RC output. Symmetric endpoints
and record identifiers are not electrical differences.
"""
import hashlib,json,shlex,sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
def rows(text):return [shlex.split(s) for s in text.splitlines() if s.strip()]
def capkey(row):
    assert row[0]=='cap' and len(row)==4
    return (*sorted(row[1:3]),Decimal(row[3]))
def reorder(current,historical):
    a,b=rows(current),rows(historical)
    ac=[r for r in a if r[0]=='cap'];bc=[r for r in b if r[0]=='cap']
    assert Counter(map(capkey,ac))==Counter(map(capkey,bc)),'Coupling endpoints/values differ'
    for kind in ('node','port','equiv','substrate'):
        assert [r for r in a if r[0]==kind]==[r for r in b if r[0]==kind],('Non-coupling source changed',kind)
    original=[s for s in historical.splitlines() if s.strip() and shlex.split(s)[0]=='cap']
    it=iter(original);out=[]
    for s in current.splitlines():
        out.append(next(it) if s.strip() and shlex.split(s)[0]=='cap' else s)
    assert next(it,None) is None
    result='\n'.join(out)+'\n'
    assert [r for r in rows(result) if r[0]=='cap']==bc
    assert [s for s in result.splitlines() if not s.strip() or shlex.split(s)[0]!='cap']==[s for s in current.splitlines() if not s.strip() or shlex.split(s)[0]!='cap']
    return result,dict(coupling_records=len(ac),symmetric_endpoint_value_multiset_exact=True,non_coupling_records_unchanged=True,original_order_restored=True)
def controls():
    old='node "p" 0 1\nnode "q" 0 2\ncap "p" "q" 3\ncap "q" "p" 4\n'
    new='node "p" 0 1\nnode "q" 0 2\ncap "p" "q" 4\ncap "q" "p" 3\n'
    out,proof=reorder(new,old);assert out==old
    tests={'missing':new.replace('cap "p" "q" 4\n',''),'value':new.replace('"q" 4','"q" 5'),'endpoint':new.replace('"q" 4','"r" 4'),'node':new.replace('"p" 0 1','"p" 0 9')}
    for name,value in tests.items():
        try:reorder(value,old)
        except AssertionError:pass
        else:raise AssertionError('Accepted '+name)
    return list(tests)
if __name__=='__main__':
    if sys.argv[1:] == ['--controls']:print(json.dumps(dict(positive=True,rejected=controls())));sys.exit(0)
    current,historical=map(Path,sys.argv[1:]);a=current.read_text();b=historical.read_text();out,proof=reorder(a,b)
    proof.update(current_sha256=hashlib.sha256(a.encode()).hexdigest(),historical_sha256=hashlib.sha256(b.encode()).hexdigest(),reordered_sha256=hashlib.sha256(out.encode()).hexdigest())
    current.with_suffix('.fresh-order.ext').write_text(a)
    current.write_text(out)
    current.with_suffix('.order-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
