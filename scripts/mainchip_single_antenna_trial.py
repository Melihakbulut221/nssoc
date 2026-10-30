#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explicit one-diode insertion and Metal1 target-branch admission contract."""
import hashlib,json,re
from pathlib import Path
import mainchip_original_clock_restoration as c
import mainchip_fixed_clock_signal_repair as old
ROOT=Path(__file__).resolve().parents[1]
NET="$abc$1804206$new_n41321"
SINK=("fanout36953","A")
NEW="NSSOC_ANT_TRIAL_fanout36953"
REMOVE=(NEW,)
MANIFEST="scripts/mainchip-single-antenna-trial-pins.json"
INPUT=dict(bytes=213428597,sha256="a3c6aa0b946d01850fd4956b3fe359c34da120550caffdbbce113072cb381c76")
VIOLATIONS="docs/evidence/mainchip-full-antenna-readback-terminal-40985634146/derived/candidate-violations.json"
def encode(v):return(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def pin(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def source_guard():
    m=json.loads((ROOT/MANIFEST).read_bytes());assert m["schema"]=="single-antenna-trial-pins-v1"
    for name,row in m["files"].items():
        f=c.regular(ROOT/name);assert pin(f.read_bytes())==row,("source",name)
    return m
def overlap(a,b):return a[0]<b[2]and b[0]<a[2]and a[1]<b[3]and b[1]<a[3]
def contains(a,b):return a[0]<=b[0]<b[2]<=a[2]and a[1]<=b[1]<b[3]<=a[3]
def legal_sites(rows,occupied,size,sink,limit=40000):
    w,h=size;assert type(w)is int and w>0 and type(h)is int and h>0
    assert type(limit)is int and 0<limit<=40000
    candidates=[];seen=set()
    for row in rows:
        assert row["direction"]=="HORIZONTAL"and row["orientation"]in("R0","MX")
        assert row["count"]>0 and row["spacing"]>0
        if row["site_height"]!=h or row["box"][1]!=sink[1]:continue
        assert row["site_width"]==row["spacing"]and w%row["spacing"]==0
        x0,y0=row["box"][:2];step=row["spacing"]
        for k in range(row["count"]):
            x=x0+k*step
            if abs(x-sink[0])>limit:continue
            box=[x,y0,x+w,y0+h]
            if not contains(row["box"],box)or any(overlap(box,o["box"])for o in occupied):continue
            key=(tuple(box),row["orientation"]);assert key not in seen,"overlapping duplicate rows";seen.add(key)
            candidates.append(dict(row=row["name"],site=row["site"],orientation=row["orientation"],
              location=[x,y0],box=box,site_index=k,distance=abs(2*x+w-sink[0]-sink[2])))
    return sorted(candidates,key=lambda q:(q["distance"],q["location"],q["row"]))
def center(box):
    assert len(box)==4 and all(type(v)is int for v in box)
    p=[((box[0]+box[2])//10)*5,((box[1]+box[3])//10)*5]
    assert box[0]<p[0]<box[2]and box[1]<p[1]<box[3];return p
def branch(a,b,width):
    assert width==160
    x=center(a);y=center(b)
    lo=max(a[1],b[1]);hi=min(a[3],b[3])
    if hi-lo>=width:
        x[1]=y[1]=((lo+hi)//10)*5
    points=[x,[y[0],x[1]],y]
    out=[]
    for q in points:
        if not out or out[-1]!=q:out.append(q)
    assert len(out)in(2,3)and all(abs(q[0])<2**31 and abs(q[1])<2**31 for q in out)
    for u,v in zip(out,out[1:]):assert (u[0]==v[0])!=(u[1]==v[1])
    return out
def branch_boxes(points,width):
    assert width==160
    return [[min(a[0],b[0])-80,min(a[1],b[1])-80,max(a[0],b[0])+80,max(a[1],b[1])+80]for a,b in zip(points,points[1:])]
def append_branch(record,points):
    assert record.startswith(("- "+NET+"\n").encode())or record.startswith(("- "+NET+" ").encode())
    assert len(points)in(2,3)
    for q in points:assert len(q)==2 and all(type(v)is int and v%5==0 for v in q)
    for a,b in zip(points,points[1:]):assert (a[0]==b[0])!=(a[1]==b[1])
    head=old.wire_head(record);wire=record[len(head):]
    assert wire.count(b";")==1 and wire.rstrip().endswith(b";")
    assert re.findall(rb"\+[ \t]+[A-Z_]+",wire)==[b"+ ROUTED"]
    i=record.index(b";")
    extra=(" NEW Metal1 "+" ".join("( %d %d )"%tuple(q)for q in points)+"\n").encode()
    return record[:i]+extra+record[i:]
def normalized_def(raw,removed_pins,expected_removed_instances):
    """Exclude exactly the new diode and its declared connections plus target wire; preserve everything else."""
    p=c.parse_def(raw);record=p["records"][NET]
    a,b=p["spans"][NET]
    raw=raw[:a]+old.wire_head(record)+b" + ROUTED __SINGLE_TARGET_WIRE__ ;\n"+raw[b:]
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

def run_phase(phase,action,input_check,writer):
    """Independent finalization attempts; none may replace the original failure."""
    import sys,traceback
    primary=None;errors=[]
    def attempt(label,fn):
        try:return fn()
        except BaseException as exc:errors.append(dict(label=label,error=repr(exc)));return None
    try:action()
    except BaseException as exc:
        primary=exc;trace=traceback.format_exc()
        attempt("failure-record",lambda:writer(phase+"-failure.json",dict(error=repr(primary),traceback=trace,
          physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)))
    finally:
        attempt("input-unchanged",input_check)
        terminal=dict(phase=phase,complete=primary is None and not errors,error=None if primary is None else repr(primary),
          terminal_errors=list(errors),physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
        attempt("terminal-record",lambda:writer(phase+"-terminal.json",terminal))
        if primary is not None or errors:
            attempt("stderr-diagnostic",lambda:print(json.dumps(dict(phase=phase,primary=None if primary is None else repr(primary),
              terminal_errors=errors),sort_keys=True),file=sys.stderr,flush=True))
    if primary is not None:raise primary
    if errors:raise RuntimeError("phase finalization failed: "+repr(errors))
    return terminal
