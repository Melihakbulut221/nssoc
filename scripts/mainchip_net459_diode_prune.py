#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bounded net459 path selection and exact two-instance comparison helpers."""
import copy,hashlib,json,re
from pathlib import Path
import mainchip_two_signal_geometry as g
import mainchip_net459_connectivity as graph
import mainchip_original_clock_restoration as c
import mainchip_fixed_clock_signal_repair as old
ROOT=Path(__file__).resolve().parents[1]
BRANCH="codex/mainchip-net459-diode-prune"
GROUP="mainchip-net459-diode-prune"
MANIFEST="scripts/mainchip-net459-diode-prune-pins.json"
INPUT=dict(bytes=213429713,sha256="47d657f41565f5c379a9152672eac824a5d296043c3726527031452ad2097677")
REMOVE=("ANTENNA_1574","ANTENNA_1575")
KEEP_PINS={("fanout459","X"),("fanout36386","A"),("ANTENNA_1573","A")}
KEEP_SHAPES=[0,1,2,3,4,5,6,7,8,9,10,16,18,19,20,25,27,29,30,32,33,35,36,38,39,41,42,44,45,47,48,50,51,53,54,56,57,59,60,62,63,65,66,68,69,71,72,74,75,77,99,101,105,107,108,110,111,113,129,130,131,132,133,134]
def encode(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def pin(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def source_guard():
    m=json.loads((ROOT/MANIFEST).read_bytes())
    assert m["schema"]=="net459-diode-prune-pins-v1"
    for name,row in m["files"].items():
        p=c.regular(ROOT/name);assert pin(p.read_bytes())==row,("source",name)
    return m
def material(shapes):
    return [{k:v for k,v in s.items()if k!="opcode_index"}for s in shapes]
def primitives(raw,catalog):
    starts=[i for i,(op,data)in enumerate(raw)if op&31==0]
    assert starts and starts[0]==0
    result=[]
    for j,a in enumerate(starts):
        b=starts[j+1]if j+1<len(starts)else len(raw);part=raw[a:b]
        assert part[0][0]==96 and part[1][0]==68 and part[2][0]==69,"independent ROUTED path"
        kinds=[x[0]for x in part]
        if len(part)==5 and part[3][0]in(68,69)and part[4]==[12,0]:kind="wire"
        elif len(part)==5 and part[3][0]==136 and part[4]==[16,0]:kind="via"
        elif len(part)==7 and kinds[3:]==[14,11,11,11]:kind="wire-rect"
        else:raise AssertionError(("unsupported path",j,part))
        projected=g.project_wire(part,catalog)
        assert projected["shapes"]and {s["kind"]for s in projected["shapes"]}=={kind}
        shapes=[dict(s,opcode_index=s["opcode_index"]+a)for s in projected["shapes"]]
        result.append(dict(index=j,start=a,end=b,kind=kind,raw=part,shapes=shapes))
    return result
def plan(source):
    p=source["projection"];raw=p["raw"];shapes=p["shapes"]
    assert source["scoped_identity"]==["net","net459"]
    assert source["sigtype"]=="SIGNAL"and source["metadata_class"]=="ROUTED"
    assert (len(raw),len(shapes),len(source["pins"]))==(375,139,5)
    catalog=copy.deepcopy(p["catalog"])
    catalog["path_layers"]={int(k):v for k,v in catalog["path_layers"].items()}
    replay=g.project_wire(raw,catalog)
    assert replay["shapes"]==shapes and replay["raw_sha256"]==p["raw_sha256"]
    assert shapes[21]["opcode_index"]==108 and shapes[21]["box"]==[947420,1789520,947620,1790560]
    for mode in ("positive_area","closed_boundary"):
        obs=graph.observe(shapes,source["pins"],mode,[21])
        assert len(obs["wire_components"])==2
        assert obs["wire_components"][0]["shape_indices"]==KEEP_SHAPES
        assert {tuple(q["scoped_identity"][1:])for q in obs["pins"]if q["wire_components"]==[0]}==KEEP_PINS
        assert {tuple(q["scoped_identity"][1:])for q in obs["pins"]if q["wire_components"]==[1]}=={(x,"A")for x in REMOVE}
        assert all(len(q["wire_components"])==1 for q in obs["pins"])
    groups=primitives(raw,catalog)
    assert len(groups)==71 and [s for q in groups for s in q["shapes"]]==shapes
    keep=[];all_indices=[];cursor=0
    for q in groups:
        indices=list(range(cursor,cursor+len(q["shapes"])));cursor+=len(indices)
        metals=[i for i in indices if shapes[i]["layer"]in graph.METALS]
        assert metals
        flags={i in KEEP_SHAPES for i in metals}
        assert len(flags)==1,"partial native via removal"
        if flags=={True}:keep.append(q["index"]);all_indices+=indices
    assert keep and keep[0]==0 and len(keep)==43 and len(all_indices)==85
    retained_raw=[v for q in groups if q["index"]in keep for v in q["raw"]]
    assert len(retained_raw)==227
    projected=g.project_wire(retained_raw,catalog)
    assert material(projected["shapes"])==material([shapes[i]for i in all_indices])
    pins=[x for x in source["pins"]if tuple(x["scoped_identity"][1:])in KEEP_PINS]
    for mode in ("positive_area","closed_boundary"):
        obs=graph.observe(projected["shapes"],pins,mode)
        assert obs["all_pins_share_one_wire_component"]and obs["all_wire_material_one_component"]
    return dict(keep_paths=keep,kept_shape_indices=all_indices,source_paths=71,source_raw=375,
      retained_raw=retained_raw,retained_shapes=projected["shapes"],retained_pins=pins,
      raw_count=227,shape_count=85,paths=43,removed_instances=list(REMOVE),
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
def prune_record(record,keep,count):
    head=old.wire_head(record);wire=record[len(head):]
    assert wire.count(b";")==1 and wire.rstrip().endswith(b";")
    assert re.findall(rb"\+[ \t]+[A-Z_]+",wire)==[b"+ ROUTED"],"unsupported inline wire clause"
    end=wire.index(b";");body=wire[:end]
    hits=list(re.finditer(rb"(?m)^[ \t]*(?:\+ ROUTED|NEW) (?=\S)",body))
    assert len(hits)==count and hits[0].start()==0
    assert sorted(set(keep))==keep and keep and keep[0]==0 and keep[-1]<count
    chunks=[body[h.start():hits[i+1].start()if i+1<count else len(body)]for i,h in enumerate(hits)]
    assert chunks[0].lstrip().startswith(b"+ ROUTED ")and all(x.lstrip().startswith(b"NEW ")for x in chunks[1:])
    assert len(c.ROUTE.findall(record))==1
    return head+b"".join(chunks[i]for i in keep)+wire[end:]
def normalized_def(raw,removed_pins,expected_removed_instances):
    """Only two exact COMPONENTS/connection deltas and net459 wire are excluded."""
    p=c.parse_def(raw);record=p["records"]["net459"]
    a,b=p["spans"]["net459"]
    raw=raw[:a]+old.wire_head(record)+b" + ROUTED __NET459_WIRE__ ;\n"+raw[b:]
    del p,record
    h=list(re.finditer(rb"(?m)^COMPONENTS ([0-9]+) ;\n",raw));assert len(h)==1
    h=h[0];end=raw.index(b"END COMPONENTS\n",h.end());body=raw[h.end():end]
    starts=list(re.finditer(rb"(?m)^[ \t]*- ([^\s]+)(?=\s)",body));assert len(starts)==int(h.group(1))
    assert not body[:starts[0].start()].strip()
    chunks=[];removed=[]
    for i,m in enumerate(starts):
        stop=starts[i+1].start()if i+1<len(starts)else len(body)
        row=body[m.start():stop];name=m.group(1).decode("ascii")
        assert row.count(b";")==1 and row.rstrip().endswith(b";")
        if name in REMOVE:
            assert row.split()[2]==b"sg13g2_antennanp";removed.append(name)
        else:chunks.append(row)
    assert set(removed)==set(expected_removed_instances)
    assert int(h.group(1))-len(removed)==153128
    raw=raw[:h.start()]+b"COMPONENTS 153128 ;\n"+b"".join(chunks)+raw[end:]
    counts={}
    for inst,term,net,sigtype in removed_pins:
        pattern=rb"\([ \t\n]+"+re.escape(inst.encode())+rb"[ \t\n]+"+re.escape(term.encode())+rb"[ \t\n]+\)"
        matches=list(re.finditer(pattern,raw))
        quoted=list(re.finditer(rb'"(?:\\.|[^"\\])*"',raw))
        for match in matches:
            assert not any(q.start()<=match.start()<q.end()for q in quoted),"connection inside quoted value"
            owners=[]
            for section in (b"NETS",b"SPECIALNETS"):
                headers=list(re.finditer(rb"(?m)^"+section+rb" [0-9]+ ;\n",raw))
                assert len(headers)<=1
                if headers:
                    a=headers[0].end();b=raw.index(b"END "+section+b"\n",a)
                    if a<=match.start()<b:
                        starts2=list(re.finditer(rb"(?m)^[ \t]*- ([^\s]+)(?=\s)",raw[a:match.start()]))
                        assert starts2;owners.append(starts2[-1].group(1).decode("ascii"))
            assert owners==[net],("connection outside its exact native net",inst,term,owners,net)
        raw,n=re.subn(pattern,b"",raw);counts[inst+"/"+term]=n
        assert n in(0,1),"duplicate deleted connection"
        if inst in expected_removed_instances and term=="A":assert n==1
        if not expected_removed_instances:assert n==0
    # Preserve quoted contents while ignoring only exporter whitespace/wrapping.
    digest=hashlib.sha256()
    for match in re.finditer(rb'"(?:\\.|[^"\\])*"|[^\s"]+',raw):
        token=match.group();token.decode("ascii")
        digest.update(len(token).to_bytes(8,"big"));digest.update(token)
    return dict(sha256=digest.hexdigest(),
      removed_components=sorted(removed),removed_connection_counts=counts)
