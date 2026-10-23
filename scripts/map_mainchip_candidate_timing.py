#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read actual candidate cell connections; do not infer RTL equivalence from names."""
import re
def map_endpoints(path, corners):
    text=path.read_text()
    lines=text.splitlines()
    targets=sorted({p[k] for c in corners.values() for mode in c.values()
                    for p in mode['paths'] for k in ('Startpoint','Endpoint')
                    if p[k].startswith('$auto$ff.cc:')})
    assert targets
    result={}
    for name in targets:
        pattern=re.compile(r'^\s*(\S+)\s+\\'+re.escape(name)+r'\s*\(')
        found=[(i,pattern.match(line)) for i,line in enumerate(lines) if pattern.match(line)]
        assert len(found)==1,('Expected one exact native endpoint cell',name,len(found))
        i,m=found[0]
        end=next((j for j in range(i,min(i+80,len(lines))) if re.search(r'\)\s*;\s*$',lines[j])),None)
        assert end is not None,('Unterminated native cell',name)
        raw='\n'.join(lines[i:end+1])
        pairs=re.findall(r'\.([A-Za-z0-9_]+)\s*\(\s*([^()]*)\s*\)',raw)
        pins=dict(pairs)
        assert len(pairs)==len(pins),('Repeated pins or merged cell records',name)
        pins={k:v.strip() for k,v in pins.items()}
        assert 'D' in pins and 'Q' in pins and 'CLK' in pins,(name,pins)
        result[name]={'cell_type':m.group(1),'line':i+1,'native_instance_text':raw,
                      'connections':pins,'exact_assignment_aliases':[]}
    assignments=[]
    for i,line in enumerate(lines):
        m=re.match(r'^\s*assign\s+(.+?)\s*=\s*(.+?)\s*;\s*$',line)
        if m:assignments.append((i+1,m.group(1).strip(),m.group(2).strip(),line))
    for name,row in result.items():
        nets=set(row['connections'].values())
        row['exact_assignment_aliases']=[{'line':i,'native_text':raw}
            for i,lhs,rhs,raw in assignments if lhs in nets or rhs in nets]
    return {'endpoint_count':len(result),'cells':result,
            'scope':'Literal exact candidate cell ports and directly matching assignment sides. This is source mapping, not an RTL functional proof, CDC waiver or final timing result.'}
