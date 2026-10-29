#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source checks. Every archive/model/native-format fixture is SYNTHETIC."""
import argparse,ast,base64,collections,contextlib,copy,io,json,os,shutil,tarfile,tempfile,traceback,zlib
from pathlib import Path
from unittest.mock import patch
import cloud_cdr_current_rc_contacts as r

def synthetic():
    """API-shaped text fixture, not a current native model or real extraction."""
    c=r.source_guard();d=r.metadata(c);c=copy.deepcopy(c);d=copy.deepcopy(d)
    targets=c["targets"];labels=[n for t in targets.values()for n in t["contacts"]]+["P_avdd","P_sub"]
    anchors=[];records=[];geo=[];edges=[];mappings={}
    for owner,cluster,net,ls in [(17,28,"$131",targets["28"]["contacts"]),(61,124,"$680",targets["124"]["contacts"]),(1,24,"sub",labels[-2:])]:
        center="n"+str(owner);geo.append(dict(component=owner,native_cluster=cluster,native_name=net))
        for k,label in enumerate(ls):
            anchors.append(dict(label=label,wire_component=owner,native_cluster=cluster,point_dbu=[owner*100+k,200],metal=134,logical_labels=[label]))
            if len(ls)==2:
                if k==0:edges.append(["R"+str(len(edges)),ls[0],ls[1],"2"])
            else:edges.append(["R"+str(len(edges)),label,center,str(k+1)])
            edges.append(["C"+str(len(edges)),label,"sub","1e-15"])
    edges.append(["C_cross",labels[0],labels[8],"2e-15"])
    raw_nodes={n for row in edges for n in row[1:3]}
    mappings={n:("wire_cref"if n=="sub"else"w_"+n)for n in raw_nodes}
    for i,a in enumerate(anchors,1):
        label=a["label"];terminal=label.rsplit("_",1)[1]
        real_id=int(label[1:4])if label.startswith("T")else 900+i
        records.append(dict(native_id=real_id,instance="XD"+str(i),model="fixture_device",
          parameters=dict(p="1"),terminals=[dict(terminal=terminal,node=mappings[label],anchor=label,native_cluster=a["native_cluster"],native_net=next(g["native_name"]for g in geo if g["component"]==a["wire_component"]))]))
    header=".subckt pump_wires "+" ".join(labels)+"\n"
    wire=header+"\n".join(" ".join(row)for row in edges)+"\n.ends pump_wires\n"
    mim=["X0",labels[0],labels[8],"cap_cmim","l=1u","w=1u"]
    precise=header+" ".join(mim)+"\n"+"\n".join(" ".join(row)for row in edges)+"\n.ends pump_wires\n"
    comp=dict(interface=["avdd","wire_cref"],device_records=records,wire_node_map=mappings,
      counts=dict(devices=len(records),R=sum(row[0].startswith("R")for row in edges),C=sum(row[0].startswith("C")for row in edges)))
    model=".subckt fixture avdd wire_cref\n"+"\n".join(" ".join([q["instance"],q["terminals"][0]["node"],q["model"],"p=1"])for q in records)+"\n"
    model+="\n".join(" ".join([row[0],mappings[row[1]],mappings[row[2]],row[3]])for row in edges)+"\n.ends fixture\n"
    aa=dict(anchors=anchors,logical_anchor_aliases={n:n for n in labels})
    geometry=dict(wire_components=geo)
    counts=dict(comp["counts"],anchors=len(anchors),components=3,canonical_R=comp["counts"]["R"],canonical_C=comp["counts"]["C"])
    c["counts"]=counts;d["composition"]=comp;d["geometry"]=geometry
    _,components,_=r.incidence(r.statements(wire),aa,geometry,counts)
    d["precise_audit"]={"audit":{"components":components}};d["wire_audit"]={"audit":{"components":components}}
    removed=[" defaultareacap     *mimcap metal5 1500\n"," defaultperimeter   *mimcap metal5 40\n"]
    tech="extract\n# SYNTHETIC units deliberately unspecified\nresist metal7 0.001\ncontact via6 0.2\n"+"".join(removed)+"end\n"
    d["precise_capture"]=dict(intrinsic_capture_binding=dict(native_mim_devices=[dict(export=mim)]),
      private_tech=dict(removed_cdl_device_estimate_lines=removed,all_other_technology_bytes_unchanged=True))
    rep="scale 1000 1 0.5\n"+"\n".join("resist "+row[1]+" "+row[2]+" "+row[3]for row in edges if row[0].startswith("R"))+"\n"
    rep+="\n".join('rnode "'+n+'" 0 0 1 2 metal7'for n in sorted(raw_nodes)if n!="sub")+"\n"
    files={}
    for name in c["selected"]:
        if name.endswith("composition.json"):raw=r.encode(comp)
        elif name.endswith("pd500-mim-wire.spice"):raw=model.encode()
        elif name.endswith("anchors08.json"):raw=r.encode(aa)
        elif name.endswith("pump_wires.res.ext"):raw=rep.encode()
        elif name.endswith("pump_wires.ext"):raw=b'scale 1000 1 0.5\nstyle "ngspice()"\n'
        elif name.endswith("verified-wire-projection.spice"):raw=wire.encode()
        elif name.endswith("wires.spice"):raw=(precise if name.startswith("mim/")else wire).encode()
        elif name.endswith("extract.tech"):raw=(tech if name.startswith("canonical")else tech.replace(removed[0],"").replace(removed[1],"")).encode()
        else:raw=b'# SYNTHETIC Tcl\nset topvia2_resistance 0.2\n'
        files[name]=raw
    c["selected"]={n:r.fingerprint(b)["sha256"]for n,b in files.items()}
    d["full"]=dict(c["selected"])
    return c,d,files

