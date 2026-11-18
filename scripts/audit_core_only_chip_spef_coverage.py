#!/usr/bin/env python3
"""Exact parent ODB/SPEF terminal inventory and resistance graph diagnostic."""
import os,json,re,math,hashlib
from pathlib import Path
from collections import Counter

def escaped(name,instance=False):
    assert name.isascii()
    return ''.join(('\\' if not ch.isalnum() and ch not in '_\\/' and (instance or ch not in '[]') and (i==0 or name[i-1]!='\\') else '')+ch for i,ch in enumerate(name))

def parse(path):
    mapping={};nets={};current=None;section=None;inmap=False;delimiter=None
    for line in path.read_text().splitlines():
        fields=line.split()
        if not fields:continue
        key=fields[0]
        if key=='*DELIMITER':assert fields==['*DELIMITER',':'];delimiter=':'
        if key=='*NAME_MAP':inmap=True;continue
        if inmap:
            if re.fullmatch(r'\*\d+',key):
                assert len(fields)==2 and key not in mapping;mapping[key]=fields[1];continue
            inmap=False
        if key=='*D_NET':
            assert current is None and len(fields)==3 and key not in nets
            token=fields[1];assert token in mapping and token not in nets
            value=float(fields[2]);assert math.isfinite(value)and value>=0
            current=dict(token=token,conn=[],res=[],name=mapping[token]);nets[token]=current;section=None
        elif key in ('*CONN','*CAP','*RES'):
            assert current is not None;section=key
        elif key=='*END':assert current is not None;current=None;section=None
        elif current and section=='*CONN':
            assert key in ('*I','*P')and len(fields)>=3
            token=fields[1];direction=fields[2];assert direction in ('I','O','B')
            if key=='*I':
                match=re.fullmatch(r'(\*\d+):(.+)',token);assert match and match[1]in mapping
                terminal=mapping[match[1]]+':'+match[2]
            else:terminal=token
            current['conn'].append((key,terminal,direction,token))
        elif current and section=='*RES':
            assert len(fields)==4 and fields[0].isdigit()
            value=float(fields[3]);assert math.isfinite(value)and value>=0
            current['res'].append((fields[1],fields[2],value))
    assert delimiter==':'and current is None and nets
    return nets

def connected(terminals,edges):
    parent={}
    def root(x):
        parent.setdefault(x,x)
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    for a,b,_ in edges:parent[root(a)]=root(b)
    roots={root(t)for t in terminals}
    allroots={root(t)for t in list(parent)}
    return len(roots)<=1 and len(allroots)<=1

def main():
    import odb
    out=Path(os.environ['NSSOC_SPEF_COVERAGE_OUT']);odbpath=out/'chip-detailedroute.odb';spef=out/'chip-shell.nom.spef'
    protected={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [odbpath,spef,Path(__file__)]}
    db=odb.dbDatabase.create();odb.read_db(db,str(odbpath));b=db.getChip().getBlock();parsed=parse(spef)
    inventory={};unwired=[];single=[]
    for net in b.getNets():
        if str(net.getSigType())in ('POWER','GROUND'):continue
        name=escaped(net.getName());assert name not in inventory
        terms=[]
        for t in net.getITerms():terms.append(('*I',escaped(t.getInst().getName(),True)+':'+escaped(t.getMTerm().getName()),str(t.getIoType())[0]))
        for t in net.getBTerms():terms.append(('*P',escaped(t.getName()),str(t.getIoType())[0]))
        inventory[name]=dict(name=net.getName(),terms=terms,wire=bool(net.getWire()))
        if not net.getWire()and len(terms)>1:unwired.append(net.getName())
        if len(terms)<=1:single.append(net.getName())
    missing=[];extra=[];mismatch=[];disconnected=[];present=set();faults={}
    for token,data in parsed.items():
        name=data['name'];assert name not in present;present.add(name)
        if name not in inventory:extra.append(name);continue
        native=odb.dbNet.getNet(b,int(token[1:]));assert native and escaped(native.getName())==name
        expected=Counter(inventory[name]['terms']);actual=Counter(x[:3]for x in data['conn'])
        if expected!=actual:mismatch.append(dict(net=name,missing=list((expected-actual).elements()),extra=list((actual-expected).elements())))
        if not connected([x[3]for x in data['conn']],data['res']):disconnected.append(name)
        if not faults and len(data['conn'])>1 and expected==actual and connected([x[3]for x in data['conn']],data['res']):
            assert Counter(x[:3]for x in data['conn'][1:])!=expected
            assert not connected([x[3]for x in data['conn']],[])
            faults=dict(net=name,removed_terminal_detected=True,removed_all_resistors_detected=True)
    for name,row in inventory.items():
        if row['wire']and len(row['terms'])>1 and name not in present:missing.append(row['name'])
    expected_wired={name for name,row in inventory.items()if row['wire']and len(row['terms'])>1}
    assert expected_wired and faults
    victim=next(iter(expected_wired&present));assert victim in expected_wired-(present-{victim})
    faults['removed_routed_net_detected']=True
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
    report=dict(source_hashes=protected,inputs_unchanged=True,parsed_nets=len(parsed),expected_wired_multiterminal_nets=len(expected_wired),missing_wired_nets=missing,unexpected_spef_nets=extra,terminal_mismatches=mismatch,resistance_graph_disconnections=disconnected,unwired_multiterminal_nets=sorted(unwired),zero_or_one_terminal_nets=sorted(single),negative_controls=faults,accepted=False,scope='Parent-level SPEF net and terminal inventory plus resistor-graph continuity. Does not qualify RC accuracy, coupling symmetry, core internal parasitics, full-chip timing or manufacturing.')
    (out/'coverage.json').write_text(json.dumps(report,indent=2)+'\n')
    assert not missing and not extra and not mismatch and not disconnected,'Native ODB/SPEF coverage failed'
if __name__=='__main__':main()
