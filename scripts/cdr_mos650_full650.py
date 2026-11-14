
# SPDX-License-Identifier: Apache-2.0
"""Compose actual650 identities with exact native MIM/metal and qualified gate ports."""
from collections import Counter
from decimal import Decimal
import math
import cdr_mos650_spice_syntax as parser
def need(value,message):
 if not value:raise ValueError(message)
def geometry_readback_matches(exact,observed):
 return math.isfinite(observed) and abs(exact-Decimal.from_float(observed))<=Decimal.from_float(math.ulp(observed))
def assemble(identity,anchors,legacy,wiretext,capture,reductions,fixture,n):
 need(n in(1,2,4,8,16),"declared gate partition")
 pairs={p["layout"]["id"]:p for p in identity["pairs"]}
 need(len(pairs)==650 and identity["terminal_count"]==2046,"complete current650 native identity")
 need(Counter(p["layout"]["model"]for p in pairs.values())==dict(sg13_lv_nmos=200,npn13g2=124,rppd=98,cap_cmim=7,ptap1=221),"complete actual model census")
 rows={(r["device"],r["terminal"].upper()):r for r in anchors["rows"]}
 need(len(rows)==2046 and set(rows)=={(i,t)for i,p in pairs.items()for t in p["layout"]["terminals"]},"every native terminal retained")
 physical={a["label"]:a for a in anchors["anchors"]}
 need(len(physical)==1428 and anchors["physical_gate_contact_count"]==200 and not anchors["intrinsic_gate_metal_shortcuts"],"all distinct actual metal references")
 parsed=parser.statements(wiretext)
 need(parsed[0][:2]==[".subckt","pump_wires"]and parsed[-1][0]==".ends","actual native metal subcircuit")
 need(len(parsed[0][2:])==1428 and set(parsed[0][2:])==set(physical),"all actual metal ports")
 rc=[r for r in parsed[1:-1]if r[0].startswith(("R","C"))]
 native_caps=[r for r in parsed[1:-1]if r[0].startswith("X")]
 need(Counter(r[0][0]for r in parsed[1:-1])==dict(R=28634,C=18488,X=7),"actual MIM-aware native census")
 need(len({r[0].lower()for r in parsed[1:-1]})==len(parsed)-2,"unique native element names")
 public={a["label"]:a["detail"]["public_port"]for a in physical.values()if "public_port"in a["detail"]}
 need(len(public)==25 and set(public.values())=={p["name"]for p in identity["ports"]},"all actual public pin names")
 graph=parser.Union()
 for r in rc:
  need(len(r)==4 and r[1]!=r[2],"complete native passive record")
  need(parser.number(r[3])>0 if r[0].startswith("R")else parser.number(r[3])>=0,"native passive value")
  if r[0].startswith("R"):graph.join(r[1],r[2])
 owners={}
 for label,a in physical.items():
  need(label in graph.parent,"no disconnected physical point")
  root=graph.find(label)
  need(owners.setdefault(root,a["wire_component"])==a["wire_component"],"no cross-conductor R short")
 need(len(owners)==len(set(owners.values()))==113 and all(graph.find(x)in owners for x in graph.parent),"complete independently owned resistor graph")
 nodes={node for r in rc for node in r[1:3]}|{node for r in native_caps for node in r[1:3]}
 need(set(physical)<=nodes and "sub"in nodes,"complete native node scope")
 def rename(node):return "wire_cref"if node=="sub"else public.get(node,"w_"+node)
 wire_map={node:rename(node)for node in nodes}
 need(len(set(v.lower()for v in wire_map.values()))==len(wire_map),"bijective native point mapping")
 old={d["native_id"]:d for d in legacy["devices"]}
 need(len(old)==500,"canonical source parameter binding only; no old RC reuse")
 unit_cases={d["native_id"]:d for d in fixture["devices"]};need(len(unit_cases)==200,"all native MOS geometry cases")
 body={};physical_terminals={}
 for (i,t),row in rows.items():
  device=pairs[i]["layout"];native=device["terminals"][t]
  need(row["model"].lower()==device["model"]and row["native_cluster"]==native["cluster"]and row["native_net"]==native["name"],"actual native terminal identity")
  disposition=row["disposition"]
  if disposition=="ACTUAL_TERMINAL_METAL_POINT_REFERENCE":
   label=row["wire_anchor"];a=physical[label]
   need(label=="T"+format(i,"03d")+"_"+row["terminal"]and label in a["logical_labels"],"exact native terminal point label")
   need(all(a[k]==row[k]for k in("metal","point_dbu","wire_component","native_cluster")),"exact terminal material point and owner")
   node=wire_map[label]
  elif disposition=="RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE":
   node="body_"+str(row["native_cluster"])
   need(body.setdefault(node,row["native_net"])==row["native_net"],"intrinsic body partition identity")
  else:
   need(disposition=="RETAINED_INTRINSIC_GATE_REQUIRES_POLY_RC"and device["model"]=="sg13_lv_nmos"and t=="G","only actual intrinsic gates require projection")
   node=None
  physical_terminals[i,t]=node
 need(not set(body)&set(wire_map.values()),"intrinsic bodies are not supply aliases")
 gate_nodes={};gate_instances=[];gate_fragments=[];seen_contacts=set();gate_bindings=[]
 need(len(reductions)==50,"all actual physical gate groups")
 for reduction,fragment in reductions:
  need(reduction["copies"]==n and reduction["reference_contact_is_not_global_ground"],"same actual fixed port basis")
  gi=reduction["group_index"];ports=reduction["ports"];mapping=[]
  def contact(c):
   label=c["label"];want=c["physical_anchor"];a=physical[label]
   need(label not in seen_contacts and "gate_contact"in a["detail"],"every physical GC used exactly once")
   seen_contacts.add(label)
   need(all(a[k]==want[k]for k in("label","metal","point_dbu","native_cluster","wire_component")),"same current physical gate contact")
   need(a["detail"]["gate_group"]==reduction["group"],"same physical poly group")
   return wire_map[label]
  mapping.append(contact(reduction["actual_reference_contact"]))
  for port in ports:
   if port["kind"]=="metal_contact":mapping.append(contact(port))
   else:
    need(port["kind"]=="projected_gate"and port["copies"]==n,"actual projected intrinsic gate")
    i=port["device"];stripe=port["stripe"];key=(i,stripe)
    need(i in unit_cases and unit_cases[i]["gate_group"]==reduction["group"]and 0<=stripe<n and key not in gate_nodes,"unique correct actual gate stripe")
    need(port["intrinsic_multiplicity"]==dict(numerator=1,denominator=n),"exact physical unit weight")
    node="g"+str(i)+"_"+str(stripe);gate_nodes[key]=node;mapping.append(node)
  first=parser.statements(fragment)[0];model="gp_g"+str(gi)+"_n"+str(n)
  need(first==[".subckt",model,"ref",*["p"+str(i)for i in range(len(ports))]],"complete unchanged reduced macro interface")
  need(parser.statements(fragment)[-1]==[".ends"],"complete reduced macro")
  gate_fragments.append(fragment);gate_instances.append(["Xgate"+str(gi),*mapping,model])
  gate_bindings.append(dict(group_index=gi,model=model,nodes=mapping,reference_is_actual_contact=True))
 need(len(seen_contacts)==200 and len(gate_nodes)==200*n and set(gate_nodes)=={(i,j)for i in unit_cases for j in range(n)},"all physical gates and contacts integrated exactly once")
 caps={d["native_id"]:d for d in capture["native_mim_devices"]}
 need(len(caps)==7 and Counter(tuple(d["export"])for d in caps.values())==Counter(map(tuple,native_caps)),"exact original seven native MIM cards")
 out=[];records=[]
 for i,pair in sorted(pairs.items()):
  dev=pair["layout"];source=pair["original_source"];model=dev["model"];instances=[]
  need(source["model"]==model,"actual source primitive model")
  logical={}
  for reference,layout in pair["reference_to_layout_terminal"].items():
   logical[layout]=source["terminals"][reference].lower()
  need(set(logical)==set(dev["terminals"]),"complete source correspondence for probe selection")
  if model=="sg13_lv_nmos":
   need(unit_cases[i]["parameters"]==dev["parameters"],"exact native current MOS dimensions")
   p=dev["parameters"]
   parameters=dict(w=format(p["W"],".12g")+"u",l=format(p["L"],".12g")+"u",
    **{"as":format(p["AS"]*1e-12,".12g"),"ad":format(p["AD"]*1e-12,".12g")},
    ps=format(p["PS"],".12g")+"u",pd=format(p["PD"],".12g")+"u",ng="1",rfmode="1",pre_layout="0",m=format(1/n,".17g"))
   need(parser.number(parameters["m"])*n==1,"exact total physical multiplicity")
   for j in range(n):
    name="XD"+format(i,"04d")+"_s"+str(j);ns=[physical_terminals[i,"D"],gate_nodes[i,j],physical_terminals[i,"S"],physical_terminals[i,"B"]]
    instances.append(dict(name=name,nodes=ns,parameters=parameters,stripe=j))
  else:
   need(dev["parameters"]==source["layout_parameters"],"unchanged actual non-MOS geometry")
   prior=old[source["origin_native_id"]]
   need(prior["instance"]==source["loaded_instance"]and prior["model"]==model,"exact canonical non-MOS source identity")
   need(set(prior["native_parameters"])==set(dev["parameters"]),"complete non-MOS native parameter set")
   need(all(geometry_readback_matches(Decimal(prior["native_parameters"][k]),float(v))for k,v in dev["parameters"].items()),"canonical native-SPICE parameters match current geometry within original one-ULP readback")
   parameters=dict(prior["parameters"]);name="XD"+format(i,"04d")
   if model=="cap_cmim":
    card=caps[i]["export"];need(card[3]=="cap_cmim","same native intrinsic MIM")
    native_params=dict(t.split("=")for t in card[4:])
    need(set(native_params)==set(parameters)=={"w","l"}and all(parser.number(native_params[k])==parser.number(parameters[k])for k in native_params),"same intrinsic MIM canonical dimensions")
    need(owners[graph.find(card[1])]==rows[i,"MIM_TOP"]["wire_component"]and owners[graph.find(card[2])]==rows[i,"MIM_BTM"]["wire_component"],"actual MIM card conductor ownership")
    ns=[wire_map[card[1]],wire_map[card[2]]];parameters=native_params
   else:ns=[physical_terminals[i,t.upper()]for t in prior["compact_model_order"]]
   instances.append(dict(name=name,nodes=ns,parameters=parameters))
  for inst in instances:
   need(all(node is not None for node in inst["nodes"]),"every actual terminal bound")
   out.append([inst["name"],*inst["nodes"],model,*[k+"="+v for k,v in inst["parameters"].items()]])
  records.append(dict(native_id=i,model=model,native_parameters=dev["parameters"],original_source=source,logical_terminals=logical,instances=instances))
 out+=gate_instances
 for row in rc:out.append([row[0],wire_map[row[1]],wire_map[row[2]],row[3]])
 need(len({r[0].lower()for r in out})==len(out),"unique whole circuit instance names")
 interface=[p["name"]for p in sorted(identity["ports"],key=lambda p:p["native_pin_id"])]+["wire_cref"]
 need(set(interface)==set(["dp","dn","cp","cn","xp","xn","yp","yn","avdd","avss","sub","wire_cref","vip","vin","irvx","irvy","ira","irb","irc","ird","irx","iry","ibda","ibdc","ibs0","ibs1"])and len(interface)==26,"complete unchanged full loaded external interface")
 model="nssoc_cdr650_gate_n"+str(n)
 text="\n".join(["* Actual650 devices, physical gate fields and current MIM-aware metal network; not PHY signoff.",
  *gate_fragments,".subckt "+model+" "+" ".join(interface),*[" ".join(r)for r in out],".ends "+model,""])
 contract=dict(model=model,interface=interface,partition=n,devices=records,gate_macros=gate_bindings,body_partition=body,
  metal_node_map=wire_map,native_mim_cards_preserved=capture["native_mim_devices"],physical_devices=650,physical_terminals=2046,
  actual_intrinsic_MOS_instances=200*n,other_intrinsic_instances=450,gate_macros_instantiated=50,physical_gate_contacts=200,
  metal_R=28634,metal_C=18488,actual_MIM_native_attachment_points_preserved=True,intrinsic_total_multiplicity_per_physical_device=1,
  full_loaded_simulation_passed=False,full_phy_accepted=False,final_timing_complete=False,substrate_r_modeled=False,gate_extrinsic_C_included=False)
 return text,contract

