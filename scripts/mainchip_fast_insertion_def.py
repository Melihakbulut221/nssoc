#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact insertion DEF normalization without one full-file scan per diode pin."""
import hashlib,re
from bisect import bisect_right

def exact(a,b,label):
    assert a==b,label

def normalized_added_def(raw,removed_pins,expected_removed_instances,added_names,original_instances):
    """Same tokens and exact native net ownership, using bounded whole-file scans."""
    added_names=set(added_names);expected_removed_instances=set(expected_removed_instances)
    h=list(re.finditer(rb"(?m)^COMPONENTS ([0-9]+) ;\n",raw));assert len(h)==1
    h=h[0];end=raw.index(b"END COMPONENTS\n",h.end());body=raw[h.end():end]
    starts=list(re.finditer(rb"(?m)^[ \t]*- ([^\s]+)(?=\s)",body));assert len(starts)==int(h.group(1))
    assert not body[:starts[0].start()].strip()
    chunks=[];removed=[]
    for i,m in enumerate(starts):
        stop=starts[i+1].start()if i+1<len(starts)else len(body)
        row=body[m.start():stop];name=m.group(1).decode("ascii")
        assert row.count(b";")==1 and row.rstrip().endswith(b";")
        if name in added_names:
            assert row.split()[2]==b"sg13g2_antennanp";removed.append(name)
        else:chunks.append(row)
    assert set(removed)==set(expected_removed_instances)
    assert int(h.group(1))-len(removed)==original_instances
    raw=raw[:h.start()]+("COMPONENTS "+str(original_instances)+" ;\n").encode()+b"".join(chunks)+raw[end:]
    requested={}
    for inst,term,net,sigtype in removed_pins:
        key=(inst.encode("ascii"),term.encode("ascii"))
        assert all(re.fullmatch(rb"[^ \t\n()]+",part)for part in key),"unsupported target connection name"
        assert key not in requested,"duplicate requested terminal"
        requested[key]=(inst,term,net)
    # These offsets are computed once on the unchanged post-component byte stream.
    # Quoted target-shaped text must still be rejected, never silently ignored.
    quoted=[(m.start(),m.end())for m in re.finditer(rb'"(?:\\.|[^"\\])*"',raw)]
    quote_starts=[x[0]for x in quoted]
    sections=[]
    for section in (b"NETS",b"SPECIALNETS"):
        headers=list(re.finditer(rb"(?m)^"+section+rb" [0-9]+ ;\n",raw))
        assert len(headers)<=1
        if headers:
            start=headers[0].end();stop=raw.index(b"END "+section+b"\n",start)
            starts=[(start+m.start(),m.group(1).decode("ascii"))for m in re.finditer(rb"(?m)^[ \t]*- ([^\s]+)(?=\s)",raw[start:stop])]
            sections.append((start,stop,[x[0]for x in starts],[x[1]for x in starts]))
    counts={inst+"/"+term:0 for inst,term,net in requested.values()}
    assert len(counts)==len(requested),"ambiguous terminal count key"
    spans=[]
    for match in re.finditer(rb"\([ \t\n]+([^ \t\n()]+)[ \t\n]+([^ \t\n()]+)[ \t\n]+\)",raw):
        key=(match.group(1),match.group(2))
        if key not in requested:continue
        inst,term,net=requested[key];pos=match.start()
        q=bisect_right(quote_starts,pos)-1
        assert q<0 or pos>=quoted[q][1],"connection inside quoted value"
        owners=[]
        for start,stop,starts,names in sections:
            if start<=pos<stop:
                i=bisect_right(starts,pos)-1;assert i>=0
                owners.append(names[i])
        assert owners==[net],("connection outside its exact native net",inst,term,owners,net)
        label=inst+"/"+term;counts[label]+=1
        assert counts[label]<=1,"duplicate deleted connection"
        spans.append((match.start(),match.end()))
    for inst,term,net in requested.values():
        n=counts[inst+"/"+term]
        if inst in expected_removed_instances and term=="A":assert n==1
        if not expected_removed_instances:assert n==0
    chunks=[];start=0
    for lo,hi in spans:chunks.append(raw[start:lo]);start=hi
    chunks.append(raw[start:]);raw=b"".join(chunks)
    # Preserve quoted contents while ignoring only exporter whitespace/wrapping.
    digest=hashlib.sha256()
    for match in re.finditer(rb'"(?:\\.|[^"\\])*"|[^\s"]+',raw):
        token=match.group();token.decode("ascii")
        digest.update(len(token).to_bytes(8,"big"));digest.update(token)
    return dict(sha256=digest.hexdigest(),
      removed_components=sorted(removed),removed_connection_counts=counts)

def insertion_def_delta(before_raw,after_raw,plan,after_snapshot,original_instances):
    removed=[]
    for inst in plan["added_instances"]:
        for terminal,row in after_snapshot["instances"][inst]["pins"].items():
            removed.append([inst,terminal,row["net"],row["sigtype"]])
    before=normalized_added_def(before_raw,removed,[],plan["added_instances"],original_instances)
    after=normalized_added_def(after_raw,removed,plan["added_instances"],plan["added_instances"],original_instances)
    exact(after["sha256"],before["sha256"],"all original DEF tokens preserved through insertion")
    return dict(before=before,after=after,excluded_added_components=plan["added_instances"],
      excluded_added_connections=removed,no_route_material_excluded=True)

