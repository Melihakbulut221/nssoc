#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Reject physical changes made during the fresh global-guide stage."""
import hashlib,json,os,re
from pathlib import Path
import odb
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def normalized(s):return re.sub(r'(?m)^GCELLGRID[^\n]*\n','',s)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    before=Path(os.environ['NSSOC_GLOBAL_BEFORE']);after=Path(os.environ['NSSOC_GLOBAL_AFTER'])
    out=Path(os.environ['NSSOC_GLOBAL_GEOMETRY_OUT']);out.mkdir(exist_ok=False)
    hashes={str(p):sha(p)for p in (before,after)};texts=[]
    for label,path in [('before',before),('after',after)]:
        db=odb.dbDatabase.create();odb.read_db(db,str(path));block=db.getChip().getBlock()
        assert len(list(block.getInsts()))==153130
        assert sum(i.getMaster().isBlock()for i in block.getInsts())==20
        target=out/(label+'.def');odb.write_def(block,str(target));texts.append(target.read_text())
    a,b=texts;assert normalized(a)==normalized(b),'Physical DEF changed beyond routing grid'
    # Real-record header and connectivity corruption controls.
    bad_header=b.replace('DESIGN ','DESIGN CORRUPT_',1)
    i=b.index('\nNETS ');j=b.index('(',i);bad_pin=b[:j]+'( CORRUPT'+b[j+1:]
    rejected=[]
    for label,bad in [('header',bad_header),('net-pin',bad_pin)]:
        assert bad!=b
        try:assert normalized(a)==normalized(bad)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Accepted physical corruption '+label)
    assert all(sha(p)==h for p,h in hashes.items())
    (out/'result.json').write_text(json.dumps(dict(
        status='PASS_GLOBAL_GUIDE_STAGE_PHYSICAL_DEF_EXACT_EXCEPT_GCELLGRID',
        instance_count=153130,sram_instances=20,source_hashes=hashes,
        rejected=rejected,sources_unchanged=True,final_timing_complete=False),indent=2)+'\n')
if __name__=='__main__':main()