def probes(contract):
 n=contract["partition"];physical={d["native_id"]:d for d in contract["devices"]}
 external={p:"0"if p in("avss","sub","wire_cref")else p for p in contract["interface"]}
 def node(value):return external[value]if value in external else"xpd."+value.lower()
 groups={k:{}for k in("npn13g2","sg13_lv_nmos","rppd","cap_cmim","ptap1")}
 names={};logic={}
 for i,d in physical.items():
  names[i]=[]
  for instance in d["instances"]:
   name="xpd."+instance["name"].lower();names[i].append(name)
   record=dict(nodes=[node(x)for x in instance["nodes"]],parameters=instance["parameters"],native_id=i)
   if d["model"]=="npn13g2":record["nx"]=int(parser.number(instance["parameters"]["nx"]))
   groups[d["model"]][name]=record;logic[name]=d["logical_terminals"]
 need({k:len(v)for k,v in groups.items()}==dict(npn13g2=124,sg13_lv_nmos=200*n,rppd=98,cap_cmim=7,ptap1=221),"all full model native probes")
 def candidates(net,terminal="C"):
  return[name for name in groups["npn13g2"]if logic[name][terminal]==net]
 aliases={};sampler={};witnesses={}
 for tag in"abcd":
  for leg,other in(("p","n"),("n","p")):
   net=tag+"q"+leg;opposite=tag+"q"+other
   allnames=candidates(net);chosen=[name for name in allnames if logic[name]["B"]!=opposite]
   need(len(allnames)==2 and len(chosen)==1,"unique actual data-pair collector "+net)
   name=chosen[0];point=groups["npn13g2"][name]["nodes"][0]
   aliases["xpd."+net]=point;sampler[net]=point
   witnesses[net]=dict(device=name,native_id=groups["npn13g2"][name]["native_id"],terminal="C",probe=point,load_f=150e-15,selection="data-pair collector; hold-pair base is opposite output")
 for net in("adp","adn","cdp","cdn","s0p","s0n","s1p","s1n"):
  chosen=candidates(net);need(len(chosen)==1,"unique actual interface collector "+net)
  aliases["xpd."+net]=groups["npn13g2"][chosen[0]]["nodes"][0]
 tails=[];mos_tails=[];mos_tail_groups={};tail_physical=set();tail_origins=set()
 for bias in("ira","irb","irc","ird","irx","iry","ibs0","ibs1"):
  found=[name for name in groups["sg13_lv_nmos"]if logic[name]["G"]==bias and logic[name]["S"]=="avss"and logic[name]["D"]!=bias]
  need(found,"all actual MOS tail currents "+bias)
  for name in found:
   i=groups["sg13_lv_nmos"][name]["native_id"];origin=physical[i]["original_source"]["origin_native_id"]
   tail_physical.add(i);tail_origins.add(origin)
   drain=logic[name]["D"];key=drain if bias in("ira","irb","irc","ird")else drain+":"+str(origin)
   mos_tail_groups.setdefault(bias+":"+key,[]).append(name)
  mos_tails+=found
 need(len(tail_physical)==192 and len(tail_origins)==42 and len(mos_tails)==192*n and len(mos_tail_groups)==16,"complete original42 tail families,192 physical units,16 stages")
 need(sum(map(len,mos_tail_groups.values()))==len(set(mos_tails))==len(mos_tails),"all tail currents counted once")
 for bias in("ibda","ibdc"):
  found=[name for name in groups["npn13g2"]if logic[name]["B"]==bias and logic[name]["E"]=="avss"and logic[name]["C"]!=bias]
  need(len(found)==1,"exact HBT tail "+bias);tails+=found
 vi={}
 for role,base,collector in(("xxp","xp","vin"),("xxn","xn","vip"),("xyp","yp","vip"),("xyn","yn","vin")):
  chosen=[name for name in groups["npn13g2"]if logic[name]["B"]==base and logic[name]["C"]==collector]
  need(len(chosen)==1,"exact actual VI device "+role);vi[role]=chosen[0]
 for role,bias in(("xtx","irvx"),("xty","irvy")):
  chosen=[name for name in groups["npn13g2"]if logic[name]["B"]==bias and logic[name]["E"]=="avss"and logic[name]["C"]!=bias]
  need(len(chosen)==1,"exact actual VI tail "+role);vi[role]=chosen[0]
 for a,b,tail in(("xxp","xxn","xtx"),("xyp","xyn","xty")):
  need(logic[vi[a]]["E"]==logic[vi[b]]["E"]==logic[vi[tail]]["C"],"native VI shared emitter identity")
 return dict(partition=n,groups=groups,ports=[external[p]for p in contract["interface"]],interface=external,aliases=aliases,sampler_points=sampler,
  probe_witnesses=witnesses,tail_names=tails,mos_tail_names=mos_tails,mos_tail_groups=mos_tail_groups,vi_names=vi,physical_mos_tail_count=192,original_mos_tail_families=42)
