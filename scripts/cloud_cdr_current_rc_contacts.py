#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Runner-only authenticated current RC/text readback; no CAD or electrical acceptance."""
import argparse,base64,collections,copy,hashlib,json,math,os,re,shlex,shutil
import subprocess,sys,tarfile,tempfile,traceback,zlib
from decimal import Decimal,InvalidOperation
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
REPOSITORY="Melihakbulut221/nssoc"
BRANCH="codex/cdr-current-rc-contact-readback"
GROUP="cdr-current-rc-contact-readback"
CONFIG="scripts/cdr-current-rc-contact-inputs.json"
CONFIG_SHA="8f67918556ffea7b8bf9914c770268a1dcc56e2accedb791dfb40f4f2ade2715"
FLAGS=dict(accepted=False,physical_acceptance=False,electrical_acceptance=False,
 full_phy_accepted=False,causality_proven=False,dominant_path_proven=False,
 new_simulation=False,geometry_changed=False,native_CAD_executed=False)
SOURCE_COUNTS=dict(positive=14,refusal=80,lifecycle=5)
SELECTED=('mim/composition/pd500-mim-wire.spice', 'mim/composition/verified-wire-projection.spice', 'mim/composition/composition.json', 'mim/precise/wire/anchors08.json', 'mim/precise/wire/rc03/pump_wires.ext', 'mim/precise/wire/rc03/pump_wires.res.ext', 'mim/precise/wire/rc03/wires.spice', 'mim/precise/ngspice-mim-tech/ihp-sg13g2-extract.tech', 'mim/precise/ngspice-mim-tech/ihp-sg13g2-via.tcl', 'mim/precise/ngspice-mim-tech/ihp-sg13g2-res.tcl', 'canonical-current-view/magic-cloud/tech/ihp-sg13g2-extract.tech', 'canonical-current-view/wire/anchors08.json', 'canonical-current-view/wire/rc03/wires.spice', 'canonical-current-view/wire/rc03/pump_wires.ext', 'canonical-current-view/wire/rc03/pump_wires.res.ext')
def require(ok,message):
    if not ok:raise AssertionError(message)


def encode(obj):
    return (json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()


def decode(raw):
    def pairs(items):
        d={}
        for k,v in items:
            require(k not in d,"duplicate JSON key");d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=pairs,
      parse_constant=lambda x:(_ for _ in ()).throw(ValueError("nonfinite JSON")))


def fingerprint(raw):
    return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def regular(root,name):
    checked_path(name);p=Path(root)/name
    for q in (p,*p.parents):
        require(not q.is_symlink(),"path symlink: "+name)
        if q==Path(root):break
    require(p.is_file(),"missing regular file: "+name)
    return p


def checked_path(name):
    require(isinstance(name,str)and name and "\\"not in name and "\x00"not in name,
            "unsafe archive path")
    p=PurePosixPath(name)
    require(not p.is_absolute()and str(p)==name and all(v not in ("",".","..")for v in p.parts),
            "unsafe archive path")
    return p


def api(endpoint):
    return decode(subprocess.check_output(["gh","api","repos/"+REPOSITORY+"/"+endpoint]))


def release_binding(info,ref,tag,source):
    require(type(info.get("id"))is int and info["id"]>0 and info.get("tag_name")==tag,
            "release identity")
    require(info.get("target_commitish")==source and info.get("prerelease")is True and
      info.get("draft")is False,"release target")
    require(ref.get("ref")=="refs/tags/"+tag and ref.get("object",{}).get("type")=="commit"and
      ref["object"].get("sha")==source,"release tag target")
    assets=info.get("assets",[])
    require(isinstance(assets,list)and len({a["id"]for a in assets})==len(assets)and
      len({a["name"]for a in assets})==len(assets),"release asset duplicates")
    return {a["name"]:a for a in assets}


def reservation(ctx,proof,info,ref):
    tag="cloud-results-"+ctx["token"]+"-"+ctx["group"]
    assets=release_binding(info,ref,tag,ctx["source"])
    require(proof.get("tag")==tag and proof.get("tested_source")==ctx["source"]and
      proof.get("release_id")==info["id"],"reservation identity")
    require(proof.get("target_verified")is True and proof.get("assets_overwritten")is False and
      proof.get("externally_reserved")is True and proof.get("creation_attempted")is False,
      "externally verified reservation")
    require(proof.get("existing_assets")==[]and assets=={},"fresh reservation required")
    return dict(release_id=info["id"],tag=tag,source=ctx["source"],
      verified_before_archive_acquisition=True,assets_overwritten=False)


