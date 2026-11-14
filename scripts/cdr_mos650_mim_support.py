# SPDX-License-Identifier: Apache-2.0
"""Actual650 MIM geometry, complete native identity and corruption checks."""
from pathlib import Path
from collections import Counter
from decimal import Decimal
import copy,json,hashlib,os
import cdr_mos650_spice_syntax as parser
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get("NSSOC_MIM_STAGE",str(ROOT/"unused-mim-stage")))
TOP="nssoc_cdr_pd500_resistor_v59"
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)
def generate():
    import klayout.db as pya
    P=ROOT/'paired-terminal-anchors/native/view';G=P/'parent/layout'/(TOP+'.gds');D=P/'parent/physical/lvs_flat/result.lvsdb'
    assert sha(G)=='c335182048dc1696821ab875fb34447e5b5a9ba0f1a24d5d16d572680906c16c'
    L=pya.Layout();L.read(str(G));T=L.cell(TOP);assert L.dbu==.001 and T is not None
    native=pya.LayoutVsSchematic();native.read(str(D));assert native.netlist().top_circuit().name==TOP
    original=json.loads((P/'wire/anchors08.json').read_text());a=copy.deepcopy(original);geo=json.loads((P/'wire/native05/result.json').read_text());devices=json.loads((P/'wire/device-locations01.json').read_text())['devices']
    oldwire=pya.LayoutToNetlist();oldwire.read(str(P/'wire/native05/wires.l2n'))
    rows={(r['device'],r['terminal']):r for r in a['rows']};labels={r['label']:r for r in a['anchors']};changes=[]
    mask=pya.Region(T.begin_shapes_rec(L.layer(36,0))).merged();vias=pya.Region(T.begin_shapes_rec(L.layer(129,0))).merged();assert not mask.is_empty()and not vias.is_empty()
    native_masks={36:pya.Region(),129:pya.Region()}
    def replace_points(value,point):
        if isinstance(value,dict):
            for k,v in value.items():
                if k=='point_dbu':value[k]=list(point)
                else:replace_points(v,point)
        elif isinstance(value,list):
            for v in value:replace_points(v,point)
    caps=[d for d in devices if d['model']=='cap_cmim'];assert len(caps)==7
    for d in caps:
        c=L.cell(d['pcell']['cell']);dt=pya.DCplxTrans.from_s(d['pcell']['transform']);tr=pya.ICplxTrans(dt.mag,dt.angle,dt.is_mirror(),round(dt.disp.x/L.dbu),round(dt.disp.y/L.dbu))
        for layer in native_masks:native_masks[layer]+=pya.Region(c.begin_shapes_rec(L.layer(layer,0))).transformed(tr)
        metal=pya.Region(c.begin_shapes_rec(L.layer(67,0))).transformed(tr).merged();access=(metal-mask).merged()
        boxes=[p.bbox()for p in access.decompose_trapezoids_to_region().each()if p.area()==p.bbox().area()and p.bbox().width()>20 and p.bbox().height()>20];assert boxes
        point=max(boxes,key=lambda b:b.area()).center();label=f"T{d['native_id']:03d}_mim_btm";row=rows[d['native_id'],'mim_btm'];anchor=labels[label]
        assert row['metal']==anchor['metal']==67 and row['wire_anchor']==label
        old=anchor['point_dbu'];new=[point.x,point.y];assert old!=new
        replace_points(anchor,new);row['point_dbu']=new
        changes.append(dict(native_id=d['native_id'],label=label,old_point_dbu=old,new_point_dbu=new,reason='Actual bottom Metal5 access outside the intrinsic MIM mask; no logical net or geometry edited.'))
    assert (native_masks[36]^mask).is_empty()and(native_masks[129]^vias).is_empty(),'Intrinsic masks must be exactly the seven native PCells'
    W=pya.Layout();W.read(str(P/'wire/native05/wires.gds'));WT=W.top_cell();assert WT.name=='pump_wires'and W.dbu==L.dbu
    for layer in (8,10,30,50,67,126,134,19,29,49,66,125,133):
        assert(pya.Region(WT.begin_shapes_rec(W.layer(layer,0)))^pya.Region(T.begin_shapes_rec(L.layer(layer,0)))).is_empty()
    for layer,region in ((36,mask),(129,vias)):
        assert pya.Region(WT.begin_shapes_rec(W.layer(layer,0))).is_empty();WT.shapes(W.layer(layer,0)).insert(region)
    for anchor in a['anchors']:
        m=anchor['metal'];point=pya.Point(*anchor['point_dbu']);n=native.probe_net(native.layer_by_index(geo['native_layer_mapping'][str(m)]),point);assert n is not None and n.cluster_id==anchor['native_cluster']
        wn=oldwire.probe_net(oldwire.layer_by_name('gds_'+str(m)),point);assert wn is not None and wn.cluster_id==anchor['wire_component']
        witness=pya.Region(pya.Box(point.x-1,point.y-1,point.x+1,point.y+1))
        if m==67:assert (witness&mask).is_empty(),'A Metal5 label would be painted onto the MIM top plate'
    assert len(a['anchors'])==len({(x['metal'],*x['point_dbu'])for x in a['anchors']})==1428
    wire=OUT/'wire';wire.mkdir();(wire/'native05').mkdir();W.write(str(wire/'native05/wires.gds'))
    a['inputs']={str(p):sha(p)for p in [Path(__file__),G,D,P/'wire/anchors08.json',P/'wire/native05/result.json',P/'wire/native05/wires.l2n',P/'wire/device-locations01.json',wire/'native05/wires.gds']}
    a['status']='PASS_ALL1428_NATIVE_POINTS_WITH_SEVEN_MIM_BOTTOM_ACCESS_REBINDINGS';a['mim_bottom_point_changes']=changes
    (wire/'anchors08.json').write_text(json.dumps(a,indent=2)+'\n')
    result=dict(status='PASS_FULL_PD_MASK_GEOMETRY_AND_NATIVE_POINT_BINDING',original_metal_and_vias_unchanged=True,actual_mim_devices=7,actual_mim_masks_exact=True,point_changes=changes,all1428points_match_original_native_clusters_and_physical_components=True,qualified_pex=False,output_gds_sha256=sha(wire/'native05/wires.gds'))
    (OUT/'native-binding.json').write_text(json.dumps(result,indent=2)+'\n')

