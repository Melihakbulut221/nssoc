#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Complete antenna evidence identities and native-LEF antenna statements."""
import hashlib,json,math,re
from pathlib import Path
INPUT=dict(bytes=213428597,sha256="a3c6aa0b946d01850fd4956b3fe359c34da120550caffdbbce113072cb381c76")
VIOLATIONS="docs/evidence/mainchip-full-antenna-readback-terminal-40985634146/derived/candidate-violations.json"
VIOLATION_PIN=dict(bytes=300408,sha256="cd40e466571adfa89e4c820fa24786b3e09d92327fec6a4b28790e7e1618e575")
def encoded(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def pin(b):return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load_violations(root):
    b=(Path(root)/VIOLATIONS).read_bytes();assert pin(b)==VIOLATION_PIN
    rows=json.loads(b);validate(rows,(609,697,916));return rows
def validate(rows,expected):
    assert isinstance(rows,list)and rows
    seen=set();nets=set();pins=set()
    for r in rows:
        for k in("net","pin","master","layer","rule","display_value","display_limit"):assert isinstance(r[k],str)and r[k]
        assert r["violated"]is True and r["rule"]=="Cumulative area"
        assert r["layer"]in("Metal1","Metal2","Metal3","Metal4","Metal5","TopMetal1","TopMetal2")
        assert all(re.fullmatch(r"-?[0-9]+\.[0-9]{2}",r[k])for k in("display_value","display_limit"))
        key=tuple(r[k]for k in("net","pin","layer","rule"));assert key not in seen;seen.add(key)
        nets.add(r["net"]);pins.add((r["net"],r["pin"]))
    assert (len(nets),len(pins),len(rows))==expected
    return sorted(nets)
def antenna_statements(text,layer_names):
    """Read full exact native-exported technology LEF; retain every antenna clause."""
    assert "\r"not in text and "\x00"not in text;text.encode("ascii")
    lines=text.splitlines();found={};active=None;buf=[]
    for ln,line in enumerate(lines,1):
        s=line.strip()
        if active is None:
            m=re.fullmatch(r"LAYER (\S+)",s)
            if m:active=m.group(1);assert active not in found;found[active]=[];buf=[]
            continue
        if buf:
            buf.append(s)
            if ";"in s:
                full=" ".join(buf);assert full.count(";")==1 and full.endswith(";")
                found[active].append(full);buf=[]
            continue
        if s=="END "+active:active=None;continue
        if s.startswith("ANTENNA"):
            assert re.match(r"ANTENNA[A-Z]+(?: |;)",s),("antenna clause",ln,s)
            if ";"in s:assert s.count(";")==1 and s.endswith(";");found[active].append(s)
            else:buf=[s]
    assert active is None and not buf
    assert set(found)==set(layer_names),("complete technology layer census",set(found)^set(layer_names))
    return found
def join(rows,native):
    nets=validate(rows,(609,697,916));assert set(native)==set(nets)
    for net in nets:
        n=native[net];assert n["name"]==net and n["wire_present"]and not n["special"]
        pins=n["pins"];by={p["display_name"]:p for p in pins};assert len(by)==len(pins)
        for r in rows:
            if r["net"]!=net:continue
            assert r["pin"]in by,("missing pin",net,r["pin"])
            p=by[r["pin"]];assert p["master"][1]==r["master"]and p["io"]=="INPUT"
            assert p["gate_area_max"]>0 and math.isfinite(p["gate_area_max"])
    return dict(status="COMPLETE_609_NET_697_PIN_NATIVE_JOIN_NOT_REPAIR",nets=609,pins=697,checks=916,
      all_report_violations_joined=True,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