def download(pin,path):
    require(not path.exists()and not path.is_symlink(),"download no overwrite")
    with path.open("xb")as f:
        subprocess.run(["gh","api","-H","Accept: application/octet-stream",
          "repos/"+REPOSITORY+"/releases/assets/"+str(pin["id"])],
          stdout=f,check=True,timeout=1800)
    require(file_pin(path)=={k:pin[k]for k in ("bytes","sha256")},"download fingerprint")


def digest(path):
    with Path(path).open("rb")as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()


def file_pin(path):
    require(path.is_file()and not path.is_symlink(),"regular downloaded file")
    return dict(bytes=path.stat().st_size,sha256=digest(path))


def select_archive(archive,expected,selected,directory,out):
    """Verify EVERY member; retain only exact wave and derived input JSON on runner."""
    require(set(selected)<=set(expected),"selected map")
    require(not out.exists()and not out.is_symlink(),"selected output new")
    out.mkdir()
    directories={str(p)for name in expected for p in PurePosixPath(name).parents if str(p)!="."}
    seen=set();observed={};total=0
    with tarfile.open(archive,"r|gz")as tar:
        for member in tar:
            raw=member.name
            if member.isdir()and raw.endswith("/"):raw=raw[:-1]
            checked_path(raw)
            if raw==directory:
                require(member.isdir()and raw not in seen,"archive root type/duplicate")
                seen.add(raw);continue
            require(raw.startswith(directory+"/"),"archive root namespace")
            name=raw[len(directory)+1:];checked_path(name)
            require(raw not in seen,"duplicate archive member");seen.add(raw)
            if member.isdir():
                require(name in directories,"unexpected archive directory");continue
            require(member.isfile()and not member.issparse(),"archive link/special/sparse")
            require(name in expected,"unexpected archive member")
            require(0<=member.size<=8*1024**3,"member size bound")
            total+=member.size;require(total<=16*1024**3,"archive expansion bound")
            h=hashlib.sha256();size=0;target=None
            if name in selected:
                p=out/name;p.parent.mkdir(parents=True,exist_ok=True);target=p.open("xb")
            try:
                stream=tar.extractfile(member);require(stream is not None,"archive stream")
                with stream:
                    while block:=stream.read(1024*1024):
                        size+=len(block);h.update(block)
                        if target is not None:target.write(block)
                require(size==member.size and h.hexdigest()==expected[name],"member fingerprint: "+name)
            finally:
                if target is not None:target.close()
            observed[name]=dict(bytes=size,sha256=h.hexdigest())
    require(set(observed)==set(expected),"incomplete full archive map")
    require(all(regular(out,n).is_file()for n in selected),"selected missing")
    return dict(full_members=observed,full_member_count=len(observed),uncompressed_bytes=total,
      every_member_authenticated=True,selected={n:observed[n]for n in selected},
      extraction_only_on_runner=True,source_archives_modified=False)


def write_new(path,raw):
    with path.open("xb")as out:out.write(raw)



def context(env):
    require(env.get("GITHUB_ACTIONS")=="true","hosted only")
    require(env.get("GITHUB_EVENT_NAME")=="workflow_dispatch","manual only")
    require(env.get("GITHUB_REPOSITORY")==REPOSITORY,"repository")
    require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH,"readback branch")
    require(env.get("GITHUB_RUN_ATTEMPT")=="1","attempt one only")
    run=env.get("GITHUB_RUN_ID","");source=env.get("GITHUB_SHA","")
    require(re.fullmatch(r"[1-9][0-9]*",run)is not None,"run ID")
    require(re.fullmatch(r"[0-9a-f]{40}",source)is not None,"immutable source")
    return dict(source=source,run_id=int(run),attempt=1,group=GROUP,token=run+"-1")

def source_guard(root=ROOT):
    raw=regular(root,CONFIG).read_bytes()
    require(fingerprint(raw)["sha256"]==CONFIG_SHA,"input contract bytes")
    c=decode(raw)
    require(c["schema"]=="current-rc-contact-readback-inputs-v1" and
      c["branch"]==BRANCH and c["all_acceptance_false"]is True and
      c["native_CAD_authorized"]is False,"contract scope")
    for p,pin in c["required_files"].items():
        require(fingerprint(regular(root,p).read_bytes())==pin,"source/input bytes: "+p)
    return c

def pinned(c,root,key):
    p=c["paths"][key];raw=regular(root,p).read_bytes()
    require(fingerprint(raw)==c["required_files"][p],"pinned report: "+key)
    return decode(raw)

