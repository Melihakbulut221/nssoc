#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted controls for exact candidate selection, exclusion bounds and publication."""
import argparse,copy,json,os,subprocess,tempfile
from pathlib import Path
from unittest.mock import patch
import mainchip_net459_diode_prune as p
import cloud_mainchip_net459_diode_prune as host
import mainchip_net459_connectivity as graph
import mainchip_original_clock_restoration as c
import check_mainchip_southern_neighborhood as inherited

def capsule_controls(ctx):
    positive=[];refused=[]
    def fixture(mode):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);work=root/"work";work.mkdir();out=work/"out";out.mkdir()
            evidence=root/"evidence";evidence.mkdir();(work/"owner.json").write_bytes(p.encode(ctx))
            directory=out/"work/net459-diode-prune";directory.mkdir(parents=True)
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
            assert result["files"]=={"work/net459-diode-prune/candidate.odb":p.pin(native.read_bytes())}
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
        except (AssertionError,ValueError,KeyError,TypeError):refused.append(name)
        else:raise AssertionError("not refused: "+name)
    source,proof=graph.source_guard();plan=p.plan(source)
    assert (plan["source_paths"],plan["paths"],plan["shape_count"],plan["raw_count"])==(71,43,85,227)
    positive.append("authentic_full_raw_and_whole_via_selection")
    for label,edit in(
      ("short_geometry",lambda x:x["projection"]["shapes"][21]["box"].__setitem__(0,0)),
      ("omitted_shape",lambda x:x["projection"]["shapes"].pop()),
      ("omitted_pin",lambda x:x["pins"].pop()),
      ("unsupported_raw_path",lambda x:x["projection"]["raw"][0].__setitem__(0,97)),
      ("raw_width_rule",lambda x:x["projection"]["raw"][4].__setitem__(0,3)),
      ("wrong_native_sigtype",lambda x:x.__setitem__("sigtype","CLOCK"))):
        bad=copy.deepcopy(source);edit(bad);reject(label,lambda bad=bad:p.plan(bad))
    rec=b"- net459 ( fanout459 X ) ( fanout36386 A ) ( ANTENNA_1573 A ) ( ANTENNA_1574 A ) ( ANTENNA_1575 A )\n"
    rec+=b"      + ROUTED Metal1 ( 0 0 ) ( 0 2 )\n"
    rec+=b"".join(("      NEW Metal1 ( %d 0 ) ( %d 2 )\n"%(i,i)).encode()for i in range(1,71))+b" ;\n"
    chosen=p.prune_record(rec,plan["keep_paths"],71)
    assert chosen.count(b"NEW ")==42 and chosen.count(b"+ ROUTED")==1
    assert chosen.startswith(rec[:rec.index(b"      + ROUTED")])
    positive.append("whole_DEF_paths_and_exact_connection_prefix")
    for name,record,keep,count in(
      ("extra_route_clause",rec.replace(b"      NEW Metal1",b"      + ROUTED Metal1",1),plan["keep_paths"],71),
      ("path_count",rec,plan["keep_paths"],70),
      ("missing_first_path",rec,plan["keep_paths"][1:],71),
      ("duplicate_path",rec,[0,0],71),
      ("unknown_path",rec,[0,71],71),
      ("unsorted_path",rec,[0,2,1],71),
      ("wire_suffix_property",rec.replace(b" ;\n",b" + PROPERTY BAD 1 ;\n"),plan["keep_paths"],71)):
        reject(name,lambda record=record,keep=keep,count=count:p.prune_record(record,keep,count))
    rows=[("- I%d BUF + PLACED ( %d 0 ) N ;\n"%(i,i)).encode()for i in range(153128)]
    deleted=[("- "+x+" sg13g2_antennanp + PLACED ( 1 2 ) N ;\n").encode()for x in p.REMOVE]
    header=b'VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN top ;\nUNITS DISTANCE MICRONS 1000 ;\n'
    other=b"- clk ( I0 A ) ( I1 X )\n      + FIXED Metal1 ( 1 2 ) ( 2 2 ) ;\n"
    special=b"SPECIALNETS 2 ;\n- VDD ( ANTENNA_1574 VDD ) ( ANTENNA_1575 VDD ) + USE POWER ;\n- VSS ( ANTENNA_1574 VSS ) ( ANTENNA_1575 VSS ) + USE GROUND ;\nEND SPECIALNETS\n"
    before=header+b"COMPONENTS 153130 ;\n"+b"".join(rows+deleted)+b"END COMPONENTS\n"+special+b"NETS 2 ;\n"+rec+other+b"END NETS\nEND DESIGN\n"
    pins=sorted([[name,term,net,sig]for name in p.REMOVE for term,net,sig in(("A","net459","SIGNAL"),("VDD","VDD","POWER"),("VSS","VSS","GROUND"))])
    after=before.replace(b"COMPONENTS 153130",b"COMPONENTS 153128")
    for row in deleted:after=after.replace(row,b"")
    for name,term,net,sig in pins:after=after.replace(("( "+name+" "+term+" )").encode(),b"")
    after=c.replace_records(after,{"net459":p.prune_record(c.parse_def(after)["records"]["net459"],plan["keep_paths"],71)})
    a=p.normalized_def(before,pins,p.REMOVE);b=p.normalized_def(after,pins,())
    assert a["sha256"]==b["sha256"]and a["removed_components"]==list(p.REMOVE)and not b["removed_components"]
    positive.append("complete153130_to153128_delta_with_six_connections")
    assert c.parse_def(before)["records"]["clk"]==c.parse_def(after)["records"]["clk"]
    positive.append("unrelated_fixed_record_byte_identity")
    def require_same(raw):assert p.normalized_def(raw,pins,())["sha256"]==a["sha256"]
    for label,bad in(
      ("other_placement",after.replace(b"- I0 BUF + PLACED ( 0 0 )",b"- I0 BUF + PLACED ( 9 0 )")),
      ("other_net_connection",after.replace(b"( I0 A )",b"( I2 A )")),
      ("other_fixed_geometry",after.replace(b"+ FIXED Metal1 ( 1 2 )",b"+ FIXED Metal1 ( 7 2 )")),
      ("other_master",after.replace(b"- I0 BUF ",b"- I0 WRONG "))):
        reject(label,lambda bad=bad:require_same(bad))
    reject("wrong_component_census",lambda:p.normalized_def(before.replace(b"COMPONENTS 153130",b"COMPONENTS 153128"),pins,p.REMOVE))
    reject("wrong_diode_master",lambda:p.normalized_def(before.replace(b"sg13g2_antennanp",b"sg13g2_buf_1",1),pins,p.REMOVE))
    reject("wrong_supply_net",lambda:p.normalized_def(before.replace(b"- VDD ",b"- VDD_WRONG "),pins,p.REMOVE))
    reject("quoted_connection",lambda:p.normalized_def(before.replace(b"END DESIGN",b'PROPERTY "( ANTENNA_1574 A )"\nEND DESIGN'),pins,p.REMOVE))
    graph_controls=graph.controls()
    # Explicit synthetic context for unchanged inherited context/lifecycle fixtures.
    # The real deployment context above remains the actual candidate branch.
    with patch.dict(os.environ,{"GITHUB_REF":"refs/heads/"+inherited.w.BRANCH}):
        old=inherited.controls(inherited.w.context(os.environ))
    positive.append("unchanged_inherited_archive_lifecycle_and_graph_controls")
    cp,cr=capsule_controls(ctx);positive+=cp;refused+=cr
    assert len(positive)==8 and len(refused)==25
    return dict(status="PASS_NET459_DIODE_PRUNE_SOURCE_CONTROLS",current_context=ctx,
      positive=positive,refusals=refused,positive_count=len(positive),refusal_count=len(refused),
      authentic_plan=plan,authentic_source_proof=proof,graph_controls=graph_controls,
      inherited_controls=old,inherited_context_explicitly_synthetic=True,
      full_DEF_control_fixture_synthetic=True,native_executed=False,physical_acceptance=False,
      timing_accepted=False,full_phy_accepted=False)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    primary=None
    try:r=controls()
    except BaseException as exc:
        primary=exc;r=dict(status="FAIL_NET459_DIODE_PRUNE_SOURCE_CONTROLS",error=repr(exc),
          native_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("xb")as f:f.write(p.encode(r))
    print(json.dumps(r,sort_keys=True),flush=True)
    if primary is not None:raise primary
if __name__=="__main__":main()
