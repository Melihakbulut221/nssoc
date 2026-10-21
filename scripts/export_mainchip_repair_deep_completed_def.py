#!/usr/bin/env python3
"""Export fresh DEF from the exact completed native ODB without mutation."""
import hashlib,json,os
from pathlib import Path
import odb
def sha(p):
    with Path(p).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    source=Path(os.environ['NSSOC_EXPORT_ODB']);expected=os.environ['NSSOC_EXPORT_SHA256']
    out=Path(os.environ['NSSOC_EXPORT_OUT']);out.mkdir(exist_ok=False)
    assert sha(source)==expected
    db=odb.dbDatabase.create();odb.read_db(db,str(source));block=db.getChip().getBlock()
    assert len(block.getInsts())==153130 and block.getName()=='soc_top'
    target=out/'completed.def'
    odb.write_def(block,str(target))
    assert target.is_file()and target.stat().st_size>0 and sha(source)==expected
    r=dict(status='PASS_NATIVE_ODB_DEF_EXPORT_ONLY',odb_sha256=expected,def_sha256=sha(target),
        def_bytes=target.stat().st_size,instances=len(block.getInsts()),nets=len(block.getNets()),
        signal_wires=sum(n.getWire()is not None for n in block.getNets()),
        source_unchanged=True,native_routing_started=False,final_timing_complete=False)
    assert r['signal_wires']>0
    odb.dbDatabase.destroy(db)
    (out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