def validate_live(c,run,jobs,info,ref):
    p=c["producer"]
    require(all(run.get(k)==v for k,v in p.items())and run.get("status")=="completed"
      and run.get("conclusion")=="success","producer terminal identity")
    rows=jobs.get("jobs",[])
    require(jobs.get("total_count")==len(rows)==len(c["jobs"]) and
      len({j["id"]for j in rows})==len(rows),"complete producer jobs")
    found={j["id"]:j for j in rows}
    for expected in c["jobs"]:
        j=found.get(expected["id"],{})
        require(all(j.get(k)==v for k,v in expected.items()if k!="steps"),"producer job identity")
        require([{k:s[k]for k in ("number","name","status","conclusion")}for s in j["steps"]]
          ==expected["steps"],"producer job steps")
    assets=release_binding(info,ref,c["tag"],p["head_sha"])
    require(info["id"]==c["release_id"]and set(assets)==set(c["assets"]),"producer assets")
    for name,pin in c["assets"].items():
        a=assets[name]
        require(a.get("id")==pin["id"]and a.get("size")==pin["bytes"]and
          a.get("digest")=="sha256:"+pin["sha256"]and a.get("state")=="uploaded","producer asset: "+name)
    return dict(source=p["head_sha"],run_id=p["id"],attempt=1,release_id=info["id"],
      successful_RC_production_only=True,electrical_acceptance=False)

def metadata(c,root=ROOT):
    d={k:pinned(c,root,k) for k in c["paths"]}
    receipt=d["receipt"]
    require(receipt["run"]==40830441311 and receipt["source"]==c["producer"]["head_sha"]
      and receipt["terminal"]=="success","original terminal receipt")
    for p,pin in c["required_files"].items():
        if p.startswith("docs/evidence/cdr-selector-width-fresh-rc-native-terminal-20261029/")and p!=c["paths"]["receipt"]:
            require(receipt["files"].get(p)==pin,"original receipt report join")
    full=d["full"];s=d["summary"];raw=d["raw"]
    require(len(full)==c["full_count"]==6647 and len(s["outputs"])==6646 and len(raw["outputs"])==6645,"complete member census")
    require(full==dict(s["outputs"],**{"result.json":c["required_files"][c["paths"]["raw"]]["sha256"]}),"raw/summary substitution")
    require(s["outputs"]==dict(raw["outputs"],**{"publication-driver.log":"704f93a52832b1db4821218ee91e0d70a1c872ca4ad9f433f39db82e274b106f"}),"publication-only inventory delta")
    require({k:v for k,v in s.items()if k!="outputs"}=={k:v for k,v in raw.items()if k!="outputs"},"raw/summary semantics")
    require(s["status"]=="PASS_FRESH_WIDTH500_BINDING_WIRE_RC_SEVEN_MIM_TWO_ORDERS_REQUIRES_ORIGINAL_ELECTRICAL_MATRIX"
      and s["run_id"]==40830441311 and s["run_attempt"]==1 and s["source_head"]==c["producer"]["head_sha"],"current RC identity")
    require((s["complete_graph_members"],s["current_members"],s["original_graph_run"],s["original_width_run"])
      ==(4103,75,40808550817,40815684037),"current width/graph lineage")
    require(s["original_graph_source"]=="97705f184239c0c522582b9d8e82c542bd902b65"and
      s["original_width_source"]=="214ec651fd501de7e2f49a38509b184a1fd66f8d","current producer sources")
    require(all(s[k]is False for k in ("simulation_executed","physical_accepted","electrical_accepted","qualified_pex","full_phy_accepted")),"producer scope")
    require(all(x["returncode"]==0 and x["supervision_failure"]is None and not x["process_group_cleanup"]["remaining_live"]for x in s["commands"])and len(s["commands"])==4,"four actual phases")
    require(all(x["completed"]is True for x in s["terminal_actions"])and not s.get("terminal_errors"),"producer finalization")
    for n,h in full.items():
        checked_path(n);require(re.fullmatch(r"[0-9a-f]{64}",h)is not None,"member digest")
    require(set(c["selected"])==set(SELECTED)and set(c["selected"])<=set(full)and all(full[n]==h for n,h in c["selected"].items()),"exact selected full paths")
    parts=d["parts"]
    require(parts["format"]=="ordered-tar-gzip-parts-v1"and
      parts["source_directory"]=="cloud-cdr-selector-width-fresh-rc"and
      parts["stem"]=="cdr-selector-width-fresh-rc-40830441311-1","archive namespace")
    require([x["index"]for x in parts["parts"]]==[0,1]and sum(x["bytes"]for x in parts["parts"])==parts["bytes"],"ordered complete parts")
    require(parts["verification"]==dict(parts=2,bytes=parts["bytes"],sha256=parts["sha256"],all_parts_and_combined_bytes_verified=True),"part verification")
    for row in parts["parts"]:
        pin=c["assets"][row["name"]]
        require(all(row[k]==pin[k]for k in ("bytes","sha256")),"part asset join")
    require(d["composition"]["counts"]==dict(devices=500,R=24356,C=15566),"current composition")
    for key,nr,nc in [("wire_audit",24341,15559),("precise_audit",24356,15566)]:
        a=d[key]["audit"]
        require(a["status"]=="PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY"and
          (a["actual_exported_resistors"],a["actual_exported_capacitors"],a["connected_wire_components"])==(nr,nc,113),"actual audit counts")
        require(a["native_export_r_edge_value_multiset_exact"]is True and
          a["point_attachment_or_rf_distribution_qualified"]is False and a["full_pex_qualified"]is False,"actual audit scope")
    validate_live(c,d["run"],d["jobs"],d["release"],d["ref"])
    return d