def check_capture(text,anchors,binding):
    rows=parser.statements(text);assert rows[0][:2]==['.subckt','pump_wires']and rows[-1][0]=='.ends'
    points={x['label']:x for x in anchors['anchors']};assert len(rows[0][2:])==1428 and set(rows[0][2:])==set(points)
    R=[];C=[];X=[]
    for r in rows[1:-1]:
        if r[0].startswith('R'):assert len(r)==4 and parser.number(r[3])>0;R.append(r)
        elif r[0].startswith('C'):assert len(r)==4 and parser.number(r[3])>=0;C.append(r)
        else:assert r[0].startswith('X')and len(r)==6 and r[3]=='cap_cmim';X.append(r)
    assert len({x[0]for x in rows[1:-1]})==len(rows)-2 and len(X)==7
    graph=parser.Union()
    for _,a,b,v in R:graph.join(a,b)
    owners={}
    for name,point in points.items():
        assert name in graph.parent,'Unattached physical point'
        root=graph.find(name);owners.setdefault(root,point['wire_component']);assert owners[root]==point['wire_component'],'Physical conductor short'
    assert len(owners)==len(set(owners.values()))==113
    assert all(graph.find(n)in owners for n in graph.parent)
    for _,a,b,v in C:assert all(n=='sub'or n in graph.parent for n in (a,b))
    native_rows={(r['device'],r['terminal']):r for r in anchors['rows']};expected={}
    for d in binding['devices']:
        if d['model']!='cap_cmim':continue
        plus=native_rows[d['native_id'],'mim_top']['wire_component'];minus=native_rows[d['native_id'],'mim_btm']['wire_component']
        key=(plus,minus,Decimal(d['native_parameters']['w']),Decimal(d['native_parameters']['l']));assert key not in expected;expected[key]=d['native_id']
    found={};devices=[]
    for x in X:
        assert all(n in graph.parent for n in x[1:3]);p=dict(v.split('=')for v in x[4:]);assert set(p)=={'w','l'}
        key=(owners[graph.find(x[1])],owners[graph.find(x[2])],parser.number(p['w'])/Decimal('1e-6'),parser.number(p['l'])/Decimal('1e-6'))
        assert key in expected and key not in found,('Wrong/duplicate native MIM geometry or terminal ownership',key,list(expected),list(found));found[key]=x[0]
        devices.append(dict(native_id=expected[key],export=x,plus_component=key[0],minus_component=key[1]))
    assert set(found)==set(expected)
    return dict(status='PASS_CAPTURE_COMPONENTS_AND_SEVEN_INTRINSIC_MIM_IDENTITIES_REQUIRES_RAW_RC_AUDIT',R=len(R),C=len(C),native_mim_devices=devices,physical_components=113,physical_points=1428,raw_point_capacitance_audited=False,qualified_pex=False)

