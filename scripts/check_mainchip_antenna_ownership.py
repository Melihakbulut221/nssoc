#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Actual parser/join/acquisition controls; no CAD or real native acquisition."""
import argparse,copy,hashlib,io,json,tarfile,tempfile
from pathlib import Path
from unittest.mock import patch
import mainchip_antenna_ownership as p
import cloud_mainchip_antenna_ownership as h
import cloud_mainchip_full_antenna_readback as reader
def controls():
    h.source_gate();positive=[];refusal=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError,RuntimeError,TypeError):refusal.append(name);return
        raise AssertionError("accepted invalid case "+name)
    rows=p.load_violations(h.ROOT);names=p.validate(rows,(609,697,916));positive.append("authentic_complete916_violation_list")
    native={}
    for r in rows:
        n=native.setdefault(r["net"],dict(name=r["net"],wire_present=True,special=False,pins=[]))
        if not any(x["display_name"]==r["pin"]for x in n["pins"]):n["pins"].append(dict(display_name=r["pin"],master=["lib",r["master"]],io="INPUT",gate_area_max=1.0))
    result=p.join(rows,native);assert result["all_report_violations_joined"];positive.append("complete697_pin609_net_join")
    for mode in("duplicate","false_flag","wrong_rule","unknown_layer","bad_number","missing_row"):
        rr=copy.deepcopy(rows)
        if mode=="duplicate":rr.append(rr[0])
        if mode=="false_flag":rr[0]["violated"]=False
        if mode=="wrong_rule":rr[0]["rule"]="Gate area"
        if mode=="unknown_layer":rr[0]["layer"]="Unknown"
        if mode=="bad_number":rr[0]["display_value"]="nan"
        if mode=="missing_row":rr.pop()
        reject("report_"+mode,lambda rr=rr:p.validate(rr,(609,697,916)))
    for mode in("missing_net","missing_pin","master","output_pin","zero_gate","wire_absent","special","duplicate_pin"):
        nn=copy.deepcopy(native);net=rows[0]["net"];nnn=nn[net];pin=nnn["pins"][0]
        if mode=="missing_net":nn.pop(net)
        if mode=="missing_pin":nnn["pins"].pop(0)
        if mode=="master":pin["master"][1]="other"
        if mode=="output_pin":pin["io"]="OUTPUT"
        if mode=="zero_gate":pin["gate_area_max"]=0.0
        if mode=="wire_absent":nnn["wire_present"]=False
        if mode=="special":nnn["special"]=True
        if mode=="duplicate_pin":nnn["pins"].append(pin)
        reject("join_"+mode,lambda nn=nn:p.join(rows,nn))
    lef="VERSION 5.8 ;\nLAYER Metal1\n TYPE ROUTING ;\n ANTENNACUMAREARATIO 400 ;\n ANTENNADIFFAREARATIO PWL (\n ( 0 400 ) ( 1 800 ) ) ;\nEND Metal1\nLAYER Via1\n TYPE CUT ;\nEND Via1\nEND LIBRARY\n"
    out=p.antenna_statements(lef,["Metal1","Via1"]);assert len(out["Metal1"])==2 and out["Via1"]==[];positive.append("complete_multiline_native_lef_antenna_clauses")
    for name,bad,layers in [
      ("missing_layer",lef,["Metal1"]),("duplicate_layer",lef+lef,["Metal1","Via1"]),
      ("unterminated",lef.replace("END Metal1",""),["Metal1","Via1"]),
      ("truncated_clause",lef.replace("( 1 800 ) ) ;","( 1 800 ) )"),["Metal1","Via1"]),
      ("CRLF",lef.replace("\n","\r\n"),["Metal1","Via1"])]:
        reject("lef_"+name,lambda bad=bad,layers=layers:p.antenna_statements(bad,layers))
    def acquisition(mode):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);work=root/"work";ev=root/"evidence";work.mkdir();ev.mkdir()
            selected=h.CURRENT_MEMBER
            members={selected:b"abc","unselected.json":b"{}\n"}
            inventory={n:p.pin(v)for n,v in members.items()}
            tarbytes=io.BytesIO()
            with tarfile.open(fileobj=tarbytes,mode="w:gz")as tf:
                for n,b in members.items():
                    if mode=="unselected_corrupt"and n=="unselected.json":b=b"bad"
                    t=tarfile.TarInfo(n);t.size=len(b);tf.addfile(t,io.BytesIO(b))
            raw=tarbytes.getvalue();ar=p.pin(raw)
            metadata=dict(source=reader.SOURCE,run=reader.PRODUCER,attempt=1,files=inventory)
            parts=dict(archive=ar,parts=[dict(name="candidate-native.tar.gz.part000",**ar)])
            if mode=="metadata_source":metadata["source"]="0"*40
            if mode=="current_pin":metadata["files"][selected]=p.pin(b"bad")
            if mode=="parts":parts["parts"]=[]
            payload={"candidate-outputs.json":p.encoded(metadata),"candidate-parts.json":p.encoded(parts),"candidate-native.tar.gz.part000":raw}
            def download(n,w,e):
                q=w/n;q.write_bytes(payload[n]);return q
            with patch.object(reader,"producer",lambda e:None),patch.object(reader,"download",download),patch.object(h,"CURRENT",p.pin(b"abc")):
                h.acquire_current(work,ev)
            assert (work/"current-input.odb").read_bytes()==b"abc"and not(work/"current-transport").exists()
            record=json.loads((ev/"current-input-restoration.json").read_bytes());assert record["full_members"]==inventory
    acquisition("complete");positive.append("actual_acquisition_authenticates_unselected_members")
    for mode in("unselected_corrupt","metadata_source","current_pin","parts"):reject("acquisition_"+mode,lambda mode=mode:acquisition(mode))
    assert (len(positive),len(refusal))==(4,23)
    return dict(status="PASS_ANTENNA_OWNERSHIP_SOURCE_CONTROLS",positive=positive,refusal=refusal,
      positive_count=len(positive),refusal_count=len(refusal),native_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",type=Path,required=True);a=ap.parse_args();error=None
    try:result=controls()
    except BaseException as exc:error=exc;result=dict(status="FAIL_ANTENNA_OWNERSHIP_SOURCE_CONTROLS",error=repr(exc),native_executed=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(p.encoded(result));print(json.dumps(result,sort_keys=True),flush=True)
    if error is not None:raise error
if __name__=="__main__":main()
