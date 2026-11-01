#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Join existing compact obstacle evidence to the original DRT class map.
No CAD, geometry reconstruction, routing decision, or production acceptance.
Run controls and actual analysis only on GitHub runners.
"""
import argparse,base64,collections,hashlib,json,os,pathlib,re,subprocess,traceback,zlib

FLAGS=dict(native_tools_executed=False,routing_executed=False,physical_acceptance=False,
 timing_accepted=False,full_phy_accepted=False,physical_cause_proven=False,
 iteration10_mutable_routes_present=False,route_mutation_authorized=False)
MEMBERSHIPS=("mutable_cleared_manifest","protected_manifest","not_in_either_manifest")
WIRE_KINDS=("wire","wire-rect","via")
PIN_KINDS=("iterm-pin","bterm-pin")
ROOT=pathlib.Path(__file__).resolve().parents[1]
CONFIG="scripts/mainchip-drt-counterpart-scope-inputs.json"
REPO="repos/Melihakbulut221/nssoc/"
def require(ok,message):
    if not ok:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def unique_names(rows,label):
    require(type(rows)is list and all(type(x)is str and x for x in rows),label+" names")
    require(len(rows)==len(set(rows)),label+" duplicate")
    return set(rows)
def decode(raw):
    def pairs(items):
        result={}
        for k,v in items:
            require(k not in result,"duplicate JSON key")
            result[k]=v
        return result
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in()).throw(ValueError("nonfinite JSON")))
def false_scope(value,keys):
    require(all(value.get(k)is False for k in keys),"unchanged unqualified scope")
def classify(summary,endpoints,markers,witnesses,other,original,plan,expected):
    false_scope(summary,("physical_acceptance","timing_accepted","full_phy_accepted","routing_executed","physical_cause_proven","iteration10_mutable_routes_present"))
    false_scope(plan,("physical_acceptance","timing_accepted","full_phy_accepted"))
    require(summary["status"]=="COMPLETE_AUTHENTICATED_PREROUTE_OBSTACLE_REDUCTION" and summary["all_source_marker_and_witness_records_retained"]is True and summary["complete_input_sha256_verified"]is True,"complete authenticated compact reduction")
    mutable=unique_names(plan["mutable_nets"],"mutable")
    protected=unique_names(plan["protected_nets"],"protected")
    require(not mutable&protected,"mutable/protected overlap")
    require(len(mutable)==expected["mutable"] and len(protected)==expected["protected"],"full plan census")
    added=unique_names(plan["added_instances"],"added")
    require(type(plan["attachments"])is dict and set(plan["attachments"])==added and set(plan["attachments"].values())==mutable,"all diode attachments")
    require(len(added)==expected["diodes"],"full diode census")
    require(type(original)is dict and len(original)==expected["original_classes"],"complete original class map")
    require(all(type(n)is str and n and (v is None or type(v)is str and v in("ROUTED","FIXED","COVER"))for n,v in original.items()),"original class vocabulary")
    require(not mutable&set(original) and protected<=set(original),"original map excludes mutable and includes protected")
    require(len(original)+len(mutable)==expected["all_nets"],"complete original ordinary net census")
    names=unique_names([e["name"]for e in endpoints],"endpoint")
    require(len(names)==summary["endpoints"]==expected["endpoints"],"complete endpoint census")
    require(names<=set(original)|mutable,"endpoint absent from original map and mutable set")
    require(type(markers)is list and len(markers)==summary["selected_markers"]==expected["markers"],"complete selected markers")
    require(type(other)is list and len(other)==summary["other_marker_records"]==expected["other_markers"],"complete other markers")
    require(type(witnesses)is list and len(witnesses)==summary["complete_witness_records"]==expected["witnesses"],"complete witness census")
    require(all(type(x["ordinal"])is int for x in markers+other) and sorted(x["ordinal"]for x in markers+other)==list(range(len(markers)+len(other))),"all original ordinals exactly once")
    annotated_endpoints=[];by_name={};category_counts=collections.Counter();membership_counts=collections.Counter()
    for ep in endpoints:
        n=ep["name"];member=MEMBERSHIPS[0]if n in mutable else MEMBERSHIPS[1]if n in protected else MEMBERSHIPS[2]
        require(ep["manifest_membership"]==member,"endpoint membership disagrees with original plan")
        encoded=ep["encoded_class_counts"]
        require(type(encoded)is dict and all(k in("ROUTED","FIXED","COVER")and type(v)is int and v>0 for k,v in encoded.items()),"encoded class counts")
        require(type(ep["encoded_wire_present"])is bool,"encoded presence type")
        require(ep["encoded_wire_present"]==bool(encoded),"encoded presence census")
        present=n in original;old=original.get(n);pg=ep["signal_type"]in("POWER","GROUND")
        if n in mutable:
            require(not ep["encoded_wire_present"] and ep["route_metadata"]=="ROUTED","mutable routes remain cleared")
            category="mutable_cleared"
        else:
            # Validate actual ordinary-wire metadata separately from special PG geometry.
            if old is None:
                require(not ep["encoded_wire_present"],"originally unwired net acquired ordinary wire")
            else:
                require(ep["encoded_wire_present"] and ep["route_metadata"]=="FIXED" and set(encoded)=={"FIXED"},"observed nonmutable overlay is not FIXED")
            if pg:category="power_ground_keep_special"
            elif n in protected:category="protected_keep"
            elif ep["signal_type"]!="SIGNAL":category="non_signal_keep"
            elif old=="ROUTED":category="temporary_fixed_original_routed"
            elif old=="FIXED":category="original_fixed_keep"
            elif old=="COVER":category="original_cover_keep"
            else:category="original_unwired_keep"
        row=dict(source=ep,original_class_record_present=present,original_class=old,classification=category,route_mutation_authorized=False)
        annotated_endpoints.append(row);by_name[n]=row;category_counts[category]+=1;membership_counts[member]+=1
    require(dict(membership_counts)==summary["endpoint_membership_counts"],"original endpoint memberships counted exactly")
    observed_by_marker=collections.defaultdict(list);seen=set();global_groups=collections.Counter();joined=[];candidate_rows=collections.defaultdict(list)
    for w in witnesses:
        i=w["source_marker_index"];j=w["source_witness_index"]
        require(type(i)is int and 0<=i<len(markers) and type(j)is int and j>=0,"witness ordinal types and range")
        require((i,j)not in seen,"duplicate witness ordinal");seen.add((i,j))
        m=markers[i];n=w["owner"]
        require(m["source_marker_index"]==i and w["source_marker_ordinal"]==m["ordinal"],"witness source marker identity")
        require(n in m["nets"] and w["other_endpoint"]in m["nets"] and w["other_endpoint"]!=n,"exact two endpoint incidence")
        ep=by_name[n];s=ep["source"]
        require(w["manifest_membership"]==s["manifest_membership"] and w["signal_type"]==s["signal_type"],"witness endpoint metadata")
        require(w["source_pointer"]=="/markers/"+str(i)+"/endpoint_witnesses/"+str(j),"complete source pointer")
        same=w["layer"]==m["layer"]
        require(w["layer_relation"]==("same_layer"if same else"xy_projection_only_different_layer"),"source layer relation")
        require(w["relation"]["closed_intersection"]is True and type(w["relation"]["positive_area_intersection"])is bool,"source intersection flags")
        if w["kind"]in WIRE_KINDS:
            require(same and w["details"]["route_metadata"]==s["route_metadata"] and w["details"]["encoded_class_counts"]==s["encoded_class_counts"],"ordinary wire observation")
            require(w["evidence_group"]==("ordinary-wire-FIXED"if s["route_metadata"]=="FIXED"else"ordinary-wire-other-metadata"),"ordinary wire evidence group")
        elif w["kind"]in PIN_KINDS:require(w["evidence_group"]==w["kind"],"pin group")
        else:
            require(w["kind"]in("special-wire","special-via")and same,"special geometry kind/layer")
            require(w["evidence_group"]==("special-PG"if s["signal_type"]in("POWER","GROUND")else"special-other-signal-type"),"special signal group")
        overlap="positive-area"if w["relation"]["positive_area_intersection"]else"boundary-only"
        group="|".join((w["manifest_membership"],w["evidence_group"],w["layer_relation"],overlap))
        global_groups[group]+=1;observed_by_marker[i].append((j,group,n))
        eligible=ep["classification"]=="temporary_fixed_original_routed" and w["kind"]in WIRE_KINDS and same and w["relation"]["positive_area_intersection"]
        row=dict(source=w,original_class_record_present=ep["original_class_record_present"],original_class=ep["original_class"],
                 classification=ep["classification"],temporary_fixed_same_layer_positive_witness=eligible,route_mutation_authorized=False)
        joined.append(row)
        if eligible:candidate_rows[n].append(dict(source_marker_index=i,source_marker_ordinal=m["ordinal"],source_witness_index=j,other_endpoint=w["other_endpoint"],source_pointer=w["source_pointer"]))
    require(dict(global_groups)==summary["evidence_groups"],"complete original evidence-group multiplicity")
    require({n for m in markers for n in m["nets"]}==names,"all marker endpoints and only those endpoints")
    annotated_markers=[]
    for i,m in enumerate(markers):
        require(m["source_marker_index"]==i and m["layer"]=="Metal2","marker sequence/layer")
        require(type(m["nets"])is list and len(m["nets"])==2 and len(set(m["nets"]))==2 and set(m["nets"])<=names,"marker endpoint identity")
        require(m["endpoint_membership"]=={n:by_name[n]["source"]["manifest_membership"]for n in m["nets"]},"marker membership")
        rows=observed_by_marker[i]
        require(sorted(x[0]for x in rows)==list(range(m["all_witnesses"])),"complete per-marker witness sequence")
        require(dict(collections.Counter(x[1]for x in rows))==m["evidence_groups"],"per-marker group multiplicity")
        require(dict(collections.Counter(x[2]for x in rows))==m["witnesses_by_owner"],"per-marker owner multiplicity")
        require(m["no_observed_endpoint_intersection"]is(not rows),"marker no-intersection flag")
        annotated_markers.append(dict(source=m,endpoint_classification={n:by_name[n]["classification"]for n in m["nets"]}))
    candidates=[dict(net=n,original_class="ROUTED",observed_class="FIXED",witness_count=len(rows),
        source_marker_indices=sorted({r["source_marker_index"]for r in rows}),
        source_marker_ordinals=sorted({r["source_marker_ordinal"]for r in rows}),
        other_endpoints=sorted({r["other_endpoint"]for r in rows}),witnesses=rows,
        route_mutation_authorized=False)for n,rows in sorted(candidate_rows.items())]
    result=dict(status="COMPLETE_ORIGINAL_CLASS_COUNTERPART_JOIN",endpoint_classification_counts=dict(sorted(category_counts.items())),
      selected_markers=len(markers),endpoints=len(endpoints),other_marker_records=len(other),witness_records=len(witnesses),
      original_class_records=len(original),protected_nets_retained=len(protected),mutable_nets_retained=len(mutable),
      temporary_fixed_counterpart_nets=len(candidates),
      temporary_fixed_counterpart_witnesses=sum(x["witness_count"]for x in candidates),
      temporary_fixed_counterpart_markers=len({i for c in candidates for i in c["source_marker_indices"]}),
      original_summary=summary,all_marker_and_witness_ordinals_retained=True,
      interpretation="Original ROUTED to temporary FIXED metadata is established per net. This is neither the cause of the iteration10 violation nor permission to unfreeze. The original baseline/insertion native identity and actual iteration10 mutable routes remain separate evidence.",
      **FLAGS)
    return dict(result=result,endpoints=annotated_endpoints,markers=annotated_markers,witnesses=joined,other_markers=other,counterparts=candidates)

def api(path,binary=False):
    cmd=["gh","api",REPO+path]
    if binary:cmd+=["-H","Accept: application/octet-stream"]
    p=subprocess.run(cmd,capture_output=True,timeout=90)
    require(p.returncode==0,"GitHub acquisition failed "+path+": "+p.stderr.decode(errors="replace")[:2000])
    return p.stdout if binary else decode(p.stdout)
def pin(raw):return dict(bytes=len(raw),sha256=digest(raw))
def fetch_input(name,rule,out):
    if "asset_id"in rule:
        meta=api("releases/assets/"+str(rule["asset_id"]))
        require(meta["id"]==rule["asset_id"] and meta["name"]==rule["asset_name"] and meta["state"]=="uploaded" and meta["size"]==rule["bytes"] and meta["digest"]=="sha256:"+rule["sha256"],"exact original derived asset metadata")
        raw=api("releases/assets/"+str(rule["asset_id"]),True)
        (out/(name+".asset.json")).write_bytes(encode(meta))
    else:
        meta=api("contents/"+rule["path"]+"?ref="+rule["source"])
        require(meta["type"]=="file" and meta["size"]==rule["bytes"],"exact derived Git source file")
        blob=meta if meta.get("content")else api("git/blobs/"+meta["sha"])
        raw=base64.b64decode(blob["content"])
        require(hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==meta["sha"],"derived Git blob identity")
        (out/(name+".source.json")).write_bytes(encode(meta))
    require(pin(raw)=={k:rule[k]for k in("bytes","sha256")},"complete input byte pin "+name)
    (out/name).write_bytes(raw)
    return raw
def source_guard():
    config=decode((ROOT/CONFIG).read_bytes())
    for name,expected in config["source_files"].items():
        require(pin((ROOT/name).read_bytes())==expected,"current source pin "+name)
    return config
def emit(out):
    for p in sorted(out.glob("*")):
        if not p.is_file():continue
        raw=p.read_bytes()
        if p.suffix not in(".json",".jsonl",".txt"):continue
        packed=zlib.compress(raw,9);parts=[packed[i:i+24000]for i in range(0,len(packed),24000)]
        print("COUNTERPART_INDEX "+json.dumps(dict(name=p.name,**pin(raw),chunks=len(parts),encoding="zlib-base64")),flush=True)
        for i,data in enumerate(parts):print("COUNTERPART_CHUNK "+json.dumps(dict(name=p.name,index=i,data=base64.b64encode(data).decode())),flush=True)
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);a=p.parse_args()
    out=pathlib.Path(a.output);out.mkdir(parents=True,exist_ok=False);inputs=out/"inputs";inputs.mkdir()
    result=dict(status="FAILED_BEFORE_CLASSIFICATION",**FLAGS)
    try:
        c=source_guard()
        require(os.environ.get("GITHUB_ACTIONS")=="true" and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc","cloud runner only")
        source=os.environ["GITHUB_SHA"];run=int(os.environ["GITHUB_RUN_ID"]);attempt=int(os.environ["GITHUB_RUN_ATTEMPT"]);require(attempt==1,"single attempt")
        (out/"context.json").write_bytes(encode(dict(source=source,run=run,attempt=attempt,inputs=c["inputs"])))
        release=api("releases/"+str(c["class_map_producer"]["release"]))
        require({k:release[k]for k in("id","tag_name","target_commitish","draft","prerelease")}==c["class_map_producer"]["identity"],"original class map collector release identity")
        ref=api("git/ref/tags/"+release["tag_name"])
        require(ref["object"]["type"]=="commit" and ref["object"]["sha"]==release["target_commitish"],"original collector tag")
        assets={x["id"]:x for x in release["assets"]}
        for rule in c["inputs"].values():
            if "asset_id"in rule:require(rule["asset_id"]in assets and assets[rule["asset_id"]]["digest"]=="sha256:"+rule["sha256"],"original release owns exact asset")
        (out/"producer-release.json").write_bytes(encode(release));(out/"producer-ref.json").write_bytes(encode(ref))
        raw={n:fetch_input(n,r,inputs)for n,r in c["inputs"].items()}
        values={n:([decode(line)for line in b.splitlines()]if n.endswith(".jsonl")else decode(b))for n,b in raw.items()}
        joined=classify(values["summary.json"],values["endpoints.json"],values["markers.json"],values["witnesses.jsonl"],values["other_markers.json"],values["original_classes.json"],values["insertion_plan.json"],c["expected"])
        for n,value in joined.items():(out/(n+".json")).write_bytes(encode(value))
        for n,b in raw.items():require(pin((inputs/n).read_bytes())==pin(b),"input unchanged "+n)
        source_guard();result=joined["result"]
    except BaseException as e:
        result.update(error=repr(e),traceback=traceback.format_exc())
        (out/"result.json").write_bytes(encode(result));raise
    finally:
        emit(out)
if __name__=="__main__":main()