def acquire(c,parts,tmp,fetch=download):
    # Same ordered transport as qualified contact reader; current single producer namespace.
    shim=dict(cases={"rc":dict(assets=c["assets"])})
    return acquire_parts(shim,"rc",parts,tmp,fetch)
def acquire_parts(c,case,parts,tmp,fetch=download):
    e=c["cases"][case];archive=tmp/"source.tar.gz"
    require(not archive.exists(),"archive no overwrite")
    whole=hashlib.sha256();size=0;observed=[]
    with archive.open("xb")as out:
        for row in parts["parts"]:
            pin=e["assets"][row["name"]];p=tmp/row["name"]
            fetch(pin,p)
            require(file_pin(p)=={k:row[k]for k in ("bytes","sha256")},"part fingerprint")
            with p.open("rb")as f:
                while block:=f.read(1024*1024):
                    out.write(block);whole.update(block);size+=len(block)
            observed.append(dict(row,asset_id=pin["id"]));p.unlink()
    require(size==parts["bytes"]and whole.hexdigest()==parts["sha256"],"combined archive fingerprint")
    return archive,dict(parts=observed,bytes=size,sha256=whole.hexdigest())



def number(token):
    m=re.fullmatch('([+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][+-]?\\d+)?)(meg|[tgkmunpf])?',token,re.I)
    require(m is not None,"unsupported numeric literal: "+token)
    value=Decimal(m[1])*{"":Decimal(1),"t":Decimal("1e12"),"g":Decimal("1e9"),
      "meg":Decimal("1e6"),"k":Decimal("1e3"),"m":Decimal("1e-3"),"u":Decimal("1e-6"),
      "n":Decimal("1e-9"),"p":Decimal("1e-12"),"f":Decimal("1e-15")}[m[2].lower()if m[2]else""]
    require(value.is_finite(),"nonfinite number")
    return value

def native_number(text):
    match = re.fullmatch(r'([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)([numkpf]?)', text.lower())
    require(match is not None, 'Unsupported native number')
    value = Decimal(match[1]) * dict(n=Decimal('1e-9'), u=Decimal('1e-6'), m=Decimal('1e-3'),
                                    k=Decimal('1e3'), p=Decimal('1e-12'), f=Decimal('1e-15'), **{'': Decimal(1)})[match[2]]
    require(value.is_finite(), 'Nonfinite number')
    return value


def statements(text):
    rows=[]
    for line_no,line in enumerate(text.splitlines(),1):
        line=line.strip()
        if not line or line.startswith("*"):continue
        if line.startswith("+"):
            require(bool(rows),"orphan continuation");rows[-1]["tokens"].extend(line[1:].split());continue
        rows.append(dict(line=line_no,tokens=line.split()))
    require(len(rows)>2 and rows[0]["tokens"][0].lower()==".subckt"and rows[-1]["tokens"][0].lower()==".ends","single complete SPICE subcircuit")
    names=set();edges=[];devices=[]
    ports=rows[0]["tokens"][2:]
    require(len(ports)==len(set(x.lower()for x in ports)),"duplicate SPICE port")
    for row in rows[1:-1]:
        tokens=row["tokens"];name=tokens[0];key=name.lower()
        require(key not in names,"duplicate SPICE element");names.add(key)
        if name[0].upper()in ("R","C"):
            require(len(tokens)==4 and tokens[1]!=tokens[2],"R/C record shape")
            value=number(tokens[3]);require(value>0 if name[0].upper()=="R"else value>=0,"invalid R/C value")
            edges.append(dict(line=row["line"],name=name,kind=name[0].upper(),a=tokens[1],b=tokens[2],token=tokens[3],value=str(value)))
        else:
            require(name.startswith("X"),"unsupported SPICE statement")
            devices.append(row)
    return dict(ports=ports,edges=edges,devices=devices)

