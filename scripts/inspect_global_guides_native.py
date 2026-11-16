import odb,os,json,pathlib
p=pathlib.Path(os.environ['NSSOC_AUDIT_OUT'])
db=odb.dbDatabase.create();odb.read_db(db,os.environ['NSSOC_AUDIT_ODB']);block=db.getChip().getBlock();assert block.getName()=='soc_top'
rows=[];missing=[];total=0
for net in block.getNets():
 count=len(net.getGuides());total+=count
 terminals=len(net.getITerms())+len(net.getBTerms())
 if count:rows.append(dict(name=net.getName(),guides=count,terminals=terminals))
 elif str(net.getSigType()) not in ('POWER','GROUND') and terminals>1:
  missing.append(dict(name=net.getName(),terminals=terminals,special=net.isSpecial(),has_wire=net.getWire() is not None))
assert total>0 and rows
r=dict(block=block.getName(),guide_count=total,nets_with_guides=len(rows),instances=len(block.getInsts()),connected_nets_without_guides=missing,guide_nets=rows,accepted=False)
(p/'guide-inventory.json').write_text(json.dumps(r,indent=2));print('NSSOC_NATIVE_GUIDE_AUDIT',total,len(rows),'missing',len(missing))
