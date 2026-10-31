#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact terminal coverage, separate from RC accuracy and setup/hold signoff."""
import math,re
import mainchip_routed_view_admission as a

def census(v):
    a.validate_inventory(v);ends={n:{}for n in v["nets"]}
    for inst,row in v["instances"].items():
        for pin,r in row["pins"].items():
            if r["net"]is not None and r["sigtype"]not in a.PG:
                ends[r["net"]][("I",inst,pin)]=r["io"]
    for port,r in v["ports"].items():
        if r["net"]is not None and r["sigtype"]not in a.PG:ends[r["net"]][("P",port)]=r["io"]
    required={};excluded={}
    for net,row in v["nets"].items():
        if row["sigtype"]in a.PG:excluded[net]="power-or-ground"
        elif not ends[net]:excluded[net]="no-signal-terminals"
        elif len(ends[net])==1 and not row["wire"]:excluded[net]="unwired-single-terminal"
        else:required[net]=ends[net]
    return required,excluded,ends

def finite(token,nonnegative=True):
    try:value=float(token)
    except (ValueError,TypeError):raise ValueError("invalid SPEF number")
    a.require(math.isfinite(value)and(not nonnegative or value>=0),"nonfinite/negative SPEF number")
    return value

def parse_spef(raw):
    """Fail closed on ambiguous names; never fuzzy-match escaped native objects."""
    a.require(type(raw)is bytes,"SPEF bytes")
    text=raw.decode("utf-8");names={};nets={};current=None;section=None
    delimiter=None;design=None;cap_unit=None;res_unit=None;flow=False
    def resolve(token):
        if token.startswith("*"):
            m=re.fullmatch(r"\*(\d+)(.*)",token);a.require(m is not None,"bad SPEF name reference")
            a.require(m[1]in names,"unknown SPEF name reference")
            suffix=m[2];a.require(not suffix or suffix.startswith(delimiter),"name reference suffix")
            return names[m[1]]+suffix
        return token
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith("//"):continue
        words=line.split();head=words[0]
        if head=="*DESIGN":
            a.require(design is None and len(words)==2,"one SPEF design")
            design=words[1].strip('"')
        elif head=="*DELIMITER":
            a.require(delimiter is None and len(words)==2 and words[1]==":","pinned SPEF delimiter")
            delimiter=words[1]
        elif head=="*DESIGN_FLOW":flow='"PIN_CAP NONE"'in line
        elif head in("*C_UNIT","*R_UNIT"):
            a.require(len(words)==3 and finite(words[1])>0,"SPEF units")
            if head=="*C_UNIT":
                a.require(cap_unit is None and words[2]in("F","NF","PF","FF"),"SPEF capacitance unit");cap_unit=words[1:]
            else:
                a.require(res_unit is None and words[2]in("OHM","KOHM"),"SPEF resistance unit");res_unit=words[1:]
        elif head=="*NAME_MAP":
            a.require(current is None and not names,"unique SPEF name map");section="names"
        elif head=="*PORTS":
            a.require(current is None,"PORTS inside net");section="ports"
        elif head=="*D_NET":
            a.require(current is None and len(words)==3 and delimiter is not None,"complete SPEF net header")
            net=resolve(words[1]);a.name(net);a.require(net not in nets,"duplicate SPEF net")
            current=dict(connections={},declared_cap=finite(words[2]),cap_entries=0,res_entries=0)
            nets[net]=current;section="header"
        elif head=="*END":
            a.require(current is not None and len(words)==1 and section in("cap","res"),"complete SPEF END")
            current=None;section=None
        elif head in("*CONN","*CAP","*RES"):
            a.require(current is not None and len(words)==1,"SPEF section scope")
            wanted={"*CONN":"conn","*CAP":"cap","*RES":"res"}[head]
            a.require((section,wanted)in{("header","conn"),("conn","cap"),("cap","res")},"SPEF section order")
            section=wanted
        elif current is not None and section=="conn":
            a.require(head in("*I","*P")and len(words)>=3,"SPEF connection")
            resolved=resolve(words[1]);direction=words[2];a.require(direction in("I","O","B"),"SPEF direction")
            if head=="*I":
                a.require(delimiter in resolved,"SPEF instance pin")
                inst,pin=resolved.rsplit(delimiter,1);a.name(inst);a.name(pin);key=("I",inst,pin)
            else:key=("P",a.name(resolved))
            a.require(key not in current["connections"],"duplicate SPEF terminal")
            # Coordinates/load/driver metadata are irrelevant to incidence, but
            # unexpected inline grammar is refused rather than silently discarded.
            rest=words[3:]
            while rest:
                flag=rest.pop(0);a.require(flag in("*C","*L","*D"),"SPEF connection metadata")
                count=2 if flag=="*C"else 1;a.require(len(rest)>=count,"truncated SPEF metadata")
                vals=rest[:count];del rest[:count]
                if flag!="*D":
                    for value in vals:finite(value,nonnegative=flag!="*C")
                else:a.name(vals[0])
            current["connections"][key]=direction
        elif current is not None and section in("cap","res"):
            a.require(words[0].isdigit(),"SPEF element identifier")
            a.require(len(words)in((3,4)if section=="cap"else(4,)),"SPEF element arity")
            finite(words[-1]);current[section+"_entries"]+=1
        elif section=="names"and re.fullmatch(r"\*\d+",head):
            a.require(len(words)==2 and head[1:]not in names,"unique unambiguous SPEF name map")
            names[head[1:]]=a.name(words[1].strip('"'))
        elif section=="ports"and head.startswith("*"):
            # Incidence is checked per D_NET; global port hints are not evidence.
            a.require(len(words)>=2,"SPEF global port")
        elif current is not None:raise ValueError("unexpected SPEF net content")
        elif head in("*SPEF","*DATE","*VENDOR","*PROGRAM","*VERSION","*DIVIDER","*BUS_DELIMITER","*T_UNIT","*L_UNIT"):
            pass
        else:raise ValueError("unexpected SPEF header")
    a.require(current is None and nets and design=="soc_top"and flow and cap_unit and res_unit,"complete actual PIN_CAP NONE SPEF")
    return nets

