#!/usr/bin/env python3
"""Actual construction reductions and lifetime-aware target value ancestry; no physical acceptance."""
import argparse,collections,hashlib,math,os,shutil,subprocess,types
from pathlib import Path
import cloud_magic_resistor_coefficients as c
import magic_resistor_target_trace as t
b=c.b
ROOT=b.ROOT
require=b.require
decode=b.decode
encode=b.encode
write=b.write
pin=b.pin
frozen=b.frozen
source_census=b.source_census
validate_coefficients=c.validate_coefficients
SPEC="scripts/magic-resistor-ancestry-patch.json"
PAYLOAD="scripts/magic_resistor_provenance_trace_v3.inc"
SOURCE_TEXT="docs/evidence/magic-resistor-qualified-reduction-source-20261030.json"

def qualified_payload(root=ROOT):
    spec=decode(frozen.regular(root,SPEC).read_bytes())
    old=c.qualified_payload(root).decode()
    require(old.count("NSSOC resistor provenance v2.")==1 and
      old.count("nssoc_resistor_provenance_v2")==1 and old.count(c.END)==1,"exact v2 payload seams")
    expected=old.replace("NSSOC resistor provenance v2.","NSSOC resistor provenance v3.")
    expected=expected.replace("nssoc_resistor_provenance_v2","nssoc_resistor_provenance_v3")
    expected=expected.replace(c.END,spec["extra_payload_text"]+"\n"+c.END).encode()
    raw=frozen.regular(root,PAYLOAD).read_bytes()
    require(raw==expected and pin(frozen.regular(root,PAYLOAD))==
      {k:spec["payload"][k]for k in ("bytes","sha256")},"exact v3 additive diagnostic payload")
    return raw,spec

def source_guard(expected,root=ROOT):
    result=c.source_guard(expected,root);_,spec=qualified_payload(root)
    old=decode(frozen.regular(root,b.CONFIG).read_bytes())["source_producer"]["candidate"]
    require(len(spec["before"])==len(spec["after"])==6 and len(spec["rules"])==8,"six source/eight reduction insertions")
    require(all(v["sha256"]==old[n]for n,v in spec["before"].items()),"actual qualified six source identities")
    return result

def derive(sources,root=ROOT):
    payload,spec=qualified_payload(root)
    require({n:dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest())for n,v in sources.items()}==
      spec["before"],"complete actual six source inputs")
    rules=decode(frozen.regular(root,b.historical.SPEC).read_bytes())["rules"]+spec["rules"]
    after=b.trace_sources(sources,{n:v["sha256"]for n,v in spec["before"].items()},rules,
      {"scripts/magic_resistor_provenance_trace.inc":payload})
    require({n:dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest())for n,v in after.items()}==
      spec["after"],"exact six source derived identities")
    return after,rules

def instrument_source(baseline,out,config,root=ROOT):
    _,spec=qualified_payload(root)
    sources={n:(baseline/n).read_bytes()for n in spec["before"]}
    after,rules=derive(sources,root)
    target=out/"trace-source";shutil.copytree(baseline,target)
    for n,raw in after.items():(target/n).write_bytes(raw)
    final=source_census(target);initial=source_census(baseline)
    require(set(final)==set(initial)and {n for n in final if final[n]!=initial[n]}==set(after),
      "only six diagnostic source changes")
    write(out/"trace-source-derivation.json",encode(dict(before=initial,after=final,rules=rules,
      all_original_bytes_reverse_exact=True,numerical_statements_changed=False,
      instrumentation="nssoc_resistor_provenance_v3",payload=pin(frozen.regular(root,PAYLOAD)),
      diagnostic_format_errors_are_compiler_errors=True,reduced_element_ownership_proved=False)))
    return target,final

