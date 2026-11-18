#!/usr/bin/env python3
"""Classify current core-only unannotated drivers without legacy design counts.

Diagnostic only; no disconnected/loaded driver is waived. Run in pinned native
OpenROAD with hash-bound ODB, SPEF and standalone STA log supplied by producer.
"""
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import re

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def annotation_groups(text):
    assert len(re.findall(r'(?m)^Found \d+ unannotated drivers\.',text))==1
    assert len(re.findall(r'(?m)^Found \d+ partially unannotated drivers\.',text))==1
    match=re.search(r'(?m)^Found (\d+) unannotated drivers\.\s*\n(.*?)^Found (\d+) partially unannotated drivers\.[ \t]*\n?',text,re.S)
    assert match,'Missing native annotation sections'
    full=[x.strip()for x in match[2].splitlines()if x.strip()]
    assert len(full)==int(match[1])and len(full)==len(set(full))
    partial={};current=None
    for line in text[match.end():].splitlines():
        if not line.strip():continue
        if re.fullmatch(r' [^\s].*',line):
            current=line[1:];assert current not in partial and current not in full;partial[current]=[]
        elif re.fullmatch(r'  [^\s].*',line):
            assert current is not None,'Missing load without driver';load=line[2:];assert load not in partial[current];partial[current].append(load)
        else:break
    assert len(partial)==int(match[3]),('Partial driver count mismatch',len(partial),int(match[3]))
    assert all(partial.values()),'Partial driver without missing loads'
    return full,partial

def controls():
    text='Found 2 unannotated drivers.\n a\n b/Y\nFound 1 partially unannotated drivers.\n c/X\n  d/A\n  e/A\nEND\n'
    assert annotation_groups(text)==(['a','b/Y'],{'c/X':['d/A','e/A']})
    zero='Found 0 unannotated drivers.\nFound 0 partially unannotated drivers.\nEND\n'
    assert annotation_groups(zero)==([],{})
    faults=[text.replace('Found 2','Found 3'),text.replace(' b/Y',' a'),text.replace('Found 1 partially','Found 2 partially'),text.replace(' c/X',' a'),text.replace('  e/A','  d/A'),text.replace(' c/X\n',''),text.replace('  d/A\n  e/A\n','')]
    for bad in faults:
        try:annotation_groups(bad)
        except AssertionError:continue
        raise AssertionError('Malformed native annotation accepted')
    return dict(positive=2,negative=len(faults),partial_load_inventory_checked=True)

def spef_net_name(name):
    # Exact extSpef::addEscChar(name, false), pinned OpenROAD dcf36133.
    # Already escaped literal brackets must not be unescaped into bus indexes.
    assert name.isascii()
    return ''.join(('\\' if not ch.isalnum() and ch not in '_\\/[]' and (i==0 or name[i-1]!='\\') else '')+ch for i,ch in enumerate(name))

def name_controls():
    pairs=[('bus[2]','bus[2]'),(r'bus\[2\]',r'bus\[2\]'),('$a.b:c',r'\$a\.b\:c'),('path/a','path/a'),(r'\$a',r'\$a')]
    # Literal escaped brackets and true bus indexes remain distinct.
    for source,expected in pairs:assert spef_net_name(source)==expected,(source,expected,spef_net_name(source))
    assert spef_net_name(pairs[0][0])!=spef_net_name(pairs[1][0])
    return dict(exact_native_writer_cases=len(pairs),literal_brackets_distinct=True)