def coverage(inventory,raw):
    required,excluded,ends=census(inventory);nets=parse_spef(raw)
    a.require(set(required)<=set(nets),"SPEF omits a required wired or multi-terminal net")
    a.require(set(nets)<=set(inventory["nets"]),"SPEF has unknown native net")
    direction={"INPUT":"I","OUTPUT":"O","INOUT":"B","FEEDTHRU":"B"}
    for net,row in nets.items():
        a.require(inventory["nets"][net]["sigtype"]not in a.PG,"PG net outside signal extraction scope")
        expected={key:direction[io]for key,io in ends[net].items()}
        a.exact(row["connections"],expected,"all actual SPEF terminals: "+net)
    return dict(status="PASS_EXACT_SPEF_TERMINAL_COVERAGE_NOT_RC_ACCURACY",
      inventory_nets=len(inventory["nets"]),required_nets=len(required),spef_nets=len(nets),
      excluded=excluded,optional_extracted=sorted(set(nets)-set(required)),spef=a.pin_bytes(raw),**a.FLAGS)

def annotation(inventory,loads,corner,raw):
    """Parse pinned OpenSTA ReportParasiticAnnotation.cc DRIVER counts."""
    a.require(corner in a.CORNERS,"original PVT")
    required,excluded,ends=census(inventory);payload=loads[corner]
    drivers={}
    for row in payload["pins"]:
        if row["driver"]:drivers[row["path"]]=row["net"]
    for row in payload["ports"]:
        if row["driver"]:
            a.require(row["path"]not in drivers,"unique native driver path");drivers[row["path"]]=row["net"]
    a.require(type(raw)is bytes,"annotation bytes")
    lines=raw.decode().splitlines();groups={};current=None
    for line in lines:
        m=re.fullmatch(r"Found (\d+) (unannotated|partially unannotated) drivers\.",line)
        if m:
            key=m[2];a.require(key not in groups,"duplicate annotation summary")
            groups[key]=dict(count=int(m[1]),rows=[]);current=key
        else:
            a.require(current is not None and line.startswith(" ")and line.strip(),"annotation row grammar")
            groups[current]["rows"].append(line[1:])
    a.exact(set(groups),{"unannotated","partially unannotated"},"complete native driver annotation report")
    partial=groups["partially unannotated"]
    a.require(partial["count"]==0 and partial["rows"]==[],"partially annotated driver/load")
    missing=groups["unannotated"]
    a.require(len(missing["rows"])==missing["count"]==len(set(missing["rows"])),"exact unannotated driver census")
    for path in missing["rows"]:
        a.require(path in drivers,"unknown unannotated native driver")
        net=drivers[path]
        a.require(net is None or excluded.get(net)in("no-signal-terminals","unwired-single-terminal"),"required driver has no parasitic annotation")
    return dict(status="PASS_NATIVE_DRIVER_ANNOTATION_WITH_EXPLICIT_EXCLUSIONS",
      corner=corner,native_driver_count=len(drivers),unannotated_drivers=missing["rows"],
      excluded_driver_nets={p:drivers[p]for p in missing["rows"]},partially_unannotated_drivers=0,
      report=a.pin_bytes(raw),**a.FLAGS)

def verify_all(inventory,loads,added,spef,reports):
    a.validate_loads(inventory,loads,added)
    a.exact(set(reports),set(a.CORNERS),"all native annotation corners")
    return dict(spef=coverage(inventory,spef),
      annotation={c:annotation(inventory,loads,c,reports[c])for c in a.CORNERS},
      scope="Connectivity/coverage only; original RC provenance, capacitance conservation, propagated-clock timing and signoff gates remain required.",**a.FLAGS)