def validate_trace(path,emitted_count,expected_lines=None):
    counts=collections.Counter();seq=0;epochs=0;active=False;footer=None;snapshot=None;seen_start=False;emitted=[]
    with path.open("rb")as stream:
        for line in stream:
            require(footer is None,"records after footer")
            r=decode(line);e=r.get("event");require(r.get("schema")==1,"trace schema");counts[e]+=1
            if e=="trace_start":
                require(not seen_start and seq==0 and counts[e]==1,"trace first record")
                require(r["instrumentation"]=="nssoc_resistor_provenance_v3"and r["resistor_footprint_is_not_inferred"]is True,"trace identity")
                seen_start=True;continue
            require(seen_start,"missing trace start")
            if e=="trace_end":
                require(r["records_before_footer"]==seq and r["epochs"]==epochs and r["net_still_open"]is False
                  and r["physical_ownership_proved"]is False and not active and snapshot is None,"complete trace footer")
                footer=r;continue
            seq+=1;require(r.get("seq")==seq,"contiguous trace sequence")
            if e=="net_begin":
                require(not active,"nested trace net");active=True;epochs+=1
                require(r["physical_ownership_proved"]is False and isinstance(r["net_name_hex"],str),"net provenance")
                bytes.fromhex(r["net_name_hex"])
            require(r.get("epoch")==epochs and epochs>0,"trace epoch")
            if e=="net_end":require(active,"net end without begin");active=False
            elif e=="snapshot_begin":
                require(snapshot is None and r["phase"]in ("before_simplify","after_simplify"),"snapshot begin")
                snapshot=[r["phase"],0]
            elif e=="snapshot_resistor":
                require(snapshot is not None and r["phase"]==snapshot[0]and r["index"]==snapshot[1],"snapshot sequence")
                snapshot[1]+=1
            elif e=="snapshot_end":
                require(snapshot==[r["phase"],r["count"]],"snapshot complete count");snapshot=None
            require(e in ("net_begin","net_end","create_tile","create_contact","snapshot_begin","snapshot_resistor",
              "snapshot_end","emitted_resistor","emitted_orphan_zero","reduction","delete_resistor"),"unknown trace event")
            if "rr_value_milliohms_hex"in r:
                value=float.fromhex(r["rr_value_milliohms_hex"])
                require(math.isfinite(value)and value>=0,"finite native resistance observation")
                require(type(r["rr_tt"])is int and type(r["type_index_valid"])is bool,"typed material observation")
            if "rr_value_milliohms_hex"in r:validate_coefficients(r)
            if e=="reduction":
                require(r["kind"]in ("series","parallel","triangle")and r["phase"]in ("before","after"),"reduction event shape")
                for m in r["members"]:
                    validate_coefficients(m)
                    require(math.isfinite(float.fromhex(m["rr_value_milliohms_hex"])),"finite reduction value")
            if e=="delete_resistor":
                require(math.isfinite(float.fromhex(r["deleted_value_milliohms_hex"])),"finite deleted value")
            if expected_lines is not None and e in ("emitted_resistor","emitted_orphan_zero"):
                first=r["node1"]["name_hex"]if e=="emitted_resistor"else r["node1_name_hex"]
                second=r["node2"]["name_hex"]if e=="emitted_resistor"else r["node2_name_hex"]
                emitted.append(b'resist "'+bytes.fromhex(first)+b'" "'+bytes.fromhex(second)+b'" '+r["ext_value_token"].encode())
            if e in ("create_tile","create_contact","emitted_resistor","emitted_orphan_zero"):
                require(r["final_footprint_proved"]is False,"no reduced footprint ownership")
    require(footer is not None and counts["trace_start"]==counts["trace_end"]==1,"trace complete")
    require(counts["create_tile"]>0 and counts["create_contact"]>0 and counts["snapshot_resistor"]>0,"actual constructor observations")
    require(counts["emitted_resistor"]+counts["emitted_orphan_zero"]==emitted_count,"all native resistor emissions observed")
    require(counts["net_begin"]==counts["net_end"]==epochs,"all construction epochs closed")
    if expected_lines is not None:require(emitted==expected_lines,"every trace emitted endpoint/value/order matches native file")
    return dict(status="PASS_COMPLETE_ACTUAL_RESISTOR_TRACE_NOT_REDUCED_OWNERSHIP",counts=dict(counts),
      trace=pin(path),epochs=epochs,records=seq,reduced_element_ownership_proved=False)


