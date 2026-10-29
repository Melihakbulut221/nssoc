#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted analytic and falsification controls; never imports an EDA/native module."""
import argparse,base64,copy,io,json,os,sys,tempfile,zlib
from decimal import Decimal,localcontext
from pathlib import Path
from unittest.mock import patch
import cdr_current_dc_contacts as w

def synthetic(nodes,contacts,resistors,capacitors=()):
    cluster=28;component=17;net="$synthetic"
    return dict(native_cluster=cluster,component=component,native_net=net,
      nodes=[dict(native=n,loaded=n)for n in nodes],
      contacts=[dict(device=i+1,loaded_node=n,
        terminal=dict(node=n,anchor=n,native_cluster=cluster,native_net=net,terminal="synthetic"),
        anchor=dict(label=n,wire_component=component,native_cluster=cluster))
        for i,n in enumerate(contacts)],
      incidence=[dict(name=name,kind=kind,a=a,b=b,loaded_a=a,loaded_b=b,
        a_owner=component if a in nodes else 0,b_owner=component if b in nodes else 0,
        value=value,token=value,line=i+1)
        for i,(kind,name,a,b,value)in enumerate(
           [("R",*row)for row in resistors]+[("C",*row)for row in capacitors])],
      synthetic=True)

def screen(target):return w.screen_graph(w.graph_from_target(target))
def pair(result,a,b):
    return next(x for x in result["pair_unit_injections"]
        if x["positive_contact"]==a and x["negative_contact"]==b)

def equal_numbers(actual,expected,label):
    assert len(actual)==len(expected)
    for index,(a,b)in enumerate(zip(actual,expected)):
        w.close(Decimal(a),Decimal(b),label+":"+str(index))

def equal_matrices(actual,expected,label):
    assert len(actual)==len(expected)
    for index,(a,b)in enumerate(zip(actual,expected)):equal_numbers(a,b,label+":"+str(index))