def archive_bytes(files,directory="cloud-cdr-selector-width-fresh-rc",extra=None,omit=None):
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode="w:gz")as tar:
        for name,raw in files.items():
            if name==omit:continue
            entry=tarfile.TarInfo(directory+"/"+name);entry.size=len(raw);tar.addfile(entry,io.BytesIO(raw))
        if extra:
            entry,raw=extra;tar.addfile(entry,io.BytesIO(raw)if raw is not None else None)
    return buffer.getvalue()

def controls():
    c=r.source_guard();d=r.metadata(c);positive=[];refusal=[];lifecycle=[]
    def good(name,fn):value=fn();positive.append(name);return value
    def bad(name,fn,message=None):
        try:fn()
        except (AssertionError,ValueError,KeyError,IndexError,TypeError,FileExistsError,OSError,tarfile.TarError,UnicodeError)as exc:
            if message is not None:assert message in str(exc),(name,str(exc))
            refusal.append(dict(name=name,error=type(exc).__name__,message=str(exc)));return
        raise AssertionError("missing refusal: "+name)
    def mutated(obj,fn):
        value=copy.deepcopy(obj);fn(value);return value
    def no_network(*a,**kw):raise AssertionError("UNEXPECTED SOURCE-CONTROL NETWORK")
    good("authentic complete6647 metadata",lambda:r.metadata(c))
    good("authentic current20asset threejob success",lambda:r.validate_live(c,d["run"],d["jobs"],d["release"],d["ref"]))
    env=dict(GITHUB_ACTIONS="true",GITHUB_EVENT_NAME="workflow_dispatch",GITHUB_REPOSITORY=r.REPOSITORY,
      GITHUB_REF="refs/heads/"+r.BRANCH,GITHUB_RUN_ATTEMPT="1",GITHUB_RUN_ID="321",GITHUB_SHA="a"*40)
    ctx=good("strict current hosted context",lambda:r.context(env))
    tag="cloud-results-"+ctx["token"]+"-"+ctx["group"]
    info=dict(id=987,tag_name=tag,target_commitish=ctx["source"],prerelease=True,draft=False,assets=[])
    ref=dict(ref="refs/tags/"+tag,object=dict(type="commit",sha=ctx["source"]))
    reserved=dict(tag=tag,tested_source=ctx["source"],release_id=987,target_verified=True,
      assets_overwritten=False,externally_reserved=True,creation_attempted=False,existing_assets=[])
    good("fresh exact source reservation",lambda:r.reservation(ctx,reserved,info,ref))
    report=dict(status="PASS_CURRENT_RC_CONTACT_SOURCE_CONTROLS",passed=True,counts=r.SOURCE_COUNTS,
      current_context=dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False),
      native_executed=False,physical_acceptance=False)
    report_raw=r.encode(report)
    good("exact current source report binding",lambda:r.controls_binding(report_raw,ctx))
    original=(r.ROOT/"scripts/cloud_cdr_width_nominal_contacts.py").read_text()
    current=Path(r.__file__).read_text()
    def body(text,name):
        n=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name==name)
        return "".join(text.splitlines(True)[n.lineno-1:n.end_lineno])
    names=['require', 'encode', 'decode', 'fingerprint', 'regular', 'checked_path', 'api', 'release_binding', 'reservation', 'download', 'digest', 'file_pin', 'select_archive', 'write_new']
    def derivation():
        assert all(body(original,n)==body(current,n)for n in names)
        assert body(original,"acquire").replace("def acquire(","def acquire_parts(",1)==body(current,"acquire_parts")
        assert body(original,"emit").replace("CDR_CONTACT_","CDR_RC_CONTACT_")==body(current,"emit")
        native=(r.ROOT/'docs/evidence/cdr-v59-tail-fresh-RC-qualified-raw-parser-20261027.py').read_text()
        assert body(native,"number").replace("def number(text):","def native_number(text):",1)==body(current,"native_number")
        return dict(unchanged_helpers=names,native_number_renamed_only=True)
    good("actual frozen selector and transport derivation",derivation)
    good("exact decimal SPICE scaling",lambda:check_numbers())
    good("authentic component and raw parser protocol",lambda:check_actual_protocol(d))
    good("quoted slash native/export identity",lambda:check_native_names())
    for token in (".","1..2","1x2","1e","1e+","ddd","d.d","NaN","Inf","1kk","0x10","1 2"):
        bad("malformed decimal "+token,lambda token=token:r.number(token),"unsupported numeric literal")
    for token in (".5","1meg"):
        bad("original native numeric grammar "+token,lambda token=token:r.native_number(token),"Unsupported native number")
    for key,val in [("GITHUB_ACTIONS","false"),("GITHUB_EVENT_NAME","push"),("GITHUB_REPOSITORY","wrong/repo"),
      ("GITHUB_REF","refs/heads/main"),("GITHUB_RUN_ATTEMPT","2"),("GITHUB_RUN_ID","0"),("GITHUB_SHA","f"*39)]:
        bad("context "+key,lambda key=key,val=val:r.context(dict(env,**{key:val})))
    for key,val in [("tested_source","b"*40),("release_id",988),("target_verified",False),
      ("assets_overwritten",True),("externally_reserved",False),("creation_attempted",True),("existing_assets",["x"])]:
        bad("reservation "+key,lambda key=key,val=val:r.reservation(ctx,dict(reserved,**{key:val}),info,ref))
    bad("occupied release",lambda:r.reservation(ctx,reserved,dict(info,assets=[dict(id=1,name="x")]),ref))
    for name,which,change in [
      ("source","run",lambda x:x.update(head_sha="b"*40)),("run ID","run",lambda x:x.update(id=1)),
      ("job conclusion","jobs",lambda x:x["jobs"][1].update(conclusion="failure")),
      ("step","jobs",lambda x:x["jobs"][1]["steps"][0].update(conclusion="skipped")),
      ("asset digest","release",lambda x:x["assets"][0].update(digest="sha256:"+"0"*64)),
      ("missing asset","release",lambda x:x["assets"].pop()),
      ("old tag source","ref",lambda x:x["object"].update(sha="b"*40))]:
        args={k:d[k]for k in ("run","jobs","release","ref")};args[which]=mutated(args[which],change)
        bad("live "+name,lambda args=args:r.validate_live(c,*[args[k]for k in ("run","jobs","release","ref")]))
    with tempfile.TemporaryDirectory()as name:
        root=Path(name)
        for path in [r.CONFIG,*c["required_files"]]:
            p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(r.regular(r.ROOT,path).read_bytes())
        p=root/"scripts/cloud_cdr_width_nominal_contacts.py";old=p.read_bytes();p.write_bytes(old+b"\n")
        bad("protected helper changed",lambda:r.source_guard(root),"source/input bytes");p.write_bytes(old)
        p.unlink();bad("protected helper missing",lambda:r.source_guard(root),"missing regular file");p.write_bytes(old)
        (root/r.CONFIG).write_bytes(b"{}");bad("input contract corrupted",lambda:r.source_guard(root),"input contract bytes")
    for name,key,change in [
      ("raw substituted with summary","raw",lambda x:x.update(outputs=d["summary"]["outputs"])),
      ("missing native member","full",lambda x:x.pop(next(iter(x)))),
      ("old graph source","summary",lambda x:x.update(original_graph_source="b"*40)),
      ("electrical accepted","summary",lambda x:x.update(electrical_accepted=True))]:
        docs=copy.deepcopy(d);change(docs[key])
        with patch.object(r,"pinned",side_effect=lambda _c,_root,k,docs=docs:docs[k]):
            bad("metadata "+name,lambda:r.metadata(c))
    old_selected=copy.deepcopy(c)
    old_name="mim/precise/wire/anchors08.json"
    stale="restore/graph-input/physical-input/saved-input/current-mim-bundle/mim/precise/wire/anchors08.json"
    del old_selected["selected"][old_name]
    old_selected["selected"][stale]=d["full"][stale]
    bad("historical same-suffix anchor path",lambda:r.metadata(old_selected),"exact selected full paths")
    for name,change in [
      ("status",lambda x:x.update(status="PASS_OTHER")),
      ("source",lambda x:x["current_context"].update(source="b"*40)),
      ("counts",lambda x:x.update(counts={})),
      ("native",lambda x:x.update(native_executed=True))]:
        bad("controls "+name,lambda change=change:r.controls_binding(r.encode(mutated(report,change)),ctx))
    for name,text in [
      ("duplicate","R1 a b 1\nR1 a b 2"),("nonfinite","R1 a b NaN"),("negative","R1 a b -1"),
      ("unsupported include",".include other"),("duplicate port","R1 a b 1"),("orphan","R1 a b 1")]:
        text=("+ a b\n"if name=="orphan"else"")+".subckt x a "+("a"if name=="duplicate port"else"b")+"\n"+text+"\n.ends x\n"
        bad("SPICE "+name,lambda text=text:r.statements(text))
    sc,sd,files=synthetic()
    def materialize(root,values):
        for n,b in values.items():p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    with tempfile.TemporaryDirectory()as td:
        saved=Path(td)/"selected";saved.mkdir();materialize(saved,files)
        result=good("actual analyzer with synthetic complete graph/model",lambda:r.analyze(saved,sc,sd))
        assert set(result["targets"])=={"28","124"}and result["loaded_model_R_C_tokens_exact"]is True
        assert all(t["geometric_bridge_edge_assignment_proven"]is False for t in result["targets"].values())
        for name,path,mutator in [
          ("projection missing R","mim/composition/verified-wire-projection.spice",lambda b:b.replace(b"R0 T061_E n17 1\n",b"",1)),
          ("projection changed R","mim/composition/verified-wire-projection.spice",lambda b:b.replace(b"R0 T061_E n17 1",b"R0 T061_E n17 2",1)),
          ("loaded wire node","mim/composition/pd500-mim-wire.spice",lambda b:b.replace(b"R0 w_T061_E w_n17 1",b"R0 w_T061_E w_n61 1",1)),
          ("current cluster","mim/precise/wire/anchors08.json",lambda b:r.encode(mutated(r.decode(b),lambda x:x["anchors"][0].update(native_cluster=124)))),
          ("loaded device parameter","mim/composition/pd500-mim-wire.spice",lambda b:b.replace(b"p=1",b"p=2",1)),
          ("private technology","mim/precise/ngspice-mim-tech/ihp-sg13g2-extract.tech",lambda b:b+b"\n"),
          ("native resistor","mim/precise/wire/rc03/pump_wires.res.ext",lambda b:b.replace(b"resist T061_E n17 1",b"resist T061_E n17 2",1)),
          ("source scale","mim/precise/wire/rc03/pump_wires.ext",lambda b:b.replace(b"scale 1000 1 0.5",b"scale 1 1 0.5",1)),
          ("replacement scale","mim/precise/wire/rc03/pump_wires.res.ext",lambda b:b.replace(b"scale 1000 1 0.5",b"scale 1 1 0.5",1)),
          ("native endpoint renamed","mim/precise/wire/rc03/pump_wires.res.ext",lambda b:b.replace(b"resist T061_E n17 1",b"resist T061_E renamed/n17 1",1)),
          ("native unknown rnode","mim/precise/wire/rc03/pump_wires.res.ext",lambda b:b+b'rnode "unknown/native" 0 0 1 2 metal7\n'),
          ("extra MIM","mim/precise/wire/rc03/wires.spice",lambda b:b.replace(b".ends",b"X99 T061_E T115_E cap_cmim l=1u w=1u\n.ends",1)),
          ("anchor alias","mim/precise/wire/anchors08.json",lambda b:r.encode(mutated(r.decode(b),lambda x:x["logical_anchor_aliases"].update(T061_E="T062_E"))))]:
            old=files[path];changed=mutator(old);assert changed!=old,name
            (saved/path).write_bytes(changed);bad("actual analyzer "+name,lambda:r.analyze(saved,sc,sd));(saved/path).write_bytes(old)
    good("unproved absent technology coefficients",lambda:check_absent_tech())
    tiny={"a.txt":b"hello","empty":b""};expected={n:r.fingerprint(b)["sha256"]for n,b in tiny.items()}
    packed=archive_bytes(tiny);directory="cloud-cdr-selector-width-fresh-rc"
    with tempfile.TemporaryDirectory()as td:
        root=Path(td);a=root/"a.tar.gz";a.write_bytes(packed)
        good("actual selector complete synthetic archive",lambda:r.select_archive(a,expected,list(tiny),directory,root/"ok"))
        variants=[]
        for name,path,kind in [("traversal",directory+"/../escape",None),("absolute","/escape",None),
          ("unexpected",directory+"/extra",None),("duplicate",directory+"/a.txt",None),
          ("link",directory+"/link",tarfile.SYMTYPE),("unexpected directory",directory+"/extra/",tarfile.DIRTYPE),
          ("wrong root","wrong/a.txt",None)]:
            entry=tarfile.TarInfo(path);entry.size=0
            if kind:entry.type=kind;entry.linkname="a.txt"if kind==tarfile.SYMTYPE else""
            variants.append((name,archive_bytes(tiny,extra=(entry,b""if not kind else None))))
        variants.append(("missing",archive_bytes(tiny,omit="a.txt")))
        for i,(name,blob)in enumerate(variants):
            a.write_bytes(blob);bad("archive "+name,lambda i=i:r.select_archive(a,expected,list(tiny),directory,root/("bad"+str(i))))
        a.write_bytes(packed)
        bad("archive member hash",lambda:r.select_archive(a,dict(expected,**{"a.txt":"0"*64}),list(tiny),directory,root/"hash"))
        bad("archive selected not declared",lambda:r.select_archive(a,expected,["absent"],directory,root/"select"))
        partname="part0000";pin=dict(id=88,**r.fingerprint(packed));parts=dict(bytes=len(packed),sha256=pin["sha256"],parts=[dict(index=0,name=partname,bytes=pin["bytes"],sha256=pin["sha256"])])
        tc=dict(assets={partname:pin})
        def fetch(pin,path):path.write_bytes(packed)
        (root/"transport").mkdir()
        good("actual ordered synthetic transport",lambda:r.acquire(tc,parts,root/"transport",fetch))
        for name,part,fetcher in [
          ("bad part",parts,lambda pin,path:path.write_bytes(packed+b"x")),
          ("combined hash",dict(parts,sha256="0"*64),fetch)]:
            target=root/name;target.mkdir();bad("transport "+name,lambda target=target,part=part,fetcher=fetcher:r.acquire(tc,part,target,fetcher))
        bad("transport overwrite",lambda:r.acquire(tc,parts,root/"transport",fetch))
        out=root/"emit";out.mkdir();(out/"empty").write_bytes(b"");(out/"proof.json").write_bytes(r.encode(dict(a=1)))
        good("complete empty and nonempty emission",lambda:check_emission(out))
    def fake_api(endpoint):
        table={"releases/tags/"+tag:info,"git/ref/tags/"+tag:ref,
          "actions/runs/"+str(c["producer"]["id"]):d["run"],
          "actions/runs/"+str(c["producer"]["id"])+"/attempts/1/jobs?per_page=100":d["jobs"],
          "releases/"+str(c["release_id"]):d["release"],"git/ref/tags/"+c["tag"]:d["ref"]}
        return table[endpoint]
    # Only archive transport/metadata I/O is synthetic; production reservation/live/source gates,
    # complete selector, analyzer, cleanup and run/failure paths execute.
    synthetic_archive=archive_bytes(files)
    sd["parts"]=dict(d["parts"]);sd["parts"]["bytes"]=len(synthetic_archive)
    def fake_acquire(_c,_parts,work,fetch):
        path=work/"fixture.tar.gz";path.write_bytes(synthetic_archive)
        return path,dict(synthetic=True,**r.fingerprint(synthetic_archive))
    with tempfile.TemporaryDirectory()as td:
        out=Path(td)/"perform";out.mkdir()
        with patch.object(r,"metadata",return_value=sd),patch.object(r,"acquire",side_effect=fake_acquire):
            value=r.perform(ctx,reserved,report_raw,out,sc,api_call=fake_api,fetch=no_network)
        assert value["complete_input_members"]==len(files)and value["accepted"]is False
        lifecycle.append("actual perform with explicit synthetic transport, actual live/reservation/selector/analyzer")
    original_tmp=r.tempfile.TemporaryDirectory
    class BadCleanup:
        def __init__(self,*a,**kw):self.t=original_tmp(*a,**kw);self.name=self.t.name
        def cleanup(self):self.t.cleanup();raise RuntimeError("synthetic cleanup failure")
    with original_tmp()as td:
        out=Path(td)/"cleanup";out.mkdir()
        with patch.object(r,"metadata",return_value=sd),patch.object(r,"acquire",side_effect=OSError("primary transport")),patch.object(r.tempfile,"TemporaryDirectory",BadCleanup):
            try:r.perform(ctx,reserved,report_raw,out,sc,api_call=fake_api)
            except OSError as exc:assert str(exc)=="primary transport"
            else:raise AssertionError("primary transport lost")
        assert r.decode((out/"cleanup-error.json").read_bytes())["primary_error"]=="OSError('primary transport')"
        lifecycle.append("actual perform cleanup cannot replace primary transport")
    with tempfile.TemporaryDirectory()as td:
        out=Path(td)/"source"
        with patch.object(r,"source_guard",side_effect=ValueError("source integrity")),patch.object(r,"emit",side_effect=RuntimeError("emit")):
            try:r.run(ctx,reserved,report_raw,out)
            except ValueError as exc:assert str(exc)=="source integrity"
            else:raise AssertionError("source failure lost")
        assert (out/"readback-failure.json").exists()and not(out/"readback-result.json").exists()
        lifecycle.append("actual run source refusal and emit error preserve primary")
    with tempfile.TemporaryDirectory()as td:
        out=Path(td)/"save";real=r.write_new
        def failing(path,raw):
            if path.name=="readback-result.json":raise OSError("result save")
            real(path,raw)
        with patch.object(r,"perform",return_value=dict(status="synthetic")),patch.object(r,"write_new",side_effect=failing),patch.object(r,"emit",return_value={}):
            try:r.run(ctx,reserved,report_raw,out)
            except OSError as exc:assert str(exc)=="result save"
            else:raise AssertionError("save failure lost")
        assert r.decode((out/"readback-failure.json").read_bytes())["error"]["message"]=="result save"
        lifecycle.append("actual run result write failure preserved")
        try:r.run(ctx,reserved,report_raw,out)
        except AssertionError as exc:assert "output no overwrite"in str(exc)
        else:raise AssertionError("existing output overwritten")
        lifecycle.append("actual run no overwrite")
    result=dict(status="PASS_CURRENT_RC_CONTACT_SOURCE_CONTROLS",passed=True,
      positive=positive,refusal=refusal,lifecycle=lifecycle,
      counts=dict(positive=len(positive),refusal=len(refusal),lifecycle=len(lifecycle)),
      native_executed=False,physical_acceptance=False,
      synthetic_native_formats_and_archives=True,actual_source_metadata_authenticated=True,
      actual_native_archive_extracted=False,actual_RC_readback_qualified=False)
    assert result["counts"]==r.SOURCE_COUNTS,result["counts"]
    return result

