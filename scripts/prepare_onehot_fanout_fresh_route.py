#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Invalidate stale data wires only; audit exact non-wire physical DEF content."""
import hashlib,json,os,re
from pathlib import Path
import odb
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def split_def(text):
    before,tail=text.split('\nNETS ',1)
    heading,tail=tail.split('\n',1);body,after=tail.split('END NETS',1)
    records={};pending=[]
    for line in body.splitlines():
        if not line.strip():continue
        if line.lstrip().startswith('- '):
            assert not pending;pending=[line]
        else:
            assert pending;pending.append(line)
        if ';' in line:
            assert line.count(';')==1
            statement='\n'.join(pending);name=statement.split()[1]
            assert name not in records
            records[name]=statement;pending=[]
    assert not pending and int(heading.split()[0])==len(records)
    return before+'\nNETS '+heading+'\nEND NETS'+after,records
def without_route(statement):
    tokens=statement.split()
    if '+' not in tokens:return tokens
    hits=[i for i in range(len(tokens)-1)if tokens[i:i+2]==['+','ROUTED']]
    if not hits:return tokens
    assert len(hits)==1
    i=hits[0];assert '+' not in tokens[i+2:] and tokens[-1]==';','Unexpected trailing DEF clause'
    return tokens[:i]+[';']
def verify(before,after,removed):
    a,an=split_def(before);b,bn=split_def(after)
    assert a==b,'Non-NETS physical DEF changed'
    assert an.keys()==bn.keys(),'Native nets added/removed'
    for name in an:
        if name in removed:
            assert without_route(an[name])==bn[name].split(),('Non-wire content changed',name)
        else:assert an[name].split()==bn[name].split(),('Unrelated native net changed',name)
    assert set(removed)<=an.keys()
    return dict(native_nets=len(an),cleared_data_wires=len(removed),all_non_wire_physical_def_preserved=True,all_other_net_records_preserved=True)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    source=Path(os.environ['NSSOC_FRESH_ROUTE_SOURCE'])
    out=Path(os.environ['NSSOC_FRESH_ROUTE_OUT']);out.mkdir(exist_ok=False)
    original=sha(source);db=odb.dbDatabase.create();odb.read_db(db,str(source))
    block=db.getChip().getBlock();assert len(list(block.getInsts()))==152762
    before=out/'before.def';after=out/'after.def';odb.write_def(block,str(before))
    removed={};protected={}
    for net in block.getNets():
        w=net.getWire()
        if w is None:continue
        name=net.getName();kind=str(net.getSigType());wiretype=str(net.getWireType())
        if kind in ('POWER','GROUND','CLOCK')or wiretype=='FIXED':
            protected[name]=dict(kind=kind,wire_type=wiretype,length=w.getLength());continue
        assert wiretype=='ROUTED',(name,wiretype)
        removed[name]=dict(kind=kind,wire_type=wiretype,length=w.getLength())
        odb.dbWire.destroy(w);assert net.getWire()is None
    assert removed and 'clknet_3_5_0_pcie_clk_i' in protected
    for name,record in protected.items():
        net=block.findNet(name);assert net.getWire()is not None
        assert dict(kind=str(net.getSigType()),wire_type=str(net.getWireType()),length=net.getWire().getLength())==record
    odb.write_def(block,str(after))
    a,b=before.read_text(),after.read_text();proof=verify(a,b,removed)
    outside,nets=split_def(b)
    faults=[]
    # Real exported instance content, data connectivity and protected route each
    # have independent corruption controls. Never activate the corrupted data.
    name=next(iter(removed));name_fixed='clknet_3_5_0_pcie_clk_i'
    mutations={
      'physical_header':b.replace('DESIGN ', 'DESIGN CORRUPT_',1),
      'data_net_connection':b.replace(nets[name],nets[name].replace('(', '( CORRUPT',1),1),
      'fixed_clock_route':b.replace(nets[name_fixed],nets[name_fixed].replace('+ FIXED','+ ROUTED',1),1)}
    assert all(c!=b for c in mutations.values())
    for label,corrupt in mutations.items():
        try:verify(a,corrupt,removed)
        except AssertionError:faults.append(dict(name=label,rejected=True))
        else:raise AssertionError('Physical corruption accepted: '+label)
    candidate=out/'candidate.odb';odb.write_db(db,str(candidate))
    # Prove the persisted ODB, not only in-memory mutation.
    reread=odb.dbDatabase.create();odb.read_db(reread,str(candidate))
    persisted=out/'persisted.def';odb.write_def(reread.getChip().getBlock(),str(persisted))
    assert verify(a,persisted.read_text(),removed)==proof
    assert sha(source)==original
    result=dict(status='PASS_ONLY_STALE_DATA_WIRES_REMOVED_REQUIRES_FRESH_GLOBAL_AND_DETAIL_ROUTE',
      source_sha256=original,candidate_sha256=sha(candidate),proof=proof,controls=faults,
      removed=removed,protected=protected,accepted=False,source_unchanged=True)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ('status','proof','controls')}),flush=True)
if __name__=='__main__':main()
