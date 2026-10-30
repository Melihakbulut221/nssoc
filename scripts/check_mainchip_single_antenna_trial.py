#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted real contract controls, exact insertion footprint and preserved failure."""
import argparse,copy,json,os,subprocess,tempfile
from pathlib import Path
from unittest.mock import patch
import mainchip_single_antenna_trial as p
import cloud_mainchip_single_antenna_trial as host
import mainchip_original_clock_restoration as c
def capsule_controls(ctx):
    positive=[];refused=[]
    def fixture(mode):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);work=root/"work";work.mkdir();out=work/"out";out.mkdir()
            evidence=root/"evidence";evidence.mkdir();(work/"owner.json").write_bytes(p.encode(ctx))
            directory=out/"work/single-antenna-trial";directory.mkdir(parents=True)
            native=directory/"candidate.odb";native.write_bytes(b"synthetic bytes, not a native database")
            if mode=="symlink":
                native.unlink();native.symlink_to(work/"owner.json")
            tag="cloud-results-"+ctx["token"]+"-"+host.GROUP
            proof=dict(tag=tag,release_id=7)
            assets=([dict(name="unexpected",id=1,size=0,digest="sha256:"+"0"*64)]if mode=="unexpected_asset"else [])
            def read(path):
                if path=="releases/tags/"+tag:return dict(id=7,tag_name=tag,target_commitish=ctx["source"],draft=False,prerelease=True,assets=copy.deepcopy(assets))
                assert path=="git/ref/tags/"+tag
                return dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=ctx["source"]))
            def upload(argv,**kw):
                assert argv[:3]==["gh","release","upload"]and argv[3]==tag and argv[5:]==["--repo","Melihakbulut221/nssoc"]
                path=Path(argv[4]);row=p.pin(path.read_bytes())
                assets.append(dict(id=len(assets)+1,name=path.name,size=row["bytes"],
                  digest="sha256:"+("0"*64 if mode=="wrong_digest"else row["sha256"])))
                if mode=="changed_output":native.write_bytes(b"changed after archive")
                return subprocess.CompletedProcess(argv,1 if mode=="uncertain_success"else 0,
                    stdout=b"synthetic upload",stderr=b"synthetic transport uncertainty"if mode=="uncertain_success"else b"")
            with patch.object(host.f,"api",read),patch.object(host.subprocess,"run",upload):
                result=host.publish_capsule(ctx,proof,work,out,evidence)
            assert result["status"]=="COMPLETE_PERMANENT_NATIVE_CAPSULE"and len(result["assets"])==3
            assert result["files"]=={"work/single-antenna-trial/candidate.odb":p.pin(native.read_bytes())}
            assert (evidence/"native-capsule-publication.json").is_file()
            return result
    for mode in("complete","uncertain_success"):
        result=fixture(mode)
        assert all((x["reconciled_upload_error"]is not None)==(mode=="uncertain_success")for x in result["assets"])
        positive.append("synthetic_capsule_"+mode)
    for mode in("wrong_digest","unexpected_asset","symlink","changed_output"):
        try:fixture(mode)
        except (AssertionError,ValueError,KeyError,TypeError):refused.append("capsule_"+mode)
        else:raise AssertionError("capsule did not refuse "+mode)
    return positive,refused


