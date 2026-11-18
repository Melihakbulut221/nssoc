#!/usr/bin/env python3
"""Read-only admission of already-canonical ECO identifiers for RC extraction.

No renaming, no geometry mutation and no inference of SPEF coverage. Ports and
power/ground names retain their original naming convention, as in the prior
qualified canonicalization. Native annotation coverage must still be checked.
"""
import os,json,re,hashlib
from pathlib import Path
import odb

def main():
 source=Path(os.environ['NSSOC_EXTRACTION_NAME_ODB'])
 output=Path(os.environ['NSSOC_EXTRACTION_NAME_REPORT'])
 expected=int(os.environ['NSSOC_EXTRACTION_EXPECTED_INSTANCES'])
 before=hashlib.sha256(source.read_bytes()).hexdigest()
 db=odb.dbDatabase.create();odb.read_db(db,str(source));b=db.getChip().getBlock()
 safe=re.compile(r'[A-Za-z_][A-Za-z0-9_.]*')
 instances=list(b.getInsts());nets=list(b.getNets())
 invalid_i=sorted(i.getName()for i in instances if not safe.fullmatch(i.getName()))
 checked=[n for n in nets if not list(n.getBTerms())and str(n.getSigType())not in ('POWER','GROUND')]
 invalid_n=sorted(n.getName()for n in checked if not safe.fullmatch(n.getName()))
 unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==before
 report=dict(source_odb_sha256=before,source_unchanged=unchanged,instances=len(instances),expected_instances=expected,internal_nets_checked=len(checked),invalid_instances=invalid_i,invalid_internal_nets=invalid_n,renaming_performed=False,spef_coverage_checked=False,accepted=False)
 output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2)+'\n')
 assert unchanged and len(instances)==expected and not invalid_i and not invalid_n,'Already-canonical extraction admission failed; inspect report'
if __name__=='__main__':main()