def replay(records,target):
    require(records and records[0]["event"]=="net_begin","epoch begins with construction")
    require(len({r["epoch"]for r in records})==1 and
      [r["seq"]for r in records]==list(range(records[0]["seq"],records[-1]["seq"]+1)),
      "complete contiguous target epoch")
    active={};nodes={};operations=[];deletions=[];emitted=[];pending=None
    def value(row,key="rr_value_milliohms_hex"):
        v=row[key]
        require(type(v)is str and math.isfinite(float.fromhex(v)),"finite native float observation")
        return v
    def current(row,key="rr_value_milliohms_hex"):
        p=row["resistor_address"];require(p in active,"unobserved or retired address")
        n=active[p];require(nodes[n]["value"]==value(row,key),"unobserved native value change")
        return n
    for r in records:
        event=r["event"]
        if event in ("create_tile","create_contact"):
            require(pending is None and r["resistor_address"]not in active,"unretired address recreation")
            n="constructor:"+str(r["seq"])
            nodes[n]=dict(kind=event,value=value(r),parents=[],record=r,constructor_geometry_provenance_only=True)
            active[r["resistor_address"]]=n
        elif event=="reduction":
            kind=r["kind"];phase=r["phase"];members=r["members"]
            require(kind in ("series","parallel","triangle")and phase in ("before","after"),"known reduction transition")
            addresses=[m["resistor_address"]for m in members]
            require(len(set(addresses))==len(addresses)and [m["slot"]for m in members]==list(range(len(members))),"unique ordered operand slots")
            if phase=="before":
                require(pending is None and len(members)==(3 if kind=="triangle"else 2),"complete reduction operands")
                pending=dict(kind=kind,record=r,parents=[current(m)for m in members],addresses=addresses)
            else:
                require(pending is not None and pending["kind"]==kind,"paired reduction kind")
                wanted=pending["addresses"]if kind=="triangle"else pending["addresses"][:1]
                require(addresses==wanted,"exact surviving operand identity")
                for i,m in enumerate(members):
                    n="reduction:"+str(r["seq"])+":"+str(i)
                    nodes[n]=dict(kind=kind,value=value(m),parents=pending["parents"],
                      output_index=i,before=pending["record"],after=r,
                      native_arithmetic_observed_not_recomputed=True,physical_ownership_proved=False)
                    active[m["resistor_address"]]=n
                operations.append(dict(kind=kind,before_seq=pending["record"]["seq"],after_seq=r["seq"]))
                pending=None
        elif event=="delete_resistor":
            require(pending is None,"deletion inside unclosed value transition")
            n=current(r,"deleted_value_milliohms_hex")
            deletions.append(dict(node=n,record=r));del active[r["resistor_address"]]
        elif event in ("snapshot_resistor","emitted_resistor"):
            require(pending is None,"observation inside unclosed transition")
            n=current(r)
            if event=="emitted_resistor":emitted.append(dict(node=n,record=r))
        elif event=="emitted_orphan_zero":
            raise AssertionError("orphan output has no target constructor ancestry")
    require(pending is None,"unclosed reduction")
    expected=[r["raw"]for r in target["native_primitive_records"]if r["tokens"][0]=="resist"]
    require([t.emitted_line(e["record"])for e in emitted]==expected,"all current target native output rows")
    candidates=collections.defaultdict(list)
    for row in target["canonical_incidence"]:
        if row["kind"]=="R":candidates[t.edge_key(row["a"],row["b"],row["token"])].append(row)
    require(collections.Counter(t.edge_key(t.name(e["record"]["node1"]["name_hex"]),
      t.name(e["record"]["node2"]["name_hex"]),e["record"]["ext_value_token"])for e in emitted)==
      collections.Counter({k:len(v)for k,v in candidates.items()}),"complete current SPICE multiplicity")
    for e in emitted:
        r=e["record"];e["canonical_candidates"]=candidates[t.edge_key(t.name(r["node1"]["name_hex"]),
          t.name(r["node2"]["name_hex"]),r["ext_value_token"])]
        seen=set();todo=[e["node"]]
        while todo:
            n=todo.pop()
            if n in seen:continue
            require(n in nodes,"missing ancestry node")
            seen.add(n);todo.extend(nodes[n]["parents"])
        e["ancestry_nodes"]=sorted(seen)
        e["constructor_nodes"]=sorted(n for n in seen if not nodes[n]["parents"])
        e["operation_kinds"]=sorted({nodes[n]["kind"]for n in seen if nodes[n]["parents"]})
        e["all_observed_value_ancestry_complete"]=True
        e["physical_ownership_proved"]=False
    return dict(schema=1,epoch=records[0]["epoch"],component=target["component"],native_net=target["native_net"],
      native_cluster=target["native_cluster"],nodes=nodes,operations=operations,deletions=deletions,emitted=emitted,
      counts=dict(events=len(records),constructors=sum(not x["parents"]for x in nodes.values()),
        graph_nodes=len(nodes),operations=len(operations),deletions=len(deletions),emitted=len(emitted)),
      all_observed_target_value_ancestry_complete=True,
      native_arithmetic_observed_not_recomputed=True,coordinates_remain_raw_constructor_observations=True,
      resistor_footprint_or_transient_causality_proved=False,**b.FLAGS)