def native_rows(text):
    return [dict(line=i,raw=line,tokens=shlex.split(line))for i,line in enumerate(text.splitlines(),1)if line.strip()]

def native_export_identity(source_rows,replacement_rows,projection,owners):
    """Replay the pinned audit protocol; no generic Magic unit/name conversion."""
    for label,rows in (("source",source_rows),("replacement",replacement_rows)):
        require([r["tokens"][1:]for r in rows if r["tokens"][0]=="scale"]==[["1000","1","0.5"]],label+" extraction scale")
    require([r["tokens"][1:]for r in source_rows if r["tokens"][0]=="style"]==[["ngspice()"]],"source extraction style")
    rs=[r for r in replacement_rows if r["tokens"][0]=="resist"]
    require(all(len(r["tokens"])==4 for r in rs),"native resistor shape")
    nr=collections.Counter((tuple(sorted(r["tokens"][1:3])),native_number(r["tokens"][3]))for r in rs)
    rr=collections.Counter((tuple(sorted((e["a"],e["b"]))),Decimal(e["value"]))for e in projection["edges"]if e["kind"]=="R")
    require(nr==rr,"native/export exact resistor incidence")
    points=[r for r in replacement_rows if r["tokens"][0]=="rnode"]
    for row in points:
        tokens=row["tokens"];require(len(tokens)>=4 and tokens[1]in owners,"native rnode identity/value")
        legacy_r=Decimal(tokens[2]);cap_literal=Decimal(tokens[3])
        require(legacy_r.is_finite()and cap_literal.is_finite()and legacy_r==0 and cap_literal>=0,"native rnode identity/value")
    return dict(native_export_R_multiset_exact=True,source_and_replacement_scale=["1000","1","0.5"],
      source_style="ngspice()",native_number_source_sha256="f8132c8498cd32c4e27e6a8c054a7b35a72129bbf15ab8cc1ee9d6d65610e667",
      value_rule="Exact qualified Decimal token comparison; no additional scale multiplier.",
      endpoint_rule="shlex native quote removal then exact exported endpoint identity; no slash rewriting or aliases.",
      resistor_records=len(rs),rnode_records=len(points),generic_Magic_units_inferred=False)

def incidence(parsed,anchors,geometry,expected_counts):
    aa=anchors["anchors"];by={a["label"]:a for a in aa}
    require(len(by)==len(aa)==expected_counts["anchors"]and set(parsed["ports"])==set(by),"complete anchor ports")
    require(all(k==v for k,v in anchors["logical_anchor_aliases"].items()),"no implicit anchor aliases")
    comps={r["component"]:r for r in geometry["wire_components"]}
    require(len(comps)==expected_counts["components"],"component census")
    adjacency={n:set()for n in by}
    for a in aa:require(comps[a["wire_component"]]["native_cluster"]==a["native_cluster"],"anchor native component")
    counts=collections.Counter(x["kind"]for x in parsed["edges"])
    require(counts=={k:expected_counts[k]for k in ("R","C")},"complete exact R/C census")
    for e in parsed["edges"]:
        if e["kind"]=="R":
            adjacency.setdefault(e["a"],set()).add(e["b"]);adjacency.setdefault(e["b"],set()).add(e["a"])
    owners={};records=[]
    for seed in sorted(adjacency):
        if seed in owners:continue
        todo=[seed];visited=set()
        while todo:
            n=todo.pop()
            if n in visited:continue
            visited.add(n);todo.extend(adjacency[n]-visited)
        ids={by[n]["wire_component"]for n in visited if n in by}
        require(len(ids)==1,"unanchored or cross-conductor R component")
        owner=next(iter(ids));require(len(visited)>1,"isolated contact")
        owners.update({n:owner for n in visited})
        records.append(dict(component=owner,nodes=len(visited),probes=sorted(visited&set(by))))
    require(len(records)==len({r["component"]for r in records})==expected_counts["components"],"split or missing R conductor")
    owners["sub"]=0
    require(all(e["a"]in owners and e["b"]in owners for e in parsed["edges"]),"unknown capacitor endpoint")
    return owners,sorted(records,key=lambda x:x["component"]),by

def edge_multiset(edges):
    return collections.Counter((e["kind"],tuple(sorted((e["a"],e["b"]))),Decimal(e["value"]))for e in edges)

