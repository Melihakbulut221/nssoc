#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted parity/refusal controls against the frozen exact normalizer."""
import copy
import mainchip_bulk_postdrt_antenna as old
import mainchip_fast_insertion_def as fast

def fixture(n=2,pg=True):
    names=["__diode_%d"%i for i in range(n)]
    pins=[[name,term,("s%d"%i if term=="A"else term),"SIGNAL"if term=="A"else"POWER"]for i,name in enumerate(names)for term in("A","VDD","VSS")]
    def raw(after):
        comps=["- keep0 sg13g2_inv_1 + PLACED ( 10 20 ) N ;","- keep1 sg13g2_buf_1 + PLACED ( 20 20 ) N ;"]
        if after:comps+=["- "+x+" sg13g2_antennanp + PLACED ( 30 20 ) N ;"for x in names]
        lines=["VERSION 5.8 ;","COMPONENTS %d ;"%len(comps),*comps,"END COMPONENTS","NETS %d ;"%n]
        for i,name in enumerate(names):
            lines+=["- s%d ( keep0 Y ) %s + ROUTED Metal1 ( 10 10 ) ( 20 10 ) ;"%(i,("( "+name+" A )")if after else"")]
        lines+=["END NETS","SPECIALNETS 2 ;"]
        for term in("VDD","VSS"):
            connections=" ".join("( "+x+" "+term+" )"for x in names)if after and pg else""
            lines+=["- "+term+" ( keep1 "+term+" ) "+connections+" + ROUTED Metal1 ( 0 0 ) ( 100 0 ) ;"]
        lines+=["END SPECIALNETS","END DESIGN"]
        return ("\n".join(lines)+"\n").encode()
    return raw(False),raw(True),pins,names

def run():
    rows=[];before,after,pins,names=fixture()
    def parity(label,raw,removed=names,pins=pins):
        a=old.normalized_added_def(raw,pins,removed,names,2)
        b=fast.normalized_added_def(raw,pins,removed,names,2)
        assert a==b,(label,a,b);rows.append("fast DEF "+label)
    def refused(label,raw,pins=pins,removed=names):
        for fn in(old.normalized_added_def,fast.normalized_added_def):
            try:fn(raw,pins,removed,names,2)
            except(AssertionError,ValueError,IndexError,KeyError):pass
            else:raise AssertionError(label+" accepted by "+fn.__module__)
        rows.append("fast DEF "+label)
    # Twelve complete-output parity cases, including absent optional PG connections.
    parity("baseline exact empty deletions",before,[])
    parity("all owned signal and power deletions",after)
    parity("wrapped connection whitespace",after.replace(b"( __diode_",b"(\n __diode_").replace(b" A )",b"\tA\n )"))
    parity("component indentation",after.replace(b"\n- ",b"\n  - "))
    parity("preserved quoted unrelated text",after.replace(b"END DESIGN",b'PROPERTY foo "unrelated ( keep0 Y ) string" ;\nEND DESIGN'))
    parity("preserved escaped quoted text",after.replace(b"END DESIGN",b'PROPERTY foo "a \\" quoted \\\\ value" ;\nEND DESIGN'))
    parity("absent both optional PG contacts",fixture(pg=False)[1])
    parity("absent one optional PG contact",after.replace(b"( __diode_0 VDD )",b""))
    parity("preserved other instance connection",after.replace(b"( keep0 Y )",b"( keep0 Y ) ( keep1 A )"))
    parity("preserved exporter wrapping",after.replace(b" + ROUTED",b"\n + ROUTED"))
    parity("all requested pins reversed",after,pins=list(reversed(pins)))
    parity("preserved route keyword text",after.replace(b"ROUTED",b"FIXED"))
    # Twelve malformed ownership/material cases must remain rejected by both.
    refused("missing required diode signal",after.replace(b"( __diode_0 A )",b""))
    refused("duplicate diode signal",after.replace(b"( __diode_0 A )",b"( __diode_0 A ) ( __diode_0 A )"))
    refused("duplicate diode power",after.replace(b"( __diode_0 VDD )",b"( __diode_0 VDD ) ( __diode_0 VDD )"))
    refused("wrong signal owner",after.replace(b"- s0 ",b"- wrong "))
    refused("wrong power owner",after.replace(b"- VDD ",b"- wrong "))
    refused("target connection inside quoted property",after.replace(b"END DESIGN",b'PROPERTY foo "( __diode_0 VSS )" ;\nEND DESIGN'))
    refused("target connection outside net sections",after.replace(b"( __diode_0 A )",b"").replace(b"END DESIGN",b"( __diode_0 A )\nEND DESIGN"))
    refused("wrong added master",after.replace(b"sg13g2_antennanp",b"sg13g2_inv_1"))
    refused("wrong component census",after.replace(b"COMPONENTS 4 ;",b"COMPONENTS 5 ;"))
    refused("unexpected component removal",after,removed=names[:1])
    refused("baseline deletion forbidden",after,removed=[])
    bad=copy.deepcopy(pins);bad[0][2]="other";refused("wrong native attachment binding",after,pins=bad)
    # Four insertion-delta checks preserve the original token hash, including routes.
    snapshot=dict(instances={x:dict(pins={t:dict(net=("s%d"%i if t=="A"else t),sigtype="SIGNAL"if t=="A"else"POWER")for t in("A","VDD","VSS")})for i,x in enumerate(names)})
    plan=dict(added_instances=names)
    result=fast.insertion_def_delta(before,after,plan,snapshot,2)
    assert result==old.insertion_def_delta(before,after,plan,snapshot,2);rows.append("fast DEF complete insertion delta parity")
    for label,changed in [
        ("changed old route coordinate",after.replace(b"( 20 10 )",b"( 21 10 )")),
        ("changed old route class",after.replace(b"+ ROUTED Metal1",b"+ FIXED Metal1")),
        ("changed old cell position",after.replace(b"( 10 20 )",b"( 11 20 )"))]:
        for fn in(old.insertion_def_delta,fast.insertion_def_delta):
            try:fn(before,changed,plan,snapshot,2)
            except AssertionError:pass
            else:raise AssertionError(label+" accepted")
        rows.append("fast DEF "+label)
    # The real bulk-size cardinality is exercised without the old O(pins*file) walk.
    b,a,ps,ns=fixture(n=1351)
    baseline=fast.normalized_added_def(b,ps,[],ns,2)
    actual=fast.normalized_added_def(a,ps,ns,ns,2)
    assert actual["sha256"]==baseline["sha256"]and len(actual["removed_connection_counts"])==4053
    assert set(actual["removed_connection_counts"].values())=={1}
    rows.append("fast DEF full1351 diode4053 terminal cardinality")
    assert len(rows)==29 and len(set(rows))==29
    return rows