def classify(odb_path, spef_path, log_path, output):
    import odb
    d=odb.dbDatabase.create();odb.read_db(d,str(odb_path));b=d.getChip().getBlock()
    assert b and len(b.getInsts()) > 0 and len(b.getNets()) > 0
    nets={n.getName():n for n in b.getNets()};namemap={};caps={};inmap=False;aliases=collections.Counter()
    encoded={}
    for original in nets:
        name=spef_net_name(original)
        assert name not in encoded,('Ambiguous exact SPEF name',name)
        encoded[name]=original
    def resolve(token,name):
        assert re.fullmatch(r'\*\d+',token),('Expected native name map token',token)
        ident=int(token[1:]);assert ident>0
        # LibreLane RCX reads DEF, rebuilding numeric dbNet IDs. They are local
        # SPEF name-map keys, not persistent identifiers of the routed ODB.
        assert name in encoded,('Unknown exact SPEF net name',token,name)
        chosen=encoded[name];assert spef_net_name(chosen)==name
        aliases['unique_exact_writer_name_after_DEF_roundtrip']+=1;return chosen
    with spef_path.open() as stream:
        for line in stream:
            row=line.strip()
            if row=='*NAME_MAP':inmap=True;continue
            if inmap:
                m=re.fullmatch(r'(\*\d+)\s+(.+)',row)
                if m:assert m[1] not in namemap;namemap[m[1]]=m[2];continue
                if row.startswith('*'):inmap=False
            if row.startswith('*D_NET '):
                fields=row.split();assert len(fields)==3
                token=fields[1];n=resolve(token,namemap[token]);assert n not in caps;caps[n]=float(fields[2]);assert math.isfinite(caps[n]) and caps[n]>=0
    assert caps, 'No extracted SPEF nets'
    full,partial=annotation_groups(log_path.read_text())
    names=full+list(partial)
    rows=[]
    for name in names:
        term=b.findBTerm(name)
        if term:kind='boundary';io=str(term.getIoType());net=term.getNet();master=None
        else:
            inst,pin=name.rsplit('/',1);i=b.findInst(inst);assert i,('Missing driver instance',name)
            term=i.findITerm(pin);assert term,('Missing driver pin',name)
            kind='instance';io=str(term.getIoType());net=term.getNet();master=i.getMaster().getName()
        assert io in (('INPUT','INOUT') if kind=='boundary' else ('OUTPUT','INOUT')),('Not a driver',name,io)
        row=dict(driver=name,kind=kind,io=io,master=master,net=None if not net else net.getName(),annotation_kind='partial'if name in partial else 'unannotated',native_missing_loads=partial.get(name,[]))
        if not net:row.update(category='DISCONNECTED_DRIVER',sinks=[],spef_present=False)
        else:
            n=net.getName();terminals=[]
            for t in net.getITerms():terminals.append(dict(name=t.getInst().getName()+'/'+t.getMTerm().getName(),kind='instance',io=str(t.getIoType())))
            for t in net.getBTerms():terminals.append(dict(name=t.getName(),kind='boundary',io=str(t.getIoType())))
            sinks=[t['name'] for t in terminals if t['name']!=name and t['io'] in (('INPUT','INOUT') if t['kind']=='instance' else ('OUTPUT','INOUT'))]
            wire=net.getWire()
            category='CONNECTED_NO_SINK' if not sinks else 'LOADED_PRESENT_IN_SPEF_UNANNOTATED' if n in caps else 'LOADED_ABSENT_FROM_SPEF'
            row.update(category=category,sinks=sinks,terminals=terminals,spef_present=n in caps,spef_d_net_cap=caps.get(n),signal_type=str(net.getSigType()),wire_present=bool(wire),wire_length_dbu=wire.getLength() if wire else None)
        row['native_missing_loads_not_in_exact_odb_sinks']=sorted(set(row['native_missing_loads'])-set(row['sinks']))
        rows.append(row)
    counts=dict(collections.Counter(r['category'] for r in rows));loaded=[r for r in rows if r['sinks']]
    output.write_text(json.dumps(dict(status='COMPLETE_SOURCE_BOUND_ANNOTATION_DIAGNOSIS_NOT_COVERAGE_ACCEPTANCE',accepted=False,database_instances=len(b.getInsts()),database_nets=len(b.getNets()),checked=len(rows),fully_unannotated_drivers=len(full),partially_unannotated_drivers=len(partial),native_missing_loads=sum(map(len,partial.values())),unresolved_native_load_names=sum(len(r['native_missing_loads_not_in_exact_odb_sinks'])for r in rows),counts=counts,loaded_unannotated_drivers=len(loaded),spef_nets=len(caps),spef_name_resolution=dict(aliases),drivers=rows,scope='Descriptive native OpenSTA driver classification against exact routed ODB terminals and extracted SPEF D_NET inventory. No missing loaded net is waived. Disconnected outputs alone do not prove unused functional interfaces or complete timing coverage.'),indent=2)+'\n')
    print(json.dumps(dict(counts=counts,loaded_unannotated_drivers=len(loaded))),flush=True)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    manifest=Path(os.environ['NSSOC_CORE_ANNOTATION_INPUTS'])
    spec=json.loads(manifest.read_text())
    assert set(spec)=={'odb','spef','sta_log','output'}
    paths={}
    for kind in ('odb','spef','sta_log'):
        row=spec[kind];assert set(row)=={'path','sha256'}
        path=Path(row['path']).resolve();assert path.is_file()
        assert sha(path)==row['sha256'],kind
        paths[kind]=path
    output=Path(spec['output']);assert not output.exists()
    control_result=dict(annotation=controls(),spef_names=name_controls())
    classify(paths['odb'],paths['spef'],paths['sta_log'],output)
    assert all(sha(paths[k])==spec[k]['sha256'] for k in paths)
    result=json.loads(output.read_text())
    result.update(inputs=spec,inputs_unchanged=True,controls=control_result,
        source_sha256=sha(Path(__file__)))
    output.write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