def technology(text):
    """Preserve literal numeric directives; do not invent a unit or physical-edge mapping."""
    lines=text.splitlines();records=[];section=None;aliases=[]
    for i,line in enumerate(lines,1):
        stripped=line.strip()
        if stripped=="extract":section="extract"
        if stripped=="end":section=None
        try:tokens=shlex.split(stripped,comments=True)if stripped else[];tokenization_complete=True
        except ValueError:tokens=stripped.split();tokenization_complete=False
        numeric=[]
        for pos,token in enumerate(tokens):
            try:value=number(token)
            except (AssertionError,InvalidOperation):continue
            numeric.append(dict(token_index=pos,literal=token,decimal=str(value)))
        if numeric and(section=="extract"or any(re.search(r"resist|contact|sheet|via|metal7|topmetal2|topvia2",t,re.I)for t in tokens)):
            records.append(dict(line=i,section=section,raw=line,tokens=tokens,numeric_literals=numeric,
              preceding_lines=lines[max(0,i-4):i-1],tokenization_complete=tokenization_complete,units_and_layer_meaning_inferred=False))
        if re.search(r"metal7|topmetal2|topvia2|via6",line,re.I):
            aliases.append(dict(line=i,raw=line,association="literal source mention only"))
    return dict(numeric_directives=records,TM2_or_upper_via_mentions=aliases,
      absent_coefficients_remain_unproved=True,technology_not_executed=True)

def analyze(saved,c,d):
    def raw(name):return regular(saved,name).read_bytes()
    def txt(name):return raw(name).decode("utf-8")
    base="mim/precise/wire/"
    anchors=decode(raw(base+"anchors08.json"));composition=decode(raw("mim/composition/composition.json"))
    require(composition==d["composition"],"archived actual composition")
    geometry=d["geometry"]
    projection=statements(txt("mim/composition/verified-wire-projection.spice"))
    require(not projection["devices"],"wire projection contains device")
    precise=statements(txt(base+"rc03/wires.spice"))
    require(precise["ports"]==projection["ports"]and [(e["name"],e["a"],e["b"],e["token"])for e in precise["edges"]]
      ==[(e["name"],e["a"],e["b"],e["token"])for e in projection["edges"]],"actual precise R/C projection")
    wanted=[x["export"]for x in d["precise_capture"]["intrinsic_capture_binding"]["native_mim_devices"]]
    require([x["tokens"]for x in precise["devices"]]==wanted,"seven original native MIM cards")
    owners,components,by=incidence(projection,anchors,geometry,c["counts"])
    require(components==sorted(d["precise_audit"]["audit"]["components"],key=lambda x:x["component"]),"actual component report replay")
    rows=native_rows(txt(base+"rc03/pump_wires.res.ext"))
    native_proof=native_export_identity(native_rows(txt(base+"rc03/pump_wires.ext")),rows,projection,owners)
    model=statements(txt("mim/composition/pd500-mim-wire.spice"));mapping=composition["wire_node_map"]
    require(len(model["devices"])==c["counts"]["devices"]and model["ports"]==composition["interface"],"actual loaded model interface/devices")
    require(len(set(v.lower()for v in mapping.values()))==len(mapping),"node mapping collision")
    require(set(mapping)=={n for e in projection["edges"]for n in (e["a"],e["b"])},"complete current node mapping")
    projected=[dict(e,a=mapping[e["a"]],b=mapping[e["b"]])for e in projection["edges"]]
    require([(e["name"],e["a"],e["b"],e["token"])for e in projected]==[(e["name"],e["a"],e["b"],e["token"])for e in model["edges"]],"exact loaded R/C mapping")
    devices={r["tokens"][0]:r["tokens"]for r in model["devices"]}
    require(set(devices)=={r["instance"]for r in composition["device_records"]},"complete loaded device IDs")
    for rec in composition["device_records"]:
        row=devices[rec["instance"]];n=len(rec["terminals"])
        require(row[1:n+1]==[t["node"]for t in rec["terminals"]]and row[n+1]==rec["model"]and
          dict(t.split("=",1)for t in row[n+2:])==rec["parameters"],"loaded device terminal/parameter binding")
    canonical=statements(txt("canonical-current-view/wire/rc03/wires.spice"))
    canonical_anchors=decode(raw("canonical-current-view/wire/anchors08.json"))
    oldcounts=dict(c["counts"],R=c["counts"]["canonical_R"],C=c["counts"]["canonical_C"])
    oldowners,oldcomponents,oldby=incidence(canonical,canonical_anchors,geometry,oldcounts)
    require(oldcomponents==sorted(d["wire_audit"]["audit"]["components"],key=lambda x:x["component"]),"canonical component replay")
    out={}
    for cluster,target in c["targets"].items():
        owner=target["component"];contacts=target["contacts"]
        require({a["label"]for a in by.values()if a["wire_component"]==owner}==set(contacts),"exact target contacts")
        selected=[]
        for label in contacts:
            a=by[label];require(a["native_cluster"]==int(cluster)and oldby[label]["point_dbu"]==a["point_dbu"]and
              oldby[label]["wire_component"]==owner,"current anchor identity")
            recs=[(r,t)for r in composition["device_records"]for t in r["terminals"]if t["anchor"]==label]
            require(len(recs)==1,"contact association ambiguity")
            rec,t=recs[0]
            require(t["native_cluster"]==int(cluster)and t["native_net"]==target["net"]and t["node"]==mapping[label],"current contact net mapping")
            selected.append(dict(anchor=a,device=rec["native_id"],terminal=t,loaded_node=mapping[label]))
        es=[dict(e,a_owner=owners[e["a"]],b_owner=owners[e["b"]],loaded_a=mapping[e["a"]],loaded_b=mapping[e["b"]])for e in projection["edges"]if owner in (owners[e["a"]],owners[e["b"]])]
        oldes=[e for e in canonical["edges"]if owner in (oldowners[e["a"]],oldowners[e["b"]])]
        nodes=sorted(n for n,v in owners.items()if v==owner)
        native=[r for r in rows if r["tokens"][0]in ("rnode","resist")and any(n in owners and owners[n]==owner for n in r["tokens"][1:3])]
        out[cluster]=dict(native_cluster=int(cluster),native_net=target["net"],component=owner,
          contacts=selected,nodes=[dict(native=n,loaded=mapping[n])for n in nodes],incidence=es,
          native_primitive_records=native,primitive_coordinates_interpreted=False,
          canonical_incidence=oldes,
          canonical_to_loaded_R_edge_value_multiset_equal=edge_multiset([e for e in es if e["kind"]=="R"])==edge_multiset([e for e in oldes if e["kind"]=="R"]),
          geometric_bridge_edge_assignment_proven=False,current_flow_or_effective_resistance_computed=False)
    original=txt("canonical-current-view/magic-cloud/tech/ihp-sg13g2-extract.tech")
    current=txt("mim/precise/ngspice-mim-tech/ihp-sg13g2-extract.tech")
    private=d["precise_capture"]["private_tech"];derived=original
    for line in private["removed_cdl_device_estimate_lines"]:
        require(derived.count(line)==1,"private tech exact removal");derived=derived.replace(line,"",1)
    require(derived==current and private["all_other_technology_bytes_unchanged"]is True,"precise technology derivation")
    tech={n:dict(pin=file_pin(regular(saved,n)),**technology(txt(n)))for n in c["selected"]if n.endswith((".tech","-via.tcl","-res.tcl"))}
    return dict(status="CURRENT_RC_CONTACT_INCIDENCE_READBACK_ONLY",targets=out,technology=tech,
      full_current_counts=dict(devices=len(devices),R=sum(e["kind"]=="R"for e in projection["edges"]),C=sum(e["kind"]=="C"for e in projection["edges"]),components=len(components),anchors=len(by)),
      native_export_R_multiset_exact=True,native_export_identity=native_proof,loaded_model_R_C_tokens_exact=True,complete_device_mapping_exact=True,
      private_MIM_technology_derivation=private,all_full_component_rows=components,
      missing=["dynamic branch currents","internal-node voltages at contact witness times","full dynamic KCL",
        "qualified per-edge physical bridge/via assignment","units not explicitly established by retained technology source"],
      source_interpretation="Literal coefficients and source lines; no generic process values, no ideal aliases, no geometry selection.",
      **FLAGS)

