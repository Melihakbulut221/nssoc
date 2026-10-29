#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic acquisition guards; no native archive or CAD acquisition."""
import argparse,base64,copy,hashlib,io,json,os,tarfile,tempfile,zlib
from pathlib import Path
from unittest.mock import patch
import cloud_mainchip_current_neighborhood as w
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    ctx=w.context(os.environ);w.source_gate();passed=[];refused=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,ValueError,KeyError,TypeError):refused.append(name)
        else:raise AssertionError("did not refuse "+name)
    env=dict(os.environ)
    for key,value in (("GITHUB_ACTIONS","false"),("GITHUB_RUN_ATTEMPT","2"),
                      ("GITHUB_REF","refs/heads/main"),("GITHUB_EVENT_NAME","push")):
        bad=dict(env);bad[key]=value;reject("context:"+key,lambda bad=bad:w.context(bad))
    tag="cloud-results-"+ctx["token"]+"-"+w.GROUP
    proof=dict(tag=tag,tested_source=ctx["source"],release_id=7,existing_assets=[],
      target_verified=True,assets_overwritten=False,externally_reserved=True,creation_attempted=False)
    rel=dict(id=7,tag_name=tag,target_commitish=ctx["source"],draft=False,prerelease=True,assets=[])
    ref=dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=ctx["source"]))
    assert w.reservation(ctx,proof,rel,ref)["verified_before_acquisition"];passed.append("exact reservation")
    for key,value in (("tested_source","0"*40),("externally_reserved",False),
                      ("creation_attempted",True),("assets_overwritten",True),("existing_assets",[1])):
        bad=dict(proof);bad[key]=value;reject("reservation:"+key,lambda bad=bad:w.reservation(ctx,bad,rel,ref))
    with tempfile.TemporaryDirectory()as temp:
        root=Path(temp);serial=0
        data=b"synthetic current database bytes, never a native ODB"
        member=w.CURRENT_MEMBER;pin=w.f.digest(data)
        expected={member:pin,"other.json":w.f.digest(b"{}")}
        def archive(entries):
            nonlocal serial
            serial+=1;path=root/("case-"+str(serial)+".tgz")
            with tarfile.open(path,"w:gz")as t:
                for name,raw,kind in entries:
                    info=tarfile.TarInfo(name)
                    if kind=="link":info.type=tarfile.SYMTYPE;info.linkname="elsewhere";t.addfile(info)
                    else:info.size=len(raw);t.addfile(info,io.BytesIO(raw))
            return path
        good=[(member,data,"file"),("other.json",b"{}","file")]
        def select(entries,mapping=None):
            return w.select_database(archive(entries),expected if mapping is None else mapping,root/("input-"+str(serial)))
        with patch.object(w,"CURRENT",pin):
            got=select(good);assert got["full_archive_verified"]and got["full_members"]==expected;passed.append("complete stream")
            for name,entries in (
              ("missing",good[:1]),("duplicate",good+good[:1]),
              ("extra",good+[("extra",b"x","file")]),("wrong digest",[(member,b"x"*len(data),"file"),good[1]]),
              ("traversal",good+[("../escape",b"x","file")]),
              ("symlink",[(member,b"","link"),good[1]])):
                reject("archive:"+name,lambda entries=entries:select(entries))
            wrong=copy.deepcopy(expected);wrong[member]["sha256"]="0"*64
            reject("archive wrong selected map",lambda:select(good,wrong))
        evidence=root/"evidence";evidence.mkdir()
        (evidence/"report.json").write_bytes(b'{"accepted":false}\n')
        output=io.StringIO()
        with patch("sys.stdout",output):w.emit(evidence)
        lines=output.getvalue().splitlines()
        index=json.loads(lines[0].split(" ",1)[1]);assert index=={"report.json":w.f.file_digest(evidence/"report.json")}
        chunks=[json.loads(x.split(" ",1)[1])for x in lines[1:]]
        unpacked=zlib.decompress(b"".join(base64.b64decode(x["base64"])for x in chunks))
        assert unpacked==(evidence/"report.json").read_bytes();passed.append("complete compressed evidence")
        (evidence/"forbidden.odb").write_bytes(b"x")
        reject("native evidence refusal",lambda:w.emit(evidence))
    result=dict(status="PASS_CURRENT_NEIGHBORHOOD_SOURCE_CONTROLS",current_context=ctx,
      positive=passed,refusals=refused,positive_count=len(passed),refusal_count=len(refused),
      all_archives_synthetic=True,native_archive_acquired=False,native_executed=False,
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(w.f.encode(result))
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
