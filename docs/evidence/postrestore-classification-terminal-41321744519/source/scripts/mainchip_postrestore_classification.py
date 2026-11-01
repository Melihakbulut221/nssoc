"""Lossless classification of authenticated post-restoration physical violations.
This proposes inspection owners; it does not authorize route edits or waive markers.
"""
from collections import Counter
from decimal import Decimal
import hashlib,json
FLAGS=dict(physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def flatten(tree):
 assert isinstance(tree,dict)and tree
 rows=[];cats=[]
 def visit(name,node,path):
  assert isinstance(node,dict)
  assert set(node)<={"description","source","max_markers","violations","category"}
  assert node["source"]=="DRT"
  cap=int(node["max_markers"]);assert cap>0
  items=node.get("violations",[]);assert isinstance(items,list)and len(items)<cap
  cats.append(dict(path=path+[name],count=len(items),cap=cap))
  for i,m in enumerate(items):
   assert isinstance(m,dict)and m.get("layer")
   assert isinstance(m.get("sources"),list)and m["sources"]
   assert isinstance(m.get("shape"),list)and m["shape"]
   assert m.get("waived")=="false"
   for shape in m["shape"]:
    assert shape["type"]=="box"and len(shape["points"])==2
    for p in shape["points"]:
     assert set(p)=={"x","y"}and all(Decimal(str(v)).is_finite()for v in p.values())
    a,b=shape["points"];assert Decimal(a["x"])<=Decimal(b["x"])and Decimal(a["y"])<=Decimal(b["y"])
   for source in m["sources"]:assert isinstance(source.get("type"),str)and isinstance(source.get("name"),str)and source["name"]
   rows.append(dict(ordinal=len(rows),category=path+[name],category_index=i,record_sha256=digest(m),record=m))
  children=node.get("category",{});assert isinstance(children,dict)
  for n,c in children.items():visit(n,c,path+[name])
 for n,c in tree.items():visit(n,c,[])
 return rows,cats
def classify(tree,antenna,scope,classes):
 rows,cats=flatten(tree)
 sets={k:set(scope[k])for k in ("antenna_nets","counterpart_nets","protected_nets","routing_nets")}
 assert sets["routing_nets"]==sets["antenna_nets"]|sets["counterpart_nets"]
 assert not sets["routing_nets"]&sets["protected_nets"]and not sets["antenna_nets"]&sets["counterpart_nets"]
 def role(name):
  if name in sets["protected_nets"]:return "protected"
  if name in ("VPWR","VGND"):return "power"
  if name in sets["antenna_nets"]:return "antenna_owner"
  if name in sets["counterpart_nets"]:return "counterpart_owner"
  return "outside_routing_scope"
 owners={}
 def own(name):
  if name not in owners:
   owners[name]=dict(net=name,role=role(name),original_overlay_class=classes.get(name),original_class_record_present=name in classes,marker_ordinals=[],antenna_row_ordinals=[])
  return owners[name]
 byrule=Counter();bylayer=Counter();byroles=Counter();non_net=[]
 for row in rows:
  m=row["record"];nets=sorted(set(s["name"]for s in m["sources"]if s["type"]=="net"))
  other=[s for s in m["sources"]if s["type"]!="net"]
  row.update(nets=nets,net_roles={n:role(n)for n in nets},non_net_sources=other)
  if other:non_net.append(row["ordinal"])
  for n in nets:own(n)["marker_ordinals"].append(row["ordinal"])
  byrule[row["category"][-1]]+=1;bylayer[m["layer"]]+=1
  byroles["+".join(sorted(set(role(n)for n in nets)))or"no_net_source"]+=1
 antrows=[]
 assert isinstance(antenna,list)
 for i,row in enumerate(antenna):
  assert row["violated"]is True and isinstance(row["net"],str)and row["net"]
  assert row["rule"]and row["layer"]and row["pin"]
  assert Decimal(row["display_value"]).is_finite()and Decimal(row["display_limit"]).is_finite()
  own(row["net"])["antenna_row_ordinals"].append(i)
  antrows.append(dict(ordinal=i,role=role(row["net"]),record_sha256=digest(row),record=row))
 for row in owners.values():
  row["inspection_candidate_only"]=row["role"]not in ("protected","power")
  row["native_signal_identity_and_class_confirmation_required"]=row["inspection_candidate_only"]
  row["routing_authorized"]=False
 groups=[];pending=set(owners)
 # Components connect net co-occurrence only; not a claim of conductor connectivity.
 neighbors={n:set()for n in owners}
 for row in rows:
  for n in row["nets"]:neighbors[n].update(set(row["nets"])-{n})
 while pending:
  seed=min(pending);todo=[seed];component=set()
  while todo:
   n=todo.pop()
   if n in component:continue
   component.add(n);todo.extend(neighbors[n]-component)
  pending-=component
  markers=sorted({i for n in component for i in owners[n]["marker_ordinals"]})
  ants=sorted({i for n in component for i in owners[n]["antenna_row_ordinals"]})
  groups.append(dict(nets=sorted(component),marker_ordinals=markers,antenna_row_ordinals=ants,
    roles=dict(Counter(role(n)for n in component)),routing_authorized=False))
 summary=dict(markers=len(rows),categories=cats,by_rule=dict(byrule),by_layer=dict(bylayer),by_owner_roles=dict(byroles),
  antenna_rows=len(antrows),antenna_nets=len({r["record"]["net"]for r in antrows}),
  antenna_by_role=dict(Counter(r["role"]for r in antrows)),
  owners=len(owners),owners_by_role=dict(Counter(r["role"]for r in owners.values())),
  marker_non_net_source_ordinals=non_net,cooccurrence_components=len(groups),
  input_markers_sha256=digest(tree),input_antenna_sha256=digest(antenna),
  all_marker_ordinals_preserved=[r["ordinal"]for r in rows]==list(range(len(rows))),
  classification_only=True,routing_authorized=False,**FLAGS)
 return dict(summary=summary,markers=rows,antenna=antrows,owners=[owners[n]for n in sorted(owners)],cooccurrence_components=groups)
def controls():
 import copy
 names=[]
 marker=dict(visited="false",visible="true",waived="false",layer="Metal2",shape=[dict(type="box",points=[dict(x="1.0000",y="2.0000"),dict(x="1.2000",y="2.2000")])],sources=[dict(type="net",name="a"),dict(type="net",name="outside")])
 tree={"root":dict(source="DRT",max_markers="10",category={"Short":dict(source="DRT",max_markers="10",violations=[marker])})}
 scope=dict(antenna_nets=["a"],counterpart_nets=["b"],protected_nets=["clock"],routing_nets=["a","b"])
 antenna=[dict(net="b",pin="inst/A",rule="Cumulative area",layer="Metal3",display_value="201.00",display_limit="200.00",violated=True)]
 def run(t=tree,a=antenna,s=scope):return classify(t,a,s,{"outside":"ROUTED","clock":"FIXED"})
 def ok(name,condition):assert condition,name;names.append(name)
 r=run();ok("unscoped net retained",next(x for x in r["owners"]if x["net"]=="outside")["role"]=="outside_routing_scope")
 ok("antenna without DRC retained",next(x for x in r["owners"]if x["net"]=="b")["antenna_row_ordinals"]==[0])
 ok("original marker unchanged",r["markers"][0]["record"]==marker)
 t=copy.deepcopy(tree);t["root"]["category"]["Short"]["violations"].append(copy.deepcopy(marker))
 ok("identical records retain distinct ordinals",[x["ordinal"]for x in run(t)["markers"]]==[0,1])
 t=copy.deepcopy(tree);t["root"]["category"]["Short"]["violations"][0]["sources"]=[dict(type="net",name="clock"),dict(type="net",name="VPWR")]
 ok("protected and PG never offered",[x["inspection_candidate_only"]for x in run(t,[])["owners"]]==[False,False])
 t=copy.deepcopy(tree);t["root"]["category"]["Short"]["violations"][0]["sources"].append(dict(type="inst",name="physical_instance"))
 ok("non-net source retained",run(t)["summary"]["marker_non_net_source_ordinals"]==[0])
 def refuse(name,fn):
  try:fn()
  except (AssertionError,ValueError,KeyError):names.append(name);return
  raise AssertionError("accepted invalid case "+name)
 t=copy.deepcopy(tree);t["root"]["category"]["Short"]["max_markers"]="1";refuse("saturated cap",lambda:run(t))
 t=copy.deepcopy(tree);t["root"]["category"]["Short"]["source"]="other";refuse("non-DRT source",lambda:run(t))
 t=copy.deepcopy(tree);t["root"]["category"]["Short"]["violations"][0]["waived"]="true";refuse("waived marker",lambda:run(t))
 t=copy.deepcopy(tree);t["root"]["category"]["Short"]["violations"][0]["shape"][0]["points"][0]["x"]="NaN";refuse("nonfinite point",lambda:run(t))
 t=copy.deepcopy(tree);t["root"]["category"]["Short"]["violations"][0]["shape"][0]["points"][0]["x"]="9";refuse("reversed box",lambda:run(t))
 a=copy.deepcopy(antenna);a[0]["violated"]=False;refuse("nonviolating antenna row",lambda:run(a=a))
 s=copy.deepcopy(scope);s["protected_nets"].append("a");refuse("protected overlap",lambda:run(s=s))
 t=copy.deepcopy(tree);t["root"]["unexpected_unread_markers"]=[];refuse("unknown category data",lambda:run(t))
 t=copy.deepcopy(tree);t["root"]["category"]["Other"]=dict(source="DRT",max_markers="10",violations=[copy.deepcopy(marker)])
 ok("all rule categories retained",run(t)["summary"]["by_rule"]=={"Short":1,"Other":1})
 ok("no route or acceptance authority",all(r["summary"][k]is False for k in ("routing_authorized",*FLAGS)))
 return dict(status="PASS",controls=len(names),names=names,**FLAGS)
