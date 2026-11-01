"""Explicit physical-conductor model using independently GDS-qualified pin rectangles.
Original wire-only observations remain immutable and separately reported.
The caller must bind the exact current database and qualification files by hash.
"""
import copy,hashlib,json
FLAGS=dict(physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,layout_modified=False)
MODEL="routed_metal_plus_independently_GDS_verified_pin_rectangles"
CANDIDATE=dict(bytes=214409779,sha256="d526feec659883b65dc737853d4d6a192d529384e2676d8a2d17e9b5e7d6de7e")
GDS_STATUS="PASS_OBSERVED_PIN_METAL_GDS_LEF_TRANSFORMS_NOT_CHIP_ACCEPTANCE"
def enc(v):return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def pin(v):return dict(bytes=len(enc(v)),sha256=hashlib.sha256(enc(v)).hexdigest())
def qualification(rows,result,expected=(142,1300,77)):
 nets,pins,masterpins=expected
 assert result["status"]==GDS_STATUS and result["all_observed_pin_rectangles_verified"]is True
 assert result["missing_or_mismatched_pins"]==0
 assert (result["original_failed_nets"],result["observed_pin_count"],result["unique_master_pins"])==expected
 assert all(result[k]is False for k in ["physical_acceptance","timing_accepted","full_phy_accepted","layout_modified","original_connectivity_gate_modified"])
 table={};identities=set();masters=set()
 for row in rows:
  assert row["passed"]is True and row["exact_master_to_observed_pin_transform"]is True and row["master_pin_gds_lef_passed"]is True
  ident=tuple(row["pin"]);assert len(ident)==3 and ident[0]=="iterm"and ident not in identities
  identities.add(ident);masters.add(tuple(row["master"])+ident[2:])
  name=row["net"];group=table.setdefault(name,{})
  assert ident not in group;group[ident]=row
  assert row["observed_rectangles"]
  for i,g in enumerate(row["observed_rectangles"]):
   assert g["pin"]==list(ident)and g["geometry_index"]==i
   assert type(g["layer"])is str and len(g["box"])==4 and all(type(x)is int for x in g["box"])
   x0,y0,x1,y1=g["box"];assert x0<x1 and y0<y1
 assert(len(table),len(identities),len(masters))==expected
 return table
def conductors(original,approved,observe):
 pins=original["source_pins"];shapes=original["source_shapes"]
 ids=[tuple(p["scoped_identity"])for p in pins]
 assert len(ids)==len(set(ids))and set(ids)==set(approved)
 added=[]
 for p in pins:
  ident=tuple(p["scoped_identity"]);row=approved[ident]
  actual=[dict(pin=list(ident),geometry_index=i,layer=layer,box=rect)for i,(layer,rect)in enumerate(p["geometries"])]
  assert enc(actual)==enc(row["observed_rectangles"]),"actual pin differs from independently verified GDS geometry"
  for g in actual:
   added.append(dict(kind="wire-rect",layer=g["layer"],box=copy.deepcopy(g["box"]),
    physical_material_origin="GDS_verified_cell_pin",scoped_pin=g["pin"],pin_geometry_index=g["geometry_index"]))
 assert len(shapes)+len(added)<=4096,"retain original graph size limit"
 return observe(copy.deepcopy(shapes)+added,copy.deepcopy(pins),original["mode"]),added
def audit(observations,plan,rows,gds_result,observe,gate,expected=(828,142,1300,77)):
 total,failed,pincount,masterpins=expected
 assert len(observations)==total and sorted(observations)==sorted(plan["mutable_nets"])
 approved=qualification(rows,gds_result,(failed,pincount,masterpins))
 actual_failures={};corrected={};reports=[]
 for name,modes in sorted(observations.items()):
  assert set(modes)=={"positive_area","closed_boundary"}
  for mode,record in modes.items():
   assert record["mode"]==mode
   assert enc(observe(record["source_shapes"],record["source_pins"],mode))==enc(record),"original graph replay"
  local_plan=dict(mutable_nets=[name],attachments={i:n for i,n in plan["attachments"].items()if n==name})
  try:gate({name:modes},local_plan)
  except AssertionError as error:actual_failures[name]=str(error)
  if name in actual_failures:
   assert name in approved,"new/unqualified original failure"
   corrected[name]={};mode_reports={}
   for mode,record in modes.items():
    actual,added=conductors(record,approved[name],observe);corrected[name][mode]=actual
    mode_reports[mode]=dict(original_components=len(record["wire_components"]),physical_components=len(actual["wire_components"]),
     original_graph=pin(record),physical_graph=pin(actual),added_pin_rectangles=added,
     pins_share=actual["all_pins_share_one_wire_component"],material_connected=actual["all_wire_material_one_component"])
   gate({name:corrected[name]},local_plan)
   reports.append(dict(net=name,original_wire_only_passed=False,original_rejection=actual_failures[name],modes=mode_reports))
  else:
   assert name not in approved,"qualification no longer matches original wire-only failure"
   corrected[name]=modes
   reports.append(dict(net=name,original_wire_only_passed=True,modes={m:dict(original_graph=pin(r),physical_graph=pin(r),added_pin_rectangles=[])for m,r in modes.items()}))
 assert set(actual_failures)==set(approved)and len(actual_failures)==failed
 original_predicate=gate(corrected,plan)
 result=dict(**original_predicate,model=MODEL,original_wire_only_failed_nets=failed,original_wire_only_passed_nets=total-failed,
  original_graphs_replayed=total*2,qualified_pin_observations=pincount,qualified_master_pins=masterpins,
  independently_GDS_qualified_pin_metal=True,original_wire_only_results_preserved=True,
  arbitrary_logical_pin_bridging=False,layout_modified=False)
 assert all(result[k]is False for k in ["physical_acceptance","timing_accepted","full_phy_accepted"])
 return result,reports