def check_numbers():
    cases={"0":"0","17":"17","-3":"-3","+12.5":"12.5",".125":".125","1.":"1","-.5":"-.5",
      "1.25e-3":".00125","2E+3":"2000",".5e2":"50","1k":"1000","1M":".001","1meg":"1000000",
      "2t":"2e12","3g":"3e9","4u":"4e-6","5n":"5e-9","6p":"6e-12","7f":"7e-15","-2.5e+2m":"-.25"}
    assert all(r.number(token)==r.Decimal(value)for token,value in cases.items())
    return dict(accepted_literals=len(cases))


def check_actual_protocol(d):
    for name in ("precise_audit","wire_audit"):
        rows=d[name]["audit"]["components"]
        assert len(rows)==113 and all(set(row)=={"component","nodes","probes"}for row in rows)
        assert [(row["component"],row["nodes"],len(row["probes"]))for row in sorted(rows,key=lambda x:x["component"])if row["component"]in(17,61)]==[(17,102,8),(61,102,8)]
    pins=d["precise_audit"]["audit"]["inputs"]
    raw=[v for k,v in pins.items()if k.endswith("/audit_pilot.py")]
    assert raw==[dict(bytes=8291,sha256="f8132c8498cd32c4e27e6a8c054a7b35a72129bbf15ab8cc1ee9d6d65610e667")]
    return dict(full_components=113,target_nodes=[102,102],target_probes=[8,8])