def controls_binding(raw,ctx):
    r=decode(raw)
    require(r.get("status")=="PASS_CURRENT_RC_CONTACT_SOURCE_CONTROLS"and r.get("passed")is True,"source controls status")
    require(r.get("current_context")==dict(source=ctx["source"],run_id=ctx["run_id"],attempt=1,source_controls_only=True,native_executed=False),"same-source controls")
    require(r.get("counts")==SOURCE_COUNTS and r.get("native_executed")is False and r.get("physical_acceptance")is False,"complete controls scope")
    return fingerprint(raw)

def perform(ctx,reserved,controls_raw,out,c,root=ROOT,api_call=api,fetch=download):
    control_pin=controls_binding(controls_raw,ctx);d=metadata(c,root)
    tag="cloud-results-"+ctx["token"]+"-"+ctx["group"]
    fresh=reservation(ctx,reserved,api_call("releases/tags/"+tag),api_call("git/ref/tags/"+tag))
    write_new(out/"reservation.json",encode(fresh));write_new(out/"source-controls.json",controls_raw)
    run=api_call("actions/runs/"+str(c["producer"]["id"]))
    jobs=api_call("actions/runs/"+str(c["producer"]["id"])+"/attempts/1/jobs?per_page=100")
    info=api_call("releases/"+str(c["release_id"]));ref=api_call("git/ref/tags/"+c["tag"])
    live=validate_live(c,run,jobs,info,ref)
    for name,obj in [("producer-run.json",run),("producer-jobs.json",jobs),("producer-release.json",info),("producer-ref.json",ref),("live-binding.json",live)]:
        write_new(out/name,encode(obj))
    require(shutil.disk_usage(out.parent).free>=d["parts"]["bytes"]+3*1024**3,"runner space before acquisition")
    primary=None;tmp=tempfile.TemporaryDirectory(prefix="cdr-current-rc-contact-",dir=out.parent)
    try:
        work=Path(tmp.name);archive,transport=acquire(c,d["parts"],work,fetch)
        write_new(out/"transport-proof.json",encode(transport))
        proof=select_archive(archive,d["full"],list(c["selected"]),d["parts"]["source_directory"],work/"selected")
        write_new(out/"complete-input-census.json",encode(proof))
        source_guard(root)
        result=analyze(work/"selected",c,d)
        write_new(out/"incidence-and-technology.json",encode(result))
        require(all(file_pin(regular(work/"selected",n))==proof["selected"][n]for n in c["selected"]),"selected source mutation")
        return dict(status="PASS_CURRENT_RC_CONTACT_READBACK_NOT_ACCEPTANCE",current_context=ctx,
          producer=live,reservation=fresh,current_controls=control_pin,complete_input_members=proof["full_member_count"],
          selected=proof["selected"],analysis=file_pin(out/"incidence-and-technology.json"),**FLAGS)
    except BaseException as exc:primary=exc;raise
    finally:
        try:tmp.cleanup()
        except BaseException as exc:
            try:write_new(out/"cleanup-error.json",encode(dict(error=repr(exc),primary_error=None if primary is None else repr(primary))))
            except BaseException:pass
            if primary is None:raise

