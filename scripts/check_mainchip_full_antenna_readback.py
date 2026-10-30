#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted positive/refusal controls exercising actual report, archive and publication paths."""
import argparse,copy,io,json,os,subprocess,tarfile,tempfile
from pathlib import Path
from unittest.mock import patch
import mainchip_full_antenna_report as p
import cloud_mainchip_full_antenna_readback as h
AUTHENTIC="docs/evidence/mainchip-net459-diode-prune-terminal-40976029940/records/native/net459-diode-prune/candidate-net459-antenna.rpt"
def pair(kind,rule,value="1.00",limit="20.00",flag=False):
    return "      "+kind+" area ratio: "+value+"\n      Required ratio: "+limit+" ("+rule+") "+("(VIOLATED)"if flag else"")+"\n"
def layer(name="Via1",rule=None):
    s="    Layer: "+name+"\n"+pair("Partial","Gate area",flag=rule=="Gate area")
    if rule!="Gate area":s+=pair("Cumulative","Cumulative area",flag=rule=="Cumulative area")
    if name in p.ROUTING:s+=pair("Partial","Side area",flag=rule=="Side area")+pair("Cumulative","Cumulative side area",flag=rule=="Cumulative side area")
    return s+"\n"
def net(name="n",lay=None):return "Net: "+name+"\n  Pin:   u/A (BUF)\n"+(layer()if lay is None else lay)+"\n"
def parse(s,count=None):return p.parse(io.StringIO(s),count)
def controls():
    ctx=h.context(os.environ);h.source_guard();positive=[];refused=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,ValueError,KeyError,TypeError):refused.append(name)
        else:raise AssertionError("not refused: "+name)
    actual=(h.ROOT/AUTHENTIC).read_text();obs=parse(actual,0)
    assert obs[0]["counts"]["nets"]==1 and not obs[2];positive.append("actual_pinned_net459_report")
    for lname,rule in(("Via1",None),("Via1","Gate area"),("Via1","Cumulative area"),
      ("Metal2",None),("Metal2","Gate area"),("Metal2","Cumulative area"),("Metal2","Side area"),("Metal2","Cumulative side area")):
        r=parse(net(lay=layer(lname,rule)),int(rule is not None))
        assert len(r[2])==int(rule is not None);positive.append("complete_"+lname+"_"+str(rule))
    rounded=net(lay=layer("Via1","Gate area").replace("1.00","20.00"))
    assert parse(rounded,1)[2][0]["display_value"]=="20.00";positive.append("native_unrounded_violation_flag_retained")
    a=net("n1",layer("Via1","Gate area"));b=net("n2",layer("Metal3","Cumulative area"))
    comparison=p.compare(parse(a+b,2),parse(b+a,2))
    assert comparison["identical_violation_semantics"]and not comparison["changed_net_census"];positive.append("order_independent_complete_semantics")
    comparison=p.compare(parse(a,1),parse(a.replace("1.00","2.00"),1))
    assert not comparison["identical_violation_semantics"]and len(comparison["changed_violations"])==1;positive.append("exact_display_change_visible")
    basic=net();routing=net(lay=layer("Metal2"));violate=net(lay=layer("Via1","Gate area"))
    bads={
     "duplicate_net":basic+basic,"duplicate_pin":basic+"  Pin:   u/A (BUF)\n"+layer(),
     "duplicate_layer":basic+layer(),"duplicate_rule":basic.replace("\n\n",pair("Cumulative","Cumulative area")+"\n",1),
     "unknown_line":basic+"unknown\n","missing_final_LF":basic.rstrip("\n"),"CRLF":basic.replace("\n","\r\n"),
     "missing_required":basic.replace("      Required ratio: 20.00 (Gate area) \n",""),
     "blank_inside_pair":basic.replace("      Required ratio:","\n      Required ratio:",1),
     "unknown_layer":basic.replace("Via1","Unknown"),"wrong_kind":basic.replace("Partial","Cumulative",1),
     "unknown_rule":basic.replace("Gate area","Different"),"missing_CAR":basic.replace(pair("Cumulative","Cumulative area"),""),
     "extra_CAR_after_violated_PAR":violate+pair("Cumulative","Cumulative area"),
     "missing_PSR":routing.replace(pair("Partial","Side area"),""),"missing_CSR":routing.replace(pair("Cumulative","Cumulative side area"),""),
     "cut_with_side_rule":basic+pair("Partial","Side area"),"NaN":basic.replace("1.00","nan",1),
     "non_ascii":basic.replace("BUF","BÜF"),"empty":"","pin_without_net":"  Pin:   u/A (BUF)\n"+layer(),
     "layer_without_pin":"Net: n\n"+layer(),"value_without_layer":"Net: n\n  Pin:   u/A (BUF)\n"+pair("Partial","Gate area"),
     "required_without_value":basic.replace("      Partial area ratio: 1.00\n",""),
     "trailing_unpaired_ratio":basic+"      Partial area ratio: 1.00\n"}
    for name,bad in bads.items():reject("report_"+name,lambda bad=bad:parse(bad))
    reject("native_net_census_mismatch",lambda:parse(basic,1))
    # Entire archive is checked even when a corrupted member was not selected.
    def archive_case(mode):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);archive=root/"input.tar.gz";files={"a.txt":dict(bytes=3,sha256="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"),"b.txt":dict(bytes=3,sha256="cb8379ac2098aa165029e3938a51da0bcecfc008fd6795f401178647f96c5b34")}
            members=[("a.txt",b"abc"),("b.txt",b"def")]
            if mode=="missing":members.pop()
            if mode=="duplicate":members.append(members[0])
            if mode=="excluded_corrupt":members[1]=("b.txt",b"bad")
            if mode=="extra":members.append(("extra.txt",b"x"))
            if mode=="traversal":members[0]=("../a.txt",b"abc")
            if mode=="absolute":members[0]=("/a.txt",b"abc")
            with tarfile.open(archive,"w:gz")as tar:
                for name,raw in members:
                    t=tarfile.TarInfo(name);t.size=len(raw);tar.addfile(t,io.BytesIO(raw))
                if mode in("symlink","hardlink","directory"):
                    t=tarfile.TarInfo("bad");t.type={"symlink":tarfile.SYMTYPE,"hardlink":tarfile.LNKTYPE,"directory":tarfile.DIRTYPE}[mode];t.linkname="a.txt";tar.addfile(t)
            selected={"unknown.txt"}if mode=="selection"else{"a.txt"}
            result=h.restore(archive,files,selected,root/"selected")
            assert result==files and (root/"selected/a.txt").read_bytes()==b"abc"and not(root/"selected/b.txt").exists()
    archive_case("complete");positive.append("complete_archive_unselected_member_authentication")
    for mode in("missing","duplicate","excluded_corrupt","extra","traversal","absolute","symlink","hardlink","directory","selection"):
        reject("archive_"+mode,lambda mode=mode:archive_case(mode))
    # Actual publication function with a synthetic API/upload transport.
    def publish_case(mode):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td);(out/"result.json").write_text("{}\n")
            assets=[];reserved=dict(release_id=7)
            if mode=="symlink":(out/"bad.json").symlink_to(out/"result.json")
            if mode=="native_suffix":(out/"bad.odb").write_bytes(b"synthetic")
            if mode=="unexpected":assets.append(dict(id=99,name="unexpected",size=0,digest="sha256:"+"0"*64))
            def get(path):
                if path=="releases/tags/"+ctx["tag"]:return dict(id=7,tag_name=ctx["tag"],target_commitish=ctx["source"],draft=False,prerelease=True,assets=copy.deepcopy(assets))
                assert path=="git/ref/tags/"+ctx["tag"]
                return dict(ref="refs/tags/"+ctx["tag"],object=dict(type="commit",sha=ctx["source"]))
            def upload(argv,**kw):
                assert argv[:3]==["gh","release","upload"]and argv[3]==ctx["tag"]
                path=Path(argv[4]);row=h.pin(path)
                assets.append(dict(id=len(assets)+1,name=path.name,size=row["bytes"],digest="sha256:"+("0"*64 if mode=="digest"else row["sha256"])))
                if mode=="changed":path.write_text("changed")
                return subprocess.CompletedProcess(argv,1 if mode=="uncertain"else 0,stdout=b"full stdout",stderr=b"full stderr")
            with patch.object(h,"api",get),patch.object(h.subprocess,"run",upload):r=h.publish(ctx,reserved,out)
            assert r["status"]=="COMPLETE_PERMANENT_DERIVED_PUBLICATION"and len(r["assets"])==2
            assert all(bool(x["reconciled_error"])==(mode=="uncertain")for x in r["assets"])
    for mode in("complete","uncertain"):publish_case(mode);positive.append("publication_"+mode)
    for mode in("symlink","native_suffix","unexpected","digest","changed"):reject("publication_"+mode,lambda mode=mode:publish_case(mode))
    assert len(positive)==15 and len(refused)==41
    return dict(status="PASS_FULL_ANTENNA_READBACK_SOURCE_CONTROLS",context=ctx,positive=positive,refusal=refused,
      positive_count=len(positive),refusal_count=len(refused),native_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
def main():
    a=argparse.ArgumentParser();a.add_argument("--output",type=Path,required=True);args=a.parse_args();error=None
    try:r=controls()
    except BaseException as exc:
        error=exc;r=dict(status="FAIL_FULL_ANTENNA_READBACK_SOURCE_CONTROLS",error=repr(exc),native_executed=False)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(p.encoded(r));print(json.dumps(r,sort_keys=True),flush=True)
    if error is not None:raise error
if __name__=="__main__":main()
