#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted DC-only screening of authenticated derived resistor incidence; no CAD."""
import argparse,base64,hashlib,json,os,re,sys,zlib
from decimal import Decimal,localcontext,ROUND_HALF_EVEN
from itertools import combinations
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent.parent
BRANCH="codex/cdr-current-dc-contact-screen"
CONFIG="scripts/cdr-current-dc-contact-inputs.json"
CONFIG_SHA="990d9d58c8a1d8060ce02b6f0da6354c7b57cbe29244c8e5e6c63267368604da"
PRECISION=80
TOL=Decimal("1e-40")
FLAGS=dict(physical_acceptance=False,electrical_acceptance=False,full_phy_accepted=False,
    geometry_changed=False,new_transistor_simulation=False,transient_recovery_proven=False,
    geometric_bridge_attribution_proven=False,dominant_path_proven=False,causality_proven=False,
    DC_analysis_only=True,native_archive_acquired=False,native_CAD_executed=False)

def require(value,message):
    if not value:raise ValueError(message)

def encode(value):return (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()
def digest(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def canonical(value):return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()

def decode(raw):
    def pairs(items):
        value={}
        for key,item in items:
            require(key not in value,"duplicate JSON key");value[key]=item
        return value
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError("nonfinite JSON")))

def secure_file(root,name):
    path=PurePosixPath(name)
    require(type(name)is str and str(path)==name and not path.is_absolute()
        and not any(p in ("",".","..")for p in path.parts),"unsafe source path")
    result=Path(root)
    for part in path.parts:
        result=result/part;require(not result.is_symlink(),"source symlink")
    require(result.is_file(),"missing source file: "+name)
    return result

def context(env):
    require(env.get("GITHUB_ACTIONS")=="true"and env.get("RUNNER_OS")=="Linux","hosted Linux only")
    require(env.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc","repository")
    require(env.get("GITHUB_EVENT_NAME")=="workflow_dispatch","manual only")
    require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH,"screen branch")
    require(env.get("GITHUB_RUN_ATTEMPT")=="1","attempt one")
    source=env.get("GITHUB_SHA","");run=env.get("GITHUB_RUN_ID","")
    require(re.fullmatch("[0-9a-f]{40}",source)and re.fullmatch("[1-9][0-9]*",run),"source/run")
    return dict(source=source,run_id=int(run),attempt=1,derived_JSON_only=True,native_executed=False)

def number(text,positive=False):
    require(type(text)is str and re.fullmatch(
        r"[+-]?(?:[0-9]+(?:[.][0-9]*)?|[.][0-9]+)(?:[eE][+-]?[0-9]+)?",text),"decimal literal")
    value=Decimal(text)
    require(value.is_finite()and (value>0 if positive else value>=0),"finite nonnegative value")
    require(value==0 or -100<=value.adjusted()<=100,"bounded decimal exponent")
    return value

def close(a,b,label,scale=None):
    scale=max(Decimal(1),abs(a),abs(b))if scale is None else max(Decimal(1),abs(scale))
    error=abs(a-b);require(error<=TOL+TOL*scale,label)
    return error

