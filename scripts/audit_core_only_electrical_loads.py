#!/usr/bin/env python3
"""Read-only native electrical sink inventory; no fanout or antenna waiver."""
import os,json,re,hashlib
from collections import Counter
from pathlib import Path
import odb
out=Path(os.environ['NSSOC_CORE_LOAD_AUDIT_OUT']);path=out/'source.odb';before=hashlib.sha256(path.read_bytes()).hexdigest()
d=odb.dbDatabase.create();odb.read_db(d,str(path));b=d.getChip().getBlock()
text=(out/'checks.rpt').read_text();m=re.search(r'(?m)^max fanout\s*\n',text);assert m
section=text[m.end():].split('\n\n',2)[0]
# OpenSTA emits a blank line immediately below the section title.
from parse_core_only_fanout_report import parse_rows,controls
parser_controls=controls();rows=parse_rows(section)
assert sum(row[3] is None for row in rows)==61
assert len(rows)==171,len(rows)
result=[]
for pin,limit,reported,slack in rows:
 inst,port=pin.rsplit('/',1);i=b.findInst(inst);assert i
 t=i.findITerm(port);assert t and t.getNet()and str(t.getIoType())=='OUTPUT'
 net=t.getNet();sinks=[];drivers=[]
 for terminal in net.getITerms():
  ii=terminal.getInst();master=ii.getMaster();kind=str(terminal.getIoType());name=ii.getName()+'/'+terminal.getMTerm().getName()
  if kind=='OUTPUT':drivers.append(name)
  elif kind in ('INPUT','INOUT')and str(terminal.getSigType())not in ('POWER','GROUND'):
   sinks.append(dict(pin=name,master=master.getName(),master_type=str(master.getType()),io_type=kind))
 assert drivers==[pin],(pin,drivers)
 result.append(dict(driver=pin,driver_master=i.getMaster().getName(),net=net.getName(),net_signal_type=str(net.getSigType()),reported_limit=int(limit),reported_fanout=int(reported),printed_slack=slack,computed_slack=int(limit)-int(reported),native_input_terminals=len(sinks),native_boundary_terminals=[t.getName()for t in net.getBTerms()],sink_master_counts=dict(Counter(s['master']for s in sinks)),sink_type_counts=dict(Counter(s['master_type']for s in sinks)),sinks=sinks))
assert hashlib.sha256(path.read_bytes()).hexdigest()==before
(out/'load-inventory.json').write_text(json.dumps(dict(parser_controls=parser_controls,rows_with_blank_printed_slack=61,rows=result,violating_drivers=len(result),input_odb_sha256=before,source_unchanged=True,accepted=False,waivers_applied=False,scope='Native connectivity and master-type inventory only; does not prove electrical adequacy or antenna protection.'),indent=2)+'\n')
