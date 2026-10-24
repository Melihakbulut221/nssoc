#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare every source clock/fixed DEF net record and its attached instance geometry."""
import hashlib,json,os
from pathlib import Path
import odb
from prepare_mainchip_repair_deep_fresh_route import split_def
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 before=Path(os.environ['NSSOC_CLOCK_BEFORE']);after=Path(os.environ['NSSOC_CLOCK_AFTER']);out=Path(os.environ['NSSOC_CLOCK_AUDIT']);out.mkdir(exist_ok=False)
 hashes={str(p):sha(p)for p in [before,after]};snapshots={};clocks=None
 for label,path in [('before',before),('after',after)]:
  db=odb.dbDatabase.create();odb.read_db(db,str(path));b=db.getChip().getBlock()
  assert len(list(b.getInsts()))==153130
  if clocks is None:
   clocks={n.getName()for n in b.getNets()if str(n.getSigType())=='CLOCK'or str(n.getWireType())=='FIXED'or any(str(t.getMTerm().getSigType())=='CLOCK'or t.getInst().getName().startswith('clkbuf')for t in n.getITerms())}
   clocks={n for n in clocks if str(b.findNet(n).getSigType())not in ('POWER','GROUND')}
   assert 'clknet_3_5_0_pcie_clk_i'in clocks and len(clocks)>100
  path=out/(label+'.def');odb.write_def(b,str(path));_,records=split_def(path.read_text())
  # All names remain literal native DEF names; fail instead of fuzzy matching.
  assert clocks<=records.keys(),sorted(clocks-records.keys())[:10]
  snap={}
  for name in sorted(clocks):
   n=b.findNet(name);assert n
   snap[name]=dict(statement=records[name].split(),instances={i.getName():dict(master=i.getMaster().getName(),location=list(i.getLocation()),orientation=str(i.getOrient()),status=str(i.getPlacementStatus()))for i in {t.getInst()for t in n.getITerms()}})
  snapshots[label]=snap
  odb.dbDatabase.destroy(db)
 assert snapshots['before']==snapshots['after'],'Source clock/fixed physical route or attached instance geometry changed'
 assert all(sha(p)==h for p,h in hashes.items())
 (out/'result.json').write_text(json.dumps(dict(status='PASS_ALL_SOURCE_CLOCK_AND_FIXED_NET_DEF_RECORDS_AND_ATTACHED_GEOMETRY_EXACT',source_hashes=hashes,clock_or_fixed_nets=len(clocks),all_source_clock_and_fixed_records_preserved=True,accepted=False,scope='Every source CLOCK, fixed, clock-pin or clkbuf-connected net. Signal routing, antenna, RC and timing remain separate.'),indent=2)+'\n')
if __name__=='__main__':main()