def validate_incidence(value,cfg):
    require(value.get("status")=="CURRENT_RC_CONTACT_INCIDENCE_READBACK_ONLY","incidence status")
    for key in ("accepted","causality_proven","dominant_path_proven","electrical_acceptance",
                "full_phy_accepted","geometry_changed","native_CAD_executed","new_simulation","physical_acceptance"):
        require(value.get(key)is False,"incidence unqualified flag: "+key)
    for key in ("complete_device_mapping_exact","loaded_model_R_C_tokens_exact","native_export_R_multiset_exact"):
        require(value.get(key)is True,"incidence source gate: "+key)
    require(value["full_current_counts"]==cfg["expected_counts"],"whole composition")
    require(len(value["all_full_component_rows"])==113 and set(value["targets"])==set(cfg["targets"]),"complete components/targets")
    for key,spec in cfg["targets"].items():
        target=value["targets"][key]
        for name in ("native_cluster","component","native_net"):require(target[name]==spec[name],"current target "+name)
        require(target["canonical_to_loaded_R_edge_value_multiset_equal"]is True,"canonical loaded R binding")
        require(target["current_flow_or_effective_resistance_computed"]is False
          and target["geometric_bridge_edge_assignment_proven"]is False
          and target["primitive_coordinates_interpreted"]is False,"prior scope")
        require(len(target["nodes"])==spec["nodes"]and len(target["contacts"])==spec["contacts"],"target node/contact counts")
        require([x["loaded_node"]for x in target["contacts"]]==spec["loaded_contacts"],"exact loaded contacts")
        components=[row for row in value["all_full_component_rows"]if row["component"]==target["component"]]
        require(len(components)==1 and components[0]["nodes"]==spec["nodes"]
          and len(components[0]["probes"])==spec["contacts"]
          and set(components[0]["probes"])=={x["terminal"]["anchor"]for x in target["contacts"]},
          "complete target component membership")
        require(sum(x["kind"]=="R"for x in target["incidence"])==spec["resistors"]
          and sum(x["kind"]=="C"for x in target["incidence"])==spec["capacitors"],"target RC counts")
        graph_from_target(target)
    return value

def source_guard(root=ROOT):
    raw=secure_file(root,CONFIG).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==CONFIG_SHA,"configuration bytes")
    cfg=decode(raw);require(cfg["schema"]=="current-dc-contact-inputs-v1","configuration schema")
    require(cfg["precision"]==PRECISION and number(cfg["numerical_relative_tolerance"])==TOL
      and number(cfg["numerical_absolute_tolerance"])==TOL,"numeric method") 
    observed={}
    for name,pin in cfg["evidence_files"].items():
        data=secure_file(root,name).read_bytes();observed[name]=digest(data)
        require(observed[name]==pin,"full evidence bytes: "+name)
    receipt=decode(secure_file(root,cfg["receipt_path"]).read_bytes())
    old_files={k:v for k,v in cfg["evidence_files"].items()if k!=cfg["receipt_path"]}
    require(receipt["files"]==old_files,"complete receipt inventory")
    origin=cfg["producer_readback"]
    require(receipt["run"]==origin["run"]and receipt["source"]==origin["source"]
      and receipt["attempt"]==1 and receipt["terminal"]=="success","actual readback producer")
    require(receipt["physical_acceptance"]is False and receipt["full_phy_accepted"]is False,"no transferred acceptance")
    report=receipt["readback"]
    require(report["status"]=="PASS_CURRENT_RC_CONTACT_READBACK_NOT_ACCEPTANCE"
      and report["complete_input_members"]==6647 and report["producer"]==cfg["original_rc_producer"],"original full input lineage")
    require(report["reservation"]["release_id"]==origin["release_id"]
      and report["reservation"]["source"]==origin["source"],"readback reservation lineage")
    incidence_raw=secure_file(root,cfg["incidence_path"]).read_bytes()
    require(report["analysis"]==digest(incidence_raw)==old_files[cfg["incidence_path"]],"complete incidence bytes")
    incidence=validate_incidence(decode(incidence_raw),cfg)
    return cfg,incidence,dict(configuration=digest(raw),evidence_files=observed,
      incidence=digest(incidence_raw),proof_commit=cfg["proof_commit"],
      readback_producer=origin,original_rc_producer=cfg["original_rc_producer"],
      complete_original_native_members=6647,source_guard_complete=True,**FLAGS)