def controls():
    ctx=host.context(os.environ);host.source_gate();p.source_guard()
    assert subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==ctx["source"]
    positive=["exact_deployment_and_source_pins"];refused=[]
    def reject(name,fn):
        try:fn()
        except(AssertionError,ValueError,KeyError,TypeError):refused.append(name);return
        raise AssertionError("not refused: "+name)
    authentic=json.loads((p.ROOT/p.VIOLATIONS).read_bytes());vv=[r for r in authentic if r["net"]==p.NET]
    assert len(vv)==1
    r=vv[0];assert r["pin"]=="/".join(p.SINK)and r["master"]=="sg13g2_buf_1"and r["layer"]=="Metal4"and r["rule"]=="Cumulative area"
    assert r["display_value"]=="216.77"and r["display_limit"]=="200.00"and r["violated"]
    positive.append("authentic_single_target_violation")
    row=dict(name="ROW",box=[0,0,10000,1000],orientation="R0",direction="HORIZONTAL",count=20,spacing=500,
      site=["lib","site"],site_height=1000,site_width=500)
    occ=[dict(name="sink",box=[4000,0,5000,1000]),dict(name="other",box=[2500,0,4000,1000])]
    sites=p.legal_sites([row],occ,[1000,1000],[4000,0,5000,1000])
    assert sites[0]["location"]==[5000,0]and all(not p.overlap(q["box"],v["box"])for q in sites for v in occ)
    assert not p.legal_sites([row],[dict(name="blocked",box=row["box"])],[1000,1000],[4000,0,5000,1000])
    positive.append("actual_same_row_whole_site_nonoverlap_selection")
    for name,rr,sz,lim in[
      ("direction",dict(row,direction="VERTICAL"),[1000,1000],40000),
      ("orientation",dict(row,orientation="R90"),[1000,1000],40000),
      ("pitch",dict(row,spacing=501),[1000,1000],40000),
      ("fractional_sites",row,[1100,1000],40000),
      ("empty_count",dict(row,count=0),[1000,1000],40000),
      ("limit",row,[1000,1000],40001),
      ("negative_width",row,[-1,1000],40000)]:
        reject("placement_"+name,lambda rr=rr,sz=sz,lim=lim:p.legal_sites([rr],occ,sz,[4000,0,5000,1000],lim))
    reject("duplicate_rows",lambda:p.legal_sites([row,row],occ,[1000,1000],[4000,0,5000,1000]))
    points=p.branch([4000,200,4200,400],[6000,200,6200,400],160)
    assert points==[[4100,300],[6100,300]]and p.branch_boxes(points,160)==[[4020,220,6180,380]]
    corner=p.branch([4000,200,4200,400],[6000,600,6200,800],160)
    assert corner==[[4100,300],[6100,300],[6100,700]]
    positive.append("actual_pin_centres_straight_and_L_branch")
    reject("wrong_route_width",lambda:p.branch([0,0,200,200],[400,0,600,200],200))
    rec=("- "+p.NET+" ( I0 X ) ( fanout36953 A )\n      + ROUTED Metal1 ( 4000 300 ) ( 4100 300 ) ;\n").encode()
    append=p.append_branch(rec,points)
    assert append.startswith(rec[:rec.index(b";")])and append.count(b"NEW Metal1")==1
    positive.append("only_additive_Metal1_path")
    for name,rr,pts in[
      ("other_net",rec.replace(p.NET.encode(),b"other"),points),
      ("diagonal",rec,[[4100,300],[6100,700]]),
      ("off_grid",rec,[[4101,300],[6100,300]]),
      ("bool_coordinate",rec,[[True,300],[6100,300]]),
      ("route_property",rec.replace(b" ;",b" + PROPERTY BAD 1 ;"),points),
      ("extra_semicolon",rec+b";",points),
      ("duplicate_point",rec,[[4100,300],[4100,300]])]:
        reject("branch_"+name,lambda rr=rr,pts=pts:p.append_branch(rr,pts))
    rows=[("- I%d BUF + PLACED ( %d 0 ) N ;\n"%(i,i)).encode()for i in range(153128)]
    added=("- "+p.NEW+" sg13g2_antennanp + PLACED ( 1 2 ) N ;\n").encode()
    header=b'VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN top ;\nUNITS DISTANCE MICRONS 1000 ;\n'
    other=b"- clk ( I0 A ) ( I1 X )\n      + FIXED Metal1 ( 1 2 ) ( 2 2 ) ;\n"
    special=b"SPECIALNETS 2 ;\n- VDD + USE POWER ;\n- VSS + USE GROUND ;\nEND SPECIALNETS\n"
    before=header+b"COMPONENTS 153128 ;\n"+b"".join(rows)+b"END COMPONENTS\n"+special+b"NETS 2 ;\n"+rec+other+b"END NETS\nEND DESIGN\n"
    after=before.replace(b"COMPONENTS 153128",b"COMPONENTS 153129").replace(b"END COMPONENTS\n",added+b"END COMPONENTS\n")
    after=after.replace(b"- VDD ",("- VDD ( "+p.NEW+" VDD ) ").encode()).replace(b"- VSS ",("- VSS ( "+p.NEW+" VSS ) ").encode())
    arec=rec.replace(b" ( I0 X )",(" ( "+p.NEW+" A ) ( I0 X )").encode())
    after=c.replace_records(after,{p.NET:p.append_branch(arec,points)})
    pins=[[p.NEW,t,n,s]for t,n,s in(("A",p.NET,"SIGNAL"),("VDD","VDD","POWER"),("VSS","VSS","GROUND"))]
    aa=p.normalized_def(before,pins,());bb=p.normalized_def(after,pins,(p.NEW,))
    assert aa["sha256"]==bb["sha256"]and bb["removed_components"]==[p.NEW]
    positive.append("full153128_to153129_only_added_diode_three_connections")
    def same(raw):assert p.normalized_def(raw,pins,(p.NEW,))["sha256"]==aa["sha256"]
    for name,bad in[
      ("other_placement",after.replace(b"- I0 BUF + PLACED ( 0 0 )",b"- I0 BUF + PLACED ( 9 0 )")),
      ("other_connection",after.replace(b"( I0 A )",b"( I2 A )")),
      ("other_fixed_wire",after.replace(b"+ FIXED Metal1 ( 1 2 )",b"+ FIXED Metal1 ( 7 2 )")),
      ("other_master",after.replace(b"- I0 BUF ",b"- I0 WRONG ")),
      ("wrong_added_master",after.replace(b"sg13g2_antennanp",b"sg13g2_buf_1")),
      ("wrong_supply",after.replace(b"- VDD ",b"- BAD ")),
      ("wrong_census",after.replace(b"COMPONENTS 153129",b"COMPONENTS 153128")),
      ("quoted_connection",after.replace(b"END DESIGN",('PROPERTY "( '+p.NEW+' A )"\nEND DESIGN').encode()))]:
        reject("delta_"+name,lambda bad=bad:same(bad))
    cp,cr=capsule_controls(ctx);positive+=cp;refused+=cr
    assert len(positive)==8 and len(refused)==28
    return dict(status="PASS_SINGLE_ANTENNA_TRIAL_SOURCE_CONTROLS",current_context=ctx,positive=positive,refusals=refused,
      positive_count=len(positive),refusal_count=len(refused),native_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",type=Path,required=True);a=ap.parse_args();error=None
    try:r=controls()
    except BaseException as exc:error=exc;r=dict(status="FAIL_SINGLE_ANTENNA_TRIAL_SOURCE_CONTROLS",error=repr(exc),native_executed=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(p.encode(r));print(json.dumps(r,sort_keys=True),flush=True)
    if error is not None:raise error
if __name__=="__main__":main()
