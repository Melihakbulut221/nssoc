#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reverse only native coupling-record enumeration before native RC extraction."""
import hashlib,json,shlex,sys
from pathlib import Path
from tx_native_cap_order import reorder,controls
def reverse(text):
    caps=[s for s in text.splitlines()if s.strip()and shlex.split(s)[0]=='cap']
    assert len(caps)>1
    iterator=iter(reversed(caps))
    target='\n'.join(next(iterator)if s.strip()and shlex.split(s)[0]=='cap'else s for s in text.splitlines())+'\n'
    out,proof=reorder(text,target)
    assert out==target and next(iterator,None)is None
    proof['reversed_enumeration']=True
    return out,proof
if __name__=='__main__':
    if sys.argv[1:]==['--controls']:
        original='node "p" 0 1\nnode "q" 0 2\ncap "p" "q" 3\ncap "q" "p" 4\n'
        changed,_=reverse(original);again,_=reverse(changed)
        assert original==again and changed!=original
        print(json.dumps(dict(reversal_roundtrip=True,rejected=controls())));sys.exit(0)
    path=Path(sys.argv[1]);original=path.read_text();out,proof=reverse(original)
    proof.update(original_sha256=hashlib.sha256(original.encode()).hexdigest(),reordered_sha256=hashlib.sha256(out.encode()).hexdigest())
    path.with_suffix('.original-order.ext').write_text(original)
    path.write_text(out);path.with_suffix('.order-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
