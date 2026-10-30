#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Strict streaming parser for the pinned OpenROAD antenna report, not a rule reimplementation."""
import hashlib,json,re
from collections import Counter
from decimal import Decimal
from pathlib import Path
PRIMARY_SHA="ab842999d3ccaf9de34347fa1f3b723e0a4a7d0b19a42271dfb4c8dede2c9ca7"
PRIMARY="scripts/source-snapshots/openroad-dcf36133-AntennaChecker.cc"
ROUTING={"Metal1","Metal2","Metal3","Metal4","Metal5","TopMetal1","TopMetal2"}
CUT={"Via1","Via2","Via3","Via4","TopVia1","TopVia2"}
RULES={"Gate area":"Partial","Cumulative area":"Cumulative","Side area":"Partial","Cumulative side area":"Cumulative"}
NUM=r"-?[0-9]+\.[0-9]{2}"
VALUE=re.compile(r"      (Partial|Cumulative) area ratio: +("+NUM+r")\n")
REQUIRED=re.compile(r"      Required ratio: +("+NUM+r") \((Gate area|Cumulative area|Side area|Cumulative side area)\) (|\(VIOLATED\))\n")
def encoded(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def digest(v):return hashlib.sha256(canonical(v)).hexdigest()
def save(path,v):Path(path).write_bytes(encoded(v))
def semantics(v):return {k:x for k,x in v.items()if k not in("line","required_line")}
def parse(lines,expected_nets=None):
    nets={};violations=[];counts=Counter();line_count=0
    net=None;pin=None;master=None;layer=None;pending=None;checks=[];pins={};layers={}
    def finish_layer():
        nonlocal checks,layer
        assert pending is None,"unpaired ratio"
        if layer is None:return
        names=[q["rule"]for q in checks]
        assert names and names[0]=="Gate area"
        want=["Gate area"]+([]if checks[0]["violated"]else["Cumulative area"])
        if layer in ROUTING:want+=["Side area","Cumulative side area"]
        assert names==want,("complete exact native check sequence",layer,names,want)
        assert layer not in layers,"duplicate layer"
        layers[layer]=[semantics(q)for q in checks];counts["layers"]+=1
        checks=[];layer=None
    def finish_pin():
        nonlocal pin,master,layers
        finish_layer()
        if pin is None:return
        assert pin not in pins,"duplicate pin"
        pins[pin]=dict(master=master,layers=layers);counts["pins"]+=1
        pin=master=None;layers={}
    def finish_net():
        nonlocal net,pins
        finish_pin()
        if net is None:return
        assert net not in nets,"duplicate net"
        rows=[q for p in pins.values()for ls in p["layers"].values()for q in ls]
        nets[net]=dict(sha256=digest(dict(net=net,pins=pins)),pins=len(pins),layers=sum(len(p["layers"])for p in pins.values()),checks=len(rows),violations=sum(q["violated"]for q in rows))
        counts["nets"]+=1;net=None;pins={}
    for line_count,line in enumerate(lines,1):
        assert isinstance(line,str)and line.endswith("\n")and "\r"not in line and "\x00"not in line,"complete ASCII LF lines"
        line.encode("ascii")
        if line=="\n":
            assert pending is None,"blank between ratio pair"
            continue
        if line.startswith("Net: "):
            finish_net();net=line[5:-1]
            assert net and not any(x.isspace()for x in net)
            continue
        m=re.fullmatch(r"  Pin:   (.+) \(([^()\s]+)\)\n",line)
        if m:
            assert net is not None;finish_pin();pin,master=m.groups()
            assert pin and not any(x.isspace()for x in pin)
            continue
        m=re.fullmatch(r"    Layer: (\S+)\n",line)
        if m:
            assert pin is not None;finish_layer();layer=m.group(1);assert layer in ROUTING|CUT
            continue
        m=VALUE.fullmatch(line)
        if m:
            assert layer is not None and pending is None
            pending=dict(kind=m.group(1),display_value=m.group(2),line=line_count)
            continue
        m=REQUIRED.fullmatch(line)
        if m:
            assert pending is not None and layer is not None
            required,rule,flag=m.groups();assert RULES[rule]==pending["kind"]
            assert not any(q["rule"]==rule for q in checks),"duplicate rule"
            row=dict(net=net,pin=pin,master=master,layer=layer,rule=rule,
              display_value=pending["display_value"],display_limit=required,violated=flag=="(VIOLATED)",
              line=pending["line"],required_line=line_count)
            # Native flags use unrounded doubles; displayed numbers must never replace them.
            assert Decimal(required).is_finite()and Decimal(pending["display_value"]).is_finite()
            checks.append(row);counts["checks"]+=1
            if row["violated"]:violations.append(row)
            pending=None;continue
        raise AssertionError(("unrecognized report line",line_count,line[:200]))
    finish_net();assert line_count and nets
    vnets={r["net"]for r in violations};vpins={(r["net"],r["pin"])for r in violations}
    if expected_nets is not None:assert len(vnets)==expected_nets,("native violating-net count",len(vnets),expected_nets)
    violations.sort(key=lambda r:(r["net"],r["pin"],r["layer"],r["rule"]))
    assert len({(r["net"],r["pin"],r["layer"],r["rule"])for r in violations})==len(violations)
    summary=dict(status="COMPLETE_PINNED_NATIVE_ANTENNA_REPORT_PARSE",lines=line_count,counts=dict(counts),
      violating_nets=len(vnets),violating_pins=len(vpins),violating_checks=len(violations),
      by_layer=dict(sorted(Counter(r["layer"]for r in violations).items())),
      by_rule=dict(sorted(Counter(r["rule"]for r in violations).items())),
      by_master=dict(sorted(Counter(r["master"]for r in violations).items())),
      violating_net_names=sorted(vnets),complete_net_census_sha256=digest(nets),
      violation_semantics_sha256=digest([semantics(r)for r in violations]),
      source_report_values_rounded=True,violation_flags_not_recomputed=True,
      full_signoff_DRC=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
    return summary,nets,violations
def compare(a,b):
    sa,na,va=a;sb,nb,vb=b
    def key(r):return (r["net"],r["pin"],r["layer"],r["rule"])
    ma={key(r):semantics(r)for r in va};mb={key(r):semantics(r)for r in vb}
    common=set(ma)&set(mb)
    return dict(status="COMPLETE_EXACT_REPORT_COMPARISON_NOT_REPAIR",
      added_nets=sorted(set(nb)-set(na)),removed_nets=sorted(set(na)-set(nb)),
      changed_net_census=[dict(net=k,before=na[k],after=nb[k])for k in sorted(set(na)&set(nb))if na[k]!=nb[k]],
      added_violations=[mb[k]for k in sorted(set(mb)-set(ma))],
      removed_violations=[ma[k]for k in sorted(set(ma)-set(mb))],
      changed_violations=[dict(before=ma[k],after=mb[k])for k in sorted(common)if ma[k]!=mb[k]],
      identical_violation_semantics=ma==mb,before_counts=sa["counts"],after_counts=sb["counts"],
      before_violating_nets=sa["violating_nets"],after_violating_nets=sb["violating_nets"],
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