def validate_mim(rows,rep,before,after,original,owners,anchors):
    binding=json.loads((OUT/'binding.json').read_text())
    terminal={(r['device'],r['terminal']):r for r in anchors['rows']};expected=Counter()
    for d in binding['devices']:
        if d['model']!='cap_cmim':continue
        pair=tuple(terminal[d['native_id'],t]['wire_component']for t in ('mim_top','mim_btm'))
        params=tuple((k,Decimal(d['native_parameters'][k])*Decimal('1e-6'))for k in ('l','w'))
        expected[pair,'cap_cmim',params]+=1
    require(len(expected)==sum(expected.values())==7,'Native MIM census changed')
    def norm(devices,mapping):
        result=Counter()
        for ns,model,params in devices:
            require(model=='cap_cmim'and len(ns)==2 and all(n in mapping for n in ns)and {k for k,v in params}=={'w','l'},'Unexpected native MIM model/terminal/parameter')
            result[tuple(mapping[n]for n in ns),model,params]+=1
        return result
    require(norm(before['devices'],original)==expected,'Baseline native MIM identity/order/value changed')
    require(norm(after['devices'],owners)==expected,'Export native MIM identity/order/value changed')
    require([r for r in rows if r[0]=='parameters']==[['parameters','cap_cmim','w=w','l=l']],'Native MIM parameter declaration changed')
    sources={};source_devices=[]
    for r in rows:
        if r[0]!='device':continue
        require(len(r)==16 and r[:3]==['device','csubckt','cap_cmim']and r[9]=='None','Unexpected source intrinsic device record')
        box=tuple(map(int,r[3:7]));require(box not in sources,'Duplicate native MIM location')
        p=dict(x.split('=')for x in r[7:9]);require(set(p)=={'w','l'}and r[10]in original and r[13]in original,'Native MIM source parameter/terminal changed')
        signature=((original[r[10]],original[r[13]]),'cap_cmim',tuple((k,Decimal(p[k])*Decimal('5e-9'))for k in ('l','w')))
        sources[box]=signature;source_devices.append(r)
    require(Counter(sources.values())==expected,'Source native MIM identity/order/value changed')
    seen=set();replacement_devices=[]
    for r in rep:
        if r[0]!='device':continue
        require(len(r)==14 and r[:3]==['device','csubckt','cap_cmim']and r[7]=='None','Unexpected replacement intrinsic device record')
        box=tuple(map(int,r[3:7]));require(box in sources and box not in seen,'Replacement native MIM location changed');seen.add(box)
        require(r[8]in owners and r[11]in owners and (owners[r[8]],owners[r[11]])==sources[box][0],'Replacement native MIM terminal ownership changed')
        replacement_devices.append(r)
    require(seen==set(sources),'Missing replacement native MIM device')
    return dict(status='PASS_SEVEN_NATIVE_MIM_SOURCE_REPLACEMENT_BASELINE_EXPORT_IDENTITIES',devices=7,source_records=source_devices,replacement_records=replacement_devices,parameter_source='Native source w/l in5nm units, exact match to KLayout native dimensions; explicit PDK subcircuit uses w/l.',replacement_perimeter_metadata_used_for_model=False,intrinsic_devices_excluded_from_wire_C_matrix=True,full_pex_qualified=False)