def check_native_names():
    projection=r.statements(".subckt x contact/A contact/B\nR1 contact/A internal/path.n1 1.25e-3\nR2 internal/path.n1 contact/B 2k\n.ends x\n")
    original=r.native_rows('scale 1000 1 0.5\nstyle "ngspice()"\n')
    replacement=r.native_rows('scale 1000 1 0.5\nresist "contact/A" "internal/path.n1" 0.00125\nresist "internal/path.n1" "contact/B" 2000\nrnode "internal/path.n1" 0 1 1 2 metal7\n')
    result=r.native_export_identity(original,replacement,projection,{"contact/A":17,"contact/B":17,"internal/path.n1":17})
    assert result["resistor_records"]==2 and result["rnode_records"]==1 and result["generic_Magic_units_inferred"]is False
    return result
def check_absent_tech():
    result=r.technology("# no coefficient supplied\n")
    assert result["numeric_directives"]==[]and result["absent_coefficients_remain_unproved"]is True
    return result

def check_emission(out):
    lines=[];index=r.emit(out,writer=lambda text,**kw:lines.append(text))
    chunks=collections.defaultdict(list);ends={}
    for line in lines:
        marker,raw=line.split(" ",1);obj=r.decode(raw)
        if marker=="CDR_RC_CONTACT_CHUNK":chunks[obj["name"]].append(obj)
        elif marker=="CDR_RC_CONTACT_END":ends[obj["name"]]=obj
    assert set(index)==set(ends)
    for name,pin in index.items():
        xs=chunks[name];assert [x["index"]for x in xs]==list(range(len(xs)))
        raw=zlib.decompress(b"".join(base64.b64decode(x["data"])for x in xs))
        assert r.fingerprint(raw)==pin and raw==(out/name).read_bytes()
    return index

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);args=p.parse_args()
    ctx=r.context(os.environ);result=None
    try:
        result=controls()
        result["current_context"]=dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False)
    except BaseException as exc:
        result=dict(status="FAIL_CURRENT_RC_CONTACT_SOURCE_CONTROLS",passed=False,error=repr(exc),traceback=traceback.format_exc(),
          native_executed=False,physical_acceptance=False,current_context=dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False))
        raise
    finally:
        if result is not None:
            raw=r.encode(result);args.output.parent.mkdir(parents=True,exist_ok=True)
            try:r.write_new(args.output,raw)
            finally:print(raw.decode(),end="",flush=True)
if __name__=="__main__":main()