def graph_from_target(target):
    pairs=target["nodes"];require(type(pairs)is list and 2<=len(pairs)<=256,"node list")
    loaded=[p["loaded"]for p in pairs];native=[p["native"]for p in pairs]
    require(all(type(x)is str and x for x in loaded+native),"node names")
    require(len(set(loaded))==len(loaded)and len(set(native))==len(native),"unique exact node map")
    mapping=dict(zip(native,loaded));nodes=set(loaded)
    contacts=target["contacts"];ports=[x["loaded_node"]for x in contacts]
    require(2<=len(ports)<=16 and len(set(ports))==len(ports)and set(ports)<=nodes,"unique contact nodes")
    for contact in contacts:
        terminal=contact["terminal"]
        require(terminal["node"]==contact["loaded_node"]and mapping.get(terminal["anchor"])==contact["loaded_node"],"contact alias")
        require(terminal["native_cluster"]==target["native_cluster"]and terminal["native_net"]==target["native_net"],"contact partition")
        anchor=contact["anchor"]
        require(anchor["label"]==terminal["anchor"]and anchor["wire_component"]==target["component"]
          and anchor["native_cluster"]==target["native_cluster"],"contact anchor")
    edges=[];caps=[];names=set();adj={n:set()for n in nodes}
    require(type(target["incidence"])is list and len(target["incidence"])<=4096,"incidence bounds")
    for row in target["incidence"]:
        require(type(row["name"])is str and row["name"]and row["name"]not in names,"unique element")
        names.add(row["name"]);require(row["kind"]in ("R","C"),"element kind")
        require(type(row["line"])is int and row["line"]>0 and type(row["token"])is str,"original line/token")
        value=number(row["value"],positive=row["kind"]=="R")
        a,b=row["loaded_a"],row["loaded_b"]
        require(type(a)is str and type(b)is str and a!=b,"distinct edge endpoints")
        if row["kind"]=="R":
            require(a in nodes and b in nodes and mapping.get(row["a"])==a
              and mapping.get(row["b"])==b,"exact resistor endpoints")
            require(row["a_owner"]==target["component"]and row["b_owner"]==target["component"],"resistor partition")
            edges.append(dict(name=row["name"],a=a,b=b,resistance=value,source=row))
            adj[a].add(b);adj[b].add(a)
        else:
            require(a in nodes or b in nodes,"capacitor incidence unrelated to target")
            for raw_name,loaded_name,owner in ((row["a"],a,row["a_owner"]),(row["b"],b,row["b_owner"])):
                if loaded_name in nodes:
                    require(mapping.get(raw_name)==loaded_name and owner==target["component"],"capacitor local identity")
            caps.append(row)
    require(edges and len(edges)<=2048,"resistor bounds")
    seen={loaded[0]};todo=[loaded[0]]
    while todo:
        for node in adj[todo.pop()]-seen:seen.add(node);todo.append(node)
    require(seen==nodes,"disconnected resistor network")
    return dict(nodes=sorted(nodes),contacts=ports,edges=edges,capacitors=caps,original=target)

def factor(graph):
    nodes=[n for n in graph["nodes"]if n!=graph["contacts"][0]]
    index={name:i for i,name in enumerate(nodes)};size=len(nodes)
    matrix=[[Decimal(0)for _ in nodes]for _ in nodes]
    for edge in graph["edges"]:
        conductance=Decimal(1)/edge["resistance"];a=index.get(edge["a"]);b=index.get(edge["b"])
        if a is not None:matrix[a][a]+=conductance
        if b is not None:matrix[b][b]+=conductance
        if a is not None and b is not None:matrix[a][b]-=conductance;matrix[b][a]-=conductance
    lower=[[Decimal(int(i==j))for j in range(size)]for i in range(size)];diag=[]
    for j in range(size):
        pivot=matrix[j][j]-sum((lower[j][k]*lower[j][k]*diag[k]for k in range(j)),Decimal(0))
        require(pivot.is_finite()and pivot>0,"nonpositive reduced Laplacian pivot")
        diag.append(pivot)
        for i in range(j+1,size):
            lower[i][j]=(matrix[i][j]-sum((lower[i][k]*lower[j][k]*diag[k]for k in range(j)),Decimal(0)))/pivot
    return nodes,lower,diag