def audit_faults(wire):
 import importlib.util,difflib,re
 from unittest.mock import patch
 target=wire/"audit-rc48.py";p=wire/"rc03"
 spec=importlib.util.spec_from_file_location("actual650_mim_audit",target);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 anchors=json.loads((wire/"anchors08.json").read_text())
 texts={n:(p/n).read_text()for n in("wires.spice","baseline.spice","pump_wires.ext","pump_wires.res.ext")}
 source_rows=texts["wires.spice"].splitlines();idx=next(i for i,x in enumerate(source_rows)if x.startswith("X"));x=source_rows[idx].split();cases=[]
 def spice_case(name,change):
  lines=source_rows.copy();fields=x.copy();change(fields)
  if fields:lines[idx]=" ".join(fields)
  else:del lines[idx]
  cases.append((name,"wires.spice","\n".join(lines)+"\n"))
 spice_case("missing_export_mim",lambda f:f.clear())
 spice_case("wrong_export_model",lambda f:f.__setitem__(3,"cap_rfcmim"))
 spice_case("wrong_export_width",lambda f:f.__setitem__(next(i for i,t in enumerate(f)if t.startswith("w=")),"w=999u"))
 spice_case("swapped_export_plates",lambda f:f.__setitem__(slice(1,3),list(reversed(f[1:3]))))
 for name,filename,transform in [
  ("missing_source_device","pump_wires.ext",lambda t:re.sub(r"^device .*\n","",t,count=1,flags=re.M)),
  ("wrong_source_dimension","pump_wires.ext",lambda t:re.sub(r"^(device .*? w=)\S+",r"\g<1>999999",t,count=1,flags=re.M)),
  ("missing_replacement_device","pump_wires.res.ext",lambda t:re.sub(r"^device .*\n","",t,count=1,flags=re.M)),
  ("shifted_replacement_location","pump_wires.res.ext",lambda t:re.sub(r"^(device csubckt cap_cmim )\d+",r"\g<1>1",t,count=1,flags=re.M)),
  ("wrong_parameter_declaration","pump_wires.ext",lambda t:t.replace("parameters cap_cmim w=w l=l","parameters cap_cmim w=l l=w",1))]:
  cases.append((name,filename,transform(texts[filename])))
 original_read=Path.read_text;results=[]
 for name,filename,changed in cases:
  assert changed!=texts[filename]
  def changed_read(path,*a,**kw):return changed if path==p/filename else original_read(path,*a,**kw)
  with patch.object(Path,"read_text",changed_read):
   try:module.audit(p,anchors)
   except ValueError as e:reason=str(e)
   else:raise AssertionError("Accepted "+name)
  assert "MIM"in reason,(name,reason)
  results.append(dict(name=name,rejected=True,reason=reason,sha256=hashlib.sha256(changed.encode()).hexdigest(),diff="".join(difflib.unified_diff(texts[filename].splitlines(True),changed.splitlines(True)))))
 assert len(results)==9
 (OUT/"intrinsic-controls.json").write_text(json.dumps(results,indent=2)+"\n")
def records(path):
 result=Counter()
 for row in parser.statements(path.read_text())[1:-1]:
  assert row[0].startswith(("R","C","X"))
  key=tuple(row)if row[0][0]in("R","X")else("C",*sorted(row[1:3]),Decimal(row[3]))
  result[key]+=1

def current_binding(flat):
 import re
 assert len(flat["pairs"])==650 and flat["terminal_count"]==2046
 devices=[];dimensions=[]
 for pair in flat["pairs"]:
  device=pair["layout"];p={k:str(v)for k,v in device["parameters"].items()}
  if device["model"]=="cap_cmim":
   boxes=[]
   for terminal in("MIM_TOP","MIM_BTM"):
    layers=device["terminals"][terminal]["native_layers"];assert len(layers)==1
    layer=layers[0];points=[tuple(map(int,t))for t in re.findall(r"(-?\d+),(-?\d+)",layer["polygons"][0])]
    assert len(layer["polygons"])==1 and len(points)==len(set(points))==4
    xs=[x for x,y in points];ys=[y for x,y in points]
    box=(min(xs),min(ys),max(xs),max(ys))
    assert set(points)=={(x,y)for x in(box[0],box[2])for y in(box[1],box[3])}
    parsed=re.fullmatch(r"\((-?\d+),(-?\d+);(-?\d+),(-?\d+)\)",layer["bbox_dbu"]);assert parsed
    assert tuple(map(int,parsed.groups()))==box
    assert layer["area_dbu2"]==(box[2]-box[0])*(box[3]-box[1])
    boxes.append(box)
   assert boxes[0]==boxes[1]
   box=boxes[0];w=Decimal(box[2]-box[0])/1000;l=Decimal(box[3]-box[1])/1000
   exact=dict(w=w,l=l,A=w*l,P=2*(w+l))
   assert device["parameters"]["m"]==1 and w>0 and l>0
   corrections=[]
   for key,value in exact.items():
    observed=Decimal(p[key])
    if observed!=value:
     assert (p[key],str(value))in{("4.800000000000001","4.8"),("19.200000000000003","19.2")},("unrecognized native geometry discrepancy",key,p[key],str(value))
     corrections.append(dict(parameter=key,raw=p[key],exact_from_integer_polygons=str(value)))
    p[key]=str(value)
   dimensions.append(dict(native_id=device["id"],bbox_dbu=box,raw_parameters=device["parameters"],exact_parameters=p,known_serialization_artifacts=corrections))
  devices.append(dict(native_id=device["id"],model=device["model"],native_parameters=p))
 assert len(dimensions)==7
 return dict(devices=devices),dimensions

if __name__=="__main__":
 import sys
 if sys.argv[1:]==["--geometry"]:generate()
 elif sys.argv[1:]==["--faults"]:audit_faults(OUT/"wire")
 else:raise ValueError("explicit geometry or fault mode required")
