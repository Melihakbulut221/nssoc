#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compare real native ODB topology before/after completed antenna round3."""
import argparse,copy,hashlib,json,os
from pathlib import Path
import odb
def digest(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def capture(path):
    db=odb.dbDatabase.create();odb.read_db(db,str(path));block=db.getChip().getBlock();assert block
    inst={}
    for i in block.getInsts():
        inst[i.getName()]=dict(master=i.getMaster().getName(),pins={t.getMTerm().getName():dict(net=t.getNet().getName()if t.getNet()else None,io=str(t.getIoType()),sig=str(t.getSigType()))for t in i.getITerms()})
    ports={t.getName():dict(net=t.getNet().getName()if t.getNet()else None,io=str(t.getIoType()),sig=str(t.getSigType()))for t in block.getBTerms()}
    nets={n.getName():dict(sig=str(n.getSigType()),ndr=n.getNonDefaultRule().getName()if n.getNonDefaultRule()else None)for n in block.getNets()}
    result=dict(instances=inst,ports=ports,nets=nets)
    odb.dbDatabase.destroy(db)
    return result

def compare(before,after):
    assert before['ports']==after['ports'],'Original boundary terminals changed'
    assert before['nets']==after['nets'],'Original logical nets or NDR assignments changed'
    assert set(before['instances'])<=set(after['instances']),'Original instance missing'
    for name,row in before['instances'].items():assert row==after['instances'][name],('Original master or terminal changed',name)
    added={n:r for n,r in after['instances'].items()if n not in before['instances']}
    assert len(added)==3374,('Unexpected antenna instance delta',len(added))
    for name,row in added.items():
        assert row['master']=='sg13g2_antennanp',('Non-antenna addition',name)
        signal={k:v for k,v in row['pins'].items()if v['sig']not in ('POWER','GROUND')}
        assert set(signal)=={'A'}and signal['A']['io']=='INPUT'and signal['A']['net']in before['nets'],('Invalid diode endpoint',name,signal)
    return dict(original_instances=len(before['instances']),retained_instances=len(before['instances']),added_diode_count=len(added),added_diodes=added,ports=len(before['ports']),nets=len(before['nets']),original_masters_all_pin_connections_nets_ndrs_preserved=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args(['--before',os.environ['NSSOC_TOPOLOGY_BEFORE'],'--after',os.environ['NSSOC_TOPOLOGY_AFTER'],'--out',os.environ['NSSOC_TOPOLOGY_OUT']]if 'NSSOC_TOPOLOGY_BEFORE'in os.environ else None)
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    pinned={str(v):digest(v)for v in (a.before,a.after,Path(__file__))}
    before=capture(a.before);after=capture(a.after);positive=compare(before,after)
    original=next(iter(before['instances']));added=next(n for n in after['instances']if n not in before['instances']);faults=[]
    for label in ('changed_master','changed_pin','non_diode_addition'):
        wrong=dict(after);wrong['instances']=dict(after['instances'])
        chosen=added if label=='non_diode_addition'else original
        wrong['instances'][chosen]=copy.deepcopy(after['instances'][chosen])
        if label in ('changed_master','non_diode_addition'):wrong['instances'][chosen]['master']='CORRUPTED_NATIVE_MASTER'
        else:
            pin=next(iter(wrong['instances'][chosen]['pins']));wrong['instances'][chosen]['pins'][pin]['net']='CORRUPTED_NATIVE_NET'
        try:compare(before,wrong)
        except AssertionError:faults.append(label)
        else:raise AssertionError('Accepted corrupted native topology '+label)
    assert all(digest(p)==h for p,h in pinned.items())
    r=dict(status='PASS_NATIVE_SAVED_ROUTE_TOPOLOGY_ONLY_NOT_TIMING_OR_LVS',inputs=pinned,proof=positive,rejected=faults,qualified_pex=False,full_phy_accepted=False)
    a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in positive.items()if k!='added_diodes'}))
if __name__=='__main__':main()
