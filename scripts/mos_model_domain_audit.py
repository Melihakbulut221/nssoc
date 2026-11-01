#!/usr/bin/env python3
"""Audit exact MOS parameter/domain declarations in the existing native archive, cloud only."""
import base64,hashlib,json,os,pathlib,re,subprocess,tarfile
from decimal import Decimal
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"cloud-mos-model-domain-audit"
CFG="scripts/mos-model-domain-audit-inputs.json"
REPO="repos/Melihakbulut221/nssoc/"
def require(ok,label):
    if not ok:raise ValueError(label)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def enc(value):return(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def pin(path):
    with path.open("rb")as stream:return dict(bytes=path.stat().st_size,sha256=hashlib.file_digest(stream,"sha256").hexdigest())
def api(path):
    r=subprocess.run(["gh","api",REPO+path],capture_output=True,timeout=120)
    require(r.returncode==0,r.stderr.decode()[:2000]);return json.loads(r.stdout)
def fetch(p):
    d=api("contents/"+p["path"]+"?ref="+p["source"])
    b=d if d.get("content")else api("git/blobs/"+d["sha"])
    raw=base64.b64decode(b["content"])
    require(dict(bytes=len(raw),sha256=sha(raw))=={k:p[k]for k in("bytes","sha256")},"exact derived input")
    return raw
def restore(archive,inventory,wanted,directory,prefix="cloud-cdr-via2-m3-loaded"):
    """Hash every member; materialize only explicitly requested native members."""
    require(set(wanted)<=set(inventory)and not directory.exists(),"exclusive selected native output")
    directory.mkdir();seen=set();dirs=set();receipt={}
    with tarfile.open(archive,"r|gz")as tar:
        for member in tar:
            path=pathlib.PurePosixPath(member.name.rstrip("/"))
            require(not path.is_absolute()and ".."not in path.parts and str(path)==member.name.rstrip("/")and path.parts[0]==prefix,"owned archive path")
            if member.isdir():
                require(str(path)not in dirs,"duplicate archive directory");dirs.add(str(path));continue
            require(member.isreg()and len(path.parts)>1,"regular archive member only")
            name="/".join(path.parts[1:]);require(name in inventory and name not in seen,"complete unique archive member")
            expected=inventory[name];require(member.size==expected["bytes"],"member declared byte count")
            stream=tar.extractfile(member);require(stream is not None,"regular member stream")
            destination=(directory/("selected-"+str(len(receipt))))if name in wanted else None
            output=destination.open("xb")if destination else None
            h=hashlib.sha256();count=0
            try:
                while block:=stream.read(4*1024**2):
                    count+=len(block);require(count<=expected["bytes"],"bounded member stream");h.update(block)
                    if output:output.write(block)
            finally:
                stream.close()
                if output:output.close()
            require(dict(bytes=count,sha256=h.hexdigest())==expected,"complete member digest")
            seen.add(name)
            if destination:receipt[name]=dict(path=str(destination),**expected)
    require(seen==set(inventory)and set(receipt)==set(wanted),"all indexed members and requested files")
    return dict(verified_members=len(seen),all_members_verified=True,selected=receipt)

def selected_lines(lines):
    domain=re.compile(r"\b[wl](?:min|max)\b|(?:validity|valid|calibrat|characteriz).*range|range.*(?:valid|calibrat)|(?:finger.*width|width.*finger)|(?:maximum|minimum).*\b(?:width|length)\b|\bw\s*/\s*ng\b",re.I)
    parameter=re.compile(r"\b(?:w|l|ng|m|nf|mult)\s*=",re.I)
    branch=re.compile(r"\s*\.(?:if|elseif|else|endif)\b",re.I)
    ids={i for i,line in enumerate(lines)if domain.search(line)or parameter.search(line)or branch.match(line)}
    for i,line in enumerate(lines):
        if re.search(r"(?:valid|validity).*range",line,re.I):
            ids.update(range(max(0,i-1),min(len(lines),i+5)))
    return [dict(line=i+1,text=lines[i].strip())for i in sorted(ids)]
def selector_controls():
    require(selected_lines(["+ W=w NG=ng"])==[dict(line=1,text="+ W=w NG=ng")],"actual parameter mapping selection")
    require(selected_lines([".if (pre_layout)"])==[dict(line=1,text=".if (pre_layout)")],"actual branch selection")
    require([x["line"]for x in selected_lines(["* Valid range for model: L = (0.13 - 10)um","* W = (0.15 - 10)um"]) ]==[1,2],"continued range selection")
    require(selected_lines(["sg13_lv_nmos_thesatw=1.5"])==[],"unrelated model coefficient is not wrapper width")
    require(selected_lines(["+ nf=ng mult=m"])==[dict(line=1,text="+ nf=ng mult=m")],"core finger and multiplier mapping")
    return dict(checks=5,failures=0,scope="derived selector controls only")
def inspect_text(path):
    raw=path.read_bytes();lines=raw.decode().splitlines()
    rows=selected_lines(lines)
    headers=[dict(line=i,text=line.strip())for i,line in enumerate(lines,1)if re.match(r"\s*\.subckt\s+sg13_lv_[np]mos\b",line,re.I)]
    require(len(rows)<200,"bounded parameter/domain declaration report")
    return dict(file_pin=pin(path),total_lines=len(lines),domain_or_finger_expression_matches=rows,continuation_context_preserved=True,wrapper_parameter_selector_checked=True,device_headers=headers,no_match_is_not_domain_acceptance=True)
def scalar(value):
    m=re.fullmatch(r"([0-9]+(?:\.[0-9]*)?)([unp]?)",value)
    require(m is not None,"explicit geometry scalar")
    return Decimal(m[1])*{"":Decimal(1),"u":Decimal("1e-6"),"n":Decimal("1e-9"),"p":Decimal("1e-12")}[m[2]]

def decimal_close(a,b,label):
    require(abs(Decimal(str(a))-Decimal(str(b)))<=Decimal("1e-9"),label)
def joined_mos(comp,locations):
    records=comp["device_records"];physical=locations["devices"]
    require(len(records)==len(physical)==500,"complete500 both inputs")
    require(len({r["native_id"]for r in records})==len({r["native_id"]for r in physical})==500,"unique native identities")
    require({r["native_id"]for r in records}=={r["native_id"]for r in physical},"same full identity set")
    pm={r["native_id"]:r for r in physical};joined=[]
    for r in records:
        if r["model"]!="sg13_lv_nmos":continue
        p=pm[r["native_id"]];q=r["parameters"]
        require(p["model"]==r["model"]and q["ng"]==q["m"]=="1","exact model ng and multiplicity")
        rt={t["terminal"]:t for t in r["terminals"]};pt={t["name"]:t for t in p["terminals"]}
        require(set(rt)==set(pt)=={"D","G","S","B"}and len(r["terminals"])==len(p["terminals"])==4,"four unique terminals")
        for t in rt:require(rt[t]["native_cluster"]==pt[t]["native_cluster"]and rt[t]["native_net"]==pt[t]["net"],"terminal cluster and net")
        for k,unit in [("w","1e-6"),("l","1e-6"),("ad","1e-12"),("as","1e-12"),("pd","1e-6"),("ps","1e-6")]:
            decimal_close(scalar(q[k])/Decimal(unit),p["parameters"][k.upper()],"same extracted "+k)
        require(Decimal(q["rfmode"])==Decimal(str(p["parameters"]["rfmode"])),"same rfmode")
        gates=pt["G"]["native_layers"]
        require(len(gates)==1 and gates[0]["polygons"]==1,"single extracted gate polygon")
        m=re.fullmatch(r"\((-?\d+),(-?\d+);(-?\d+),(-?\d+)\)",gates[0]["bbox_dbu"])
        require(m is not None,"integer gate bbox");x0,y0,x1,y1=map(int,m.groups())
        require(x1>x0 and y1>y0 and (x1-x0)*(y1-y0)==gates[0]["area_dbu2"],"gate rectangle equals bbox area")
        require(p["pcell"]["path"]and p["pcell"]["cell"],"owned physical PCell")
        joined.append(dict(native_id=r["native_id"],simulation=r,physical=p,gate_rectangle_dbu=dict(dx=x1-x0,dy=y1-y0),gate_polygon_count=1))
    require(len(joined)==50 and len({j["physical"]["pcell"]["path"]for j in joined})==50,"complete50 distinct physical instances")
    return joined
def partition_units(width):
    # Candidate independent-device geometry on a declared 5 nm design grid.
    # This is not an assertion that these devices have been physically placed.
    grid=Decimal(".005");w=Decimal(width)
    require(w>0 and w/grid==(w/grid).to_integral_value(),"exact proposed width grid")
    n=int((w/Decimal("9")).to_integral_value(rounding="ROUND_CEILING"))
    steps=int(w/grid);base,remainder=divmod(steps,n)
    widths=[Decimal(base+(i<remainder))*grid for i in range(n)]
    require(sum(widths)==w and all(Decimal(".15")<=x<=Decimal("10")for x in widths),"preserved total width and explicit per-unit domain")
    return widths
def validate_plan(plan,joined):
    require(len(plan)==len(joined)==50 and {p["native_id"]for p in plan}=={j["native_id"]for j in joined},"complete unique plan origins")
    origins={j["native_id"]:j["simulation"]for j in joined};names=[]
    for p in plan:
        r=origins[p["native_id"]];q=r["parameters"];units=p["units"]
        require(units and p["source_instance"]==r["instance"],"source owner")
        require(sum(scalar(u["parameters"]["w"])for u in units)==scalar(q["w"]),"original total width conserved")
        for u in units:
            names.append(u["instance"]);v=u["parameters"]
            require(u["terminals"]==r["terminals"]and u["model"]==r["model"],"all four exact source connections")
            require(v["ng"]==v["m"]=="1"and v["l"]==q["l"]and v["rfmode"]==q["rfmode"],"length model mode and multiplicity conserved")
            w=scalar(v["w"])/Decimal("1e-6")
            require(Decimal(".15")<=w<=Decimal("10"),"unit width model domain")
            require(w/Decimal(".005")==(w/Decimal(".005")).to_integral_value(),"unit width on proposed grid")
            require(scalar(v["as"])==scalar(v["ad"])==w*Decimal(".34e-12"),"independent junction area")
            require(scalar(v["ps"])==scalar(v["pd"])==2*(w+Decimal(".34"))*Decimal("1e-6"),"independent junction perimeter")
    require(len(names)==len(set(names)),"unique expanded instances")
def make_plan(joined):
    plan=[]
    for j in joined:
        r=j["simulation"];q=r["parameters"];units=[]
        for i,w in enumerate(partition_units(scalar(q["w"])/Decimal("1e-6"))):
            v=dict(q,w=str(w)+"u",ad=str(w*Decimal(".34"))+"p",**{"as":str(w*Decimal(".34"))+"p"},
                pd=str(2*(w+Decimal(".34")))+"u",ps=str(2*(w+Decimal(".34")))+"u")
            units.append(dict(instance=r["instance"]+"_U"+str(i),model=r["model"],parameters=v,terminals=r["terminals"]))
        plan.append(dict(native_id=r["native_id"],source_instance=r["instance"],original_parameters=q,units=units))
    validate_plan(plan,joined);return plan
def physical_controls(comp,locations,joined,plan):
    import copy
    checks=[]
    def refuses(label,fun):
        try:fun()
        except ValueError:checks.append(label)
        else:raise ValueError("accepted corrupt control: "+label)
    def change_physical(fn):
        p=copy.deepcopy(locations);fn(p["devices"]);return joined_mos(comp,p)
    target=joined[0]["native_id"]
    def one(rows):return next(r for r in rows if r["native_id"]==target)
    refuses("missing physical device",lambda:change_physical(lambda rows:rows.pop()))
    refuses("duplicate physical identity",lambda:change_physical(lambda rows:rows.__setitem__(-1,copy.deepcopy(rows[0]))))
    refuses("changed extracted width",lambda:change_physical(lambda rows:one(rows)["parameters"].__setitem__("W",1)))
    refuses("changed terminal cluster",lambda:change_physical(lambda rows:one(rows)["terminals"][0].__setitem__("native_cluster",-99)))
    refuses("changed model",lambda:change_physical(lambda rows:one(rows).__setitem__("model","wrong")))
    def corrupt_gate(rows):
        g=next(t for t in one(rows)["terminals"]if t["name"]=="G")["native_layers"][0];g["polygons"]=2
    refuses("unqualified multiple gate polygons",lambda:change_physical(corrupt_gate))
    def change_plan(fn):
        p=copy.deepcopy(plan);fn(p);validate_plan(p,joined)
    refuses("missing plan origin",lambda:change_plan(lambda p:p.pop()))
    refuses("changed unit width",lambda:change_plan(lambda p:p[0]["units"][0]["parameters"].__setitem__("w","54u")))
    refuses("changed unit length",lambda:change_plan(lambda p:p[0]["units"][0]["parameters"].__setitem__("l","0.5u")))
    refuses("changed unit connection",lambda:change_plan(lambda p:p[0]["units"][0]["terminals"][0].__setitem__("node","wrong")))
    refuses("stale wide junction perimeter",lambda:change_plan(lambda p:p[0]["units"][0]["parameters"].__setitem__("pd",p[0]["original_parameters"]["pd"])))
    refuses("metadata-only finger repair",lambda:change_plan(lambda p:p[0]["units"][0]["parameters"].__setitem__("ng","4")))
    require(len(checks)==12,"twelve corruption controls")
    return dict(checks=len(checks),failures=0,refused=checks)


def rewrite_parallel(text,comp,plan,joined):
    validate_plan(plan,joined)
    origins={r["native_id"]:r for r in comp["device_records"]}
    result=text;deltas=[];expanded=[]
    plan_by_id={p["native_id"]:p for p in plan}
    for p in plan:
        r=origins[p["native_id"]];name=r["instance"]
        pattern=re.compile(r"(?mi)^"+re.escape(name)+r"[ \t][^\r\n]*(?:\r?\n\+[^\r\n]*)*")
        matches=list(pattern.finditer(result));require(len(matches)==1,"one original MOS card "+name)
        match=matches[0];before=match.group();words=re.sub(r"\r?\n\+"," ",before).split()
        nodes=[t["node"]for t in r["terminals"]]
        require(words[:6]==[name,*nodes,r["model"]],"original MOS ordered card binding")
        require(len(words[6:])==len(r["parameters"])and set(words[6:])=={k+"="+v for k,v in r["parameters"].items()},"complete original MOS parameters")
        cards=[]
        for u in p["units"]:
            require(not re.search(r"(?mi)^"+re.escape(u["instance"])+r"[ \t]",result),"exclusive candidate instance")
            cards.append(" ".join([u["instance"],*[t["node"]for t in u["terminals"]],u["model"],*[k+"="+v for k,v in sorted(u["parameters"].items())]]))
        after="\n".join(cards);result=result[:match.start()]+after+result[match.end():]
        deltas.append(dict(native_id=r["native_id"],source_instance=name,before=before,after=after,unit_instances=[u["instance"]for u in p["units"]]))
    reverse=result
    for d in deltas:
        require(reverse.count(d["after"])==1,"unique full expanded card block")
        reverse=reverse.replace(d["after"],d["before"],1)
    require(reverse==text,"all other original model bytes and distributed RC preserved")
    old_names=re.findall(r"(?mi)^(XD[0-9]+)[ \t]",text)
    new_names=re.findall(r"(?mi)^(XD[0-9]+(?:_U[0-9]+)?)[ \t]",result)
    require(len(old_names)==len(set(old_names))==500,"all original500 native card identities")
    require(len(new_names)==len(set(new_names))==650,"complete650 unique expanded native cards")
    expected={r["instance"]for r in comp["device_records"]if r["native_id"]not in plan_by_id}|{u["instance"]for p in plan for u in p["units"]}
    require(set(new_names)==expected,"only explicitly declared 50-to200 expansion")
    for r in comp["device_records"]:
        if r["native_id"]in plan_by_id:
            for u in plan_by_id[r["native_id"]]["units"]:
                expanded.append(dict(source_native_id=r["native_id"],candidate_instance=u["instance"],device=u))
        else:expanded.append(dict(source_native_id=r["native_id"],candidate_instance=r["instance"],device=r))
    require(len(expanded)==650,"complete origin expansion mapping")
    return result,expanded,deltas
def renderer_controls(comp,plan,joined):
    import copy
    cards=[]
    for r in comp["device_records"]:
        cards.append(" ".join([r["instance"],*[t["node"]for t in r["terminals"]],r["model"],*[k+"="+v for k,v in sorted(r["parameters"].items())]]))
    fixture="* synthetic full500 binding control only\n"+"\n".join(cards)+"\nR_SENTINEL a b 7\n.end\n"
    output,expanded,delta=rewrite_parallel(fixture,comp,plan,joined)
    require("R_SENTINEL a b 7\n.end\n"in output and len(expanded)==650,"positive complete binding and unaffected bytes")
    first=joined[0]["simulation"];line=next(x for x in cards if x.startswith(first["instance"]+" "))
    cases={"duplicate original MOS":fixture+line+"\n",
        "missing original MOS":fixture.replace(line+"\n","",1),
        "wrong model terminal":fixture.replace(line,line.replace(first["terminals"][0]["node"],"bad_node",1),1),
        "wrong original width":fixture.replace(line,line.replace("w="+first["parameters"]["w"],"w=1u",1),1),
        "extra original token":fixture.replace(line,line+" bad=1",1),
        "missing other device":fixture.replace(next(x for x in cards if x.startswith("XD0500 "))+"\n","",1),
        "preexisting expanded identity":fixture+plan[0]["units"][0]["instance"]+" d g s b sg13_lv_nmos\n"}
    refused=[]
    for label,bad in cases.items():
        try:rewrite_parallel(bad,comp,plan,joined)
        except ValueError:refused.append(label)
        else:raise ValueError("renderer accepted invalid control "+label)
    require(len(refused)==7,"seven renderer corruptions")
    return dict(checks=8,positive_complete500_to650=True,refused=refused,failures=0,synthetic_fixture_not_native_acceptance=True)
def output_reservation():
    import time
    tag="cloud-results-"+os.environ["GITHUB_RUN_ID"]+"-1-mos-parallel-candidate"
    for attempt in range(90):
        p=subprocess.run(["gh","api",REPO+"releases/tags/"+tag],capture_output=True,timeout=120)
        if p.returncode==0:break
        require(b"HTTP 404"in p.stderr,"reservation read failure");time.sleep(2)
    else:raise ValueError("independent exact-source output reservation missing")
    r=json.loads(p.stdout);ref=api("git/ref/tags/"+tag)
    require(r["target_commitish"]==os.environ["GITHUB_SHA"]and r["tag_name"]==tag and r["assets"]==[]and r["prerelease"]and not r["draft"],"empty independent exact-source release")
    require(ref["object"]["type"]=="commit"and ref["object"]["sha"]==os.environ["GITHUB_SHA"],"exact output tag")
    return r
def publish_native_generation(directory,reservation):
    expected={p.name:pin(p)for p in directory.iterdir()if p.is_file()}
    require(set(expected)=={"model.spice","candidate-expansion.json","source-composition.json","native-generation.json"},"complete native candidate output set")
    for name in expected:
        p=subprocess.run(["gh","release","upload",reservation["tag_name"],str(directory/name),"--repo","Melihakbulut221/nssoc"],capture_output=True,timeout=600)
        require(p.returncode==0,p.stderr.decode()[:2000])
    observed=api("releases/"+str(reservation["id"]))
    require(len(observed["assets"])==len(expected)and {a["name"]for a in observed["assets"]}==set(expected),"all native outputs published")
    for a in observed["assets"]:require(a["size"]==expected[a["name"]]["bytes"]and a["digest"]=="sha256:"+expected[a["name"]]["sha256"],"exact published bytes")
    return dict(release=observed["id"],tag=observed["tag_name"],source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),outputs=expected,assets=observed["assets"],simulation_executed=False,physical_acceptance=False)