def current_controls(raw,ctx):
    r=decode(raw)
    require(r["status"]=="PASS_MAGIC_ANCESTRY_SOURCE_CONTROLS"and r["passed"]is True and
      r["counts"]==dict(positive=6,refusal=18,lifecycle=3),"actual ancestry controls")
    require(r["current_context"]==dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,
      source_controls_only=True,native_executed=False),"current ancestry source context")
    return r

def perform(ctx,reserved,controls_raw,expected,out,ancestry_controls,coefficient_controls,
            root=ROOT,api_call=frozen.api,fetch=frozen.download):
    source_guard(expected,root);current_controls(ancestry_controls,ctx)
    c.current_controls(coefficient_controls,ctx)
    write(out/"ancestry-source-controls.json",ancestry_controls)
    write(out/"coefficient-source-controls.json",coefficient_controls)
    namespace=dict(b.perform.__globals__)
    changed=dict(instrument_source=instrument_source,validate_trace=validate_trace,source_guard=source_guard)
    namespace.update(changed)
    execute=types.FunctionType(b.perform.__code__,namespace,b.perform.__name__,b.perform.__defaults__,b.perform.__closure__)
    require(execute.__code__ is b.perform.__code__ and
      {k for k in namespace if namespace[k]is not b.perform.__globals__[k]}==set(changed),
      "unchanged actual build/extraction/equivalence/cleanup body")
    result=execute(ctx,reserved,controls_raw,expected,out,root,api_call,fetch)
    write(out/"qualified-build-equivalence.json",encode(result))
    _,_,inc,_=t.proof(root)
    trace=out/"work/trace_on/resistor-physical-trace.jsonl"
    records=t.select_epochs(trace,inc["targets"],out)
    summaries={}
    for k,rows in records.items():
        report=replay(rows,inc["targets"][k])
        write(out/("target-"+k+"-ancestry.json"),encode(report))
        summaries[k]=dict(counts=report["counts"],all_observed_target_value_ancestry_complete=True)
    source_guard(expected,root)
    result.update(status="PASS_CURRENT500_OBSERVED_TARGET_ANCESTRY_NOT_PHYSICAL_OWNERSHIP",
      instrumentation="nssoc_resistor_provenance_v3",targets=summaries,
      all_global_ancestry_claimed=False,substituted_globals=sorted(changed),frozen_controller_code_identical=True)
    return result

def main():
    p=argparse.ArgumentParser()
    for n in ("pins-sha256","reservation","controls","coefficient-controls","ancestry-controls","output"):
        p.add_argument("--"+n,required=True)
    a=p.parse_args();ctx=b.context(os.environ)
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],"checkout source")
    a_raw=Path(a.ancestry_controls).read_bytes();c_raw=Path(a.coefficient_controls).read_bytes()
    b.run(ctx,decode(Path(a.reservation).read_bytes()),Path(a.controls).read_bytes(),a.pins_sha256,
      Path(a.output).resolve(),lambda *args:perform(*args,ancestry_controls=a_raw,coefficient_controls=c_raw))
if __name__=="__main__":main()