def controls(ctx):
    positive=[];refusals=[];lifecycle=[]
    def reject(name,action):
        try:action()
        except (ValueError,KeyError,TypeError,ArithmeticError)as exc:
            refusals.append(dict(name=name,type=type(exc).__name__,message=str(exc)))
        else:raise AssertionError("did not refuse "+name)
    cfg,authentic,input_proof=w.source_guard()
    assert input_proof["source_guard_complete"]and len(authentic["targets"])==2
    positive.append("authentic complete incidence and 34-file proof census")
    series=synthetic(["A","M","B"],["A","B","M"],[("R1","A","M","2"),("R2","M","B","3")])
    result=screen(series);row=pair(result,"A","B")
    w.close(Decimal(row["effective_resistance_ohm"]),Decimal(5),"series resistance")
    equal_numbers([x["current_a_to_b_A"]for x in row["edge_responses"]],[1,1],"series current")
    equal_numbers([x["power_W"]for x in row["edge_responses"]],[2,3],"series power")
    positive.append("analytic series full edge response")
    matrix=result["effective_resistance_ohm"]
    equal_matrices(matrix,[[0,5,2],[5,0,3],[2,3,0]],"three-terminal matrix")
    assert len(result["reference_unit_injections"])==2 and len(result["pair_unit_injections"])==3
    positive.append("analytic three-terminal resistance and reciprocity")
    parallel=synthetic(["A","B"],["A","B"],[("R1","A","B","2"),("R2","A","B","3")])
    row=pair(screen(parallel),"A","B")
    w.close(Decimal(row["effective_resistance_ohm"]),Decimal("1.2"),"parallel resistance")
    equal_numbers([x["current_a_to_b_A"]for x in row["edge_responses"]],[".6",".4"],"parallel current")
    positive.append("analytic parallel branches")
    balanced=synthetic(["A","B","C","D"],["A","B","C","D"],
      [("R1","A","C","1"),("R2","C","B","1"),("R3","A","D","1"),
       ("R4","D","B","1"),("R5","C","D","7")])
    row=pair(screen(balanced),"A","B")
    w.close(Decimal(row["effective_resistance_ohm"]),Decimal(1),"balanced bridge resistance")
    w.close(Decimal(row["edge_responses"][-1]["current_a_to_b_A"]),Decimal(0),"balanced bridge current")
    positive.append("analytic balanced bridge zero cross-edge current")
    bridge=synthetic(["A","B","C","D"],["A","B","C","D"],
      [("R1","A","C","1"),("R2","C","B","2"),("R3","A","D","3"),
       ("R4","D","B","4"),("R5","C","D","5")])
    row=pair(screen(bridge),"A","B")
    with localcontext()as decimal:
        decimal.prec=80
        w.close(Decimal(row["effective_resistance_ohm"]),Decimal(155)/74,"analytic delta-star resistance")
        w.close(Decimal(row["edge_responses"][-1]["current_a_to_b_A"]),Decimal(1)/37,"analytic bridge current")
    positive.append("analytic unbalanced bridge 155/74 ohm and 1/37 A cross-edge")
    reverse=copy.deepcopy(series)
    reverse["incidence"][0].update(a="M",b="A",loaded_a="M",loaded_b="A")
    row=pair(screen(reverse),"A","B")
    w.close(Decimal(row["edge_responses"][0]["current_a_to_b_A"]),Decimal(-1),"reverse edge current")
    w.close(Decimal(row["edge_responses"][0]["power_W"]),Decimal(2),"reverse edge power")
    positive.append("signed original-edge orientation and nonnegative power")
    cap=synthetic(["A","M","B"],["A","B","M"],[("R1","A","M","2"),("R2","M","B","3")],
       [("C1","A","outside","1e-12"),("C2","M","B","2e-12")])
    cap_result=screen(cap)
    assert cap_result["effective_resistance_ohm"]==result["effective_resistance_ohm"]
    assert cap_result["capacitors_open_for_DC_only"]==cap["incidence"][2:]and cap_result["omitted_capacitor_count"]==2
    positive.append("DC-only capacitor omission preserves complete rows")
    reordered=copy.deepcopy(bridge);reordered["nodes"].reverse();reordered["incidence"].reverse()
    equal_matrices(screen(reordered)["effective_resistance_ohm"],screen(bridge)["effective_resistance_ohm"],"iteration-order invariance")
    positive.append("node and edge iteration do not alter resistance matrix")
    for token in ("0",".5","1.","+2e-3","1E+2"):assert w.number(token)>=0
    positive.append("finite decimal grammar")

    for token in ("NaN","Infinity","1..2","1k","1 2","True","1e","1e101","1e-101"):
        reject("decimal:"+token,lambda token=token:w.number(token))
    reject("zero resistor",lambda:w.number("0",positive=True))
    reject("negative resistor",lambda:w.number("-1",positive=True))
    for name,change in [
      ("duplicate node",lambda t:t["nodes"].append(copy.deepcopy(t["nodes"][0]))),
      ("duplicate contact",lambda t:t["contacts"].append(copy.deepcopy(t["contacts"][0]))),
      ("unknown contact",lambda t:t["contacts"][0].update(loaded_node="outside")),
      ("contact alias",lambda t:t["contacts"][0]["terminal"].update(anchor="M")),
      ("contact native partition",lambda t:t["contacts"][0]["terminal"].update(native_cluster=124)),
      ("duplicate resistor",lambda t:t["incidence"].append(copy.deepcopy(t["incidence"][0]))),
      ("unknown resistor endpoint",lambda t:t["incidence"][0].update(loaded_b="outside")),
      ("raw-loaded endpoint mismatch",lambda t:t["incidence"][0].update(a="B")),
      ("wrong resistor partition",lambda t:t["incidence"][0].update(a_owner=61)),
      ("zero R",lambda t:t["incidence"][0].update(value="0")),
      ("negative R",lambda t:t["incidence"][0].update(value="-1")),
      ("self loop",lambda t:t["incidence"][0].update(b="A",loaded_b="A")),
      ("unsupported element",lambda t:t["incidence"][0].update(kind="L")),
      ("disconnected node",lambda t:t["nodes"].append(dict(native="Z",loaded="Z")))]:
        bad=copy.deepcopy(series);change(bad)
        reject("graph:"+name,lambda bad=bad:w.graph_from_target(bad))
    bad=copy.deepcopy(cap);bad["incidence"][-1]["value"]="-1"
    reject("negative capacitance",lambda:w.graph_from_target(bad))
    bad=copy.deepcopy(cap);bad["incidence"][-1].update(loaded_a="X",loaded_b="Y")
    reject("unrelated capacitor",lambda:w.graph_from_target(bad))
    with localcontext()as decimal:
        decimal.prec=80;graph=w.graph_from_target(series);factors=w.factor(graph)
        voltages=w.solve(graph,factors,"A","B")
        bad=dict(voltages);bad["M"]+=Decimal(".01")
        reject("KCL corrupted interior voltage",lambda:w.response(graph,"A","B",bad))
        bad=dict(voltages);bad["A"]=Decimal(".01")
        reject("reference gauge changed",lambda:w.response(graph,"A","B",bad))
        bad=dict(voltages);bad.pop("M")
        reject("missing full node response",lambda:w.response(graph,"A","B",bad))
        bad=dict(voltages);bad["M"]=Decimal("NaN")
        reject("nonfinite response",lambda:w.response(graph,"A","B",bad))
        reject("unknown injection contact",lambda:w.solve(graph,factors,"A","Z"))
        reject("same injection contact",lambda:w.solve(graph,factors,"A","A"))
        reject("incorrect numerical equality",lambda:w.close(Decimal(1),Decimal(2),"deliberate numerical mismatch"))
    bad=copy.deepcopy(authentic);bad["accepted"]=True
    reject("actual incidence acceptance changed",lambda:w.validate_incidence(bad,cfg))
    bad=copy.deepcopy(authentic);bad["full_current_counts"]["R"]-=1
    reject("actual complete composition changed",lambda:w.validate_incidence(bad,cfg))
    bad=copy.deepcopy(authentic);bad["targets"]["28"]["native_net"]="$680"
    reject("actual current net swapped",lambda:w.validate_incidence(bad,cfg))
    for key,value in (("GITHUB_ACTIONS","false"),("GITHUB_REF","refs/heads/main"),
       ("GITHUB_EVENT_NAME","push"),("GITHUB_RUN_ATTEMPT","2"),("GITHUB_SHA","0"),("GITHUB_RUN_ID","x")):
        env=dict(os.environ);env[key]=value
        reject("context:"+key,lambda env=env:w.context(env))
    for path in ("../outside","/absolute","a/../b"):
        reject("source path:"+path,lambda path=path:w.secure_file(w.ROOT,path))
    with tempfile.TemporaryDirectory()as temp:
        temp=Path(temp);repo=temp/"repo";repo.mkdir()
        # Copy only existing authenticated JSON/text proof into a hosted temporary fixture.
        for name in [w.CONFIG,*cfg["evidence_files"]]:
            path=repo/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(w.secure_file(w.ROOT,name).read_bytes())
        path=repo/cfg["incidence_path"];raw=path.read_bytes();path.write_bytes(raw+b" ")
        reject("authentic incidence bytes changed",lambda:w.source_guard(repo))
        path.write_bytes(raw)
        receipt_path=repo/cfg["receipt_path"];receipt_raw=receipt_path.read_bytes()
        receipt_path.write_bytes(receipt_raw+b" ")
        reject("complete proof receipt bytes changed",lambda:w.source_guard(repo))
        receipt_path.write_bytes(receipt_raw)
        target_name=next(n for n in cfg["evidence_files"]if n.endswith(".log"))
        log=repo/target_name;log_raw=log.read_bytes();log.write_bytes(log_raw+b"x")
        reject("full raw log evidence changed",lambda:w.source_guard(repo))
        log.write_bytes(log_raw)
        config_raw=(repo/w.CONFIG).read_bytes();(repo/w.CONFIG).write_bytes(config_raw+b" ")
        reject("input configuration changed",lambda:w.source_guard(repo))
        (repo/w.CONFIG).write_bytes(config_raw)
        log.unlink();reject("missing full evidence member",lambda:w.source_guard(repo))
        log.write_bytes(log_raw)
        # Actual run() and finalization with small explicit synthetic DC networks.
        synthetic_root=temp/"synthetic";synthetic_root.mkdir()
        (synthetic_root/"incidence.json").write_bytes(w.encode({"synthetic":True}))
        (synthetic_root/"receipt.json").write_bytes(w.encode({"synthetic":True}))
        fake_cfg=dict(incidence_path="incidence.json",receipt_path="receipt.json")
        fake_data=dict(targets={"28":series,"124":parallel})
        fake_proof=dict(synthetic_fixture=True,no_actual_RC_screening=True)
        def source(_root):return fake_cfg,fake_data,fake_proof
        with patch.object(w,"source_guard",source),patch("sys.stdout",io.StringIO())as output:
            passed=w.run(temp/"run-success",ctx,synthetic_root)
        assert passed["status"]=="PASS_CURRENT_DC_CONTACT_SCREEN_NOT_ELECTRICAL_ACCEPTANCE"
        assert passed["networks"]["28"]["pair_count"]==3 and passed["networks"]["124"]["pair_count"]==1
        rows=w.decode(next(x for x in output.getvalue().splitlines()if x.startswith("CURRENT_DC_CONTACT_INDEX ")).split(" ",1)[1])
        assert rows==w.output_map(temp/"run-success")
        chunks=[json.loads(x.split(" ",1)[1])for x in output.getvalue().splitlines()if x.startswith("CURRENT_DC_CONTACT_CHUNK ")]
        for name in rows:
            pieces=sorted([x for x in chunks if x["name"]==name],key=lambda x:x["index"])
            restored=zlib.decompress(b"".join(base64.b64decode(x["base64"])for x in pieces))
            assert restored==(temp/"run-success"/name).read_bytes()
        lifecycle.append("actual run complete outputs and byte-exact chunk roundtrip using synthetic networks")
        primary=RuntimeError("synthetic second network failure");real_screen=w.screen_graph
        def fail_second(graph):
            if len(graph["nodes"])==2:raise primary
            return real_screen(graph)
        with patch.object(w,"source_guard",source),patch.object(w,"screen_graph",fail_second),patch("sys.stdout",io.StringIO()):
            try:w.run(temp/"run-partial",ctx,synthetic_root)
            except RuntimeError as exc:assert exc is primary
            else:raise AssertionError("missing primary")
        assert (temp/"run-partial/network-28.json").is_file()
        lifecycle.append("actual run retains complete first network on second-network primary failure")
        real_write=w.write_new
        def save_failure(path,raw):
            if Path(path).name=="result.json":raise OSError("synthetic final save failure")
            return real_write(path,raw)
        with patch.object(w,"source_guard",source),patch.object(w,"screen_graph",fail_second),patch.object(w,"write_new",save_failure),patch("sys.stdout",io.StringIO())as output:
            try:w.run(temp/"run-save",ctx,synthetic_root)
            except RuntimeError as exc:assert exc is primary
            else:raise AssertionError("primary replaced")
        fallback=json.loads(next(x for x in output.getvalue().splitlines()if x.startswith("CURRENT_DC_CONTACT_FALLBACK ")).split(" ",1)[1])
        assert fallback["status"]=="FAIL_CURRENT_DC_CONTACT_SCREEN"and "network-28.json"in fallback["available_outputs"]
        lifecycle.append("actual run primary plus terminal-save failure retains complete fallback")
        with patch.object(w,"source_guard",side_effect=primary),patch.object(w,"emit",side_effect=OSError("synthetic emitter failure")):
            try:w.run(temp/"run-source",ctx,synthetic_root)
            except RuntimeError as exc:assert exc is primary
            else:raise AssertionError("primary replaced by emitter")
        lifecycle.append("actual run source primary survives emitter failure")
        reject("actual run refuses output overwrite",lambda:w.run(temp/"run-success",ctx,synthetic_root))
        lifecycle.append("actual run no-clobber output")
    assert len(positive)==10 and len(refusals)==52 and len(lifecycle)==5,(len(positive),len(refusals),len(lifecycle))
    return dict(status="PASS_CURRENT_DC_CONTACT_SOURCE_CONTROLS",current_context=ctx,
      counts=dict(positive=len(positive),refusal=len(refusals),lifecycle=len(lifecycle)),
      positive=positive,refusals=refusals,lifecycle=lifecycle,
      authentic_input_bytes_verified=True,authentic_network_solve_executed=False,
      all_computed_networks_synthetic=True,**w.FLAGS)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    report=dict(status="FAIL_CURRENT_DC_CONTACT_SOURCE_CONTROLS",**w.FLAGS);primary=None
    try:report=controls(w.context(os.environ))
    except BaseException as exc:primary=exc;report["error"]=dict(type=type(exc).__name__,message=str(exc))
    try:w.write_new(args.output,w.encode(report))
    except BaseException:
        if primary is None:raise
        try:print("CURRENT_DC_CONTROL_FALLBACK "+json.dumps(report,sort_keys=True),flush=True)
        except BaseException:pass
    if primary is not None:raise primary
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