def solve(graph,factors,positive,negative):
    require(positive in graph["contacts"]and negative in graph["contacts"]and positive!=negative,"unit injection contacts")
    nodes,lower,diag=factors
    rhs=[Decimal(int(n==positive)-int(n==negative))for n in nodes]
    y=[]
    for i,value in enumerate(rhs):y.append(value-sum((lower[i][j]*y[j]for j in range(i)),Decimal(0)))
    z=[value/diag[i]for i,value in enumerate(y)];x=[Decimal(0)]*len(nodes)
    for i in range(len(nodes)-1,-1,-1):
        x[i]=z[i]-sum((lower[j][i]*x[j]for j in range(i+1,len(nodes))),Decimal(0))
    return {graph["contacts"][0]:Decimal(0),**dict(zip(nodes,x))}

def response(graph,positive,negative,voltages):
    require(set(voltages)==set(graph["nodes"])and all(type(v)is Decimal and v.is_finite()for v in voltages.values()),"full finite voltages")
    require(voltages[graph["contacts"][0]]==0,"reference gauge")
    require(positive in graph["contacts"]and negative in graph["contacts"]and positive!=negative,"unit injection contacts")
    balance={n:Decimal(0)for n in graph["nodes"]};scale=dict(balance);edges=[];power=Decimal(0)
    for edge in graph["edges"]:
        drop=voltages[edge["a"]]-voltages[edge["b"]]
        current=drop/edge["resistance"];dissipation=current*current*edge["resistance"]
        require(dissipation.is_finite()and dissipation>=0,"nonnegative edge dissipation")
        balance[edge["a"]]+=current;balance[edge["b"]]-=current
        scale[edge["a"]]+=abs(current);scale[edge["b"]]+=abs(current);power+=dissipation
        edges.append(dict(name=edge["name"],a=edge["a"],b=edge["b"],
          resistance_ohm=str(edge["resistance"]),voltage_a_minus_b_V=str(drop),
          current_a_to_b_A=str(current),power_W=str(dissipation),original_incidence=edge["source"]))
    residuals={}
    for node in graph["nodes"]:
        expected=Decimal(int(node==positive)-int(node==negative))
        residuals[node]=str(close(balance[node],expected,"KCL: "+node,scale[node]))
    terminal_power=voltages[positive]-voltages[negative]
    require(terminal_power>0,"positive effective DC resistance")
    error=close(power,terminal_power,"total power equals injected terminal power")
    return dict(positive_contact=positive,negative_contact=negative,injection_A="1",
      other_contact_boundary="zero external current; internal voltages solved, no clamping",
      reference_contact=graph["contacts"][0],reference_voltage_V="0",
      effective_resistance_ohm=str(terminal_power),
      node_voltages_V={n:str(voltages[n])for n in graph["nodes"]},edge_responses=edges,
      checks=dict(KCL_residual_A=residuals,total_dissipation_W=str(power),
        terminal_injection_power_W=str(terminal_power),power_error_W=str(error),
        absolute_tolerance=str(TOL),relative_tolerance=str(TOL)))

def screen_graph(graph):
    with localcontext()as ctx:
        ctx.prec=PRECISION;ctx.rounding=ROUND_HALF_EVEN
        factors=factor(graph);ports=graph["contacts"];reference=ports[0]
        basis=[response(graph,p,reference,solve(graph,factors,p,reference))for p in ports[1:]]
        z=[[Decimal(0)for _ in ports]for _ in ports]
        for j,row in enumerate(basis,1):
            for i,port in enumerate(ports):z[i][j]=Decimal(row["node_voltages_V"][port])
        reciprocity=[]
        for i,j in combinations(range(len(ports)),2):
            error=close(z[i][j],z[j][i],"contact reciprocity")
            reciprocity.append(dict(i=ports[i],j=ports[j],error_ohm=str(error)))
        cases=[];effective=[[Decimal(0)for _ in ports]for _ in ports];consistency=[]
        for i,j in combinations(range(len(ports)),2):
            row=response(graph,ports[i],ports[j],solve(graph,factors,ports[i],ports[j]))
            resistance=Decimal(row["effective_resistance_ohm"])
            expected=z[i][i]+z[j][j]-z[i][j]-z[j][i]
            error=close(resistance,expected,"pair versus multi-terminal impedance")
            effective[i][j]=effective[j][i]=resistance
            cases.append(row);consistency.append(dict(i=ports[i],j=ports[j],error_ohm=str(error)))
        return dict(schema="current-contact-dc-network-v1",scope="Linear passive DC resistor network only",
          decimal_precision=PRECISION,rounding="ROUND_HALF_EVEN",nodes=graph["nodes"],contact_order=ports,
          reference_contact=reference,contact_impedance_ohm=[[str(x)for x in row]for row in z],
          effective_resistance_ohm=[[str(x)for x in row]for row in effective],
          reference_unit_injections=basis,pair_unit_injections=cases,
          reciprocity_checks=reciprocity,multi_terminal_pair_checks=consistency,
          original_target=graph["original"],capacitors_open_for_DC_only=graph["capacitors"],
          omitted_capacitor_count=len(graph["capacitors"]),
          capacitor_omission_is_not_valid_for_original_transient=True,
          boundary="One +1 A/-1 A contact pair; all other contact external currents zero; no transistor model or supply is attached.",
          **FLAGS)