def main():
    require(os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("GITHUB_RUN_ATTEMPT")=="1"and os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc","single cloud execution")
    c=json.loads((ROOT/CFG).read_bytes())
    for p,expected in c["source_files"].items():require(pin(ROOT/p)==expected,"exact audit source")
    OUT.mkdir(exist_ok=False)
    (OUT/"selector-controls.json").write_bytes(enc(selector_controls()))
    for p in [*c["source_files"],CFG]:
        target=OUT/"source"/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/p).read_bytes())
    values={}
    for name,p in c["inputs"].items():
        raw=fetch(p);(OUT/name).write_bytes(raw);values[name]=json.loads(raw)
    comp_pre=values["composition.json"];joined_pre=joined_mos(comp_pre,values["physical-locations.json"]);plan_pre=make_plan(joined_pre)
    (OUT/"renderer-controls.json").write_bytes(enc(renderer_controls(comp_pre,plan_pre,joined_pre)))
    reservation=output_reservation();(OUT/"output-reservation.json").write_bytes(enc(reservation))
    index=values["index.json"];parts=values["parts.json"]
    require(index["files"]["native/candidate/model.spice"]==dict(bytes=1967632,sha256="4b5c155517c81990e528190b6ebd0405a876184da57224233fd1f05ae25d658b"),"exact existing mixed20 native model")
    require(parts["context"]==index["context"]==c["producer_context"]and parts["archive"]==c["archive"],"exact native producer and complete archive")
    run=api("actions/runs/"+str(c["producer_context"]["run_id"]));release=api("releases/"+str(c["release_id"]));tag=api("git/ref/tags/"+c["release_tag"])
    require(run["status"]=="completed"and run["conclusion"]=="failure"and run["run_attempt"]==1 and run["head_sha"]==c["producer_context"]["source"],"actual producer identity")
    require(release["target_commitish"]==c["producer_context"]["source"]and release["tag_name"]==c["release_tag"]and tag["object"]["type"]=="commit"and tag["object"]["sha"]==c["producer_context"]["source"],"exact archive release")
    assets={a["name"]:a for a in release["assets"]}
    require(len(assets)==len(release["assets"])==6 and len(parts["parts"])==4 and len(index["files"])==109,"complete release and archive inventory")
    work=pathlib.Path(os.environ["RUNNER_TEMP"])/("nssoc-mos-model-audit-"+os.environ["GITHUB_RUN_ID"]);work.mkdir(exist_ok=False)
    archive=work/"complete-native.tar.gz";observations=[]
    with archive.open("xb")as output:
        for i,row in enumerate(parts["parts"]):
            a=assets[row["name"]];require(row["index"]==i and a["state"]=="uploaded"and a["size"]==row["bytes"]and a["digest"]=="sha256:"+row["sha256"],"exact ordered archive part")
            p=work/("part-"+str(i))
            with p.open("xb")as stream:r=subprocess.run(["gh","api",REPO+"releases/assets/"+str(a["id"]),"-H","Accept: application/octet-stream"],stdout=stream,stderr=subprocess.PIPE,timeout=600)
            observed=pin(p);require(r.returncode==0 and observed=={k:row[k]for k in("bytes","sha256")},"complete part acquired")
            observations.append(dict(index=i,asset=a["id"],pin=observed));(OUT/"acquisition.json").write_bytes(enc(observations))
            with p.open("rb")as stream:
                while block:=stream.read(4*1024**2):output.write(block)
    require(pin(archive)==c["archive"],"complete native archive digest")
    selected=restore(archive,index["files"],set(c["model_members"])|{"native/candidate/model.spice"},work/"selected",prefix="cloud-sampler-load")
    (OUT/"restore.json").write_bytes(enc(selected))
    models={name:inspect_text(pathlib.Path(value["path"]))for name,value in selected["selected"].items()if name in c["model_members"]}
    comp=values["composition.json"];require(len(comp["device_records"])==500 and len({r["native_id"]for r in comp["device_records"]})==500,"complete composition")
    mos=[]
    for r in comp["device_records"]:
        if not {"D","G","S","B"}<={t["terminal"]for t in r["terminals"]}:continue
        p=r["parameters"];ng=int(p["ng"]);require(ng>0,"positive gate count")
        mos.append(dict(native_id=r["native_id"],model=r["model"],parameters=p,
            total_width_um=str(scalar(p["w"])/Decimal("1e-6")),
            reported_finger_width_um=str(scalar(p["w"])/ng/Decimal("1e-6"))))
    require(len(mos)==50,"all50 MOS geometry records")
    # This conclusion applies to the current explicit ng=1 records, not inferred layout fingers.
    require(all(r["parameters"]["ng"]=="1"for r in mos),"current single-finger simulation census")
    for suffix in ("cornerMOSlv.lib","sg13g2_moslv_parm.lib"):
        entries=[v for k,v in models.items()if k.endswith("/"+suffix)]
        require(len(entries)==1 and any(re.search(r"\bW\s*=\s*\(0\.15\s*-\s*10\)um",x["text"])for x in entries[0]["domain_or_finger_expression_matches"]),"exact declared W range in used model")
    outside=[r for r in mos if not Decimal(".15")<=Decimal(r["reported_finger_width_um"])<=Decimal("10")]

    joined=joined_mos(comp,values["physical-locations.json"]);plan=make_plan(joined)
    controls=physical_controls(comp,values["physical-locations.json"],joined,plan)
    (OUT/"physical-controls.json").write_bytes(enc(controls))
    (OUT/"physical-join.json").write_bytes(enc(dict(status="COMPLETE50_PINNED_PHYSICAL_JOIN_NOT_NEW_EXTRACTION",devices=joined,physical_input=c["inputs"]["physical-locations.json"],no_new_layout=True)))
    (OUT/"parallel-device-plan.json").write_bytes(enc(dict(status="PROPOSED_PARALLEL_DEVICE_PLAN_NOT_NATIVE_ACCEPTANCE",devices=plan,original_mos_count=50,proposed_mos_count=sum(len(p["units"])for p in plan),unmodified_other_devices=450,proposed_total_device_count=450+sum(len(p["units"])for p in plan),proposed_width_grid_um=".005",source_drain_extension_um=".34",new_layout_generated=False,new_netlist_generated=False,fresh_parasitics=False,model_domain_passed_for_proposed_unit_widths_only=True,original_other_devices_sha256=sha(enc([r for r in comp["device_records"]if r["model"]!="sg13_lv_nmos"])),caveat="Explicit independent devices, not ng-only. Junction perimeters change. Contacts, spacing, routing, body taps, extracted identity expansion, model core mapping and independent DRC/LVS/PEX/electrical gates remain to be proven.")))
    original_path=pathlib.Path(selected["selected"]["native/candidate/model.spice"]["path"])
    candidate,expanded,deltas=rewrite_parallel(original_path.read_text(),comp,plan,joined)
    native=ROOT/"cloud-mos-parallel-native";native.mkdir(exist_ok=False)
    (native/"model.spice").write_text(candidate)
    (native/"source-composition.json").write_bytes((OUT/"composition.json").read_bytes())
    (native/"candidate-expansion.json").write_bytes(enc(dict(schema="explicit-origin500-to-native650-v1",expanded_device_records=expanded,original_device_count=500,expanded_device_count=650,model_mos_count=200,geometry_regenerated=False,wire_rc_recomputed=False)))
    generation=dict(source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),original_model=pin(original_path),candidate_model=pin(native/"model.spice"),original_composition=pin(OUT/"composition.json"),expanded_composition=pin(native/"candidate-expansion.json"),delta=[{k:v for k,v in row.items()if k not in ("before","after")}|dict(before_sha256=sha(row["before"].encode()),after_sha256=sha(row["after"].encode()))for row in deltas],all_other_model_bytes_preserved=True,native_simulation_executed=False,physical_acceptance=False,fresh_rc=False,full_phy_accepted=False,final_timing_complete=False)
    (native/"native-generation.json").write_bytes(enc(generation));(OUT/"native-generation.json").write_bytes(enc(generation))
    (OUT/"native-publication.json").write_bytes(enc(publish_native_generation(native,reservation)))
    result=dict(status="COMPLETE_PINNED_MOS_MODEL_PARAMETER_AUDIT_NOT_ACCEPTANCE",
        source=os.environ["GITHUB_SHA"],run=int(os.environ["GITHUB_RUN_ID"]),producer_context=c["producer_context"],
        native_archive=c["archive"],models=models,all50_mos=mos,physical_join_count=len(joined),parallel_proposed_units=sum(len(p["units"])for p in plan),declared_width_range_um=["0.15","10"],
        all50_current_simulation_ng_one=True,outside_declared_width_range=outside,model_width_domain_passed=not outside,
        proposed_slave_width_trial=dict(native_ids=[7,8,9,10,36,37,38,39],width_um=54,ng=1,dispatched=False,model_domain_qualified=False),
        interpretation="Range declarations and width/finger mapping from the exact used model must be interpreted before a new width trial. LVS total-width equality and prior stress-gate success are not model-domain qualification. No model file or raw archive is included in derived outputs.",
        native_models_retained_on_runner_only=True,native_simulation_rerun=False,geometry_changed=False,physical_acceptance=False,full_phy_accepted=False,final_timing_complete=False)
    (OUT/"producer.json").write_bytes(enc(dict(run=run,release=release,tag=tag)))
    (OUT/"result.json").write_bytes(enc(result));print(json.dumps(dict(status=result["status"],models=models,mos_geometry_census=len(mos))),flush=True)
if __name__=="__main__":main()
