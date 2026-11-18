#!/usr/bin/env python3
"""Check antenna instances in flat native Verilog, decoding scalar identifiers."""
import re

def identifier(expression):
    match=re.fullmatch(r'\s*\\([^\s]+)\s+',expression)
    if match:return match.group(1)
    plain=expression.strip()
    if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*',plain):return plain
    raise ValueError('Not one scalar Verilog identifier: '+repr(expression))

def check_added_antennas(text,cells):
    missing=[];mismatches=[];duplicates=[];matched=0
    indexed={}
    for master in sorted({c['master']for c in cells.values()}):
        pattern=r'\b'+re.escape(master)+r'\s+([A-Za-z_][A-Za-z0-9_$]*)\s*\((.*?)\);'
        for found in re.finditer(pattern,text,re.S):
            name=found.group(1)
            if name in cells and cells[name]['master']==master:indexed.setdefault(name,[]).append(found.group(2))
    for name,cell in cells.items():
        found=indexed.get(name,[])
        if not found:missing.append(name);continue
        if len(found)!=1:duplicates.append(name);continue
        pairs=re.findall(r'\.([A-Za-z_][A-Za-z0-9_$]*)\s*\(([^()]*)\)',found[0])
        assert len(pairs)==len({k for k,v in pairs}),'Duplicate pin assignment'
        terms={k:identifier(v)for k,v in pairs}
        expected={t['pin']:t['net']for t in cell['signal_terms']}
        actual={k:v for k,v in terms.items()if k in expected}
        if actual!=expected:mismatches.append(dict(instance=name,expected=expected,actual=actual))
        matched+=1
    return dict(new_diodes_expected=len(cells),new_diodes_exported=matched,missing_diodes=missing,duplicate_diodes=duplicates,signal_connection_mismatches=mismatches)