def write_new(path,raw):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    require(not path.exists()and not path.is_symlink(),"output no overwrite")
    with path.open("xb")as stream:stream.write(raw)

def output_map(out):
    result={}
    for path in sorted(Path(out).rglob("*")):
        require(not path.is_symlink(),"output symlink")
        if path.is_file():result[path.relative_to(out).as_posix()]=digest(path.read_bytes())
    return result

def emit(out):
    rows=output_map(out);print("CURRENT_DC_CONTACT_INDEX "+json.dumps(rows,sort_keys=True),flush=True)
    for name,pin in rows.items():
        packed=zlib.compress((Path(out)/name).read_bytes(),9)
        pieces=[packed[i:i+12000]for i in range(0,len(packed),12000)]or[b""]
        for index,piece in enumerate(pieces):
            print("CURRENT_DC_CONTACT_CHUNK "+json.dumps(dict(name=name,index=index,chunks=len(pieces),
                **pin,encoding="zlib-base64",base64=base64.b64encode(piece).decode()),sort_keys=True),flush=True)

def run(out,ctx,root=ROOT):
    out=Path(out);require(not out.exists()and not out.is_symlink(),"new output directory")
    out.mkdir(parents=True);primary=None;report=dict(status="FAIL_CURRENT_DC_CONTACT_SCREEN",context=ctx,**FLAGS)
    try:
        cfg,incidence,proof=source_guard(root)
        write_new(out/"input-proof.json",encode(proof))
        for key in ("incidence_path","receipt_path"):
            write_new(out/"inputs"/Path(cfg[key]).name,secure_file(root,cfg[key]).read_bytes())
        report["input_proof"]=proof;report["networks"]={}
        for key in sorted(incidence["targets"],key=int):
            result=screen_graph(graph_from_target(incidence["targets"][key]))
            path=out/("network-"+key+".json");write_new(path,encode(result))
            report["networks"][key]=dict(file=path.name,**digest(path.read_bytes()),
              node_count=len(result["nodes"]),contact_count=len(result["contact_order"]),
              pair_count=len(result["pair_unit_injections"]),basis_count=len(result["reference_unit_injections"]))
        report["status"]="PASS_CURRENT_DC_CONTACT_SCREEN_NOT_ELECTRICAL_ACCEPTANCE"
    except BaseException as exc:
        primary=exc;report["error"]=dict(type=type(exc).__name__,message=str(exc))
    finally:
        try:
            report["available_outputs"]=output_map(out);write_new(out/"result.json",encode(report))
        except BaseException as exc:
            if primary is None:primary=exc
            report["status"]="FAIL_CURRENT_DC_CONTACT_SCREEN"
            report["final_write_error"]=dict(type=type(exc).__name__,message=str(exc))
            try:
                report["available_outputs"]=output_map(out)
                print("CURRENT_DC_CONTACT_FALLBACK "+json.dumps(report,sort_keys=True,allow_nan=False),flush=True)
            except BaseException:pass
        try:emit(out)
        except BaseException:
            if primary is None:raise
    if primary is not None:raise primary
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    run(args.output,context(os.environ))
if __name__=="__main__":main()