def emit(out,writer=print):
    records={p.relative_to(out).as_posix():file_pin(p)for p in sorted(out.rglob("*"))if p.is_file()}
    writer("CDR_RC_CONTACT_INDEX "+json.dumps(records,sort_keys=True),flush=True)
    for name,pin in records.items():
        compressor=zlib.compressobj(level=6);pending=b"";index=0
        with regular(out,name).open("rb")as f:
            while block:=f.read(65536):
                pending+=compressor.compress(block)
                while len(pending)>=24576:
                    part,pending=pending[:24576],pending[24576:]
                    writer("CDR_RC_CONTACT_CHUNK "+json.dumps(dict(name=name,index=index,encoding="zlib+base64",
                      data=base64.b64encode(part).decode()),sort_keys=True),flush=True);index+=1
        pending+=compressor.flush()
        for pos in range(0,len(pending),24576):
            writer("CDR_RC_CONTACT_CHUNK "+json.dumps(dict(name=name,index=index,encoding="zlib+base64",
              data=base64.b64encode(pending[pos:pos+24576]).decode()),sort_keys=True),flush=True);index+=1
        writer("CDR_RC_CONTACT_END "+json.dumps(dict(name=name,chunks=index,**pin),sort_keys=True),flush=True)
    return records


def run(ctx,reserved,controls_raw,out,root=ROOT,api_call=api,fetch=download):
    require(not out.exists()and not out.is_symlink(),"output no overwrite")
    out.mkdir(parents=True);primary=None
    try:
        c=source_guard(root)
        result=perform(ctx,reserved,controls_raw,out,c,root,api_call,fetch)
        source_guard(root)
        write_new(out/"readback-result.json",encode(result));return result
    except BaseException as exc:
        primary=exc
        failure=dict(status="FAIL_CURRENT_RC_CONTACT_READBACK",current_context=ctx,
          error=dict(type=type(exc).__name__,message=str(exc)),traceback=traceback.format_exc(),**FLAGS)
        try:write_new(out/"readback-failure.json",encode(failure))
        except BaseException:
            try:print("CDR_RC_CONTACT_FAILURE "+json.dumps(failure,sort_keys=True),flush=True)
            except BaseException:pass
        raise
    finally:
        try:emit(out)
        except BaseException:
            if primary is None:raise

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--readback",action="store_true",required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--reservation",type=Path,required=True)
    p.add_argument("--controls-proof",type=Path,required=True)
    args=p.parse_args();ctx=context(os.environ)
    require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==ctx["source"],"checkout identity")
    require(args.reservation.is_file()and not args.reservation.is_symlink(),"reservation regular")
    require(args.controls_proof.is_file()and not args.controls_proof.is_symlink(),"controls regular")
    run(ctx,decode(args.reservation.read_bytes()),args.controls_proof.read_bytes(),args.output)
if __name__=="__main__":main()
